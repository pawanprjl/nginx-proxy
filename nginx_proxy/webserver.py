import os
import sys

from jinja2 import Template

from nginx.nginx import Nginx


def strip_end(string: str, char="/"):
    return string[:-1] if string.endswith(char) else string


def loadconfig():
    return {
        'config_dir': strip_end(os.getenv('NGINX_CONFIG_DIR', '/etc/nginx/')),
    }


class WebServer:

    def __init__(self):
        self.config = loadconfig()
        self.conf_file_name = self.config['config_dir'] + "/conf.d/default.conf"
        self.nginx = Nginx(self.conf_file_name)
        file = open("vhosts_template/default.conf.jinja2")
        self.template = Template(file.read())
        file.close()

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

        self.reload()

    def reload(self, forced=False) -> bool:
        """
        Creates a new configuration based on current state and signals nginx to reload.
        This is called whenever there's change in container or network state.
        """
        output = self.template.render(config=self.config)
        response = self.nginx.update_config(output)
        return response
