import json
import random
import tempfile
import unittest
from pathlib import Path

from odrig import errors, limits

WHITE = b"\xff\xff\xff"
SNAKE = 180
FULL_WHITE_SNAKE = WHITE * SNAKE


def picture(rng, leds, brightest=255, density=1.0):
    """The bytes of a leg of random LEDs."""
    return bytes(rng.randint(0, brightest) if rng.random() < density else 0 for _ in range(3 * leds))


def by_definition(parts, budget):
    """The level of the rule, found by trying every level from 254 down."""
    estimate = sum(limits.estimate(part) for part in parts)
    if budget <= 0 or estimate <= budget:
        return 255
    if budget <= sum(len(part) // 3 for part in parts):
        return 1
    for level in range(254, 0, -1):
        if sum(limits.estimate(limits.fade(part, level)) for part in parts) <= budget:
            return level
    return 1


class TheEstimate(unittest.TestCase):
    def test_an_led_at_rest_is_one_milliamp_and_full_white_55_more(self):
        self.assertEqual(limits.estimate(bytes(3 * 60)), 60)
        self.assertEqual(limits.estimate(WHITE + bytes(3 * 59)), 55 + 60)
        self.assertEqual(limits.estimate(FULL_WHITE_SNAKE), 180 * 55 + 180)
        self.assertEqual(limits.estimate(b""), 0)

    def test_the_sum_of_the_bytes_is_rounded_down_once_for_the_leg(self):
        self.assertEqual(limits.estimate(bytes([1, 0, 0])), 1)
        self.assertEqual(limits.estimate(bytes([14, 0, 0])), 1 + 1)
        self.assertEqual(limits.estimate(bytes([13, 0, 0])), 0 + 1)
        self.assertEqual(limits.estimate(bytes([7, 7, 0])), 1 + 1)

    def test_the_installation_at_full_white_is_201600_milliamps(self):
        self.assertEqual(sum(limits.estimate(FULL_WHITE_SNAKE) for _ in range(20)), 201600)


class TheFade(unittest.TestCase):
    def test_at_255_nothing_changes(self):
        data = bytes(range(256)) * 3
        self.assertEqual(limits.fade(data, 255), data)

    def test_a_black_led_stays_black_and_a_lit_channel_above_a_quarter_keeps_its_lowest_bit(self):
        self.assertEqual(limits.fade(bytes(3), 1), bytes(3))
        self.assertEqual(limits.fade(WHITE, 1), b"\x01\x01\x01")
        self.assertEqual(limits.fade(WHITE, 7), b"\x07\x07\x07")
        self.assertEqual(limits.fade(WHITE, 8), b"\x09\x09\x09")
        self.assertEqual(limits.fade(WHITE, 254), bytes([253, 253, 253]))

    def test_a_dim_led_keeps_its_hue_as_far_as_wled_keeps_it(self):
        faded = limits.fade(bytes([200, 100, 40, 4, 1, 0, 255, 0, 0, 2, 2, 2]), 1)
        self.assertEqual(faded, bytes([1, 1, 0, 1, 0, 0, 1, 0, 0, 1, 1, 1]))

    def test_a_low_even_byte_can_be_raised_by_one(self):
        self.assertEqual(limits.fade(bytes([2, 2, 2]), 254), bytes([3, 3, 3]))
        self.assertEqual(limits.fade(bytes([4, 0, 0]), 254), bytes([5, 0, 0]))

    def test_each_byte_is_faded_by_the_rule(self):
        rng = random.Random(45)
        for _ in range(300):
            led = bytes(rng.choice((0, 1, 2, 3, 4, 63, 64, 65, 128, 200, 255)) for _ in range(3))
            level = rng.randint(1, 254)
            kept = (max(led) >> 2) + 1
            wanted = led if led == bytes(3) else bytes(((b * level + 127) >> 8) | (1 if b > kept else 0) for b in led)
            self.assertEqual(limits.fade(led, level), wanted, (led, level))

    def test_the_order_of_the_three_bytes_does_not_matter(self):
        rng = random.Random(3)
        data = picture(rng, 200)
        turned = b"".join(bytes([data[at + 1], data[at + 2], data[at]]) for at in range(0, len(data), 3))
        for level in (1, 9, 128, 254):
            faded = limits.fade(turned, level)
            back = b"".join(bytes([faded[at + 2], faded[at], faded[at + 1]]) for at in range(0, len(faded), 3))
            self.assertEqual(limits.fade(data, level), back)

    def test_the_estimate_of_the_faded_bytes_never_falls_as_the_level_rises(self):
        rng = random.Random(7)
        for _ in range(20):
            data = picture(rng, 30, brightest=rng.choice((3, 40, 255)), density=rng.choice((0.3, 1.0)))
            found = [limits.estimate(limits.fade(data, level)) for level in range(1, 255)]
            self.assertEqual(found, sorted(found))
        # A fade can raise a low even byte, so the faded bytes may be estimated above the
        # bytes as they are, which the level 255 leaves.
        twos = bytes([2]) * 540
        self.assertGreater(limits.estimate(limits.fade(twos, 254)), limits.estimate(twos))

    def test_a_level_outside_1_to_255_is_no_level(self):
        for level in (0, 256, -1, 1.0):
            with self.assertRaises(ValueError):
                limits.fade(WHITE, level)


class TheLevel(unittest.TestCase):
    def test_a_full_white_snake_with_500_milliamps_is_held_at_level_7_and_451(self):
        self.assertEqual(limits.level(FULL_WHITE_SNAKE, 500), 7)
        self.assertEqual(limits.estimate(limits.fade(FULL_WHITE_SNAKE, 7)), 451)
        self.assertEqual(limits.estimate(limits.fade(FULL_WHITE_SNAKE, 8)), 529)

    def test_wleds_level_would_leave_684(self):
        estimate = limits.estimate(FULL_WHITE_SNAKE)
        self.assertEqual(estimate, 10080)
        wleds = 500 * 255 // estimate + 1
        self.assertEqual(wleds, 13)
        self.assertEqual(limits.estimate(limits.fade(FULL_WHITE_SNAKE, wleds)), 684)

    def test_no_budget_or_an_estimate_within_it_dims_nothing(self):
        self.assertEqual(limits.level(FULL_WHITE_SNAKE, 0), 255)
        self.assertEqual(limits.level(FULL_WHITE_SNAKE, 10080), 255)
        self.assertEqual(limits.level(FULL_WHITE_SNAKE, 65535), 255)
        self.assertEqual(limits.level(FULL_WHITE_SNAKE, 10079), 254)

    def test_a_budget_at_or_below_the_leds_at_rest_is_level_1(self):
        for budget in (1, 100, 179, 180):
            with self.subTest(budget=budget):
                self.assertEqual(limits.level(FULL_WHITE_SNAKE, budget), 1)

    def test_level_1_when_no_level_brings_the_estimate_within_the_budget(self):
        self.assertEqual(limits.estimate(limits.fade(FULL_WHITE_SNAKE, 1)), 218)
        self.assertEqual(limits.level(FULL_WHITE_SNAKE, 181), 1)
        self.assertEqual(limits.level(FULL_WHITE_SNAKE, 217), 1)
        self.assertEqual(limits.level(FULL_WHITE_SNAKE, 218), 1)
        self.assertEqual([limits.estimate(limits.fade(FULL_WHITE_SNAKE, level)) for level in (2, 3, 4)], [296, 296, 374])
        self.assertEqual(limits.level(FULL_WHITE_SNAKE, 295), 1)
        self.assertEqual(limits.level(FULL_WHITE_SNAKE, 296), 3)

    def test_a_dark_picture_is_level_1_only_below_its_leds_at_rest(self):
        dark = bytes(3 * SNAKE)
        self.assertEqual(limits.level(dark, 179), 1)
        self.assertEqual(limits.level(dark, 180), 255)
        self.assertEqual(limits.level(dark, 0), 255)

    def test_the_halving_finds_the_level_of_the_definition(self):
        rng = random.Random(12)
        for number in range(60):
            data = picture(rng, rng.choice((1, 18, 60)), brightest=rng.choice((3, 8, 40, 255)), density=rng.choice((0.05, 0.5, 1.0)))
            budget = rng.randint(0, limits.estimate(data) + 3)
            with self.subTest(picture=number, budget=budget):
                self.assertEqual(limits.level(data, budget), by_definition((data,), budget))

    def test_the_halving_takes_eight_fades(self):
        found = []
        fade = limits.fade

        def counted(data, level):
            found.append(level)
            return fade(data, level)

        limits.fade = counted
        try:
            for budget in (181, 500, 9000, 10079):
                found.clear()
                limits.level(FULL_WHITE_SNAKE, budget)
                self.assertEqual(len(found), 8, budget)
                self.assertEqual(found[0], 128)
        finally:
            limits.fade = fade

    def test_the_wall_counts_all_its_legs_and_estimates_each_leg_on_its_own(self):
        legs = [bytes([255, 255, 1]) * 5, bytes([1, 0, 0]) * 7, WHITE * 3]
        whole = sum(limits.estimate(leg) for leg in legs)
        joined = limits.estimate(b"".join(legs))
        self.assertNotEqual(whole, joined)
        self.assertEqual(limits.wall_level(legs, whole), 255)
        self.assertEqual(limits.wall_level(legs, whole - 1), by_definition(legs, whole - 1))
        self.assertEqual(limits.wall_level(legs, 15), 1)
        self.assertEqual(limits.wall_level([bytes(3 * 15)], 14), 1)


class TheOrder(unittest.TestCase):
    def test_without_budgets_nothing_changes(self):
        rng = random.Random(1)
        legs = [picture(rng, 180) for _ in range(20)]
        found = limits.limit(legs, [0] * 20, 0)
        self.assertEqual(found.legs, tuple(legs))
        self.assertEqual(found.estimates, tuple(limits.estimate(leg) for leg in legs))
        self.assertEqual(found.limited, (False,) * 20)
        self.assertEqual(found.wall_estimate, sum(found.estimates))
        self.assertFalse(found.wall_limited)

    def test_a_snakes_budget_dims_that_snake_alone(self):
        found = limits.limit([FULL_WHITE_SNAKE] * 20, [500] + [0] * 19, 0)
        self.assertEqual(found.legs[0], bytes([7]) * 540)
        self.assertEqual(found.legs[1:], (FULL_WHITE_SNAKE,) * 19)
        self.assertEqual(found.estimates, (451,) + (10080,) * 19)
        self.assertEqual(found.limited, (True,) + (False,) * 19)
        self.assertEqual(found.wall_estimate, 451 + 19 * 10080)
        self.assertFalse(found.wall_limited)

    def test_the_wall_at_730_holds_the_installation_at_level_1(self):
        rng = random.Random(15)
        legs = [bytes(rng.choice((0, 0, 3, 40, 128, 255)) for _ in range(540)) for _ in range(20)]
        found = limits.limit(legs, [0] * 20, 730)
        self.assertTrue(found.wall_limited)
        self.assertEqual(found.limited, (False,) * 20)
        for before, after in zip(legs, found.legs):
            for at in range(0, 540, 3):
                led = before[at:at + 3]
                kept = (max(led) >> 2) + 1
                self.assertEqual(after[at:at + 3], bytes(1 if value > kept else 0 for value in led))
        self.assertGreater(found.wall_estimate, 730)
        self.assertEqual(limits.limit([bytes(540)] * 20, [0] * 20, 730).legs, (bytes(540),) * 20)

    def test_a_budget_at_or_below_the_leds_at_rest_holds_every_led_at_its_lowest_level(self):
        found = limits.limit([FULL_WHITE_SNAKE, FULL_WHITE_SNAKE], [100, 0], 0)
        self.assertEqual(found.legs[0], b"\x01" * 540)
        self.assertEqual(found.estimates, (218, 10080))
        self.assertEqual(found.limited, (True, False))
        # A wall that dims at a level that keeps a byte of 1 does not fade the snake again.
        wall = limits.limit([FULL_WHITE_SNAKE, FULL_WHITE_SNAKE], [100, 0], 10000)
        self.assertTrue(wall.wall_limited)
        self.assertEqual(wall.legs[0], b"\x01" * 540)

    def test_a_dark_picture_is_limited_by_a_budget_below_its_leds_at_rest_and_unchanged(self):
        dark = bytes(3 * SNAKE)
        found = limits.limit([dark, dark], [179, 180], 359)
        self.assertEqual(found.legs, (dark, dark))
        self.assertEqual(found.limited, (True, False))
        self.assertEqual(found.estimates, (180, 180))
        self.assertTrue(found.wall_limited)
        self.assertFalse(limits.limit([dark, dark], [0, 0], 360).wall_limited)

    def test_the_wall_dims_what_the_snakes_own_budgets_left(self):
        found = limits.limit([FULL_WHITE_SNAKE, FULL_WHITE_SNAKE], [500, 0], 5000)
        left = [limits.fade(FULL_WHITE_SNAKE, 7), FULL_WHITE_SNAKE]
        level = limits.wall_level(left, 5000)
        self.assertLess(level, 255)
        self.assertEqual(found.legs, tuple(limits.fade(leg, level) for leg in left))
        self.assertLessEqual(found.wall_estimate, 5000)
        self.assertEqual(found.limited, (True, False))
        self.assertTrue(found.wall_limited)

    def test_a_snake_the_walls_fade_takes_above_its_budget_is_faded_again(self):
        twos = bytes([2]) * 540
        self.assertEqual(limits.estimate(twos), 257)
        self.assertEqual(limits.estimate(limits.fade(twos, 254)), 296)
        self.assertEqual(limits.estimate(limits.fade(FULL_WHITE_SNAKE, 254)), 10002)
        found = limits.limit([twos, FULL_WHITE_SNAKE], [257, 0], 296 + 10002)
        self.assertTrue(found.wall_limited)
        self.assertEqual(found.legs, (b"\x01" * 540, bytes([253]) * 540))
        self.assertEqual(found.estimates, (218, 10002))
        self.assertEqual(found.limited, (True, False))
        self.assertEqual(found.wall_estimate, 218 + 10002)

    def test_the_order_on_random_pictures(self):
        rng = random.Random(45)
        for number in range(25):
            count = rng.randint(1, 6)
            legs = [picture(rng, rng.choice((1, 18, 60)), brightest=rng.choice((2, 4, 40, 255)), density=rng.choice((0.2, 1.0))) for _ in range(count)]
            budgets = [rng.choice((0, 0, rng.randint(1, limits.estimate(leg) + 2))) for leg in legs]
            wall = rng.choice((0, rng.randint(1, sum(map(limits.estimate, legs)) + 2)))
            with self.subTest(picture=number, budgets=budgets, wall=wall):
                found = limits.limit(legs, budgets, wall)
                own = [limits.level(leg, budget) for leg, budget in zip(legs, budgets)]
                sent = [limits.fade(leg, level) for leg, level in zip(legs, own)]
                within = [budget == 0 or limits.estimate(leg) <= budget for leg, budget in zip(sent, budgets)]
                level = by_definition(sent, wall) if wall else 255
                sent = [limits.fade(leg, level) for leg in sent]
                again = [255] * count
                for i, budget in enumerate(budgets):
                    if level < 255 and budget and within[i] and limits.estimate(sent[i]) > budget:
                        again[i] = by_definition((sent[i],), budget)
                        sent[i] = limits.fade(sent[i], again[i])
                self.assertEqual(found.legs, tuple(sent))
                self.assertEqual(found.estimates, tuple(map(limits.estimate, sent)))
                self.assertEqual(found.limited, tuple(a < 255 or b < 255 for a, b in zip(own, again)))
                self.assertEqual(found.wall_estimate, sum(found.estimates))
                self.assertEqual(found.wall_limited, level < 255)
                for estimate, budget, a, b in zip(found.estimates, budgets, own, again):
                    if budget and estimate > budget:
                        self.assertEqual(min(a, b), 1)

    def test_a_leg_and_a_budget_for_each(self):
        with self.assertRaises(ValueError):
            limits.limit([WHITE, WHITE], [0], 0)


def text(wall=730, legs=(), version=1, **more):
    listed = legs if legs is ... else [list(entry) for entry in legs]
    top = {"version": version, "wall": wall, "legs": listed, **more}
    return json.dumps({name: value for name, value in top.items() if value is not ...}).encode()


class TheFile(unittest.TestCase):
    def malformed(self, data):
        with self.assertRaises(errors.Rejection) as caught:
            limits.loads(data)
        self.assertEqual(caught.exception.reason, errors.LIMITS_MALFORMED)
        return caught.exception.detail

    def test_it_reads_the_wall_and_the_legs_in_the_files_order(self):
        found = limits.loads(text(2000, [(3, 500), (1, 0), (255, 65535)]))
        self.assertEqual((found.wall, found.legs), (2000, ((3, 500), (1, 0), (255, 65535))))
        self.assertEqual((found.of(3), found.of(1), found.of(255), found.of(2)), (500, 0, 65535, 0))
        self.assertEqual(limits.loads(text(0, [])).legs, ())
        self.assertEqual(limits.loads(text(250000)).wall, 250000)
        self.assertEqual(limits.loads(b' \r\n{ "legs" : [ [ 2 , 7 ] ] , "wall" : -0 , "version" : 1 }\n\t').of(2), 7)

    def test_the_writer_writes_one_line_and_leaves_out_the_legs_at_0(self):
        written = limits.dumps(730, [(1, 500), (2, 0), (20, 180)])
        self.assertEqual(written, b'{"version":1,"wall":730,"legs":[[1,500],[20,180]]}\n')
        self.assertEqual(limits.dumps(0, []), b'{"version":1,"wall":0,"legs":[]}\n')
        found = limits.loads(written)
        self.assertEqual((found.wall, found.legs), (730, ((1, 500), (20, 180))))

    def test_the_writer_refuses_what_the_reader_would(self):
        for wall, legs in ((-1, []), (250001, []), (True, []), (0, [(0, 1)]), (0, [(256, 1)]), (0, [(1, 65536)]), (0, [(1, -1)]), (0, [(1, 2), (1, 3)])):
            with self.subTest(wall=wall, legs=legs), self.assertRaises(ValueError):
                limits.dumps(wall, legs)

    def test_every_broken_rule_is_limits_malformed(self):
        cases = {
            "not json": b"{",
            "not utf-8": b'{"version":1,"wall":730,"legs":[]}\xff',
            "a byte-order mark": b"\xef\xbb\xbf" + text(),
            "two values": text() + text(),
            "not an object": b"[1,730,[]]",
            "no version": text(version=...),
            "no wall": text(wall=...),
            "no legs": text(legs=...),
            "an unknown member": text(more=1),
            "a repeated member": b'{"version":1,"wall":730,"wall":730,"legs":[]}',
            "version 2": text(version=2),
            "version 1.0": b'{"version":1.0,"wall":730,"legs":[]}',
            "a wall below 0": text(-1),
            "a wall above 250,000": text(250001),
            "a wall with a fraction": b'{"version":1,"wall":730.0,"legs":[]}',
            "a wall with an exponent": b'{"version":1,"wall":7e2,"legs":[]}',
            "a wall that is true": b'{"version":1,"wall":true,"legs":[]}',
            "a wall that is text": b'{"version":1,"wall":"730","legs":[]}',
            "a wall of many digits": b'{"version":1,"wall":' + b"9" * 40 + b',"legs":[]}',
            "a wall with a leading zero": b'{"version":1,"wall":0730,"legs":[]}',
            "legs that are an object": b'{"version":1,"wall":730,"legs":{"1":500}}',
            "an entry that is an object": b'{"version":1,"wall":730,"legs":[{"leg":1,"budget":500}]}',
            "an entry of one value": text(legs=[(1,)]),
            "an entry of three values": text(legs=[(1, 500, 0)]),
            "an empty entry": text(legs=[()]),
            "leg 0": text(legs=[(0, 500)]),
            "leg 256": text(legs=[(256, 500)]),
            "a budget below 0": text(legs=[(1, -1)]),
            "a budget above 65,535": text(legs=[(1, 65536)]),
            "a leg named twice": text(legs=[(1, 500), (2, 0), (1, 500)]),
            "a leg that is text": b'{"version":1,"wall":730,"legs":[["1",500]]}',
            "null": b"null",
        }
        for name, data in cases.items():
            with self.subTest(name):
                self.assertTrue(self.malformed(data))

    def test_the_detail_says_which_rule(self):
        self.assertIn("leg 1 is named twice", self.malformed(text(legs=[(1, 5), (1, 6)])))
        self.assertIn("above 65535", self.malformed(text(legs=[(4, 65536)])))
        self.assertIn("unknown member", self.malformed(text(more=1)))

    def test_read_names_the_file_and_an_absent_file_is_not_found(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder, limits.NAME)
            with self.assertRaises(errors.Rejection) as caught:
                limits.read(path)
            self.assertEqual(caught.exception.reason, errors.NOT_FOUND)
            path.write_bytes(text(730, [(1, 500)]))
            self.assertEqual(limits.read(path).of(1), 500)
            path.write_bytes(text(version=2))
            with self.assertRaises(errors.Rejection) as caught:
                limits.read(path)
            self.assertEqual(caught.exception.reason, errors.LIMITS_MALFORMED)
            self.assertIn(str(path), caught.exception.detail)


if __name__ == "__main__":
    unittest.main()
