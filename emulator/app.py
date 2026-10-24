"""The command line of the emulator: arguments, the order of starting, exit statuses.

Exit status 0 means the emulator did its work, 1 that it could not start, with one line
`error: <reason>: <detail>` on standard error, and 2 that the command line was not
understood.
"""

import argparse
import decimal
import os
import pathlib
import signal
import sys
import threading

from . import binding, engine, failure, host, httpd, hub, lineport, record

# The virtual serial port is a pseudo-terminal. A system without one has the line port.
HAS_SERIAL = hasattr(os, "openpty")
if HAS_SERIAL:
    from . import serialport

ROOT = pathlib.Path(__file__).resolve().parent.parent
LIBRARY = ROOT / "core" / "build" / binding.LIBRARY_NAME
SERIAL_LINK = ROOT / "build" / "emulator" / "serial"
PORT = 8600
TCP_PORT = 8601
WAIT_SECONDS = 0.2


def _milliseconds(text):
    """Seconds given as a decimal number, in whole milliseconds, rounded to the nearest."""
    try:
        seconds = decimal.Decimal(text)
    except decimal.InvalidOperation:
        raise argparse.ArgumentTypeError(f"{text!r} is not a number of seconds") from None
    if not seconds.is_finite():
        raise argparse.ArgumentTypeError(f"{text!r} is not a number of seconds")
    return int((seconds * 1000).quantize(decimal.Decimal(1), rounding=decimal.ROUND_HALF_UP))


def _port(text):
    if not text.isascii() or not text.isdigit() or int(text) > 65535:
        raise argparse.ArgumentTypeError(f"{text!r} is not a port number from 0 to 65535")
    return int(text)


def _storage(text):
    if not text.isascii() or not text.isdigit() or int(text) > host.MOST_STORAGE:
        raise argparse.ArgumentTypeError(f"{text!r} is not a number of bytes from 0 to {host.MOST_STORAGE}")
    return int(text)


def parser():
    made = argparse.ArgumentParser(
        prog="python -m emulator",
        description="Runs the core on the installed show of a folder: in real time, with commands through a "
        "virtual serial port or a TCP port and over HTTP, or in record mode on a virtual clock.",
    )
    made.add_argument("show_dir", metavar="SHOW_DIR", help="the folder that holds the installed show")
    made.add_argument("--port", metavar="N", type=_port, help=f"the port of the page on 127.0.0.1; 0 takes any free port (default: {PORT})")
    made.add_argument("--serial-link", metavar="PATH", help="where the link to the virtual serial port is made (default: build/emulator/serial)")
    made.add_argument("--tcp-port", metavar="N", type=_port, help=f"the port on 127.0.0.1 that takes command lines over TCP; 0 takes any free port (default: {TCP_PORT} on a system without a virtual serial port, none elsewhere)")
    made.add_argument("--core", metavar="PATH", default=str(LIBRARY), help=f"the core's shared library (default: core/build/{binding.LIBRARY_NAME})")
    made.add_argument("--verbose", action="store_true", help="print the core's diagnostic lines to standard error")
    made.add_argument("--storage", metavar="BYTES", type=_storage, default=host.STORAGE_BYTES,
                      help=f"the size of the storage that is reported as the total space (default: {host.STORAGE_BYTES}, the board's)")
    made.add_argument("--lan", action="store_true", help="let other devices of the local network open the page and send commands over HTTP")
    made.add_argument("--drive", metavar="DIR", help="a folder that stands for the top of a drive, the card: its folder odrig appearing and going is the drive plugged in and pulled out")
    made.add_argument("--drive-read-only", action="store_true", help="the drive cannot be written, as a USB stick")
    made.add_argument("--record", metavar="OUT", help="record mode: the record file to write")
    made.add_argument("--seconds", metavar="S", type=_milliseconds, help="record mode: the length of the recording")
    made.add_argument("--script", metavar="FILE", help="record mode: timed command lines to give the core")
    return made


def parse(argv):
    made = parser()
    arguments = made.parse_args(argv)
    if arguments.record is None:
        if arguments.seconds is not None or arguments.script is not None:
            made.error("--seconds and --script belong to record mode, which --record OUT starts")
    else:
        if arguments.seconds is None:
            made.error("record mode needs its length: --seconds S")
        if arguments.port is not None or arguments.serial_link is not None or arguments.tcp_port is not None or arguments.verbose or arguments.lan:
            made.error("record mode opens no page and no port: --port, --serial-link, --tcp-port, --verbose and --lan do not go with --record")
        if arguments.drive is not None:
            made.error("record mode has no drive: --drive does not go with --record")
    return arguments


def ports(arguments, has_serial=HAS_SERIAL):
    """Which ports a run in real time opens: `(link of the serial port, TCP port)`, each
    `None` when the run does not have it."""
    if has_serial:
        return SERIAL_LINK if arguments.serial_link is None else arguments.serial_link, arguments.tcp_port
    if arguments.serial_link is not None:
        raise failure.Failure(failure.SERIAL_UNAVAILABLE, f"{arguments.serial_link}: this system has no pseudo-terminal; command lines are taken on the TCP port")
    return None, TCP_PORT if arguments.tcp_port is None else arguments.tcp_port


def serve(arguments, out):
    """Real time: starts the core, opens the ports and the page address, and runs until a
    signal. A step that fails undoes the ones before it."""
    link, tcp_port = ports(arguments)
    drive = None if arguments.drive is None else host.Drive(arguments.drive, writable=not arguments.drive_read_only)
    files = host.FolderHost(arguments.show_dir, verbose=arguments.verbose, storage=arguments.storage, drive=drive)
    port = None
    line_port = None
    server = None
    try:
        core = binding.Core(arguments.core, files)
        running = engine.Engine(core, hub.Hub())
        running.tick()
        running.refresh_status()
        if link is not None:
            port = serialport.Port(link, lambda data: running.feed(data, "serial"))
        if tcp_port is not None:
            line_port = lineport.Port(tcp_port, lambda data: running.feed(data, "tcp"))
        described = {
            "show": os.path.abspath(arguments.show_dir),
            "drive": None if drive is None else os.path.abspath(drive.top),
            "serial": None if port is None else port.link,
            "tcp": None if line_port is None else line_port.address,
            "legs": [list(leg) for leg in core.legs],
            "t0": running.t0,
        }
        if arguments.lan:
            print("warning: --lan: anyone on the local network can send commands to this emulator and open its page", file=sys.stderr, flush=True)
        server = httpd.Server(
            PORT if arguments.port is None else arguments.port, running, arguments.show_dir,
            lambda: {"show": described["show"], "drive": described["drive"], "page": server.url, "serial": described["serial"], "tcp": described["tcp"], "legs": [list(leg) for leg in core.legs], "t0": described["t0"], "error": running.error()},
            lan=arguments.lan,
        )

        stopped = threading.Event()
        for name in ("SIGINT", "SIGTERM", "SIGBREAK"):
            if hasattr(signal, name):
                signal.signal(getattr(signal, name), lambda *_: stopped.set())

        print(f"page: {server.url}", file=out)
        if port is not None:
            print(f"serial: {port.link}", file=out)
        if line_port is not None:
            print(f"tcp: {line_port.address}", file=out)
        if arguments.lan:
            # The address a phone on the same network is given.
            address = httpd.lan_address()
            print("lan: no address" if address is None else f"lan: http://{address}:{server.port}/", file=out)
        out.flush()

        if port is not None:
            port.start()
        if line_port is not None:
            line_port.start()
        loop = engine.RealTime(running)
        loop.start()
        server.start()
        # A wait without a limit is not interrupted by a signal on every system.
        while not stopped.wait(WAIT_SECONDS):
            pass
        server.stop()
        server = None
        loop.stop()
        loop.join()
        running.hub.close()
    finally:
        if server is not None:
            server.server_close()
        if line_port is not None:
            line_port.close()
        if port is not None:
            port.close()
        files.release()
    return 0


def run(arguments, out):
    if not os.path.isdir(arguments.show_dir):
        raise failure.Failure(failure.NOT_A_FOLDER, f"{arguments.show_dir}: there is no such folder")
    if arguments.record is not None:
        record.run(arguments.show_dir, arguments.record, arguments.seconds, arguments.script, arguments.core, out, arguments.storage)
        return 0
    return serve(arguments, out)


def main(argv=None):
    arguments = parse(argv)
    try:
        return run(arguments, sys.stdout)
    except failure.Failure as failed:
        print(failed.line(), file=sys.stderr)
        return 1
