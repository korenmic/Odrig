"""Helpers shared by the tests of the emulator: where things are and how shows are packed."""

import contextlib
import pathlib
import tempfile

from odrig import pack

from . import LIBRARY, ROOT

HEADER = ROOT / "core" / "include" / "odrig_core.h"
EXAMPLE_SHOW = ROOT / "shows" / "example" / "show.json"
TWO_LEGS = ROOT / "mapping" / "legs-2.json"
TEN_LEGS = ROOT / "mapping" / "legs-10.json"


@contextlib.contextmanager
def packed(show, mapping, sources, compressed=True):
    """A temporary folder that holds a show as `python -m odrig pack` installs it."""
    with tempfile.TemporaryDirectory() as folder:
        out = pathlib.Path(folder, "show")
        pack.pack(show, mapping, sources, out, compressed=compressed)
        yield out


def example_show():
    """The example show, packed on the two-leg mapping into a temporary folder."""
    return packed(EXAMPLE_SHOW, TWO_LEGS, ROOT / "animations")


def files_of(folder):
    """The installed files of a folder: the content of each by its name."""
    return {path.name: path.read_bytes() for path in sorted(pathlib.Path(folder).iterdir()) if path.is_file()}
