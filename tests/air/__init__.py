"""The suite that needs the board on USB and this Mac on the board's Wi-Fi network.

`python3 firmware/fw.py test-air --http ADDRESS` runs it with the work folder's Python;
ADDRESS is the board's address on its network, 4.3.2.1 on its own access point. Joining
that network is done by a person. Without a board on USB, or when the address answers no
command, the package cannot be imported, so no test runs.

One test saves WLED's LED settings through WLED's own interface; see `test_wled.py`.
"""

import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
FIRMWARE = ROOT / "firmware"

if str(FIRMWARE) not in sys.path:
    sys.path.insert(0, str(FIRMWARE))

from odrigctl import client  # noqa: E402

from fwtool import Failure, board  # noqa: E402

ADDRESS_VARIABLE = "ODRIG_BOARD_HTTP"

# The board's port. Looking for it fails with `no-board` when there is none.
PORT = board.find()

# The board's address on the network.
ADDRESS = os.environ.get(ADDRESS_VARIABLE, "")
if not ADDRESS:
    raise Failure("no-board", f"no address is given; run `python3 firmware/fw.py test-air --http ADDRESS`, or set {ADDRESS_VARIABLE}")
try:
    client.http_exchange(ADDRESS, b"status\n", 5.0)
except client.Unreachable as unreachable:
    raise Failure("no-board", f"{ADDRESS} answers no command over HTTP: {unreachable}") from None
