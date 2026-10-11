"""The mapping file of docs/mapping.md: the canvas size and the legs of one physical build."""

import dataclasses

from . import errors, files, strictjson

VERSION = 1
WIDEST = 65535
LARGEST_CANVAS = 65534
SIDES = ("left", "right")

_MEMBERS = ("version", "width", "legs")
_LEG_MEMBERS = ("leg", "pin", "first_led", "rows")


@dataclasses.dataclass(frozen=True)
class Leg:
    leg: int
    pin: int
    first_led: str
    rows: tuple[int, ...]


@dataclasses.dataclass(frozen=True)
class Mapping:
    width: int
    height: int
    legs: tuple[Leg, ...]


def read(path):
    """Reads a mapping file. A file that is absent is `mapping-missing`."""
    data = files.read(path, missing=errors.MAPPING_MISSING)
    with errors.naming(path):
        return loads(data)


def loads(data):
    """Reads a mapping file given as bytes. Every broken rule is `mapping-malformed`."""
    try:
        return _mapping(data)
    except errors.Rejection as rejection:
        if rejection.reason == errors.MAPPING_MALFORMED:
            raise
        raise errors.Rejection(
            errors.MAPPING_MALFORMED, f"{rejection.reason}: {rejection.detail}"
        ) from None


def _malformed(detail):
    return errors.Rejection(errors.MAPPING_MALFORMED, detail)


def _mapping(data):
    top = strictjson.loads(data)
    if type(top) is not dict:
        raise errors.Rejection(errors.BAD_JSON, "the top level is not an object")
    if "version" not in top:
        raise errors.Rejection(errors.MISSING_MEMBER, 'the file has no member "version"')
    version = strictjson.integer(top["version"], what="version")
    if version != VERSION:
        raise errors.Rejection(errors.BAD_VERSION, f"version is {version}, not {VERSION}")
    strictjson.members(top, _MEMBERS)
    width = strictjson.integer(top["width"], 1, WIDEST, what="width")
    listed = strictjson.array(top["legs"], what="legs")
    if not listed:
        raise _malformed("legs is empty")

    legs = []
    numbers = set()
    pins = set()
    for position, entry in enumerate(listed, 1):
        what = f"entry {position} of legs"
        strictjson.members(entry, _LEG_MEMBERS, what=what)
        number = strictjson.integer(entry["leg"], 1, 255, what=f"leg of {what}")
        if number in numbers:
            raise _malformed(f"two legs have the number {number}")
        numbers.add(number)
        pin = strictjson.integer(entry["pin"], 0, 255, what=f"pin of leg {number}")
        if pin in pins:
            raise _malformed(f"two legs have the pin {pin}")
        pins.add(pin)
        first_led = entry["first_led"]
        if type(first_led) is not str or first_led not in SIDES:
            raise _malformed(f'first_led of leg {number} is not "left" or "right"')
        rows = strictjson.array(entry["rows"], what=f"rows of leg {number}")
        if not rows:
            raise _malformed(f"rows of leg {number} is empty")
        for row in rows:
            strictjson.integer(row, what=f"a row of leg {number}")
        legs.append(Leg(number, pin, first_led, tuple(rows)))

    height = sum(len(leg.rows) for leg in legs)
    seen = set()
    for leg in legs:
        for row in leg.rows:
            if row < 1 or row > height:
                raise _malformed(f"row {row} of leg {leg.leg} is not from 1 to {height}, the number of rows")
            if row in seen:
                raise _malformed(f"row {row} is listed twice")
            seen.add(row)
    if width * height > LARGEST_CANVAS:
        raise _malformed(
            f"the canvas of {width} x {height} has {width * height} pixels, above {LARGEST_CANVAS}"
        )
    return Mapping(width, height, tuple(legs))
