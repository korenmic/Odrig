"""The command line: the line that is sent, the printed reply and the exit statuses.

Exit status 0 means the reply has `"ok":true`, 1 that it has `"ok":false`, 2 that the
command line was not understood, and 3 that the target could not be reached or did not
answer in time.
"""

import argparse
import json
import sys

from . import client

# Each command and whether it takes its one argument.
COMMANDS = {"play": "ID", "on": None, "off": None, "brightness": "N", "status": None}
TIMEOUT_SECONDS = 2.0


def _seconds(text):
    try:
        seconds = float(text)
    except ValueError:
        seconds = -1.0
    if not 0 < seconds < float("inf"):
        raise argparse.ArgumentTypeError(f"{text!r} is not a number of seconds above 0")
    return seconds


def parser():
    made = argparse.ArgumentParser(
        prog="python -m odrigctl",
        description="Sends one command to a target, over its serial port or over HTTP, and prints the reply.",
        epilog="Commands: play ID, on, off, brightness N, status. ID and N are sent as they are typed.",
    )
    target = made.add_mutually_exclusive_group(required=True)
    target.add_argument("--port", metavar="NAME", help="the serial port of the target")
    target.add_argument("--http", metavar="ADDRESS", help="the address of the target: host or host:port")
    made.add_argument("--timeout", metavar="SECONDS", type=_seconds, default=TIMEOUT_SECONDS, help="how long to wait for the reply (default: 2)")
    made.add_argument("command", metavar="COMMAND", choices=sorted(COMMANDS), help="play, on, off, brightness or status")
    made.add_argument("argument", metavar="ARGUMENT", nargs="?", help="the ID of play, or the N of brightness")
    return made


def command_line(made, arguments):
    """The line for a command, with its newline. The argument goes into it as typed."""
    takes = COMMANDS[arguments.command]
    if takes is None and arguments.argument is not None:
        made.error(f"{arguments.command} takes no argument")
    if takes is not None and arguments.argument is None:
        made.error(f"{arguments.command} takes one argument: {takes}")
    if arguments.argument is not None and "\n" in arguments.argument:
        made.error("a command is one line")
    words = [arguments.command] if arguments.argument is None else [arguments.command, arguments.argument]
    return " ".join(words).encode("utf-8") + b"\n"


def main(argv=None):
    made = parser()
    arguments = made.parse_args(argv)
    line = command_line(made, arguments)
    try:
        if arguments.port is not None:
            reply = client.serial_exchange(arguments.port, line, arguments.timeout)
        else:
            reply = client.http_exchange(arguments.http, line, arguments.timeout)
            if not client.is_reply(reply):
                raise client.Unreachable(f"{arguments.http}: the answer is not a reply")
    except client.Unreachable as unreachable:
        print(f"error: unreachable: {unreachable}", file=sys.stderr)
        return 3
    print(reply.decode("utf-8", "replace"))
    return 0 if json.loads(reply)["ok"] is True else 1
