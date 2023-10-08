from typing import Set

from nginx_proxy.container import Container


class Host:
    """
    It is equivalent to a nginx server block.
    It contains the locations and information about which containers serve the location.
    """

    def __init__(self, hostname: str, port: int):
        self.hostname: str = hostname
        self.port: int = port
        self.container_set: Set[str] = set()

    def add_container(self, container: Container) -> None:
        self.container_set.add(container.id)

    def __repr__(self):
        return str({"server_name": self.hostname, "port": self.port})

    def __str__(self):
        return self.__repr__()
