"""The command line of the app's tool: its commands, the error line and the exit statuses.

Status 0 means the command did its work, 1 that it could not, with one line
`error: <reason>: <detail>` on standard error, and 2 that the command line was not
understood.
"""

import argparse
import signal
import sys
import threading

from . import Failure, build, device, toolchain, webserver

WAIT_SECONDS = 0.2


def _port(text):
    if not text.isascii() or not text.isdigit() or int(text) > 65535:
        raise argparse.ArgumentTypeError(f"{text!r} is not a port number from 0 to 65535")
    return int(text)


def parser():
    made = argparse.ArgumentParser(prog="python3 app/app.py", description="Sets up the build tools of the operators' app, builds its APK, installs it on a phone, and serves its web code to a browser.")
    commands = made.add_subparsers(dest="command", metavar="COMMAND", required=True)
    commands.add_parser("setup", help="put the build tools into app/node_modules/ and build/app/")
    commands.add_parser("build", help="build the debug APK, build/app/odrig-debug.apk")
    commands.add_parser("install", help="install the built APK on the one phone that is connected by USB")
    serve = commands.add_parser("serve", help="serve the web code on 127.0.0.1, for a browser on this computer")
    serve.add_argument("--port", metavar="N", type=_port, default=webserver.PORT, help=f"the port on 127.0.0.1; 0 takes any free port (default: {webserver.PORT})")
    return made


def _serve(arguments, out):
    """Serves the web code until a signal ends the command."""
    server = webserver.Server(arguments.port)
    stopped = threading.Event()
    for name in ("SIGINT", "SIGTERM", "SIGBREAK"):
        if hasattr(signal, name):
            signal.signal(getattr(signal, name), lambda *_: stopped.set())
    print(f"app: {server.url}", file=out, flush=True)
    server.start()
    # A wait without a limit is not interrupted by a signal on every system.
    while not stopped.wait(WAIT_SECONDS):
        pass
    server.stop()
    return 0


def _setup(arguments, out):
    toolchain.setup(out)
    return 0


def _build(arguments, out):
    build.build(out)
    return 0


def _install(arguments, out):
    return device.install(out)


ACTIONS = {"setup": _setup, "build": _build, "install": _install, "serve": _serve}


def main(argv=None, out=None):
    arguments = parser().parse_args(argv)
    try:
        return ACTIONS[arguments.command](arguments, sys.stdout if out is None else out)
    except Failure as failure:
        print(f"error: {failure.reason}: {failure.detail}", file=sys.stderr)
        return 1
