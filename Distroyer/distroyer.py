#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
+------------------------------------------------------------------+
|         DISTROYER - Web Security & Penetration Testing           |
|                     Framework v2.0                               |
|                                                                  |
|  [!] FOR AUTHORIZED USE ONLY - EDUCATIONAL & ETHICAL PURPOSES    |
|  Only test systems you have explicit permission to test          |
+------------------------------------------------------------------+

Usage:
    python distroyer.py -u <URL> [options]
    python distroyer.py -u https://target.com --full
    python distroyer.py -u https://target.com --modules recon,headers,ssl
    python distroyer.py -u https://target.com --stealth --threads 1

Modules:
    recon, ports, headers, ssl, fingerprint, dirs, subdomains, cors,
    crawl, sqli, xss, csrf, lfi, redirect, ssrf, secrets, ratelimit, auth

Options:
    --full          Run all modules
    --stealth       Slow/quiet mode (bypass WAF)
    --threads N     Number of threads (default: 10)
    --timeout N     Request timeout seconds (default: 10)
    --output FILE   Save report (json/html auto-detected)
    --no-color      Disable colors
    --verbose       Verbose output
"""

import sys
import os
import json
import time
import argparse
import asyncio
from datetime import datetime
from pathlib import Path

# Add modules directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
    from rich.text import Text
    from rich import box
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

from modules.recon import ReconModule
from modules.headers import HeadersModule
from modules.ssl_tls import SSLModule
from modules.tech_fingerprint import FingerprintModule
from modules.dir_enum import DirEnumModule
from modules.sqli import SQLiModule
from modules.xss import XSSModule
from modules.csrf import CSRFModule
from modules.lfi_rfi import LFIModule
from modules.open_redirect import OpenRedirectModule
from modules.cors import CORSModule
from modules.subdomain import SubdomainModule
from modules.crawler import CrawlerModule
from modules.portscan import PortScanModule
from modules.auth_test import AuthModule
from modules.secrets_scanner import SecretsModule
from modules.ssrf import SSRFModule
from modules.rate_limit import RateLimitModule
from modules.dystroyer_network import DystroyerNetworkModule
from modules.network import NetworkManager
from modules.report import ReportGenerator
from modules.distroy_it import Distroyit


console = Console() if HAS_RICH else None

BANNER = r"""
[bold red]
DISTROYER - Web Security & Penetration Testing Framework
[/bold red]
[bold yellow]          v2.0 | Enterprise Red Team Edition[/bold yellow]
[red]          [!] FOR AUTHORIZED TESTING ONLY - RED TEAM TOOL [!][/red]
"""

ALL_MODULES = {
    'recon': ('Reconnaissance & OSINT', ReconModule),
    'ports': ('Port Scanning & Services', PortScanModule),
    'headers': ('HTTP Security Headers', HeadersModule),
    'ssl': ('SSL/TLS Analysis', SSLModule),
    'fingerprint': ('Technology Fingerprinting', FingerprintModule),
    'net': ('Dystroyer Network Defense & Egress Analyzer', DystroyerNetworkModule),
    'dirs': ('Directory & File Enumeration', DirEnumModule),
    'subdomains': ('Subdomain Enumeration', SubdomainModule),
    'cors': ('CORS Misconfiguration', CORSModule),
    'crawl': ('Web Crawler & JS Route Analysis', CrawlerModule),
    'sqli': ('SQL Injection Testing', SQLiModule),
    'xss': ('Cross-Site Scripting (XSS)', XSSModule),
    'csrf': ('CSRF Detection', CSRFModule),
    'lfi': ('LFI/RFI Testing', LFIModule),
    'redirect': ('Open Redirect Testing', OpenRedirectModule),
    'ssrf': ('Server-Side Request Forgery', SSRFModule),
    'secrets': ('Secrets & API Key Scanner', SecretsModule),
    'ratelimit': ('Rate Limiting & Brute Force', RateLimitModule),
    'auth': ('Authentication Testing', AuthModule),
    'distroyit': ('Distroyit', Distroyit),
}


def print_banner():
    if HAS_RICH:
        console.print(BANNER)
        console.print(Panel(
            "[yellow][!] Only test systems you have EXPLICIT written permission to test.\n"
            "   Unauthorized testing is illegal and unethical.[/yellow]",
            title="[bold red]LEGAL DISCLAIMER[/bold red]",
            border_style="red"
        ))
    else:
        print("=" * 70)
        print("  DISTROYER - Web Penetration Testing Framework")
        print("  [!] AUTHORIZED USE ONLY")
        print("=" * 70)


def parse_args():
    parser = argparse.ArgumentParser(
        description='Distroyer - Comprehensive Web Security Testing Framework',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument('-u', '--url', required=False, help='Target URL (e.g. https://target.com)')
    parser.add_argument('--full', action='store_true', help='Run ALL modules')
    parser.add_argument('--modules', help='Comma-separated list of modules to run')
    parser.add_argument('--stealth', action='store_true', help='Stealth mode (slow, evades WAF)')
    parser.add_argument('--threads', type=int, default=10, help='Number of concurrent threads')
    parser.add_argument('--timeout', type=int, default=10, help='Request timeout in seconds')
    parser.add_argument('--output', help='Output file (report.json or report.html)')
    parser.add_argument('--no-color', action='store_true', help='Disable colored output')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--user-agent', default='Mozilla/5.0 (compatible; Distroyer/1.0)', 
                        help='Custom User-Agent string')
    parser.add_argument('--cookie', help='Cookie header to include in requests')
    parser.add_argument('--header', action='append', help='Custom header (format: Key:Value)')
    parser.add_argument('--proxy', help='HTTP proxy (e.g. http://127.0.0.1:8080)')
    parser.add_argument('--depth', type=int, default=2, help='Crawl depth')
    parser.add_argument('--wordlist-dirs', help='Custom directory wordlist')
    parser.add_argument('--wordlist-subs', help='Custom subdomain wordlist')
    parser.add_argument('--extract', dest='extract', action='store_true', default=True,
                        help='Automatically extract/download discovered sensitive & backup files (default: enabled)')
    parser.add_argument('--no-extract', dest='extract', action='store_false',
                        help='Disable automatic extraction of discovered files')
    parser.add_argument('--loot-dir', default='loot', help='Directory to save extracted files (default: loot)')
    parser.add_argument('--extract-report', help='Extract exposed files from an existing HTML or JSON report')
    parser.add_argument('--rate-limit', type=float, help='Max requests per second rate limit')
    parser.add_argument('--insecure', '-k', action='store_true', help='Disable SSL certificate verification')
    parser.add_argument('--scope-mode', choices=['exact', 'subdomains'], default='subdomains',
                        help='Target scope boundary (exact: target host only, subdomains: include subdomains)')
    parser.add_argument('--exclude-hosts', help='Comma-separated hosts to strictly exclude from all tests')
    parser.add_argument('--oob-server', help='Out-Of-Band callback server for blind SSRF (e.g. oob.interactsh.com)')
    parser.add_argument('--oob-poll-url', help='Endpoint URL to retrieve OOB interactions')
    parser.add_argument('--check-session-url', help='URL endpoint to verify session health/validity')
    parser.add_argument('--fail-on', choices=['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'], default='HIGH',
                        help='Severity threshold to trigger exit code 1 (default: HIGH)')
    parser.add_argument('--soft-fail', action='store_true', help='Always exit with code 0 regardless of findings')
    parser.add_argument('--net-mode', choices=['passive', 'active', 'hybrid'], default='hybrid',
                        help='Dystroyer Network execution mode (default: hybrid)')
    args = parser.parse_args()

    if not args.url and not args.extract_report:
        parser.error("-u/--url is required (unless using --extract-report)")

    return args


def build_config(args):
    custom_headers = {}
    if args.header:
        for h in args.header:
            if ':' in h:
                k, v = h.split(':', 1)
                custom_headers[k.strip()] = v.strip()
    if args.cookie:
        custom_headers['Cookie'] = args.cookie
    custom_headers['User-Agent'] = args.user_agent

    target_url = args.url.rstrip('/') if args.url else ''

    scan_context = {}
    config = {
        'url': target_url,
        'stealth': args.stealth,
        'threads': 1 if args.stealth else args.threads,
        'timeout': args.timeout,
        'verbose': args.verbose,
        'headers': custom_headers,
        'proxy': args.proxy,
        'depth': args.depth,
        'wordlist_dirs': args.wordlist_dirs,
        'wordlist_subs': args.wordlist_subs,
        'delay': 2.0 if args.stealth else (1.0 / args.rate_limit if args.rate_limit else 0.1),
        'rate_limit': args.rate_limit,
        'insecure': args.insecure,
        'scope_mode': args.scope_mode,
        'exclude_hosts': args.exclude_hosts,
        'oob_server': args.oob_server,
        'oob_poll_url': args.oob_poll_url,
        'check_session_url': args.check_session_url,
        'extract': getattr(args, 'extract', True),
        'loot_dir': getattr(args, 'loot_dir', 'loot'),
        'net_mode': getattr(args, 'net_mode', 'hybrid'),
        'context': scan_context,
    }
    config['network'] = NetworkManager(config)
    return config


def select_modules(args):
    if args.full:
        return list(ALL_MODULES.keys())
    if args.modules:
        requested = [m.strip().lower() for m in args.modules.split(',')]
        invalid = [m for m in requested if m not in ALL_MODULES]
        if invalid:
            print(f"[!] Unknown modules: {', '.join(invalid)}")
            print(f"    Valid: {', '.join(ALL_MODULES.keys())}")
            sys.exit(1)
        # Preserve natural pipeline order for requested modules
        return [m for m in ALL_MODULES if m in requested]
    # Default: safe reconnaissance & discovery modules
    return ['recon', 'headers', 'ssl', 'fingerprint', 'cors', 'crawl', 'secrets']


def run_modules(selected, config, results):
    total = len(selected)
    
    if HAS_RICH:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[cyan]{task.completed}/{task.total}"),
            console=console,
            transient=False
        ) as progress:
            task = progress.add_task("[green]Running modules...", total=total)
            
            for mod_name in selected:
                desc, ModClass = ALL_MODULES[mod_name]
                progress.update(task, description=f"[cyan]» {desc}")
                
                try:
                    module = ModClass(config)
                    mod_results = module.run()
                    results[mod_name] = mod_results
                    
                    # Print findings immediately
                    _print_module_results(mod_name, desc, mod_results)
                    
                except KeyboardInterrupt:
                    console.print("\n[yellow][!] Interrupted by user[/yellow]")
                    break
                except Exception as e:
                    results[mod_name] = {'error': str(e), 'findings': []}
                    if config.get('verbose'):
                        console.print(f"[red][!] Module {mod_name} error: {e}[/red]")
                
                progress.advance(task)
                time.sleep(config.get('delay', 0.1))
    else:
        for i, mod_name in enumerate(selected, 1):
            desc, ModClass = ALL_MODULES[mod_name]
            print(f"\n[{i}/{total}] Running: {desc}")
            try:
                module = ModClass(config)
                results[mod_name] = module.run()
            except Exception as e:
                results[mod_name] = {'error': str(e), 'findings': []}


def _print_module_results(mod_name, desc, mod_results):
    if not HAS_RICH:
        return
    
    findings = mod_results.get('findings', [])
    if not findings:
        return

    table = Table(
        title=f"[bold]{desc}[/bold]",
        box=box.SIMPLE_HEAVY,
        show_header=True,
        header_style="bold magenta"
    )
    table.add_column("Severity", style="bold", width=10)
    table.add_column("Finding", style="white")
    table.add_column("Detail", style="dim")

    sev_colors = {'CRITICAL': 'red', 'HIGH': 'bright_red', 'MEDIUM': 'yellow', 
                  'LOW': 'cyan', 'INFO': 'green'}
    
    for f in findings:
        sev = f.get('severity', 'INFO')
        color = sev_colors.get(sev, 'white')
        table.add_row(
            f"[{color}]{sev}[/{color}]",
            f.get('title', ''),
            f.get('detail', '')[:80]
        )
    
    console.print(table)


def print_summary(results, start_time):
    elapsed = time.time() - start_time
    all_findings = []
    for mod_name, data in results.items():
        for f in data.get('findings', []):
            f['module'] = mod_name
            all_findings.append(f)

    by_sev = {'CRITICAL': 0, 'HIGH': 0, 'MEDIUM': 0, 'LOW': 0, 'INFO': 0}
    for f in all_findings:
        sev = f.get('severity', 'INFO')
        by_sev[sev] = by_sev.get(sev, 0) + 1

    if HAS_RICH:
        summary = Table(title="[bold red]SCAN SUMMARY[/bold red]", box=box.DOUBLE_EDGE)
        summary.add_column("Category", style="bold")
        summary.add_column("Count", justify="right")
        
        summary.add_row("[red]Critical", str(by_sev['CRITICAL']))
        summary.add_row("[bright_red]High", str(by_sev['HIGH']))
        summary.add_row("[yellow]Medium", str(by_sev['MEDIUM']))
        summary.add_row("[cyan]Low", str(by_sev['LOW']))
        summary.add_row("[green]Info", str(by_sev['INFO']))
        summary.add_row("-" * 20, "-" * 10)
        summary.add_row("[bold]Total Findings", f"[bold]{len(all_findings)}[/bold]")
        summary.add_row("[dim]Scan Duration", f"{elapsed:.1f}s")
        
        console.print(summary)
    else:
        print("\n" + "=" * 40)
        print("SCAN SUMMARY")
        for sev, count in by_sev.items():
            print(f"  {sev}: {count}")
        print(f"  Total: {len(all_findings)}")
        print(f"  Duration: {elapsed:.1f}s")

    # Display extracted loot summary
    loot_items = []
    seen_loot_paths = set()
    for f in all_findings:
        l = f.get('loot')
        if l and l.get('file_path') and l['file_path'] not in seen_loot_paths:
            seen_loot_paths.add(l['file_path'])
            loot_items.append(l)

    if loot_items:
        if HAS_RICH:
            loot_table = Table(title="[bold green]EXTRACTED FILES (LOOT)[/bold green]", box=box.HEAVY_EDGE)
            loot_table.add_column("URL", style="cyan")
            loot_table.add_column("Saved Path", style="yellow")
            loot_table.add_column("Size", justify="right", style="green")
            loot_table.add_column("Unpacked Directory", style="magenta")

            for item in loot_items:
                unpacked = item.get('unpacked_dir') or '-'
                loot_table.add_row(
                    item.get('url', ''),
                    item.get('file_path', ''),
                    f"{item.get('size', 0)} B",
                    unpacked
                )
            console.print(loot_table)
        else:
            print("\n" + "=" * 40)
            print("EXTRACTED FILES (LOOT)")
            for item in loot_items:
                unpacked_str = f" (Unpacked: {item['unpacked_dir']})" if item.get('unpacked_dir') else ""
                print(f"  • {item.get('url')} -> {item.get('file_path')}{unpacked_str}")

    return all_findings


def main():
    args = parse_args()
    print_banner()

    if args.extract_report:
        from modules.extractor import FileExtractor
        FileExtractor.extract_from_report(args.extract_report, base_dir=args.loot_dir)
        if not args.url:
            return 0

    if HAS_RICH:
        console.print(f"\n[bold green]Target:[/bold green] [cyan]{args.url}[/cyan]")
        console.print(f"[bold green]Started:[/bold green] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    config = build_config(args)
    selected = select_modules(args)
    
    if HAS_RICH:
        mod_list = ", ".join(f"[cyan]{m}[/cyan]" for m in selected)
        console.print(f"[bold]Modules:[/bold] {mod_list}\n")

    results = {}
    start_time = time.time()
    
    run_modules(selected, config, results)

    # Session health check verification
    if config.get('check_session_url'):
        if not config['network'].check_session_health():
            if HAS_RICH:
                console.print("\n[bold red][!] WARNING: Session health check failed! Authenticated session appears expired or revoked.[/bold red]")
            else:
                print("\n[!] WARNING: Session health check failed! Authenticated session appears expired or revoked.")

    # Deferred Out-Of-Band (OOB) interactions polling
    if config.get('oob_server'):
        if HAS_RICH:
            console.print("\n[bold cyan]» Performing deferred Out-Of-Band (OOB) correlation polling...[/bold cyan]")
        else:
            print("\n» Performing deferred Out-Of-Band (OOB) correlation polling...")
        SSRFModule.poll_oob_interactions(config, config['context'], results, all_findings=[])

    all_findings = print_summary(results, start_time)
    
    # Generate report
    if args.output:
        elapsed = time.time() - start_time
        reporter = ReportGenerator(config, results, all_findings, duration=elapsed)
        if args.output.endswith('.sarif'):
            reporter.save_sarif(args.output)
        elif args.output.endswith('.html'):
            reporter.save_html(args.output)
        else:
            reporter.save_json(args.output)
        if HAS_RICH:
            console.print(f"\n[green]Report saved:[/green] [cyan]{args.output}[/cyan]")

    if args.soft_fail:
        return 0

    fail_map = {
        'CRITICAL': ['CRITICAL'],
        'HIGH': ['CRITICAL', 'HIGH'],
        'MEDIUM': ['CRITICAL', 'HIGH', 'MEDIUM'],
        'LOW': ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'],
    }
    threshold = fail_map.get(args.fail_on, ['CRITICAL', 'HIGH'])
    return 1 if any(f.get('severity') in threshold for f in all_findings) else 0


if __name__ == '__main__':
    sys.exit(main())
