"""Entry point of `python -m emulator`."""

import sys

from .app import main

sys.exit(main(sys.argv[1:]))
