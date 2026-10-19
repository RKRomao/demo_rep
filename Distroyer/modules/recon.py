"""
Reconnaissance Module - DNS, WHOIS, IP info, ASN, robots.txt, sitemap
"""
import socket
import json
import re
from .base import BaseModule


class ReconModule(BaseModule):
    """Passive and active reconnaissance module."""

    def run(self) -> dict:
        domain = self.get_domain()
        base = self.get_base_url()

        self._check_dns(domain)
        self._check_whois(domain)
        self._check_ip_info(domain)
        self._check_robots(base)
        self._check_sitemap(base)
        self._check_security_txt(base)
        self._check_well_known(base)
        self._check_git_exposure(base)
        self._check_backup_files(base)
        self._check_metadata_files(base)

        return self.result({'domain': domain})

    def _check_dns(self, domain):
        records = {}
        try:
            addr_info = socket.getaddrinfo(domain, None)
            ips = []
            for r in addr_info:
                ip = r[4][0]
                if ip and ip not in ips:
                    ips.append(ip)
            if ips:
                records['A'] = ips
                self.context['ips'] = ips
                self.context['ip'] = ips[0]
        except Exception:
            pass

        try:
            import dns.resolver
            for rtype in ['MX', 'NS', 'TXT', 'CNAME', 'SOA', 'AAAA']:
                try:
                    ans = dns.resolver.resolve(domain, rtype)
                    records[rtype] = [str(r) for r in ans]
                except Exception:
                    pass
        except ImportError:
            pass

        if records:
            self.add_finding(
                'DNS Records Enumerated',
                'INFO',
                f"Found {len(records)} record types",
                json.dumps(records, indent=2)[:500],
                'Review DNS for information leakage (TXT, SPF, DMARC).'
            )
        
        # Check zone transfer
        self._check_zone_transfer(domain)

    def _check_zone_transfer(self, domain):
        try:
            import dns.resolver
            import dns.query
            import dns.zone
            ns_records = dns.resolver.resolve(domain, 'NS')
            for ns in ns_records:
                ns_str = str(ns).rstrip('.')
                try:
                    z = dns.zone.from_xfr(dns.query.xfr(ns_str, domain, timeout=5))
                    if z:
                        self.add_finding(
                            'DNS Zone Transfer Allowed',
                            'CRITICAL',
                            f'NS {ns_str} allows zone transfer (AXFR)',
                            f'Exposed {len(list(z.nodes.keys()))} DNS records',
                            'Disable zone transfers on all authoritative nameservers.'
                        )
                except Exception:
                    pass
        except Exception:
            pass

    def _check_whois(self, domain):
        try:
            import whois
            w = whois.whois(domain)
            detail = (
                f"Registrar: {w.registrar}\n"
                f"Created: {w.creation_date}\n"
                f"Expires: {w.expiration_date}\n"
                f"Name Servers: {w.name_servers}"
            )
            self.add_finding('WHOIS Information', 'INFO', 'Domain registration data', detail[:400])
        except Exception:
            pass

    def _check_ip_info(self, domain):
        try:
            ip = socket.gethostbyname(domain)
            resp = self.get(f'https://ipinfo.io/{ip}/json')
            if resp and resp.status_code == 200:
                data = resp.json()
                detail = f"IP: {ip}\nOrg: {data.get('org','')}\nCity: {data.get('city','')}\nCountry: {data.get('country','')}"
                self.add_finding('IP & ASN Information', 'INFO', f'Target resolves to {ip}', detail)
        except Exception:
            pass

    def _check_robots(self, base):
        resp = self.get(f'{base}/robots.txt')
        if resp and resp.status_code == 200 and 'Disallow' in resp.text:
            # Extract disallowed paths
            disallowed = re.findall(r'Disallow:\s*(.+)', resp.text)
            self.add_finding(
                'robots.txt Found',
                'INFO',
                f'{len(disallowed)} disallowed paths found',
                '\n'.join(disallowed[:20]),
                'Review disallowed paths - they may reveal sensitive endpoints.'
            )
            # Check for sensitive paths
            sensitive = [p for p in disallowed if any(k in p.lower() for k in 
                        ['admin', 'config', 'backup', 'api', 'secret', 'private', 'token'])]
            if sensitive:
                self.add_finding(
                    'Sensitive Paths in robots.txt',
                    'MEDIUM',
                    'Potentially sensitive paths exposed',
                    '\n'.join(sensitive),
                    'Avoid listing sensitive paths in robots.txt as it guides attackers.'
                )

    def _check_sitemap(self, base):
        for path in ['/sitemap.xml', '/sitemap_index.xml', '/sitemap.xml.gz']:
            resp = self.get(f'{base}{path}')
            if resp and resp.status_code == 200:
                urls = re.findall(r'<loc>(.*?)</loc>', resp.text)
                self.add_finding(
                    'Sitemap Discovered',
                    'INFO',
                    f'{len(urls)} URLs in sitemap',
                    path
                )
                break

    def _check_security_txt(self, base):
        for path in ['/.well-known/security.txt', '/security.txt']:
            resp = self.get(f'{base}{path}')
            if resp and resp.status_code == 200:
                self.add_finding('security.txt Present', 'INFO', 
                                'Security contact policy file found', path)
                return
        self.add_finding(
            'No security.txt',
            'LOW',
            'No security.txt file found',
            '',
            'Add /.well-known/security.txt for responsible disclosure.'
        )

    def _check_well_known(self, base):
        paths = ['/.well-known/openid-configuration', '/.well-known/jwks.json',
                 '/.well-known/oauth-authorization-server']
        for path in paths:
            resp = self.get(f'{base}{path}')
            if resp and resp.status_code == 200:
                self.add_finding(
                    f'Well-known endpoint: {path}',
                    'INFO',
                    'OAuth/OIDC configuration exposed',
                    path
                )

    def _check_git_exposure(self, base):
        git_paths = ['/.git/HEAD', '/.git/config', '/.git/COMMIT_EDITMSG', '/.svn/wc.db']
        for path in git_paths:
            resp = self.get(f'{base}{path}', allow_redirects=True)
            if resp and resp.status_code == 200:
                final_url = getattr(resp, 'url', None)
                if final_url and any(final_url.lower().endswith(ap) for ap in ('/login', '/signin', '/auth', '/404', '/error')):
                    continue
                if path.endswith('HEAD') and 'ref:' in resp.text:
                    loot = self.extract_file(f'{base}{path}', content=resp.content)
                    self.add_finding(
                        'Git Repository Exposed',
                        'CRITICAL',
                        f'.git directory accessible: {path}',
                        resp.text[:200],
                        'Block access to /.git directory in web server config.',
                        loot=loot
                    )
                elif '.svn' in path and b'SQLite format 3' in resp.content[:50]:
                    loot = self.extract_file(f'{base}{path}', content=resp.content)
                    self.add_finding(
                        'SVN Repository Exposed',
                        'HIGH',
                        f'SVN repository accessible: {path}',
                        'Valid SVN wc.db SQLite database confirmed.',
                        'Block access to /.svn directory.',
                        loot=loot
                    )

    def _check_backup_files(self, base):
        p = self.get_parsed_url()
        path = p.path or '/'
        base_name = path.rstrip('/').split('/')[-1] or 'index'
        
        backups = [
            f'{base}/{base_name}.bak', f'{base}/{base_name}.old',
            f'{base}/{base_name}.backup', f'{base}/backup.zip',
            f'{base}/backup.tar.gz', f'{base}/dump.sql',
            f'{base}/db.sql', f'{base}/database.sql',
            f'{base}/config.php.bak', f'{base}/web.config.bak',
            f'{base}/.env.backup', f'{base}/.env.old',
        ]
        from .extractor import FileExtractor
        for url in backups:
            resp = self.get(url, allow_redirects=False)
            if resp and resp.status_code in (200, 301, 302, 307, 308):
                loc = resp.headers.get('Location', '')
                if resp.status_code == 200:
                    if FileExtractor.validate_file_content(url, resp.content):
                        ct = resp.headers.get('Content-Type', '').lower()
                        loot = self.extract_file(url, content=resp.content)
                        self.add_finding(
                            'Backup File Exposed',
                            'HIGH',
                            f'Backup/sensitive file found: {url}',
                            f'Status: 200, Size: {len(resp.content)} bytes, Content-Type: {ct}',
                            'Remove all backup files from web-accessible directories.',
                            loot=loot
                        )
                    else:
                        self.add_finding(
                            'Backup Path Found (HTML)',
                            'INFO',
                            f'Backup path returned HTML page: {url}',
                            f'Status: 200, Size: {len(resp.content)} bytes',
                            'Verify if backup file is actually served or handled by custom 404/login.'
                        )
                else:
                    # 301, 302, etc. Check if redirect leads to an authentic file (e.g. S3 / CDN)
                    resp_follow = self.get(url, allow_redirects=True)
                    if resp_follow and resp_follow.status_code == 200 and FileExtractor.validate_file_content(url, resp_follow.content, final_url=getattr(resp_follow, 'url', None)):
                        loot = self.extract_file(url, content=resp_follow.content)
                        self.add_finding(
                            'Backup File Exposed',
                            'HIGH',
                            f'Backup/sensitive file found: {url}',
                            f'Status: {resp_follow.status_code}, Size: {len(resp_follow.content)} bytes (via redirect)',
                            'Remove all backup files from web-accessible directories.',
                            loot=loot
                        )
                    else:
                        self.add_finding(
                            'Backup Path Redirects',
                            'INFO',
                            f'Backup path redirects: {url}',
                            f'HTTP {resp.status_code} -> {loc}',
                            'Verify if redirect destination protects the intended resource.'
                        )

    def _check_metadata_files(self, base):
        meta = [
            '/.env', '/config.yaml', '/config.yml', '/config.json',
            '/app.config', '/web.config', '/phpinfo.php', '/info.php',
            '/server-status', '/server-info', '/_profiler',
            '/actuator', '/actuator/env', '/actuator/health',
            '/api/swagger.json', '/api/openapi.json', '/swagger-ui.html',
            '/graphql', '/graphiql', '/__debug__', '/debug',
            '/console', '/adminer.php', '/phpmyadmin/',
        ]
        from .extractor import FileExtractor
        for path in meta:
            resp = self.get(f'{base}{path}', allow_redirects=False)
            if resp and resp.status_code in (200, 301, 302, 307, 308):
                loc = resp.headers.get('Location', '')
                is_file = any(path.endswith(ext) for ext in ('.env', '.yaml', '.yml', '.json', '.config', '.php', '.html'))
                if resp.status_code == 200:
                    if FileExtractor.validate_file_content(path, resp.content):
                        ct = resp.headers.get('Content-Type', '').lower()
                        loot = self.extract_file(f'{base}{path}', content=resp.content) if is_file else None
                        self.add_finding(
                            f'Sensitive Endpoint Found: {path}',
                            'HIGH',
                            f'Accessible: {base}{path}',
                            f'Content-Type: {ct}',
                            'Restrict or remove this endpoint from production.',
                            loot=loot
                        )
                    else:
                        self.add_finding(
                            f'Endpoint Accessible (HTML): {path}',
                            'INFO',
                            f'Endpoint returned HTML: {base}{path}',
                            f'Status: 200',
                            'Review public endpoint.'
                        )
                else:
                    # 301, 302
                    resp_follow = self.get(f'{base}{path}', allow_redirects=True)
                    if resp_follow and resp_follow.status_code == 200 and FileExtractor.validate_file_content(path, resp_follow.content, final_url=getattr(resp_follow, 'url', None)):
                        loot = self.extract_file(f'{base}{path}', content=resp_follow.content) if is_file else None
                        self.add_finding(
                            f'Sensitive Endpoint Found: {path}',
                            'HIGH',
                            f'Accessible via redirect: {base}{path}',
                            f'Status: {resp_follow.status_code}',
                            'Restrict or remove this endpoint from production.',
                            loot=loot
                        )
                    else:
                        self.add_finding(
                            f'Endpoint Redirects: {path}',
                            'INFO',
                            f'Endpoint redirects: {base}{path}',
                            f'HTTP {resp.status_code} -> {loc}',
                            'Review endpoint redirection.'
                        )
