"""Helpers shared by the tests that need the board: running the tool and what it builds."""

import collections
import contextlib
import io

from fwtool import build, cli

from . import PORT

Result = collections.namedtuple("Result", "status out err")


def tool(*arguments):
    """Runs one command line of the firmware tool in this interpreter, on the board's port."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            status = cli.main([str(argument) for argument in arguments])
        except SystemExit as stopped:
            status = stopped.code
    return Result(status, out.getvalue(), err.getvalue())


def on_port(*arguments):
    """The same, with the board's port given."""
    return tool(*arguments, "--port", PORT)


def built(kind):
    """The image of one kind, built now when the work folder does not hold it."""
    image = build.image_path(kind)
    try:
        return build.checked_image(image)
    except build.Failure:
        build.build(kind)
        return build.checked_image(image)
