"""The current limits: the core limits the LED data of every refresh that writes the LEDs by
the budgets of `limits.json`, or by the host's default while none are saved, as
`odrig.limits` states it."""

import json
import random
import unittest

from odrig import errors, jsonframes, limits, mapping, odrg

from . import support
from .test_playback import T0, refreshes

TARGET = support.mapping_texts()["legs-20"].encode()
TWO_LEGS = support.mapping_texts()["legs-2"].encode()
WHITE = b"\xff\xff\xff"
UNREADABLE = "limits unreadable"


def picture_file(mapping_text, colour_of, frames=1):
    """An ODRG file of pictures of 20 ms on a mapping's canvas, in which LED `led`, from 0,
    of leg `leg` shows `colour_of(leg, led, frame)`, three bytes."""
    canvas = mapping.loads(mapping_text)
    pictures = []
    for frame in range(frames):
        pixels = bytearray(3 * canvas.width * canvas.height)
        for leg in canvas.legs:
            for led, place in enumerate(support.led_pixels(canvas, leg)):
                pixels[3 * place:3 * place + 3] = colour_of(leg.leg, led, frame)
        pictures.append((20, bytes(pixels)))
    return odrg.encode(jsonframes.Animation(canvas.width, canvas.height, tuple(pictures)))


def show_files(mapping_text, clip, budgets=None, brightness=255):
    """A show of one animation that plays from power-on, with a budgets' file when
    `budgets` is given: `(wall, [(leg, mA), ...])`, or the bytes of the file."""
    files = {
        "mapping.json": mapping_text,
        "show.json": support.show_text([{"id": 1, "file": "clip.odrg"}], brightness, 1),
        "clip.odrg": clip,
    }
    if isinstance(budgets, (bytes, str)):
        files[limits.NAME] = budgets
    elif budgets is not None:
        files[limits.NAME] = limits.dumps(budgets[0], budgets[1])
    return files


def pictures(run):
    """The LED data of each refresh of a session, `{leg: bytes}` in the mapping's order."""
    produced, _ = refreshes([line for line in run.lines if line.startswith(("refresh ", "data ", "idle "))])
    return [legs for _, legs in produced]


def polls(count, start=T0):
    return [f"poll {start + 20 * step}" for step in range(count)]


def limited(picture, budgets, wall):
    """A refresh's LED data, `{leg: bytes}`, limited by the reference: each leg by its budget
    in `budgets`, by its number, and the wall by `wall`."""
    legs = list(picture)
    done = limits.limit([picture[leg] for leg in legs], [budgets.get(leg, 0) for leg in legs], wall)
    return dict(zip(legs, done.legs))


class LimitedTestCase(unittest.TestCase):
    def assert_as_the_reference(self, files, script, options=(), limit_default=0):
        """Runs a script on the core and on the reference player and compares every line.
        Returns the core's pictures."""
        run = support.start(files, script, options)
        expected = support.ReferencePlayer(files, limit_default=limit_default).run(script)
        self.assertEqual(len(run.lines), len(expected))
        for number, (line, wanted) in enumerate(zip(run.lines, expected)):
            if line != wanted:
                self.fail(f"line {number} differs: the core printed {line[:90]}, the reference {wanted[:90]}")
        return pictures(run)

    def assert_limited_as_without(self, files, script, budgets, wall, options=()):
        """Runs a script with the files and with the files without their budgets, and checks
        that each refresh of the first is the second's limited by the reference. Returns the
        pictures of both."""
        with_budgets = pictures(support.start(files, script, options))
        unlimited = pictures(support.start({name: data for name, data in files.items() if name != limits.NAME}, script, options))
        self.assertEqual(len(with_budgets), len(unlimited))
        self.assertGreater(len(with_budgets), 0)
        for number, (picture, plain) in enumerate(zip(with_budgets, unlimited)):
            self.assertEqual(picture, limited(plain, budgets, wall), f"refresh {number}")
        return with_budgets, unlimited


class WorkedCases(LimitedTestCase):
    def test_a_full_white_snake_with_a_budget_of_500_mA_is_held_at_level_7_and_estimated_at_451(self):
        files = show_files(TARGET, picture_file(TARGET, lambda leg, led, frame: WHITE), (0, [(1, 500)]))
        for picture in self.assert_as_the_reference(files, polls(3)):
            self.assertEqual(picture[1], bytes([7]) * 540)
            self.assertEqual(limits.estimate(picture[1]), 451)
            for leg in range(2, 21):
                self.assertEqual(picture[leg], WHITE * 180, leg)

    def test_a_budget_at_or_below_the_leds_at_rest_holds_every_lit_led_at_its_lowest_level(self):
        for budget in (1, 100, 179, 180):
            with self.subTest(budget=budget):
                files = show_files(TWO_LEGS, picture_file(TWO_LEGS, lambda leg, led, frame: WHITE), (0, [(2, budget)]))
                for picture in self.assert_as_the_reference(files, polls(2)):
                    self.assertEqual(picture, {1: WHITE * 180, 2: b"\x01" * 540})

    def test_the_wall_at_730_mA_holds_the_installation_at_its_lowest_level(self):
        clip = support.clip(5, 60, 60, (20, 20))
        files = show_files(TARGET, clip, (730, []))
        shown = self.assert_as_the_reference(files, polls(2))
        for picture in shown:
            lit = b"".join(picture.values())
            self.assertLessEqual(max(lit), 1)
            self.assertGreater(lit.count(1), 1000)

    def test_a_budget_above_what_the_picture_draws_changes_nothing(self):
        clip = picture_file(TWO_LEGS, lambda leg, led, frame: bytes([led % 256, 40, 200]))
        estimate = limits.estimate(bytes([0, 40, 200]) * 180)
        files = show_files(TWO_LEGS, clip, (100000, [(1, 2 * estimate), (2, 65535)]))
        with_budgets, unlimited = self.assert_limited_as_without(files, polls(2), {1: 2 * estimate, 2: 65535}, 100000)
        self.assertEqual(with_budgets, unlimited)


class BothKindsOfBudget(LimitedTestCase):
    def test_the_wall_dims_every_leg_by_one_level_after_the_legs_own_budgets(self):
        files = show_files(TARGET, picture_file(TARGET, lambda leg, led, frame: WHITE), (50000, [(1, 500), (2, 1000)]))
        for picture in self.assert_as_the_reference(files, polls(2)):
            own = [limits.fade(WHITE * 180, limits.level(WHITE * 180, budget)) for budget in (500, 1000)] + [WHITE * 180] * 18
            level = limits.wall_level(own, 50000)
            self.assertLess(level, 255)
            for leg in range(1, 21):
                self.assertEqual(picture[leg], limits.fade(own[leg - 1], level), leg)
            self.assertLessEqual(sum(limits.estimate(data) for data in picture.values()), 50000)

    def test_the_wall_alone_and_a_leg_alone_dim_only_what_they_hold(self):
        clip = support.clip(8, 60, 6, (20, 20, 20))
        for budgets, wall in (({}, 2000), ({2: 300}, 0), ({1: 250, 2: 400}, 600)):
            with self.subTest(budgets=budgets, wall=wall):
                files = show_files(TWO_LEGS, clip, (wall, sorted(budgets.items())))
                with_budgets, unlimited = self.assert_limited_as_without(files, polls(3), budgets, wall)
                self.assertNotEqual(with_budgets, unlimited)
                for picture, plain in zip(with_budgets, unlimited):
                    if wall == 0:
                        self.assertEqual(picture[1], plain[1])


class TheThirdPass(LimitedTestCase):
    def test_a_leg_the_walls_fade_took_above_its_budget_is_faded_again_by_its_own(self):
        # Leg 1 is within its budget of 205 mA, red at 2; the wall's fade at 254 raises
        # every 2 to 3, 218 mA, and leg 1's own budget then holds it at 1.
        colours = {1: bytes([2, 0, 0]), 2: WHITE}
        files = show_files(TWO_LEGS, picture_file(TWO_LEGS, lambda leg, led, frame: colours[leg]), (10250, [(1, 205)]))
        self.assertEqual(limits.estimate(colours[1] * 180), 205)
        self.assertEqual(limits.wall_level([colours[1] * 180, WHITE * 180], 10250), 254)
        self.assertEqual(limits.estimate(limits.fade(colours[1] * 180, 254)), 218)
        for picture in self.assert_as_the_reference(files, polls(2)):
            self.assertEqual(picture, {1: bytes([1, 0, 0]) * 180, 2: bytes([253]) * 540})

    def test_a_leg_its_own_budget_left_above_it_is_not_faded_at_level_1_again(self):
        # Leg 1 is held at level 1 by its budget of 100 mA, at 218 mA; the wall's fade at
        # 144 keeps its bytes of 1, and a second fade at level 1 would make them 0.
        files = show_files(TWO_LEGS, picture_file(TWO_LEGS, lambda leg, led, frame: WHITE), (6000, [(1, 100)]))
        self.assertEqual(limits.wall_level([b"\x01" * 540, WHITE * 180], 6000), 144)
        self.assertEqual(limits.fade(b"\x01" * 540, 1), bytes(540))
        for picture in self.assert_as_the_reference(files, polls(2)):
            self.assertEqual(picture[1], b"\x01" * 540)
            self.assertEqual(limits.estimate(picture[1]), 218)

    def test_a_wall_below_level_129_takes_a_leg_held_at_level_1_to_dark(self):
        files = show_files(TWO_LEGS, picture_file(TWO_LEGS, lambda leg, led, frame: WHITE), (5000, [(1, 100)]))
        self.assertEqual(limits.wall_level([b"\x01" * 540, WHITE * 180], 5000), 119)
        for picture in self.assert_as_the_reference(files, polls(2)):
            self.assertEqual(picture[1], bytes(540))


class RandomPictures(LimitedTestCase):
    def budget(self, rng, data):
        """A budget for bytes: none, one at or below the LEDs at rest, one about the
        estimate, or one above it."""
        leds = len(data) // 3
        estimate = limits.estimate(data)
        return rng.choice([0, 0, rng.randint(1, leds), rng.randint(leds + 1, max(leds + 1, estimate)), rng.randint(estimate, estimate + 200)])

    def test_random_pictures_and_budgets_are_limited_as_the_reference_limits_them(self):
        rng = random.Random(45)
        for case in range(12):
            text = TARGET if case % 3 == 0 else TWO_LEGS
            canvas = mapping.loads(text)
            colours = rng.choice([4, 30, 1000])
            clip = odrg.encode(support.seeded_animation(case, canvas.width, canvas.height, (20, 20, 40), colours=colours))
            brightness = rng.choice([255, 255, 128, 37, 1])
            first = support.ReferencePlayer(show_files(text, clip, brightness=brightness)).poll(T0)
            budgets = {leg: self.budget(rng, data) for leg, data in first if rng.random() < 0.6}
            total = sum(limits.estimate(data) for _, data in first)
            wall = rng.choice([0, rng.randint(1, total), rng.randint(total // 2, total + 100)])
            with self.subTest(case=case, budgets=budgets, wall=wall, brightness=brightness):
                files = show_files(text, clip, (wall, sorted(budgets.items())), brightness)
                script = polls(4)
                self.assert_as_the_reference(files, script)
                self.assert_limited_as_without(files, script, budgets, wall)


class DarkAndKeptPictures(LimitedTestCase):
    def test_a_dark_picture_stays_dark_under_every_budget(self):
        clip = support.clip(2, 60, 6, (20, 20))
        dark = {1: bytes(540), 2: bytes(540)}
        for budgets in ((0, [(1, 1), (2, 179)]), (1, []), (360, [(2, 100)])):
            for brightness in (0, 255):
                with self.subTest(budgets=budgets, brightness=brightness):
                    files = show_files(TWO_LEGS, clip, budgets, brightness)
                    script = polls(2) + [support.line(T0 + 40, "off")] + polls(2, T0 + 40)
                    shown = self.assert_as_the_reference(files, script)
                    self.assertEqual(shown[2:], [dark, dark])
                    self.assertEqual(shown[0] == dark, brightness == 0)

    def test_a_refresh_that_keeps_the_picture_before_keeps_it_as_it_was_limited(self):
        # Frames of 1 ms, then a pause: the player catches up over several refreshes, which
        # keep the picture before. Held at the lowest level, the picture would go dark if it
        # were limited a second time.
        animation = support.seeded_animation(31, 16, 16, (1,) * 2000, colours=1000)
        files = {
            "mapping.json": support.one_leg_mapping(16, 16),
            "show.json": support.show_text([{"id": 1, "file": "clip.odrg"}]),
            "clip.odrg": odrg.encode(animation, compressed=False),
            limits.NAME: limits.dumps(0, [(1, 100)]),
        }
        script = polls(10) + polls(40, start=T0 + 11000)
        printed, _ = self.assert_limited_as_without(files, script, {1: 100}, 0)
        before = printed[9]
        self.assertTrue(any(before[1]))
        self.assertLessEqual(max(before[1]), 1)
        kept = [number for number in range(10, 50) if printed[number] == before]
        self.assertGreaterEqual(len(kept), 3)
        self.assertEqual(kept, list(range(10, 10 + len(kept))))


class TheMappingTests(LimitedTestCase):
    def test_the_diagonal_and_the_snake_tests_are_limited_like_any_picture(self):
        files = support.demo_show()
        files[limits.NAME] = limits.dumps(3700, [(3, 181), (7, 250)])
        script = [support.line(T0, "mapping test on")] + polls(3) + [support.line(T0 + 60, "mapping test snake 3")] + polls(30, T0 + 60)
        script += [support.line(T0 + 700, "mapping test snake 7")] + polls(3, T0 + 700)
        with_budgets, unlimited = self.assert_limited_as_without(files, script, {3: 181, 7: 250}, 3700)
        self.assertNotEqual(with_budgets[:3], unlimited[:3])
        self.assertTrue(any(picture[3] != plain[3] and any(picture[3]) for picture, plain in zip(with_budgets[3:33], unlimited[3:33])))
        self.assertTrue(any(picture[7] != plain[7] and any(picture[7]) for picture, plain in zip(with_budgets[33:], unlimited[33:])))


class TheDefaults(LimitedTestCase):
    @classmethod
    def setUpClass(cls):
        cls.clip = picture_file(TARGET, lambda leg, led, frame: WHITE)

    def test_without_budgets_the_test_host_limits_nothing(self):
        for options in ((), ("--limit-default", "0")):
            with self.subTest(options=options):
                for picture in self.assert_as_the_reference(show_files(TARGET, self.clip), polls(2), options):
                    self.assertEqual(set(picture.values()), {WHITE * 180})

    def test_while_no_budgets_are_saved_the_hosts_default_is_the_walls_budget(self):
        for default in (730, 1, 3600, 100000, 250000):
            with self.subTest(default=default):
                files = show_files(TARGET, self.clip)
                shown = self.assert_as_the_reference(files, polls(2), ("--limit-default", str(default)), limit_default=default)
                for picture in shown:
                    if default <= 3600:
                        self.assertEqual(set(picture.values()), {b"\x01" * 540})
                    elif default >= 201600:
                        self.assertEqual(set(picture.values()), {WHITE * 180})
                    else:
                        self.assertLessEqual(sum(limits.estimate(data) for data in picture.values()), default)

    def test_saved_budgets_replace_the_default_and_an_unreadable_file_does_not(self):
        options = ("--limit-default", "730")
        no_wall = self.assert_as_the_reference(show_files(TARGET, self.clip, (0, [(1, 500)])), polls(1), options, limit_default=730)
        self.assertEqual(no_wall[0][1], bytes([7]) * 540)
        self.assertEqual({no_wall[0][leg] for leg in range(2, 21)}, {WHITE * 180})
        files = show_files(TARGET, self.clip, b'{"version":1,"wall":0}')
        run = support.start(files, polls(1), options)
        self.assertEqual(run.logs, (UNREADABLE,))
        self.assertEqual(set(pictures(run)[0].values()), {b"\x01" * 540})

    def test_a_host_default_out_of_range_is_a_usage_error(self):
        with support.installed(show_files(TARGET, self.clip)) as folder:
            for value in ("250001", "-1", "x", "", "1234567890"):
                result = support.host("session", folder, "--limit-default", value)
                self.assertEqual(result.status, 64, value)


# Texts of a budgets' file on the two-leg mapping, each read by the core and by the library.
FILES = [
    b'{"version":1,"wall":0,"legs":[[1,500]]}',
    b'{"version":1,"wall":0,"legs":[[1,500]]}\n',
    b' \r\n\t{ "legs" : [ [ 1 , 500 ] ] , "wall" : 0 , "version" : 1 } \n',
    b'{"legs":[[1,500]],"wall":0,"version":1}',
    b'{"version":1,"wall":0,"legs":[[2,0],[1,500]]}',
    b'{"version":1,"wall":0,"legs":[[1,500],[7,99],[255,65535]]}',
    b'{"version":1,"wall":250000,"legs":[[1,500]]}',
    b'{"version":1,"w\\u0061ll":0,"legs":[[1,500]]}',
    b'{"version":1,"wall":-0,"legs":[[1,500]]}',
    b'{"version":1,"wall":0,"legs":[]}',
    b'{"version":1,"wall":0,"legs":[[1,500]]',
    b'{"version":1,"wall":0,"legs":[[1,500]]}}',
    b'{"version":1,"wall":0,"legs":[[1,500]]} x',
    b'{"version":1,"wall":0,"legs":[[1,500],]}',
    b'{"version":1,"wall":0}',
    b'{"version":1,"legs":[[1,500]]}',
    b'{"wall":0,"legs":[[1,500]]}',
    b'{"version":1,"wall":0,"legs":[[1,500]],"pins":[]}',
    b'{"version":1,"wall":0,"wall":0,"legs":[[1,500]]}',
    b'{"version":1,"version":1,"wall":0,"legs":[[1,500]]}',
    b'{"version":1,"wall":0,"legs":[[1,500]],"legs":[]}',
    b'{"version":2,"wall":0,"legs":[[1,500]]}',
    b'{"version":"1","wall":0,"legs":[[1,500]]}',
    b'{"version":1.0,"wall":0,"legs":[[1,500]]}',
    b'{"version":1,"wall":250001,"legs":[[1,500]]}',
    b'{"version":1,"wall":-1,"legs":[[1,500]]}',
    b'{"version":1,"wall":1e3,"legs":[[1,500]]}',
    b'{"version":1,"wall":99999999999999999999999,"legs":[[1,500]]}',
    b'{"version":1,"wall":true,"legs":[[1,500]]}',
    b'{"version":1,"wall":null,"legs":[[1,500]]}',
    b'{"version":1,"wall":0,"legs":[[0,500]]}',
    b'{"version":1,"wall":0,"legs":[[256,500]]}',
    b'{"version":1,"wall":0,"legs":[[-0,500]]}',
    b'{"version":1,"wall":0,"legs":[[1,65536]]}',
    b'{"version":1,"wall":0,"legs":[[1,-5]]}',
    b'{"version":1,"wall":0,"legs":[[1,500],[1,400]]}',
    b'{"version":1,"wall":0,"legs":[[9,1],[9,1]]}',
    b'{"version":1,"wall":0,"legs":[[1]]}',
    b'{"version":1,"wall":0,"legs":[[1,500,7]]}',
    b'{"version":1,"wall":0,"legs":[[]]}',
    b'{"version":1,"wall":0,"legs":[1,500]}',
    b'{"version":1,"wall":0,"legs":[{"leg":1,"mA":500}]}',
    b'{"version":1,"wall":0,"legs":{}}',
    b'{"version":1,"wall":0,"legs":[[1,"500"]]}',
    b'{"version":1,"wall":0,"legs":[[1,5.0]]}',
    b'{"version":1,"wall":0,"legs":[[1,500]],}',
    b'{"version":1,"wall":0,"legs":[[1,500]]}\x00',
    b'\xef\xbb\xbf{"version":1,"wall":0,"legs":[[1,500]]}',
    b'{"version":1,"wall":0,"legs":[[1,500]],"\xc3\xa9":1}',
    b'{"version":1,"wall":0,"legs":[[1,500]],"longer than a name":1}',
    b'[1,0,[]]',
    b'null',
    b'',
    b'{}',
]


class TheFile(LimitedTestCase):
    def test_the_core_reads_the_file_as_strictly_as_the_library(self):
        clip = picture_file(TWO_LEGS, lambda leg, led, frame: WHITE)
        file_sets = [show_files(TWO_LEGS, clip, text) for text in FILES]
        runs = support.start_each(file_sets, polls(1), ["--limit-default", "1000"])
        verdicts = []
        for text, run in zip(FILES, runs):
            try:
                read = limits.loads(text)
            except errors.Rejection as refusal:
                self.assertEqual(refusal.reason, errors.LIMITS_MALFORMED, text)
                read = None
            verdicts.append(read is not None)
            with self.subTest(text=text):
                self.assertIsNone(run.error)
                if read is None:
                    self.assertEqual(run.logs, (UNREADABLE,))
                    # The defaults: no leg's budget, and the wall's the host's.
                    expected = limited({1: WHITE * 180, 2: WHITE * 180}, {}, 1000)
                else:
                    self.assertEqual(run.logs, ())
                    expected = limited({1: WHITE * 180, 2: WHITE * 180}, dict(read.legs), read.wall)
                self.assertEqual(pictures(run)[0], expected)
        self.assertEqual(verdicts.count(True), 10)

    def test_an_unreadable_file_is_said_once_in_the_log_at_the_start(self):
        files = show_files(TWO_LEGS, support.clip(3, 60, 6), b'{"version":1}')
        run = support.start(files, polls(20) + [support.line(T0 + 400, "status")])
        self.assertEqual(run.logs, (UNREADABLE,))
        self.assertFalse(any(line.startswith("log ") for line in run.lines))
        self.assertIsNone(json.loads(run.lines[-1][len("reply "):])["error"])
        # Before the reason of a mapping that cannot be used, and before a file's fault.
        for name, reason in (("mapping.json", "mapping-missing"), ("show.json", "show-missing"), ("clip.odrg", "file clip.odrg unavailable: file-missing")):
            without = {key: data for key, data in files.items() if key != name}
            run = support.start(without)
            self.assertEqual(run.logs, (UNREADABLE, reason))
            self.assertEqual(list(run.logs), support.ReferencePlayer(without).start_logs)

    def test_a_file_the_host_cannot_read_is_unreadable(self):
        files = show_files(TWO_LEGS, picture_file(TWO_LEGS, lambda leg, led, frame: WHITE), (0, [(1, 500)]))
        for offset in ("0", "12", "30"):
            run = support.start(files, polls(1), ["--read-fails", limits.NAME, offset])
            self.assertEqual(run.logs, (UNREADABLE,), offset)
            self.assertEqual(pictures(run)[0], {1: WHITE * 180, 2: WHITE * 180}, offset)

    def test_a_leg_the_mapping_lacks_is_passed_over(self):
        files = show_files(TWO_LEGS, picture_file(TWO_LEGS, lambda leg, led, frame: WHITE), (0, [(20, 1), (2, 500), (3, 1)]))
        picture = self.assert_as_the_reference(files, polls(1))[0]
        self.assertEqual(picture, {1: WHITE * 180, 2: bytes([7]) * 540})

    def test_the_start_opens_the_file_once_right_after_the_mapping(self):
        files = show_files(TWO_LEGS, support.clip(3, 60, 6), (0, [(1, 500)]))
        run = support.start(files, options=["--trace-files", "--trace-reads"])
        names = [name for name, _ in run.opened if not name.startswith("catalog")]
        self.assertEqual(names[:4], ["mapping.json", "mapping.json", limits.NAME, "show.json"])
        self.assertEqual(run.opened.count((limits.NAME, 1)), 1)
        self.assertIn((limits.NAME, len(files[limits.NAME])), run.taken)
        without = support.start({name: data for name, data in files.items() if name != "mapping.json"}, options=["--trace-files"])
        self.assertEqual(without.opened, (("catalog.do", 0), ("mapping.json", 0), (limits.NAME, 1)))

    def test_budgets_need_no_storage_that_can_be_changed_and_no_block_of_memory(self):
        clip = picture_file(TWO_LEGS, lambda leg, led, frame: WHITE)
        files = show_files(TWO_LEGS, clip, (0, [(1, 500)]))
        for options in ((), ("--no-storage",), ("--only-space",)):
            run = support.start(files, polls(1), options)
            self.assertEqual(pictures(run)[0], {1: bytes([7]) * 540, 2: WHITE * 180}, options)
            self.assertEqual(run.memory, support.start(show_files(TWO_LEGS, clip), (), options).memory)


if __name__ == "__main__":
    unittest.main()
