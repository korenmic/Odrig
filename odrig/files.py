"""Reading an input file whole and writing an output file whole."""

import contextlib
import os

from . import errors


def read(path, missing=errors.NOT_FOUND):
    """The bytes of the file. A file that is absent or unreadable is rejected as `missing`."""
    try:
        with open(path, "rb") as file:
            return file.read()
    except OSError as error:
        raise errors.Rejection(missing, f"{path}: {_why(error)}") from None


def write(path, data):
    """Writes the file through `<name>.part`, which takes the file's place once complete.

    An existing file is replaced. When writing fails, no `.part` file is left and an
    existing file is as it was.
    """
    part = f"{path}.part"
    try:
        with open(part, "wb") as file:
            file.write(data)
        os.replace(part, path)
    except OSError as error:
        with contextlib.suppress(OSError):
            os.remove(part)
        raise errors.Rejection(errors.CANNOT_WRITE, f"{path}: {_why(error)}") from None


def _why(error):
    return error.strerror or type(error).__name__
