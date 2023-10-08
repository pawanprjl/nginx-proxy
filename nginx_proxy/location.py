from typing import Set

from nginx_proxy.container import Container


class Location:
    """
    Location Represents the Location block in server block
    """

    def __init__(self, name):
        self.name = name
        self.containers: Set[Container] = set()

    def __repr__(self):
        return str({"name": self.name, "containers": self.containers})

    def add(self, container: Container):
        self.containers.add(container)

    def remove(self, container: Container) -> bool:
        if container in self.containers:
            self.containers.remove(container)
            return True
        return False

    def is_empty(self) -> bool:
        return len(self.containers) == 0
