"""
Directory & File Enumeration Module
Brute-forces hidden directories and sensitive files
"""
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from .base import BaseModule


# Built-in wordlist (also loads external if provided)
BUILTIN_DIRS = """
.env
.env.local
.env.production
.git
.git/HEAD
.git/config
.htaccess
.htpasswd
.DS_Store
.svn
.npmrc
.yarnrc
.dockerignore
Dockerfile
docker-compose.yml
docker-compose.yaml
Makefile
package.json
package-lock.json
composer.json
composer.lock
requirements.txt
Pipfile
Gemfile
admin
admin/
administrator/
admin/login
api
api/v1
api/v2
backup
backup.zip
backup.sql
backup.tar.gz
config
config.php
config.yml
config.json
config.xml
configuration.php
wp-config.php
wp-config.php.bak
web.config
appsettings.json
application.properties
database.yml
secrets.yml
console
control
cpanel
dashboard
debug
dev
developer
development
dump.sql
error_log
files
hidden
include
includes
index.php.bak
info.php
phpinfo.php
install
install.php
log
logs
login
management
manager
old
panel
private
secret
secrets
server-status
server-info
setup
staging
static
swagger.json
swagger.yaml
openapi.json
openapi.yaml
test
tests
tmp
uploads
users
vendor
""".strip().split('\n')

SENSITIVE_EXTENSIONS = ['.bak', '.backup', '.old', '.orig', '.tmp', '.log', '.sql', '.env', '.cfg']


class DirEnumModule(BaseModule):
    """Directory and file brute-force enumeration."""

    def run(self) -> dict:
        wordlist = self._load_wordlist()
        base = self.get_base_url()
        threads = min(self.config.get('threads', 10), 20)

        found = []
        with ThreadPoolExecutor(max_workers=threads) as executor:
            futures = {
                executor.submit(self._probe, f'{base}/{path.strip("/")}', path): path
                for path in wordlist if path
            }
            for future in as_completed(futures):
                result = future.result()
                if result:
                    found.append(result)

        self.add_finding(
            'Directory Enumeration Complete',
            'INFO',
            f'Scanned {len(wordlist)} paths, found {len(found)} accessible',
            '\n'.join(f'{r["path"]} ({r["status"]})' for r in found[:20])
        )

        return self.result({'found': found, 'scanned': len(wordlist)})

    def _probe(self, url, path):
        try:
            from .extractor import FileExtractor
            resp = self.get(url, allow_redirects=False)
            if resp is None:
                return None
            
            if resp.status_code in (200, 201, 301, 302, 307, 308, 403, 401):
                size = len(resp.content)
                loc = resp.headers.get('Location', '')
                severity = 'INFO'
                title = f'Path Found: {path}'
                loot = None
                
                # Check for sensitive paths
                sensitive_keywords = [
                    'config', 'env', 'secret', 'password', 'backup', 'dump',
                    'sql', '.git', '.htpasswd', 'admin', 'phpinfo', 'debug',
                    'swagger', 'openapi', 'actuator', 'console',
                ]
                
                is_sensitive = (
                    any(kw in path.lower() for kw in sensitive_keywords) or
                    any(path.endswith(ext) for ext in SENSITIVE_EXTENSIONS)
                )

                if resp.status_code == 200:
                    if is_sensitive and FileExtractor.validate_file_content(path, resp.content):
                        severity = 'HIGH'
                        title = f'Sensitive File Exposed: {path}'
                        if any(path.endswith(ext) for ext in SENSITIVE_EXTENSIONS):
                            if '.sql' in path or '.env' in path:
                                severity = 'CRITICAL'
                        loot = self.extract_file(url, content=resp.content)
                elif resp.status_code in (301, 302, 307, 308):
                    # Check if redirect leads to an authentic file (e.g. S3 / CDN)
                    if is_sensitive:
                        resp_follow = self.get(url, allow_redirects=True)
                        if resp_follow and resp_follow.status_code == 200:
                            if FileExtractor.validate_file_content(path, resp_follow.content, final_url=getattr(resp_follow, 'url', None)):
                                severity = 'HIGH'
                                title = f'Sensitive File Exposed: {path}'
                                if any(path.endswith(ext) for ext in SENSITIVE_EXTENSIONS):
                                    if '.sql' in path or '.env' in path:
                                        severity = 'CRITICAL'
                                loot = self.extract_file(url, content=resp_follow.content)
                elif resp.status_code == 403:
                    if is_sensitive:
                        severity = 'MEDIUM'
                        title = f'Sensitive Path Forbidden: {path}'

                evidence = f'HTTP {resp.status_code} - Size: {size} bytes'
                if loc:
                    evidence += f' -> {loc}'

                self.add_finding(
                    title,
                    severity,
                    f'{title} ({resp.status_code})',
                    evidence,
                    'Remove or restrict access to sensitive files and directories.',
                    loot=loot
                )
                
                return {'path': path, 'url': url, 'status': resp.status_code, 'size': size}
        except Exception:
            pass
        return None

    def _load_wordlist(self):
        custom = self.config.get('wordlist_dirs')
        if custom and os.path.isfile(custom):
            with open(custom, 'r', errors='ignore') as f:
                return [line.strip() for line in f if line.strip() and not line.startswith('#')]
        
        # Try built-in wordlist file
        wl_path = os.path.join(os.path.dirname(__file__), '..', 'wordlists', 'dirs.txt')
        if os.path.isfile(wl_path):
            with open(wl_path, 'r', errors='ignore') as f:
                return [line.strip() for line in f if line.strip() and not line.startswith('#')]
        
        return BUILTIN_DIRS
