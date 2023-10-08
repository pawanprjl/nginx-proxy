import signal
import sys

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
    server = WebServer()
except (KeyboardInterrupt, SystemExit):
    print("-------------------------------\nPerforming Graceful ShutDown !!")
