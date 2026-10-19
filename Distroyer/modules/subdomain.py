"""
Subdomain Enumeration Module
DNS brute-force, certificate transparency, and passive enumeration
"""
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed
from .base import BaseModule


BUILTIN_SUBDOMAINS = """
www
mail
smtp
pop
imap
ftp
ssh
ns1
ns2
api
dev
staging
test
uat
qa
demo
admin
portal
app
apps
mobile
m
static
cdn
assets
media
images
img
files
download
uploads
blog
shop
store
payment
secure
login
auth
oauth
sso
vpn
remote
internal
intranet
extranet
git
gitlab
github
jira
jenkins
ci
cd
monitor
status
help
support
docs
wiki
dashboard
panel
console
backend
frontend
microservices
kafka
redis
elastic
mongo
db
database
mysql
postgres
""".strip().split('\n')


class SubdomainModule(BaseModule):
    """Subdomain enumeration via DNS brute-force and certificate transparency."""

    def run(self) -> dict:
        domain = self.get_domain()
        # Strip www if present
        if domain.startswith('www.'):
            domain = domain[4:]

        found = []
        
        # 1. Certificate Transparency logs
        ct_subs = self._crt_sh(domain)
        found.extend(ct_subs)

        # 2. DNS brute-force
        bf_subs = self._bruteforce(domain)
        found.extend(bf_subs)

        # Deduplicate and resolve
        unique = list(set(found))
        resolved = self._resolve_all(unique)

        if resolved:
            self.add_finding(
                'Subdomains Discovered',
                'INFO',
                f'Found {len(resolved)} active subdomains',
                '\n'.join(f'{sub} → {ip}' for sub, ip in resolved[:20]),
                'Review all subdomains for forgotten/vulnerable services.'
            )

            # Flag potentially dangerous subdomains
            risky_keywords = ['dev', 'staging', 'test', 'qa', 'admin', 'internal', 
                             'beta', 'old', 'backup', 'debug', 'jenkins', 'gitlab']
            risky = [(sub, ip) for sub, ip in resolved 
                    if any(kw in sub.lower() for kw in risky_keywords)]
            
            if risky:
                self.add_finding(
                    'Potentially Risky Subdomains',
                    'MEDIUM',
                    f'{len(risky)} development/internal subdomains exposed',
                    '\n'.join(f'{sub} → {ip}' for sub, ip in risky[:10]),
                    'Development/staging environments often have weaker security. Review access controls.'
                )

        return self.result({'found': [s for s, _ in resolved], 'total': len(resolved)})

    def _crt_sh(self, domain):
        """Query crt.sh certificate transparency logs."""
        subdomains = []
        try:
            resp = self.get(f'https://crt.sh/?q=%.{domain}&output=json')
            if resp and resp.status_code == 200:
                entries = resp.json()
                for entry in entries:
                    name = entry.get('name_value', '')
                    for sub in name.split('\n'):
                        sub = sub.strip().lower().lstrip('*.')
                        if sub.endswith(f'.{domain}') and sub not in subdomains:
                            subdomains.append(sub)
        except Exception:
            pass
        return subdomains[:50]

    def _bruteforce(self, domain):
        wordlist = self._load_wordlist()
        candidates = [f'{sub}.{domain}' for sub in wordlist if sub]
        return candidates

    def _resolve_all(self, subdomains):
        resolved = []
        threads = min(self.config.get('threads', 10), 30)

        def resolve_one(sub):
            try:
                ip = socket.gethostbyname(sub)
                return (sub, ip)
            except Exception:
                return None

        with ThreadPoolExecutor(max_workers=threads) as executor:
            futures = {executor.submit(resolve_one, sub): sub for sub in subdomains}
            for future in as_completed(futures):
                result = future.result()
                if result:
                    resolved.append(result)

        return resolved

    def _load_wordlist(self):
        import os
        custom = self.config.get('wordlist_subs')
        if custom and os.path.isfile(custom):
            with open(custom, 'r', errors='ignore') as f:
                return [line.strip() for line in f if line.strip() and not line.startswith('#')]
        
        wl_path = os.path.join(os.path.dirname(__file__), '..', 'wordlists', 'subdomains.txt')
        if os.path.isfile(wl_path):
            with open(wl_path, 'r', errors='ignore') as f:
                return [line.strip() for line in f if line.strip() and not line.startswith('#')]
        
        return BUILTIN_SUBDOMAINS
