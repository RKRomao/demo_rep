"""
Open Redirect Testing Module
Tests for unvalidated redirect vulnerabilities
"""
import re
from .base import BaseModule


REDIRECT_PAYLOADS = [
    '//evil.com',
    'https://evil.com',
    'http://evil.com',
    '//evil.com/%2F..',
    '/\\evil.com',
    '/%09/evil.com',
    '///evil.com',
    '////evil.com',
    'https:evil.com',
    'https:%0a%0devil.com',
    '//google.com',  # Use benign domain for testing
    '/%2F%2Fevil.com',
    '/%5C%5Cevil.com',
    'http://0x7f000001',  # 127.0.0.1 hex
    'http://2130706433',  # 127.0.0.1 decimal
    'javascript://evil.com',
    'data:text/html,<script>alert(1)</script>',
    '\x0ahttps://evil.com',
    'https://evil.com#@legitimate.com',
    'https://legitimate.com@evil.com',
]

REDIRECT_PARAMS = [
    'redirect', 'redirect_to', 'redirect_url', 'url', 'next',
    'return', 'return_to', 'returnUrl', 'returnURL', 'goto',
    'destination', 'dest', 'target', 'redir', 'r', 'u',
    'link', 'forward', 'out', 'continue', 'view', 'callback',
    'continue_url', 'success_url', 'cancel_url',
]


class OpenRedirectModule(BaseModule):
    """Open Redirect vulnerability testing module."""

    def run(self) -> dict:
        endpoints = self.context.get('endpoints')
        if endpoints is None:
            from .crawler import CrawlerModule
            crawler = CrawlerModule(self.config)
            crawl_data = crawler.run()
            endpoints = crawl_data.get('endpoints', [self.url])

        for ep in [self.url] + endpoints[:20]:
            self._test_endpoint(ep)

        return self.result({'endpoints_tested': len(endpoints)})

    def _test_endpoint(self, url):
        from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
        parsed = urlparse(url)
        params = parse_qs(parsed.query, keep_blank_values=True)

        # Test known redirect params
        for param in list(params.keys()) + REDIRECT_PARAMS:
            if param not in params:
                continue
            
            for payload in REDIRECT_PAYLOADS:
                test_params = dict(params)
                test_params[param] = [payload]
                test_query = urlencode(test_params, doseq=True)
                test_url = urlunparse(parsed._replace(query=test_query))

                resp = self.get(test_url, allow_redirects=False)
                if resp:
                    if resp.status_code in (301, 302, 303, 307, 308):
                        location = resp.headers.get('Location', '')
                        if self._is_redirecting_to_payload(location, payload):
                            self.add_finding(
                                f'Open Redirect: {param}',
                                'HIGH',
                                f'Unvalidated redirect via parameter "{param}"',
                                f'Payload: {payload}\nRedirects to: {location}',
                                'Validate redirect URLs against a whitelist. Never redirect to arbitrary user-supplied URLs.'
                            )
                            break

        # Also test without existing params (inject redirect params)
        self._inject_redirect_params(parsed)

    def _inject_redirect_params(self, parsed):
        from urllib.parse import urlencode, urlunparse
        for param in REDIRECT_PARAMS[:5]:
            for payload in REDIRECT_PAYLOADS[:3]:
                test_query = urlencode({param: payload})
                test_url = urlunparse(parsed._replace(query=test_query))

                resp = self.get(test_url, allow_redirects=False)
                if resp and resp.status_code in (301, 302, 303, 307, 308):
                    location = resp.headers.get('Location', '')
                    if self._is_redirecting_to_payload(location, payload):
                        self.add_finding(
                            f'Open Redirect via Injected Param: {param}',
                            'HIGH',
                            f'Server accepted injected redirect param "{param}"',
                            f'Redirects to: {location}',
                            'Validate all redirect destinations against a whitelist.'
                        )

    def _is_redirecting_to_payload(self, location, payload):
        """Check if the redirect location is going to the attacker domain."""
        evil_indicators = ['evil.com', 'google.com']
        for ind in evil_indicators:
            if ind in location:
                return True
        # Also check for exact match
        if location and (location.startswith('//') and 'localhost' not in location and 
                        'localhost' not in location):
            return True
        return False
