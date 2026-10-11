"""The suite of the firmware tool that needs no board.

It needs no board, no network connection and nothing outside the work folder,
`build/firmware/`. `python3 firmware/fw.py test` runs it with the work folder's Python.
"""

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
FIRMWARE = ROOT / "firmware"

if str(FIRMWARE) not in sys.path:
    sys.path.insert(0, str(FIRMWARE))
