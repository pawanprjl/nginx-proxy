import difflib
import os
import pathlib
import random
import socket
import string
import subprocess
import sys
import time
from os import path
from typing import Union, Tuple

import requests

from nginx import Url


class Nginx:
    command_config_test = ["nginx", "-t"]
    command_start = ["nginx"]
    command_reload = ["nginx", "-s", "reload"]

    def __init__(self, config_file_path, challenge_dir="/tmp/acme-challenges/"):
        self.config_file_path = config_file_path
        self.challenge_dir = challenge_dir

        if path.exists(config_file_path):
            with open(config_file_path) as file:
                self.last_working_config = file.read()
        else:
            self.last_working_config = ""

        self.config_stack = [self.last_working_config]
        self.last_error = None
        if not os.path.exists(challenge_dir):
            pathlib.Path(self.challenge_dir).mkdir(parents=True)

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

    def verify_domain(self, _domain: list or str):
        """Verify that a domain is owned by the current machine.
        :param _domain: A list of domains to verify.
        :returns: True if the domain is owned by the current machine, False otherwise.
        """
        domains = [_domain] if type(_domain) is str else _domain

        # Filter out any invalid domains
        domains = [x for x in domains if Url.is_valid_hostname(x)]

        # generate a random challenge token
        unique_challenge_name = "".join(random.choices(string.ascii_letters + string.digits, k=32))
        challenge_token = "".join(random.choices(string.ascii_letters + string.digits, k=256))

        # write the challenge token to a file on the current machine.
        challenge_file = os.path.join(self.challenge_dir, unique_challenge_name)
        with open(challenge_file, mode="wt") as file_descriptor:
            file_descriptor.write(challenge_token)

        # try to access the challenge token from each domain
        success = []

        for domain in domains:
            try:
                url = f"http://{domain}/.well-known/acme-challenge/{unique_challenge_name}"
                response = requests.get(url, allow_redirects=False, timeout=3)
                if response.status_code == 200 and response.content.decode("utf-8") == challenge_token:
                    success.append(domain)
                    continue
                print(f"[ERROR] [{domain}] Not owned by this machine: Status Code[{response.status_code}] -> {url}",
                      file=sys.stderr)
                continue
            except requests.exceptions.RequestException as err:
                print(f"[ERROR] Domain is not owned by this machine: {err}", file=sys.stderr)
                continue

        # remove the challenge file from the current machine
        os.remove(challenge_file)

        # return the result
        return len(success) > 0 if type(_domain) is str else success

    def wait(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', 80))
        while result != 0:
            print("Waiting for nginx process to be ready")
            time.sleep(1)
            result = sock.connect_ex(('127.0.0.1', 80))
        sock.close()
        print("Nginx is alive")
