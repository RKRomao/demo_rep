"""
Authentication Testing Module
Tests for default credentials, weak auth, JWT issues, and auth bypass
"""
import re
import base64
import json
from .base import BaseModule


DEFAULT_CREDENTIALS = [
    ('admin', 'admin'), ('admin', 'password'), ('admin', '123456'),
    ('admin', 'admin123'), ('admin', ''), ('root', 'root'),
    ('root', 'toor'), ('root', 'password'), ('user', 'user'),
    ('user', 'password'), ('test', 'test'), ('guest', 'guest'),
    ('administrator', 'administrator'), ('administrator', 'password'),
    ('admin', 'letmein'), ('admin', 'qwerty'), ('admin', 'admin1234'),
    ('pi', 'raspberry'),  # Raspberry Pi default
    ('ubnt', 'ubnt'),    # Ubiquiti
]

LOGIN_FORMS_PATHS = [
    '/login', '/signin', '/auth', '/wp-login.php', '/admin/login',
    '/user/login', '/account/login', '/api/auth', '/api/login',
    '/api/v1/auth', '/api/v1/login',
]

JWT_WEAK_SECRETS = [
    'secret', 'password', 'changeme', '123456', 'jwt_secret',
    'mysecret', 'supersecret', 'your-256-bit-secret', '',
]


class AuthModule(BaseModule):
    """Authentication testing module."""

    def run(self) -> dict:
        self._find_login_forms()
        self._test_http_auth()
        self._check_jwt_tokens()
        self._test_auth_bypass()
        self._check_password_policy()
        self._test_account_enumeration()

        return self.result()

    def _find_login_forms(self):
        base = self.get_base_url()
        login_pages = []

        for path in LOGIN_FORMS_PATHS:
            resp = self.get(f'{base}{path}')
            if resp and resp.status_code == 200:
                if any(kw in resp.text.lower() for kw in ['password', 'login', 'signin']):
                    login_pages.append(f'{base}{path}')

        if login_pages:
            self.add_finding(
                'Login Pages Discovered',
                'INFO',
                f'{len(login_pages)} login endpoint(s) found',
                '\n'.join(login_pages),
                'Ensure login pages use HTTPS, have rate limiting, and lockout after failed attempts.'
            )
            
            # Test default credentials on discovered login pages
            for login_url in login_pages[:2]:
                self._test_default_creds(login_url)

    def _test_default_creds(self, login_url):
        resp = self.get(login_url)
        if not resp:
            return

        from bs4 import BeautifulSoup
        from urllib.parse import urljoin
        soup = BeautifulSoup(resp.text, 'html.parser')
        form = soup.find('form')
        if not form:
            return

        action = form.get('action', login_url)
        if not action.startswith('http'):
            action = urljoin(login_url, action)
        method = form.get('method', 'POST').upper()

        # Identify username/password fields
        inputs = form.find_all('input')
        user_field = None
        pass_field = None
        other_fields = {}

        for inp in inputs:
            name = inp.get('name', '')
            itype = inp.get('type', 'text').lower()
            if not name:
                continue
            if itype == 'password':
                pass_field = name
            elif itype in ('text', 'email') or any(kw in name.lower() for kw in ['user', 'email', 'login', 'name']):
                user_field = name
            elif itype not in ('submit', 'button', 'reset'):
                other_fields[name] = inp.get('value', '')

        if not user_field or not pass_field:
            return

        failed_len = None
        for username, password in DEFAULT_CREDENTIALS[:10]:
            data = {**other_fields, user_field: username, pass_field: password}
            r = self.post(action, data=data)
            if not r:
                continue

            # Detect successful login
            failed_keywords = ['invalid', 'incorrect', 'wrong', 'failed', 'error', 'denied']
            success_keywords = ['dashboard', 'logout', 'welcome', 'profile', 'account']

            text_lower = r.text.lower()
            is_success = (
                any(kw in text_lower for kw in success_keywords) or
                (r.url and '/login' not in r.url and r.status_code == 200) or
                r.status_code in (302, 303) and '/login' not in r.headers.get('Location', '/login')
            )
            is_fail = any(kw in text_lower for kw in failed_keywords)

            if failed_len is None:
                failed_len = len(r.content)

            if is_success and not is_fail:
                self.add_finding(
                    f'Default Credentials Work: {username}:{password}',
                    'CRITICAL',
                    f'Login succeeded with default credentials {username}:{password}',
                    f'URL: {action}\nStatus: {r.status_code}',
                    'Change default credentials immediately. Implement strong password requirements.'
                )
                break

    def _test_http_auth(self):
        resp = self.get(self.url, allow_redirects=False)
        if resp and resp.status_code == 401:
            www_auth = resp.headers.get('WWW-Authenticate', '')
            if 'Basic' in www_auth:
                self.add_finding(
                    'HTTP Basic Authentication',
                    'MEDIUM',
                    'Server uses HTTP Basic Authentication (credentials sent in plaintext).',
                    www_auth,
                    'Use modern token-based auth or at minimum ensure HTTPS is enforced.'
                )
                # Try default creds for basic auth
                for user, pwd in DEFAULT_CREDENTIALS[:5]:
                    creds = base64.b64encode(f'{user}:{pwd}'.encode()).decode()
                    r = self.get(self.url, headers={'Authorization': f'Basic {creds}'})
                    if r and r.status_code == 200:
                        self.add_finding(
                            f'HTTP Basic Auth - Default Creds: {user}:{pwd}',
                            'CRITICAL',
                            f'HTTP Basic Auth accepts default credentials: {user}:{pwd}',
                            '',
                            'Change default credentials and implement account lockout.'
                        )
                        break

    def _check_jwt_tokens(self):
        resp = self.get(self.url)
        if not resp:
            return

        # Look for JWTs in cookies and response
        all_values = list(resp.cookies.values()) + list(resp.headers.values())
        all_values.append(resp.text[:5000])

        jwt_pattern = r'eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]*'
        jwt_found = []
        for val in all_values:
            if isinstance(val, str):
                tokens = re.findall(jwt_pattern, val)
                jwt_found.extend(tokens)

        for token in jwt_found[:3]:
            self._analyze_jwt(token)

    def _analyze_jwt(self, token):
        try:
            parts = token.split('.')
            if len(parts) != 3:
                return

            # Decode header and payload
            header = json.loads(base64.b64decode(parts[0] + '==').decode('utf-8', errors='ignore'))
            payload = json.loads(base64.b64decode(parts[1] + '==').decode('utf-8', errors='ignore'))

            alg = header.get('alg', '').upper()

            if alg == 'NONE':
                self.add_finding(
                    'JWT: Algorithm None',
                    'CRITICAL',
                    'JWT uses "none" algorithm - signature verification disabled!',
                    f'Algorithm: {alg}',
                    'Never accept JWTs with alg=none. Always verify signatures.'
                )

            if alg in ('HS256', 'HS384', 'HS512'):
                self.add_finding(
                    'JWT: HMAC Algorithm',
                    'INFO',
                    f'JWT uses symmetric algorithm {alg}.',
                    f'Payload claims: {list(payload.keys())}',
                    'Ensure JWT secret is long, random, and stored securely.'
                )
                # Test weak secrets (basic check only)
                self._test_weak_jwt_secret(token, parts, payload)

            # Check sensitive data in payload
            sensitive_claims = ['password', 'secret', 'key', 'token', 'card', 'ssn', 'email']
            found_sensitive = [k for k in payload.keys() if any(s in k.lower() for s in sensitive_claims)]
            if found_sensitive:
                self.add_finding(
                    'Sensitive Data in JWT Payload',
                    'HIGH',
                    f'JWT payload contains potentially sensitive claims: {found_sensitive}',
                    str(payload)[:200],
                    'Minimize data stored in JWT payload. It is base64-encoded, not encrypted.'
                )

            # Check expiry
            if 'exp' not in payload:
                self.add_finding(
                    'JWT: No Expiration',
                    'MEDIUM',
                    'JWT has no "exp" claim - token never expires.',
                    str(payload)[:200],
                    'Always include an exp claim in JWTs.'
                )

        except Exception:
            pass

    def _test_weak_jwt_secret(self, token, parts, payload):
        try:
            import hmac
            import hashlib
            header_payload = f'{parts[0]}.{parts[1]}'.encode()
            for secret in JWT_WEAK_SECRETS:
                sig = base64.urlsafe_b64encode(
                    hmac.new(secret.encode(), header_payload, hashlib.sha256).digest()
                ).rstrip(b'=').decode()
                if sig == parts[2]:
                    self.add_finding(
                        f'JWT: Weak Secret Cracked: "{secret}"',
                        'CRITICAL',
                        f'JWT signature verified with weak secret: "{secret}"',
                        f'Secret: {secret}',
                        'Use a cryptographically secure random secret of at least 256 bits.'
                    )
                    return
        except Exception:
            pass

    def _test_auth_bypass(self):
        """Test common auth bypass techniques."""
        bypass_headers = {
            'X-Original-URL': '/admin',
            'X-Rewrite-URL': '/admin',
            'X-Forwarded-For': '127.0.0.1',
            'X-Real-IP': '127.0.0.1',
            'X-Remote-IP': '127.0.0.1',
            'X-Custom-IP-Authorization': '127.0.0.1',
            'X-Forwarded-Host': 'localhost',
        }
        
        base = self.get_base_url()
        for header, value in bypass_headers.items():
            r = self.get(f'{base}/admin', headers={header: value})
            if r and r.status_code == 200:
                if 'login' not in r.url.lower():
                    self.add_finding(
                        f'Auth Bypass via {header}',
                        'CRITICAL',
                        f'Admin panel accessible by spoofing header {header}: {value}',
                        f'Header: {header}: {value}\nStatus: {r.status_code}',
                        'Never trust X-Forwarded-* headers for access control decisions.'
                    )

    def _check_password_policy(self):
        """Check for common weak password policy indicators."""
        base = self.get_base_url()
        register_paths = ['/register', '/signup', '/create-account', '/join']
        for path in register_paths:
            resp = self.get(f'{base}{path}')
            if resp and resp.status_code == 200:
                if 'password' in resp.text.lower():
                    # Look for password hints
                    if not re.search(r'(minimum|at least|must contain|characters)', resp.text, re.IGNORECASE):
                        self.add_finding(
                            'No Visible Password Policy',
                            'LOW',
                            f'Registration page {path} does not show password requirements.',
                            path,
                            'Enforce strong passwords: min 12 chars, mixed case, numbers, symbols.'
                        )
                    break

    def _test_account_enumeration(self):
        """Test if the app reveals whether a username exists."""
        base = self.get_base_url()
        for path in LOGIN_FORMS_PATHS[:3]:
            resp = self.get(f'{base}{path}')
            if not resp or resp.status_code != 200:
                continue

            from bs4 import BeautifulSoup
            from urllib.parse import urljoin
            soup = BeautifulSoup(resp.text, 'html.parser')
            form = soup.find('form')
            if not form:
                continue

            action = form.get('action', f'{base}{path}')
            if not action.startswith('http'):
                action = urljoin(f'{base}{path}', action)

            # Try definitely non-existent user
            r1 = self.post(action, data={'username': 'definitelynotauser_xyzxyz', 'password': 'test'})
            # Try possible real user
            r2 = self.post(action, data={'username': 'admin', 'password': 'wrongpassword123'})

            if r1 and r2:
                msg1 = r1.text.lower()
                msg2 = r2.text.lower()
                if ('user not found' in msg2 or 'user does not exist' in msg2 or 
                    'no account' in msg2):
                    self.add_finding(
                        'Username Enumeration Possible',
                        'MEDIUM',
                        'Different error messages for valid vs invalid usernames.',
                        f'Valid user error: {msg2[:100]}\nInvalid user error: {msg1[:100]}',
                        'Return generic error: "Invalid username or password" for all auth failures.'
                    )
            break
