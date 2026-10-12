"""Builds the test vectors in tests/vectors. Run by hand, from the repository root:

    python -m tests.converter.build_vectors

Every file is made from fixed data and seeded choices, so a second run writes the same
bytes. The frame records are forced with the building blocks of the encoder, and the
expected frames of a vector come from the pictures the builder started with, never from a
decoder.
"""

import collections
import pathlib
import random
import struct
import zlib

from odrig import jsonframes, odrg

VECTORS = pathlib.Path(__file__).resolve().parents[1] / "vectors"

Valid = collections.namedtuple("Valid", "name odrg json zlib")
Invalid = collections.namedtuple("Invalid", "name reason odrg valid zlib")

STORED_BLOCKS, FIXED_BLOCKS, DYNAMIC_BLOCKS = 0, 1, 2


class Dice:
    """Seeded choices that use only `Random.random()`, whose sequence Python keeps stable."""

    def __init__(self, seed):
        self._random = random.Random(seed)

    def below(self, count):
        return int(self._random.random() * count)

    def chance(self, probability):
        return self._random.random() < probability

    def shuffled(self, items):
        items = list(items)
        for last in range(len(items) - 1, 0, -1):
            other = self.below(last + 1)
            items[last], items[other] = items[other], items[last]
        return items


def residual(code):
    """The residual byte a code stands for: 0, -1, +1, -2, +2, ... modulo 256."""
    return code // 2 if code % 2 == 0 else (256 - (code + 1) // 2) % 256


def neighbour(a, i, stride, bpp):
    if i % stride >= bpp:
        return a[i - bpp]
    if i >= stride:
        return a[i - stride]
    return 0


def grow(old, width, bpp, predictor, limit, choose):
    """Builds a new pixel buffer byte by byte and returns it with the codes that spell it.

    `choose(i)` lists the codes to try for byte i, in order. The first one whose byte is
    below `limit` is taken, so the bytes of a palette file stay inside its palette.
    """
    stride = width * bpp
    new = bytearray(len(old))
    change = bytearray(len(old))
    codes = bytearray(len(old))
    for i in range(len(old)):
        if predictor == 0:
            expected = old[i]
        elif predictor == 1:
            expected = old[i] + neighbour(change, i, stride, bpp)
        elif predictor == 2:
            expected = neighbour(new, i, stride, bpp)
        else:
            expected = 0
        for code in choose(i):
            value = (expected + residual(code)) % 256
            if value < limit:
                break
        else:
            raise RuntimeError(f"no code fits byte {i} with predictor {predictor}")
        new[i] = value
        change[i] = (value - old[i]) % 256
        codes[i] = code
    return bytes(new), bytes(codes)


def rice_bits(k, value):
    return (value >> k) + 1 + k if value >> k < 8 else 16


def uses_escape(codes, run, k):
    """Whether writing the codes takes the long form of a Rice code."""
    if run:
        return any(code and (code - 1) >> k >= 8 for code in codes)
    return any(code >> k >= 8 for code in codes)


def short_codes(k):
    """The codes that plain mode writes with at most 8 bits, so N of them fit in N bytes."""
    return range(min((8 - k) << k, 128))


def plain_choice(dice, k):
    return lambda i: dice.shuffled(short_codes(k))


def run_choice(dice, k, zero=0.55, end=None):
    """Codes for run mode: often zero. `end` forces the last byte: "zero" or "code"."""

    def choose(i):
        others = dice.shuffled(code + 1 for code in short_codes(k))
        if end == "zero" and i == choose.last:
            return [0]
        if end == "code" and i == choose.last:
            return others
        return [0] + others if dice.chance(zero) else others + [0]

    choose.last = None
    return choose


def colours(count, seed):
    """`count` different colours."""
    dice = Dice(seed)
    made = []
    while len(made) < count:
        colour = bytes(dice.below(256) for _ in range(3))
        if colour not in made:
            made.append(colour)
    return made


class Film:
    """One file in the making: its frame records and the picture after each of them."""

    def __init__(self, width, height, palette=None):
        self.width = width
        self.height = height
        self.palette = palette
        self.bpp = 1 if palette else 3
        self.limit = len(palette) if palette else 256
        self.buffer = bytes(width * height * self.bpp)
        self.records = []
        self.frames = []
        self.escapes = 0

    def coded(self, duration, predictor, run, k, choose):
        if hasattr(choose, "last"):
            choose.last = len(self.buffer) - 1
        new, intended = grow(self.buffer, self.width, self.bpp, predictor, self.limit, choose)
        if odrg.codes(self.buffer, new, self.width, self.bpp, predictor) != intended:
            raise RuntimeError("the encoder's codes are not the codes the picture was built from")
        self.escapes += uses_escape(intended, run, k)
        self.records.append(
            odrg.coded_record(self.buffer, new, self.width, self.bpp, duration, predictor, run, k)
        )
        self._show(duration, new)
        return intended

    def stored(self, duration, new):
        self.records.append(odrg.stored_record(new, duration))
        self._show(duration, new)

    def _show(self, duration, new):
        self.buffer = new
        if self.palette:
            picture = b"".join(self.palette[index] for index in new)
        else:
            picture = new
        self.frames.append((duration, picture))

    def odrg(self, deflate=None):
        return odrg.container(self.width, self.height, self.palette, self.records, deflate)

    def json(self):
        animation = jsonframes.Animation(self.width, self.height, tuple(self.frames))
        return jsonframes.dumps(animation, merge=False)

    def valid(self, name, deflate=None):
        return Valid(name, self.odrg(deflate), self.json(), deflate is not None)


def deflate_with(level, strategy=zlib.Z_DEFAULT_STRATEGY):
    def deflate(body):
        deflater = zlib.compressobj(level, zlib.DEFLATED, -15, 8, strategy)
        return deflater.compress(body) + deflater.flush()

    return deflate


def fixed_block(body):
    """A raw DEFLATE stream of one block with the fixed codes, every byte as a literal,
    written without zlib."""
    bits = [1, 1, 0]
    for value in body:
        code, length = (0x30 + value, 8) if value < 144 else (0x190 + value - 144, 9)
        bits += [(code >> (length - 1 - place)) & 1 for place in range(length)]
    bits += [0] * 7
    bits += [0] * (-len(bits) % 8)
    return bytes(sum(bit << place for place, bit in enumerate(bits[at:at + 8])) for at in range(0, len(bits), 8))


def fixed_codes(deflate):
    """A deflate whose output is one block of the fixed codes: what zlib makes when it is
    told to use them, and where a zlib does not do as told, the block written here."""
    def made(body):
        data = deflate(body)
        return data if data[0] & 7 == 0b011 else fixed_block(body)

    return made


def first_block(data):
    """`(is the last block, block type)` of the first DEFLATE block of a compressed file."""
    first = data[16]
    return bool(first & 1), (first >> 1) & 3


def every_combination(film, dice):
    """One coded record for each of the 64 combinations of predictor, mode and k."""
    for predictor in range(4):
        for run in (False, True):
            for k in range(8):
                choose = run_choice(dice, k) if run else plain_choice(dice, k)
                film.coded(20, predictor, run, k, choose)
    if film.escapes:
        raise RuntimeError("the combinations are meant to do without the escape code")
    return film


def escape_film():
    """Plain and run records for k from 0 to 4 with codes on both sides of the escape."""
    film = Film(6, 4)
    dice = Dice(31)
    for k in range(5):
        first_long = 8 << k
        for run in (False, True):
            if run:
                wanted = [first_long - 1, first_long, first_long + 1, 255]
            else:
                wanted = [first_long - 1, first_long, 255]
            places = dict(zip(dice.shuffled(range(len(film.buffer)))[:len(wanted)], wanted))

            def choose(i, places=places, run=run, k=k):
                if i in places:
                    return [places[i]]
                if run:
                    return [0] if dice.chance(0.6) else [1 + dice.below(2 << k)]
                return [dice.below(2 << k)]

            codes = film.coded(20 + k, (k + run) % 4, run, k, choose)
            if not set(wanted) <= set(codes):
                raise RuntimeError("the escape record lost a code it was built for")
    if film.escapes != 10:
        raise RuntimeError("every record of the escape vector uses the escape code")
    return film


def stored_film(palette):
    """Stored records: first in the file, after a coded record and after a stored one."""
    film = Film(3, 2, palette)
    dice = Dice(41)
    size = len(film.buffer)
    film.stored(20, bytes(dice.below(film.limit) for _ in range(size)))
    film.coded(40, 0, False, 1, plain_choice(dice, 1))
    film.stored(60, bytes(dice.below(film.limit) for _ in range(size)))
    film.stored(80, bytes(film.limit - 1 - index % film.limit for index in range(size)))
    return film


def run_to_end_film():
    """Run-mode records that end in a zero run, and records whose codes are all zero."""
    film = Film(5, 3)
    dice = Dice(51)
    for predictor, k in ((3, 0), (0, 1), (1, 2), (2, 3), (0, 5), (2, 7)):
        codes = film.coded(20, predictor, True, k, run_choice(dice, k, end="zero"))
        if codes[-1] != 0 or not any(codes):
            raise RuntimeError("the record does not end in a zero run after a code")
    for predictor, k in ((0, 0), (1, 4)):
        codes = film.coded(20, predictor, True, k, lambda i: [0])
        if any(codes):
            raise RuntimeError("the record is meant to have only zero codes")
    return film


def run_last_nonzero_film():
    """Run-mode records whose last code is not zero, so nothing follows it."""
    film = Film(5, 3)
    dice = Dice(61)
    for predictor, k in ((3, 0), (0, 1), (1, 2), (2, 3), (3, 4), (0, 6), (1, 7)):
        codes = film.coded(20, predictor, True, k, run_choice(dice, k, end="code"))
        if codes[-1] == 0:
            raise RuntimeError("the last code is meant to be other than zero")
    return film


def long_run_film():
    """Zero runs longer than 255 codes on a 20 x 16 canvas with a palette."""
    film = Film(20, 16, colours(4, 71))
    plans = (
        (3, 0, {300: 2}),
        (0, 1, {0: 2, 256: 2}),
        (0, 0, {257: 2, 300: 1}),
        (0, 3, {0: 1}),
        (2, 2, {10: 2}),
        (1, 0, {319: 2}),
    )
    for predictor, k, places in plans:
        film.coded(20, predictor, True, k, lambda i, places=places: [places.get(i, 0)])
    return film


def durations_film():
    """Records of 1 ms and of 65,535 ms."""
    film = Film(2, 2)
    dice = Dice(81)
    film.coded(1, 3, False, 3, plain_choice(dice, 3))
    film.coded(65535, 0, True, 0, lambda i: [0])
    film.coded(65535, 0, False, 2, plain_choice(dice, 2))
    film.stored(1, bytes(dice.below(256) for _ in range(12)))
    film.stored(65535, bytes(dice.below(256) for _ in range(12)))
    return film


def palette_256_film():
    """A 16 x 16 file whose first picture uses each of 256 palette entries once."""
    film = Film(16, 16, colours(256, 91))
    dice = Dice(92)
    film.stored(20, bytes(dice.shuffled(range(256))))
    film.coded(20, 0, True, 0, run_choice(dice, 0, zero=0.9))
    film.coded(20, 0, False, 1, plain_choice(dice, 1))
    return film


def palette_1_film():
    """A palette of one colour: every index is 0."""
    film = Film(3, 3, colours(1, 101))
    film.coded(20, 0, True, 0, lambda i: [0])
    film.stored(20, bytes(9))
    film.coded(20, 3, False, 0, lambda i: [0])
    film.coded(20, 2, True, 3, lambda i: [0])
    return film


def small_canvas_film(width, height, palette, seed):
    """A canvas one pixel wide or high, with every predictor, 1 and 2 twice."""
    film = Film(width, height, palette)
    dice = Dice(seed)
    for predictor, run, k in ((3, False, 2), (1, False, 1), (2, False, 2), (0, False, 0), (1, True, 0), (2, True, 1)):
        choose = run_choice(dice, k, zero=0.4) if run else plain_choice(dice, k)
        film.coded(20, predictor, run, k, choose)
    return film


def one_pixel_film(palette, seed):
    """A 1 x 1 canvas. With a palette there is one byte, so a coded record is one code."""
    film = Film(1, 1, palette)
    dice = Dice(seed)
    for predictor, k in ((1, 0), (2, 1), (0, 2), (3, 0), (1, 3), (2, 0)):
        film.coded(20, predictor, False, k, plain_choice(dice, k))
    film.stored(20, bytes(dice.below(film.limit) for _ in range(len(film.buffer))))
    film.coded(20, 1, False, 0, plain_choice(dice, 0))
    return film


def deflate_film():
    """A body that is worth a code of its own: bytes with a skewed spread and few repeats."""
    film = Film(12, 6)
    dice = Dice(111)
    size = len(film.buffer)
    for _ in range(6):
        film.stored(20, bytes(dice.below(dice.below(96) + 1) for _ in range(size)))
        film.coded(20, 0, False, 2, plain_choice(dice, 2))
    return film


def encoded_cases():
    """Two short animations written by `encode`, compressed: with and without a palette."""
    bar = colours(5, 121)
    with_palette = []
    for step in range(8):
        picture = bytearray()
        for y in range(4):
            for x in range(12):
                picture += bar[1 + (x + y + step) % 4] if (x + step) % 6 < 2 else bar[0]
        with_palette.append((20 * (step + 1), bytes(picture)))
    without = []
    for step in range(8):
        picture = bytearray()
        for y in range(5):
            for x in range(9):
                picture += bytes((16 * x + 2 * step, 24 * y + 3 * step, 3 * (x + 9 * y) + 7 * step))
        without.append((40, bytes(picture)))

    cases = []
    for name, width, height, frames, palette in (
        ("encoded.pal", 12, 4, with_palette, True),
        ("encoded.rgb", 9, 5, without, False),
    ):
        if jsonframes.merged(frames) != frames or (odrg.palette_for(frames) is not None) != palette:
            raise RuntimeError("the animation is not of the kind the vector is named for")
        animation = jsonframes.Animation(width, height, tuple(frames))
        data = odrg.encode(animation, compressed=True)
        if struct.unpack_from("<I", data, 12)[0] != len(frames):
            raise RuntimeError("the encoder did not write one record for each frame")
        cases.append(Valid(name, data, jsonframes.dumps(animation, merge=False), True))
    return cases


def valid_cases():
    """Every valid vector: its name, the ODRG bytes, the expected frames, and whether zlib made it."""
    cases = [
        every_combination(Film(4, 3), Dice(11)).valid("rgb-modes"),
        every_combination(Film(5, 4, colours(7, 21)), Dice(22)).valid("pal-modes"),
        escape_film().valid("escape"),
        stored_film(None).valid("stored.rgb"),
        stored_film(colours(5, 42)).valid("stored.pal"),
        run_to_end_film().valid("run-to-end"),
        run_last_nonzero_film().valid("run-last-nonzero"),
        long_run_film().valid("long-run"),
        durations_film().valid("durations"),
        palette_256_film().valid("pal-256"),
        palette_1_film().valid("pal-1"),
        small_canvas_film(1, 5, None, 131).valid("one-wide.rgb"),
        small_canvas_film(1, 5, colours(6, 132), 133).valid("one-wide.pal"),
        small_canvas_film(5, 1, None, 134).valid("one-high.rgb"),
        small_canvas_film(5, 1, colours(6, 135), 136).valid("one-high.pal"),
        one_pixel_film(None, 137).valid("one-pixel.rgb"),
        one_pixel_film(colours(9, 138), 139).valid("one-pixel.pal"),
    ]
    body = deflate_film()
    for name, deflate, kind in (
        ("deflate-stored", deflate_with(0), STORED_BLOCKS),
        ("deflate-fixed", fixed_codes(deflate_with(9, zlib.Z_FIXED)), FIXED_BLOCKS),
        ("deflate-dynamic", deflate_with(9), DYNAMIC_BLOCKS),
    ):
        case = body.valid(name, deflate)
        if first_block(case.odrg) != (True, kind):
            raise RuntimeError(f"{name} is not one DEFLATE block of the kind its name says")
        cases.append(case)
    cases += encoded_cases()
    for case in cases:
        if len(case.odrg) > 4096:
            raise RuntimeError(f"{case.name} is {len(case.odrg)} bytes, above 4,096")
    return cases


def compose(width, height, palette, records, magic=b"ODRG", version=1, flags=0, colours=None,
            frames=None, wrap=None):
    """A file put together field by field, so that any one field can be made wrong."""
    body = b"".join(palette) + b"".join(records)
    if wrap is not None:
        body = wrap(body)
        flags |= 1
    header = struct.pack(
        "<4sBBHHHI",
        magic,
        version,
        flags,
        width,
        height,
        len(palette) if colours is None else colours,
        len(records) if frames is None else frames,
    )
    return header + body


def record(duration, mode, data, length=None):
    """A frame record put together by hand. `length` overrides the right value of L."""
    if length is None:
        length = len(data) + 1
    return struct.pack("<HHB", duration, length, mode) + data


def changed(whole, duration=None, length=None, mode=None, data=None):
    """A frame record with some of its parts replaced."""
    old_duration, old_length, old_mode = struct.unpack_from("<HHB", whole)
    return record(
        old_duration if duration is None else duration,
        old_mode if mode is None else mode,
        whole[5:] if data is None else data,
        (old_length if data is None else len(data) + 1) if length is None else length,
    )


def bits(text):
    """Bytes from a string of 0 and 1; spaces are ignored and zero-bits fill the last byte."""
    text = text.replace(" ", "")
    text += "0" * (-len(text) % 8)
    return bytes(int(text[at:at + 8], 2) for at in range(0, len(text), 8))


def stored_block(body):
    """A raw DEFLATE stream of one stored block, written without zlib."""
    return b"\x01" + struct.pack("<HH", len(body), len(body) ^ 0xFFFF) + body


def invalid_cases():
    """Every invalid vector: a valid file with one defect, named for the reason of its rejection.

    Each case carries the valid bytes it was changed from. None is made with zlib.
    """
    cases = []

    def case(name, odrg_bytes, valid):
        cases.append(Invalid(name, name.split(".")[0], odrg_bytes, valid, False))

    # A 3 x 2 file with a palette of 4: a coded record, a stored record, a coded record.
    palette = colours(4, 201)
    film = Film(3, 2, palette)
    dice = Dice(202)
    film.coded(20, 3, False, 1, plain_choice(dice, 1))
    film.stored(40, bytes([3, 0, 1, 2, 3, 0]))
    film.coded(60, 0, True, 0, run_choice(dice, 0, end="zero"))
    first, stored, last = film.records
    n = len(film.buffer)
    base = compose(3, 2, palette, film.records)
    body = base[16:]
    packed = compose(3, 2, palette, film.records, wrap=stored_block)
    start_of_stored = 16 + 3 * len(palette) + len(first)

    case("truncated.header", base[:10], base)
    case("truncated.palette", base[:16 + 5], base)
    case("truncated.record-start", base[:start_of_stored + 3], base)
    case("truncated.record-data", base[:start_of_stored + 5 + 2], base)
    case("truncated.deflate", packed[:-3], packed)
    case("truncated.deflate-body", base[:5] + b"\x01" + base[6:16] + stored_block(body[:-2]), packed)

    case("bad-magic", compose(3, 2, palette, film.records, magic=b"ODRH"), base)
    case("bad-version", compose(3, 2, palette, film.records, version=2), base)
    case("reserved-bits.flag", compose(3, 2, palette, film.records, flags=0x02), base)
    case(
        "reserved-bits.mode-bit-7",
        compose(3, 2, palette, [changed(first, mode=first[4] | 0x80), stored, last]),
        base,
    )
    case(
        "reserved-bits.stored-mode",
        compose(3, 2, palette, [first, changed(stored, mode=0x41), last]),
        base,
    )
    case("zero-size.width", compose(0, 2, palette, film.records), base)
    case("zero-size.height", compose(3, 0, palette, film.records), base)
    case("bad-palette-size", compose(3, 2, palette, film.records, colours=257), base)
    case("no-frames", compose(3, 2, palette, film.records, frames=0), base)

    case("bad-deflate.block-type", packed[:16] + b"\x07" + packed[17:], packed)
    case("bad-deflate.stored-length", packed[:19] + bytes([packed[19] ^ 0x01]) + packed[20:], packed)

    case("zero-duration", compose(3, 2, palette, [first, changed(stored, duration=0), last]), base)
    case("bad-length.below-2", compose(3, 2, palette, [first, stored, changed(last, length=1)]), base)
    case("bad-length.above-n-plus-1", compose(3, 2, palette, [first, stored, changed(last, length=n + 2)]), base)
    case("bad-stored-length", compose(3, 2, palette, [first, changed(stored, length=n), last]), base)

    case("bad-palette-index.stored", compose(3, 2, palette, [first, changed(stored, data=bytes([3, 0, 1, 2, 4, 0])), last]), base)
    case("trailing-bytes.body", base + b"\x00", base)
    case("trailing-bytes.deflate-body", base[:5] + b"\x01" + base[6:16] + stored_block(body + b"\x00"), packed)
    case("trailing-bytes.after-deflate", packed + b"\x00", packed)

    # The largest canvases, and each of them one pixel wider.
    all_zero = record(20, 0x08, bits("0" * 15 + "1" * 16))
    one_colour = colours(1, 203)
    case(
        "canvas-too-large.palette",
        compose(65535, 1, one_colour, [all_zero]),
        compose(65534, 1, one_colour, [all_zero]),
    )
    all_zero = record(20, 0x08, bits("0" * 15 + "1111111111111101"))
    case("canvas-too-large.rgb", compose(21845, 1, [], [all_zero]), compose(21844, 1, [], [all_zero]))

    # A 2 x 1 file with a palette of 3. Predictor 3, plain mode, k = 0: the codes 4 and 0 are
    # the indexes 2 and 0, and the code 6 would be the index 3.
    three = colours(3, 204)
    case(
        "bad-palette-index.coded",
        compose(2, 1, three, [record(20, 0x30, bits("1111110 0"))]),
        compose(2, 1, three, [record(20, 0x30, bits("11110 0"))]),
    )

    # A 2 x 2 file without a palette: twelve codes.
    film = Film(2, 2)
    dice = Dice(205)
    film.coded(20, 3, False, 2, plain_choice(dice, 2))
    plain = film.records[0]
    valid = compose(2, 2, [], [plain])
    case("out-of-bits.plain", compose(2, 2, [], [changed(plain, data=plain[5:-1])]), valid)
    if len(plain) - 5 >= 12:
        raise RuntimeError("the record has no room for a byte of padding")
    case("too-much-padding", compose(2, 2, [], [changed(plain, data=plain[5:] + b"\x00")]), valid)
    # Predictor 0, run mode, k = 0. Gamma 13 = 0001101 is twelve zero codes; Gamma 14 is thirteen.
    case(
        "run-past-end",
        compose(2, 2, [], [record(20, 0x08, bits("0001110"))]),
        compose(2, 2, [], [record(20, 0x08, bits("0001101"))]),
    )

    # A 20 x 16 file with a palette of 2: 320 codes. Predictor 3, run mode, k = 0: Gamma 1 and
    # Rice 1 = 10 make the first code 2, the index 1; Gamma 320 = 00000000 101000000 ends the
    # buffer. Without its last byte the Gamma code is cut off.
    two = colours(2, 206)
    long_run = record(20, 0x38, bits("1 10 00000000 101000000"))
    case(
        "out-of-bits.gamma",
        compose(20, 16, two, [changed(long_run, data=long_run[5:-1])]),
        compose(20, 16, two, [long_run]),
    )

    # A 2 x 1 file without a palette: six codes. Predictor 3, plain mode, k = 6: 1110 111111 is
    # the code 255 and 11110 000000 would be the code 256. Five codes 0 = 0 000000 follow.
    zeros = " 0 000000" * 5
    case(
        "bad-code.plain",
        compose(2, 1, [], [record(20, 0x36, bits("11110 000000" + zeros))]),
        compose(2, 1, [], [record(20, 0x36, bits("1110 111111" + zeros))]),
    )
    # Predictor 3, run mode, k = 0: Gamma 1, then Rice 254 in the long form makes the code
    # 255, and Rice 255 would make it 256. Gamma 6 = 00110 ends the buffer.
    case(
        "bad-code.run",
        compose(2, 1, [], [record(20, 0x38, bits("1 11111111 11111111 00110"))]),
        compose(2, 1, [], [record(20, 0x38, bits("1 11111111 11111110 00110"))]),
    )

    for made in cases:
        if len(made.odrg) > 4096 or len(made.valid) > 4096:
            raise RuntimeError(f"{made.name} is above 4,096 bytes")
    if len({made.name for made in cases}) != len(cases):
        raise RuntimeError("two invalid vectors have the same name")
    return cases


def write(folder, files):
    """Makes `folder` hold exactly `files`, a mapping from file name to bytes."""
    folder.mkdir(parents=True, exist_ok=True)
    for stale in folder.iterdir():
        if stale.name not in files:
            stale.unlink()
    for name, data in files.items():
        (folder / name).write_bytes(data)


def valid_files():
    files = {}
    for case in valid_cases():
        files[f"{case.name}.odrg"] = case.odrg
        files[f"{case.name}.json"] = case.json
    return files


def invalid_files():
    return {f"{case.name}.odrg": case.odrg for case in invalid_cases()}


def main():
    write(VECTORS / "valid", valid_files())
    write(VECTORS / "invalid", invalid_files())


if __name__ == "__main__":
    main()
