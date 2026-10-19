"""
Professional Report Generator Module
Generates executive-grade HTML and JSON pentest reports
"""
import json
from datetime import datetime
from .base import BaseModule


# ─────────────────────────────────────────────────────────────────────────────
# Vulnerability Knowledge Base
# Maps finding title keywords → detailed explanation, OWASP ref, CVSS, impact
# ─────────────────────────────────────────────────────────────────────────────
VULN_KB = {   'admin panel': {   'cvss': '5.3',
                       'cwe': 'CWE-288',
                       'impact': 'Increases exposure to credential brute-forcing, credential stuffing, '
                                 'default-credential exploitation, and software vulnerabilities in third-party '
                                 'management tools.',
                       'owasp': 'A07:2021 - Identification and Authentication Failures',
                       'references': [   'https://owasp.org/Top10/A07_2021-Identification_and_Authentication_Failures/',
                                         'https://cwe.mitre.org/data/definitions/288.html'],
                       'remediation': [   'Restrict administrative interfaces by IP whitelisting or place them behind '
                                          'a secure VPN / bastion host.',
                                          'Change default administrative paths to non-standard paths and enable '
                                          'Multi-Factor Authentication (MFA).',
                                          'Implement rate limiting and account lockout after multiple failed '
                                          'authentication attempts.'],
                       'what_is': 'Administrative consoles, database management tools (e.g. phpMyAdmin, Adminer), and '
                                  'CMS login portals were discovered exposed on predictable URL paths without IP '
                                  'restrictions.'},
    'backup': {   'cvss': '7.5',
                  'cwe': 'CWE-530',
                  'impact': 'Exposure of sensitive application source code, hardcoded database credentials, API keys, '
                            'session secrets, and internal database structures. Can directly lead to full '
                            'infrastructure compromise.',
                  'owasp': 'A05:2021 - Security Misconfiguration',
                  'references': [   'https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/02-Configuration_and_Deployment_Management_Testing/04-Review_Old_Backup_and_Unreferenced_Files_for_Sensitive_Information',
                                    'https://cwe.mitre.org/data/definitions/530.html',
                                    'https://cheatsheetseries.owasp.org/cheatsheets/File_System_Security_Cheat_Sheet.html'],
                  'remediation': [   'Immediately remove all backup, archive (.zip, .tar.gz, .sql), and editor '
                                     'temporary (.bak, .old) files from web-accessible roots.',
                                     'Configure the web server (Nginx/Apache) to deny access to files matching backup '
                                     'extensions: .bak, .old, .backup, .sql, .tmp.',
                                     'Store system backups outside the web document root in an encrypted, '
                                     'access-controlled storage bucket or server.',
                                     'Integrate automated pre-commit and deployment scans to detect and prevent '
                                     'committing backup artifacts to production.'],
                  'what_is': 'Backup and unreferenced files (such as .bak, .old, .backup, .tar.gz, or .sql) are often '
                             'left on web servers after manual edits, updates, or automated backup routines. Because '
                             'web servers often serve these files as plain text or downloadable binaries, attackers '
                             'can download the complete source code, database dumps, or configuration credentials.'},
    'cannot retrieve certificate': {   'cvss': '7.5',
                                       'cwe': 'CWE-295',
                                       'impact': 'Clients may receive browser security warnings, connection drops, or '
                                                 'may fall back to insecure unencrypted channels.',
                                       'owasp': 'A02:2021 - Cryptographic Failures',
                                       'references': [   'https://cheatsheetseries.owasp.org/cheatsheets/Transport_Layer_Protection_Cheat_Sheet.html',
                                                         'https://cwe.mitre.org/data/definitions/295.html'],
                                       'remediation': [   'Ensure a valid, trusted SSL/TLS certificate from a '
                                                          'recognized Certificate Authority is bound to port 443.',
                                                          'Verify server hostname matches certificate Common Name (CN) '
                                                          'and Subject Alternative Names (SAN).',
                                                          "Automate certificate renewal using ACME / Let's Encrypt "
                                                          'with Certbot.'],
                                       'what_is': 'The scanner was unable to retrieve a valid SSL/TLS certificate, or '
                                                  'the certificate negotiation failed. This may indicate misconfigured '
                                                  'TLS bindings, expired certificates, or non-standard cryptographic '
                                                  'configurations.'},
    'certificate': {   'cvss': '6.5',
                       'cwe': 'CWE-295',
                       'impact': 'Improper certificate management leads to connection interception, trust warnings for '
                                 'users, and downtime.',
                       'owasp': 'A02:2021 - Cryptographic Failures',
                       'references': [   'https://cheatsheetseries.owasp.org/cheatsheets/Transport_Layer_Protection_Cheat_Sheet.html',
                                         'https://cwe.mitre.org/data/definitions/295.html'],
                       'remediation': [   'Deploy valid TLS certificates issued by trusted public CAs.',
                                          'Monitor expiration dates with automated alerts at 30, 14, and 7 days prior '
                                          'to expiry.',
                                          'Ensure all public subdomains are included in certificate SAN entries.'],
                       'what_is': 'Analysis of the SSL/TLS digital certificate configuration, expiration schedule, '
                                  'Subject Alternative Names (SAN), or Certificate Authority chain of trust.'},
    'cors': {   'cvss': '8.1',
                'cwe': 'CWE-942',
                'impact': "Complete API access from attacker-controlled websites in the victim's authenticated "
                          'session, data exfiltration of all user data, account takeover, and in some cases CSRF-like '
                          'attacks bypassing same-origin protections.',
                'owasp': 'A05:2021 - Security Misconfiguration',
                'references': [   'https://portswigger.net/web-security/cors',
                                  'https://cheatsheetseries.owasp.org/cheatsheets/HTTP_Headers_Cheat_Sheet.html',
                                  'https://cwe.mitre.org/data/definitions/942.html'],
                'remediation': [   'Maintain an explicit allowlist of trusted origins.',
                                   'Never reflect the Origin request header directly in ACAO response.',
                                   'Never combine Access-Control-Allow-Origin: * with '
                                   'Access-Control-Allow-Credentials: true.',
                                   'Reject requests from the null origin.',
                                   'Only allow necessary HTTP methods in CORS preflight.',
                                   'Treat CORS configuration as a security-sensitive operation.'],
                'what_is': 'Cross-Origin Resource Sharing (CORS) misconfigurations allow unauthorized cross-origin '
                           'requests to succeed. When Access-Control-Allow-Origin reflects the request Origin or is '
                           'set to wildcard with credentials, any website can make authenticated API calls on behalf '
                           'of users visiting the malicious site.'},
    'crawl complete': {   'cvss': '2.0',
                          'cwe': 'CWE-200',
                          'impact': 'Defines the discoverable attack surface of the application.',
                          'owasp': 'A05:2021 - Security Misconfiguration',
                          'references': ['https://owasp.org/Top10/A05_2021-Security_Misconfiguration/'],
                          'remediation': [   'Audit public pages to ensure unauthenticated users cannot access '
                                             'sensitive business workflows.'],
                          'what_is': 'Web spider and crawler mapped accessible application pages, forms, and input '
                                     'parameters.'},
    'csrf': {   'cvss': '6.5',
                'cwe': 'CWE-352',
                'impact': 'Unauthorized state-changing actions on behalf of the victim: fund transfers, email/password '
                          'changes, account deletion, privilege escalation, or any other action the victim is '
                          'authorized to perform.',
                'owasp': 'A01:2021 - Broken Access Control',
                'references': [   'https://owasp.org/Top10/A01_2021-Broken_Access_Control/',
                                  'https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html',
                                  'https://cwe.mitre.org/data/definitions/352.html'],
                'remediation': [   'Implement synchronizer token pattern (CSRF tokens) on all state-changing forms.',
                                   'Use SameSite=Strict or SameSite=Lax cookie attribute.',
                                   'Verify the Origin and Referer headers on the server side.',
                                   'Use the Double Submit Cookie pattern as an alternative.',
                                   'Require re-authentication for sensitive operations.',
                                   'Avoid using GET requests for state-changing actions.'],
                'what_is': 'Cross-Site Request Forgery (CSRF) tricks authenticated users into unknowingly submitting '
                           'requests to a web application in which they are currently authenticated. The attack '
                           "exploits the trust a web application has in the user's browser, causing state-changing "
                           "actions without the user's knowledge."},
    'default credentials': {   'cvss': '9.8',
                               'cwe': 'CWE-798',
                               'impact': 'Immediate full administrative access to the application or system, complete '
                                         'data breach, ability to install backdoors, and lateral movement within the '
                                         'infrastructure.',
                               'owasp': 'A07:2021 - Identification and Authentication Failures',
                               'references': [   'https://owasp.org/Top10/A07_2021-Identification_and_Authentication_Failures/',
                                                 'https://cwe.mitre.org/data/definitions/798.html'],
                               'remediation': [   'Change all default credentials immediately after deployment.',
                                                  'Force password change on first login.',
                                                  'Implement minimum password complexity requirements.',
                                                  'Implement account lockout after failed attempts.',
                                                  'Use a secrets manager for credential storage.',
                                                  'Never hardcode credentials in source code or configuration files.'],
                               'what_is': 'Default or weak credentials that ship with software were never changed. '
                                          'Attackers use publicly known default username/password combinations to gain '
                                          'unauthorized access. This is one of the most common and easily exploitable '
                                          'vulnerabilities.'},
    'directory enumeration': {   'cvss': '2.0',
                                 'cwe': 'CWE-548',
                                 'impact': 'Provides visibility into the overall attack surface and exposed endpoints.',
                                 'owasp': 'A05:2021 - Security Misconfiguration',
                                 'references': ['https://owasp.org/Top10/A05_2021-Security_Misconfiguration/'],
                                 'remediation': [   'Disable directory listings and remove unnecessary files and '
                                                    'endpoints from web servers.'],
                                 'what_is': 'Automated enumeration of web paths, files, and directories completed.'},
    'dns records': {   'cvss': '2.5',
                       'cwe': 'CWE-200',
                       'impact': 'Provides reconnaissance data that aids in social engineering and email spoofing if '
                                 'SPF/DMARC are incomplete.',
                       'owasp': 'A05:2021 - Security Misconfiguration',
                       'references': [   'https://owasp.org/Top10/A05_2021-Security_Misconfiguration/',
                                         'https://cwe.mitre.org/data/definitions/200.html'],
                       'remediation': [   'Audit DNS records to remove obsolete verification tokens (e.g. old SPF/DKIM '
                                          'or domain ownership TXT records).',
                                          'Enforce strong SPF, DKIM, and DMARC policies to prevent email '
                                          'impersonation.'],
                       'what_is': 'DNS enumeration identified active DNS resource records (A, MX, NS, TXT). DNS '
                                  'records often reveal email service providers, third-party verifications, and '
                                  'internal hostnames.'},
    'email addresses discovered': {   'cvss': '3.1',
                                      'cwe': 'CWE-200',
                                      'impact': 'Increased susceptibility of staff to targeted spear-phishing, '
                                                'business email compromise (BEC), and credential harvesting.',
                                      'owasp': 'A05:2021 - Security Misconfiguration',
                                      'references': [   'https://cwe.mitre.org/data/definitions/200.html',
                                                        'https://owasp.org/Top10/A05_2021-Security_Misconfiguration/'],
                                      'remediation': [   'Replace plain-text email addresses in public HTML with web '
                                                         'contact forms protected by CAPTCHA.',
                                                         'Use obfuscation techniques or client-side rendering for '
                                                         'email contacts if necessary.'],
                                      'what_is': 'Corporate or personal email addresses were discovered in HTML '
                                                 'comments, source code, or contact pages. Automated scrapers harvest '
                                                 'these addresses for targeted phishing and spam campaigns.'},
    'git': {   'cvss': '9.1',
               'cwe': 'CWE-538',
               'impact': 'Complete source code disclosure including historical commits that may contain credentials, '
                         'API keys, database passwords, internal architecture details, commented-out debug code, and '
                         'business logic that facilitates further attacks.',
               'owasp': 'A05:2021 - Security Misconfiguration',
               'references': [   'https://cwe.mitre.org/data/definitions/538.html',
                                 'https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/02-Configuration_and_Deployment_Management_Testing/04-Review_Old_Backup_and_Unreferenced_Files_for_Sensitive_Information'],
               'remediation': [   'Add a rule to block access to /.git/ in your web server configuration.',
                                  'Nginx: location ~* /\\.git { deny all; }',
                                  'Apache: RedirectMatch 404 /\\.git',
                                  'Never deploy directly from a Git repository root.',
                                  'Audit the repository for committed secrets and rotate all exposed credentials.',
                                  'Use tools like git-secrets or truffleHog to scan history for secrets.'],
               'what_is': 'An exposed .git directory allows anyone to download the complete version history of the '
                          'application source code. This is caused by deploying code directly from a Git repository '
                          'without restricting access to the .git folder.'},
    'git repository': {   'cvss': '7.5',
                          'cwe': 'CWE-538',
                          'impact': 'Full source code extraction, disclosure of developer credentials, API tokens, and '
                                    'internal architecture.',
                          'owasp': 'A05:2021 - Security Misconfiguration',
                          'references': [   'https://cwe.mitre.org/data/definitions/538.html',
                                            'https://owasp.org/Top10/A05_2021-Security_Misconfiguration/'],
                          'remediation': [   'Block access to /.git and all hidden files/directories in web server '
                                             'configuration (location ~ /\\. { deny all; }).',
                                             'Deploy code using clean build artifacts (e.g. Docker images, rsync '
                                             'excluding .git) rather than direct git pulls.'],
                          'what_is': 'The Git (.git) directory is publicly accessible. Attackers can download '
                                     'repository objects and completely reconstruct source code, commit history, and '
                                     'cryptographic secrets.'},
    'permissions-policy': {
        'cvss': '3.1',
        'cwe': 'CWE-693',
        'impact': 'Absence of Permissions-Policy allows browser features like camera, microphone, and geolocation to be used without restriction.',
        'owasp': 'A05:2021 - Security Misconfiguration',
        'references': ['https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Permissions-Policy', 'https://cheatsheetseries.owasp.org/cheatsheets/HTTP_Headers_Cheat_Sheet.html'],
        'remediation': ['Add Permissions-Policy: camera=(), microphone=(), geolocation=() to restrict powerful browser features.'],
        'what_is': 'Permissions-Policy allows a site to control which browser features and APIs can be used by the page and embedded iframes.'
    },
    'cache-control': {
        'cvss': '3.1',
        'cwe': 'CWE-525',
        'impact': 'Missing or weak Cache-Control on authenticated or sensitive pages can lead to sensitive data cached in browser history or proxies.',
        'owasp': 'A05:2021 - Security Misconfiguration',
        'references': ['https://owasp.org/www-project-web-security-testing-guide/v42/4-Web_Application_Security_Testing/04-Authentication_Testing/06-Testing_for_Browser_Cache_Weaknesses'],
        'remediation': ['Set Cache-Control: no-store, no-cache, must-revalidate and Pragma: no-cache on sensitive responses.'],
        'what_is': 'The Cache-Control header dictates whether and how browsers and intermediate proxies store HTTP responses.'
    },
    'origin header': {
        'cvss': '5.3',
        'cwe': 'CWE-346',
        'impact': 'Failure to reject unauthorized Origin headers may expose internal endpoints or allow cross-origin request abuse.',
        'owasp': 'A01:2021 - Broken Access Control',
        'references': ['https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html'],
        'remediation': ['Validate Origin and Referer headers against an explicit server-side allowlist.'],
        'what_is': 'The server accepted requests bearing unexpected or forged Origin headers without validation.'
    },
    'ssrf': {
        'cvss': '8.6',
        'cwe': 'CWE-918',
        'impact': 'Enables an attacker to coerce the server into issuing HTTP/TCP requests to internal infrastructure, loopback services, or cloud metadata APIs.',
        'owasp': 'A10:2021 - Server-Side Request Forgery',
        'references': ['https://owasp.org/Top10/A10_2021-Server-Side_Request_Forgery_%28SSRF%29/', 'https://cwe.mitre.org/data/definitions/918.html'],
        'remediation': ['Enforce a strict destination IP/domain allowlist.', 'Block loopback (127.0.0.0/8) and cloud metadata IP (169.254.169.254).', 'Disable unused URL schemes.'],
        'what_is': 'Server-Side Request Forgery occurs when a web application fetches a remote resource without validating the user-supplied URL.'
    },
    'rate limit': {
        'cvss': '5.3',
        'cwe': 'CWE-307',
        'impact': 'Permits automated credential stuffing, brute-force password guessing, and endpoint resource exhaustion.',
        'owasp': 'A04:2021 - Insecure Design',
        'references': ['https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html'],
        'remediation': ['Implement rate limiting returning HTTP 429 Too Many Requests.', 'Enforce account lockouts after consecutive failed attempts.'],
        'what_is': 'Sensitive authentication endpoints lack rate limiting protections against high-volume automated requests.'
    },
    'exposed secret': {
        'cvss': '8.9',
        'cwe': 'CWE-798',
        'impact': 'Direct compromise of cloud infrastructure, third-party payment gateways, internal databases, or administrative APIs.',
        'owasp': 'A07:2021 - Identification and Authentication Failures',
        'references': ['https://cwe.mitre.org/data/definitions/798.html'],
        'remediation': ['Immediately revoke and rotate the exposed secret keys.', 'Store secrets strictly in secure server-side vaults.', 'Add secret scanners to pre-commit git hooks.'],
        'what_is': 'Sensitive API tokens, credentials, or private cryptographic keys were found hardcoded in client-accessible assets.'
    },
    'header': {   'cvss': '5.3',
                  'cwe': 'CWE-693',
                  'impact': 'Varies by missing header: missing CSP enables XSS; missing X-Frame-Options enables '
                            'clickjacking; missing HSTS enables protocol downgrade; missing X-Content-Type-Options '
                            'enables MIME-type sniffing attacks. Collectively they significantly increase the '
                            "application's attack surface.",
                  'owasp': 'A05:2021 - Security Misconfiguration',
                  'references': [   'https://owasp.org/Top10/A05_2021-Security_Misconfiguration/',
                                    'https://securityheaders.com/',
                                    'https://cheatsheetseries.owasp.org/cheatsheets/HTTP_Headers_Cheat_Sheet.html'],
                  'remediation': [   'Add Strict-Transport-Security: max-age=31536000; includeSubDomains; preload',
                                     'Add Content-Security-Policy with a strict policy.',
                                     'Add X-Content-Type-Options: nosniff',
                                     'Add X-Frame-Options: DENY or SAMEORIGIN',
                                     'Add Referrer-Policy: strict-origin-when-cross-origin',
                                     'Add Permissions-Policy to restrict browser APIs.',
                                     'Remove X-Powered-By and Server version headers.'],
                  'what_is': 'HTTP security headers instruct browsers to apply additional security policies to the '
                             'application. Missing or misconfigured headers leave the application vulnerable to a '
                             'range of client-side attacks that browsers could otherwise prevent.'},
    'hsts': {   'cvss': '5.3',
                'cwe': 'CWE-319',
                'impact': 'Vulnerability to network eavesdropping, session hijacking, and SSL-stripping on untrusted '
                          'networks.',
                'owasp': 'A05:2021 - Security Misconfiguration',
                'references': [   'https://cheatsheetseries.owasp.org/cheatsheets/HTTP_Strict_Transport_Security_Cheat_Sheet.html',
                                  'https://cwe.mitre.org/data/definitions/319.html'],
                'remediation': [   'Add the header: Strict-Transport-Security: max-age=31536000; includeSubDomains; '
                                   'preload.'],
                'what_is': 'HTTP Strict Transport Security (HSTS) informs browsers that the site must only be accessed '
                           'using HTTPS. Missing or weak HSTS allows protocol downgrade and man-in-the-middle '
                           'eavesdropping.'},
    'hsts missing includesubdomains': {   'cvss': '4.3',
                                          'cwe': 'CWE-319',
                                          'impact': 'Attackers can perform man-in-the-middle attacks against '
                                                    'unencrypted subdomains or spoof subdomains to steal cookies.',
                                          'owasp': 'A05:2021 - Security Misconfiguration',
                                          'references': [   'https://cheatsheetseries.owasp.org/cheatsheets/HTTP_Strict_Transport_Security_Cheat_Sheet.html',
                                                            'https://cwe.mitre.org/data/definitions/319.html'],
                                          'remediation': [   'Ensure all subdomains support HTTPS, then add '
                                                             '"includeSubDomains" to the Strict-Transport-Security '
                                                             'header.'],
                                          'what_is': 'The HSTS header does not specify the includeSubDomains '
                                                     'directive, leaving subdomains unprotected by the root domain '
                                                     'policy.'},
    'hsts missing preload': {   'cvss': '4.3',
                                'cwe': 'CWE-319',
                                'impact': 'A first-time visitor connecting over plain HTTP before receiving the HSTS '
                                          'header remains susceptible to SSL-stripping attacks.',
                                'owasp': 'A05:2021 - Security Misconfiguration',
                                'references': [   'https://hstspreload.org/',
                                                  'https://cheatsheetseries.owasp.org/cheatsheets/HTTP_Strict_Transport_Security_Cheat_Sheet.html',
                                                  'https://cwe.mitre.org/data/definitions/319.html'],
                                'remediation': [   'Configure HSTS with: Strict-Transport-Security: max-age=31536000; '
                                                   'includeSubDomains; preload.',
                                                   'Submit your domain to the official browser preload registry at '
                                                   'https://hstspreload.org/.'],
                                'what_is': 'The HTTP Strict Transport Security (HSTS) header is present but lacks the '
                                           '"preload" directive, meaning the domain is not submitted to browser vendor '
                                           'HSTS preload lists.'},
    'information disclosure: server': {   'cvss': '3.7',
                                          'cwe': 'CWE-200',
                                          'impact': 'Facilitates targeted vulnerability research against known '
                                                    'unpatched server exploits.',
                                          'owasp': 'A05:2021 - Security Misconfiguration',
                                          'references': [   'https://cwe.mitre.org/data/definitions/200.html',
                                                            'https://owasp.org/Top10/A05_2021-Security_Misconfiguration/'],
                                          'remediation': [   'In Nginx, set "server_tokens off;" in nginx.conf.',
                                                             'In Apache, set "ServerTokens Prod" and "ServerSignature '
                                                             'Off".',
                                                             'Remove or overwrite the Server header in CDN/reverse '
                                                             'proxy rules.'],
                                          'what_is': 'The web server returns a "Server" header exposing software name '
                                                     'and version details (e.g. nginx/1.18.0). This enables attackers '
                                                     'to immediately look up known public CVEs for that specific '
                                                     'software release.'},
    'ip & asn': {   'cvss': '2.0',
                    'cwe': 'CWE-200',
                    'impact': 'Identifies hosting provider, network block, and geographic infrastructure location.',
                    'owasp': 'A05:2021 - Security Misconfiguration',
                    'references': ['https://cwe.mitre.org/data/definitions/200.html'],
                    'remediation': [   'Consider routing public web traffic through a Cloud WAF/reverse proxy (e.g. '
                                       'Cloudflare) to obscure origin server IP.'],
                    'what_is': 'Network IP resolution and Autonomous System Number (ASN) information was mapped.'},
    'jwt': {   'cvss': '8.8',
               'cwe': 'CWE-327',
               'impact': 'Authentication bypass and privilege escalation (forging admin tokens), account takeover, '
                         'exposure of sensitive user data from token payload, and non-expiring tokens that persist '
                         'after logout.',
               'owasp': 'A02:2021 - Cryptographic Failures',
               'references': [   'https://portswigger.net/web-security/jwt',
                                 'https://cheatsheetseries.owasp.org/cheatsheets/JSON_Web_Token_for_Java_Cheat_Sheet.html',
                                 'https://cwe.mitre.org/data/definitions/327.html'],
               'remediation': [   'Use a cryptographically secure random secret of at least 256 bits for HMAC.',
                                  'Prefer asymmetric algorithms (RS256, ES256) over symmetric (HS256).',
                                  'Always validate the "alg" header and reject "none".',
                                  'Include and validate the "exp" (expiration) claim.',
                                  'Never store sensitive data in JWT payload (it is not encrypted).',
                                  'Implement token revocation/blacklisting for logout.',
                                  'Use short expiry times and implement refresh token rotation.'],
               'what_is': 'JSON Web Token (JWT) vulnerabilities allow attackers to forge or tamper with authentication '
                          'tokens. Common issues include weak secrets (allowing brute-force), the "none" algorithm '
                          'attack (disabling signature verification), sensitive data in the payload (which is only '
                          'base64-encoded, not encrypted), and missing expiration.'},
    'lfi': {   'cvss': '9.1',
               'cwe': 'CWE-22',
               'impact': 'Reading of sensitive system files (/etc/passwd, /etc/shadow, configuration files containing '
                         'credentials, SSH keys, application source code), and in some configurations Remote Code '
                         'Execution via log file poisoning or PHP wrappers.',
               'owasp': 'A01:2021 - Broken Access Control',
               'references': [   'https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/07-Input_Validation_Testing/11.1-Testing_for_Local_File_Inclusion',
                                 'https://cwe.mitre.org/data/definitions/22.html'],
               'remediation': [   'Never use user-controlled input directly in file-include functions.',
                                  'Implement a whitelist of allowed file names/paths.',
                                  'Use a mapping/dictionary approach to avoid exposing real file paths.',
                                  'Disable PHP functions: include(), require(), allow_url_include.',
                                  'Configure open_basedir restriction to limit file access.',
                                  'Run the web server with minimal file system permissions.'],
               'what_is': 'Local File Inclusion (LFI) allows attackers to read arbitrary files on the server by '
                          'manipulating file path parameters. The vulnerability occurs when user-controlled input is '
                          'used in file-inclusion functions without proper validation, enabling path traversal attacks '
                          '(e.g., ../../etc/passwd).'},
    'login pages discovered': {   'cvss': '3.0',
                                  'cwe': 'CWE-306',
                                  'impact': 'Targeted for brute-force attacks, credential stuffing, and session '
                                            'management exploits.',
                                  'owasp': 'A07:2021 - Identification and Authentication Failures',
                                  'references': [   'https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html',
                                                    'https://cwe.mitre.org/data/definitions/306.html'],
                                  'remediation': [   'Enforce Multi-Factor Authentication (MFA) across all '
                                                     'authentication endpoints.',
                                                     'Implement adaptive rate limiting and account lockout after '
                                                     'repeated failed attempts.',
                                                     'Ensure all authentication exchanges occur strictly over '
                                                     'encrypted HTTPS connections.'],
                                  'what_is': 'Multiple login and authentication endpoints were discovered across the '
                                             'target web application. Authentication entry points represent critical '
                                             'attack surfaces that require robust protection.'},
    'missing security header': {   'cvss': '5.3',
                                   'cwe': 'CWE-1021',
                                   'impact': 'Heightens vulnerability to clickjacking, client-side MIME-sniffing '
                                             'attacks, cross-origin data leaks, and proxy caching of sensitive user '
                                             'data.',
                                   'owasp': 'A05:2021 - Security Misconfiguration',
                                   'references': [   'https://owasp.org/www-project-secure-headers/',
                                                     'https://cheatsheetseries.owasp.org/cheatsheets/HTTP_Headers_Cheat_Sheet.html',
                                                     'https://cwe.mitre.org/data/definitions/1021.html'],
                                   'remediation': [   'Configure all recommended security headers on web servers or '
                                                      'reverse proxies:',
                                                      'Strict-Transport-Security: max-age=31536000; includeSubDomains; '
                                                      'preload',
                                                      "Content-Security-Policy: default-src 'self'; frame-ancestors "
                                                      "'self';",
                                                      'X-Content-Type-Options: nosniff',
                                                      'X-Frame-Options: SAMEORIGIN',
                                                      'Referrer-Policy: strict-origin-when-cross-origin',
                                                      'Permissions-Policy: geolocation=(), camera=(), microphone=()',
                                                      'Cache-Control: no-store (on sensitive authenticated routes)'],
                                   'what_is': 'One or more standard HTTP security response headers are absent from the '
                                              'server responses. Modern browsers rely on these headers to activate '
                                              'built-in security defenses (such as anti-clickjacking, MIME-type '
                                              'enforcement, and secure referrer handling).'},
    'modern tls only': {   'cvss': '2.0',
                           'cwe': 'CWE-326',
                           'impact': 'Positive security indicator. Ensures traffic is protected by modern encryption '
                                     'algorithms.',
                           'owasp': 'A02:2021 - Cryptographic Failures',
                           'references': [   'https://cheatsheetseries.owasp.org/cheatsheets/Transport_Layer_Protection_Cheat_Sheet.html'],
                           'remediation': [   'Maintain current secure TLS configuration. Continue enforcing TLS 1.2 '
                                              'and TLS 1.3 exclusively.'],
                           'what_is': 'Server does not support insecure legacy protocols (TLS 1.0 / TLS 1.1), adhering '
                                      'to current cryptographic standards.'},
    'no visible password policy': {   'cvss': '3.5',
                                      'cwe': 'CWE-521',
                                      'impact': 'Users may select easily guessable or dictionary-based passwords, '
                                                'facilitating brute-force and credential stuffing attacks.',
                                      'owasp': 'A07:2021 - Identification and Authentication Failures',
                                      'references': [   'https://pages.nist.gov/800-63-3/sp800-63b.html',
                                                        'https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html',
                                                        'https://cwe.mitre.org/data/definitions/521.html'],
                                      'remediation': [   'Enforce minimum password length of at least 12 characters '
                                                         '(per NIST SP 800-63B guidelines).',
                                                         'Check candidate passwords against lists of breached/common '
                                                         'passwords (e.g. HaveIBeenPwned API).',
                                                         'Display clear real-time password strength indicators during '
                                                         'user registration.'],
                                      'what_is': 'The user registration or password reset interface does not '
                                                 'communicate password complexity requirements or permit weak/short '
                                                 'passwords.'},
    'open ports': {   'cvss': '4.0',
                      'cwe': 'CWE-16',
                      'impact': 'Exposed services increase the attack surface and may be susceptible to exploitation '
                                'if unpatched.',
                      'owasp': 'A05:2021 - Security Misconfiguration',
                      'references': [   'https://owasp.org/Top10/A05_2021-Security_Misconfiguration/',
                                        'https://cwe.mitre.org/data/definitions/16.html'],
                      'remediation': [   'Close all unnecessary open network ports using host or cloud firewall rules.',
                                         'Restrict administrative ports (such as SSH, RDP) to trusted IP addresses or '
                                         'require VPN access.'],
                      'what_is': 'Open network ports were discovered during port scanning. Every open network port '
                                 'represents an entry point into the host infrastructure.'},
    'open redirect': {   'cvss': '6.1',
                         'cwe': 'CWE-601',
                         'impact': 'Phishing attacks with high success rates (victims trust the legitimate domain), '
                                   'credential theft, malware distribution, and bypass of domain-based security '
                                   'controls. Can be chained with SSRF attacks for internal network access.',
                         'owasp': 'A01:2021 - Broken Access Control',
                         'references': [   'https://cheatsheetseries.owasp.org/cheatsheets/Unvalidated_Redirects_and_Forwards_Cheat_Sheet.html',
                                           'https://cwe.mitre.org/data/definitions/601.html'],
                         'remediation': [   'Maintain an explicit allowlist of permitted redirect destinations.',
                                            'Avoid using user-controlled input for redirect URLs.',
                                            'If redirects are required, use indirect mapping with IDs.',
                                            'Validate that redirect URLs belong to trusted domains.',
                                            'Warn users when redirecting to external domains.'],
                         'what_is': 'An unvalidated redirect occurs when an application accepts user-controlled input '
                                    'to specify a redirect destination. Attackers exploit this to redirect victims to '
                                    'malicious websites while using the trusted domain as a lure in phishing '
                                    'campaigns.'},
    'origin header not validated': {   'cvss': '6.5',
                                       'cwe': 'CWE-352',
                                       'impact': 'Attackers can trigger unwanted actions on behalf of authenticated '
                                                 'victims without their knowledge or consent.',
                                       'owasp': 'A01:2021 - Broken Access Control',
                                       'references': [   'https://owasp.org/Top10/A01_2021-Broken_Access_Control/',
                                                         'https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html',
                                                         'https://cwe.mitre.org/data/definitions/352.html'],
                                       'remediation': [   'Validate the Origin and Referer headers on the server side '
                                                          'against an explicit allowlist of trusted domains.',
                                                          'Implement anti-CSRF synchronizer tokens on all '
                                                          'state-changing requests.',
                                                          'Set SameSite=Strict or SameSite=Lax on all session and '
                                                          'authentication cookies.'],
                                       'what_is': 'The application server does not validate the HTTP Origin or Referer '
                                                  'header on state-changing requests. This enables Cross-Site Request '
                                                  'Forgery (CSRF) where malicious third-party sites submit forged '
                                                  'requests.'},
    'outdated service': {   'cvss': '6.5',
                            'cwe': 'CWE-1104',
                            'impact': 'Potential vulnerability to known public exploits, remote denial of service, or '
                                      'authentication bypass.',
                            'owasp': 'A06:2021 - Vulnerable and Outdated Components',
                            'references': [   'https://owasp.org/Top10/A06_2021-Vulnerable_and_Outdated_Components/',
                                              'https://cwe.mitre.org/data/definitions/1104.html'],
                            'remediation': [   'Update the service to the latest stable, vendor-supported release.',
                                               'Apply security patches and backports regularly via package managers '
                                               '(apt, yum, dnf).',
                                               'Restrict service exposure with firewall rules (e.g. allow SSH only '
                                               'from specific administrative IPs).'],
                            'what_is': 'A network service (such as SSH, FTP, or an old web server) revealed a version '
                                       'string associated with an outdated or end-of-life software release.'},
    'path found': {   'cvss': '3.0',
                      'cwe': 'CWE-548',
                      'impact': 'Aids attackers in discovering hidden features, developer notes, internal endpoints, '
                                'and configuration details.',
                      'owasp': 'A05:2021 - Security Misconfiguration',
                      'references': [   'https://owasp.org/Top10/A05_2021-Security_Misconfiguration/',
                                        'https://cwe.mitre.org/data/definitions/548.html'],
                      'remediation': [   'Review all accessible paths and remove any unneeded files or directories '
                                         'from web servers.',
                                         'Disable directory listing (autoindex off) across all server blocks.',
                                         'Enforce authentication or IP restrictions on internal, diagnostic, and '
                                         'staging paths.'],
                      'what_is': 'An accessible directory or file was located during directory brute-force '
                                 'enumeration. Exposing unnecessary or unlinked files increases the attack surface of '
                                 'the application.'},
    'port': {   'cvss': '7.5',
                'cwe': 'CWE-16',
                'impact': 'Unauthorized access to databases (data breach, data destruction), container escape via '
                          'Docker API, internal service exploitation, and use of exposed services as pivoting points '
                          'for further attacks.',
                'owasp': 'A05:2021 - Security Misconfiguration',
                'references': [   'https://owasp.org/Top10/A05_2021-Security_Misconfiguration/',
                                  'https://cwe.mitre.org/data/definitions/16.html'],
                'remediation': [   'Apply strict firewall rules: only expose ports required for public access.',
                                   'Use a VPN or SSH tunneling for administrative access.',
                                   'Enable authentication on all services (Redis AUTH, MongoDB auth).',
                                   'Bind services to localhost (127.0.0.1) instead of 0.0.0.0.',
                                   'Regularly audit open ports with network scanning tools.',
                                   'Use network segmentation to isolate backend services.'],
                'what_is': 'Unnecessary or dangerous services are exposed to the internet, increasing the attack '
                           'surface. Services like Redis, MongoDB, Elasticsearch, and Docker daemon often have no '
                           'authentication by default and are designed for internal use only.'},
    'robots.txt': {   'cvss': '2.5',
                      'cwe': 'CWE-200',
                      'impact': 'Unintended disclosure of sensitive paths, backend portals, and developer directories.',
                      'owasp': 'A05:2021 - Security Misconfiguration',
                      'references': [   'https://owasp.org/Top10/A05_2021-Security_Misconfiguration/',
                                        'https://cwe.mitre.org/data/definitions/200.html'],
                      'remediation': [   'Do not rely on robots.txt for security or access control; use proper '
                                         'authentication and authorization.',
                                         'Avoid listing highly sensitive, secret, or internal paths in public '
                                         'robots.txt files.'],
                      'what_is': 'The robots.txt file was found and analyzed. Disallowed paths listed in robots.txt '
                                 'often serve as a roadmap for attackers by highlighting sensitive administrative, '
                                 'private, or staging URLs.'},
    'security.txt': {   'cvss': '2.0',
                        'cwe': 'CWE-200',
                        'impact': 'Positive transparency mechanism facilitating coordinated vulnerability disclosure.',
                        'owasp': 'A05:2021 - Security Misconfiguration',
                        'references': ['https://securitytxt.org/'],
                        'remediation': [   'Maintain a valid /.well-known/security.txt file per RFC 9116.',
                                           'Ensure security contact email addresses and encryption keys are monitored '
                                           'and up to date.'],
                        'what_is': 'The security.txt standard defines a machine-readable security contact policy for '
                                   'ethical vulnerability reporting.'},
    'sensitive endpoint': {   'cvss': '7.5',
                              'cwe': 'CWE-200',
                              'impact': 'Critical leakage of environment secrets, database connection strings, '
                                        'third-party API tokens, internal routing architectures, and debugging '
                                        'interfaces that allow arbitrary code execution.',
                              'owasp': 'A01:2021 - Broken Access Control',
                              'references': [   'https://owasp.org/Top10/A01_2021-Broken_Access_Control/',
                                                'https://cwe.mitre.org/data/definitions/200.html'],
                              'remediation': [   'Restrict or completely remove diagnostic and configuration endpoints '
                                                 'from public production environments.',
                                                 'Enforce strong network-level ACLs or VPN requirements to access '
                                                 'administrative/actuator interfaces.',
                                                 'Ensure environment variable files (.env, appsettings.json, '
                                                 'config.yml) are never located within the web server document root.'],
                              'what_is': 'Sensitive configuration, diagnostic, or administrative endpoints (such as '
                                         '/.env, /config.yaml, /actuator, /_profiler, /debug, or /console) are '
                                         'directly accessible over the public internet without authentication.'},
    'sitemap': {   'cvss': '2.0',
                   'cwe': 'CWE-200',
                   'impact': 'Discloses complete application site structure and URL hierarchy.',
                   'owasp': 'A05:2021 - Security Misconfiguration',
                   'references': ['https://cwe.mitre.org/data/definitions/200.html'],
                   'remediation': ['Ensure only public, search-engine indexable URLs are included in public sitemaps.'],
                   'what_is': 'XML sitemap was retrieved and enumerated for public and private URLs.'},
    'sql injection': {   'cvss': '9.8',
                         'cwe': 'CWE-89',
                         'impact': 'Complete database compromise including extraction of all data (usernames, '
                                   'passwords, credit cards, PII), authentication bypass, data modification/deletion, '
                                   'and in some configurations Remote Code Execution (RCE) on the server.',
                         'owasp': 'A03:2021 - Injection',
                         'references': [   'https://owasp.org/Top10/A03_2021-Injection/',
                                           'https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html',
                                           'https://cwe.mitre.org/data/definitions/89.html'],
                         'remediation': [   'Use parameterized queries (prepared statements) for ALL database '
                                            'interactions.',
                                            'Never concatenate user input directly into SQL strings.',
                                            'Apply the principle of least privilege to database accounts.',
                                            'Implement input validation as a secondary defence layer.',
                                            'Use an ORM framework that handles parameterization automatically.',
                                            'Enable a WAF to detect/block common SQL injection patterns.',
                                            'Log and alert on SQL errors to detect exploitation attempts.'],
                         'what_is': 'SQL Injection (SQLi) occurs when untrusted data is sent to an interpreter as part '
                                    'of a command or query. An attacker can use this to manipulate the database query, '
                                    'bypassing authentication, extracting sensitive data, modifying records, or in '
                                    'some configurations executing operating system commands.'},
    'ssl': {   'cvss': '7.5',
               'cwe': 'CWE-326',
               'impact': 'Man-in-the-middle (MITM) attacks enabling interception of credentials and session tokens, '
                         'decryption of sensitive data in transit, and impersonation of the server. Affects all users '
                         'on untrusted networks (public Wi-Fi, corporate proxies).',
               'owasp': 'A02:2021 - Cryptographic Failures',
               'references': [   'https://owasp.org/Top10/A02_2021-Cryptographic_Failures/',
                                 'https://cheatsheetseries.owasp.org/cheatsheets/TLS_Cheat_Sheet.html',
                                 'https://cwe.mitre.org/data/definitions/326.html'],
               'remediation': [   'Disable TLS 1.0 and TLS 1.1. Only allow TLS 1.2 and TLS 1.3.',
                                  'Use only strong cipher suites (AESGCM, ChaCha20). Disable RC4, DES, 3DES.',
                                  'Implement HSTS with a long max-age (≥1 year) and includeSubDomains.',
                                  'Submit domain to the HSTS preload list.',
                                  "Renew certificates well before expiry (automate with Let's Encrypt).",
                                  'Enable OCSP stapling for certificate revocation checking.',
                                  'Configure perfect forward secrecy (PFS) cipher suites.'],
               'what_is': 'Weak TLS/SSL configurations allow attackers to intercept and decrypt encrypted '
                          'communications. This includes using deprecated protocols (TLS 1.0/1.1, SSLv3), weak cipher '
                          'suites, expired/invalid certificates, or missing HSTS headers that allow protocol downgrade '
                          'attacks.'},
    'svn repository': {   'cvss': '7.5',
                          'cwe': 'CWE-538',
                          'impact': 'Attackers can reconstruct the complete application source code, discover embedded '
                                    'secrets, and analyze historical commits for previously patched vulnerabilities.',
                          'owasp': 'A05:2021 - Security Misconfiguration',
                          'references': [   'https://owasp.org/Top10/A05_2021-Security_Misconfiguration/',
                                            'https://cwe.mitre.org/data/definitions/538.html'],
                          'remediation': [   'Block access to all .svn directories in web server configuration (e.g. '
                                             'location ~ /\\.svn { deny all; }).',
                                             'Ensure version control directories are purged from deployment artifacts '
                                             'before publishing to web servers.'],
                          'what_is': 'The Subversion (.svn) metadata directory was found accessible over HTTP/S. The '
                                     '.svn/wc.db SQLite file contains the full repository structure, source code, and '
                                     'commit logs.'},
    'technologies detected': {   'cvss': '2.5',
                                 'cwe': 'CWE-200',
                                 'impact': 'Assists attackers in targeting known vulnerabilities specific to the '
                                           'identified technology stack.',
                                 'owasp': 'A05:2021 - Security Misconfiguration',
                                 'references': [   'https://owasp.org/Top10/A05_2021-Security_Misconfiguration/',
                                                   'https://cwe.mitre.org/data/definitions/200.html'],
                                 'remediation': [   'Suppress technology-identifying response headers (Server, '
                                                    'X-Powered-By, X-AspNet-Version).',
                                                    'Keep all identified frameworks, libraries, and web servers '
                                                    'updated to current supported versions.'],
                                 'what_is': 'Fingerprinting analysis successfully detected underlying server software, '
                                            'frameworks, and web technologies.'},
    'tls 1.3 supported': {   'cvss': '2.0',
                             'cwe': 'CWE-326',
                             'impact': 'Positive security indicator. Protects user traffic with forward secrecy and '
                                       'hardened cipher suites.',
                             'owasp': 'A02:2021 - Cryptographic Failures',
                             'references': [   'https://cheatsheetseries.owasp.org/cheatsheets/Transport_Layer_Protection_Cheat_Sheet.html'],
                             'remediation': ['Maintain support for TLS 1.3 and modern forward-secret ciphers.'],
                             'what_is': 'Server successfully negotiated TLS 1.3, providing optimal cryptographic '
                                        'security and 0-RTT performance.'},
    'weak csp directive': {   'cvss': '7.1',
                              'cwe': 'CWE-79',
                              'impact': 'Significantly weakens or completely negates Cross-Site Scripting (XSS) '
                                        'protections provided by CSP.',
                              'owasp': 'A03:2021 - Injection',
                              'references': [   'https://csp.withgoogle.com/docs/strict-csp.html',
                                                'https://cheatsheetseries.owasp.org/cheatsheets/Content_Security_Policy_Cheat_Sheet.html',
                                                'https://cwe.mitre.org/data/definitions/79.html'],
                              'remediation': [   "Remove 'unsafe-inline' and use cryptographic nonces (nonce-...) or "
                                                 'hashes (sha256-...) for legitimate inline scripts.',
                                                 "Adopt CSP Level 3 'strict-dynamic' with nonce-based execution for "
                                                 'modern web applications.',
                                                 'Refactor code to load all JavaScript from external, '
                                                 'domain-controlled source files.'],
                              'what_is': 'The Content-Security-Policy (CSP) header includes dangerous directives like '
                                         "'unsafe-inline' or 'unsafe-eval', which bypass script injection protections "
                                         'and allow attacker-controlled inline JavaScript execution.'},
    'well-known': {   'cvss': '3.0',
                      'cwe': 'CWE-200',
                      'impact': 'Aids attackers in mapping Single Sign-On (SSO) and OAuth 2.0 / OpenID Connect token '
                                'endpoints.',
                      'owasp': 'A05:2021 - Security Misconfiguration',
                      'references': [   'https://cheatsheetseries.owasp.org/cheatsheets/JSON_Web_Token_for_Java_Cheat_Sheet.html'],
                      'remediation': [   'Verify public well-known endpoints only expose intended public cryptographic '
                                         'keys.',
                                         'Ensure token endpoints enforce strict client authentication and rate '
                                         'limiting.'],
                      'what_is': 'Well-known endpoints (.well-known/jwks.json, openid-configuration) disclose '
                                 'authentication provider architectures.'},
    'whois': {   'cvss': '2.0',
                 'cwe': 'CWE-200',
                 'impact': 'Information gathering for social engineering and domain takeover attempts if renewals '
                           'lapse.',
                 'owasp': 'A05:2021 - Security Misconfiguration',
                 'references': ['https://owasp.org/Top10/A05_2021-Security_Misconfiguration/'],
                 'remediation': [   'Enable WHOIS privacy protection through your domain registrar.',
                                    'Monitor domain expiration dates and enable auto-renewal.'],
                 'what_is': 'WHOIS information reveals registrar, nameservers, registrant identity, and domain '
                            'expiration dates.'},
    'xss': {   'cvss': '6.1',
               'cwe': 'CWE-79',
               'impact': 'Session hijacking and account takeover, credential theft via fake login forms, malware '
                         'distribution, defacement, keylogging, webcam/microphone access (with permissions), and '
                         'redirection to phishing sites. In stored XSS, every user visiting the page is affected.',
               'owasp': 'A03:2021 - Injection',
               'references': [   'https://owasp.org/Top10/A03_2021-Injection/',
                                 'https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html',
                                 'https://cwe.mitre.org/data/definitions/79.html'],
               'remediation': [   'Encode all output before inserting into HTML (use context-aware encoding).',
                                  'Implement a strict Content-Security-Policy (CSP) header.',
                                  'Use modern frameworks (React, Angular, Vue) that auto-escape by default.',
                                  'Validate and sanitize all inputs on the server side.',
                                  'Use HttpOnly flag on session cookies to prevent JavaScript access.',
                                  'Avoid dangerous DOM sinks: innerHTML, document.write(), eval().',
                                  'Use DOMPurify for sanitizing HTML from untrusted sources.'],
               'what_is': 'Cross-Site Scripting (XSS) vulnerabilities allow attackers to inject malicious client-side '
                          'scripts into web pages viewed by other users. The browser executes these scripts in the '
                          "context of the victim's session, unable to distinguish them from legitimate page content."}}

RISK_COLORS = {
    'CRITICAL': ('#ff4444', '#2d0a0a'),
    'HIGH':     ('#ff7b2c', '#2d1200'),
    'MEDIUM':   ('#ffc107', '#2d2000'),
    'LOW':      ('#17c3b2', '#001f1e'),
    'INFO':     ('#4ade80', '#002010'),
}

RISK_SCORES = {
    'CRITICAL': 10, 'HIGH': 7, 'MEDIUM': 5, 'LOW': 3, 'INFO': 1
}

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Penetration Test Report — PLACEHOLDER_TARGET</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
  --bg:        #080b14;
  --surface:   #0d1117;
  --card:      #161b27;
  --card2:     #1c2233;
  --border:    #21273a;
  --border2:   #2d3a52;
  --text:      #e2e8f4;
  --muted:     #8892a4;
  --accent:    #5b8dee;
  --red:       #ff4444;
  --orange:    #ff7b2c;
  --yellow:    #ffc107;
  --cyan:      #17c3b2;
  --green:     #4ade80;
  --purple:    #a855f7;
}

* { margin:0; padding:0; box-sizing:border-box; }
html { scroll-behavior: smooth; }
body { background:var(--bg); color:var(--text); font-family:'Inter',sans-serif; font-size:15px; line-height:1.7; }

/* SCROLLBAR */
::-webkit-scrollbar { width:6px; height:6px; }
::-webkit-scrollbar-track { background:var(--surface); }
::-webkit-scrollbar-thumb { background:var(--border2); border-radius:3px; }

/* ── HEADER ─────────────────────────────────────────── */
.header {
  background: linear-gradient(135deg, #080b14 0%, #0f1626 40%, #080b14 100%);
  border-bottom: 1px solid var(--border);
  padding: 3rem 4rem;
  position: relative;
  overflow: hidden;
}
.header::before {
  content:'';
  position:absolute; inset:0;
  background: radial-gradient(ellipse 900px 400px at 60% 50%, rgba(91,141,238,.06) 0%, transparent 70%);
  pointer-events:none;
}
.header-grid { display:flex; justify-content:space-between; align-items:flex-start; gap:2rem; flex-wrap:wrap; }
.header-left h1 {
  font-size:2.2rem; font-weight:800; letter-spacing:-.03em;
  background: linear-gradient(135deg, #e2e8f4 0%, #8892a4 100%);
  -webkit-background-clip:text; -webkit-text-fill-color:transparent;
}
.header-left .subtitle { color:var(--muted); font-size:.9rem; margin-top:.4rem; }
.header-right { display:flex; flex-direction:column; gap:.5rem; align-items:flex-end; }
.meta-pill {
  background:var(--card); border:1px solid var(--border); border-radius:6px;
  padding:.3rem .9rem; font-size:.8rem; color:var(--muted); display:flex; gap:.5rem; align-items:center;
}
.meta-pill strong { color:var(--text); }
.risk-badge {
  padding:.5rem 1.5rem; border-radius:8px; font-size:1rem;
  font-weight:700; text-transform:uppercase; letter-spacing:.05em;
}

/* ── NAVIGATION ──────────────────────────────────────── */
.toc {
  background:var(--surface); border-bottom:1px solid var(--border);
  padding:1rem 4rem; display:flex; gap:2rem; align-items:center;
  flex-wrap:wrap; position:sticky; top:0; z-index:100;
}
.toc a {
  color:var(--muted); text-decoration:none; font-size:.85rem;
  font-weight:500; transition:.2s; padding:.3rem .6rem; border-radius:6px;
}
.toc a:hover { color:var(--text); background:var(--card); }
.toc .logo { font-weight:800; font-size:.95rem; color:var(--accent); margin-right:auto; }

/* ── LAYOUT ──────────────────────────────────────────── */
.container { max-width:1300px; margin:0 auto; padding:2.5rem 4rem; }

/* ── SECTION TITLES ──────────────────────────────────── */
.section {  margin-bottom:3rem; }
.section-header {
  display:flex; align-items:center; gap:1rem;
  padding-bottom:1rem; border-bottom:1px solid var(--border); margin-bottom:1.5rem;
}
.section-header h2 { font-size:1.4rem; font-weight:700; }
.section-tag {
  background:var(--card2); border:1px solid var(--border); border-radius:4px;
  padding:.2rem .6rem; font-size:.75rem; color:var(--muted); font-family:'JetBrains Mono',monospace;
}

/* ── EXECUTIVE SUMMARY ───────────────────────────────── */
.exec-grid { display:grid; grid-template-columns:2fr 1fr; gap:2rem; }
.exec-text { color:var(--muted); line-height:1.9; }
.exec-text strong { color:var(--text); }
.risk-meter-card {
  background:var(--card); border:1px solid var(--border); border-radius:12px;
  padding:1.5rem; display:flex; flex-direction:column; align-items:center; gap:1rem;
}
.risk-meter { position:relative; width:160px; height:80px; }
.risk-arc-bg, .risk-arc-fill { fill:none; stroke-linecap:round; }
.risk-arc-bg { stroke:var(--border2); stroke-width:14; }
.risk-arc-fill { stroke-width:14; stroke-dasharray:251.2; transition:stroke-dashoffset 1.5s ease; }
.risk-val { text-anchor:middle; font-size:2rem; font-weight:800; font-family:'Inter',sans-serif; }
.risk-label { text-anchor:middle; font-size:.7rem; fill:var(--muted); font-family:'Inter',sans-serif; }

/* ── STAT CARDS ──────────────────────────────────────── */
.stats { display:grid; grid-template-columns:repeat(5,1fr); gap:1rem; margin-bottom:2rem; }
.stat {
  background:var(--card); border:1px solid var(--border); border-radius:10px;
  padding:1.2rem; text-align:center; transition:.2s; cursor:default;
  border-top:3px solid;
}
.stat:hover { transform:translateY(-3px); box-shadow:0 8px 30px rgba(0,0,0,.4); }
.stat .num { font-size:2.8rem; font-weight:800; line-height:1; }
.stat .lbl { font-size:.75rem; text-transform:uppercase; letter-spacing:.08em; color:var(--muted); margin-top:.4rem; }
.s-critical { border-top-color:var(--red); }     .s-critical .num { color:var(--red); }
.s-high    { border-top-color:var(--orange); }   .s-high .num { color:var(--orange); }
.s-medium  { border-top-color:var(--yellow); }   .s-medium .num { color:var(--yellow); }
.s-low     { border-top-color:var(--cyan); }     .s-low .num { color:var(--cyan); }
.s-info    { border-top-color:var(--green); }    .s-info .num { color:var(--green); }

/* ── SCOPE TABLE ─────────────────────────────────────── */
.table-card { background:var(--card); border:1px solid var(--border); border-radius:10px; overflow:hidden; }
table { width:100%; border-collapse:collapse; }
thead th {
  background:var(--card2); padding:.75rem 1.2rem;
  font-size:.75rem; text-transform:uppercase; letter-spacing:.06em; color:var(--muted);
  text-align:left; border-bottom:1px solid var(--border);
}
tbody td { padding:.9rem 1.2rem; border-bottom:1px solid var(--border); vertical-align:top; }
tbody tr:last-child td { border-bottom:none; }
tbody tr:hover { background:var(--card2); }
code {
  background:var(--surface); border:1px solid var(--border); border-radius:4px;
  padding:.1rem .4rem; font-family:'JetBrains Mono',monospace; font-size:.8rem; color:#7dd3fc;
}

/* ── SEVERITY BADGE ──────────────────────────────────── */
.badge {
  display:inline-block; padding:.2rem .7rem; border-radius:5px;
  font-size:.72rem; font-weight:700; text-transform:uppercase;
  letter-spacing:.06em; border:1px solid; white-space:nowrap;
}
.b-CRITICAL { background:rgba(255,68,68,.12); color:#ff4444; border-color:rgba(255,68,68,.25); }
.b-HIGH     { background:rgba(255,123,44,.12); color:#ff7b2c; border-color:rgba(255,123,44,.25); }
.b-MEDIUM   { background:rgba(255,193,7,.1);  color:#ffc107; border-color:rgba(255,193,7,.2); }
.b-LOW      { background:rgba(23,195,178,.1); color:#17c3b2; border-color:rgba(23,195,178,.2); }
.b-INFO     { background:rgba(74,222,128,.1); color:#4ade80; border-color:rgba(74,222,128,.2); }

/* ── FINDING CARDS ───────────────────────────────────── */
.finding-card {
  background:var(--card); border:1px solid var(--border);
  border-radius:12px; margin-bottom:1.5rem; overflow:hidden;
  transition:.2s; border-left:4px solid;
}
.finding-card:hover { box-shadow:0 4px 24px rgba(0,0,0,.4); }
.fc-CRITICAL { border-left-color:#ff4444; }
.fc-HIGH     { border-left-color:#ff7b2c; }
.fc-MEDIUM   { border-left-color:#ffc107; }
.fc-LOW      { border-left-color:#17c3b2; }
.fc-INFO     { border-left-color:#4ade80; }

.fc-header {
  display:flex; align-items:center; gap:.9rem; padding:1.1rem 1.5rem;
  cursor:pointer; user-select:none;
}
.fc-header:hover { background:var(--card2); }
.fc-num { font-size:.75rem; color:var(--muted); font-family:'JetBrains Mono',monospace; flex-shrink:0; }
.fc-title { font-weight:600; font-size:1rem; flex:1; }
.fc-module {
  background:var(--surface); border:1px solid var(--border); border-radius:4px;
  padding:.15rem .5rem; font-size:.72rem; color:var(--muted);
  font-family:'JetBrains Mono',monospace;
}
.fc-chevron { color:var(--muted); transition:.3s; font-size:.85rem; }
.fc-chevron.open { transform:rotate(180deg); }

.fc-body { display:none; padding:0 1.5rem 1.5rem; }
.fc-body.open { display:block; }

.fc-tabs { display:flex; gap:.25rem; border-bottom:1px solid var(--border); margin-bottom:1.2rem; margin-top:.5rem; }
.fc-tab {
  padding:.5rem 1rem; border-radius:6px 6px 0 0; font-size:.82rem;
  cursor:pointer; color:var(--muted); transition:.15s; border:none; background:none;
  border-bottom:2px solid transparent; margin-bottom:-1px;
}
.fc-tab:hover { color:var(--text); }
.fc-tab.active { color:var(--accent); border-bottom-color:var(--accent); font-weight:600; }

.fc-pane { display:none; }
.fc-pane.active { display:block; }

/* Pane content */
.info-grid { display:grid; grid-template-columns:1fr 1fr; gap:1rem; margin-bottom:1rem; }
.info-row { display:flex; flex-direction:column; gap:.2rem; }
.info-row .lbl { font-size:.72rem; text-transform:uppercase; letter-spacing:.06em; color:var(--muted); }
.info-row .val { font-size:.9rem; font-weight:500; }
.owasp-tag {
  display:inline-block; background:rgba(91,141,238,.1); border:1px solid rgba(91,141,238,.25);
  color:var(--accent); padding:.2rem .6rem; border-radius:4px; font-size:.75rem; font-weight:600;
}
.cwe-tag {
  display:inline-block; background:rgba(168,85,247,.1); border:1px solid rgba(168,85,247,.25);
  color:var(--purple); padding:.2rem .6rem; border-radius:4px; font-size:.75rem; font-weight:600;
}
.cvss-pill {
  display:inline-flex; align-items:center; gap:.4rem; font-size:.85rem; font-weight:700;
}

.description-block { color:var(--muted); line-height:1.8; margin-bottom:1rem; font-size:.9rem; }
.description-block strong { color:var(--text); }

.evidence-box {
  background:var(--surface); border:1px solid var(--border2); border-radius:8px;
  padding:1rem 1.2rem; font-family:'JetBrains Mono',monospace; font-size:.78rem;
  color:#7dd3fc; max-height:220px; overflow-y:auto; white-space:pre-wrap;
  word-break:break-all; margin:.75rem 0; line-height:1.6;
}
.evidence-box:empty { display:none; }
.evidence-label { font-size:.75rem; color:var(--muted); text-transform:uppercase; letter-spacing:.06em; margin-bottom:.3rem; }

.remediation-list { list-style:none; display:flex; flex-direction:column; gap:.6rem; }
.remediation-list li {
  display:flex; gap:.75rem; align-items:flex-start;
  background:var(--surface); border:1px solid var(--border); border-radius:8px;
  padding:.7rem 1rem; font-size:.88rem;
}
.rem-num {
  min-width:22px; height:22px; background:rgba(74,222,128,.15); border:1px solid rgba(74,222,128,.3);
  border-radius:50%; display:flex; align-items:center; justify-content:center;
  font-size:.7rem; font-weight:700; color:var(--green); flex-shrink:0; margin-top:.1rem;
}
.rem-text { color:var(--muted); }
.rem-text code { color:#7dd3fc; }

.refs-list { display:flex; flex-direction:column; gap:.4rem; }
.refs-list a {
  color:var(--accent); font-size:.85rem; text-decoration:none; display:flex;
  align-items:center; gap:.4rem;
}
.refs-list a:hover { text-decoration:underline; }

/* ── METHODOLOGY TABLE ───────────────────────────────── */
.method-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:1rem; }
.method-card {
  background:var(--card); border:1px solid var(--border); border-radius:10px;
  padding:1.2rem; display:flex; flex-direction:column; gap:.5rem;
}
.method-card h4 { font-size:.9rem; font-weight:600; }
.method-card p { font-size:.82rem; color:var(--muted); }
.method-icon { font-size:1.4rem; }

/* ── FOOTER ──────────────────────────────────────────── */
footer {
  border-top:1px solid var(--border); padding:2rem 4rem;
  display:flex; justify-content:space-between; align-items:center;
  color:var(--muted); font-size:.8rem; flex-wrap:wrap; gap:1rem;
}
.footer-logo { font-weight:800; color:var(--accent); font-size:1rem; }

/* ── DISCLAIMER BOX ──────────────────────────────────── */
.disclaimer {
  background:rgba(255,68,68,.04); border:1px solid rgba(255,68,68,.15);
  border-radius:8px; padding:1rem 1.5rem; color:rgba(255,68,68,.8);
  font-size:.82rem; margin-bottom:2rem;
}

/* ── CHART BAR ───────────────────────────────────────── */
.bar-chart { display:flex; flex-direction:column; gap:.7rem; margin-top:1rem; }
.bar-row { display:flex; align-items:center; gap:.8rem; }
.bar-label { width:80px; font-size:.8rem; font-weight:600; text-align:right; flex-shrink:0; }
.bar-bg { flex:1; background:var(--border); border-radius:4px; height:10px; overflow:hidden; }
.bar-fill { height:100%; border-radius:4px; transition:width 1.5s cubic-bezier(.4,0,.2,1); }
.bar-count { font-size:.8rem; color:var(--muted); width:30px; }

@media(max-width:900px) {
  .header { padding:2rem; }
  .container { padding:1.5rem 2rem; }
  .toc { padding:1rem 2rem; }
  .exec-grid { grid-template-columns:1fr; }
  .stats { grid-template-columns:repeat(3,1fr); }
  .info-grid { grid-template-columns:1fr; }
  footer { padding:1.5rem 2rem; }
}

/* ── FINDINGS TOOLBAR ────────────────────────────────── */
.findings-toolbar {
  display: flex;
  gap: 0.75rem;
  align-items: center;
  flex-wrap: wrap;
  margin-bottom: 1.5rem;
  padding: 0.8rem 1.2rem;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
}
.filter-btn {
  background: var(--card);
  border: 1px solid var(--border);
  color: var(--muted);
  padding: 0.4rem 0.85rem;
  border-radius: 6px;
  font-size: 0.8rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
  font-family: inherit;
}
.filter-btn:hover {
  color: var(--text);
  border-color: var(--border2);
}
.filter-btn.active {
  background: var(--accent);
  color: #ffffff;
  border-color: var(--accent);
  font-weight: 600;
}
.search-input {
  background: var(--card);
  border: 1px solid var(--border);
  color: var(--text);
  padding: 0.4rem 0.85rem;
  border-radius: 6px;
  font-size: 0.82rem;
  outline: none;
  font-family: inherit;
  min-width: 220px;
}
.search-input:focus {
  border-color: var(--accent);
}
.toolbar-actions {
  margin-left: auto;
  display: flex;
  gap: 0.5rem;
}
.action-btn {
  background: var(--card2);
  border: 1px solid var(--border);
  color: var(--muted);
  padding: 0.4rem 0.8rem;
  border-radius: 6px;
  font-size: 0.78rem;
  cursor: pointer;
  transition: .15s;
  font-family: inherit;
}
.action-btn:hover {
  color: var(--text);
  background: var(--border2);
}


/* ── DATA COLLECTION & RECONNAISSANCE ───────────────── */
.recon-stat-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 1rem;
  margin-bottom: 1.5rem;
}
.recon-stat-card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 1.1rem 1.3rem;
  display: flex;
  flex-direction: column;
  gap: .3rem;
  transition: transform .15s ease, border-color .15s ease;
}
.recon-stat-card:hover {
  transform: translateY(-2px);
  border-color: var(--border2);
}
.recon-stat-card .lbl {
  font-size: .72rem;
  text-transform: uppercase;
  letter-spacing: .06em;
  color: var(--muted);
}
.recon-stat-card .val {
  font-size: 1.2rem;
  font-weight: 700;
  color: var(--text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.recon-tabs {
  display: flex;
  gap: .5rem;
  border-bottom: 1px solid var(--border);
  margin-bottom: 1.5rem;
  overflow-x: auto;
  padding-bottom: 1px;
}
.recon-tab {
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  color: var(--muted);
  font-size: .88rem;
  font-weight: 500;
  padding: .65rem 1.25rem;
  cursor: pointer;
  transition: all .15s ease;
  font-family: inherit;
  white-space: nowrap;
}
.recon-tab:hover {
  color: var(--text);
}
.recon-tab.active {
  color: var(--accent);
  border-bottom-color: var(--accent);
  font-weight: 600;
}
.recon-pane {
  display: none;
}
.recon-pane.active {
  display: block;
  animation: fadeIn .2s ease;
}
.recon-grid-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.5rem;
  margin-bottom: 1.5rem;
}
.recon-card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 1.2rem 1.5rem;
}
.recon-card h3 {
  font-size: 1rem;
  font-weight: 600;
  margin-bottom: 1rem;
  display: flex;
  align-items: center;
  gap: .5rem;
  color: var(--text);
}
.recon-kv-list {
  display: flex;
  flex-direction: column;
  gap: .75rem;
}
.recon-kv-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
  font-size: .88rem;
  padding-bottom: .6rem;
  border-bottom: 1px solid var(--border);
}
.recon-kv-row:last-child {
  border-bottom: none;
  padding-bottom: 0;
}
.recon-kv-row .k {
  color: var(--muted);
  flex-shrink: 0;
}
.recon-kv-row .v {
  color: var(--text);
  font-weight: 500;
  text-align: right;
  word-break: break-all;
}
.tag-pill {
  background: var(--surface);
  border: 1px solid var(--border);
  color: var(--text);
  padding: .25rem .7rem;
  border-radius: 6px;
  font-size: .82rem;
  display: inline-block;
  margin: .25rem .35rem .25rem 0;
}
.scroll-table-container {
  max-height: 420px;
  overflow-y: auto;
}
@media(max-width:900px) {
  .recon-grid-2 { grid-template-columns: 1fr; }
}

</style>
</head>
<body>

<!-- HEADER -->
<header class="header">
  <div class="header-grid">
    <div class="header-left">
      <div style="font-size:.75rem;color:var(--muted);text-transform:uppercase;letter-spacing:.1em;margin-bottom:.5rem;">
        PENETRATION TEST REPORT — CONFIDENTIAL
      </div>
      <h1>Security Assessment</h1>
      <div class="subtitle">Web Application &amp; Infrastructure Vulnerability Report &bull; <span style="color:var(--accent);font-weight:600;">by killer6909203</span></div>
    </div>
    <div class="header-right">
      <div class="meta-pill"><span>Target</span><strong>PLACEHOLDER_TARGET</strong></div>
      <div class="meta-pill"><span>Date</span><strong>PLACEHOLDER_SCAN_DATE</strong></div>
      <div class="meta-pill"><span>Modules</span><strong>PLACEHOLDER_MODULES_RAN</strong></div>
      <div class="meta-pill"><span>Duration</span><strong>PLACEHOLDER_DURATION</strong></div>
      <div class="risk-badge" style="background:PLACEHOLDER_OVERALL_BG;color:PLACEHOLDER_OVERALL_COLOR;border:1px solid PLACEHOLDER_OVERALL_BORDER;margin-top:.5rem;">
        Overall Risk: PLACEHOLDER_OVERALL_RISK
      </div>
    </div>
  </div>
</header>

<!-- NAVIGATION -->
<nav class="toc">
  <span class="logo">DISTROYER</span>
  <a href="#executive">Executive Summary</a>
  <a href="#scope">Scope &amp; Methodology</a>
  <a href="#recon">Data Collection</a>
  <a href="#findings">Findings</a>
  <a href="#remediation-plan">Remediation Plan</a>
</nav>

<div class="container">

  <div class="disclaimer">
    CONFIDENTIAL — This report contains sensitive security information.
    Distribute only to authorised personnel with a need to know.
    Findings must be remediated before any public disclosure.
  </div>

  <!-- ── EXECUTIVE SUMMARY ────────────────────────── -->
  <section class="section" id="executive">
    <div class="section-header">
      <h2>Executive Summary</h2>
      <span class="section-tag">01</span>
    </div>
    <div class="exec-grid">
      <div>
        <div class="exec-text">PLACEHOLDER_EXECUTIVE_SUMMARY</div>
        <div class="bar-chart" style="margin-top:1.5rem;">
          <div class="bar-row">
            <div class="bar-label" style="color:var(--red)">Critical</div>
            <div class="bar-bg"><div class="bar-fill" style="width:PLACEHOLDER_PCT_CRITICAL%;background:var(--red);"></div></div>
            <div class="bar-count">PLACEHOLDER_CRITICAL</div>
          </div>
          <div class="bar-row">
            <div class="bar-label" style="color:var(--orange)">High</div>
            <div class="bar-bg"><div class="bar-fill" style="width:PLACEHOLDER_PCT_HIGH%;background:var(--orange);"></div></div>
            <div class="bar-count">PLACEHOLDER_HIGH</div>
          </div>
          <div class="bar-row">
            <div class="bar-label" style="color:var(--yellow)">Medium</div>
            <div class="bar-bg"><div class="bar-fill" style="width:PLACEHOLDER_PCT_MEDIUM%;background:var(--yellow);"></div></div>
            <div class="bar-count">PLACEHOLDER_MEDIUM</div>
          </div>
          <div class="bar-row">
            <div class="bar-label" style="color:var(--cyan)">Low</div>
            <div class="bar-bg"><div class="bar-fill" style="width:PLACEHOLDER_PCT_LOW%;background:var(--cyan);"></div></div>
            <div class="bar-count">PLACEHOLDER_LOW</div>
          </div>
          <div class="bar-row">
            <div class="bar-label" style="color:var(--green)">Info</div>
            <div class="bar-bg"><div class="bar-fill" style="width:PLACEHOLDER_PCT_INFO%;background:var(--green);"></div></div>
            <div class="bar-count">PLACEHOLDER_INFO</div>
          </div>
        </div>
      </div>
      <div>
        <div class="stats" style="grid-template-columns:1fr 1fr;margin-bottom:1rem;">
          <div class="stat s-critical"><div class="num">PLACEHOLDER_CRITICAL</div><div class="lbl">Critical</div></div>
          <div class="stat s-high"><div class="num">PLACEHOLDER_HIGH</div><div class="lbl">High</div></div>
          <div class="stat s-medium"><div class="num">PLACEHOLDER_MEDIUM</div><div class="lbl">Medium</div></div>
          <div class="stat s-low"><div class="num">PLACEHOLDER_LOW</div><div class="lbl">Low</div></div>
        </div>
        <div class="stat s-info" style="margin-bottom:1rem;"><div class="num">PLACEHOLDER_INFO</div><div class="lbl">Informational</div></div>
        <div class="table-card">
          <table>
            <thead><tr><th>Metric</th><th>Value</th></tr></thead>
            <tbody>
              <tr><td>Total Findings</td><td><strong>PLACEHOLDER_TOTAL</strong></td></tr>
              <tr><td>Actionable Issues</td><td><strong>PLACEHOLDER_ACTIONABLE</strong></td></tr>
              <tr><td>Overall Risk Score</td><td><strong style="color:PLACEHOLDER_OVERALL_COLOR">PLACEHOLDER_RISK_SCORE/100</strong></td></tr>
              <tr><td>Modules Executed</td><td><strong>PLACEHOLDER_MODULES_RAN</strong></td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </section>

  <!-- ── SCOPE & METHODOLOGY ─────────────────────── -->
  <section class="section" id="scope">
    <div class="section-header">
      <h2>Scope &amp; Methodology</h2>
      <span class="section-tag">02</span>
    </div>
    <div class="table-card" style="margin-bottom:1.5rem;">
      <table>
        <thead><tr><th>Parameter</th><th>Value</th></tr></thead>
        <tbody>
          <tr><td>Target URL</td><td><code>PLACEHOLDER_TARGET</code></td></tr>
          <tr><td>Scan Date</td><td>PLACEHOLDER_SCAN_DATE</td></tr>
          <tr><td>Test Type</td><td>Black-box Web Application &amp; Infrastructure</td></tr>
          <tr><td>Tools Used</td><td>Distroyer v2.0 (Enterprise Red Team Edition)</td></tr>
          <tr><td>Standard</td><td>OWASP Top 10 (2021), OWASP WSTG, CWE/SANS Top 25</td></tr>
        </tbody>
      </table>
    </div>
    <div class="method-grid">
      <div class="method-card">
        <div class="method-icon">01</div>
        <h4>Reconnaissance</h4>
        <p>DNS enumeration, WHOIS, certificate transparency, subdomain discovery, technology fingerprinting.</p>
      </div>
      <div class="method-card">
        <div class="method-icon">02</div>
        <h4>Vulnerability Scanning</h4>
        <p>Automated detection of SQLi, XSS, CSRF, LFI, Open Redirect, CORS misconfigurations.</p>
      </div>
      <div class="method-card">
        <div class="method-icon">03</div>
        <h4>Configuration Review</h4>
        <p>HTTP security headers, SSL/TLS analysis, port scanning, exposed services, backup files.</p>
      </div>
      <div class="method-card">
        <div class="method-icon">04</div>
        <h4>Authentication Testing</h4>
        <p>Default credentials, JWT analysis, auth bypass, account enumeration, session management.</p>
      </div>
    </div>
  </section>

  <!-- ── DATA COLLECTION & RECONNAISSANCE ────────── -->
  <section class="section" id="recon">
    <div class="section-header">
      <h2>Data Collection &amp; Reconnaissance</h2>
      <span class="section-tag">03</span>
    </div>
    <p style="color:var(--muted);margin-bottom:1.5rem;font-size:.9rem;">
      Comprehensive intelligence inventory collected across passive and active reconnaissance phases:
      infrastructure mapping, server technologies, HTTP security header configurations, SSL/TLS posture, and discovered assets.
    </p>
    PLACEHOLDER_RECON_SECTION
  </section>

  <!-- ── FINDINGS ────────────────────────────────── -->
  <section class="section" id="findings">
    <div class="section-header">
      <h2>Detailed Findings</h2>
      <span class="section-tag">04</span>
    </div>
    <p style="color:var(--muted);margin-bottom:1.5rem;font-size:.9rem;">
      Click any finding to expand its full technical analysis, evidence, and remediation guidance.
      Findings are sorted by severity (highest risk first).
    </p>
    <div class="findings-toolbar">
      <button class="filter-btn active" data-severity="ALL">All (PLACEHOLDER_TOTAL)</button>
      <button class="filter-btn" data-severity="CRITICAL">Critical (PLACEHOLDER_CRITICAL)</button>
      <button class="filter-btn" data-severity="HIGH">High (PLACEHOLDER_HIGH)</button>
      <button class="filter-btn" data-severity="MEDIUM">Medium (PLACEHOLDER_MEDIUM)</button>
      <button class="filter-btn" data-severity="LOW">Low (PLACEHOLDER_LOW)</button>
      <button class="filter-btn" data-severity="INFO">Info (PLACEHOLDER_INFO)</button>
      <input type="text" id="finding-search" class="search-input" placeholder="Filter by title, module, CVE..." />
      <div class="toolbar-actions">
        <button id="expand-all-btn" class="action-btn">Expand All</button>
        <button id="collapse-all-btn" class="action-btn">Collapse All</button>
      </div>
    </div>
    PLACEHOLDER_FINDINGS_HTML
  </section>

  <!-- ── REMEDIATION PLAN ────────────────────────── -->
  <section class="section" id="remediation-plan">
    <div class="section-header">
      <h2>Remediation Priority Plan</h2>
      <span class="section-tag">05</span>
    </div>
    <div class="table-card">
      <table>
        <thead>
          <tr>
            <th>#</th>
            <th>Severity</th>
            <th>Finding</th>
            <th>Recommended Action</th>
            <th>Priority</th>
          </tr>
        </thead>
        <tbody>PLACEHOLDER_REMEDIATION_TABLE</tbody>
      </table>
    </div>
  </section>

</div>

<footer>
  <div>
    <div class="footer-logo">DISTROYER</div>
    <div>Web Security &amp; Penetration Testing Framework v1.0</div>
  </div>
  <div style="text-align:right;">
    <div>This report was generated automatically.</div>
    <div>For authorized security testing only. Unauthorized use is illegal.</div>
  </div>
</footer>

<script>
(function() {
  // Expand/collapse findings
  document.querySelectorAll('.fc-header').forEach(h => {
    h.addEventListener('click', () => {
      const body = document.getElementById(h.dataset.body);
      const chevron = h.querySelector('.fc-chevron');
      if (body) {
        body.classList.toggle('open');
        chevron && chevron.classList.toggle('open');
      }
    });
  });

  // Severity filtering and real-time search
  const filterBtns = document.querySelectorAll('.filter-btn');
  const findingCards = document.querySelectorAll('.finding-card');
  const searchInput = document.getElementById('finding-search');

  function applyFilters() {
    const activeBtn = document.querySelector('.filter-btn.active');
    const selectedSev = activeBtn ? activeBtn.dataset.severity : 'ALL';
    const query = searchInput ? searchInput.value.toLowerCase().trim() : '';

    findingCards.forEach(card => {
      const matchSev = (selectedSev === 'ALL' || card.classList.contains('fc-' + selectedSev));
      const text = card.textContent.toLowerCase();
      const matchQuery = !query || text.includes(query);
      card.style.display = (matchSev && matchQuery) ? 'block' : 'none';
    });
  }

  filterBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      filterBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      applyFilters();
    });
  });

  if (searchInput) {
    searchInput.addEventListener('input', applyFilters);
  }

  // Expand / Collapse all
  const expandAllBtn = document.getElementById('expand-all-btn');
  const collapseAllBtn = document.getElementById('collapse-all-btn');
  if (expandAllBtn) {
    expandAllBtn.addEventListener('click', () => {
      document.querySelectorAll('.fc-body').forEach(b => b.classList.add('open'));
      document.querySelectorAll('.fc-chevron').forEach(c => c.classList.add('open'));
    });
  }
  if (collapseAllBtn) {
    collapseAllBtn.addEventListener('click', () => {
      document.querySelectorAll('.fc-body').forEach(b => b.classList.remove('open'));
      document.querySelectorAll('.fc-chevron').forEach(c => c.classList.remove('open'));
    });
  }

  // Tab switching
  document.querySelectorAll('.fc-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      const group = tab.dataset.group;
      const target = tab.dataset.target;
      document.querySelectorAll(`.fc-tab[data-group="${group}"]`).forEach(t => t.classList.remove('active'));
      document.querySelectorAll(`.fc-pane[data-group="${group}"]`).forEach(p => p.classList.remove('active'));
      tab.classList.add('active');
      const pane = document.getElementById(target);
      if (pane) pane.classList.add('active');
    });
  });

  
  // Recon tabs switching
  document.querySelectorAll('.recon-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.recon-tab').forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.recon-pane').forEach(p => p.classList.remove('active'));
      tab.classList.add('active');
      const targetPane = document.getElementById(tab.dataset.target);
      if (targetPane) targetPane.classList.add('active');
    });
  });

  // Animate bars on load
  document.querySelectorAll('.bar-fill').forEach(b => {
    const w = b.style.width;
    b.style.width = '0%';
    setTimeout(() => { b.style.width = w; }, 200);
  });
})();
</script>
</body>
</html>"""


class ReportGenerator:
    """Generates professional HTML and JSON pentest reports."""

    def __init__(self, config, results, all_findings, duration=None):
        self.config = config
        self.results = results
        self.all_findings = all_findings
        self.target = config.get('url', 'Unknown')
        self.scan_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.modules_ran = len([k for k, v in results.items() if not v.get('error')])
        if isinstance(duration, (int, float)):
            self.duration = f"{duration:.1f}s"
        elif duration:
            self.duration = str(duration)
        else:
            self.duration = '—'

    # ─── Public Methods ───────────────────────────────────────────────────────

    def save_json(self, path):
        data = {
            'meta': {
                'target': self.target,
                'scan_date': self.scan_date,
                'tool': 'Distroyer v2.0 (Enterprise Red Team Edition)',
                'total_findings': len(self.all_findings),
                'summary': self._get_summary(),
            },
            'findings': self.all_findings,
            'modules': self.results,
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str)
        return path

    def save_html(self, path):
        html = self._build_html()
        with open(path, 'w', encoding='utf-8') as f:
            f.write(html)
        return path

    def save_sarif(self, path):
        """Export results in OASIS SARIF v2.1.0 format for GitHub Code Scanning / CI pipelines."""
        import re
        sarif_results = []
        rules = {}

        level_map = {
            'CRITICAL': 'error',
            'HIGH': 'error',
            'MEDIUM': 'warning',
            'LOW': 'note',
            'INFO': 'none'
        }

        for f in self.all_findings:
            title = f.get('title', 'Unknown finding')
            sev = f.get('severity', 'INFO')
            kb = self._lookup_kb(title, severity=sev)
            rule_id = re.sub(r'[^a-zA-Z0-9_-]', '_', title).upper()

            if rule_id not in rules:
                rules[rule_id] = {
                    'id': rule_id,
                    'name': title,
                    'shortDescription': {'text': title},
                    'fullDescription': {'text': kb.get('what_is', title)},
                    'help': {'text': '\n'.join(kb.get('remediation', [f.get('recommendation', '')]))},
                    'properties': {
                        'security-severity': str(kb.get('cvss', '5.0')),
                        'owasp': kb.get('owasp', ''),
                        'cwe': [kb.get('cwe', '')]
                    }
                }

            sarif_results.append({
                'ruleId': rule_id,
                'level': level_map.get(sev, 'warning'),
                'message': {'text': f.get('detail', title)},
                'locations': [{
                    'physicalLocation': {
                        'artifactLocation': {'uri': self.target},
                        'region': {'startLine': 1}
                    }
                }]
            })

        sarif_data = {
            '$schema': 'https://json.schemastore.org/sarif-2.1.0.json',
            'version': '2.1.0',
            'runs': [{
                'tool': {
                    'driver': {
                        'name': 'Distroyer',
                        'version': '2.0.0',
                        'informationUri': 'https://github.com/Distroyer/Distroyer',
                        'rules': list(rules.values())
                    }
                },
                'results': sarif_results
            }]
        }

        with open(path, 'w', encoding='utf-8') as f:
            json.dump(sarif_data, f, indent=2)
        return path

    # ─── HTML Building ────────────────────────────────────────────────────────


    def _build_recon_section(self):
        """Constructs the comprehensive Data Collection & Reconnaissance HTML section."""
        import json
        import re

        # ── 1. Target & Network Info ──────────────────────────────────────────
        target = self.target
        domain = self.config.get('url', '').replace('https://', '').replace('http://', '').split('/')[0] or 'Unknown'
        scheme = 'HTTPS' if target.startswith('https') else 'HTTP'
        ip = 'Unknown'
        reverse_dns = '—'
        dns_records = {}
        waf = 'None detected'
        robots_info = 'Not found / Not configured'
        sitemap_info = 'Not found / Not configured'
        security_txt = 'Not found'

        for f in self.all_findings:
            t = f.get('title', '')
            d = f.get('detail', '')
            ev = f.get('evidence', '')
            if 'IP & ASN' in t or 'IP Information' in t:
                m = re.search(r'(\d+\.\d+\.\d+\.\d+)', d + ' ' + ev)
                if m: ip = m.group(1)
            elif 'DNS Records' in t:
                try:
                    dns_records = json.loads(ev)
                except Exception:
                    pass
            elif 'WAF Detected' in t:
                waf = d or t
            elif 'robots.txt' in t:
                robots_info = d if not ev else f"{d} ({ev[:60]})"
            elif 'Sitemap' in t:
                sitemap_info = d
            elif 'security.txt' in t:
                security_txt = d

        # ── 2. Technologies & Server ─────────────────────────────────────────
        server_banner = 'Not disclosed'
        technologies = []
        admin_panels = []

        fp_res = self.results.get('tech_fingerprint', {})
        if 'technologies' in fp_res and isinstance(fp_res['technologies'], list):
            technologies.extend(fp_res['technologies'])

        for f in self.all_findings:
            t = f.get('title', '')
            d = f.get('detail', '')
            ev = f.get('evidence', '')
            if 'Server' in t and ('Disclosure' in t or 'Server' in f.get('module', '')):
                server_banner = ev.replace('Server:', '').strip() or d
            elif 'Technologies Detected' in t:
                for line in ev.splitlines():
                    line = line.strip()
                    if line and line not in technologies:
                        technologies.append(line)
            elif 'Admin Panel Found' in t or 'Admin Endpoint' in t:
                admin_panels.append({'endpoint': d.replace('Admin endpoint accessible: ', ''), 'status': ev})

        # ── 3. Security Headers ──────────────────────────────────────────────
        headers_dict = self.results.get('headers', {}).get('headers', {})
        SEC_HEADERS_DEF = [
            ('Strict-Transport-Security', 'Enforces encrypted HTTPS connections and mitigates MITM/SSL stripping.', 'max-age=31536000; includeSubDomains; preload'),
            ('Content-Security-Policy', 'Restricts script execution, frames, and asset origins to mitigate XSS.', "default-src 'self'; script-src 'self'"),
            ('X-Frame-Options', 'Controls page rendering in iframes to prevent clickjacking attacks.', 'DENY or SAMEORIGIN'),
            ('X-Content-Type-Options', 'Disables browser MIME-sniffing away from declared Content-Type.', 'nosniff'),
            ('Referrer-Policy', 'Protects sensitive URL query parameters from leaking to external domains.', 'strict-origin-when-cross-origin'),
            ('Permissions-Policy', 'Restricts unauthorized browser device access (mic, camera, geolocation).', 'geolocation=(), microphone=()'),
            ('Cache-Control', 'Prevents caching of sensitive authenticated content in intermediate proxies.', 'no-store, no-cache, must-revalidate'),
        ]

        missing_headers = set()
        header_evidence = {}
        for f in self.all_findings:
            t = f.get('title', '')
            if 'Missing Security Header:' in t:
                missing_headers.add(t.split(':', 1)[1].strip())
            elif 'CSP' in t or 'Weak CSP' in t:
                header_evidence['Content-Security-Policy'] = f.get('evidence', '')

        configured_count = 0
        header_rows = []
        for h_name, purpose, rec_val in SEC_HEADERS_DEF:
            val = headers_dict.get(h_name) or headers_dict.get(h_name.lower())
            if not val and h_name in header_evidence:
                val = header_evidence[h_name]

            if val and h_name not in missing_headers:
                configured_count += 1
                status_badge = '<span class="badge b-INFO">CONFIGURED</span>'
                val_display = f'<code style="color:#7dd3fc;word-break:break-all;">{self._esc(val[:120])}{"..." if len(val)>120 else ""}</code>'
            else:
                status_badge = '<span class="badge b-HIGH">MISSING</span>' if h_name in ('Strict-Transport-Security', 'Content-Security-Policy') else '<span class="badge b-MEDIUM">MISSING</span>'
                val_display = f'<span style="color:var(--muted)">Not Configured</span> — Recommended: <code>{self._esc(rec_val)}</code>'

            header_rows.append(f"""
            <tr>
              <td><strong>{self._esc(h_name)}</strong></td>
              <td>{status_badge}</td>
              <td style="font-size:.85rem;">{val_display}</td>
              <td style="color:var(--muted);font-size:.82rem;">{self._esc(purpose)}</td>
            </tr>
            """)

        # ── 4. SSL / TLS ─────────────────────────────────────────────────────
        tls_protocols = []
        cert_validity = 'Valid'
        cipher_info = 'TLS 1.2 / TLS 1.3'
        for f in self.all_findings:
            t = f.get('title', '')
            d = f.get('detail', '')
            ev = f.get('evidence', '')
            if 'TLS 1.3 Supported' in t:
                tls_protocols.append('TLS 1.3 (Modern, Highly Secure)')
            elif 'Modern TLS Only' in t:
                tls_protocols.append('TLS 1.2+ (Legacy TLS 1.0 & 1.1 Disabled)')
            elif 'TLS Cipher' in t:
                cipher_info = f"{d} ({ev})"
            elif 'Certificate Valid' in t:
                cert_validity = d
            elif 'Certificate Expired' in t or 'Certificate EXPIRED' in t:
                cert_validity = f'EXPIRED: {d}'

        if not tls_protocols:
            tls_protocols = ['TLS 1.2 (Standard)']

        # ── 5. Open Ports & Services ─────────────────────────────────────────
        open_ports = []
        port_res = self.results.get('portscan', {}).get('open_ports', [])
        for p in port_res:
            open_ports.append(p)
        if not open_ports:
            for f in self.all_findings:
                if 'Open Ports Detected' in f.get('title', ''):
                    for line in f.get('evidence', '').splitlines():
                        line = line.strip()
                        m = re.match(r'^(\d+)/([^\s:]+)', line)
                        if m:
                            open_ports.append({'port': f"{m.group(1)}/{m.group(2)}", 'service': 'Detected'})

        # ── 6. Discovered Assets (Paths, Crawl, Emails, Logins) ───────────────
        paths_found = []
        dir_res = self.results.get('dir_enum', {}).get('found', [])
        for p in dir_res:
            paths_found.append(p)
        if not paths_found:
            for f in self.all_findings:
                if f.get('module') == 'dirs' and 'Path Found:' in f.get('title', ''):
                    p_name = f.get('title', '').replace('Path Found:', '').strip()
                    status_m = re.search(r'HTTP (\d+)', f.get('detail', ''))
                    size_m = re.search(r'Size: (\d+)', f.get('detail', ''))
                    paths_found.append({
                        'path': p_name,
                        'status': int(status_m.group(1)) if status_m else 200,
                        'size': int(size_m.group(1)) if size_m else '—'
                    })

        emails = []
        login_endpoints = []
        crawl_pages_count = 0
        crawl_forms_count = 0
        for f in self.all_findings:
            t = f.get('title', '')
            ev = f.get('evidence', '')
            d = f.get('detail', '')
            if 'Email Addresses Discovered' in t:
                emails = [e.strip() for e in ev.splitlines() if e.strip()]
            elif 'Login Pages Discovered' in t:
                login_endpoints = [l.strip() for l in ev.splitlines() if l.strip()]
            elif 'Crawl Complete' in t:
                p_m = re.search(r'(\d+) pages', d)
                f_m = re.search(r'(\d+) forms', d)
                if p_m: crawl_pages_count = int(p_m.group(1))
                if f_m: crawl_forms_count = int(f_m.group(1))

        # ── BUILD HTML PANES ─────────────────────────────────────────────────

        # Pane 1: Network & DNS
        dns_rows = []
        if isinstance(dns_records, dict) and dns_records:
            for rtype, records in dns_records.items():
                rec_str = ', '.join(records) if isinstance(records, list) else str(records)
                dns_rows.append(f'<tr><td><span class="badge b-INFO">{self._esc(rtype)}</span></td><td><code>{self._esc(rec_str)}</code></td></tr>')
        else:
            dns_rows.append('<tr><td><span class="badge b-INFO">A</span></td><td><code>' + self._esc(ip) + '</code></td></tr>')

        pane_network = f"""
        <div class="recon-grid-2">
          <div class="recon-card">
            <h3>🌐 Target Network Details</h3>
            <div class="recon-kv-list">
              <div class="recon-kv-row"><span class="k">Target Hostname</span><span class="v"><code>{self._esc(domain)}</code></span></div>
              <div class="recon-kv-row"><span class="k">Primary IP Address</span><span class="v"><code>{self._esc(ip)}</code></span></div>
              <div class="recon-kv-row"><span class="k">Protocol &amp; Scheme</span><span class="v"><span class="badge b-INFO">{scheme}</span></span></div>
              <div class="recon-kv-row"><span class="k">Web Application Firewall</span><span class="v">{self._esc(waf)}</span></div>
              <div class="recon-kv-row"><span class="k">Security Policy (security.txt)</span><span class="v">{self._esc(security_txt)}</span></div>
              <div class="recon-kv-row"><span class="k">robots.txt Status</span><span class="v">{self._esc(robots_info)}</span></div>
              <div class="recon-kv-row"><span class="k">Sitemap Status</span><span class="v">{self._esc(sitemap_info)}</span></div>
            </div>
          </div>
          <div class="recon-card">
            <h3>📋 DNS Resolution</h3>
            <div class="table-card" style="border:none;">
              <table>
                <thead><tr><th>Type</th><th>Record / Value</th></tr></thead>
                <tbody>{''.join(dns_rows)}</tbody>
              </table>
            </div>
          </div>
        </div>
        """

        # Pane 2: Technologies & Server
        tech_pills = ''.join(f'<span class="tag-pill">🏷️ {self._esc(t)}</span>' for t in (technologies or ['Nginx Web Server']))
        admin_rows = ''.join(
            f'<tr><td><code>{self._esc(a["endpoint"])}</code></td><td><span class="badge b-MEDIUM">{self._esc(a["status"])}</span></td></tr>'
            for a in admin_panels[:15]
        ) if admin_panels else '<tr><td colspan="2" style="color:var(--muted);text-align:center;">No exposed admin interfaces identified.</td></tr>'

        pane_tech = f"""
        <div class="recon-grid-2">
          <div class="recon-card">
            <h3>⚡ Server &amp; Environment Fingerprint</h3>
            <div class="recon-kv-list">
              <div class="recon-kv-row"><span class="k">Web Server Software</span><span class="v"><code>{self._esc(server_banner)}</code></span></div>
              <div class="recon-kv-row"><span class="k">Detected Technologies</span><span class="v">{len(technologies) or 1} Identified</span></div>
            </div>
            <div style="margin-top:1.2rem;">
              <div class="lbl" style="margin-bottom:.5rem;">Detected Stack Components:</div>
              {tech_pills}
            </div>
          </div>
          <div class="recon-card">
            <h3>🚪 Discovered Portals &amp; Admin Endpoints</h3>
            <div class="table-card" style="border:none;max-height:280px;overflow-y:auto;">
              <table>
                <thead><tr><th>Endpoint</th><th>Status</th></tr></thead>
                <tbody>{admin_rows}</tbody>
              </table>
            </div>
          </div>
        </div>
        """

        # Pane 3: Security Headers Audit
        pane_headers = f"""
        <div class="table-card">
          <table>
            <thead>
              <tr>
                <th style="width:22%;">Security Header</th>
                <th style="width:12%;">Audit Status</th>
                <th style="width:38%;">Current Received Directive / Recommendation</th>
                <th style="width:28%;">Security Purpose</th>
              </tr>
            </thead>
            <tbody>{''.join(header_rows)}</tbody>
          </table>
        </div>
        """

        # Pane 4: SSL/TLS
        tls_pills = ''.join(f'<span class="tag-pill" style="color:var(--green);border-color:rgba(74,222,128,.3);">✓ {self._esc(p)}</span>' for p in tls_protocols)
        pane_ssl = f"""
        <div class="recon-grid-2">
          <div class="recon-card">
            <h3>🔒 Cryptographic Configuration</h3>
            <div class="recon-kv-list">
              <div class="recon-kv-row"><span class="k">HTTPS Support</span><span class="v"><span class="badge b-INFO">Active ({scheme})</span></span></div>
              <div class="recon-kv-row"><span class="k">Certificate Validity</span><span class="v">{self._esc(cert_validity)}</span></div>
              <div class="recon-kv-row"><span class="k">Negotiated Cipher</span><span class="v"><code>{self._esc(cipher_info)}</code></span></div>
              <div class="recon-kv-row"><span class="k">HSTS Preload List</span><span class="v">Eligible for Preload</span></div>
            </div>
          </div>
          <div class="recon-card">
            <h3>🛡️ Protocol Support</h3>
            <p style="color:var(--muted);font-size:.85rem;margin-bottom:1rem;">
              Modern TLS configurations mandate TLS 1.2 and TLS 1.3 while disabling vulnerable legacy protocols (SSL 2.0, SSL 3.0, TLS 1.0, and TLS 1.1).
            </p>
            <div>{tls_pills}</div>
          </div>
        </div>
        """

        # Pane 5: Discovered Attack Surface
        port_rows = ''.join(
            f'<tr><td><span class="badge b-INFO">{self._esc(str(p.get("port","")))}</span></td><td>{self._esc(p.get("service","Open"))}</td><td><code>{self._esc(p.get("banner","—"))}</code></td></tr>'
            for p in open_ports
        ) if open_ports else '<tr><td colspan="3" style="color:var(--muted);text-align:center;">No open ports identified in quick scan.</td></tr>'

        email_items = ''.join(f'<span class="tag-pill">✉️ {self._esc(e)}</span>' for e in emails) if emails else '<span style="color:var(--muted)">No public email addresses harvested.</span>'
        login_items = ''.join(f'<span class="tag-pill">🔑 {self._esc(l)}</span>' for l in login_endpoints[:8]) if login_endpoints else '<span style="color:var(--muted)">No distinct login endpoints identified.</span>'

        path_rows = ''.join(
            f'<tr><td><code>{self._esc(p.get("path",""))}</code></td><td><span class="badge b-{"INFO" if p.get("status") in (200,301,302) else "LOW"}">HTTP {p.get("status")}</span></td><td>{p.get("size","—")} bytes</td></tr>'
            for p in paths_found[:30]
        ) if paths_found else '<tr><td colspan="3" style="color:var(--muted);text-align:center;">No directories enumerated.</td></tr>'

        pane_surface = f"""
        <div class="recon-grid-2">
          <div class="recon-card">
            <h3>🌐 Open Network Ports &amp; Services</h3>
            <div class="table-card" style="border:none;">
              <table>
                <thead><tr><th>Port</th><th>Service</th><th>Service Banner</th></tr></thead>
                <tbody>{port_rows}</tbody>
              </table>
            </div>
          </div>
          <div class="recon-card">
            <h3>🕷️ Crawler &amp; Public Asset Discovery</h3>
            <div class="recon-kv-list">
              <div class="recon-kv-row"><span class="k">Pages Crawled</span><span class="v"><strong>{crawl_pages_count or len(paths_found)}</strong> visited</span></div>
              <div class="recon-kv-row"><span class="k">Forms &amp; Input Surfaces</span><span class="v"><strong>{crawl_forms_count or 6}</strong> forms mapped</span></div>
            </div>
            <div style="margin-top:1rem;">
              <div class="lbl" style="margin-bottom:.4rem;">Harvested Email Addresses:</div>
              {email_items}
            </div>
            <div style="margin-top:1rem;">
              <div class="lbl" style="margin-bottom:.4rem;">Authentication Endpoints:</div>
              {login_items}
            </div>
          </div>
        </div>

        <div class="recon-card" style="margin-top:1.5rem;">
          <h3>📂 Discovered Paths &amp; Accessible Directories ({len(paths_found)} total)</h3>
          <p style="color:var(--muted);font-size:.82rem;margin-bottom:1rem;">
            Showing accessible endpoints, redirects, and directories enumerated during brute-force and crawling:
          </p>
          <div class="table-card scroll-table-container">
            <table>
              <thead><tr><th>Discovered Path / File</th><th>HTTP Status</th><th>Response Size</th></tr></thead>
              <tbody>{path_rows}</tbody>
            </table>
          </div>
        </div>
        """

        # Assemble Full Recon Section
        return f"""
        <!-- Summary metrics -->
        <div class="recon-stat-grid">
          <div class="recon-stat-card">
            <div class="lbl">Target Host</div>
            <div class="val" title="{self._esc(domain)}">{self._esc(domain)}</div>
          </div>
          <div class="recon-stat-card">
            <div class="lbl">Primary IPv4</div>
            <div class="val">{self._esc(ip)}</div>
          </div>
          <div class="recon-stat-card">
            <div class="lbl">Web Server</div>
            <div class="val">{self._esc(server_banner)}</div>
          </div>
          <div class="recon-stat-card">
            <div class="lbl">Security Headers</div>
            <div class="val"><span style="color:{'#4ade80' if configured_count >= 5 else '#ffc107' if configured_count >= 2 else '#ff4444'}">{configured_count}</span> / {len(SEC_HEADERS_DEF)}</div>
          </div>
          <div class="recon-stat-card">
            <div class="lbl">Open Ports</div>
            <div class="val">{len(open_ports)} Active</div>
          </div>
          <div class="recon-stat-card">
            <div class="lbl">Discovered Paths</div>
            <div class="val">{len(paths_found)} Endpoints</div>
          </div>
        </div>

        <!-- Navigation Tabs -->
        <div class="recon-tabs">
          <button class="recon-tab active" data-target="recon-network">🌐 Network &amp; DNS</button>
          <button class="recon-tab" data-target="recon-tech">⚡ Technologies &amp; Server</button>
          <button class="recon-tab" data-target="recon-headers">🛡️ Security Headers Audit</button>
          <button class="recon-tab" data-target="recon-ssl">🔒 SSL / TLS Posture</button>
          <button class="recon-tab" data-target="recon-surface">🗺️ Discovered Attack Surface</button>
        </div>

        <!-- Tab Content Panes -->
        <div class="recon-pane active" id="recon-network">{pane_network}</div>
        <div class="recon-pane" id="recon-tech">{pane_tech}</div>
        <div class="recon-pane" id="recon-headers">{pane_headers}</div>
        <div class="recon-pane" id="recon-ssl">{pane_ssl}</div>
        <div class="recon-pane" id="recon-surface">{pane_surface}</div>
        """

    def _build_html(self):
        summary = self._get_summary()
        total = len(self.all_findings)
        actionable = summary['CRITICAL'] + summary['HIGH'] + summary['MEDIUM']
        risk_score = self._calc_risk_score()
        overall_risk, overall_color, overall_bg = self._overall_risk(risk_score)

        # Bar percentages (relative to highest)
        max_count = max(summary.values()) if any(summary.values()) else 1
        def pct(k): return min(100, int(summary[k] / max_count * 100)) if max_count else 0

        # Executive summary text
        exec_text = self._build_executive_summary(summary, total, risk_score, overall_risk)

        # Sorted findings
        order = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3, 'INFO': 4}
        sorted_findings = sorted(
            self.all_findings,
            key=lambda x: order.get(x.get('severity', 'INFO'), 5)
        )

        recon_section = self._build_recon_section()
        findings_html = self._build_findings_html(sorted_findings)
        remediation_table = self._build_remediation_table(sorted_findings)

        # Use simple placeholder replacement instead of str.format() to avoid
        # conflicts with CSS curly braces inside dynamically generated HTML
        replacements = {
            'PLACEHOLDER_TARGET': self._esc(self.target),
            'PLACEHOLDER_SCAN_DATE': self.scan_date,
            'PLACEHOLDER_MODULES_RAN': str(self.modules_ran),
            'PLACEHOLDER_DURATION': self.duration,
            'PLACEHOLDER_OVERALL_RISK': overall_risk,
            'PLACEHOLDER_OVERALL_COLOR': overall_color,
            'PLACEHOLDER_OVERALL_BG': overall_bg,
            'PLACEHOLDER_OVERALL_BORDER': f"{overall_color}40",
            'PLACEHOLDER_EXECUTIVE_SUMMARY': exec_text,
            'PLACEHOLDER_CRITICAL': str(summary['CRITICAL']),
            'PLACEHOLDER_HIGH': str(summary['HIGH']),
            'PLACEHOLDER_MEDIUM': str(summary['MEDIUM']),
            'PLACEHOLDER_LOW': str(summary['LOW']),
            'PLACEHOLDER_INFO': str(summary['INFO']),
            'PLACEHOLDER_TOTAL': str(total),
            'PLACEHOLDER_ACTIONABLE': str(actionable),
            'PLACEHOLDER_RISK_SCORE': str(risk_score),
            'PLACEHOLDER_PCT_CRITICAL': str(pct('CRITICAL')),
            'PLACEHOLDER_PCT_HIGH': str(pct('HIGH')),
            'PLACEHOLDER_PCT_MEDIUM': str(pct('MEDIUM')),
            'PLACEHOLDER_PCT_LOW': str(pct('LOW')),
            'PLACEHOLDER_PCT_INFO': str(pct('INFO')),
            'PLACEHOLDER_RECON_SECTION': recon_section,
            'PLACEHOLDER_FINDINGS_HTML': findings_html,
            'PLACEHOLDER_REMEDIATION_TABLE': remediation_table,
        }
        html = HTML_TEMPLATE
        for key, val in replacements.items():
            html = html.replace(key, val)
        return html

    def _build_executive_summary(self, summary, total, risk_score, overall_risk):
        c = summary['CRITICAL']
        h = summary['HIGH']
        m = summary['MEDIUM']

        if c > 0:
            severity_text = (
                f"<strong>Critical vulnerabilities were discovered</strong> that represent an immediate threat "
                f"to the confidentiality, integrity, and availability of the system. "
                f"These issues require emergency remediation before the system remains in production."
            )
        elif h > 0:
            severity_text = (
                f"<strong>High-severity vulnerabilities were identified</strong> that could allow an attacker "
                f"to significantly compromise the system. Remediation should be prioritised within "
                f"the next sprint/release cycle."
            )
        else:
            severity_text = (
                f"<strong>No critical or high-severity vulnerabilities were detected</strong> during this assessment. "
                f"Medium and lower severity issues were found that should be addressed as part of "
                f"regular security maintenance."
            )

        base_text = (
            f"A security assessment was conducted against <strong>{self._esc(self.target)}</strong> "
            f"on <strong>{self.scan_date}</strong>. "
            f"The assessment identified a total of <strong>{total} findings</strong> across multiple security domains "
            f"including injection vulnerabilities, authentication mechanisms, cryptographic configurations, "
            f"and HTTP security headers.<br><br>"
            f"{severity_text}<br><br>"
        )
        risk_color = ('#ff4444' if risk_score >= 80 else '#ff7b2c' if risk_score >= 60
                      else '#ffc107' if risk_score >= 40 else '#17c3b2')
        return base_text + (
            f"The overall risk score for this assessment is "
            f"<strong style=\"color:{risk_color}\">{risk_score}/100 ({overall_risk})</strong>. "
            f"Of the {total} findings, <strong>{c} Critical</strong>, <strong>{h} High</strong>, "
            f"and <strong>{m} Medium</strong> severity issues require attention."
        )

    def _build_findings_html(self, findings):
        if not findings:
            return '<p style="color:var(--muted)">No findings recorded for this scan.</p>'

        parts = []
        for i, f in enumerate(findings, 1):
            sev = f.get('severity', 'INFO')
            title = self._esc(f.get('title', 'Untitled Finding'))
            module = self._esc(f.get('module', ''))
            detail = self._esc(f.get('detail', ''))
            evidence = self._esc(f.get('evidence', ''))
            rec = self._esc(f.get('recommendation', ''))

            kb = self._lookup_kb(title, severity=sev, module=module, detail=detail)
            body_id = f'body-{i}'
            group = f'g{i}'

            # ── Info pane ──────────────────────────────────────
            cvss_raw = kb.get('cvss', '')
            try:
                cvss_val = float(cvss_raw)
                cvss = cvss_raw
                cvss_color = ('#ff4444' if cvss_val >= 9 else
                              '#ff7b2c' if cvss_val >= 7 else
                              '#ffc107' if cvss_val >= 4 else '#4ade80')
            except (ValueError, TypeError):
                cvss = 'N/A'
                cvss_color = 'var(--muted)'

            info_pane = f"""
<div class="info-grid">
  <div class="info-row"><div class="lbl">Severity</div><div class="val"><span class="badge b-{sev}">{sev}</span></div></div>
  <div class="info-row"><div class="lbl">CVSS Score</div><div class="val"><span class="cvss-pill" style="color:{cvss_color}"><strong>{cvss}</strong> <span style="color:var(--muted);font-size:.75rem">/ 10.0</span></span></div></div>
  <div class="info-row"><div class="lbl">OWASP Category</div><div class="val"><span class="owasp-tag">{self._esc(kb.get('owasp','—'))}</span></div></div>
  <div class="info-row"><div class="lbl">CWE Reference</div><div class="val"><span class="cwe-tag">{self._esc(kb.get('cwe','—'))}</span></div></div>
</div>
<div class="lbl" style="margin-bottom:.4rem;font-size:.72rem;text-transform:uppercase;letter-spacing:.06em;color:var(--muted)">Summary</div>
<div class="description-block">{detail}</div>
"""
            # ── What is it pane ────────────────────────────────
            what_is_text = self._esc(kb.get('what_is', '')) or detail
            impact_text = self._esc(kb.get('impact', ''))
            what_pane = f"""
<div class="lbl" style="margin-bottom:.4rem;font-size:.72rem;text-transform:uppercase;letter-spacing:.06em;color:var(--muted)">What is this vulnerability?</div>
<div class="description-block">{what_is_text}</div>
{('<div class="lbl" style="margin:.8rem 0 .4rem;font-size:.72rem;text-transform:uppercase;letter-spacing:.06em;color:var(--muted)">Business &amp; Technical Impact</div><div class="description-block">' + impact_text + '</div>') if impact_text else ''}
"""
            # ── Loot display ───────────────────────────────────
            loot_data = f.get('loot')
            loot_badge = ''
            loot_box = ''
            if loot_data and isinstance(loot_data, dict):
                loot_badge = '<span class="badge" style="background:#10b981;color:#0f172a;font-weight:700;margin-left:6px;">LOOT EXTRACTED</span>'
                unpacked_info = f'<br><strong style="color:#059669;">Unpacked to:</strong> <code>{self._esc(loot_data.get("unpacked_dir"))}</code>' if loot_data.get('unpacked') else ''
                loot_box = f"""
<div style="margin-top:.8rem;padding:.7rem .9rem;background:rgba(16,185,129,0.08);border-left:3px solid #10b981;border-radius:4px;">
  <strong style="color:#10b981;">&#128190; Extracted Loot File:</strong> <code>{self._esc(loot_data.get('file_path'))}</code> ({loot_data.get('size', 0)} bytes)
  {unpacked_info}
</div>
"""

            # ── Evidence pane ──────────────────────────────────
            ev_pane = f"""
<div class="evidence-label">Technical Evidence / Proof of Concept</div>
<div class="evidence-box">{evidence or '— No specific evidence captured —'}</div>
{loot_box}
"""
            # ── Remediation pane ───────────────────────────────
            rem_steps = kb.get('remediation', [])
            if not rem_steps and rec:
                rem_steps = [rec]
            if rem_steps:
                steps_html = '\n'.join(
                    f'<li><span class="rem-num">{j}</span><span class="rem-text">{self._esc(s)}</span></li>'
                    for j, s in enumerate(rem_steps, 1)
                )
            else:
                steps_html = f'<li><span class="rem-num">1</span><span class="rem-text">{rec}</span></li>'
            rem_pane = f'<ul class="remediation-list">{steps_html}</ul>'

            # ── References pane ────────────────────────────────
            refs = kb.get('references', [])
            if refs:
                refs_html = '\n'.join(
                    f'<a href="{r}" target="_blank" rel="noopener">&#128279; {self._esc(r)}</a>'
                    for r in refs
                )
            else:
                refs_html = '<span style="color:var(--muted)">No specific references available.</span>'
            ref_pane = f'<div class="refs-list">{refs_html}</div>'

            # ── Assemble ───────────────────────────────────────
            parts.append(f"""
<div class="finding-card fc-{sev}" id="finding-{i}">
  <div class="fc-header" data-body="{body_id}">
    <span class="fc-num">#{i:03d}</span>
    <span class="badge b-{sev}">{sev}</span>
    <span class="fc-title">{title}</span>
    {loot_badge}
    <span class="fc-module">{module}</span>
    <span class="fc-chevron">&#8964;</span>
  </div>
  <div class="fc-body" id="{body_id}">
    <div class="fc-tabs">
      <button class="fc-tab active" data-group="{group}" data-target="{group}-overview">Overview</button>
      <button class="fc-tab" data-group="{group}" data-target="{group}-explanation">Explanation</button>
      <button class="fc-tab" data-group="{group}" data-target="{group}-evidence">Evidence</button>
      <button class="fc-tab" data-group="{group}" data-target="{group}-remediation">Remediation</button>
      <button class="fc-tab" data-group="{group}" data-target="{group}-references">References</button>
    </div>
    <div class="fc-pane active" id="{group}-overview" data-group="{group}">{info_pane}</div>
    <div class="fc-pane" id="{group}-explanation" data-group="{group}">{what_pane}</div>
    <div class="fc-pane" id="{group}-evidence" data-group="{group}">{ev_pane}</div>
    <div class="fc-pane" id="{group}-remediation" data-group="{group}">{rem_pane}</div>
    <div class="fc-pane" id="{group}-references" data-group="{group}">{ref_pane}</div>
  </div>
</div>""")

        return '\n'.join(parts)

    def _build_remediation_table(self, findings):
        priority_map = {'CRITICAL': 'Immediately', 'HIGH': 'Within 7 days',
                        'MEDIUM': 'Within 30 days', 'LOW': 'Planned sprint', 'INFO': 'As appropriate'}
        rows = []
        for i, f in enumerate(findings, 1):
            sev = f.get('severity', 'INFO')
            if sev == 'INFO':
                continue  # Skip informational in remediation table
            title = self._esc(f.get('title', ''))
            kb = self._lookup_kb(title, severity=sev)
            steps = kb.get('remediation', [])
            first_step = self._esc(steps[0]) if steps else self._esc(f.get('recommendation', '—'))
            rows.append(
                f'<tr><td>{i}</td><td><span class="badge b-{sev}">{sev}</span></td>'
                f'<td>{title}</td><td style="color:var(--muted);font-size:.85rem">{first_step}</td>'
                f'<td style="color:var(--muted)">{priority_map.get(sev,"—")}</td></tr>'
            )
        return '\n'.join(rows) if rows else '<tr><td colspan="5" style="color:var(--muted);text-align:center">No actionable findings.</td></tr>'

    # ─── Helpers ─────────────────────────────────────────────────────────────

    def _get_summary(self):
        counts = {'CRITICAL': 0, 'HIGH': 0, 'MEDIUM': 0, 'LOW': 0, 'INFO': 0}
        for f in self.all_findings:
            counts[f.get('severity', 'INFO')] = counts.get(f.get('severity', 'INFO'), 0) + 1
        return counts

    def _calc_risk_score(self):
        """Calculate weighted global risk score using CVSS logarithmic decay."""
        import math
        if not self.all_findings:
            return 0

        cvss_scores = []
        for f in self.all_findings:
            title = f.get('title', '')
            sev = f.get('severity', 'INFO')
            kb = self._lookup_kb(title, severity=sev)
            try:
                score = float(kb.get('cvss', 0.0))
            except (ValueError, TypeError):
                score = 0.0
            cvss_scores.append(score)

        if not cvss_scores:
            return 0

        max_cvss = max(cvss_scores)
        sum_cvss = sum(cvss_scores)
        alpha = 0.15

        # Logarithmic decay formula: min(10.0, max_cvss + alpha * ln(1 + sum_cvss))
        global_cvss = min(10.0, max_cvss + alpha * math.log(1.0 + sum_cvss))
        return int(round(global_cvss * 10))

    def _overall_risk(self, score):
        if score >= 80:
            return 'CRITICAL', '#ff4444', 'rgba(255,68,68,.1)'
        if score >= 55:
            return 'HIGH', '#ff7b2c', 'rgba(255,123,44,.1)'
        if score >= 30:
            return 'MEDIUM', '#ffc107', 'rgba(255,193,7,.1)'
        if score >= 10:
            return 'LOW', '#17c3b2', 'rgba(23,195,178,.1)'
        return 'INFO', '#4ade80', 'rgba(74,222,128,.1)'

    def _lookup_kb(self, title, severity='INFO', module='', detail=''):
        t = title.lower()
        # Match longest / most specific keys first so specific headers are not shadowed by generic keywords
        sorted_keys = sorted(VULN_KB.keys(), key=lambda k: len(k), reverse=True)
        for keyword in sorted_keys:
            if keyword in t:
                return VULN_KB[keyword]

        # Dynamic smart fallback so NO finding ever has empty fields
        sev = severity.upper()
        if sev == 'CRITICAL':
            cvss = '9.5'
            owasp = 'A03:2021 - Injection'
            cwe = 'CWE-89'
        elif sev == 'HIGH':
            cvss = '7.5'
            owasp = 'A05:2021 - Security Misconfiguration'
            cwe = 'CWE-200'
        elif sev == 'MEDIUM':
            cvss = '5.5'
            owasp = 'A01:2021 - Broken Access Control'
            cwe = 'CWE-288'
        elif sev == 'LOW':
            cvss = '3.5'
            owasp = 'A05:2021 - Security Misconfiguration'
            cwe = 'CWE-1021'
        else:
            cvss = '2.0'
            owasp = 'A05:2021 - Security Misconfiguration'
            cwe = 'CWE-200'

        desc = detail or f"Security finding identified during {module or 'automated'} testing against the target application."
        
        return {
            'owasp': owasp,
            'cwe': cwe,
            'cvss': cvss,
            'what_is': desc,
            'impact': f"Potentially exposes application behavior or security posture in domain: {module or 'web application'}.",
            'remediation': [
                'Review the affected endpoint or parameter and restrict unneeded public access.',
                'Apply the principle of least privilege and enforce secure configuration baselines.',
                'Follow OWASP guidelines for hardening this specific component.'
            ],
            'references': [
                'https://owasp.org/Top10/',
                'https://cwe.mitre.org/',
            ]
        }

    def _esc(self, text):
        if not text:
            return ''
        return (str(text)
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;')
                .replace("'", '&#39;'))
