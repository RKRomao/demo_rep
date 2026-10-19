"""
SSL/TLS Analysis Module
Checks certificate validity, cipher suites, protocols, vulnerabilities
"""
import ssl
import socket
import datetime
import json
from .base import BaseModule


class SSLModule(BaseModule):
    """SSL/TLS security analysis module."""

    def run(self) -> dict:
        parsed = self.get_parsed_url()
        if parsed.scheme != 'https':
            self.add_finding('No HTTPS', 'HIGH', 
                           'Target is not using HTTPS.', '',
                           'Enable HTTPS with a valid TLS certificate.')
            return self.result()

        host = self.get_domain()
        port = parsed.port or 443

        self._check_certificate(host, port)
        self._check_protocols(host, port)
        self._check_http_to_https_redirect()
        self._check_hsts_preload()

        return self.result({'host': host, 'port': port})

    def _parse_der_cert(self, der_bytes):
        """Parse DER encoded x509 certificate into a dict compatible with getpeercert()."""
        try:
            from cryptography import x509
            from cryptography.x509.oid import ExtensionOID
            cert = x509.load_der_x509_certificate(der_bytes)
            not_after = cert.not_valid_after_utc if hasattr(cert, 'not_valid_after_utc') else cert.not_valid_after
            expire_str = not_after.strftime('%b %d %H:%M:%S %Y GMT')

            sans = []
            try:
                san_ext = cert.extensions.get_extension_for_oid(ExtensionOID.SUBJECT_ALTERNATIVE_NAME)
                for name in san_ext.value:
                    sans.append(('DNS', getattr(name, 'value', str(name))))
            except Exception:
                pass

            return {
                'notAfter': expire_str,
                'subjectAltName': sans,
            }
        except Exception:
            return None

    def _get_cert(self, host, port):
        cipher = None
        version = None
        cert_error = None

        # 1. Try standard verified connection first
        try:
            ctx = ssl.create_default_context()
            with socket.create_connection((host, port), timeout=self.timeout) as sock:
                with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                    cert = ssock.getpeercert()
                    cipher = ssock.cipher()
                    version = ssock.version()
                    if cert:
                        return cert, cipher, version, None
        except ssl.SSLCertVerificationError as e:
            cert_error = str(e.verify_message if hasattr(e, 'verify_message') else e)
        except Exception as e:
            cert_error = str(e)

        # 2. Fallback to unverified connection (CERT_NONE)
        # Note: In Python, getpeercert() returns {} under CERT_NONE unless binary_form=True is used
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            with socket.create_connection((host, port), timeout=self.timeout) as sock:
                with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                    if not cipher:
                        cipher = ssock.cipher()
                    if not version:
                        version = ssock.version()

                    der = ssock.getpeercert(binary_form=True)
                    if der:
                        parsed = self._parse_der_cert(der)
                        if parsed:
                            return parsed, cipher, version, cert_error
        except Exception:
            pass

        return None, cipher, version, cert_error

    def _check_certificate(self, host, port):
        cert, cipher, version, cert_error = self._get_cert(host, port)
        if not cert:
            self.add_finding('Cannot Retrieve Certificate', 'HIGH',
                           'Unable to obtain SSL certificate details.', '')
            return

        if cert_error:
            self.add_finding('Certificate Verification Failed', 'HIGH',
                           f'Certificate validation failed: {cert_error}',
                           cert_error,
                           'Install a valid TLS certificate issued by a recognized Certificate Authority.')

        # Check expiry
        expire_str = cert.get('notAfter', '')
        if expire_str:
            try:
                expire_dt = datetime.datetime.strptime(expire_str, '%b %d %H:%M:%S %Y %Z')
                now = datetime.datetime.utcnow()
                days_left = (expire_dt - now).days

                if days_left < 0:
                    self.add_finding('Certificate EXPIRED', 'CRITICAL',
                                   f'Certificate expired {abs(days_left)} days ago', expire_str,
                                   'Renew the TLS certificate immediately.')
                elif days_left < 14:
                    self.add_finding('Certificate Expiring Soon', 'HIGH',
                                   f'Certificate expires in {days_left} days', expire_str,
                                   'Renew the TLS certificate before expiry.')
                elif days_left < 30:
                    self.add_finding('Certificate Expiring in <30 Days', 'MEDIUM',
                                   f'{days_left} days until expiry', expire_str)
                else:
                    self.add_finding('Certificate Valid', 'INFO',
                                   f'Certificate valid for {days_left} more days', expire_str)
            except Exception:
                pass

        # Check SANs
        sans = cert.get('subjectAltName', [])
        if not sans:
            self.add_finding('No SAN in Certificate', 'MEDIUM',
                           'Certificate has no Subject Alternative Names.',
                           '',
                           'Include SANs in the certificate for modern browser compatibility.')

        # Check wildcard cert
        san_values = [s[1] for s in sans]
        wildcards = [s for s in san_values if s.startswith('*')]
        if wildcards:
            self.add_finding('Wildcard Certificate', 'LOW',
                           'Certificate uses wildcard DNS names.',
                           ', '.join(wildcards),
                           'Consider per-subdomain certificates for sensitive services.')

        # Cipher info
        if cipher:
            cipher_name, proto, bits = cipher
            self.add_finding('TLS Cipher Info', 'INFO',
                           f'Negotiated: {cipher_name} ({bits} bits) via {proto}',
                           f'Protocol: {version}')

            if bits and bits < 128:
                self.add_finding('Weak Cipher Strength', 'HIGH',
                               f'Cipher uses only {bits} bits',
                               cipher_name,
                               'Use only ciphers with ≥128-bit effective security.')

    def _check_protocols(self, host, port):
        protocols_to_test = [
            (ssl.PROTOCOL_TLS, 'TLSv1', 'TLS 1.0'),
            (ssl.PROTOCOL_TLS, 'TLSv1.1', 'TLS 1.1'),
        ]

        weak_found = []
        for proto_const, proto_str, name in protocols_to_test:
            try:
                ctx = ssl.SSLContext(ssl.PROTOCOL_TLS)
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                # Try to force older protocol
                with socket.create_connection((host, port), timeout=5) as sock:
                    try:
                        with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                            ver = ssock.version()
                            if ver in ('TLSv1', 'TLSv1.1'):
                                weak_found.append(ver)
                    except ssl.SSLError:
                        pass
            except Exception:
                pass

        if weak_found:
            self.add_finding(
                'Weak TLS Protocols Enabled',
                'HIGH',
                f'Server supports deprecated protocols: {", ".join(weak_found)}',
                '',
                'Disable TLS 1.0 and TLS 1.1. Only allow TLS 1.2+ (prefer TLS 1.3).'
            )
        else:
            self.add_finding('Modern TLS Only', 'INFO',
                           'Server does not appear to support TLS 1.0/1.1.')

        # Check TLS 1.3
        try:
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            ctx.minimum_version = ssl.TLSVersion.TLSv1_3
            with socket.create_connection((host, port), timeout=5) as sock:
                with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                    if ssock.version() == 'TLSv1.3':
                        self.add_finding('TLS 1.3 Supported', 'INFO',
                                       'Server supports TLS 1.3 (recommended).')
        except Exception:
            self.add_finding('TLS 1.3 Not Supported', 'LOW',
                           'Server does not support TLS 1.3.',
                           '',
                           'Enable TLS 1.3 for improved security and performance.')

    def _check_http_to_https_redirect(self):
        parsed = self.get_parsed_url()
        http_url = f'http://{parsed.netloc}{parsed.path}'
        try:
            import requests
            resp = requests.get(http_url, allow_redirects=False, timeout=self.timeout, verify=False)
            if resp.status_code in (301, 302, 307, 308):
                loc = resp.headers.get('Location', '')
                if loc.startswith('https://'):
                    self.add_finding('HTTP->HTTPS Redirect', 'INFO',
                                   'HTTP properly redirects to HTTPS.', loc)
                else:
                    self.add_finding('HTTP Redirect Not to HTTPS', 'HIGH',
                                   f'HTTP redirects to non-HTTPS: {loc}', loc,
                                   'Ensure HTTP always redirects to HTTPS.')
            else:
                self.add_finding('No HTTP->HTTPS Redirect', 'HIGH',
                               f'HTTP returns {resp.status_code}, not a redirect to HTTPS.',
                               '',
                               'Configure server to redirect all HTTP traffic to HTTPS.')
        except Exception:
            pass

    def _check_hsts_preload(self):
        """Check HSTS preload list via API."""
        domain = self.get_domain()
        try:
            resp = self.get(f'https://hstspreload.org/api/v2/status?domain={domain}')
            if resp and resp.status_code == 200:
                data = resp.json()
                status = data.get('status', '')
                if status == 'preloaded':
                    self.add_finding('HSTS Preloaded', 'INFO', 
                                   'Domain is on the HSTS preload list.')
                else:
                    self.add_finding('Not on HSTS Preload List', 'LOW',
                                   f'HSTS preload status: {status}',
                                   '',
                                   'Submit domain to https://hstspreload.org/')
        except Exception:
            pass
