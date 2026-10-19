"""
Secrets & Token Scanner Module
Scans JavaScript and client-side files for exposed API keys, credentials, and secrets.
"""
import re
from .base import BaseModule

SECRET_PATTERNS = [
    {
        'name': 'AWS Access Key ID',
        'regex': r'\b(AKIA[0-9A-Z]{16})\b',
        'severity': 'CRITICAL',
        'desc': 'Exposed AWS IAM access key found in client-side code.',
        'remediation': 'Revoke the AWS access key immediately and utilize IAM roles or secure backend relays.'
    },
    {
        'name': 'Stripe Secret Key',
        'regex': r'\b(sk_live_[0-9a-zA-Z]{24,34})\b',
        'severity': 'CRITICAL',
        'desc': 'Live Stripe Secret API key exposed.',
        'remediation': 'Revoke the key immediately in Stripe Dashboard. Client-side code must only use publishable keys (pk_live_).'
    },
    {
        'name': 'Private Key Block',
        'regex': r'(-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----)',
        'severity': 'CRITICAL',
        'desc': 'Cryptographic private key found exposed in client source.',
        'remediation': 'Remove private key immediately and rotate associated public certificates.'
    },
    {
        'name': 'GitHub Personal Access Token',
        'regex': r'\b(gh[pousr]_[A-Za-z0-9_]{36,255})\b',
        'severity': 'CRITICAL',
        'desc': 'GitHub Personal Access Token discovered.',
        'remediation': 'Revoke the token in GitHub account settings and remove from client-side bundles.'
    },
    {
        'name': 'Slack Incoming Webhook',
        'regex': r'(https://hooks\.slack\.com/services/T[a-zA-Z0-9_]+/B[a-zA-Z0-9_]+/[a-zA-Z0-9_]+)',
        'severity': 'HIGH',
        'desc': 'Exposed Slack incoming webhook URL enables arbitrary channel message spoofing.',
        'remediation': 'Invalidate the webhook in Slack app integrations.'
    },
    {
        'name': 'Google API Key',
        'regex': r'\b(AIza[0-9A-Za-z-_]{35})\b',
        'severity': 'MEDIUM',
        'desc': 'Google Cloud / Maps API Key found.',
        'remediation': 'Restrict Google Cloud API key by HTTP referrer and API service quotas in GCP Console.'
    },
    {
        'name': 'JSON Web Token (JWT)',
        'regex': r'\b(eyJ[A-Za-z0-9-_]{10,}\.eyJ[A-Za-z0-9-_]{10,}\.[A-Za-z0-9-_]{10,})\b',
        'severity': 'HIGH',
        'desc': 'Hardcoded JWT token found in frontend code.',
        'remediation': 'Never hardcode user authentication tokens in static JavaScript bundles.'
    },
    {
        'name': 'Hardcoded Password or Secret',
        'regex': r'''(?i)(?:secret|password|api[_-]?key|auth[_-]?token)\s*[:=]\s*["']([^"'\s]{8,64})["']''',
        'severity': 'HIGH',
        'desc': 'Potential hardcoded credential or API secret variable.',
        'remediation': 'Extract credentials into secure server-side environment variables.'
    }
]


class SecretsModule(BaseModule):
    """Detects leaked credentials and API keys in frontend assets."""

    def run(self) -> dict:
        scripts = self.context.get('scripts', [])
        if not scripts:
            # Check the base page itself for inline scripts
            resp = self.get(self.url)
            if resp and resp.text:
                self._scan_content(resp.text, self.url)
            return self.result({'scripts_scanned': 0})

        scanned = 0
        for script_url in scripts[:20]:
            resp = self.get(script_url)
            if resp and resp.text:
                scanned += 1
                self._scan_content(resp.text, script_url)

        return self.result({'scripts_scanned': scanned})

    def _scan_content(self, text: str, source_url: str):
        for pattern in SECRET_PATTERNS:
            matches = re.findall(pattern['regex'], text)
            if matches:
                # Mask secret for safe reporting
                raw_match = str(matches[0])
                if len(raw_match) > 8:
                    masked = raw_match[:4] + ('*' * (len(raw_match) - 8)) + raw_match[-4:]
                else:
                    masked = '****' + raw_match[-2:]

                self.add_finding(
                    f"Exposed Secret: {pattern['name']}",
                    pattern['severity'],
                    f"{pattern['desc']} Discovered in asset: {source_url}",
                    f"Asset: {source_url}\nMatch: {masked}",
                    pattern['remediation']
                )
