"""The one way the library refuses an input: a rejection with a named reason.

Every reason is a constant of this module. docs/reasons.md lists them with their conditions.
"""

import contextlib
import sys

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

BAD_CONTAINER = "bad-container"
UNKNOWN_TYPE = "unknown-type"
UNKNOWN_TYPE_VERSION = "unknown-type-version"
PAYLOAD_SIZE = "payload-size"
CANVAS_MISMATCH = "canvas-mismatch"
LOOP_MISMATCH = "loop-mismatch"

MAPPING_MISSING = "mapping-missing"
MAPPING_MALFORMED = "mapping-malformed"

CANVAS_TOO_SMALL = "canvas-too-small"

SHOW_MISSING = "show-missing"
SHOW_MALFORMED = "show-malformed"
DUPLICATE_ID = "duplicate-id"
UNDEFINED_ID = "undefined-id"
NESTED_CYCLE = "nested-cycle"
FILE_MISSING = "file-missing"
FILE_MALFORMED = "file-malformed"
SIZE_MISMATCH = "size-mismatch"
OUTPUT_NOT_EMPTY = "output-not-empty"

UNSUPPORTED_MEDIA = "unsupported-media"
UNREADABLE_MEDIA = "unreadable-media"
BAD_RANGE = "bad-range"


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


def status_of(action):
    """Runs `action`, the work of a command line, and returns its exit status: 0, the code
    it exits with, or 1 for a rejection, whose error line goes to standard error."""
    try:
        action()
    except SystemExit as stop:
        return stop.code
    except Rejection as rejection:
        detail = " ".join(rejection.detail.split())
        print(f"error: {rejection.reason}: {detail}", file=sys.stderr)
        return 1
    return 0
