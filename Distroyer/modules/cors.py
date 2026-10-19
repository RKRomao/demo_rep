"""
CORS Misconfiguration Testing Module
Tests for dangerous Cross-Origin Resource Sharing configurations
"""
from .base import BaseModule


TEST_ORIGINS = [
    'https://evil.com',
    'https://attacker.com',
    'null',
    'https://evil.target.com',  # Subdomain of target
    'http://evil.com',          # HTTP version
    'https://notevil.com',
    'https://evilcorp.com',
]


class CORSModule(BaseModule):
    """CORS misconfiguration detection module."""

    def run(self) -> dict:
        domain = self.get_domain()
        
        reflected_origins = []
        acac_enabled = False
        sample_evidence = ""

        for origin in TEST_ORIGINS:
            if 'evil.target.com' in origin:
                origin = f'https://evil.{domain}'
            if origin == 'null':
                continue

            resp = self.get(self.url, headers={
                'Origin': origin,
                'Access-Control-Request-Method': 'GET',
            })
            if not resp:
                continue

            acao = resp.headers.get('Access-Control-Allow-Origin', '')
            acac = resp.headers.get('Access-Control-Allow-Credentials', '')

            if acao == origin:
                reflected_origins.append(origin)
                if acac.lower() == 'true':
                    acac_enabled = True
                sample_evidence = f"ACAO: {acao}\nACAC: {acac}"
            elif acao == '*' and acac.lower() == 'true':
                self.add_finding(
                    'CORS: Wildcard + Credentials',
                    'CRITICAL',
                    'Access-Control-Allow-Origin: * with Allow-Credentials: true is invalid and dangerous.',
                    f'ACAO: {acao}\nACAC: {acac}',
                    'Remove wildcard when using credentials. Use explicit origin allowlist.'
                )

        if reflected_origins:
            sev = 'CRITICAL' if acac_enabled else 'HIGH'
            origins_display = ', '.join(reflected_origins[:4])
            if len(reflected_origins) > 4:
                origins_display += f" and {len(reflected_origins) - 4} more"
            self.add_finding(
                'CORS: Arbitrary Origin Reflected',
                sev,
                f'Server dynamically reflects attacker origin ({origins_display})',
                f"{sample_evidence}\nTested Reflected Origins: {', '.join(reflected_origins)}",
                'Maintain an explicit allowlist of trusted origins. Never reflect the Origin header directly.'
            )

        self._test_null_origin()
        self._test_cors_on_api_endpoints()
        self._check_preflight()

        return self.result()

    def _test_null_origin(self):
        """Null origin is allowed by some servers."""
        resp = self.get(self.url, headers={'Origin': 'null'})
        if not resp:
            return

        acao = resp.headers.get('Access-Control-Allow-Origin', '')
        acac = resp.headers.get('Access-Control-Allow-Credentials', '')

        if acao == 'null':
            severity = 'CRITICAL' if acac.lower() == 'true' else 'HIGH'
            self.add_finding(
                'CORS: Null Origin Allowed',
                severity,
                'Server accepts null origin (can be exploited via sandboxed iframes)',
                f'ACAO: {acao}\nACAC: {acac}',
                'Do not allow null origin. Use explicit origin allowlists.'
            )

    def _test_cors_on_api_endpoints(self):
        """Test CORS on common API endpoints."""
        base = self.get_base_url()
        api_paths = ['/api/', '/api/v1/', '/api/v2/', '/graphql', '/rest/', '/v1/', '/v2/']

        for path in api_paths:
            url = f'{base}{path}'
            resp = self.get(url, headers={'Origin': 'https://evil.com'})
            if resp and resp.status_code != 404:
                acao = resp.headers.get('Access-Control-Allow-Origin', '')
                if acao in ('*', 'https://evil.com'):
                    self.add_finding(
                        f'CORS Misconfiguration on API: {path}',
                        'HIGH',
                        f'API endpoint {path} has permissive CORS.',
                        f'ACAO: {acao}',
                        'Restrict CORS on API endpoints to trusted origins only.'
                    )

    def _check_preflight(self):
        """Test OPTIONS preflight response."""
        try:
            resp = self.session.options(
                self.url,
                headers={
                    'Origin': 'https://evil.com',
                    'Access-Control-Request-Method': 'DELETE',
                    'Access-Control-Request-Headers': 'Authorization,Content-Type',
                },
                timeout=self.timeout
            )
            if resp:
                acam = resp.headers.get('Access-Control-Allow-Methods', '')
                acah = resp.headers.get('Access-Control-Allow-Headers', '')
                acao = resp.headers.get('Access-Control-Allow-Origin', '')

                if 'DELETE' in acam or 'PUT' in acam or 'PATCH' in acam:
                    if acao in ('*', 'https://evil.com'):
                        self.add_finding(
                            'CORS: Dangerous Methods Allowed',
                            'HIGH',
                            f'Preflight allows {acam} from arbitrary origins.',
                            f'ACAO: {acao}\nACAM: {acam}',
                            'Restrict allowed methods to only what is needed.'
                        )
        except Exception:
            pass
