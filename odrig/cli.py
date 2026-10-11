"""The command line: arguments, exit statuses and the error line.

Exit status 0 means the subcommand did its work, 1 that an input was rejected, and 2 that
the command line was not understood.
"""

import argparse
import collections
import sys

from . import errors, files, jsonframes, odrg

Subcommand = collections.namedtuple("Subcommand", "name summary configure run")


def _configure_decode(parser):
    parser.add_argument("input", metavar="IN.odrg", help="the ODRG file to read")
    parser.add_argument("output", metavar="OUT.json", help="the JSON frames file to write")


def _decode(arguments):
    data = files.read(arguments.input)
    with errors.naming(arguments.input):
        decoded = odrg.decode(data)
    animation = jsonframes.Animation(decoded.width, decoded.height, decoded.records)
    jsonframes.write(arguments.output, animation)


SUBCOMMANDS = (
    Subcommand("decode", "Turns an ODRG file back into a JSON frames file.", _configure_decode, _decode),
)


def build_parser():
    parser = argparse.ArgumentParser(
        prog="python -m odrig",
        description="Converts animations between media files, JSON frames and ODRG.",
    )
    subparsers = parser.add_subparsers(dest="subcommand", metavar="SUBCOMMAND", required=True)
    for subcommand in SUBCOMMANDS:
        subparser = subparsers.add_parser(
            subcommand.name, help=subcommand.summary, description=subcommand.summary
        )
        subcommand.configure(subparser)
        subparser.set_defaults(run=subcommand.run)
    return parser


def main(argv=None):
    """Runs one command line and returns the exit status."""
    try:
        arguments = build_parser().parse_args(argv)
    except SystemExit as stop:
        return stop.code
    try:
        arguments.run(arguments)
    except errors.Rejection as rejection:
        detail = " ".join(rejection.detail.split())
        print(f"error: {rejection.reason}: {detail}", file=sys.stderr)
        return 1
    return 0
