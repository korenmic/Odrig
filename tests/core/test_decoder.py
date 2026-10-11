import random
import unittest
import zlib

from odrig import errors, jsonframes, odrg

from . import support

BLACK = bytes(3)


def by_the_reference(data):
    """What the reference decoder makes of a file, in the form of `support.Decoded`."""
    try:
        decoded = odrg.decode(data)
    except errors.Rejection as rejection:
        return None, None, rejection.reason
    header = (decoded.width, decoded.height, decoded.palette_size, len(decoded.records), decoded.compressed)
    return header, decoded.records, None


def seeded_animation(seed, width, height, colours, frames):
    """An animation that depends on the seed only.

    Its pictures change in the ways pictures do: not at all, in a few pixels, by a shift, in
    one row, in every pixel, to black, and by a small step in every value. With `colours`
    it uses that many colours at most; without, far more than a palette holds.
    """
    rng = random.Random(f"{seed} {width} {height} {colours} {frames}")
    palette = [BLACK] + [rng.randbytes(3) for _ in range(colours - 1)] if colours else None

    def colour():
        return rng.choice(palette) if palette else rng.randbytes(3)

    size = width * height
    picture = [colour() for _ in range(size)]
    result = []
    for _ in range(frames):
        change = rng.choice(("none", "few", "few", "shift", "row", "all", "black", "step"))
        if change == "few":
            for _ in range(rng.randint(1, max(1, size // 10))):
                picture[rng.randrange(size)] = colour()
        elif change == "shift":
            picture = picture[-1:] + picture[:-1]
        elif change == "row":
            start = rng.randrange(height) * width
            picture[start:start + width] = [colour()] * width
        elif change == "all":
            picture = [colour() for _ in range(size)]
        elif change == "black":
            picture = [BLACK] * size
        elif change == "step" and not palette:
            step = rng.randint(1, 3)
            picture = [bytes((value + step) % 256 for value in pixel) for pixel in picture]
        result.append((rng.choice((1, 20, 20, 40, 1000, 65535)), b"".join(picture)))
    return jsonframes.Animation(width, height, tuple(result))


class EncodedFiles(unittest.TestCase):
    def check(self, files):
        results = support.decode_each(files)
        for position, (data, result) in enumerate(zip(files, results)):
            header, records, reason = by_the_reference(data)
            self.assertIsNone(reason, f"the reference decoder refuses file {position}")
            self.assertIsNone(result.reason, f"file {position}")
            self.assertEqual(result.header, header, f"file {position}")
            self.assertEqual(len(result.records), len(records), f"file {position}")
            for number, (record, expected) in enumerate(zip(result.records, records), 1):
                self.assertEqual(record, expected, f"file {position}, record {number}")

    def test_files_of_the_encoder_on_canvases_from_1_x_1_to_60_x_60(self):
        files = []
        kinds = set()
        for width, height in ((1, 1), (1, 7), (7, 1), (2, 2), (5, 4), (17, 3), (60, 6), (60, 60)):
            for colours in (2, 40, 0):
                frames = 300 if width * height < 4 else 14
                animation = seeded_animation(1, width, height, colours, frames)
                for compressed in (True, False):
                    data = odrg.encode(animation, compressed=compressed)
                    kinds.add((data[10:12] != b"\0\0", compressed))
                    files.append(data)
        self.assertEqual(len(kinds), 4)
        self.assertEqual(len(files), 48)
        self.check(files)

    def test_the_encoder_used_stored_frames_three_predictors_and_both_modes(self):
        modes = set()
        for colours in (2, 40, 0):
            for width, height in ((5, 4), (17, 3), (60, 6)):
                data = odrg.encode(seeded_animation(1, width, height, colours, 14), compressed=False)
                modes.update(odrg.decode(data).modes)
        self.assertIn(odrg.STORED, modes)
        self.assertGreaterEqual(len({(mode >> 4) & 3 for mode in modes if mode != odrg.STORED}), 3)
        self.assertEqual({bool(mode & 8) for mode in modes if mode != odrg.STORED}, {False, True})

    def test_records_of_every_predictor_mode_and_k(self):
        files = []
        written = set()
        for palette_size in (0, 7):
            rng = random.Random(f"forced {palette_size}")
            width, height = 9, 5
            bpp = 1 if palette_size else 3
            n = width * height * bpp
            palette = [rng.randbytes(3) for _ in range(palette_size)] or None
            records = []
            old = bytes(n)
            for predictor in range(4):
                for run in (False, True):
                    for k in range(8):
                        # A picture that is black but for a few low values: every
                        # combination codes it in no more bytes than the picture has.
                        new = bytearray(n)
                        for _ in range(4):
                            new[rng.randrange(n)] = rng.choice((1, 2))
                        new = bytes(new)
                        records.append(odrg.coded_record(old, new, width, bpp, 20, predictor, run, k))
                        written.add((bpp, predictor, run, k))
                        old = new
            for deflate in (None, lambda body: zlib.compress(body, 9, wbits=-15)):
                files.append(odrg.container(width, height, palette, records, deflate))
        every = {(bpp, predictor, run, k) for bpp in (1, 3) for predictor in range(4) for run in (False, True) for k in range(8)}
        self.assertEqual(written, every)
        self.check(files)

    def test_a_picture_of_65534_bytes(self):
        animation = seeded_animation(2, 32767, 2, 5, 3)
        files = [odrg.encode(animation, compressed=compressed) for compressed in (True, False)]
        for data in files:
            self.assertEqual(int.from_bytes(data[6:8], "little") * int.from_bytes(data[8:10], "little"), 65534)
            self.assertNotEqual(data[10:12], b"\0\0")
        self.check(files)

    def test_a_compressed_body_above_32768_bytes_with_matches_far_back(self):
        # Three pictures of noise in turn on 60 x 60: every record is a stored picture of
        # 10,805 bytes, which the stream holds again 32,415 bytes back, near the far end
        # of the window.
        rng = random.Random(3)
        noise = [rng.randbytes(3 * 60 * 60) for _ in range(3)]
        animation = jsonframes.Animation(60, 60, tuple((20, noise[number % 3]) for number in range(12)))
        compressed = odrg.encode(animation, compressed=True)
        plain = odrg.encode(animation, compressed=False)
        body = zlib.decompress(compressed[16:], -15)
        self.assertEqual(len(body), 12 * 10805)
        self.assertGreater(len(body), 32768)
        self.assertEqual(body, plain[16:])
        self.assertLess(len(compressed), len(plain) // 2)
        self.check([compressed, plain])


class DamagedFiles(unittest.TestCase):
    def originals(self):
        files = []
        for width, height in ((1, 1), (3, 2), (5, 4), (9, 2)):
            for colours in (3, 30, 0):
                animation = seeded_animation(4, width, height, colours, 300 if width * height < 4 else 8)
                files += [odrg.encode(animation, compressed=True), odrg.encode(animation, compressed=False)]
        return files

    def compare(self, copies):
        results = support.decode_each(copies)
        outcomes = {}
        for position, (copy, result) in enumerate(zip(copies, results)):
            header, records, reason = by_the_reference(copy)
            self.assertEqual(result.reason, reason, f"copy {position}: {copy.hex()}")
            if reason is None:
                self.assertEqual(result.header, header, f"copy {position}: {copy.hex()}")
                self.assertEqual(result.records, records, f"copy {position}: {copy.hex()}")
            outcomes[reason] = outcomes.get(reason, 0) + 1
        return outcomes

    def test_copies_with_one_byte_changed_are_judged_as_the_reference_decoder_judges_them(self):
        rng = random.Random(5)
        originals = self.originals()
        copies = []
        while len(copies) < 2000:
            copy = bytearray(rng.choice(originals))
            at = rng.randrange(len(copy)) if rng.random() < 0.7 else rng.randrange(min(40, len(copy)))
            copy[at] = rng.choice([value for value in range(256) if value != copy[at]])
            copies.append(bytes(copy))
        outcomes = self.compare(copies)
        self.assertGreater(outcomes[None], 100)
        self.assertGreater(len(outcomes), 12)

    def test_copies_with_bytes_cut_out_or_put_in_are_judged_the_same_way(self):
        rng = random.Random(6)
        originals = self.originals()
        copies = []
        for _ in range(1000):
            copy = bytearray(rng.choice(originals))
            for _ in range(rng.randint(1, 3)):
                at = rng.randrange(len(copy) + 1)
                if rng.random() < 0.5:
                    del copy[at:at + rng.randint(1, 4)]
                else:
                    copy[at:at] = rng.randbytes(rng.randint(1, 4))
            copies.append(bytes(copy))
        outcomes = self.compare(copies)
        self.assertGreater(outcomes["truncated"], 20)
        self.assertGreater(outcomes["trailing-bytes"], 20)

    def test_every_prefix_of_a_file_is_refused_as_the_reference_decoder_refuses_it(self):
        animation = seeded_animation(7, 4, 3, 5, 6)
        for compressed in (True, False):
            data = odrg.encode(animation, compressed=compressed)
            prefixes = [data[:length] for length in range(len(data))]
            outcomes = self.compare(prefixes)
            self.assertEqual(sum(outcomes.values()), outcomes["truncated"])


if __name__ == "__main__":
    unittest.main()
