import difflib
import socket
import subprocess
import sys
import time
from os import path
from typing import Union, Tuple


class Nginx:
    command_config_test = ["nginx", "-t"]
    command_start = ["nginx"]
    command_reload = ["nginx", "-s", "reload"]

    def __init__(self, config_file_path):
        self.config_file_path = config_file_path
        if path.exists(config_file_path):
            with open(config_file_path) as file:
                self.last_working_config = file.read()
        else:
            self.last_working_config = ""
        self.config_stack = [self.last_working_config]
        self.last_error = None

    def start(self) -> bool:
        """
        Starts the nginx server
        :return: True if nginx starts successfully otherwise false
        """
        start_result = subprocess.run(Nginx.command_start, stderr=subprocess.PIPE)
        if start_result.returncode != 0:
            print(start_result.stderr, file=sys.stderr)
        return start_result.returncode == 0

    def config_test(self) -> bool:
        """
        Test the current nginx configuration to determine whether it fails
        :return: true if config test is successful otherwise false
        """
        test_result = subprocess.run(Nginx.command_config_test, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if test_result.returncode != 0:
            print("Nginx config test failed!", file=sys.stderr)
            self.last_error = test_result.stderr.decode("utf-8")
            print(self.last_error, file=sys.stderr)
            return False
        return True

    def force_start(self, config_str) -> bool:
        """
        Simply reload the nginx with the configuration, don't check if configuration is changed.
        If change causes nginx to fail, revert to last working config.
        :param config_str: nginx config to start server with
        :return: true if force start is successful, otherwise false.
        """
        with open(self.config_file_path, "w") as file:
            file.write(config_str)
        if not self.start():
            with open(self.config_file_path, "w") as file:
                file.write(self.last_working_config)
            return False
        else:
            self.last_working_config = config_str
            return True

    def update_config(self, config_str) -> bool:
        """
        Change the nginx configuration
        :param config_str: string containing configuration to be written into config file
        :return: true if the new config was used, false if error or if the new configuration is same as previous
        """
        if config_str == self.last_working_config:
            print("Configuration not changed, skipping nginx reload")
            return False

        with open(self.config_file_path, "w") as file:
            file.write(config_str)

        result, data = self.reload(return_error=True)
        if not result:
            diff = str.join("\n", difflib.unified_diff(self.last_working_config.splitlines(),
                                                       config_str.splitlines(),
                                                       fromfile='Old Config',
                                                       tofile='New Config',
                                                       lineterm='\n'))
            print(diff, file=sys.stderr)
            if data is not None:
                print(data, file=sys.stderr)
            print("ERROR: New change made nginx to fail. Thus it's rolled back", file=sys.stderr)
            with open(self.config_file_path, "w") as file:
                file.write(self.last_working_config)
            return False
        else:
            print("Nginx Reloaded Successfully")
            self.last_working_config = config_str
            return True

    def reload(self, return_error=False) -> Union[bool, Tuple[bool, Union[str, None]]]:
        """
        Reload nginx so that new configurations are applied.
        :return: true if nginx reload was successful, false otherwise
        """
        reload_result = subprocess.run(Nginx.command_reload, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if reload_result.returncode != 0:
            if return_error:
                return False, reload_result.stderr.decode('utf-8')
            else:
                print("Nginx reload failed with exit code ", file=sys.stderr)
                print(reload_result.stderr.decode("utf-8"), file=sys.stderr)
                result = False
        else:
            result = True

        if return_error:
            return result, None
        else:
            return result

    def wait(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', 80))
        while result != 0:
            print("Waiting for nginx process to be ready")
            time.sleep(1)
            result = sock.connect_ex(('127.0.0.1', 80))
        sock.close()
        print("Nginx is alive")
