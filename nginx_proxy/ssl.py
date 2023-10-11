import logging
import os
import shutil
from datetime import datetime
from os.path import join

import OpenSSL
from OpenSSL import crypto

from acme_nginx.AcmeV2 import AcmeV2
from nginx.nginx import Nginx


# used acme_nginx to manage ssl certificates from https://github.com/kshcherban/acme-nginx
class SSL:

    def __init__(self, ssl_path, nginx: Nginx):
        self.ssl_path = ssl_path
        self.nginx = nginx
        self.api_url = "https://acme-v02.api.letsencrypt.org/directory"
        print("Using letsencrypt url: ", self.api_url)

    def cert_file(self, domain):
        return os.path.join(self.ssl_path, "certs", domain + ".crt")

    def private_file(self, domain):
        return os.path.join(self.ssl_path, "private", domain + ".key")

    def selfsigned_cert_file(self, domain):
        return os.path.join(self.ssl_path, "certs", domain + ".selfsigned.cert")

    def selfsigned_private_file(self, domain):
        return os.path.join(self.ssl_path, "private", domain + "selfsgned.key")

    def self_sign(self, domain):
        CERT_FILE = domain + ".selfsigned.crt"
        KEY_FILE = domain + ".selfsigned.key"

        k = crypto.PKey()
        k.generate_key(crypto.TYPE_RSA, 1024)

        # create a self-signed cert
        cert = crypto.X509()
        cert.get_subject().C = "US"
        cert.get_subject().ST = "Subject_st"
        cert.get_subject().L = "Subject_l"
        cert.get_subject().O = "Nginx-Proxy - pawanprjl/nginx-proxy"
        # cert.get_subject().OU = "my organization"
        cert.get_subject().CN = domain
        cert.set_serial_number(1000)
        cert.gmtime_adj_notBefore(0)
        cert.gmtime_adj_notAfter(10 * 365 * 24 * 60 * 60)
        cert.set_issuer(cert.get_subject())
        cert.set_pubkey(k)
        cert.sign(k, 'sha256')

        open(join(self.ssl_path, "certs", CERT_FILE), "wb").write(
            crypto.dump_certificate(crypto.FILETYPE_PEM, cert))
        open(join(self.ssl_path, "private", KEY_FILE), "wb").write(
            crypto.dump_privatekey(crypto.FILETYPE_PEM, k))

    def expiry_time(self, domain) -> datetime:
        if self.cert_exists(domain):
            with open(self.cert_file(domain)) as file:
                x509 = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, file.read())
                return datetime.strptime(x509.get_notAfter().decode(), "%Y%m%d%H%M%SZ")
        return datetime.now()

    def cert_exists(self, domain):
        return os.path.exists(self.cert_file(domain)) and os.path.exists(self.private_file(domain))

    def wildcard_domain_name(self, domain):
        slices = domain.split('.')
        if len(slices) > 2:
            return '*.' + ('.'.join(slices[1:len(slices)]))
        return None

    def cert_exists_self_signed(self, domain) -> bool:
        return self.cert_exists((domain + ".selfsigned"))

    def reuse(self, domain1, domain2):
        shutil.copy2(os.path.join(self.ssl_path, "certs", domain1 + ".crt"),
                     os.path.join(self.ssl_path, "certs", domain2 + ".crt"))
        shutil.copy2(os.path.join(self.ssl_path, "private", domain1 + ".key"),
                     os.path.join(self.ssl_path, "private", domain2 + ".key"))
        shutil.copy2(os.path.join(self.ssl_path, "accounts", domain1 + ".account.key"),
                     os.path.join(self.ssl_path, "accounts", domain2 + ".account.key"))

    def register_certificate(self, domain, no_self_check=False, ignore_existing=False):
        if type(domain) is str:
            domain = [domain]
        domain = [d for d in domain if
                  '.' in d]  # when the domain doesn't have '.' it shouldn't be requested for letsencrypt certificate
        verified_domain = domain if no_self_check else self.nginx.verify_domain(domain)
        domain = verified_domain if ignore_existing else [x for x in verified_domain if not self.cert_exists(x)]
        if len(domain):
            logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.DEBUG)
            acme = AcmeV2(
                self.nginx,
                api_url=self.api_url,
                logger=logging.getLogger("acme"),
                domains=domain,
                account_key=os.path.join(self.ssl_path, "accounts", domain[0] + ".account.key"),
                domain_key=os.path.join(self.ssl_path, "private", domain[0] + ".key"),
                cert_path=os.path.join(self.ssl_path, "certs", domain[0] + ".crt"),
                debug=False,
                dns_provider=None,
                skip_nginx_reload=False,
                challenge_dir=self.nginx.challenge_dir
            )
            directory = acme.register_account()
            return domain if acme.solve_http_challenge(directory) else []
        else:
            print("[SSL-Register] the files already so ignored: " + str(domain))
            return verified_domain

    def register_certificate_or_self_sign(self, domain, no_self_check=False, ignore_existing=False):
        print("[CertificateOrSelfSign] Adding domains:", domain)
        obtained_certificates = []

        for i in range(0, len(domain), 50):
            # only fifty at a time
            sub_list = domain[i:i + 50]
            obtained = self.register_certificate(sub_list, no_self_check=no_self_check, ignore_existing=ignore_existing)
            if len(obtained):
                domain1 = obtained[0]
                for x in obtained[1:]:
                    self.reuse(domain1, x)
                obtained_certificates.extend(obtained)

        obtained_set = set(obtained_certificates)
        self_signed = [x for x in domain if x not in obtained_set]
        if len(self_signed):
            print("[Self Signing Certificates]", self_signed)
        self.register_certificate_self_sign(self_signed)
        return obtained_certificates

    def register_certificate_self_sign(self, domains):
        if type(domains) is str:
            self.self_sign(domains)
        else:
            for domain in domains:
                if not self.cert_exists_self_signed(domain):
                    self.self_sign(domain)
