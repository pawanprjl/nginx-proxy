from docker.models.containers import Container as DockerContainer

from nginx_proxy import ProxyConfigData, Host
from nginx_proxy.container import NoHostConfiguration, UnreachableNetwork, Container
from nginx_proxy.utils import split_url


def process_virtual_hosts(container: DockerContainer, known_networks: set) -> ProxyConfigData:
    hosts = ProxyConfigData()
    try:
        for host, location, proxied_container, extras in host_generator(container, known_networks=known_networks):
            http = 'http' in host.scheme or 'https' in host.scheme
            if type(host) is not str:
                host.add_container(location, proxied_container, http=http)
                if len(extras):
                    host.locations[location].update_extras({'injected': extras})
                hosts.add_host(host)
    except NoHostConfiguration:
        print("No VIRTUAL_HOST       ", "Id:" + container.id[:12],
              "    " + container.attrs["Name"].replace("/", ""), sep="\t")
    except UnreachableNetwork:
        print("Unreachable Network   ", "Id:" + container.id[:12],
              "    " + container.attrs["Name"].replace("/", ""), sep="\t")
    return hosts


def host_generator(container: DockerContainer, known_networks: set = {}):
    network_settings: dict = container.attrs["NetworkSettings"]
    env_map = Container.get_env_map(container)

    virtual_hosts = [x[1] for x in env_map.items() if x[0].startswith("VIRTUAL_HOST")]
    if len(virtual_hosts) == 0:
        raise NoHostConfiguration()

    # instead of directly accessing container details, check if they are accessible through networks
    for name, detail in network_settings["Networks"].items():
        if detail["Aliases"] is not None:
            if detail["NetworkID"] in known_networks:
                ip_address = detail["IPAddress"]
                if ip_address:
                    break
            else:
                raise UnreachableNetwork()

    for host_config in virtual_hosts:
        host, location, container_data, extras = _parse_host_entry(host_config)
        container_data.id = container.id
        container_data.address = ip_address
        # if port is none, fetch from network settings else set default 80
        if container_data.port is None:
            if len(network_settings["Ports"]) == 1:
                container_data.port = int(list(network_settings["Ports"].keys())[0].split("/")[0])
            else:
                container_data.port = 80

        host.secured = 'https' in host.scheme or host.port == 443
        yield host, location, container_data, extras


def _parse_host_entry(entry_string: str) -> (Host, str):
    configs = entry_string.split(";", 1)
    extras = set()
    if len(configs) > 1:
        entry_string = configs[0]
        for x in configs[1].split(';'):
            x = x.strip()
            if x:
                extras.add(x)

    # We need both external and internal host mapping, so we split them.
    host_list = entry_string.strip().split("->")
    external, internal = host_list if len(host_list) == 2 else (host_list[0], "")
    external, internal = (split_url(external), split_url(internal))

    # create container config from internal host mapping.
    container = Container(
        scheme=list(internal['scheme'])[0] if len(internal['scheme']) else 'http',
        address=internal["host"] if internal["host"] else None,
        port=internal["port"] if internal["port"] else None,
        path=internal["location"] if internal["location"] else "/",
    )

    # create host config from external host mapping.
    host = Host(
        hostname=external["host"] if external["host"] else None,
        # having https port on 80 will be detected later and used for redirection.
        port=int(external["port"]) if external["port"] else 80,
        scheme=external["scheme"] if external["scheme"] else {"http"}
    )

    location = external["location"] if external["location"] else "/"

    return host, location, container, extras
