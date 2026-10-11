"""The mapping file of docs/mapping.md: the canvas size and the legs of one physical build.

A file is a row-leg file or a column-leg file. A strip is one straight run of LEDs of a
leg: a row of the canvas in a row-leg file, a column in a column-leg file.
"""

import collections
import dataclasses

from . import errors, files, strictjson

VERSION = 1
LONGEST_STRIP = 65535
LARGEST_CANVAS = 65534

ROWS = "rows"
COLUMNS = "columns"

# The names of one kind of file. `length` is the top-level member that gives the number of
# LEDs in every strip. `strips` is the member of a leg that lists its strips, and `strip`
# is what one of them is called. `ends` are the two values of `first_led`: the end of a
# strip where x or y is 1, then the other end.
_Names = collections.namedtuple("_Names", "length strips strip ends")
_NAMES = {
    ROWS: _Names("width", "rows", "row", ("left", "right")),
    COLUMNS: _Names("height", "columns", "column", ("bottom", "top")),
}


@dataclasses.dataclass(frozen=True)
class Leg:
    leg: int
    pin: int
    first_led: str            # "left" or "right" in a row leg, "bottom" or "top" in a column leg
    strips: tuple[int, ...]   # the y of each row, or the x of each column, in chain order


@dataclasses.dataclass(frozen=True)
class Mapping:
    kind: str                 # ROWS or COLUMNS
    width: int
    height: int
    legs: tuple[Leg, ...]

    @property
    def strip_length(self):
        """The number of LEDs in every strip."""
        return self.width if self.kind == ROWS else self.height

    def led_count(self, leg):
        """The number of LEDs of a leg."""
        return self.strip_length * len(leg.strips)


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


def position(canvas, leg, n):
    """The canvas position `(x, y)` of LED `n` of a leg, counted from 1 at the end wired to
    the board: the rule of docs/mapping.md, "Where each LED is", for the kind of the file."""
    length = canvas.strip_length
    if type(n) is not int or n < 1 or n > canvas.led_count(leg):
        raise ValueError(f"leg {leg.leg} has no LED {n}")
    strip, along = divmod(n - 1, length)
    low_end = _NAMES[canvas.kind].ends[0]
    # The first strip of the chain starts at the `first_led` end, and every strip after it
    # at the end opposite to the one before.
    starts_at_the_low_end = (leg.first_led == low_end) == (strip % 2 == 0)
    place = 1 + along if starts_at_the_low_end else length - along
    across = leg.strips[strip]
    return (place, across) if canvas.kind == ROWS else (across, place)


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
    if "width" in top and "height" in top:
        raise _malformed('the file has both "width" and "height"')
    if "width" not in top and "height" not in top:
        raise _malformed('the file has neither "width" nor "height"')
    kind = ROWS if "width" in top else COLUMNS
    names = _NAMES[kind]
    strictjson.members(top, ("version", names.length, "legs"))
    length = strictjson.integer(top[names.length], 1, LONGEST_STRIP, what=names.length)
    listed = strictjson.array(top["legs"], what="legs")
    if not listed:
        raise _malformed("legs is empty")

    legs = []
    numbers = set()
    pins = set()
    for place, entry in enumerate(listed, 1):
        what = f"entry {place} of legs"
        strictjson.members(entry, ("leg", "pin", "first_led", names.strips), what=what)
        number = strictjson.integer(entry["leg"], 1, 255, what=f"leg of {what}")
        if number in numbers:
            raise _malformed(f"two legs have the number {number}")
        numbers.add(number)
        pin = strictjson.integer(entry["pin"], 0, 255, what=f"pin of leg {number}")
        if pin in pins:
            raise _malformed(f"two legs have the pin {pin}")
        pins.add(pin)
        first_led = entry["first_led"]
        if type(first_led) is not str or first_led not in names.ends:
            raise _malformed(f'first_led of leg {number} is not "{names.ends[0]}" or "{names.ends[1]}"')
        strips = strictjson.array(entry[names.strips], what=f"{names.strips} of leg {number}")
        if not strips:
            raise _malformed(f"{names.strips} of leg {number} is empty")
        for strip in strips:
            strictjson.integer(strip, what=f"a {names.strip} of leg {number}")
        legs.append(Leg(number, pin, first_led, tuple(strips)))

    total = sum(len(leg.strips) for leg in legs)
    seen = set()
    for leg in legs:
        for strip in leg.strips:
            if strip < 1 or strip > total:
                raise _malformed(
                    f"{names.strip} {strip} of leg {leg.leg} is not from 1 to {total}, the number of {names.strips}"
                )
            if strip in seen:
                raise _malformed(f"{names.strip} {strip} is listed twice")
            seen.add(strip)
    width, height = (length, total) if kind == ROWS else (total, length)
    if width * height > LARGEST_CANVAS:
        raise _malformed(
            f"the canvas of {width} x {height} has {width * height} pixels, above {LARGEST_CANVAS}"
        )
    return Mapping(kind, width, height, tuple(legs))
