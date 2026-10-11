"""The one way this tool refuses an input: a rejection with a named reason.

Every reason is a constant of this module. docs/reasons.md lists them with their conditions.
"""

import contextlib

NOT_FOUND = "not-found"
CANNOT_WRITE = "cannot-write"


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
