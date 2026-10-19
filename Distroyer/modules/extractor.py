"""
Loot Extractor Module
Automatically downloads and extracts backup and sensitive files discovered during scans.
"""
import os
import re
import sys
import tarfile
import zipfile
import urllib.parse
from datetime import datetime
from pathlib import Path

try:
    from rich.console import Console
    HAS_RICH = True
    console = Console()
except ImportError:
    HAS_RICH = False
    console = None


class FileExtractor:
    """Handles automatic saving and unpacking of discovered sensitive & backup files."""

    def __init__(self, base_dir: str = 'loot', enabled: bool = True, session=None):
        self.base_dir = os.path.abspath(base_dir)
        self.enabled = enabled
        self.session = session
        self.extracted_records = []
        self._extracted_urls = set()

    def _sanitize_path(self, base_folder: str, relative_path: str) -> str:
        """
        Sanitize relative path to prevent directory traversal and invalid filename characters.
        Ensures the path remains strictly within base_folder.
        """
        # Strip scheme and host if present
        if '://' in relative_path:
            relative_path = urllib.parse.urlparse(relative_path).path

        # Normalize slashes and remove leading/trailing slashes
        clean = relative_path.replace('\\', '/').strip('/')
        parts = clean.split('/')

        safe_parts = []
        # Invalid characters on Windows: < > : " / \ | ? *
        invalid_chars = re.compile(r'[<>:"\\|?*]')
        for part in parts:
            part = part.strip()
            if not part or part in ('.', '..'):
                continue
            safe_name = invalid_chars.sub('_', part).rstrip(' ')
            if safe_name and safe_name not in ('.', '..'):
                safe_parts.append(safe_name)

        if not safe_parts:
            safe_parts = ['extracted_file.bin']

        joined = os.path.join(base_folder, *safe_parts)
        real_base = os.path.realpath(base_folder)
        real_target = os.path.realpath(joined)

        if not real_target.startswith(real_base):
            # Fallback to base folder with a single safe name
            return os.path.join(real_base, safe_parts[-1])

        return real_target

    @classmethod
    def validate_file_content(cls, path_or_url: str, content: bytes, final_url: str = None) -> bool:
        """
        Intelligently validate that the received content is an authentic file
        and not a generic HTML login, error, or catch-all landing page.
        """
        if not content or len(content) == 0:
            return False

        # 1. Check if final destination is an authentication, error, or generic home endpoint
        if final_url:
            parsed_final = urllib.parse.urlparse(final_url)
            final_path = parsed_final.path.rstrip('/').lower()
            auth_or_error = ('/login', '/signin', '/auth', '/session', '/oauth', '/sso', '/404', '/error')
            if any(final_path == ap or final_path.endswith(ap) for ap in auth_or_error):
                return False

        parsed = urllib.parse.urlparse(path_or_url)
        raw_name = (parsed.path or path_or_url).split('/')[-1] or 'file'
        lower_name = raw_name.lower()

        content_preview = content[:500].lower()
        is_html = (
            content.strip().startswith(b'<!doctype') or
            content.strip().startswith(b'<html') or
            b'<html' in content_preview or
            b'<head' in content_preview or
            b'<!doctype html' in content_preview
        )

        # 2. Archive files (.zip, .tar.gz, etc.)
        if lower_name.endswith('.zip'):
            # Must have PK magic bytes or valid zip structure
            return content.startswith(b'PK\x03\x04') or content.startswith(b'PK\x05\x06')
        if lower_name.endswith(('.tar.gz', '.tgz')):
            # Gzip magic bytes: 1f 8b
            return content.startswith(b'\x1f\x8b')
        if lower_name.endswith('.tar.bz2'):
            return content.startswith(b'BZh')
        if lower_name.endswith('.tar'):
            return not is_html

        # 3. Database dumps (.sql, .sqlite, .db)
        if lower_name.endswith(('.sqlite', '.sqlite3')):
            return content.startswith(b'SQLite format 3\x00')
        if lower_name.endswith(('.sql', '.dump')):
            if is_html:
                return False
            sql_markers = (b'create ', b'insert ', b'drop ', b'table ', b'select ', b'--', b'/*', b'database', b'dump')
            return any(m in content_preview for m in sql_markers) or not is_html

        # 4. Environment & configuration files (.env, .yaml, .yml, .json, .config)
        if '.env' in lower_name:
            if is_html:
                return False
            return b'=' in content or content.strip().startswith(b'#')

        if lower_name.endswith(('.yaml', '.yml', '.json', '.xml', '.config')):
            if is_html:
                return False
            return True

        # 5. Backup extensions (.bak, .old, .backup, .orig, .tmp)
        if any(lower_name.endswith(ext) for ext in ('.bak', '.old', '.backup', '.orig', '.tmp')):
            if is_html:
                login_markers = (b'<title>login', b'<title>404', b'<title>not found', b'<title>error', b'sign in')
                if any(m in content_preview for m in login_markers):
                    return False
            return True

        # 6. Default check: avoid saving HTML pages pretending to be files
        if is_html:
            login_markers = (b'<title>login', b'<title>404', b'<title>not found', b'<title>error', b'sign in', b'unauthorized')
            if any(m in content_preview for m in login_markers):
                return False

        return True

    def extract(self, url: str, content: bytes = None, headers: dict = None, session=None) -> dict:
        """
        Download and save a sensitive/backup file to disk with intelligent redirect following.
        If the file is an archive (.zip, .tar.gz, etc.), automatically unpack it.
        """
        if not self.enabled or not url:
            return None

        # Prevent duplicate extraction of the exact same URL in a single session
        if url in self._extracted_urls:
            for rec in self.extracted_records:
                if rec['url'] == url:
                    return rec

        parsed = urllib.parse.urlparse(url)
        domain = parsed.netloc.split(':')[0] or 'unknown_host'
        domain_clean = re.sub(r'[<>:"\\|?*]', '_', domain)
        target_dir = os.path.join(self.base_dir, domain_clean)
        os.makedirs(target_dir, exist_ok=True)

        req_session = session or self.session
        final_url = None

        # If content not provided, download it following redirects (Option 2)
        if content is None:
            try:
                import requests
                client = req_session if req_session else requests
                resp = client.get(url, timeout=15, verify=False, allow_redirects=True)
                if resp is None or resp.status_code != 200:
                    return None
                final_url = resp.url
                content = resp.content
                headers = resp.headers
            except Exception:
                return None

        if not content or len(content) == 0:
            return None

        # Intelligent content and redirect validation
        if not self.validate_file_content(url, content, final_url=final_url):
            return None

        # Determine target file destination
        raw_path = parsed.path or 'file'
        base_name = raw_path.split('/')[-1] or 'file'
        lower_name = base_name.lower()
        is_archive_ext = any(lower_name.endswith(ext) for ext in ('.zip', '.tar.gz', '.tgz', '.tar.bz2', '.tar'))

        # Determine target file destination
        file_path = self._sanitize_path(target_dir, raw_path)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # Write raw file bytes
        try:
            with open(file_path, 'wb') as f:
                f.write(content)
        except Exception as e:
            return None

        size = len(content)
        is_archive = False
        unpacked = False
        unpacked_dir = None

        # Check and unpack archive
        if is_archive_ext or content.startswith(b'PK\x03\x04'):
            is_archive = True
            unpacked_dir = file_path + '_extracted'
            unpacked = self._unpack_archive(file_path, unpacked_dir)

        rel_path = os.path.relpath(file_path, os.getcwd())
        rel_unpacked = os.path.relpath(unpacked_dir, os.getcwd()) if unpacked_dir else None

        record = {
            'url': url,
            'file_path': rel_path,
            'abs_path': file_path,
            'size': size,
            'is_archive': is_archive,
            'unpacked': unpacked,
            'unpacked_dir': rel_unpacked,
            'timestamp': datetime.now().isoformat()
        }

        self._extracted_urls.add(url)
        self.extracted_records.append(record)

        self._log_extraction(record)
        return record

    def _unpack_archive(self, archive_path: str, extract_to: str) -> bool:
        """Safely extract zip and tar archives preventing Zip Slip."""
        try:
            os.makedirs(extract_to, exist_ok=True)
            real_extract_to = os.path.realpath(extract_to)

            # Try ZipFile
            if zipfile.is_zipfile(archive_path):
                with zipfile.ZipFile(archive_path, 'r') as zf:
                    for member in zf.infolist():
                        target_path = os.path.realpath(os.path.join(extract_to, member.filename))
                        if not target_path.startswith(real_extract_to):
                            continue  # Prevent Zip Slip
                        zf.extract(member, extract_to)
                return True

            # Try TarFile
            if tarfile.is_tarfile(archive_path):
                with tarfile.open(archive_path, 'r:*') as tf:
                    # Safe extraction filter for modern python (3.12+) or manual check
                    if hasattr(tarfile, 'data_filter'):
                        tf.extractall(extract_to, filter='data')
                    else:
                        for member in tf.getmembers():
                            target_path = os.path.realpath(os.path.join(extract_to, member.name))
                            if not target_path.startswith(real_extract_to):
                                continue  # Prevent Tar Slip
                            tf.extract(member, extract_to)
                return True
        except Exception:
            return False
        return False

    def _log_extraction(self, record: dict):
        """Print log message on extraction."""
        size_str = self._format_size(record['size'])
        if HAS_RICH and console:
            console.print(f"[bold green][+] [LOOT EXTRACTED][/bold green] [cyan]{record['url']}[/cyan] -> [yellow]{record['file_path']}[/yellow] ({size_str})")
            if record.get('unpacked'):
                console.print(f"[bold green]    [-> UNPACKED ARCHIVE][/bold green] -> [yellow]{record['unpacked_dir']}[/yellow]")
        else:
            print(f"[+] [LOOT EXTRACTED] {record['url']} -> {record['file_path']} ({size_str})")
            if record.get('unpacked'):
                print(f"    [-> UNPACKED ARCHIVE] -> {record['unpacked_dir']}")

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        if size_bytes >= 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        elif size_bytes >= 1024:
            return f"{size_bytes / 1024:.1f} KB"
        return f"{size_bytes} bytes"

    @classmethod
    def extract_from_report(cls, report_path: str, base_dir: str = 'loot', session=None) -> list:
        """
        Parse an HTML or JSON report, extract all URLs found in 'Backup/sensitive file found'
        or 'File Exposed' findings, and download them.
        """
        if not os.path.isfile(report_path):
            if HAS_RICH and console:
                console.print(f"[red][!] Report file not found: {report_path}[/red]")
            else:
                print(f"[!] Report file not found: {report_path}")
            return []

        extractor = cls(base_dir=base_dir, enabled=True, session=session)
        target_urls = set()

        try:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        except Exception:
            pass

        try:
            with open(report_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # Pattern 1: Backup/sensitive file found: <url>
            pattern_backup = re.compile(r'Backup/sensitive file found:\s*(https?://[^\s<"\']+)', re.IGNORECASE)
            for m in pattern_backup.finditer(content):
                target_urls.add(m.group(1).rstrip('.'))

            # Pattern 2: JSON finding URLs or HTML evidence URLs
            pattern_url = re.compile(r'(https?://[^\s<"\']+\.(?:bak|old|backup|zip|tar\.gz|tgz|tar|sql|env|config|db))', re.IGNORECASE)
            for m in pattern_url.finditer(content):
                target_urls.add(m.group(1).rstrip('.'))

        except Exception as e:
            if HAS_RICH and console:
                console.print(f"[red][!] Error reading report: {e}[/red]")
            else:
                print(f"[!] Error reading report: {e}")
            return []

        if not target_urls:
            msg = "[yellow][!] No extractable backup or sensitive file URLs found in report.[/yellow]" if HAS_RICH else "[!] No extractable backup or sensitive file URLs found in report."
            if HAS_RICH and console:
                console.print(msg)
            else:
                print(msg)
            return []

        header = f"[bold cyan]Found {len(target_urls)} exposed file URLs in report. Attempting extraction...[/bold cyan]" if HAS_RICH else f"Found {len(target_urls)} exposed file URLs in report. Attempting extraction..."
        if HAS_RICH and console:
            console.print(header)
        else:
            print(header)

        extracted = []
        for url in sorted(target_urls):
            res = extractor.extract(url)
            if res:
                extracted.append(res)

        summary_msg = f"[bold green]Successfully extracted {len(extracted)}/{len(target_urls)} files to '{base_dir}/'[/bold green]" if HAS_RICH else f"Successfully extracted {len(extracted)}/{len(target_urls)} files to '{base_dir}/'"
        if HAS_RICH and console:
            console.print(summary_msg)
        else:
            print(summary_msg)

        return extracted
