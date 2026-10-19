"""
Technology Fingerprinting Module
Detects CMS, frameworks, server stack, JS libs, WAF
"""
import re
from .base import BaseModule


# Signatures: (pattern_in_body_or_header, technology_name, confidence)
SIGNATURES = {
    'WordPress': [
        (r'wp-content/', 'body'), (r'wp-includes/', 'body'),
        (r'WordPress', 'header:X-Powered-By'), (r'/wp-login\.php', 'body'),
    ],
    'Drupal': [
        (r'Drupal', 'header:X-Generator'), (r'/sites/default/files/', 'body'),
        (r'Drupal\.settings', 'body'),
    ],
    'Joomla': [
        (r'/media/jui/', 'body'), (r'Joomla!', 'body'),
    ],
    'Laravel': [
        (r'laravel_session', 'cookie'), (r'Laravel', 'header:X-Powered-By'),
        (r'XSRF-TOKEN', 'cookie'),
    ],
    'Django': [
        (r'csrfmiddlewaretoken', 'body'), (r'Django', 'header:X-Powered-By'),
        (r'djdt', 'body'),
    ],
    'React': [
        (r'react\.development\.js', 'body'), (r'__REACT_DEVTOOLS', 'body'),
        (r'data-reactroot', 'body'), (r'data-reactid', 'body'),
    ],
    'Angular': [
        (r'ng-version=', 'body'), (r'angular\.min\.js', 'body'),
        (r'__ngContext__', 'body'),
    ],
    'Vue.js': [
        (r'vue\.min\.js', 'body'), (r'__vue_', 'body'),
        (r'Vue\.config', 'body'),
    ],
    'Next.js': [
        (r'__NEXT_DATA__', 'body'), (r'/_next/static/', 'body'),
    ],
    'Nuxt.js': [
        (r'__NUXT__', 'body'), (r'/_nuxt/', 'body'),
    ],
    'jQuery': [
        (r'jquery[.\-](\d+[\.\d]+)\.min\.js', 'body'),
    ],
    'Bootstrap': [
        (r'bootstrap[.\-](\d+[\.\d]+)\.min\.(css|js)', 'body'),
    ],
    'PHP': [
        (r'PHP', 'header:X-Powered-By'), (r'\.php', 'body'),
        (r'PHPSESSID', 'cookie'),
    ],
    'ASP.NET': [
        (r'ASP\.NET', 'header:X-Powered-By'), (r'__VIEWSTATE', 'body'),
        (r'ASPNET', 'cookie'),
    ],
    'Ruby on Rails': [
        (r'_session_id', 'cookie'), (r'X-Runtime', 'header:X-Runtime'),
    ],
    'Express.js': [
        (r'X-Powered-By: Express', 'header:X-Powered-By'),
    ],
    'Nginx': [
        (r'nginx', 'header:Server'),
    ],
    'Apache': [
        (r'Apache', 'header:Server'),
    ],
    'Cloudflare': [
        (r'cloudflare', 'header:Server'), (r'cf-ray', 'header:CF-Ray'),
        (r'__cfduid', 'cookie'),
    ],
    'AWS CloudFront': [
        (r'CloudFront', 'header:X-Cache'), (r'cloudfront', 'header:Via'),
    ],
    'Shopify': [
        (r'myshopify\.com', 'body'), (r'Shopify\.theme', 'body'),
    ],
    'GraphQL': [
        (r'"__schema"', 'body'), (r'graphql', 'body'),
    ],
}

WAF_SIGNATURES = {
    'Cloudflare': ['CF-Ray', 'cloudflare'],
    'Akamai': ['AkamaiGHost', 'x-check-cacheable'],
    'Imperva / Incapsula': ['incap_ses', '_incap_'],
    'ModSecurity': ['Mod_Security', 'NOYB'],
    'Sucuri': ['Sucuri/Cloudproxy', 'x-sucuri-id'],
    'F5 BIG-IP ASM': ['TS01', 'BigIP'],
    'Barracuda': ['barra_counter_session'],
    'AWS WAF': ['x-amzn-RequestId', 'awselb'],
    'Wordfence': ['wordfence'],
}


class FingerprintModule(BaseModule):
    """Technology fingerprinting and WAF detection."""

    def run(self) -> dict:
        resp = self.get(self.url)
        if not resp:
            return self.result({'error': 'Could not fetch URL'})

        body = resp.text or ''
        headers = resp.headers
        cookies = {c.name: c.value for c in resp.cookies}

        techs = self._detect_technologies(body, headers, cookies)
        self._detect_waf(body, headers, cookies)
        self._check_outdated_versions(body)
        self._check_admin_panels(resp)

        return self.result({'technologies': techs})

    def _detect_technologies(self, body, headers, cookies):
        found = []
        for tech, sigs in SIGNATURES.items():
            detected = False
            for pattern, source in sigs:
                try:
                    if source == 'body':
                        if re.search(pattern, body, re.IGNORECASE):
                            detected = True
                            break
                    elif source.startswith('header:'):
                        hname = source.split(':', 1)[1]
                        hval = headers.get(hname, '')
                        if re.search(pattern, hval, re.IGNORECASE):
                            detected = True
                            break
                    elif source == 'cookie':
                        for cname, cval in cookies.items():
                            if re.search(pattern, cname + cval, re.IGNORECASE):
                                detected = True
                                break
                except Exception:
                    pass
            if detected:
                found.append(tech)

        if found:
            self.add_finding(
                'Technologies Detected',
                'INFO',
                f'Identified {len(found)} technologies',
                ', '.join(found),
                'Remove version information from headers and source code.'
            )
        return found

    def _detect_waf(self, body, headers, cookies):
        all_headers_str = str(dict(headers)).lower()
        all_cookies_str = str(cookies).lower()
        combined = all_headers_str + all_cookies_str + body[:2000].lower()

        for waf, indicators in WAF_SIGNATURES.items():
            for ind in indicators:
                if ind.lower() in combined:
                    self.add_finding(
                        f'WAF Detected: {waf}',
                        'INFO',
                        f'Web Application Firewall detected: {waf}',
                        f'Indicator: {ind}',
                        'WAF detected - adapt payloads to bypass if authorized.'
                    )
                    break

    def _check_outdated_versions(self, body):
        """Detect potentially outdated software versions."""
        version_patterns = [
            (r'jQuery v?(\d+\.\d+\.\d+)', 'jQuery', '3.7.0'),
            (r'bootstrap[/ ](\d+\.\d+\.\d+)', 'Bootstrap', '5.3.0'),
            (r'Angular[/ ](\d+\.\d+)', 'Angular', '17'),
            (r'react[/ ](\d+\.\d+)', 'React', '18'),
            (r'PHP[/ ](\d+\.\d+)', 'PHP', '8.2'),
            (r'WordPress (\d+\.\d+)', 'WordPress', '6.4'),
        ]
        for pattern, tech, min_version in version_patterns:
            m = re.search(pattern, body, re.IGNORECASE)
            if m:
                found_ver = m.group(1)
                self.add_finding(
                    f'{tech} Version Detected',
                    'INFO',
                    f'{tech} version: {found_ver} (current recommended: {min_version}+)',
                    found_ver,
                    f'Keep {tech} updated to the latest stable version.'
                )

    def _check_admin_panels(self, resp):
        base = self.get_base_url()
        admin_paths = [
            '/admin', '/wp-admin/', '/administrator/', '/manager/',
            '/cpanel/', '/phpmyadmin/', '/adminer/', '/dashboard/',
            '/control/', '/panel/', '/backend/', '/cms/',
        ]
        for path in admin_paths:
            r = self.get(f'{base}{path}', allow_redirects=False)
            if r and r.status_code in (200, 301, 302, 401, 403):
                self.add_finding(
                    f'Admin Panel Found: {path}',
                    'MEDIUM',
                    f'Admin endpoint accessible: {base}{path}',
                    f'Status: {r.status_code}',
                    'Restrict admin panel access by IP or VPN.'
                )
