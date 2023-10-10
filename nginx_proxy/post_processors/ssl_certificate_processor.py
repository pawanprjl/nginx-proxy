import threading
from datetime import date, datetime
from typing import List, Set, Dict, Union

from nginx.nginx import Nginx
from nginx_proxy import Host
from nginx_proxy import webserver
from nginx_proxy.ssl import SSL


class SslCertificateProcessor:

    def __init__(self, nginx: Nginx, server: webserver, ssl_dir="/etc/ssl"):
        self.cache: Dict[str:date] = {}
        self.self_signed: Set[str] = set()
        self.lock: threading.Condition = threading.Condition()
        self.nginx: Nginx = nginx
        self.ssl: SSL = SSL(ssl_dir, nginx)
        self.server: webserver = server
        self.next_ssl_expiry: Union[datetime, None] = None

    def process_ssl_certificates(self, hosts: List[Host]):
        ssl_requests: Set[Host] = set()
        self.lock.acquire()
        for host in hosts:
            if host.secured:
                if int(host.port) in (80, 443):
                    host.port = 443
                    host.ssl_redirect = True

                if host.hostname in self.cache:
                    host.ssl_file = host.hostname
                else:
                    wildcard = self.ssl.wildcard_domain_name(host.hostname)
                    if wildcard is not None:
                        if self.ssl.cert_exists(wildcard):
                            host.ssl_file = wildcard
                            continue

                    # check if the certificate is expired or not
                    time = self.ssl.expiry_time(host.hostname)
                    if (time - datetime.now()).days > 2:
                        self.cache[host.hostname] = time
                        host.ssl_file = host.hostname
                    else:
                        ssl_requests.add(host)

        if len(ssl_requests):
            print("process_ssl_certificates.ssl_requests: ", ssl_requests)
            registered = self.ssl.register_certificate_or_self_sign([h.hostname for h in ssl_requests],
                                                                    ignore_existing=True)

            for host in ssl_requests:
                if host.hostname not in registered:
                    host.ssl_file = host.hostname + ".selfsigned"
                    self.self_signed.add(host.hostname)
                else:
                    host.ssl_file = host.hostname
                    self.cache[host.hostname] = self.ssl.expiry_time(host.hostname)
                    host.ssl_expiry = self.cache[host.hostname]

        if len(self.cache):
            expiry = min(self.cache.values())
            if expiry != self.next_ssl_expiry:
                self.next_ssl_expiry = expiry
                self.lock.notify()

        self.lock.release()
