from typing import Set, Any, Dict

from nginx_proxy.container import Container


class Location:
    """
    Location Represents the Location block in server block
    """

    def __init__(self, name, is_websocket_backend=False, is_http_backend=False):
        self.http = is_http_backend
        self.websocket = is_websocket_backend
        self.name = name
        self.containers: Set[Container] = set()
        self.extras: Dict[str, Any] = {}

    def __repr__(self):
        return str({
            "name": self.name,
            "containers": self.containers,
            "websocket": self.websocket,
            "extras": self.extras
        })

    def __eq__(self, other) -> bool:
        if type(other) is Location:
            return other.name == self.name
        return False

    def add(self, container: Container):
        self.containers.add(container)

    def remove(self, container: Container) -> bool:
        if container in self.containers:
            self.containers.remove(container)
            return True
        return False

    def is_empty(self) -> bool:
        return len(self.containers) == 0

    def update_extras(self, extras: Dict[str, Any]):
        for x in extras:
            if x in self.extras:
                data = self.extras[x]
                if type(data) in (dict, set):
                    self.extras[x].update(extras[x])
                elif type(data) in list:
                    self.extras[x].extend(extras[x])
                else:
                    self.extras[x] = extras[x]
            else:
                self.extras[x] = extras[x]
