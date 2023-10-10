import re


class Url:
    root: 'Url' = None

    def __init__(self):
        pass

    @staticmethod
    def is_valid_hostname(hostname: str) -> bool:
        """
        https://stackoverflow.com/a/33214423/2804342
        :return: True if for valid hostname False otherwise
        """
        if hostname[-1] == ".":
            # strip exactly one dot from the right, if present
            hostname = hostname[:-1]
        if len(hostname) > 253:
            return False

        labels = hostname.split(".")

        # the TLD must be not all-numeric
        if re.match(r"[0-9]+$", labels[-1]):
            return False

        allowed = re.compile(r"(?!-)[a-z0-9-]{1,63}(?<!-)$", re.IGNORECASE)
        return all(allowed.match(label) for label in labels)
