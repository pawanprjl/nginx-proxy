from typing import Set, Dict

from nginx_proxy.container import Container
from nginx_proxy.location import Location


class Host:
    """
    It is equivalent to a nginx server block.
    It contains the locations and information about which containers serve the location.
    """

    def __init__(self, hostname: str, port: int, scheme=None):
        if scheme is None:
            scheme = {'http', }

        self.hostname: str = hostname
        self.port: int = port
        self.scheme: set = scheme
        self.locations: Dict[str, Location] = {}  # the map of locations.and the container that serve the locations
        self.container_set: Set[str] = set()
        self.secured: bool = 'https' in scheme or 'wss' in scheme

    def add_container(self, location: str, container: Container, http=True) -> None:
        if location not in self.locations:
            self.locations[location] = Location(location, is_http_backend=http)
        self.locations[location].add(container)
        self.container_set.add(container.id)

    def remove_container(self, container_id) -> bool:
        removed = False
        deletions = []
        if container_id in self.container_set:
            for path, location in self.locations.items():
                removed = location.remove(container_id) or removed
                if location.is_empty():
                    deletions.append(path)
            for path in deletions:
                del self.locations[path]
            if removed:
                self.container_set.remove(container_id)
        return removed

    def is_empty(self) -> bool:
        return len(self.container_set) == 0

    def __repr__(self):
        return str({
            "scheme": self.scheme,
            "server_name": self.hostname,
            "port": self.port,
            "locations": self.locations
        })

    def __str__(self):
        return self.__repr__()
