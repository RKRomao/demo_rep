"""
Rate Limiting & Anti-Brute Force Testing Module
Tests whether sensitive authentication and administrative endpoints implement request rate limiting.
"""
from .base import BaseModule

RATE_LIMIT_CANDIDATES = [
    '/login', '/api/login', '/auth', '/api/auth', '/signin',
    '/api/v1/auth', '/password/reset', '/api/v1/login'
]


class RateLimitModule(BaseModule):
    """Verifies that brute-force protections and rate limits exist on sensitive endpoints."""

    def run(self) -> dict:
        base_url = self.get_base_url()
        tested_endpoints = []

        # Gather sensitive endpoints from crawl or fallback list
        candidate_urls = []
        for path in RATE_LIMIT_CANDIDATES:
            candidate_urls.append(f"{base_url}{path}")

        forms = self.context.get('forms', [])
        for f in forms:
            action = f.get('action', '')
            if any(kw in action.lower() for kw in ('login', 'auth', 'signin', 'password')):
                if action not in candidate_urls:
                    candidate_urls.append(action)

        for target in candidate_urls[:3]:
            # First check if endpoint exists
            resp = self.get(target)
            if not resp or resp.status_code == 404:
                continue

            tested_endpoints.append(target)
            self._test_burst_rate_limit(target)

        return self.result({'endpoints_tested': len(tested_endpoints)})

    def _test_burst_rate_limit(self, url: str):
        """Send a short, controlled burst of 15 rapid authentication requests."""
        burst_count = 15
        got_rate_limited = False
        rate_limit_indicators = []

        for i in range(burst_count):
            resp = self.post(url, data={'username': f'testuser_{i}', 'password': 'InvalidPassword123!'})
            if not resp:
                continue

            # Check 429 Too Many Requests
            if resp.status_code == 429:
                got_rate_limited = True
                rate_limit_indicators.append(f"HTTP 429 received on request #{i+1}")
                break

            # Check for Retry-After or RateLimit headers
            if any(h in resp.headers for h in ('Retry-After', 'X-RateLimit-Remaining', 'RateLimit-Remaining')):
                remaining = resp.headers.get('X-RateLimit-Remaining') or resp.headers.get('RateLimit-Remaining')
                if remaining == '0':
                    got_rate_limited = True
                    rate_limit_indicators.append("Rate limit header exhausted")
                    break

            # Check for body indicator
            if any(msg in resp.text.lower() for msg in ('too many requests', 'rate limit exceeded', 'account locked', 'slow down')):
                got_rate_limited = True
                rate_limit_indicators.append("Lockout / rate limit message in body")
                break

        if not got_rate_limited:
            self.add_finding(
                'Missing Rate Limiting on Login Endpoint',
                'MEDIUM',
                f'Endpoint {url} accepted {burst_count} rapid authentication attempts without restriction',
                f'Endpoint: {url}\n{burst_count} requests processed with no 429 or lockout triggered.',
                'Implement IP-based and account-based rate limiting (HTTP 429) and account lockout policies.'
            )
        else:
            self.add_finding(
                'Rate Limiting Active',
                'INFO',
                f'Endpoint {url} successfully enforced rate limits: {", ".join(rate_limit_indicators)}',
                f'Endpoint: {url}\nProtection confirmed.'
            )
