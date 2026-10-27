"""The command line: the lines that are sent, the printed replies and the exit statuses.

Exit status 0 means every reply has `"ok":true`, 1 that a reply has `"ok":false`, 2 that
the command line was not understood or the file to upload cannot be read, and 3 that the
target could not be reached or did not answer in time. With `--log` the tool prints the
target's log until it is interrupted, which is exit status 0.
"""

import argparse
import os
import signal
import sys
import time

from . import client, content

# Each command and the arguments it takes.
COMMANDS = {
    "play": ("ID",),
    "on": (),
    "off": (),
    "brightness": ("N",),
    "status": (),
    "fault": (),
    "space": (),
    "list": (),
    "read": ("ID", "OFFSET"),
    "catalog": ("[OPERATION]",),
    "remove": ("ID",),
    "ignore": ("ID", "VALUE"),
    "mapping": ("OPERATION",),
    "order": ("OPERATION",),
    "limits": ("[OPERATION]",),
    "upload": ("ID", "FILE"),
}
# What an upload came to, beside its reply: a reply that does not report success leaves the
# show as it was.
UPLOAD_UNCHANGED = "upload: unchanged: the target holds this file already; nothing was sent"
UPLOAD_UNKNOWN = "upload: not known: the target did not answer; the same upload again sends nothing when the file was installed"
TIMEOUT_SECONDS = 2.0
REPORT_SECONDS = 0.5
COUNTS = ("no argument", "one argument", "two arguments")


def _seconds(text):
    try:
        seconds = float(text)
    except ValueError:
        seconds = -1.0
    if not 0 < seconds < float("inf"):
        raise argparse.ArgumentTypeError(f"{text!r} is not a number of seconds above 0")
    return seconds


def _lines_address(text):
    try:
        client.tcp_address(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{text!r} is not host:port") from None
    return text


def parser():
    made = argparse.ArgumentParser(
        prog="python -m odrigctl",
        description="Sends one command to a target, over its serial port, over TCP or over HTTP, and prints the reply. "
                    "list prints a reply for each part of a long show, and upload sends a file and prints the reply that ended it. "
                    "With --log and no command it prints the lines of the target's log as they arrive, until it is stopped.",
        epilog="Commands: play ID, play all, on, off, brightness N, status, fault, space, list, read ID OFFSET, catalog, catalog rebuild internal|external, catalog cancel, remove ID, remove many IDS, ignore ID 0|1, mapping get, mapping set REV PINS, mapping cross on|off, mapping test on|off, mapping test snake N, order get [FROM], order move REV ID BEFORE, limits [FROM], limits wall MA, limits snake N MA, limits default, upload ID FILE, upload --external FILE. ID and N are sent as they are typed; order get and limits without FROM print a reply for each part.",
    )
    target = made.add_mutually_exclusive_group(required=True)
    target.add_argument("--port", metavar="NAME", help="the serial port of the target")
    target.add_argument("--tcp", metavar="ADDRESS", type=_lines_address, help="the address of a target that takes lines over TCP: host:port")
    target.add_argument("--http", metavar="ADDRESS", help="the address of the target: host or host:port")
    made.add_argument("--timeout", metavar="SECONDS", type=_seconds, default=TIMEOUT_SECONDS, help="how long to wait for a reply (default: 2)")
    made.add_argument("--log", action="store_true", help="print each line of the target's log as it arrives, until stopped, and send nothing; with --port or --tcp, and no command")
    made.add_argument("--external", action="store_true", help="with upload: send the FILE to the target's drive, which takes no ID")
    made.add_argument("command", metavar="COMMAND", nargs="?", choices=list(COMMANDS), help=", ".join(COMMANDS))
    made.add_argument("arguments", metavar="ARGUMENT", nargs="*", help="the ID of play and of remove, the word all of play, the N of brightness, the ID and the OFFSET of read, rebuild internal, rebuild external or cancel of catalog, FROM, wall MA, snake N MA or default of limits, the ID and the FILE of upload, the FILE of upload --external")
    return made


def checked(made, arguments):
    """The command and its arguments as they were typed, or nothing with `--log`. A command
    with another number of arguments than it takes, or with a line end in one, ends the
    program as a usage error, and so do `--log` with a command or with `--http` and no
    command without `--log`."""
    if arguments.external and arguments.command != "upload":
        made.error("--external goes with upload")
    if arguments.log:
        if arguments.http is not None:
            made.error("--log goes with --port or --tcp")
        if arguments.command is not None:
            made.error("--log takes no command")
        return []
    if arguments.command is None:
        made.error("a command is needed, or --log")
    if arguments.command == "upload" and arguments.external:
        if len(arguments.arguments) != 1:
            made.error("upload --external takes one argument: FILE")
        if "\n" in arguments.arguments[0]:
            made.error("a command is one line")
        return ["upload", "external", arguments.arguments[0]]
    if arguments.command == "catalog":
        words = arguments.arguments
        if words not in ([], ["cancel"], ["rebuild", "internal"], ["rebuild", "external"]):
            made.error("catalog takes no argument, rebuild internal, rebuild external, or cancel")
        return [arguments.command, *words]
    if arguments.command == "remove" and len(arguments.arguments) == 2 and arguments.arguments[0] == "many":
        if any("\n" in word or "\r" in word for word in arguments.arguments):
            made.error("a command is one line")
        return [arguments.command, *arguments.arguments]
    if arguments.command == "mapping":
        words = arguments.arguments
        valid = words == ["get"] or (len(words) == 2 and words[0] in ("test", "cross") and words[1] in ("on", "off")) or (len(words) == 3 and words[0] == "set") or (
            len(words) == 3 and words[:2] == ["test", "snake"])
        if not valid:
            made.error("mapping takes get, set REV PINS, cross on|off, test on|off, or test snake N")
        if any("\n" in word or "\r" in word for word in words):
            made.error("a command is one line")
        return [arguments.command, *words]
    if arguments.command == "order":
        words = arguments.arguments
        if not (words == ["get"] or (len(words) == 2 and words[0] == "get") or (len(words) == 4 and words[0] == "move")):
            made.error("order takes get [FROM], or move REV ID BEFORE")
        if any("\n" in word or "\r" in word for word in words):
            made.error("a command is one line")
        return [arguments.command, *words]
    if arguments.command == "limits":
        words = arguments.arguments
        valid = len(words) == 0 or (len(words) == 1 and words[0] not in ("wall", "snake")) or (len(words) == 2 and words[0] == "wall") or (len(words) == 3 and words[0] == "snake")
        if not valid:
            made.error("limits takes no argument, FROM, wall MA, snake N MA, or default")
        if any("\n" in word or "\r" in word for word in words):
            made.error("a command is one line")
        return [arguments.command, *words]
    takes = COMMANDS[arguments.command]
    if len(arguments.arguments) != len(takes):
        made.error(f"{arguments.command} takes {COUNTS[len(takes)]}" + (": " + " ".join(takes) if takes else ""))
    if any("\n" in argument for argument in arguments.arguments):
        made.error("a command is one line")
    return [arguments.command, *arguments.arguments]


def command_line(made, arguments):
    """The line for a command that is one line, with its newline. The argument goes into
    it as typed."""
    return " ".join(checked(made, arguments)).encode("utf-8") + b"\n"


class Progress:
    """Writes how far an upload is: one line for each report, or one line written over
    again when the stream is a terminal. A report is written when half a second has
    passed since the one before, and for the last piece."""

    def __init__(self, stream, clock=time.monotonic):
        self.stream = stream
        self.clock = clock
        self.in_place = stream.isatty()
        self.reported = clock()
        self.width = 0
        self.all_sent = False

    def sent(self, sent, total, seconds):
        now = self.clock()
        if sent < total and now - self.reported < REPORT_SECONDS:
            return
        self.reported = now
        speed = round(sent / seconds) if seconds > 0 else 0
        self._write(f"upload: {sent * 100 // total}% {sent}/{total} bytes {speed} B/s")

    def checking(self):
        self.all_sent = True
        self._write("upload: checking")

    def _write(self, text):
        if self.in_place:
            self.stream.write("\r" + text.ljust(self.width))
            self.width = len(text)
        else:
            self.stream.write(text + "\n")
        self.stream.flush()

    def close(self):
        """Ends the line that was written over again."""
        if self.in_place and self.width:
            self.stream.write("\n")
            self.stream.flush()
            self.width = 0


def _print(reply):
    print(reply.decode("utf-8", "replace"))


def _interrupted(*_):
    raise KeyboardInterrupt


def _print_log(line):
    print(line.decode("utf-8", "replace"), flush=True)


def main(argv=None):
    made = parser()
    arguments = made.parse_args(argv)
    words = checked(made, arguments)
    if arguments.log:
        # Ctrl+Break, the way a program of its own group is ended on Windows, ends the log
        # as Ctrl-C does.
        if hasattr(signal, "SIGBREAK"):
            signal.signal(signal.SIGBREAK, _interrupted)
        try:
            client.follow_log(_print_log, port=arguments.port, tcp=arguments.tcp, timeout=arguments.timeout)
        except client.Unreachable as unreachable:
            print(f"error: unreachable: {unreachable}", file=sys.stderr)
            return 3
        except KeyboardInterrupt:
            return 0
    data = None
    progress = None
    if arguments.command == "upload":
        try:
            with open(words[2], "rb") as file:
                data = file.read()
        except OSError as error:
            print(f"error: not-found: {words[2]}: {error.strerror or type(error).__name__}", file=sys.stderr)
            return 2
    try:
        with client.Session(port=arguments.port, tcp=arguments.tcp, http=arguments.http, timeout=arguments.timeout) as session:
            if arguments.command == "list":
                return 0 if content.list_all(session, _print) else 1
            if words == ["order", "get"]:
                return 0 if content.list_all(session, _print, b"order get") else 1
            if words == ["limits"]:
                return 0 if content.list_all(session, _print, b"limits") else 1
            if arguments.command == "upload":
                progress = Progress(sys.stderr)
                try:
                    reply = content.upload(session, words[1], os.path.basename(words[2]), data, progress.sent, progress.checking)
                finally:
                    progress.close()
            else:
                reply = session.exchange(" ".join(words).encode("utf-8") + b"\n")
    except client.Unreachable as unreachable:
        if progress is not None and progress.all_sent:
            # `upload end` went out and its reply did not come: the file may be in place.
            print(UPLOAD_UNKNOWN, file=sys.stderr)
        print(f"error: unreachable: {unreachable}", file=sys.stderr)
        return 3
    if arguments.command == "upload" and content.is_ok(reply):
        print(UPLOAD_UNCHANGED if content.is_unchanged(reply) else f"upload: committed: {len(data)} bytes sent and checked by the target", file=sys.stderr)
    _print(reply)
    return 0 if content.is_ok(reply) else 1
