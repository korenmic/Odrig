"""ODRGX, the container of docs/format.md: a header of 20 bytes that names what the payload
is, and the payload. The reasons come in the order in which the core meets them reading a
file front to back: the header, the payload, and last the length the header gives the
payload."""

import dataclasses
import struct

from . import errors, odrg

MAGIC = b"ODRX"
VERSION = 1
HEADER = struct.Struct("<4sBBBBHHII")
ENDING = ".odrgx"

# The content types that are read, by number, the version of each, and the most bytes a
# payload of each may have.
TYPE_NAMES = {1: "frames", 2: "text"}
TYPE_VERSIONS = {1: 1, 2: 1}
LARGEST_PAYLOAD = {1: 0xFFFFFFFF, 2: 3612}


@dataclasses.dataclass(frozen=True)
class Header:
    type: int
    type_version: int
    width: int
    height: int
    loop_ms: int
    payload_size: int


def is_container(data):
    """Whether the bytes begin with the magic of a container."""
    return data[:4] == MAGIC


def read_header(data):
    """The checked header of a container given as bytes."""
    if len(data) < HEADER.size:
        raise errors.Rejection(errors.TRUNCATED, f"the file ends inside the {HEADER.size}-byte header")
    magic, version, kind, kind_version, reserved, width, height, loop_ms, payload_size = HEADER.unpack_from(data)
    if magic != MAGIC:
        raise errors.Rejection(errors.BAD_MAGIC, f"the file starts with {magic.hex(' ')}, not 4f 44 52 58")
    if version != VERSION or reserved != 0:
        raise errors.Rejection(errors.BAD_CONTAINER, f"the container's version is {version} and its reserved byte {reserved}, not {VERSION} and 0")
    if kind not in TYPE_NAMES:
        raise errors.Rejection(errors.UNKNOWN_TYPE, f"the content type is {kind}, not one of {', '.join(map(str, TYPE_NAMES))}")
    if kind_version != TYPE_VERSIONS[kind]:
        raise errors.Rejection(errors.UNKNOWN_TYPE_VERSION, f"the {TYPE_NAMES[kind]} version is {kind_version}, not {TYPE_VERSIONS[kind]}")
    if width == 0 or height == 0:
        raise errors.Rejection(errors.ZERO_SIZE, f"the canvas is {width} x {height}")
    if payload_size > LARGEST_PAYLOAD[kind]:
        raise errors.Rejection(errors.PAYLOAD_SIZE, f"a {TYPE_NAMES[kind]} payload of {payload_size} bytes is above {LARGEST_PAYLOAD[kind]}")
    return Header(kind, kind_version, width, height, loop_ms, payload_size)


def payload_of(data):
    return data[HEADER.size:]


def decode_frames(data):
    """The header of a container of frames and its payload decoded as `odrg.decode` does."""
    header = read_header(data)
    if header.type != 1:
        raise errors.Rejection(errors.UNKNOWN_TYPE, f"the content type is {header.type}, not frames")
    width, height, *_ = odrg.header(payload_of(data))
    if (width, height) != (header.width, header.height):
        raise errors.Rejection(errors.CANVAS_MISMATCH, f"the container's canvas is {header.width} x {header.height} and its frames' {width} x {height}")
    decoded = odrg.decode(payload_of(data))
    if len(data) - HEADER.size != header.payload_size:
        raise errors.Rejection(errors.PAYLOAD_SIZE, f"the header gives the payload {header.payload_size} bytes and it has {len(data) - HEADER.size}")
    loop = sum(duration for duration, _ in decoded.records)
    if loop != header.loop_ms:
        raise errors.Rejection(errors.LOOP_MISMATCH, f"the header gives a loop of {header.loop_ms} ms and the payload one of {loop} ms")
    return header, decoded


def wrap(kind, width, height, loop_ms, payload):
    """A container of a type, by its number, with this canvas, loop and payload."""
    return HEADER.pack(MAGIC, VERSION, kind, TYPE_VERSIONS[kind], 0, width, height, loop_ms, len(payload)) + bytes(payload)


def frames_of(data):
    """The ODRG file of a container of frames, or the bytes as they are for an ODRG file."""
    return payload_of(data) if is_container(data) else data
