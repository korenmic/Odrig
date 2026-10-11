"""ODRG, the runtime format of docs/format.md: the reference decoder.

The decoder follows the document step by step and favours clarity over speed. Every other
ODRG reader is checked against it.
"""

import dataclasses
import struct
import zlib

from . import errors

MAGIC = b"ODRG"
VERSION = 1
HEADER = struct.Struct("<4sBBHHHI")
RECORD_START = struct.Struct("<HHB")
COMPRESSED = 0x01
STORED = 0x40
LARGEST_PALETTE = 256
LARGEST_N = 65534
LARGEST_CODE = 255

_BITS_OF_BYTE = [f"{byte:08b}" for byte in range(256)]


@dataclasses.dataclass(frozen=True)
class Decoded:
    width: int
    height: int
    palette_size: int
    compressed: bool
    records: tuple[tuple[int, bytes], ...]
    modes: tuple[int, ...]


def decode(data):
    """Reads an ODRG file given as bytes.

    The result has one `(duration, picture)` for every frame record, in order: the picture
    the pixel buffer holds after that record.
    """
    if len(data) < HEADER.size:
        raise errors.Rejection(errors.TRUNCATED, f"the file ends inside the {HEADER.size}-byte header")
    magic, version, flags, width, height, palette_size, frame_count = HEADER.unpack_from(data)
    if magic != MAGIC:
        raise errors.Rejection(errors.BAD_MAGIC, f"the file starts with {magic.hex(' ')}, not 4f 44 52 47")
    if version != VERSION:
        raise errors.Rejection(errors.BAD_VERSION, f"version is {version}, not {VERSION}")
    if flags & ~COMPRESSED:
        raise errors.Rejection(errors.RESERVED_BITS, f"the flags byte is 0x{flags:02x}")
    if width == 0 or height == 0:
        raise errors.Rejection(errors.ZERO_SIZE, f"the canvas is {width} x {height}")
    if palette_size > LARGEST_PALETTE:
        raise errors.Rejection(errors.BAD_PALETTE_SIZE, f"the palette size is {palette_size}")
    bpp = 1 if palette_size else 3
    n = width * height * bpp
    if n > LARGEST_N:
        raise errors.Rejection(
            errors.CANVAS_TOO_LARGE, f"a picture of {width} x {height} is {n} bytes, above {LARGEST_N}"
        )
    if frame_count == 0:
        raise errors.Rejection(errors.NO_FRAMES, "the frame count is 0")

    compressed = bool(flags & COMPRESSED)
    body = _Bytes(_inflated(data[HEADER.size:]) if compressed else data[HEADER.size:])
    palette = [body.take(3, "the palette") for _ in range(palette_size)]

    buffer = bytes(n)
    records = []
    modes = []
    for number in range(1, frame_count + 1):
        what = f"frame record {number}"
        duration, length, mode = RECORD_START.unpack(body.take(RECORD_START.size, what))
        if duration == 0:
            raise errors.Rejection(errors.ZERO_DURATION, f"the duration of {what} is 0")
        if length < 2 or length > n + 1:
            raise errors.Rejection(errors.BAD_LENGTH, f"the length of {what} is {length}, not 2 to {n + 1}")
        if mode & 0x80 or (mode & STORED and mode != STORED):
            raise errors.Rejection(errors.RESERVED_BITS, f"the mode byte of {what} is 0x{mode:02x}")
        if mode == STORED and length != n + 1:
            raise errors.Rejection(
                errors.BAD_STORED_LENGTH, f"the length of stored {what} is {length}, not {n + 1}"
            )
        data_bytes = body.take(length - 1, what)
        if mode == STORED:
            buffer = data_bytes
        else:
            buffer = _coded(data_bytes, mode, buffer, width * bpp, bpp, what)
        if palette:
            for position, index in enumerate(buffer):
                if index >= palette_size:
                    raise errors.Rejection(
                        errors.BAD_PALETTE_INDEX,
                        f"pixel {position} of {what} has index {index}; the palette has {palette_size} entries",
                    )
            picture = b"".join(palette[index] for index in buffer)
        else:
            picture = buffer
        records.append((duration, picture))
        modes.append(mode)
    if body.left():
        raise errors.Rejection(
            errors.TRAILING_BYTES, f"{body.left()} bytes follow the last frame record"
        )
    return Decoded(width, height, palette_size, compressed, tuple(records), tuple(modes))


def _inflated(stream):
    """The output of the one raw DEFLATE stream that follows the header."""
    inflater = zlib.decompressobj(wbits=-15)
    try:
        body = inflater.decompress(stream) + inflater.flush()
    except zlib.error as error:
        raise errors.Rejection(errors.BAD_DEFLATE, str(error)) from None
    if not inflater.eof:
        raise errors.Rejection(errors.TRUNCATED, "the file ends inside the DEFLATE stream")
    if inflater.unused_data:
        raise errors.Rejection(
            errors.TRAILING_BYTES, f"{len(inflater.unused_data)} bytes follow the DEFLATE stream"
        )
    return body


def _coded(data, mode, old, stride, bpp, what):
    """The pixel buffer after a coded frame: codes, then residuals, then the predictor."""
    k = mode & 0x07
    run = bool(mode & 0x08)
    predictor = (mode >> 4) & 0x03
    n = len(old)
    bits = _Bits(data, what)

    def checked(code):
        if code > LARGEST_CODE:
            raise errors.Rejection(errors.BAD_CODE, f"code {i} of {what} is {code}, above {LARGEST_CODE}")
        return code

    codes = [0] * n
    if run:
        i = 0
        while i < n:
            g = bits.gamma()
            if i + g - 1 > n:
                raise errors.Rejection(
                    errors.RUN_PAST_END, f"a run of {g - 1} zero codes at code {i} of {what} passes {n}"
                )
            i += g - 1
            if i == n:
                break
            codes[i] = checked(bits.rice(k) + 1)
            i += 1
    else:
        for i in range(n):
            codes[i] = checked(bits.rice(k))
    if bits.left() >= 8:
        raise errors.Rejection(
            errors.TOO_MUCH_PADDING, f"{bits.left()} bits of {what} are unread after its {n} codes"
        )

    residuals = [code // 2 if code % 2 == 0 else (-(code + 1) // 2) % 256 for code in codes]

    new = bytearray(n)
    if predictor == 0:
        for i in range(n):
            new[i] = (old[i] + residuals[i]) % 256
    elif predictor == 1:
        d = bytearray(n)
        for i in range(n):
            d[i] = (residuals[i] + _neighbour(d, i, stride, bpp)) % 256
            new[i] = (old[i] + d[i]) % 256
    elif predictor == 2:
        for i in range(n):
            new[i] = (residuals[i] + _neighbour(new, i, stride, bpp)) % 256
    else:
        new[:] = residuals
    return bytes(new)


def _neighbour(a, i, stride, bpp):
    """The same channel of the pixel to the left, or of the first pixel of the row before."""
    if i % stride >= bpp:
        return a[i - bpp]
    if i >= stride:
        return a[i - stride]
    return 0


class _Bytes:
    """The body, read front to back."""

    def __init__(self, data):
        self.data = data
        self.position = 0

    def take(self, count, what):
        end = self.position + count
        if end > len(self.data):
            raise errors.Rejection(errors.TRUNCATED, f"the file ends inside {what}")
        taken = self.data[self.position:end]
        self.position = end
        return taken

    def left(self):
        return len(self.data) - self.position


class _Bits:
    """The data of a coded frame as bits, the most significant bit of each byte first."""

    def __init__(self, data, what):
        self.text = "".join(_BITS_OF_BYTE[byte] for byte in data)
        self.position = 0
        self.what = what

    def left(self):
        return len(self.text) - self.position

    def take(self, count):
        """The next `count` bits as a number."""
        end = self.position + count
        if end > len(self.text):
            raise self.out_of_bits()
        value = int(self.text[self.position:end], 2) if count else 0
        self.position = end
        return value

    def rice(self, k):
        """Reads one Rice(k) code: one-bits are counted up to a zero-bit or up to eight."""
        zero = self.text.find("0", self.position, self.position + 8)
        if zero < 0:
            self.take(8)
            return self.take(8)
        q = zero - self.position
        self.position = zero + 1
        return (q << k) + self.take(k)

    def gamma(self):
        """Reads one Gamma code whole: b - 1 zero-bits, then the b bits of the value."""
        one = self.text.find("1", self.position)
        if one < 0:
            raise self.out_of_bits()
        zeros = one - self.position
        self.position = one
        return self.take(zeros + 1)

    def out_of_bits(self):
        return errors.Rejection(errors.OUT_OF_BITS, f"{self.what} needs a bit after the last bit of its data")
