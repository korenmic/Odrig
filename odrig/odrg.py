"""ODRG, the runtime format of docs/format.md: the reference decoder and the encoder.

The decoder follows the document step by step and favours clarity over speed. Every other
ODRG reader is checked against it. The encoder follows the converter guidance of the
document and writes the same bytes for the same frames every time.
"""

import collections
import dataclasses
import fractions
import re
import struct
import zlib

from . import errors, jsonframes

MAGIC = b"ODRG"
VERSION = 1
HEADER = struct.Struct("<4sBBHHHI")
RECORD_START = struct.Struct("<HHB")
COMPRESSED = 0x01
STORED = 0x40
LARGEST_PALETTE = 256
LARGEST_N = 65534
LARGEST_CODE = 255
LONGEST_DURATION = 65535
MOST_FRAMES = 0xFFFFFFFF

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


def encode(animation, compressed=True):
    """The bytes of an ODRG file that shows the animation, with the smallest frame records."""
    frames = jsonframes.merged(animation.frames)
    palette = palette_for(frames)
    bpp = 1 if palette else 3
    n = animation.width * animation.height * bpp
    if n > LARGEST_N:
        raise errors.Rejection(
            errors.CANVAS_TOO_LARGE,
            f"a picture of {animation.width} x {animation.height} would be {n} bytes, above {LARGEST_N}",
        )
    count = sum(-(-ms // LONGEST_DURATION) for ms, _ in frames)
    if count > MOST_FRAMES:
        raise errors.Rejection(
            errors.TOO_MANY_FRAMES, f"{count} frame records would be needed, above {MOST_FRAMES}"
        )
    records = []
    old = bytes(n)
    for ms, picture in frames:
        new = to_buffer(picture, palette)
        while ms:
            duration = min(ms, LONGEST_DURATION)
            records.append(best_record(old, new, animation.width, bpp, duration))
            old = new
            ms -= duration
    return container(animation.width, animation.height, palette, records, _deflate if compressed else None)


def palette_for(frames):
    """The colours of the frames ordered by hue, or `None` when there are more than 256."""
    seen = set()
    for picture in {picture for _, picture in frames}:
        seen.update(jsonframes.colours(picture))
        if len(seen) > LARGEST_PALETTE:
            return None
    return sorted((colour.to_bytes(3, "big") for colour in seen), key=_hue_order)


def _hue_order(colour):
    """Hue, then saturation, then brightness, as exact fractions; no hue counts as hue 0."""
    r, g, b = colour
    mx, mn = max(colour), min(colour)
    d = mx - mn
    if d == 0:
        h = fractions.Fraction(0)
    elif mx == r:
        h = fractions.Fraction(g - b, d) % 6
    elif mx == g:
        h = fractions.Fraction(b - r, d) + 2
    else:
        h = fractions.Fraction(r - g, d) + 4
    s = fractions.Fraction(d, mx) if mx else fractions.Fraction(0)
    return h, s, mx


def to_buffer(picture, palette):
    """The pixel buffer of a picture: its bytes, or one palette index for each pixel."""
    if palette is None:
        return picture
    index = {int.from_bytes(colour, "big"): position for position, colour in enumerate(palette)}
    return bytes(index[colour] for colour in jsonframes.colours(picture))


def stored_record(new, duration):
    """A frame record that holds the new pixel buffer as it is."""
    return RECORD_START.pack(duration, len(new) + 1, STORED) + new


def coded_record(old, new, width, bpp, duration, predictor, run, k):
    """A coded frame record written with the given predictor, mode and k."""
    codes = _codes(old, new, width * bpp, bpp, predictor)
    rice = _RICE_TEXT[k]
    if run:
        pieces = []
        zeros = 0
        for code in codes:
            if code == 0:
                zeros += 1
            else:
                pieces.append(_gamma_text(zeros + 1))
                pieces.append(rice[code - 1])
                zeros = 0
        if zeros:
            pieces.append(_gamma_text(zeros + 1))
        text = "".join(pieces)
    else:
        text = "".join(rice[code] for code in codes)
    text += "0" * (-len(text) % 8)
    data = int(text, 2).to_bytes(len(text) // 8, "big")
    if len(data) > len(new):
        raise ValueError(f"{len(data)} bytes of data do not fit a record for a picture of {len(new)} bytes")
    mode = k | (0x08 if run else 0) | predictor << 4
    return RECORD_START.pack(duration, len(data) + 1, mode) + data


def best_record(old, new, width, bpp, duration):
    """The frame record with the fewest bytes of data; a stored one when coding saves nothing.

    Among equally small coded records the lowest predictor wins, then plain mode, then the
    lowest k.
    """
    best = None
    for predictor in range(4):
        codes = _codes(old, new, width * bpp, bpp, predictor)
        for run, k, size in _data_sizes(codes):
            if best is None or size < best[0]:
                best = (size, predictor, run, k)
    size, predictor, run, k = best
    if size >= len(new):
        return stored_record(new, duration)
    return coded_record(old, new, width, bpp, duration, predictor, run, k)


def container(width, height, palette, records, deflate=None):
    """A whole file: the header, then the palette and the records, through `deflate` if given."""
    body = b"".join(palette or ()) + b"".join(records)
    flags = 0
    if deflate is not None:
        body = deflate(body)
        flags = COMPRESSED
    header = HEADER.pack(MAGIC, VERSION, flags, width, height, len(palette or ()), len(records))
    return header + body


def _deflate(body):
    """One raw DEFLATE stream with a window of 32,768 bytes."""
    deflater = zlib.compressobj(9, zlib.DEFLATED, -15)
    return deflater.compress(body) + deflater.flush()


def _codes(old, new, stride, bpp, predictor):
    """The N codes that turn `old` into `new` with a predictor, one byte each."""
    if predictor == 0:
        residuals = _minus(new, old)
    elif predictor == 1:
        change = _minus(new, old)
        residuals = _minus(change, _neighbours(change, stride, bpp))
    elif predictor == 2:
        residuals = _minus(new, _neighbours(new, stride, bpp))
    elif predictor == 3:
        residuals = new
    else:
        raise ValueError(f"there is no predictor {predictor}")
    return residuals.translate(_CODE_OF_RESIDUAL)


def _minus(a, b):
    return bytes((x - y) & 0xFF for x, y in zip(a, b))


def _neighbours(a, stride, bpp):
    """`nb(a, i)` for every i: each row moved one pixel to the right, led by the row before."""
    result = bytearray()
    above = bytes(bpp)
    for start in range(0, len(a), stride):
        row = a[start:start + stride]
        result += above
        result += row[:stride - bpp]
        above = row[:bpp]
    return bytes(result)


def _data_sizes(codes):
    """`(run, k, bytes of data)` for plain mode and run mode with every k, in that order."""
    histogram = collections.Counter(codes)
    zero_runs = [len(zeros) for zeros in _ZERO_RUN.findall(codes)]
    non_zero = len(codes) - histogram[0]
    runs_before_a_code = len(zero_runs) - (1 if codes.endswith(b"\x00") else 0)
    gamma_bits = sum(2 * (zeros + 1).bit_length() - 1 for zeros in zero_runs) + non_zero - runs_before_a_code
    sizes = []
    for k in range(8):
        bits = _RICE_BITS[k]
        plain = sum(count * bits[code] for code, count in histogram.items())
        sizes.append((False, k, (plain + 7) // 8))
    for k in range(8):
        bits = _RICE_BITS[k]
        rice = sum(count * bits[code - 1] for code, count in histogram.items() if code)
        sizes.append((True, k, (gamma_bits + rice + 7) // 8))
    return sizes


def _rice_text(k, value):
    q = value >> k
    if q >= 8:
        return "1" * 8 + f"{value:08b}"
    low = f"{value & ((1 << k) - 1):0{k}b}" if k else ""
    return "1" * q + "0" + low


def _gamma_text(g):
    return "0" * (g.bit_length() - 1) + f"{g:b}"


_CODE_OF_RESIDUAL = bytes(2 * r if r < 128 else 2 * (256 - r) - 1 for r in range(256))
_RICE_TEXT = [[_rice_text(k, value) for value in range(256)] for k in range(8)]
_RICE_BITS = [[len(text) for text in row] for row in _RICE_TEXT]
_ZERO_RUN = re.compile(b"\x00+")
