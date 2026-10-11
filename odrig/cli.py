"""The command line: arguments, exit statuses and the error line.

Exit status 0 means the subcommand did its work, 1 that an input was rejected, and 2 that
the command line was not understood.
"""

import argparse
import collections
import decimal
import sys

from . import errors, files, jsonframes, mapping, media, odrg
from . import pack as packing

Subcommand = collections.namedtuple("Subcommand", "name summary configure run")


def _milliseconds(text):
    """Seconds given as a decimal number, in whole milliseconds, rounded to the nearest."""
    try:
        seconds = decimal.Decimal(text)
    except decimal.InvalidOperation:
        raise argparse.ArgumentTypeError(f"{text!r} is not a number of seconds") from None
    if not seconds.is_finite():
        raise argparse.ArgumentTypeError(f"{text!r} is not a number of seconds")
    return int((seconds * 1000).quantize(decimal.Decimal(1), rounding=decimal.ROUND_HALF_UP))


def _configure_import(parser):
    parser.add_argument("input", metavar="MEDIA", help="the .mp4, .mov or .gif file to read")
    parser.add_argument("output", metavar="OUT.json", help="the JSON frames file to write")
    parser.add_argument("--mapping", required=True, help="the mapping file that gives the canvas size")
    parser.add_argument(
        "--fit",
        choices=("fill", "fit", "stretch"),
        default="fill",
        help="how a picture of another shape is put on the canvas (default: fill)",
    )
    parser.add_argument(
        "--start", type=_milliseconds, default=0, metavar="SECONDS", help="where the part to convert starts"
    )
    parser.add_argument(
        "--duration", type=_milliseconds, default=None, metavar="SECONDS", help="how long the part to convert is"
    )


def _import(arguments):
    canvas = mapping.read(arguments.mapping)
    animation = media.import_media(
        arguments.input, canvas, arguments.fit, arguments.start, arguments.duration
    )
    jsonframes.write(arguments.output, animation)


def _configure_encode(parser):
    parser.add_argument("input", metavar="IN.json", help="the JSON frames file to read")
    parser.add_argument("output", metavar="OUT.odrg", help="the ODRG file to write")
    parser.add_argument("--uncompressed", action="store_true", help="write the body without compression")


def _encode(arguments):
    animation = jsonframes.read(arguments.input)
    with errors.naming(arguments.input):
        data = odrg.encode(animation, compressed=not arguments.uncompressed)
    files.write(arguments.output, data)


def _configure_decode(parser):
    parser.add_argument("input", metavar="IN.odrg", help="the ODRG file to read")
    parser.add_argument("output", metavar="OUT.json", help="the JSON frames file to write")


def _decode(arguments):
    data = files.read(arguments.input)
    with errors.naming(arguments.input):
        decoded = odrg.decode(data)
    animation = jsonframes.Animation(decoded.width, decoded.height, decoded.records)
    jsonframes.write(arguments.output, animation)


def _configure_check(parser):
    parser.add_argument("file", metavar="FILE", help="the JSON frames or ODRG file to check")
    parser.add_argument(
        "--format",
        choices=("json", "odrg"),
        help="the format of FILE, when its name does not end in .json or .odrg",
    )


def _check(arguments):
    kind = arguments.format
    if kind is None:
        name = str(arguments.file).lower()
        if name.endswith(".json"):
            kind = "json"
        elif name.endswith(".odrg"):
            kind = "odrg"
        else:
            arguments.parser.error(f"the name of {arguments.file} does not tell its format; give --format")
    data = files.read(arguments.file)
    with errors.naming(arguments.file):
        if kind == "json":
            animation = jsonframes.loads(data)
            width, height, frames = animation.width, animation.height, animation.frames
            lines = ["format: json-frames"]
            more = []
        else:
            decoded = odrg.decode(data)
            width, height, frames = decoded.width, decoded.height, decoded.records
            lines = ["format: odrg"]
            more = [f"palette: {decoded.palette_size}", f"compressed: {'yes' if decoded.compressed else 'no'}"]
    lines += [
        f"canvas: {width}x{height}",
        f"frames: {len(frames)}",
        f"duration_ms: {sum(ms for ms, _ in frames)}",
        f"colours: {jsonframes.colour_count(frames)}",
        f"file_bytes: {len(data)}",
    ]
    print("\n".join(lines + more))


def _configure_pack(parser):
    parser.add_argument("--show", required=True, help="the show file")
    parser.add_argument("--mapping", required=True, help="the mapping file")
    parser.add_argument("--sources", required=True, metavar="DIR", help="the folder of JSON frames sources")
    parser.add_argument("--out", required=True, metavar="DIR", help="the folder to build, new or empty")
    parser.add_argument("--uncompressed", action="store_true", help="write every ODRG file without compression")


def _pack(arguments):
    packing.pack(
        arguments.show,
        arguments.mapping,
        arguments.sources,
        arguments.out,
        compressed=not arguments.uncompressed,
    )


SUBCOMMANDS = (
    Subcommand("import", "Turns a video or GIF file into a JSON frames file.", _configure_import, _import),
    Subcommand("encode", "Turns a JSON frames file into an ODRG file.", _configure_encode, _encode),
    Subcommand("decode", "Turns an ODRG file back into a JSON frames file.", _configure_decode, _decode),
    Subcommand("check", "Validates a JSON frames or ODRG file and summarises it.", _configure_check, _check),
    Subcommand("pack", "Builds the folder of files that is installed for a show.", _configure_pack, _pack),
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
        subparser.set_defaults(run=subcommand.run, parser=subparser)
    return parser


def main(argv=None):
    """Runs one command line and returns the exit status."""

    def action():
        arguments = build_parser().parse_args(argv)
        arguments.run(arguments)

    return status_of(action)


def status_of(action):
    """Runs `action` and returns the exit status, writing the error line for a rejection."""
    try:
        action()
    except SystemExit as stop:
        return stop.code
    except errors.Rejection as rejection:
        detail = " ".join(rejection.detail.split())
        print(f"error: {rejection.reason}: {detail}", file=sys.stderr)
        return 1
    return 0
