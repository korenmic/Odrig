"""Entry point of `python -m odrigctl`."""

import sys

from .cli import main

sys.exit(main(sys.argv[1:]))
