"""The network's name and password: a settings file read and checked."""

import re

from odrig import errors as json_errors
from odrig import strictjson

from . import Failure, paths

MEMBERS = ("name", "password")
NAME_CHARACTERS = (1, 32)
PASSWORD_CHARACTERS = (8, 63)
# Printable ASCII: with it a character is a byte, which is what the radio counts.
PRINTABLE = (0x20, 0x7E)


class Settings:
    """A name and a password. Its text form does not show the password."""

    def __init__(self, name, password):
        self.name = name
        self.password = password

    def __eq__(self, other):
        return isinstance(other, Settings) and (self.name, self.password) == (other.name, other.password)

    def __hash__(self):
        return hash((self.name, self.password))

    def __repr__(self):
        return f"Settings(name={self.name!r}, password=<hidden>)"


def _checked(value, limits, reason, what, of):
    """A value with a number of printable ASCII characters inside the limits."""
    low, high = limits
    if not low <= len(value) <= high:
        raise Failure(reason, f"the {what} has {len(value)} characters; {of} has {low} to {high}")
    if any(not PRINTABLE[0] <= ord(character) <= PRINTABLE[1] for character in value):
        raise Failure(reason, f"the {what} has a character that is not printable ASCII")
    return value


def _fault(detail):
    """What is wrong with a JSON text, in words that hold nothing of the text."""
    placed = re.match(r"line \d+, column \d+", detail)
    if placed:
        return f"a fault at {placed.group(0)}"
    if "appears twice" in detail:
        return "a member is named twice"
    if detail in ("not UTF-8", "starts with a byte-order mark", "nested too deeply"):
        return detail
    return "it is not one JSON value"


def read(path=paths.WIFI_SETTINGS):
    """The settings of a settings file, checked. No detail of a refusal quotes the file."""
    if not path.is_file():
        raise Failure("wifi-settings-missing", f"{path} is not there or is not a file")
    try:
        value = strictjson.loads(path.read_bytes())
    except json_errors.Rejection as refused:
        raise Failure("wifi-settings-malformed", f"{path} is not JSON: {_fault(refused.detail)}") from None
    if not isinstance(value, dict) or sorted(value) != sorted(MEMBERS) or not all(isinstance(value[member], str) for member in MEMBERS):
        raise Failure("wifi-settings-malformed", f"{path} is not an object with exactly the strings name and password")
    name = _checked(value["name"], NAME_CHARACTERS, "wifi-name-invalid", "name", "a network name")
    password = _checked(value["password"], PASSWORD_CHARACTERS, "wifi-password-invalid", "password", "a Wi-Fi password")
    return Settings(name, password)
