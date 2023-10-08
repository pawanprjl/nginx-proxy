def split_url(entry_string: str, default_scheme=[], default_port=None, default_location=None):
    """
    Split the url into scheme, host, port and location
    """
    split_scheme = entry_string.strip().split("://", 1)
    scheme, host_part = split_scheme if len(split_scheme) == 2 else (default_scheme, split_scheme[0])
    host_entries = host_part.split("/", 1)
    hostport, location = (host_entries[0], "/" + host_entries[1]) if len(host_entries) == 2 else (
        host_entries[0], default_location)
    hostport_entries = hostport.split(":", 1)
    host, port = hostport_entries if len(hostport_entries) == 2 else (hostport_entries[0], default_port)

    return {
        "scheme": set([x for x in scheme.split("+") if x]) if scheme else default_scheme,
        "host": host if host else None,
        "port": port,
        "location": location
    }
