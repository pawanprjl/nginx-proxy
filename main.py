import signal
import sys
import traceback

import docker

from nginx_proxy.webserver import WebServer

server = None


# handle exit signal to respond to stop command.
def receive_signal(signal_number, frame):
    global server
    if signal_number == 15:
        print("\nShutdown Requested")
        if server is not None:
            server = None
        sys.exit(0)


signal.signal(signal.SIGTERM, receive_signal)

try:
    client = docker.from_env()
    client.version()
except Exception as e:
    print(
        "There was error connecting with the docker server \nHave you correctly mounted /var/run/docker.sock?\n" +
        str(e.args), file=sys.stderr)
    sys.exit(1)


def event_loop():
    for event in client.events(decode=True):
        try:
            event_type = event['Type']
            if event_type == "container":
                process_container_event(event['Action'], event)
        except (KeyboardInterrupt, SystemExit) as err:
            raise err
        except Exception as err:
            print("Unexpected error :" + err.__class__.__name__ + ' -> ' + str(err), file=sys.stderr)
            traceback.print_exc(limit=10)


def process_container_event(action, event):
    if action == "start":
        print("container started", event["id"])
        server.update_container(event["id"])
    elif action == "die":
        print("container died", event["id"])
        server.remove_container(event["id"])


try:
    server = WebServer(client)
    event_loop()
except (KeyboardInterrupt, SystemExit):
    print("-------------------------------\nPerforming Graceful ShutDown !!")
