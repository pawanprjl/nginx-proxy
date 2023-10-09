from typing import Union

from docker.models.containers import Container as DockerContainer


class Container:

    def __init__(self, id: str = None, scheme: Union[str] = 'http', address=None, port=None, path=None):
        self.id = id
        self.address: str = address
        self.port: int = port
        self.path: Union[str, None] = path
        self.scheme: str = scheme
        self.networks = set()  # the list networks through which this container is accessible.

    def __repr__(self):
        return str({
            "scheme": self.scheme,
            "address": self.address,
            "port": self.port,
            "path": self.path
        })

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other) -> bool:
        if type(other) is Container:
            return self.id == other.id
        if type(other) is str:
            return self.id == other
        return False

    def add_network(self, network_id: str):
        self.networks.add(network_id)

    @staticmethod
    def get_env_map(container: DockerContainer):
        # first we get the list of tuples each containing data in form (key, value)
        env_list = [x.split("=", 1) for x in container.attrs['Config']['Env']]
        # convert the environment list into map
        return {x[0]: x[1].strip() for x in env_list if len(x) == 2}


class MisconfiguredContainer(Exception):
    pass


class UnreachableNetwork(MisconfiguredContainer):
    pass


class NoHostConfiguration(MisconfiguredContainer):
    pass
