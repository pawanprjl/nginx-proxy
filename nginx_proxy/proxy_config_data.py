from typing import Set, Dict, Generator

from nginx_proxy.host import Host


class ProxyConfigData:
    """
    All the configuration data that are obtained from the current state of container.
    nginx or any other reverse proxy configuration can be generated using the data available here.
    """

    def __init__(self):
        # map the hostname -> port -> host_configuration
        self.config_map: Dict[str, Dict[int, Host]] = {}
        self.containers: Set[str] = set()
        self._len = 0

    def __len__(self):
        return self._len

    def add_host(self, host: Host) -> None:
        if host.hostname in self.config_map:
            pass
        else:
            self._len = self._len + 1
            self.config_map[host.hostname] = {host.port: host}

    def has_container(self, container_id):
        return container_id in self.containers

    def host_list(self) -> Generator[Host, None, None]:
        for host_map in self.config_map.values():
            for host in host_map.values():
                yield host
