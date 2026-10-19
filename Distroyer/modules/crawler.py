"""
Web Crawler Module
Extracts all links, forms, endpoints, and parameters from the target
"""
import re
from urllib.parse import urljoin, urlparse, parse_qs
from collections import deque
from bs4 import BeautifulSoup
from .base import BaseModule


class CrawlerModule(BaseModule):
    """Web crawler to discover endpoints, forms, and parameters."""

    def run(self) -> dict:
        # Check if crawl was already executed in this scan session
        if self.context.get('crawler_ran'):
            return self.result({
                'pages': self.context.get('pages', []),
                'endpoints': self.context.get('endpoints', []),
                'forms': self.context.get('forms', []),
                'scripts': self.context.get('scripts', []),
                'emails': self.context.get('emails', []),
            })

        max_depth = self.config.get('depth', 2)
        domain = self.get_domain()

        visited = set()
        queue = deque([(self.url, 0)])
        all_endpoints = []
        normalized_endpoints_seen = set()
        all_forms = []
        all_scripts = []
        all_emails = []

        while queue:
            current_url, depth = queue.popleft()
            if current_url in visited or depth > max_depth:
                continue
            if not self._is_same_domain(current_url, domain):
                continue
            visited.add(current_url)

            resp = self.get(current_url)
            if not resp or 'text/html' not in resp.headers.get('Content-Type', ''):
                continue

            soup = BeautifulSoup(resp.text, 'html.parser')

            # Extract links
            links = self._extract_links(soup, current_url, domain)
            for link in links:
                norm = self._normalize_route(link)
                if norm not in normalized_endpoints_seen:
                    normalized_endpoints_seen.add(norm)
                    if link not in all_endpoints:
                        all_endpoints.append(link)
                if link not in visited and depth < max_depth:
                    queue.append((link, depth + 1))

            # Extract forms
            forms = self._extract_forms(soup, current_url)
            all_forms.extend(forms)

            # Extract JS files
            scripts = self._extract_scripts(soup, current_url)
            for s in scripts:
                if s not in all_scripts:
                    all_scripts.append(s)

            # Extract emails
            emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', resp.text)
            all_emails.extend(emails)

        # Analyze JS files for API endpoints (deep JS scanning)
        api_endpoints = self._analyze_scripts(all_scripts, domain)
        for ep in api_endpoints:
            norm = self._normalize_route(ep)
            if norm not in normalized_endpoints_seen:
                normalized_endpoints_seen.add(norm)
                all_endpoints.append(ep)

        if all_emails:
            unique_emails = list(set(all_emails))
            self.add_finding(
                'Email Addresses Discovered',
                'LOW',
                f'{len(unique_emails)} email addresses found in source',
                '\n'.join(unique_emails[:10]),
                'Avoid exposing email addresses in public HTML (spam risk).'
            )

        self.add_finding(
            'Crawl Complete',
            'INFO',
            f'Discovered {len(visited)} pages, {len(all_forms)} forms, {len(all_endpoints)} endpoints',
            f'Pages visited: {len(visited)}'
        )

        unique_endpoints = list(dict.fromkeys(all_endpoints))
        unique_emails = list(set(all_emails))

        # Store in shared scan context so other modules don't re-crawl
        self.context['pages'] = list(visited)
        self.context['endpoints'] = unique_endpoints
        self.context['forms'] = all_forms
        self.context['scripts'] = all_scripts
        self.context['emails'] = unique_emails
        self.context['crawler_ran'] = True

        return self.result({
            'pages': list(visited),
            'endpoints': unique_endpoints,
            'forms': all_forms,
            'scripts': all_scripts,
            'emails': unique_emails,
        })

    def _normalize_route(self, url: str) -> str:
        """Normalize UUIDs, IDs, and dynamic segments to avoid scanning identical endpoints."""
        parsed = urlparse(url)
        path = parsed.path
        # Normalize UUIDs
        path = re.sub(r'/[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}', '/{uuid}', path)
        # Normalize numeric IDs
        path = re.sub(r'/\d+(?=/|$)', '/{id}', path)
        # Normalize hashes (MD5, SHA1)
        path = re.sub(r'/[0-9a-fA-F]{32,64}(?=/|$)', '/{hash}', path)
        return f"{parsed.netloc}{path}"

    def _extract_links(self, soup, base_url, domain):
        links = []
        for tag in soup.find_all(['a', 'link', 'area'], href=True):
            href = tag.get('href', '').strip()
            if not href or href.startswith('#') or href.startswith('mailto:') or href.startswith('javascript:'):
                continue
            absolute = urljoin(base_url, href)
            parsed = urlparse(absolute)
            if parsed.scheme in ('http', 'https') and parsed.netloc:
                links.append(absolute.split('#')[0])
        return links

    def _extract_forms(self, soup, base_url):
        forms = []
        for form in soup.find_all('form'):
            action = form.get('action', '')
            if action:
                action = urljoin(base_url, action)
            else:
                action = base_url

            method = form.get('method', 'GET').upper()
            fields = {}
            for inp in form.find_all(['input', 'textarea', 'select']):
                name = inp.get('name')
                if name:
                    fields[name] = inp.get('value', '') or inp.get('placeholder', '') or ''

            forms.append({
                'action': action,
                'method': method,
                'fields': fields,
                'html': str(form)[:1000],
            })
        return forms

    def _extract_scripts(self, soup, base_url):
        scripts = []
        for tag in soup.find_all('script', src=True):
            src = tag.get('src', '')
            if src:
                absolute = urljoin(base_url, src)
                if absolute not in scripts:
                    scripts.append(absolute)
        return scripts

    def _analyze_scripts(self, script_urls, domain):
        """Fetch JS files and extract API endpoints using advanced regex patterns."""
        endpoints = []
        base_url = self.get_base_url()

        # Advanced patterns for SPA routers, axios, fetch, and relative paths
        api_patterns = [
            # Relative API prefixes
            r'["\']((?:/(?:api|v[0-9]|rest|auth|graphql))[^"\'\s\?#\\]+)["\']',
            # Object route paths: path: '/users', route: '/dashboard'
            r'(?:path|url|route|endpoint)\s*:\s*["\']([^"\'\s]+)["\']',
            # fetch('/endpoint')
            r'fetch\(["\']([^"\'\s]+)["\']',
            # axios.get('/endpoint')
            r'axios\.(?:get|post|put|delete|patch)\(["\']([^"\'\s]+)["\']',
            # Template literals with base: `/api/users/${id}`
            r'`(/api/[^`]+)`',
            r'`(/v[0-9]/[^`]+)`',
        ]

        # Scan up to 15 JS files
        for url in script_urls[:15]:
            resp = self.get(url)
            if not resp or not resp.text:
                continue

            text = resp.text
            for pattern in api_patterns:
                matches = re.findall(pattern, text)
                for m in matches:
                    path = m if isinstance(m, str) else m[0]
                    # Filter out template literal syntax (${id} -> 1)
                    clean_path = re.sub(r'\$\{[^}]+\}', '1', path)
                    if clean_path.startswith('/') and not clean_path.startswith('//'):
                        # Exclude static asset extensions
                        if any(clean_path.lower().endswith(ext) for ext in ('.png', '.jpg', '.css', '.svg', '.woff', '.ico')):
                            continue
                        full = f"{base_url}{clean_path}"
                        if full not in endpoints:
                            endpoints.append(full)
        return endpoints

    def _is_same_domain(self, url, domain):
        try:
            parsed = urlparse(url)
            return parsed.netloc == domain or parsed.netloc.endswith(f'.{domain}')
        except Exception:
            return False
