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

from . import binding, engine, failure, host, httpd, hub, record, serialport

ROOT = pathlib.Path(__file__).resolve().parent.parent
LIBRARY = ROOT / "core" / "build" / "libodrig_core.dylib"
SERIAL_LINK = ROOT / "build" / "emulator" / "serial"
PORT = 8600


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
        "virtual serial port and over HTTP, or in record mode on a virtual clock.",
    )
    made.add_argument("show_dir", metavar="SHOW_DIR", help="the folder that holds the installed show")
    made.add_argument("--port", metavar="N", type=_port, help=f"the port of the page on 127.0.0.1; 0 takes any free port (default: {PORT})")
    made.add_argument("--serial-link", metavar="PATH", help="where the link to the virtual serial port is made (default: build/emulator/serial)")
    made.add_argument("--core", metavar="PATH", default=str(LIBRARY), help="the core's shared library (default: core/build/libodrig_core.dylib)")
    made.add_argument("--verbose", action="store_true", help="print the core's diagnostic lines to standard error")
    made.add_argument("--storage", metavar="BYTES", type=_storage, default=host.STORAGE_BYTES,
                      help=f"the size of the storage that is reported as the total space (default: {host.STORAGE_BYTES}, the board's)")
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
        if arguments.port is not None or arguments.serial_link is not None or arguments.verbose:
            made.error("record mode opens no page and no port: --port, --serial-link and --verbose do not go with --record")
    return arguments


def serve(arguments, out):
    """Real time: starts the core, opens the port and the page address, and runs until a
    signal. A step that fails undoes the ones before it."""
    files = host.FolderHost(arguments.show_dir, verbose=arguments.verbose, storage=arguments.storage)
    port = None
    server = None
    try:
        core = binding.Core(arguments.core, files)
        running = engine.Engine(core, hub.Hub())
        running.tick()
        running.refresh_status()
        port = serialport.Port(SERIAL_LINK if arguments.serial_link is None else arguments.serial_link, lambda data: running.feed(data, "serial"))
        described = {"show": os.path.abspath(arguments.show_dir), "serial": port.link, "legs": [list(leg) for leg in core.legs], "t0": running.t0}
        server = httpd.Server(
            PORT if arguments.port is None else arguments.port, running, arguments.show_dir,
            lambda: {"show": described["show"], "page": server.url, "serial": described["serial"], "legs": described["legs"], "t0": described["t0"], "error": running.error()},
        )

        stopped = threading.Event()
        for number in (signal.SIGINT, signal.SIGTERM):
            signal.signal(number, lambda *_: stopped.set())

        print(f"page: {server.url}", file=out)
        print(f"serial: {port.link}", file=out, flush=True)

        port.start()
        loop = engine.RealTime(running)
        loop.start()
        server.start()
        stopped.wait()
        server.stop()
        server = None
        loop.stop()
        loop.join()
        running.hub.close()
    finally:
        if server is not None:
            server.server_close()
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
