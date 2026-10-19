"""
Network Core & Connection Pool for Distroyer
Provides persistent HTTP session pooling, exponential backoff retries,
rate limiting/throttling, upstream proxy routing, TLS configuration,
scope guarding, and session health checks.
"""
import time
import math
import random
import threading
import urllib.parse
import urllib3
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Suppress insecure request warnings when operating in security testing mode
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class ScopeGuard:
    """Validates and restricts requests to target scope."""

    def __init__(self, target_url: str, scope_mode: str = 'subdomains', exclude_hosts: list = None):
        self.target_url = target_url
        parsed = urllib.parse.urlparse(target_url)
        self.target_netloc = parsed.netloc.split(':')[0].lower()
        self.scope_mode = scope_mode.lower() if scope_mode else 'subdomains'
        self.exclude_hosts = [h.strip().lower() for h in (exclude_hosts or []) if h.strip()]

    def is_in_scope(self, url: str) -> bool:
        if not url:
            return False
        try:
            parsed = urllib.parse.urlparse(url)
            host = parsed.netloc.split(':')[0].lower()
            if not host:
                return True  # Relative URL is considered in scope

            # Check explicit exclusions (e.g. CDNs, analytics)
            for excluded in self.exclude_hosts:
                if host == excluded or host.endswith(f".{excluded}"):
                    return False

            if self.scope_mode == 'exact':
                return host == self.target_netloc
            else:  # subdomains allowed
                return host == self.target_netloc or host.endswith(f".{self.target_netloc}")
        except Exception:
            return False


class RateLimiter:
    """Thread-safe token bucket rate limiter."""

    def __init__(self, rate_limit_rps: float = None, fixed_delay: float = 0.0):
        self.rate_limit_rps = rate_limit_rps
        self.fixed_delay = fixed_delay or 0.0
        self.lock = threading.Lock()
        self.last_request_time = 0.0

    def wait(self):
        with self.lock:
            now = time.time()
            # If fixed delay is set
            if self.fixed_delay > 0:
                elapsed = now - self.last_request_time
                if elapsed < self.fixed_delay:
                    time.sleep(self.fixed_delay - elapsed)
                self.last_request_time = time.time()
                return

            # If rate limit per second is set
            if self.rate_limit_rps and self.rate_limit_rps > 0:
                min_interval = 1.0 / self.rate_limit_rps
                elapsed = now - self.last_request_time
                if elapsed < min_interval:
                    time.sleep(min_interval - elapsed)
                self.last_request_time = time.time()


class NetworkManager:
    """Centralized, resilient network transport manager for Distroyer."""

    def __init__(self, config: dict):
        self.config = config
        self.timeout = config.get('timeout', 10)
        self.max_retries = config.get('retries', 3)
        self.verbose = config.get('verbose', False)

        # Rate limiter
        rps = config.get('rate_limit')
        delay = config.get('delay', 0.1 if not config.get('stealth') else 2.0)
        self.rate_limiter = RateLimiter(rate_limit_rps=rps, fixed_delay=delay)

        # Scope guard
        exclude = config.get('exclude_hosts', [])
        if isinstance(exclude, str):
            exclude = [h.strip() for h in exclude.split(',') if h.strip()]
        self.scope_guard = ScopeGuard(
            target_url=config.get('url', ''),
            scope_mode=config.get('scope_mode', 'subdomains'),
            exclude_hosts=exclude
        )

        # Session & Connection Pool
        self.session = requests.Session()
        
        # Configure Retries with Exponential Backoff
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=1.0,
            status_forcelist=[429, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS", "TRACE"],
            raise_on_status=False
        )

        pool_connections = max(20, config.get('threads', 10) * 2)
        pool_maxsize = max(50, config.get('threads', 10) * 4)

        adapter = HTTPAdapter(
            pool_connections=pool_connections,
            pool_maxsize=pool_maxsize,
            max_retries=retry_strategy
        )
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

        # Proxy Configuration
        proxy = config.get('proxy')
        if proxy:
            if isinstance(proxy, str):
                self.session.proxies = {'http': proxy, 'https': proxy}
            elif isinstance(proxy, dict):
                self.session.proxies = proxy

        # TLS verification
        self.session.verify = not config.get('insecure', True)  # Default insecure for pentest flexibility

        # Custom Headers & Auth
        self.custom_headers = dict(config.get('headers', {}))
        if config.get('user_agent'):
            self.custom_headers['User-Agent'] = config['user_agent']
        if config.get('cookie'):
            self.custom_headers['Cookie'] = config['cookie']
        self.session.headers.update(self.custom_headers)

        # Session Health Checking
        self.check_session_url = config.get('check_session_url')
        self.session_valid = True

    def check_session_health(self) -> bool:
        """Verify if current authenticated session is still valid."""
        if not self.check_session_url:
            return True
        try:
            resp = self.get(self.check_session_url, timeout=5)
            if resp and resp.status_code in (401, 403):
                self.session_valid = False
                return False
            self.session_valid = True
            return True
        except Exception:
            return self.session_valid

    def request(self, method: str, url: str, **kwargs):
        """Execute request through pool, enforcing rate limit, scope, and backoff."""
        if not self.scope_guard.is_in_scope(url):
            if self.verbose:
                print(f"[ScopeGuard] Blocked out-of-scope URL: {url}")
            return None

        self.rate_limiter.wait()
        kwargs.setdefault('timeout', self.timeout)

        # Custom retry with jitter in case of 429 or connection issues
        for attempt in range(self.max_retries + 1):
            try:
                resp = self.session.request(method, url, **kwargs)
                if resp.status_code == 429 and attempt < self.max_retries:
                    retry_after = resp.headers.get("Retry-After")
                    try:
                        wait_sec = float(retry_after) if retry_after else (2 ** attempt) + random.uniform(0.1, 0.5)
                    except ValueError:
                        wait_sec = (2 ** attempt) + random.uniform(0.1, 0.5)
                    time.sleep(wait_sec)
                    continue
                return resp
            except requests.exceptions.RequestException as e:
                if attempt < self.max_retries:
                    time.sleep((1.5 ** attempt) + random.uniform(0.1, 0.5))
                    continue
                if self.verbose:
                    print(f"[Network] Request error for {url}: {e}")
                return None
        return None

    def get(self, url: str, **kwargs):
        kwargs.setdefault('allow_redirects', True)
        return self.request('GET', url, **kwargs)

    def post(self, url: str, data=None, json=None, **kwargs):
        return self.request('POST', url, data=data, json=json, **kwargs)

    def head(self, url: str, **kwargs):
        kwargs.setdefault('allow_redirects', False)
        return self.request('HEAD', url, **kwargs)

    def options(self, url: str, **kwargs):
        return self.request('OPTIONS', url, **kwargs)
