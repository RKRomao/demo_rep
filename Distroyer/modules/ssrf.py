"""
SSRF (Server-Side Request Forgery) Testing Module
Supports both in-band cloud metadata/loopback detection and
deferred Out-of-Band (OOB) correlation testing via Interactsh/webhook.
"""
import uuid
import urllib.parse
from .base import BaseModule

SSRF_PARAM_CANDIDATES = [
    'url', 'dest', 'redirect', 'uri', 'path', 'domain', 'target',
    'feed', 'host', 'site', 'html', 'data', 'reference', 'val',
    'webhook', 'callback', 'load', 'proxy', 'endpoint'
]

LOCAL_PAYLOADS = [
    ('http://169.254.169.254/latest/meta-data/', 'AWS EC2 Metadata', ['instance-id', 'ami-id', 'security-credentials']),
    ('http://metadata.google.internal/computeMetadata/v1/', 'GCP Metadata', ['Metadata-Flavor']),
    ('http://127.0.0.1:80', 'Local Loopback (Port 80)', []),
    ('http://localhost:22', 'Local SSH (Port 22)', ['SSH-2.0']),
    ('http://[::1]:80', 'IPv6 Loopback', []),
]


class SSRFModule(BaseModule):
    """Detects Server-Side Request Forgery vulnerabilities."""

    def run(self) -> dict:
        endpoints = self.context.get('endpoints', [self.url])
        oob_server = self.config.get('oob_server')

        tested_params = 0
        for ep in [self.url] + endpoints[:25]:
            tested_params += self._test_url(ep, oob_server)

        return self.result({'endpoints_evaluated': len(endpoints), 'candidates_tested': tested_params})

    def _test_url(self, url: str, oob_server: str = None) -> int:
        parsed = urllib.parse.urlparse(url)
        params = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
        if not params:
            return 0

        tested = 0
        for param, values in params.items():
            param_lower = param.lower()
            # Target parameters likely to accept URLs/hosts
            if any(candidate in param_lower for candidate in SSRF_PARAM_CANDIDATES):
                tested += 1
                self._test_local_ssrf(url, parsed, param, params)
                if oob_server:
                    self._test_oob_ssrf(url, parsed, param, params, oob_server)
        return tested

    def _test_local_ssrf(self, url, parsed, param, params):
        for payload, desc, indicators in LOCAL_PAYLOADS:
            test_params = dict(params)
            test_params[param] = [payload]
            test_url = urllib.parse.urlunparse(parsed._replace(query=urllib.parse.urlencode(test_params, doseq=True)))

            resp = self.get(test_url)
            if resp and resp.text:
                if any(ind in resp.text for ind in indicators):
                    self.add_finding(
                        f'SSRF: In-Band Access to {desc}',
                        'CRITICAL',
                        f'Parameter "{param}" allows server-side fetch of internal resource: {desc}',
                        f'Endpoint: {url}\nPayload: {payload}\nMatch in response text',
                        'Validate and restrict URLs using a strict allowlist. Block loopback and link-local addresses (169.254.169.254).'
                    )
                    break

    def _test_oob_ssrf(self, url, parsed, param, params, oob_server: str):
        """Dispatch Out-Of-Band callback request and register correlation token for deferred verification."""
        correlation_id = f"ssrf-{uuid.uuid4().hex[:10]}"
        oob_host = oob_server.replace('http://', '').replace('https://', '').rstrip('/')
        callback_url = f"http://{correlation_id}.{oob_host}"

        test_params = dict(params)
        test_params[param] = [callback_url]
        test_url = urllib.parse.urlunparse(parsed._replace(query=urllib.parse.urlencode(test_params, doseq=True)))

        # Fire and register
        self.get(test_url)

        # Store in shared context for deferred polling at the conclusion of the entire scan
        pending = self.context.setdefault('ssrf_pending_correlations', [])
        pending.append({
            'correlation_id': correlation_id,
            'param': param,
            'url': url,
            'callback_url': callback_url
        })

    @classmethod
    def poll_oob_interactions(cls, config: dict, context: dict, results: dict, all_findings: list):
        """Deferred batch polling executed before final reporting."""
        pending = context.get('ssrf_pending_correlations', [])
        oob_server = config.get('oob_server')
        if not pending or not oob_server:
            return

        # Poll OOB interaction log if endpoint provided (e.g. Interactsh or custom polling API)
        poll_endpoint = config.get('oob_poll_url') or f"{oob_server.rstrip('/')}/interactions"
        try:
            import requests
            resp = requests.get(poll_endpoint, timeout=10)
            if resp and resp.status_code == 200:
                log_text = resp.text
                for item in pending:
                    if item['correlation_id'] in log_text:
                        finding = {
                            'title': f"Blind SSRF (OOB): {item['param']}",
                            'severity': 'CRITICAL',
                            'detail': f"Deferred OOB DNS/HTTP callback confirmed for parameter '{item['param']}'",
                            'evidence': f"Endpoint: {item['url']}\nCallback URL: {item['callback_url']}\nCorrelation ID: {item['correlation_id']}",
                            'recommendation': 'Disable external resource fetching or enforce strict destination IP allowlisting.',
                            'module': 'ssrf'
                        }
                        all_findings.append(finding)
                        ssrf_results = results.setdefault('ssrf', {'findings': []})
                        ssrf_results.setdefault('findings', []).append(finding)
        except Exception:
            pass
