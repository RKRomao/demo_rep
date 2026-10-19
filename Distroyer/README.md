# DISTROYER
### Web Security & Penetration Testing Framework

```
██████╗ ██╗███████╗████████╗██████╗  ██████╗ ██╗   ██╗███████╗██████╗ 
██╔══██╗██║██╔════╝╚══██╔══╝██╔══██╗██╔═══██╗╚██╗ ██╔╝██╔════╝██╔══██╗
██║  ██║██║███████╗   ██║   ██████╔╝██║   ██║ ╚████╔╝ █████╗  ██████╔╝
██║  ██║██║╚════██║   ██║   ██╔══██╗██║   ██║  ╚██╔╝  ██╔══╝  ██╔══██╗
██████╔╝██║███████║   ██║   ██║  ██║╚██████╔╝   ██║   ███████╗██║  ██║
╚═════╝ ╚═╝╚══════╝   ╚═╝   ╚═╝  ╚═╝ ╚═════╝    ╚═╝   ╚══════╝╚═╝  ╚═╝
```

> **AUTHORIZED USE ONLY** — Only test systems you own or have **explicit written permission** to test. Unauthorized testing is **illegal**.

---

## Features

| Module | Description |
|--------|-------------|
| `recon` | DNS enum, WHOIS, IP/ASN info, robots.txt, sitemap, .git exposure, backup files & automated loot extraction |
| `ports` | Port scanning (100+ ports), banner grabbing, high-risk service detection |
| `headers` | HTTP security headers analysis (HSTS, CSP, X-Frame, cookies, etc.) |
| `ssl` | TLS/SSL cert analysis, weak protocols, cipher suites, HSTS preload |
| `fingerprint` | CMS/framework detection, WAF fingerprinting, version detection |
| `dirs` | Directory & sensitive file brute-force with automated loot extraction |
| `subdomains` | Certificate transparency + DNS brute-force subdomain enum |
| `cors` | CORS misconfiguration (wildcard, null origin, credentials) |
| `crawl` | Recursive web crawler with SPA/JS route extraction & dynamic parameter normalization |
| `sqli` | Error-based, Boolean-based & differential Time-based SQL Injection testing with JSON type preservation |
| `xss` | Context-aware Reflected XSS with executable reflection verification |
| `csrf` | CSRF token detection, bypass testing, SameSite analysis |
| `lfi` | LFI/RFI with path traversal, null bytes, PHP wrapper attacks |
| `redirect` | Open Redirect testing with encoding bypass attempts |
| `ssrf` | Server-Side Request Forgery: in-band cloud metadata (AWS, GCP, loopback) & deferred OOB callback testing |
| `secrets` | High-entropy regex scanner for exposed secrets in JS (AWS, Stripe, JWT, GitHub, Slack) |
| `ratelimit` | Concurrency burst testing on sensitive auth endpoints for missing HTTP 429 rate limiting |
| `auth` | Default creds, JWT analysis, auth bypass headers, user enumeration |
| `net` | **Dystroyer Network**: Hybrid perimeter defense audit (Egress L4 filtering, TLS/DPI inspection, DNS sinkholing, WAF/IDS detection) |
| `distroyit` | Network stress testing & resilience verification for discovered ports/services |

---

## Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Basic scan (safe recon modules)
```bash
python distroyer.py -u https://target.com
```

### 3. Full penetration test with interactive HTML report
```bash
python distroyer.py -u https://target.com --full --output report.html
```

### 4. Specific modules
```bash
python distroyer.py -u https://target.com --modules sqli,xss,csrf,lfi,cors,secrets
```

### 5. Dystroyer Network (Hybrid Perimeter & Egress Audit)
Audit outbound egress filtering, corporate TLS/DPI inspection, DNS sinkholing, and perimeter WAF defenses:
```bash
# Run in hybrid mode (passive detection + controlled benign probes)
python distroyer.py -u https://target.com --modules net

# Run in purely passive/safe mode
python distroyer.py -u https://target.com --modules net --net-mode passive

# Standalone execution for local network diagnostics
python modules/dystroyer_network.py -u https://target.com --net-mode hybrid
```

### 6. Adaptive Rate Limiting & Scope Guard
```bash
python distroyer.py -u https://api.target.com --full \
  --rate-limit 15 \
  --scope-mode exact \
  --exclude-hosts payment.target.com,analytics.target.com
```

### 7. CI/CD Pipeline Scanning with SARIF & Fail-On Threshold
```bash
python distroyer.py -u https://staging.target.com --modules headers,cors,sqli,xss,ratelimit,secrets \
  --output report.sarif \
  --fail-on HIGH
```
*Returns exit code 1 if any High or Critical findings are discovered; returns code 0 if below threshold.*

### 8. Behind a proxy (Burp Suite) & Insecure TLS
```bash
python distroyer.py -u https://target.com --proxy http://127.0.0.1:8080 --insecure --full
```

### 9. Stealth mode (slow, WAF bypass)
```bash
python distroyer.py -u https://target.com --full --stealth --threads 1
```

### 10. Blind SSRF Out-of-Band (OOB) Testing
```bash
python distroyer.py -u https://target.com --modules ssrf \
  --oob-server oob.interactsh.com \
  --oob-poll-url https://oob.interactsh.com/poll?token=SECRET
```

### 11. Loot & Backup File Extraction (Automatic)
Distroyer automatically downloads and extracts discovered backup files (`.bak`, `.old`, `.backup`, `.sql`, `.env`, etc.) and unpacks archives (`.zip`, `.tar.gz`) into the `loot/<domain>/` directory:
```bash
# Automatic extraction into loot/ directory (default behavior)
python distroyer.py -u https://target.com --full

# Custom loot directory
python distroyer.py -u https://target.com --full --loot-dir harvested_loot/

# Extract files from a previously generated report without rescanning
python distroyer.py --extract-report report.html --loot-dir loot/
```

---

## Output Formats

### HTML Report (interactive dark-theme UI with Loot Badges & CVSS Logarithmic Meter)
```bash
python distroyer.py -u https://target.com --full --output reports/scan.html
```

### JSON Report (machine-readable)
```bash
python distroyer.py -u https://target.com --full --output reports/scan.json
```

### SARIF Report (OASIS SARIF v2.1.0 for GitHub/GitLab CI/CD)
```bash
python distroyer.py -u https://target.com --full --output reports/scan.sarif
```

---

## All Options

```
-u, --url URL              Target URL (required unless using --extract-report)
--full                     Run ALL modules
--modules m1,m2,...        Specific modules to run
--stealth                  Slow/quiet mode (evades WAF detection)
--threads N                Concurrent threads (default: 10)
--timeout N                Request timeout seconds (default: 10)
--output FILE              Save report (auto-detects .html, .json, or .sarif)
--no-color                 Disable terminal colors
-v, --verbose              Verbose output
--user-agent UA            Custom User-Agent
--cookie COOKIE            Cookie header value
--header Key:Value         Custom request header (repeatable)
--proxy URL                HTTP/HTTPS proxy (e.g., Burp Suite)
--depth N                  Crawler depth (default: 2)
--wordlist-dirs FILE       Custom directory wordlist
--wordlist-subs FILE       Custom subdomain wordlist
--extract                  Automatically extract/download sensitive & backup files (default: enabled)
--no-extract               Disable automatic file extraction
--loot-dir DIR             Directory to save extracted files (default: loot)
--extract-report FILE      Extract exposed files from an existing HTML or JSON report
--rate-limit N             Max requests per second rate limit (token bucket)
-k, --insecure             Disable TLS/SSL certificate verification
--scope-mode {exact,subdomains}
                           Target scope boundary (exact: host only, subdomains: include subdomains)
--exclude-hosts HOSTS      Comma-separated hosts to strictly exclude from all tests
--oob-server SERVER        Out-Of-Band callback server for blind SSRF (e.g. oob.interactsh.com)
--oob-poll-url URL         Endpoint URL to retrieve OOB interactions at scan conclusion
--check-session-url URL    URL endpoint to verify session health/validity before and during scan
--fail-on LEVEL            Severity threshold to trigger exit code 1: CRITICAL, HIGH, MEDIUM, LOW (default: HIGH)
--soft-fail                Always exit with code 0 regardless of findings (useful for non-blocking CI runs)
--net-mode {passive,active,hybrid}
                           Dystroyer Network execution mode: passive, active, or hybrid (default: hybrid)
```

---

## Project Structure

```
Distroyer/
├── distroyer.py          # Main CLI entrypoint & CI/CD workflow orchestrator
├── distroy-wp.py         # WordPress testing helper script
├── requirements.txt      # Python dependencies
├── README.md
├── modules/
│   ├── base.py           # Base module class with shared ScanContext & loot integration
│   ├── network.py        # Central connection pooling, token-bucket rate limit & ScopeGuard
│   ├── dystroyer_network.py # Dystroyer Network (Hybrid egress, TLS inspection, DNS defense & WAF/IDS)
│   ├── extractor.py      # Automated loot downloader & archive unpacker
│   ├── recon.py          # Reconnaissance & OSINT (backups, .git, configs)
│   ├── portscan.py       # Port scanning & sanitized banner grabbing
│   ├── headers.py        # HTTP security headers analysis
│   ├── ssl_tls.py        # SSL/TLS posture analysis
│   ├── tech_fingerprint.py  # Technology fingerprinting
│   ├── dir_enum.py       # Directory & sensitive file enumeration
│   ├── crawler.py        # SPA crawler, JS route regex extraction & parameter normalization
│   ├── sqli.py           # Differential timing SQLi with JSON type preservation
│   ├── xss.py            # Context-aware XSS with reflection executable checks
│   ├── csrf.py           # CSRF token detection & bypass testing
│   ├── lfi_rfi.py        # LFI/RFI testing
│   ├── open_redirect.py  # Open redirect testing
│   ├── cors.py           # CORS misconfiguration testing
│   ├── subdomain.py      # Subdomain enumeration
│   ├── ssrf.py           # SSRF with cloud metadata & deferred OOB polling
│   ├── secrets_scanner.py # JS secrets & API key audit (AWS, Stripe, JWT, GitHub)
│   ├── rate_limit.py     # Sensitive endpoint burst rate limiting & brute-force audit
│   ├── auth_test.py      # Authentication testing
│   ├── distroy_it.py     # Distroyit stress testing & resilience verification
│   └── report.py         # Report generation (HTML dark UI, JSON, SARIF v2.1.0 & CVSS scoring)
├── wordlists/
│   ├── dirs.txt          # Directory wordlist
│   └── subdomains.txt    # Subdomain wordlist
├── loot/                 # Extracted files & unpacked archives (by target domain)
└── reports/              # Generated reports
```

---

## Custom Wordlists

Download SecLists for better coverage:
```bash
# Directory wordlist
curl -o wordlists/dirs.txt https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/Web-Content/raft-medium-directories.txt

# Subdomain wordlist
curl -o wordlists/subdomains.txt https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/DNS/subdomains-top1million-5000.txt
```

---

## Legal Notice

This tool is provided for **educational and authorized security testing purposes only**.

- Authorized penetration testing
- Bug bounty hunting (within scope)
- Testing your own infrastructure
- CTF challenges
- Unauthorized access to systems
- Illegal activities of any kind

The authors assume no liability for misuse of this tool.

---

*Built with ❤️ for the cybersecurity community*
