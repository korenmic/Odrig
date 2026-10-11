import random
import unittest
import zlib

from . import support

SIZES = (0, 1, 2, 5, 64, 1000, 4096, 32768, 70000, 200000)

LENGTH_BASE = (3, 4, 5, 6, 7, 8, 9, 10, 11, 13, 15, 17, 19, 23, 27, 31, 35, 43, 51, 59, 67, 83, 99, 115, 131, 163, 195, 227, 258)
LENGTH_EXTRA = (0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3, 4, 4, 4, 4, 5, 5, 5, 5, 0)
DISTANCE_BASE = (1, 2, 3, 4, 5, 7, 9, 13, 17, 25, 33, 49, 65, 97, 129, 193, 257, 385, 513, 769, 1025, 1537, 2049, 3073, 4097, 6145, 8193, 12289, 16385, 24577)
DISTANCE_EXTRA = (0, 0, 0, 0, 1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7, 8, 8, 9, 9, 10, 10, 11, 11, 12, 12, 13, 13)


def by_zlib(stream):
    """What zlib makes of a raw DEFLATE stream, in the form of `support.inflate_each`."""
    inflater = zlib.decompressobj(wbits=-15)
    try:
        output = inflater.decompress(stream) + inflater.flush()
    except zlib.error:
        return ("rejected", "bad-deflate")
    if not inflater.eof:
        return ("rejected", "truncated")
    return ("data", output, len(inflater.unused_data))


def deflated(data, level=9, strategy=zlib.Z_DEFAULT_STRATEGY):
    deflater = zlib.compressobj(level, zlib.DEFLATED, -15, 9, strategy)
    return deflater.compress(data) + deflater.flush()


def two_blocks(first, second):
    """A stream of a block for each text, with an empty stored block between them."""
    deflater = zlib.compressobj(9, zlib.DEFLATED, -15)
    stream = deflater.compress(first) + deflater.flush(zlib.Z_FULL_FLUSH)
    return stream + deflater.compress(second) + deflater.flush()


def seeded(kind, size, seed):
    """`size` bytes that depend on the seed only: noise, words, or runs of a few values."""
    rng = random.Random(f"{kind} {size} {seed}")
    if kind == "noise":
        return rng.randbytes(size)
    if kind == "words":
        words = [rng.randbytes(rng.randint(2, 9)) for _ in range(40)]
        text = bytearray()
        while len(text) < size:
            text += rng.choice(words)
        return bytes(text[:size])
    runs = bytearray()
    while len(runs) < size:
        runs += bytes([rng.choice(b"\x00\x00\x00\x01\x7f\xff")]) * rng.randint(1, 700)
    return bytes(runs[:size])


class Bits:
    """A DEFLATE stream written bit by bit."""

    def __init__(self):
        self.bits = []

    def number(self, value, count):
        """A number of `count` bits, least significant bit first."""
        self.bits.extend((value >> i) & 1 for i in range(count))
        return self

    def code(self, value, length):
        """A Huffman code of `length` bits, most significant bit first."""
        self.bits.extend((value >> i) & 1 for i in reversed(range(length)))
        return self

    def literal(self, symbol):
        """A literal or length symbol in the fixed code."""
        if symbol < 144:
            return self.code(0x30 + symbol, 8)
        if symbol < 256:
            return self.code(0x190 + symbol - 144, 9)
        if symbol < 280:
            return self.code(symbol - 256, 7)
        return self.code(0xC0 + symbol - 280, 8)

    def match(self, length, distance):
        """A length and distance pair in the fixed codes."""
        symbol = max(i for i, base in enumerate(LENGTH_BASE) if base <= length)
        if length == 258:
            symbol = 28
        self.literal(257 + symbol).number(length - LENGTH_BASE[symbol], LENGTH_EXTRA[symbol])
        symbol = max(i for i, base in enumerate(DISTANCE_BASE) if base <= distance)
        return self.code(symbol, 5).number(distance - DISTANCE_BASE[symbol], DISTANCE_EXTRA[symbol])

    def bytes(self):
        padded = self.bits + [0] * (-len(self.bits) % 8)
        return bytes(sum(bit << i for i, bit in enumerate(padded[at:at + 8])) for at in range(0, len(padded), 8))


def fixed_block(final=True):
    return Bits().number(1 if final else 0, 1).number(1, 2)


CODE_LENGTH_ORDER = (16, 17, 18, 0, 8, 7, 9, 6, 10, 5, 11, 4, 12, 3, 13, 2, 14, 1, 15)


def dynamic_block(length_codes, distance_codes, code_lengths):
    """The start of a final dynamic block: the three counts and the code-length code lengths."""
    bits = Bits().number(1, 1).number(2, 2)
    bits.number(length_codes - 257, 5).number(distance_codes - 1, 5).number(len(code_lengths) - 4, 4)
    for length in code_lengths:
        bits.number(length, 3)
    return bits


def dynamic_header(literal_lengths, distance_lengths):
    """The header of a final dynamic block whose codes have these lengths.

    The code-length code gives each length from 0 to 15 a code of four bits, so each length
    is written as itself.
    """
    listed = {symbol: length for symbol, length in enumerate(literal_lengths)}
    lengths = [listed.get(symbol, 0) for symbol in range(max(257, max(listed) + 1))]
    bits = dynamic_block(len(lengths), len(distance_lengths), [0 if symbol >= 16 else 4 for symbol in CODE_LENGTH_ORDER])
    for length in [*lengths, *distance_lengths]:
        bits.code(length, 4)
    return bits


def sparse(lengths):
    """Code lengths for literal and length symbols 0 to 257, zero except for those given."""
    return [lengths.get(symbol, 0) for symbol in range(258)]


class ValidStreams(unittest.TestCase):
    def check(self, streams):
        results = support.inflate_each(streams)
        for position, (stream, result) in enumerate(zip(streams, results)):
            expected = by_zlib(stream)
            self.assertEqual(expected[0], "data", f"zlib refuses stream {position}")
            self.assertEqual(result, expected, f"stream {position} of {len(stream)} bytes")

    def test_streams_of_zlib_at_three_levels_and_with_the_fixed_code(self):
        streams = []
        first_blocks = set()
        for kind in ("noise", "words", "runs"):
            for size in SIZES:
                data = seeded(kind, size, 1)
                for level, strategy in ((0, zlib.Z_DEFAULT_STRATEGY), (1, zlib.Z_DEFAULT_STRATEGY), (9, zlib.Z_DEFAULT_STRATEGY), (9, zlib.Z_FIXED)):
                    stream = deflated(data, level, strategy)
                    first_blocks.add((stream[0] >> 1) & 3)
                    streams.append(stream)
        self.assertEqual(first_blocks, {0, 1, 2})
        self.assertEqual(len(streams), 120)
        self.check(streams)

    def test_streams_of_several_blocks_of_every_type(self):
        rng = random.Random(2)
        streams = []
        for _ in range(20):
            stream = b""
            parts = rng.randint(2, 6)
            for part in range(parts):
                data = seeded(rng.choice(("noise", "words", "runs")), rng.choice((0, 1, 300, 5000, 40000)), rng.random())
                level, strategy = rng.choice(((0, zlib.Z_DEFAULT_STRATEGY), (6, zlib.Z_DEFAULT_STRATEGY), (9, zlib.Z_FIXED), (9, zlib.Z_HUFFMAN_ONLY), (9, zlib.Z_RLE)))
                deflater = zlib.compressobj(level, zlib.DEFLATED, -15, 9, strategy)
                stream += deflater.compress(data)
                stream += deflater.flush(zlib.Z_FINISH if part == parts - 1 else zlib.Z_FULL_FLUSH)
            streams.append(stream)
        self.check(streams)

    def test_matches_at_the_longest_distance_and_of_the_longest_length(self):
        rng = random.Random(3)
        start = rng.randbytes(32768)
        expected = bytearray(start)
        bits = fixed_block()
        for byte in start:
            bits.literal(byte)
        for length, distance in ((258, 32768), (258, 32768), (3, 32768), (258, 1), (4, 32767), (257, 24577), (258, 258), (5, 3)):
            bits.match(length, distance)
            for _ in range(length):
                expected.append(expected[-distance])
        stream = bits.literal(256).bytes()
        self.assertEqual(zlib.decompress(stream, -15), bytes(expected))
        self.assertEqual(support.inflate_each([stream]), [("data", bytes(expected), 0)])

    def test_the_bytes_after_a_stream_are_not_taken(self):
        for data in (b"", b"abc", seeded("words", 3000, 4)):
            for level in (0, 9):
                stream = deflated(data, level)
                results = support.inflate_each([stream + bytes(extra) for extra in (0, 1, 2, 600)])
                self.assertEqual(results, [("data", data, extra) for extra in (0, 1, 2, 600)])

    def test_a_stream_given_alone_on_standard_input(self):
        data = seeded("words", 500, 5)
        lines = support.host_lines("inflate", stdin=deflated(data) + b"..")
        self.assertEqual(lines, [f"data {data.hex()}", "left 2"])


class InvalidStreams(unittest.TestCase):
    def test_what_the_format_forbids_is_bad_deflate(self):
        # Symbol 97 is the code 10, the end of the block 11 and length symbol 257 the code 0.
        letter_end_length = sparse({97: 2, 256: 2, 257: 1})
        streams = {
            "block type 3, last block": b"\x07",
            "block type 3": b"\x06",
            "a stored length and its complement that disagree": b"\x01\x05\x00\x00\x00hello",
            "287 literal and length codes": dynamic_block(287, 1, [0, 0, 0, 0]).bytes() + bytes(40),
            "31 distance codes": dynamic_block(257, 31, [0, 0, 0, 0]).bytes() + bytes(40),
            "an over-subscribed code-length code": dynamic_block(257, 1, [1, 1, 1, 1]).bytes() + bytes(40),
            "an incomplete code-length code": dynamic_block(257, 1, [1, 0, 0, 0]).bytes() + bytes(40),
            "a code-length code without codes": dynamic_block(257, 1, [0, 0, 0, 0]).bytes() + bytes(40),
            "a repeat with nothing to repeat": dynamic_block(257, 1, [1, 0, 0, 1]).code(1, 1).number(0, 2).bytes() + bytes(40),
            "a repeat that passes the end": dynamic_block(257, 1, [0, 0, 1, 1]).code(1, 1).number(127, 7).code(1, 1).number(127, 7).bytes() + bytes(40),
            "no code for the end of the block": dynamic_block(257, 1, [0, 0, 1, 1]).code(1, 1).number(127, 7).code(1, 1).number(109, 7).bytes() + bytes(40),
            "an over-subscribed literal code": dynamic_header(sparse({0: 1, 1: 1, 2: 1, 256: 1}), [0]).bytes() + bytes(40),
            "an incomplete literal code": dynamic_header(sparse({0: 2, 256: 2}), [0]).bytes() + bytes(40),
            "an over-subscribed distance code": dynamic_header(letter_end_length, [1, 1, 1]).bytes() + bytes(40),
            "an incomplete distance code": dynamic_header(letter_end_length, [2, 2]).bytes() + bytes(40),
            "a bit pattern outside a literal code of one code": dynamic_header(sparse({256: 1}), [0]).code(1, 1).bytes() + bytes(40),
            "a bit pattern outside a distance code of one code": dynamic_header(letter_end_length, [1]).code(2, 2).code(0, 1).code(1, 1).bytes() + bytes(40),
            "a length where there is no distance code": dynamic_header(letter_end_length, [0]).code(2, 2).code(0, 1).code(0, 1).bytes() + bytes(40),
            "length symbol 286": fixed_block().literal(65).literal(286).bytes() + bytes(4),
            "distance symbol 30": fixed_block().literal(65).literal(257).code(30, 5).bytes() + bytes(4),
            "a distance beyond the start": fixed_block().literal(65).match(3, 2).literal(256).bytes(),
            "a distance with nothing before it": fixed_block().match(3, 1).literal(256).bytes(),
        }
        results = support.inflate_each(list(streams.values()))
        for (name, stream), result in zip(streams.items(), results):
            with self.subTest(name=name):
                self.assertEqual(by_zlib(stream), ("rejected", "bad-deflate"))
                self.assertEqual(result, ("rejected", "bad-deflate"))

    def test_what_the_format_allows_at_its_edges_is_decoded(self):
        letter_end_length = sparse({97: 2, 256: 2, 257: 1})
        streams = {
            "a literal code of one code": (dynamic_header(sparse({256: 1}), [0]).code(0, 1).bytes(), b""),
            "a distance code of one code": (dynamic_header(letter_end_length, [1]).code(2, 2).code(0, 1).code(0, 1).code(3, 2).bytes(), b"aaaa"),
            "no distance code and no length": (dynamic_header(letter_end_length, [0]).code(2, 2).code(3, 2).bytes(), b"a"),
            "an empty stored block": (b"\x01\x00\x00\xff\xff", b""),
            "an empty fixed block": (fixed_block().literal(256).bytes(), b""),
            "a stored block of 65,535 bytes": (b"\x01\xff\xff\x00\x00" + bytes(65535), bytes(65535)),
        }
        results = support.inflate_each([stream for stream, _ in streams.values()])
        for (name, (stream, output)), result in zip(streams.items(), results):
            with self.subTest(name=name):
                self.assertEqual(by_zlib(stream), ("data", output, 0))
                self.assertEqual(result, ("data", output, 0))

    def test_a_stream_that_ends_inside_a_header_is_truncated_before_it_is_judged(self):
        streams = [
            dynamic_block(257, 1, [0, 0, 0, 0]).bytes() + bytes(10),
            dynamic_block(257, 1, [1, 0, 0, 1]).code(1, 1).bytes()[:-1],
            dynamic_header(sparse({0: 1, 1: 1, 2: 1, 256: 1}), [0]).bytes()[:-1],
            b"\x01\x05\x00\x00",
            fixed_block().literal(65).literal(257).bytes()[:2],
        ]
        results = support.inflate_each(streams)
        for position, (stream, result) in enumerate(zip(streams, results)):
            with self.subTest(position=position):
                self.assertEqual(by_zlib(stream), ("rejected", "truncated"))
                self.assertEqual(result, ("rejected", "truncated"))

    def test_every_prefix_of_a_short_stream_is_truncated(self):
        for name, stream in (
            ("stored", deflated(seeded("noise", 40, 6), 0)),
            ("fixed", deflated(seeded("words", 120, 6), 9, zlib.Z_FIXED)),
            ("dynamic", deflated(seeded("words", 900, 6), 9)),
            ("several blocks", two_blocks(seeded("words", 300, 6), seeded("runs", 300, 6))),
        ):
            with self.subTest(name=name):
                self.assertLess(len(stream), 700)
                prefixes = [stream[:length] for length in range(len(stream))]
                results = support.inflate_each(prefixes + [stream])
                self.assertEqual(results[-1][0], "data")
                self.assertEqual(results[:-1], [("rejected", "truncated")] * len(prefixes))
                self.assertEqual([by_zlib(prefix) for prefix in prefixes], results[:-1])

    def test_damaged_copies_are_judged_as_zlib_judges_them(self):
        rng = random.Random(7)
        originals = []
        for kind in ("noise", "words", "runs"):
            for size in (0, 3, 60, 400, 2500):
                data = seeded(kind, size, 7)
                originals += [deflated(data, 0), deflated(data, 9), deflated(data, 9, zlib.Z_FIXED), deflated(data, 1)]
        originals.append(two_blocks(seeded("words", 700, 8), seeded("runs", 700, 8)))
        copies = []
        while len(copies) < 2000:
            copy = bytearray(rng.choice(originals))
            at = rng.randrange(len(copy))
            if rng.random() < 0.5:
                copy[at] ^= 1 << rng.randrange(8)
            else:
                copy[at] = rng.choice([value for value in range(256) if value != copy[at]])
            copies.append(bytes(copy))
        results = support.inflate_each(copies)
        outcomes = {"data": 0, "bad-deflate": 0, "truncated": 0}
        for position, (copy, result) in enumerate(zip(copies, results)):
            self.assertEqual(result, by_zlib(copy), f"copy {position}: {copy.hex()}")
            outcomes[result[0] if result[0] == "data" else result[1]] += 1
        for outcome, count in outcomes.items():
            self.assertGreater(count, 50, outcome)

    def test_noise_after_a_block_header_is_judged_as_zlib_judges_it(self):
        rng = random.Random(8)
        headers = (0x05, 0x04, 0x0D, 0x0C, 0x15, 0xBD, 0xED, 0x01, 0x00, 0x03, 0x02)
        streams = [bytes([rng.choice(headers)]) + rng.randbytes(rng.randint(0, 60)) for _ in range(4000)]
        results = support.inflate_each(streams)
        outcomes = {"data": 0, "bad-deflate": 0, "truncated": 0}
        for position, (stream, result) in enumerate(zip(streams, results)):
            self.assertEqual(result, by_zlib(stream), f"stream {position}: {stream.hex()}")
            outcomes[result[0] if result[0] == "data" else result[1]] += 1
        for outcome, count in outcomes.items():
            self.assertGreater(count, 20, outcome)

    def test_cut_and_lengthened_copies_are_judged_as_zlib_judges_them(self):
        rng = random.Random(9)
        originals = [deflated(seeded(kind, size, 9), level) for kind in ("noise", "words", "runs") for size in (0, 30, 800) for level in (0, 9)]
        copies = []
        for _ in range(600):
            copy = bytearray(rng.choice(originals))
            for _ in range(rng.randint(1, 3)):
                at = rng.randrange(len(copy) + 1)
                if rng.random() < 0.5 and copy:
                    del copy[at:at + rng.randint(1, 4)]
                else:
                    copy[at:at] = rng.randbytes(rng.randint(1, 4))
            copies.append(bytes(copy))
        results = support.inflate_each(copies)
        for position, (copy, result) in enumerate(zip(copies, results)):
            self.assertEqual(result, by_zlib(copy), f"copy {position}: {copy.hex()}")


if __name__ == "__main__":
    unittest.main()
