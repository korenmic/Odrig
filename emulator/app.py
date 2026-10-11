"""The command line of the emulator: arguments, the order of starting, exit statuses.

Exit status 0 means the emulator did its work, 1 that it could not start, with one line
`error: <reason>: <detail>` on standard error, and 2 that the command line was not
understood.
"""

import argparse
import decimal
import os
import pathlib
import sys

from . import failure, record

ROOT = pathlib.Path(__file__).resolve().parent.parent
LIBRARY = ROOT / "core" / "build" / "libodrig_core.dylib"


def _milliseconds(text):
    """Seconds given as a decimal number, in whole milliseconds, rounded to the nearest."""
    try:
        seconds = decimal.Decimal(text)
    except decimal.InvalidOperation:
        raise argparse.ArgumentTypeError(f"{text!r} is not a number of seconds") from None
    if not seconds.is_finite():
        raise argparse.ArgumentTypeError(f"{text!r} is not a number of seconds")
    return int((seconds * 1000).quantize(decimal.Decimal(1), rounding=decimal.ROUND_HALF_UP))


def parser():
    made = argparse.ArgumentParser(
        prog="python -m emulator",
        description="Runs the core on the installed show of a folder and records what it gives the LEDs.",
    )
    made.add_argument("show_dir", metavar="SHOW_DIR", help="the folder that holds the installed show")
    made.add_argument("--core", metavar="PATH", default=str(LIBRARY), help="the core's shared library (default: core/build/libodrig_core.dylib)")
    made.add_argument("--record", metavar="OUT", required=True, help="record mode: the record file to write")
    made.add_argument("--seconds", metavar="S", type=_milliseconds, required=True, help="record mode: the length of the recording")
    made.add_argument("--script", metavar="FILE", help="record mode: timed command lines to give the core")
    return made


def run(arguments):
    if not os.path.isdir(arguments.show_dir):
        raise failure.Failure(failure.NOT_A_FOLDER, f"{arguments.show_dir}: there is no such folder")
    record.run(arguments.show_dir, arguments.record, arguments.seconds, arguments.script, arguments.core)
    return 0


def main(argv=None):
    arguments = parser().parse_args(argv)
    try:
        return run(arguments)
    except failure.Failure as failed:
        print(failed.line(), file=sys.stderr)
        return 1
