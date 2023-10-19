import copy
import os
import sys
from typing import List

import requests
from docker import DockerClient
from docker.models.containers import Container as DockerContainer
from jinja2 import Template

from nginx.nginx import Nginx
from nginx_proxy import ProxyConfigData, pre_processors, Host, post_processors


def strip_end(string: str, char="/"):
    return string[:-1] if string.endswith(char) else string


def loadconfig():
    return {
        'config_dir': strip_end(os.getenv('NGINX_CONFIG_DIR', '/etc/nginx/')),
        'ssl_dir': strip_end(os.getenv('SSL_DIR', '/etc/ssl/')),
        'challenge_dir': os.getenv('CHALLENGE_DIR', '/tmp/acme-challenges/'),
    }


class WebServer:

    def __init__(self, client: DockerClient):
        self.id = None
        self.container = None
        self.client = client
        self.config = loadconfig()
        self.conf_file_name = self.config['config_dir'] + "/conf.d/default.conf"
        self.nginx = Nginx(self.conf_file_name)
        self.config_data = ProxyConfigData()
        self.networks = {}
        file = open("vhosts_template/default.conf.jinja2")
        self.template = Template(file.read())
        file.close()
        self.learn_yourself()
        self.ssl_processor = post_processors.SslCertificateProcessor(self.nginx, self, ssl_dir=self.config['ssl_dir'])

        if self.nginx.config_test():
            if len(self.nginx.last_working_config) < 50:
                print("Writing default config before reloading server.")
                if not self.nginx.force_start(self.template.render(config=self.config)):
                    print("Nginx failed when reloaded with default config", file=sys.stderr)
                    print("Exiting .....", file=sys.stderr)
                    exit(1)
            elif not self.nginx.start():
                print("ERROR: Config test succeeded but nginx failed to start", file=sys.stderr)
                print("Exiting .....", file=sys.stderr)
                exit(1)
        else:
            print("ERROR: Existing nginx configuration has error, trying to override with default configuration",
                  file=sys.stderr)
            if not self.nginx.force_start(self.template.render(config=self.config)):
                print("Nginx failed when reloaded with default config", file=sys.stderr)
                print("Exiting .....", file=sys.stderr)
                exit(1)

        self.nginx.wait()

        self.rescan_all_container()
        self.reload()
        self.ssl_processor.certificate_expiry_thread.start()

    def learn_yourself(self):
        """
        Look at its own filesystem to find out the container in which it is running.
        Recognizing which container this code is running helps us to know the networks accessible
        from this container and find all other accessible containers.
        :return:
        """
        try:
            hostname = os.getenv("HOSTNAME")
            if hostname is None:
                raise Exception("HOSTNAME environment variable not set")
            self.container = self.client.containers.get(hostname)
            self.id = self.container.id
            self.networks = {self.client.networks.get(a).id: a
                             for a in self.container.attrs["NetworkSettings"]["Networks"].keys()}
        except (KeyboardInterrupt, SystemExit) as err:
            raise err
        except Exception as err:
            print("[ERROR]Couldn't determine container ID of this container:", err.args,
                  "\n Is it running in docker environment?", file=sys.stderr)
            print("Falling back to default network", file=sys.stderr)
            network = self.client.networks.get("frontend")
            self.networks[network.id] = network.id

    def _register_container(self, container: DockerContainer) -> bool:
        """
        Find the details about container and register it and return True.
        If it's not configured with desired settings or is not accessible, return False
        :return: True if the container is added to virtual hosts, false otherwise.
        """
        known_networks = set(self.networks.keys())
        hosts = pre_processors.process_virtual_hosts(container, known_networks)
        if len(hosts):
            hosts.print()
            for h in hosts.host_list():
                self.config_data.add_host(h)
        return len(hosts) > 0

    def reload(self, forced=False) -> bool:
        """
        Creates a new configuration based on current state and signals nginx to reload.
        This is called whenever there's change in container or network state.
        """
        hosts: List[Host] = []
        for host_data in self.config_data.host_list():
            host = copy.deepcopy(host_data)

            for i, location in enumerate(host.locations.values()):
                location.container = list(location.containers)[0]

                if len(location.containers) > 1:
                    print("WARNING: Multiple containers for a single location", file=sys.stderr)
                    # todo: this means that there are multiple containers for a single location
                    # definitely should be using some load balancing here

            hosts.append(host)

        self.ssl_processor.process_ssl_certificates(hosts)

        output = self.template.render(virtual_servers=hosts, config=self.config)
        response = self.nginx.update_config(output)
        return response

    def connect(self, network, container):
        if self.id is not None and container == self.id:
            if network not in self.networks:
                self.networks[network] = self.client.networks.get(network).name
                self.rescan_and_reload()
        elif network in self.networks:
            self.update_container(container)

    def disconnect(self, network, container):
        if self.id is not None and container == self.id:
            if network in self.networks:
                del self.networks[network]
                self.rescan_and_reload()
        elif container in self.config_data.containers and network in self.networks:
            if not self.update_container(container):
                self.remove_container(container)
                self.reload()

    def update_container(self, container_id) -> bool:
        """
        Rescan the container to detect changes. And update nginx configuration if necessary.
        This is usually called in one of the following conditions:
        -- new container is started
        -- an existing container has left a network in which nginx-proxy is connected.
        -- during full container rescan
        :param container_id: container id to update
        :return: true if container state change affected the nginx configuration else false
        """
        try:
            if not self.config_data.has_container(container_id):
                if self._register_container(self.client.containers.get(container_id)):
                    self.reload()
                    return True
        except requests.exceptions.HTTPError as e:
            pass
        return False

    def remove_container(self, container_id: str):
        """
        Removes container from the maintained list.
        This is called when a container dies or leaves a known network.
        """
        deleted, deleted_domain = self.config_data.remove_container(container_id)
        if deleted:
            self.reload()

    def rescan_all_container(self):
        """
        Rescan all the containers to detect changes, update nginx config if necessary.
        This is called in one of the following conditions:
        -- in the beginning of execution of the program
        """
        containers = self.client.containers.list()
        self.config_data.containers = set()
        self.config_data.config_map = {}
        for container in containers:
            self._register_container(container)

    def rescan_and_reload(self):
        self.rescan_all_container()
        self.reload()

    def cleanup(self):
        self.ssl_processor.shutdown()
