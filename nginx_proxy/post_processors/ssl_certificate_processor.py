import threading
from typing import List

from nginx_proxy import Host


class SslCertificateProcessor:

    def __init__(self):
        self.lock: threading.Condition = threading.Condition()

    def process_ssl_certificates(self, hosts: List[Host]):
        self.lock.acquire()

        for host in hosts:
            if host.secured:
                if int(host.port) in (80, 443):
                    host.port = 443
                    host.ssl_redirect = True

        self.lock.release()
