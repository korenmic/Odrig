"""The suite that needs the board.

It needs the ESP32-S3 board connected over USB, and it writes to the board: it flashes
images and restores stock WLED. `python3 firmware/fw.py test-board` runs it with the work
folder's Python. Without a board the package cannot be imported, so no test runs.
"""

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
FIRMWARE = ROOT / "firmware"

if str(FIRMWARE) not in sys.path:
    sys.path.insert(0, str(FIRMWARE))

from fwtool import board  # noqa: E402

# The board's port. Looking for it fails with `no-board` when there is none.
PORT = board.find()
