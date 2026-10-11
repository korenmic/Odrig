"""Programs that write animations as JSON frames files for the canvas of a mapping file.

Each generator is started as `python -m odrig.generators.<name> OUT --mapping MAPPING`.
"""

import argparse

from .. import cli, errors, jsonframes, mapping


def run(name, summary, frames, argv=None, configure=None):
    """The command line of a generator. `frames(width, height, arguments)` gives the frames."""

    def action():
        parser = argparse.ArgumentParser(prog=f"python -m odrig.generators.{name}", description=summary)
        parser.add_argument("output", metavar="OUT", help="the JSON frames file to write")
        parser.add_argument("--mapping", required=True, help="the mapping file that gives the canvas size")
        if configure is not None:
            configure(parser)
        arguments = parser.parse_args(argv)
        canvas = mapping.read(arguments.mapping)
        with errors.naming(arguments.mapping):
            made = frames(canvas.width, canvas.height, arguments)
        jsonframes.write(arguments.output, jsonframes.Animation(canvas.width, canvas.height, tuple(made)))

    return cli.status_of(action)


def picture(width, height, pixels):
    """A picture that is black except for `pixels`, a mapping from (x, y) to a colour."""
    result = bytearray(3 * width * height)
    for (x, y), colour in pixels.items():
        position = (y - 1) * width + (x - 1)
        result[3 * position:3 * position + 3] = colour
    return bytes(result)
