"""Entry point of `python -m odrig`."""

import sys

from .cli import main

sys.exit(main(sys.argv[1:]))
