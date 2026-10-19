"""
CSRF Detection Module
Checks for missing CSRF tokens and SameSite cookie attributes
"""
import re
from .base import BaseModule


class CSRFModule(BaseModule):
    """CSRF (Cross-Site Request Forgery) detection module."""

    def run(self) -> dict:
        forms = self.context.get('forms')
        if forms is None:
            from .crawler import CrawlerModule
            crawler = CrawlerModule(self.config)
            crawl_data = crawler.run()
            forms = crawl_data.get('forms', [])

        for form in forms:
            self._check_form_csrf(form)

        self._check_cookie_samesite()
        self._check_custom_header_protection()
        self._check_origin_validation()

        return self.result({'forms_checked': len(forms)})

    def _check_form_csrf(self, form):
        action = form.get('action', self.url)
        method = form.get('method', 'GET').upper()
        fields = form.get('fields', {})
        html = form.get('html', '')

        if method != 'POST':
            return  # CSRF mainly affects state-changing requests

        # Check for CSRF token fields
        csrf_patterns = [
            r'csrf', r'_token', r'authenticity_token', r'xsrf',
            r'nonce', r'anti.forgery', r'request.token', r'verification.token'
        ]
        has_csrf_token = False
        for field_name in fields:
            for pattern in csrf_patterns:
                if re.search(pattern, field_name, re.IGNORECASE):
                    has_csrf_token = True
                    break
            if has_csrf_token:
                break

        # Also check in hidden inputs
        if not has_csrf_token:
            hidden_inputs = re.findall(r'<input[^>]+type=["\']?hidden["\']?[^>]*>', html, re.IGNORECASE)
            for hidden in hidden_inputs:
                for pattern in csrf_patterns:
                    if re.search(pattern, hidden, re.IGNORECASE):
                        has_csrf_token = True
                        break

        if not has_csrf_token:
            self.add_finding(
                f'Missing CSRF Token in Form',
                'HIGH',
                f'POST form at {action} has no CSRF protection token.',
                f'Fields: {list(fields.keys())}',
                'Add a synchronizer token (CSRF token) to all state-changing forms.'
            )
        else:
            # Token found - check if it's actually validated by sending a tampered request
            self._test_csrf_bypass(action, fields)

    def _test_csrf_bypass(self, action, fields):
        """Try to bypass CSRF by removing/changing the token."""
        csrf_field = None
        csrf_patterns = [r'csrf', r'_token', r'authenticity_token', r'xsrf']
        for field_name in fields:
            for pattern in csrf_patterns:
                if re.search(pattern, field_name, re.IGNORECASE):
                    csrf_field = field_name
                    break
            if csrf_field:
                break

        if not csrf_field:
            return

        # Try with invalid token
        test_data = dict(fields)
        test_data[csrf_field] = 'INVALID_CSRF_TOKEN_12345'
        resp_invalid = self.post(action, data=test_data)

        # Try without token at all
        test_data_no_token = {k: v for k, v in fields.items() if k != csrf_field}
        resp_no_token = self.post(action, data=test_data_no_token)

        for resp, scenario in [(resp_invalid, 'invalid token'), (resp_no_token, 'missing token')]:
            if resp and resp.status_code == 200:
                if not any(kw in resp.text.lower() for kw in 
                          ['invalid', 'forbidden', 'error', 'csrf', 'token']):
                    self.add_finding(
                        f'CSRF Token Not Validated',
                        'HIGH',
                        f'Server accepted POST request with {scenario}.',
                        f'Action: {action}\nScenario: {scenario}',
                        'Validate CSRF token server-side on every state-changing request.'
                    )
                    break

    def _check_cookie_samesite(self):
        resp = self.get(self.url)
        if not resp:
            return
        
        for cookie in resp.cookies:
            samesite = cookie.get_nonstandard_attr('SameSite')
            if not samesite or samesite.lower() == 'none':
                self.add_finding(
                    f'Cookie Without SameSite: {cookie.name}',
                    'MEDIUM',
                    f'Cookie "{cookie.name}" lacks SameSite protection.',
                    f'SameSite: {samesite or "not set"}',
                    'Set SameSite=Strict or SameSite=Lax on session cookies.'
                )

    def _check_custom_header_protection(self):
        """Test if custom header requirement provides CSRF protection."""
        # Some APIs rely on custom headers for CSRF protection
        resp = self.get(self.url)
        if resp:
            if 'X-Requested-With' in resp.headers or 'X-CSRF-Token' in resp.headers:
                self.add_finding(
                    'Custom Header CSRF Protection Detected',
                    'INFO',
                    'Application uses custom header for CSRF protection.',
                    '',
                    'Ensure custom header validation is enforced server-side.'
                )

    def _check_origin_validation(self):
        """Check if server validates Origin/Referer header."""
        # Send request with bad origin
        resp = self.get(self.url, headers={
            'Origin': 'https://evil.com',
            'Referer': 'https://evil.com/attack.html'
        })
        if resp and resp.status_code == 200:
            # Server responded OK to bad origin - might not validate
            self.add_finding(
                'Origin Header Not Validated',
                'MEDIUM',
                'Server does not reject requests from arbitrary origins.',
                'Origin: https://evil.com → HTTP 200',
                'Validate Origin/Referer headers on state-changing endpoints.'
            )
