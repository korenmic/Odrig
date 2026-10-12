"""The limit on LED current: a limit file read and checked."""

from . import Failure, paths, settingsfile

MEMBER = "milliamps"
# WLED keeps its maximum as a 16-bit number. 0 switches its limiter off.
LOWEST, HIGHEST = 0, 65535


def read(path=paths.LIMIT_SETTINGS):
    """The limit of a limit file, in milliamps, checked."""
    value = settingsfile.value_of(path, "limit-settings-missing", "limit-settings-malformed")
    if not isinstance(value, dict) or list(value) != [MEMBER] or type(value[MEMBER]) is not int:
        raise Failure("limit-settings-malformed", f"{path} is not an object with exactly the whole number {MEMBER}")
    milliamps = value[MEMBER]
    if not LOWEST <= milliamps <= HIGHEST:
        raise Failure("limit-invalid", f"the limit is {milliamps} mA; a limit is {LOWEST} to {HIGHEST}, and 0 switches the limiter off")
    return milliamps


def line(milliamps):
    """The limit in the words the tool prints."""
    return "limit: off" if milliamps == 0 else f"limit: {milliamps} mA"
