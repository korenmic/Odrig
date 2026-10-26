"""The reproducer of a decoder that settles a defect in one call: a small compressed ODRG
file whose first frame record has a palette index outside its palette, and whose stream
goes on inflating far beyond the record, to tens of megabytes of zeros.

    python3 -m tests.core.huge_tail OUT [TAIL_BYTES]

writes it to OUT. It is made where it is needed and never installed on a board as an
ordinary animation.
"""

import struct
import sys
import zlib

WIDTH = 60
HEIGHT = 60
# The inflated bytes after the frame record: 64 MiB, as in the board's investigation.
TAIL = 64 * 1024 * 1024
# The reason a whole-file reader gives it: the record is judged after the stream is whole,
# and its palette index is the first defect met.
REASON = "bad-palette-index"


def huge_tail(tail=TAIL, width=WIDTH, height=HEIGHT):
    """The file's bytes: a header of two colours and one frame, and a raw-deflate body of
    the palette, one stored record whose first index is 255, and `tail` zero bytes."""
    pixels = width * height
    header = b"ODRG" + bytes([1, 1]) + struct.pack("<HHHI", width, height, 2, 1)
    record = struct.pack("<HHB", 20, pixels + 1, 0x40) + b"\xff" + bytes(pixels - 1)
    body = bytes([0, 0, 0, 255, 255, 255]) + record
    packer = zlib.compressobj(9, zlib.DEFLATED, -15)
    stream = packer.compress(body)
    zeros = bytes(1024 * 1024)
    left = tail
    while left > 0:
        part = min(left, len(zeros))
        stream += packer.compress(zeros[:part])
        left -= part
    stream += packer.flush()
    return header + stream


def main(arguments):
    if len(arguments) not in (1, 2):
        print(__doc__.strip().splitlines()[-4].strip(), file=sys.stderr)
        return 2
    tail = int(arguments[1]) if len(arguments) == 2 else TAIL
    with open(arguments[0], "wb") as out:
        out.write(huge_tail(tail))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
