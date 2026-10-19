"""
HTTP Security Headers Analysis Module
Checks for missing/misconfigured security headers
"""
from .base import BaseModule


SECURITY_HEADERS = {
    'Strict-Transport-Security': {
        'severity': 'HIGH',
        'recommendation': 'Add: Strict-Transport-Security: max-age=31536000; includeSubDomains; preload',
        'check': lambda v: 'max-age' in v.lower()
    },
    'Content-Security-Policy': {
        'severity': 'HIGH',
        'recommendation': 'Implement a strict CSP policy to prevent XSS.',
        'check': lambda v: len(v) > 10
    },
    'X-Content-Type-Options': {
        'severity': 'MEDIUM',
        'recommendation': 'Add: X-Content-Type-Options: nosniff',
        'check': lambda v: v.lower() == 'nosniff'
    },
    'X-Frame-Options': {
        'severity': 'MEDIUM',
        'recommendation': 'Add: X-Frame-Options: DENY or SAMEORIGIN',
        'check': lambda v: v.upper() in ('DENY', 'SAMEORIGIN')
    },
    'Referrer-Policy': {
        'severity': 'LOW',
        'recommendation': 'Add: Referrer-Policy: strict-origin-when-cross-origin',
        'check': lambda v: len(v) > 3
    },
    'Permissions-Policy': {
        'severity': 'LOW',
        'recommendation': 'Add Permissions-Policy to restrict browser APIs.',
        'check': lambda v: len(v) > 3
    },
    'X-XSS-Protection': {
        'severity': 'LOW',
        'recommendation': 'Consider using CSP instead; X-XSS-Protection is deprecated.',
        'check': lambda v: True  # Informational
    },
    'Cache-Control': {
        'severity': 'LOW',
        'recommendation': 'Ensure sensitive pages have Cache-Control: no-store',
        'check': lambda v: True
    },
}

DANGEROUS_HEADERS = {
    'Server': 'Server header reveals version information.',
    'X-Powered-By': 'Technology fingerprint - remove this header.',
    'X-AspNet-Version': 'ASP.NET version exposed.',
    'X-AspNetMvc-Version': 'ASP.NET MVC version exposed.',
    'X-Generator': 'Generator information exposed.',
}

CSP_WEAK_DIRECTIVES = [
    ("'unsafe-inline'", 'CSP allows unsafe-inline - negates XSS protection', 'HIGH'),
    ("'unsafe-eval'", 'CSP allows unsafe-eval - enables eval() attacks', 'HIGH'),
    ('*', 'Wildcard source in CSP allows any origin', 'MEDIUM'),
    ('data:', 'CSP allows data: URIs which can be abused', 'MEDIUM'),
    ('http:', 'CSP allows plain HTTP sources', 'MEDIUM'),
]


class HeadersModule(BaseModule):
    """HTTP Security Headers analysis module."""

    def run(self) -> dict:
        resp = self.get(self.url)
        if not resp:
            return self.result({'error': 'Could not fetch URL'})

        headers = resp.headers
        self._check_missing_headers(headers)
        self._check_dangerous_headers(headers)
        self._check_csp(headers)
        self._check_hsts(headers)
        self._check_cookies(resp)
        self._check_cors_headers(headers)
        self._check_information_disclosure(resp)
        self._check_clickjacking(headers)

        return self.result({'status_code': resp.status_code, 'headers': dict(headers)})

    def _check_missing_headers(self, headers):
        for header, meta in SECURITY_HEADERS.items():
            val = headers.get(header, '')
            if not val:
                self.add_finding(
                    f'Missing Security Header: {header}',
                    meta['severity'],
                    f'The {header} header is not set.',
                    '',
                    meta['recommendation']
                )
            else:
                if not meta['check'](val):
                    self.add_finding(
                        f'Weak Security Header: {header}',
                        meta['severity'],
                        f'Header present but may be misconfigured: {val[:80]}',
                        val,
                        meta['recommendation']
                    )

    def _check_dangerous_headers(self, headers):
        for header, desc in DANGEROUS_HEADERS.items():
            val = headers.get(header, '')
            if val:
                self.add_finding(
                    f'Information Disclosure: {header}',
                    'LOW',
                    desc,
                    f'{header}: {val}',
                    f'Remove or obfuscate the {header} header.'
                )

    def _check_csp(self, headers):
        csp = headers.get('Content-Security-Policy', '')
        if not csp:
            return
        for directive, desc, severity in CSP_WEAK_DIRECTIVES:
            if directive in csp:
                self.add_finding(
                    f'Weak CSP Directive: {directive}',
                    severity,
                    desc,
                    csp[:200],
                    f'Remove or restrict {directive} from Content-Security-Policy.'
                )

    def _check_hsts(self, headers):
        hsts = headers.get('Strict-Transport-Security', '')
        if hsts:
            if 'preload' not in hsts:
                self.add_finding(
                    'HSTS Missing Preload',
                    'LOW',
                    'HSTS header does not include preload directive.',
                    hsts,
                    'Add "preload" to HSTS header and submit to HSTS preload list.'
                )
            if 'includeSubDomains' not in hsts:
                self.add_finding(
                    'HSTS Missing includeSubDomains',
                    'LOW',
                    'HSTS does not cover subdomains.',
                    hsts,
                    'Add "includeSubDomains" to HSTS header.'
                )
            try:
                max_age = int([p for p in hsts.split(';') if 'max-age' in p][0].split('=')[1].strip())
                if max_age < 31536000:
                    self.add_finding(
                        'HSTS max-age Too Short',
                        'LOW',
                        f'max-age={max_age} is less than 1 year (31536000)',
                        hsts,
                        'Set max-age to at least 31536000 (1 year).'
                    )
            except Exception:
                pass

    def _check_cookies(self, resp):
        for cookie in resp.cookies:
            issues = []
            if not cookie.secure:
                issues.append('Missing Secure flag')
            if not cookie.has_nonstandard_attr('HttpOnly'):
                issues.append('Missing HttpOnly flag')
            samesite = cookie.get_nonstandard_attr('SameSite')
            if not samesite:
                issues.append('Missing SameSite attribute')
            elif samesite.lower() == 'none' and not cookie.secure:
                issues.append('SameSite=None requires Secure flag')

            if issues:
                severity = 'HIGH' if 'Secure' in ' '.join(issues) or 'HttpOnly' in ' '.join(issues) else 'MEDIUM'
                self.add_finding(
                    f'Insecure Cookie: {cookie.name}',
                    severity,
                    '; '.join(issues),
                    f'Cookie: {cookie.name}',
                    'Set Secure, HttpOnly, and SameSite=Strict on all cookies.'
                )

    def _check_cors_headers(self, headers):
        acao = headers.get('Access-Control-Allow-Origin', '')
        acac = headers.get('Access-Control-Allow-Credentials', '')
        if acao == '*' and acac.lower() == 'true':
            self.add_finding(
                'Dangerous CORS Configuration',
                'CRITICAL',
                'Access-Control-Allow-Origin: * with Allow-Credentials: true',
                f'ACAO: {acao}, ACAC: {acac}',
                'Never combine wildcard ACAO with Allow-Credentials: true.'
            )

    def _check_information_disclosure(self, resp):
        # Check for stack traces / error messages in response
        body = resp.text[:5000] if resp.text else ''
        keywords = ['stack trace', 'traceback', 'exception', 'SQL syntax',
                    'mysql_fetch', 'ORA-', 'Microsoft OLE DB', 'ODBC SQL Server',
                    'syntax error', 'Fatal error:', 'Warning:', 'Notice:']
        for kw in keywords:
            if kw.lower() in body.lower():
                self.add_finding(
                    'Information Disclosure in Response',
                    'HIGH',
                    f'Error/stack trace keyword detected: "{kw}"',
                    body[:300],
                    'Disable verbose error reporting in production.'
                )
                break

    def _check_clickjacking(self, headers):
        xfo = headers.get('X-Frame-Options', '')
        csp = headers.get('Content-Security-Policy', '')
        has_frame_ancestors = 'frame-ancestors' in csp

        if not xfo and not has_frame_ancestors:
            self.add_finding(
                'Clickjacking Protection Missing',
                'MEDIUM',
                'No X-Frame-Options or CSP frame-ancestors directive.',
                '',
                'Add X-Frame-Options: DENY or CSP: frame-ancestors \'none\''
            )
