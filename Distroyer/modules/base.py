"""
Base Module - All test modules inherit from this
"""
import requests
import time
import urllib.parse
from abc import ABC, abstractmethod


class BaseModule(ABC):
    """Base class for all Distroyer test modules."""
    
    def __init__(self, config: dict):
        self.config = config
        self.url = config['url']
        self.timeout = config.get('timeout', 10)
        self.delay = config.get('delay', 0.1)
        self.verbose = config.get('verbose', False)
        self.findings = []
        
        # Shared Scan Context (endpoints, forms, scripts, loot, etc.)
        self.context = config.get('context')
        if self.context is None:
            self.context = {}
            config['context'] = self.context

        # Centralized Network Manager
        from .network import NetworkManager
        self.network = config.get('network')
        if self.network is None:
            self.network = NetworkManager(config)
            config['network'] = self.network

        self.session = self.network.session

        # Extractor (loot)
        from .extractor import FileExtractor
        self.extractor = config.get('extractor')
        if self.extractor is None:
            self.extractor = FileExtractor(
                base_dir=config.get('loot_dir', 'loot'),
                enabled=config.get('extract', True),
                session=self.session
            )
            config['extractor'] = self.extractor
    
    @abstractmethod
    def run(self) -> dict:
        """Run the module and return results dict."""
        pass
    
    def get(self, url, **kwargs):
        """GET with centralized retry, backoff, and scope guard."""
        return self.network.get(url, **kwargs)
    
    def post(self, url, data=None, json=None, **kwargs):
        """POST with centralized retry, backoff, and scope guard."""
        return self.network.post(url, data=data, json=json, **kwargs)

    def head(self, url, **kwargs):
        """HEAD request."""
        return self.network.head(url, **kwargs)

    def options(self, url, **kwargs):
        """OPTIONS request."""
        return self.network.options(url, **kwargs)
    
    def extract_file(self, url, content=None, headers=None):
        """Extract/download discovered sensitive or backup file."""
        if self.extractor:
            return self.extractor.extract(url, content=content, headers=headers, session=self.session)
        return None

    def add_finding(self, title, severity, detail='', evidence='', recommendation='', loot=None):
        """Add a finding to results."""
        # Auto-extract if it's a backup or exposed file and not already explicitly extracted
        if loot is None and self.extractor and self.config.get('extract', True):
            lower_text = f"{title} {detail} {evidence}".lower()
            trigger_keywords = (
                'backup/sensitive file found',
                'backup file exposed',
                'sensitive file exposed',
                'file exposed',
                'git repository exposed',
                'svn repository exposed',
            )
            if any(tk in lower_text for tk in trigger_keywords):
                import re
                urls = re.findall(r'https?://[^\s<"\']+', f"{detail} {evidence}")
                if urls:
                    loot = self.extract_file(urls[0])
                elif evidence.startswith('/') or detail.startswith('/'):
                    path = evidence if evidence.startswith('/') else detail.split()[0]
                    loot = self.extract_file(f"{self.get_base_url()}{path}")

        if loot:
            loot_note = f"\n[Extracted to: {loot['file_path']}]"
            if loot.get('unpacked') and loot.get('unpacked_dir'):
                loot_note += f"\n[Archive unpacked to: {loot['unpacked_dir']}]"
            if loot_note not in evidence:
                evidence = (evidence + loot_note).strip()

        finding = {
            'title': title,
            'severity': severity,  # CRITICAL, HIGH, MEDIUM, LOW, INFO
            'detail': detail,
            'evidence': evidence,
            'recommendation': recommendation,
            'loot': loot,
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S')
        }
        self.findings.append(finding)
        return finding
    
    def result(self, extra=None):
        """Build the standard result dict."""
        data = {'findings': self.findings}
        if extra:
            data.update(extra)
        return data
    
    def get_parsed_url(self, url=None):
        """Return urllib parsed URL."""
        return urllib.parse.urlparse(url or self.url)
    
    def get_domain(self):
        return self.get_parsed_url().netloc.split(':')[0]
    
    def get_base_url(self):
        p = self.get_parsed_url()
        return f"{p.scheme}://{p.netloc}"
