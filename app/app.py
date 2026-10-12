#!/usr/bin/env python3
"""The tool of the operators' app.

    python3 app/app.py <command> [options]

This file uses only the standard library.
"""

import os
import sys

APP = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [APP]

from apptool import cli  # noqa: E402

if __name__ == "__main__":
    sys.exit(cli.main(sys.argv[1:]))
