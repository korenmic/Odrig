"""The record file: what the core gave every leg at every tick of a recording.

All integers are little-endian. A 16-byte header is followed by eight bytes for each leg
and by one record of `9 + B` bytes for each tick, B being the LED bytes of all legs.
"""

import collections
import contextlib
import os
import struct

MAGIC = b"ODRR"
VERSION = 1
TICK_MS = 20

HEADER = struct.Struct("<4sBBHII")
LEG = struct.Struct("<HHI")
TICK = struct.Struct("<QB")

Tick = collections.namedtuple("Tick", "ms produced data")
Tick.__doc__ = """One tick: its time, whether the core produced a refresh, and the LED bytes of
all legs, each leg's in chain order, the legs in header order."""

Recording = collections.namedtuple("Recording", "legs tick_ms led_bytes ticks")
Recording.__doc__ = """A record file. `legs` holds `(leg, pin, LED count)` for each leg."""


def write(path, legs, ticks):
    """Writes a record file with these legs and the ticks an iterable gives.

    Each tick is `(ms, produced, data)`. The file is written beside `path` as
    `<path>.part` and takes its place once it is complete; when anything fails, no `.part`
    file is left and an existing file is as it was.
    """
    legs = [tuple(leg) for leg in legs]
    led_bytes = 3 * sum(count for _, _, count in legs)
    dark = bytes(led_bytes)
    part = f"{os.fspath(path)}.part"
    try:
        with open(part, "wb") as file:
            file.write(HEADER.pack(MAGIC, VERSION, 0, len(legs), TICK_MS, led_bytes))
            for leg in legs:
                file.write(LEG.pack(*leg))
            for ms, produced, data in ticks:
                if produced and len(data) != led_bytes:
                    raise ValueError(f"a refresh of {len(data)} bytes for legs of {led_bytes}")
                file.write(TICK.pack(ms, 1 if produced else 0))
                file.write(data if produced else dark)
        os.replace(part, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.remove(part)
        raise


def read(path):
    """The content of a record file."""
    with open(path, "rb") as file:
        data = file.read()
    magic, version, zero, leg_count, tick_ms, led_bytes = HEADER.unpack_from(data, 0)
    if magic != MAGIC or version != VERSION or zero != 0:
        raise ValueError(f"{path} is not a record file of version {VERSION}")
    legs = tuple(LEG.unpack_from(data, HEADER.size + LEG.size * index) for index in range(leg_count))
    if led_bytes != 3 * sum(count for _, _, count in legs):
        raise ValueError(f"{path}: the LED bytes do not match the legs")
    start = HEADER.size + LEG.size * leg_count
    size = TICK.size + led_bytes
    if (len(data) - start) % size:
        raise ValueError(f"{path} ends inside a tick")
    ticks = []
    for offset in range(start, len(data), size):
        ms, produced = TICK.unpack_from(data, offset)
        ticks.append(Tick(ms, bool(produced), data[offset + TICK.size:offset + size]))
    return Recording(legs, tick_ms, led_bytes, tuple(ticks))


def split(recording, data):
    """The LED bytes of one tick, cut into the bytes of each leg."""
    parts = []
    offset = 0
    for _, _, count in recording.legs:
        parts.append(data[offset:offset + 3 * count])
        offset += 3 * count
    return tuple(parts)
