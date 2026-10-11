"""The one way this tool refuses an input: a rejection with a named reason.

Every reason is a constant of this module. docs/reasons.md lists them with their conditions.
"""

import contextlib

NOT_FOUND = "not-found"
CANNOT_WRITE = "cannot-write"

BAD_JSON = "bad-json"
MISSING_MEMBER = "missing-member"
BAD_TYPE = "bad-type"
BAD_VERSION = "bad-version"
UNKNOWN_MEMBER = "unknown-member"
OUT_OF_RANGE = "out-of-range"
NO_FRAMES = "no-frames"
BAD_PIXEL_COUNT = "bad-pixel-count"

TRUNCATED = "truncated"
BAD_MAGIC = "bad-magic"
RESERVED_BITS = "reserved-bits"
ZERO_SIZE = "zero-size"
BAD_PALETTE_SIZE = "bad-palette-size"
CANVAS_TOO_LARGE = "canvas-too-large"
BAD_DEFLATE = "bad-deflate"
ZERO_DURATION = "zero-duration"
BAD_LENGTH = "bad-length"
BAD_STORED_LENGTH = "bad-stored-length"
OUT_OF_BITS = "out-of-bits"
RUN_PAST_END = "run-past-end"
BAD_CODE = "bad-code"
TOO_MUCH_PADDING = "too-much-padding"
BAD_PALETTE_INDEX = "bad-palette-index"
TRAILING_BYTES = "trailing-bytes"

TOO_MANY_FRAMES = "too-many-frames"


class Rejection(Exception):
    """An input that is refused. `reason` is a fixed name, `detail` is text for people."""

    def __init__(self, reason, detail):
        super().__init__(f"{reason}: {detail}")
        self.reason = reason
        self.detail = detail


@contextlib.contextmanager
def naming(path):
    """Puts the name of the file concerned in front of the detail of a rejection."""
    try:
        yield
    except Rejection as rejection:
        raise Rejection(rejection.reason, f"{path}: {rejection.detail}") from None
