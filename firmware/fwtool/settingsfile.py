"""A settings file of the repository: one JSON value, read strictly. A refusal says what
is wrong in fixed words and quotes nothing of the file."""

import re

from odrig import errors as json_errors
from odrig import strictjson

from . import Failure


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


def value_of(path, missing, malformed):
    """The JSON value of a file, or a refusal with one of the two reasons."""
    if not path.is_file():
        raise Failure(missing, f"{path} is not there or is not a file")
    try:
        return strictjson.loads(path.read_bytes())
    except json_errors.Rejection as refused:
        raise Failure(malformed, f"{path} is not JSON: {_fault(refused.detail)}") from None
