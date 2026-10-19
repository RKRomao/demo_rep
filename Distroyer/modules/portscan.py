"""
Port Scanning Module
Scans common web & service ports, grabs banners
"""
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed
from .base import BaseModule


COMMON_PORTS = {
    21: 'FTP', 22: 'SSH', 23: 'Telnet', 25: 'SMTP', 53: 'DNS',
    80: 'HTTP', 110: 'POP3', 143: 'IMAP', 443: 'HTTPS',
    445: 'SMB', 993: 'IMAPS', 995: 'POP3S', 1433: 'MSSQL',
    1521: 'Oracle DB', 2375: 'Docker', 2376: 'Docker TLS',
    3000: 'Node/Rails', 3306: 'MySQL', 3389: 'RDP', 4000: 'App',
    4040: 'ngrok', 5000: 'Flask/Dev', 5432: 'PostgreSQL',
    5900: 'VNC', 6379: 'Redis', 7000: 'App', 8000: 'Dev HTTP',
    8008: 'HTTP Alt', 8080: 'HTTP Proxy', 8081: 'HTTP Alt',
    8443: 'HTTPS Alt', 8888: 'Jupyter/Dev', 9000: 'PHP-FPM',
    9090: 'Prometheus', 9200: 'Elasticsearch', 9300: 'ES Transport',
    27017: 'MongoDB', 27018: 'MongoDB', 28017: 'MongoDB HTTP',
}

HIGH_RISK_PORTS = {
    21: 'FTP - often unencrypted, weak auth',
    23: 'Telnet - unencrypted protocol, dangerous',
    2375: 'Docker daemon exposed WITHOUT TLS - critical risk',
    3389: 'RDP - brute-force and exploit target',
    5900: 'VNC - commonly misconfigured',
    6379: 'Redis - no auth by default, RCE risk',
    9200: 'Elasticsearch - no auth by default, data exposure',
    27017: 'MongoDB - no auth by default, data exposure',
}


class PortScanModule(BaseModule):
    """Port scanning and service detection module."""

    def run(self) -> dict:
        host = self.get_domain()
        threads = min(self.config.get('threads', 10), 50)

        open_ports = []
        with ThreadPoolExecutor(max_workers=threads) as executor:
            futures = {
                executor.submit(self._scan_port, host, port): port
                for port in COMMON_PORTS
            }
            for future in as_completed(futures):
                result = future.result()
                if result:
                    open_ports.append(result)

        open_ports.sort(key=lambda x: x['port'])

        self._analyze_open_ports(open_ports)

        # Salva as portas abertas no contexto compartilhado para módulos posteriores
        self.context['open_ports'] = open_ports
        self.context['ports_list'] = [p['port'] for p in open_ports]

        return self.result({'host': host, 'open_ports': open_ports})

    def _scan_port(self, host, port):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(min(self.timeout, 3))
            result = sock.connect_ex((host, port))
            if result == 0:
                banner = self._grab_banner(sock, port)
                sock.close()
                return {
                    'port': port,
                    'service': COMMON_PORTS.get(port, 'unknown'),
                    'banner': banner,
                    'state': 'open'
                }
            sock.close()
        except Exception:
            pass
        return None

    def _grab_banner(self, sock, port):
        """Attempt banner grab."""
        try:
            sock.settimeout(2)
            # Send HTTP request for web services
            if port in (80, 8080, 8000, 8008, 8081, 3000, 4000, 5000, 7000):
                sock.send(b'HEAD / HTTP/1.0\r\nHost: localhost\r\n\r\n')
            elif port == 21:
                pass  # FTP sends banner automatically
            elif port == 22:
                pass  # SSH sends banner automatically
            
            data = sock.recv(1024)
            raw = data.decode('utf-8', errors='ignore')[:200].strip()
            # Collapse multiline HTTP/service banners into a clean single line
            clean_banner = " ".join(line.strip() for line in raw.splitlines() if line.strip())
            return clean_banner[:120]
        except Exception:
            return ''

    def _analyze_open_ports(self, open_ports):
        if not open_ports:
            self.add_finding('Port Scan Complete', 'INFO', 'No open ports detected on common ports.')
            return

        port_list = ', '.join(f'{p["port"]}/{p["service"]}' for p in open_ports)
        self.add_finding(
            'Open Ports Detected',
            'INFO',
            f'{len(open_ports)} open port(s): {port_list}',
            '\n'.join(f'  {p["port"]}/{p["service"]}: {p["banner"][:50]}' for p in open_ports)
        )

        for p in open_ports:
            port = p['port']
            if port in HIGH_RISK_PORTS:
                self.add_finding(
                    f'High-Risk Service Open: Port {port}',
                    'HIGH',
                    HIGH_RISK_PORTS[port],
                    f'Port {port} ({p["service"]}) is open\nBanner: {p["banner"][:100]}',
                    f'Firewall port {port} from public access. Apply authentication.'
                )

            # Check for dev services in production
            dev_ports = {3000, 4000, 5000, 8000, 8080, 8888}
            if port in dev_ports:
                self.add_finding(
                    f'Development Service Exposed: Port {port}',
                    'MEDIUM',
                    f'Development/debug service running on port {port}',
                    f'Service: {p["service"]}',
                    'Disable development servers in production environments.'
                )

            # Banner analysis
            banner = p.get('banner', '').lower()
            if any(kw in banner for kw in ['openssh', 'ssh', 'server', 'apache', 'nginx', 'iis']):
                if any(v in banner for v in ['1.', '2.0', '2.2', '2.4.0', '2.4.1']):
                    self.add_finding(
                        f'Potentially Outdated Service: Port {port}',
                        'MEDIUM',
                        f'Service banner suggests potentially outdated software.',
                        f'Banner: {p["banner"][:200]}',
                        'Keep all services updated to latest stable versions.'
                    )
