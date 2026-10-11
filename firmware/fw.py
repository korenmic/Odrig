#!/usr/bin/env python3
"""The firmware tool: builds the firmware, flashes it, installs a show, restores stock WLED.

    python3 firmware/fw.py <command> [options]

This file uses only the standard library. It checks the command line, makes sure the work
folder holds the tool's Python environment, and runs the command with that environment's
Python. `docs/firmware.md` describes every command.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fwtool import cli  # noqa: E402

if __name__ == "__main__":
    sys.exit(cli.launch(sys.argv[1:]))
