"""The current limits: the core limits the LED data of every refresh that writes the LEDs by
the budgets of `limits.json`, or by the host's default while none are saved, as
`odrig.limits` states it."""

import json
import random
import unittest
import zlib

from odrig import errors, jsonframes, limits, mapping, odrg

from . import support
from .test_catalog_start import SHOW
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


# The pins of the target file, in snake order, and their revision.
PINS = list(range(1, 19)) + [21, 47]
OK = {"ok": True}
POWER_CUT = 75


def refused(code):
    return {"ok": False, "error": code}


def asked(time, *commands):
    """A refresh at this time after power-on, and these command lines then."""
    return [f"poll {T0 + time}", *(support.line(T0 + time, command) for command in commands)]


def replies(run):
    return [json.loads(line[len("reply "):]) for line in run.lines if line.startswith("reply ")]


def stored(run):
    """The storage calls a session made after its start, as `--trace-store` prints them."""
    return [line[len("store "):] for line in run.lines if line.startswith("store ")]


def as_bytes(files):
    """Installed files, each as bytes."""
    return {name: data if isinstance(data, bytes) else data.encode("utf-8") for name, data in files.items()}


def saving(written):
    """The storage calls of a save of the budgets whose file is these bytes."""
    return ["write_open limits.part 1", f"write {len(written)} 1", "write_close 1", "rename limits.part limits.json 1"]


def many_legs(count):
    """A mapping of `count` legs, each one row of two LEDs, leg n on pin n."""
    legs = [{"leg": number, "pin": number, "first_led": "right", "rows": [number]} for number in range(1, count + 1)]
    return json.dumps({"version": 1, "width": 2, "legs": legs})


def expected_reply(picture, budgets, wall, saved, start=0):
    """The reply of `limits <start>` after a refresh whose LED data before its limiting was
    `picture`, `{leg: bytes}` in the mapping's order, with every leg in one reply."""
    legs = list(picture)
    done = limits.limit([picture[leg] for leg in legs], [budgets.get(leg, 0) for leg in legs], wall)
    entries = [[leg, len(picture[leg]) // 3, budgets.get(leg, 0), estimate, int(dimmed)] for leg, estimate, dimmed in zip(legs, done.estimates, done.limited)]
    leds = sum(len(data) // 3 for data in picture.values())
    return {"ok": True, "saved": saved, "wall": [leds, wall, done.wall_estimate, int(done.wall_limited)], "legs": entries[start:], "next": None}


class TheReply(unittest.TestCase):
    def test_it_gives_the_budgets_and_the_estimates_of_the_latest_refresh_that_wrote_the_leds(self):
        clip = support.clip(5, 60, 60, (20, 20, 20))
        budgets = {1: 500, 3: 0, 7: 65535, 20: 180, 11: 2000}
        files = show_files(TARGET, clip, (50000, sorted(budgets.items())))
        script = asked(0, "limits") + asked(20, "limits", "limits 0", "limits 18") + asked(40, "limits 19", "limits 20", "limits 65535")
        run = support.start(files, script)
        plain = pictures(support.start(show_files(TARGET, clip), script))
        answers = replies(run)
        self.assertEqual(answers[0], expected_reply(plain[0], budgets, 50000, True))
        self.assertEqual(answers[1:3], [expected_reply(plain[1], budgets, 50000, True)] * 2)
        self.assertEqual(answers[3], expected_reply(plain[1], budgets, 50000, True, 18))
        self.assertEqual(answers[4], expected_reply(plain[2], budgets, 50000, True, 19))
        self.assertEqual(answers[5:], [expected_reply(plain[2], budgets, 50000, True, 20)] * 2)
        self.assertTrue(answers[0]["wall"][3])
        self.assertEqual((answers[0]["legs"][0][4], answers[0]["legs"][19][4]), (1, 1))
        # The estimates are those of the bytes sent.
        for answer, sent in zip((answers[0], answers[1], answers[4]), pictures(run)):
            shown = {entry[0]: entry[3] for entry in answer["legs"]}
            self.assertEqual(shown, {leg: limits.estimate(data) for leg, data in sent.items() if leg in shown})

    def test_before_any_budget_is_saved_it_gives_the_defaults(self):
        files = show_files(TWO_LEGS, picture_file(TWO_LEGS, lambda leg, led, frame: WHITE))
        for options, default in (((), 0), (("--limit-default", "730"), 730), (("--limit-default", "250000"), 250000)):
            with self.subTest(options=options):
                run = support.start(files, asked(0, "limits"), options)
                plain = {1: WHITE * 180, 2: WHITE * 180}
                self.assertEqual(replies(run), [expected_reply(plain, {}, default, False)])
        # Before the first refresh the LED data is dark: every LED at rest.
        self.assertEqual(replies(support.start(files, [support.line(T0, "limits")]))[0]["legs"], [[1, 180, 0, 180, 0], [2, 180, 0, 180, 0]])

    def test_the_legs_are_in_the_order_of_the_mapping_file(self):
        text = support.mapping_texts()["another-order"]
        canvas = mapping.loads(text.encode())
        files = show_files(text, support.clip(4, canvas.width, canvas.height), (0, [(2, 3)]))
        answer = replies(support.start(files, asked(0, "limits")))[0]
        self.assertEqual([entry[:3] for entry in answer["legs"]], [[7, 8, 0], [2, 12, 3]])

    def test_without_a_usable_mapping_it_gives_the_wall_alone(self):
        clip = support.clip(4, 60, 6)
        for budgets, options, saved, wall in ((None, (), False, 0), (None, ("--limit-default", "730"), False, 730), ((900, [(1, 5)]), (), True, 900)):
            for broken in (None, b"{"):
                with self.subTest(budgets=budgets, options=options, broken=broken):
                    files = show_files(TWO_LEGS, clip, budgets)
                    if broken is None:
                        del files["mapping.json"]
                    else:
                        files["mapping.json"] = broken
                    run = support.start(files, asked(0, "limits"), options)
                    self.assertIsNotNone(run.error)
                    self.assertEqual(replies(run), [{"ok": True, "saved": saved, "wall": [0, wall, 0, 0], "legs": [], "next": None}])

    def test_it_answers_while_the_show_is_invalid_and_refuses_only_a_position_that_is_no_number(self):
        files = show_files(TWO_LEGS, support.clip(4, 60, 6), (1000, [(2, 400)]))
        del files["show.json"]
        lines = ["limits", "limits 1", "limits x", "limits 65536", "limits -1", "limits +1", "limits 1 2", "limits ", "limits  ", "limits 1.0", "Limits", "limits\t"]
        run = support.start(files, asked(0, *lines))
        answers = replies(run)
        self.assertEqual(answers[0], {"ok": True, "saved": True, "wall": [360, 1000, 360, 0], "legs": [[1, 180, 0, 180, 0], [2, 180, 400, 180, 0]], "next": None})
        self.assertEqual(answers[1]["legs"], [[2, 180, 400, 180, 0]])
        self.assertEqual(answers[2:], [refused("bad-argument")] * 8 + [refused("unknown-command")] * 2)

    def test_a_long_mapping_is_given_in_parts_each_as_full_as_one_reply_holds(self):
        text = many_legs(255)
        budgets = [(leg, 65535 - leg) for leg in range(1, 256)]
        files = show_files(text, support.clip(6, 2, 255), (250000, budgets))
        parts = []
        position = 0
        lines = []
        while position is not None:
            run = support.start(files, asked(0, f"limits {position}"))
            (line,) = [line[len("reply "):] for line in run.lines if line.startswith("reply ")]
            lines.append(line)
            parts.append(json.loads(line))
            position = parts[-1]["next"]
        self.assertGreater(len(parts), 3)
        self.assertEqual([entry[:3] for part in parts for entry in part["legs"]], [[leg, 2, budget] for leg, budget in budgets])
        starts = [0]
        for part in parts:
            starts.append(starts[-1] + len(part["legs"]))
        self.assertEqual([part["next"] for part in parts], starts[1:-1] + [None])
        for line, part in zip(lines, parts):
            self.assertLessEqual(len(line) + 1, 1024)
            if part["next"] is not None:
                # The next leg did not fit: its entry and room for a position of five digits.
                entry = json.dumps(parts[parts.index(part) + 1]["legs"][0], separators=(",", ":"))
                self.assertGreater(len(line) + 1 - len(str(part["next"])) + 5 + 1 + len(entry), 1024)
        self.assertEqual(replies(support.start(files, asked(0, "limits 254", "limits 255", "limits 65535"))),
                         [dict(parts[-1], legs=parts[-1]["legs"][-1:]), dict(parts[-1], legs=[]), dict(parts[-1], legs=[])])

    def test_the_target_with_every_figure_at_its_longest_is_one_reply(self):
        files = show_files(TARGET, picture_file(TARGET, lambda leg, led, frame: WHITE), (250000, [(leg, 65535) for leg in range(1, 21)]))
        run = support.start(files, asked(0, "limits"))
        (line,) = [line[len("reply "):] for line in run.lines if line.startswith("reply ")]
        answer = json.loads(line)
        self.assertEqual(answer["wall"], [3600, 250000, 201600, 0])
        self.assertEqual(answer["legs"], [[leg, 180, 65535, 10080, 0] for leg in range(1, 21)])
        self.assertIsNone(answer["next"])
        self.assertLess(len(line) + 1, 600)


class TheSaves(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.clip = picture_file(TWO_LEGS, lambda leg, led, frame: WHITE)

    def test_while_the_defaults_are_in_force_every_set_writes_the_whole_file_and_then_the_same_value_writes_nothing(self):
        files = show_files(TWO_LEGS, self.clip)
        for options, default in (((), 0), (("--limit-default", "730"), 730)):
            for command, wall, legs in (("limits snake 2 500", default, [(2, 500)]), ("limits wall 730", 730, []), (f"limits wall {default}", default, []),
                                        ("limits snake 1 0", default, []), ("limits wall 0", 0, []), ("limits wall 250000", 250000, []),
                                        ("limits snake 1 65535", default, [(1, 65535)])):
                with self.subTest(options=options, command=command):
                    run, left = support.start_and_keep(files, asked(0, command, command, "limits"), [*options, "--trace-store"])
                    written = limits.dumps(wall, legs)
                    self.assertEqual(replies(run)[:2], [OK, OK])
                    self.assertEqual(left[limits.NAME], written)
                    self.assertEqual(stored(run), saving(written))
                    self.assertEqual(replies(run)[2]["saved"], True)
                    self.assertEqual(replies(run)[2]["wall"][1], wall)
                    self.assertEqual([entry[2] for entry in replies(run)[2]["legs"]], [dict(legs).get(leg, 0) for leg in (1, 2)])
                    self.assertNotIn("limits.part", left)
                    # Kept across a restart.
                    again = replies(support.start(left, asked(0, "limits"), options))[0]
                    self.assertEqual((again["saved"], again["wall"][1]), (True, wall))
                    self.assertEqual([entry[:3] for entry in again["legs"]], [entry[:3] for entry in replies(run)[2]["legs"]])

    def test_once_budgets_are_saved_a_set_writes_the_changed_file_and_the_same_value_nothing(self):
        files = show_files(TWO_LEGS, self.clip, (2000, [(1, 500)]))
        script = asked(0, "limits wall 2000", "limits snake 1 500", "limits snake 2 0", "limits snake 2 300", "limits wall 1500", "limits snake 1 0", "limits snake 1 0", "limits")
        run, left = support.start_and_keep(files, script, ["--trace-store"])
        self.assertEqual(replies(run)[:7], [OK] * 7)
        steps = [limits.dumps(2000, [(1, 500), (2, 300)]), limits.dumps(1500, [(1, 500), (2, 300)]), limits.dumps(1500, [(2, 300)])]
        self.assertEqual(stored(run), [call for written in steps for call in saving(written)])
        self.assertEqual(left[limits.NAME], steps[-1])
        self.assertEqual([entry[2] for entry in replies(run)[7]["legs"]], [0, 300])

    def test_a_set_takes_effect_from_the_next_refresh_that_writes_the_leds(self):
        files = show_files(TWO_LEGS, self.clip)
        script = asked(0, "limits snake 1 500", "limits") + asked(20, "limits", "limits wall 400", "limits default") + asked(40, "limits")
        run = support.start(files, script)
        shown = pictures(run)
        self.assertEqual(shown, [{1: WHITE * 180, 2: WHITE * 180}, {1: bytes([7]) * 540, 2: WHITE * 180}, {1: WHITE * 180, 2: WHITE * 180}])
        answers = replies(run)
        self.assertEqual(answers[1]["legs"], [[1, 180, 500, 10080, 0], [2, 180, 0, 10080, 0]])
        self.assertEqual(answers[2]["legs"], [[1, 180, 500, 451, 1], [2, 180, 0, 10080, 0]])
        self.assertEqual(answers[5], {"ok": True, "saved": False, "wall": [360, 0, 20160, 0], "legs": [[1, 180, 0, 10080, 0], [2, 180, 0, 10080, 0]], "next": None})

    def test_the_budgets_of_legs_the_mapping_lacks_are_copied_from_the_old_file(self):
        old = b'{"version":1,"wall":900,"legs":[[25,7],[2,40],[200,65535],[30,0],[1,100]]}'
        files = show_files(TWO_LEGS, self.clip, old)
        run, left = support.start_and_keep(files, asked(0, "limits snake 2 300", "limits wall 1000", "limits"))
        self.assertEqual(replies(run)[:2], [OK, OK])
        self.assertEqual(left[limits.NAME], limits.dumps(1000, [(1, 100), (2, 300), (25, 7), (200, 65535)]))
        self.assertEqual([entry[2] for entry in replies(run)[2]["legs"]], [100, 300])
        # The other mapping finds its legs' budgets.
        other = dict(left, **{"mapping.json": many_legs(30), "clip.odrg": support.clip(3, 2, 30)})
        answer = replies(support.start(other, asked(0, "limits")))[0]
        self.assertEqual({entry[0]: entry[2] for entry in answer["legs"] if entry[2]}, {1: 100, 2: 300, 25: 7})

    def test_an_old_file_that_cannot_be_read_now_is_a_storage_error_and_changes_nothing(self):
        old = limits.dumps(900, [(25, 7), (1, 100)])
        files = show_files(TWO_LEGS, self.clip, old)
        for offset in ("0", "10", str(len(old) - 2)):
            with self.subTest(offset=offset):
                run, left = support.start_and_keep(files, asked(0, "limits snake 2 300", "limits") + asked(20, "limits"), ["--command-read-fails", limits.NAME, offset])
                self.assertEqual(replies(run)[0], refused("storage-error"))
                self.assertEqual(left[limits.NAME], old)
                self.assertNotIn("limits.part", left)
                self.assertEqual([entry[2] for entry in replies(run)[2]["legs"]], [100, 0])

    def test_an_unreadable_file_is_replaced_whole_at_the_next_save(self):
        files = show_files(TWO_LEGS, self.clip, b'{"version":1,"wall":5,"legs":[[25,7]],"x":1}')
        run, left = support.start_and_keep(files, asked(0, "limits", "limits snake 1 5", "limits"), ["--limit-default", "730"])
        self.assertEqual(run.logs, (UNREADABLE,))
        self.assertEqual(replies(run)[0]["saved"], False)
        self.assertEqual(replies(run)[1], OK)
        self.assertEqual(left[limits.NAME], limits.dumps(730, [(1, 5)]))
        self.assertEqual(replies(run)[2]["saved"], True)

    def test_a_host_failure_at_every_call_of_a_save_leaves_the_budgets_as_they_were(self):
        for budgets in (None, (900, [(25, 7), (2, 40)])):
            files = show_files(TWO_LEGS, self.clip, budgets)
            before = replies(support.start(files, asked(0, "limits")))[0]
            for at in range(3, 7):
                with self.subTest(budgets=budgets, at=at):
                    run, left = support.start_and_keep(files, asked(0, "limits snake 1 300", "limits"), ["--store-fails-at", str(at)])
                    self.assertEqual(replies(run), [refused("storage-error"), before])
                    self.assertEqual(left, as_bytes(files))

    def test_a_power_cut_at_every_step_of_a_save_leaves_the_old_budgets(self):
        for budgets in (None, (900, [(25, 7), (2, 40)])):
            files = show_files(TWO_LEGS, self.clip, budgets)
            command = asked(0, "limits snake 1 300")
            observed, after = support.start_and_keep(files, command, ["--trace-store"])
            calls = len(stored(observed))
            self.assertEqual(calls, 4)
            self.assertEqual([entry[2] for entry in replies(support.start_and_keep(after, asked(0, "limits"))[0])[0]["legs"]], [300, 40 if budgets else 0])
            # The rename is the last call: a cut at any of them leaves the old budgets.
            for at in range(3, 3 + calls):
                for keeps in (0, 1):
                    with self.subTest(budgets=budgets, at=at, keeps=keeps):
                        _, left = support.start_and_keep(files, command, ["--cut-at", str(at), "--cut-keeps", str(keeps)], status=POWER_CUT)
                        recovered, settled = support.start_and_keep(left, asked(0, "limits"))
                        self.assertEqual(recovered.logs, ())
                        self.assertNotIn("limits.part", settled)
                        self.assertEqual(settled.get(limits.NAME), files.get(limits.NAME))
                        legs = [entry[2] for entry in replies(recovered)[0]["legs"]]
                        self.assertEqual(legs, [0, 40 if budgets else 0])

    def test_a_part_file_left_by_a_cut_is_removed_at_the_start(self):
        files = show_files(TWO_LEGS, self.clip, (900, [(1, 500)]))
        for part in (b"", b'{"version":1,"wa'):
            run, left = support.start_and_keep(dict(files, **{"limits.part": part}), asked(0, "limits"), ["--trace-store"])
            self.assertIn("remove limits.part 1", run.stored)
            self.assertNotIn("limits.part", left)
            self.assertEqual(left[limits.NAME], files[limits.NAME])
            self.assertEqual(replies(run)[0]["legs"][0][2], 500)
        # Without one the start removes what it removed before.
        run = support.start(files, (), ["--trace-store"])
        self.assertFalse(any("limits" in call for call in run.stored))


class TheDefaultCommand(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.clip = picture_file(TWO_LEGS, lambda leg, led, frame: WHITE)

    def test_it_removes_the_file_and_puts_the_defaults_in_force(self):
        for budgets in ((2000, [(1, 500)]), b'{"version":1}'):
            with self.subTest(budgets=budgets):
                files = show_files(TWO_LEGS, self.clip, budgets)
                script = asked(0, "limits default", "limits default") + asked(20, "limits")
                run, left = support.start_and_keep(files, script, ["--trace-store", "--limit-default", "730"])
                self.assertEqual(replies(run)[:2], [OK, OK])
                self.assertEqual(stored(run), ["remove limits.json 1"])
                self.assertNotIn(limits.NAME, left)
                self.assertEqual(replies(run)[2], expected_reply({1: WHITE * 180, 2: WHITE * 180}, {}, 730, False))
                self.assertEqual(pictures(run)[1], limited({1: WHITE * 180, 2: WHITE * 180}, {}, 730))
                self.assertLess(max(pictures(run)[1][1]), 255)

    def test_without_a_file_it_writes_nothing(self):
        for options in ((), ("--no-storage",), ("--only-space",)):
            run = support.start(show_files(TWO_LEGS, self.clip), asked(0, "limits default", "limits"), [*options, "--trace-store"])
            self.assertEqual(replies(run)[0], OK, options)
            self.assertEqual(stored(run), [], options)

    def test_a_file_that_cannot_be_removed_is_a_storage_error_and_stays_in_force(self):
        files = show_files(TWO_LEGS, self.clip, (2000, [(1, 500)]))
        for options in (("--store-fails-at", "3"), ("--no-storage",), ("--only-space",)):
            with self.subTest(options=options):
                run, left = support.start_and_keep(files, asked(0, "limits default", "limits"), options)
                self.assertEqual(replies(run)[0], refused("storage-error"))
                self.assertEqual(left[limits.NAME], files[limits.NAME])
                self.assertEqual((replies(run)[1]["saved"], replies(run)[1]["wall"][1]), (True, 2000))


class TheRefusals(unittest.TestCase):
    SETS = ("limits wall 5", "limits snake 1 5", "limits default")
    BAD = ("limits wall", "limits wall x", "limits wall 250001", "limits wall -1", "limits wall 1 2", "limits wall 5x", "limits wall 1e3", "limits wall ", "limits wall  5",
           "limits snake 1", "limits snake 0 5", "limits snake 256 5", "limits snake 1 65536", "limits snake x 5", "limits snake 1 5 6", "limits snake 1 -5", "limits snake  1 5",
           "limits default 1", "limits defaults", "limits Wall 5", "limits WALL 5", "limits snakes 1 5", "limits  wall 5", "limits wall 99999999999999999999")

    def test_words_not_in_a_form_are_a_bad_argument_before_anything_else(self):
        clip = support.clip(5, 60, 6, (20,) * 100)
        sound = show_files(TWO_LEGS, clip)
        invalid = dict(sound)
        del invalid["show.json"]
        for files, script, check_first in ((sound, asked(0, *self.BAD), True), (invalid, asked(0, *self.BAD), True), (sound, asked(0, *self.BAD), False),
                                           (SHOW, asked(0, "catalog rebuild internal", *self.BAD), True),
                                           (sound, asked(0, support.upload_lines(9, "nine.odrg", clip)[0], *self.BAD), True)):
            run, left = support.start_and_keep(files, script, ["--trace-store"], check_first=check_first)
            answers = replies(run)[-len(self.BAD):]
            self.assertEqual(answers, [refused("bad-argument")] * len(self.BAD))
            self.assertFalse(any("limits" in call for call in stored(run)))
            self.assertNotIn(limits.NAME, left)

    def test_a_rebuild_makes_them_busy(self):
        run, left = support.start_and_keep(SHOW, asked(0, "catalog rebuild internal", *self.SETS, "limits", "limits snake 99 5"))
        self.assertEqual(replies(run)[1:4], [refused("busy")] * 3)
        self.assertTrue(replies(run)[4]["ok"])
        self.assertEqual(replies(run)[5], refused("busy"))
        self.assertNotIn(limits.NAME, left)

    def test_an_invalid_show_comes_before_a_leg_the_mapping_lacks(self):
        files = show_files(TWO_LEGS, support.clip(5, 60, 6), (900, [(1, 5)]))
        for broken in ("show.json", "mapping.json"):
            invalid = {name: data for name, data in files.items() if name != broken}
            run, left = support.start_and_keep(invalid, asked(0, *self.SETS, "limits snake 3 5", "limits snake 255 0"))
            self.assertEqual(replies(run), [refused("show-invalid")] * 5, broken)
            self.assertEqual(left, as_bytes(invalid))

    def test_a_leg_the_mapping_lacks_comes_before_the_check_and_an_open_upload(self):
        clip = support.clip(5, 60, 6, (20,) * 100)
        files = show_files(TWO_LEGS, clip)
        lines = ("limits snake 3 5", "limits snake 255 5", *self.SETS)
        run = support.start(files, asked(0, *lines), check_first=False)
        self.assertEqual(replies(run), [refused("bad-argument")] * 2 + [refused("busy")] * 3)
        run = support.start(files, asked(0, support.upload_lines(9, "nine.odrg", clip)[0], *lines))
        self.assertEqual(replies(run)[1:], [refused("bad-argument")] * 2 + [refused("busy")] * 3)
        run, left = support.start_and_keep(files, asked(0, "limits snake 3 5"))
        self.assertEqual(replies(run), [refused("bad-argument")])
        self.assertNotIn(limits.NAME, left)

    def test_a_host_whose_storage_cannot_be_changed_cannot_save_them(self):
        files = show_files(TWO_LEGS, support.clip(5, 60, 6))
        for options in (("--no-storage",), ("--only-space",)):
            run, left = support.start_and_keep(files, asked(0, "limits wall 5", "limits snake 1 5", "limits"), options)
            self.assertEqual(replies(run)[:2], [refused("storage-error")] * 2, options)
            self.assertEqual(replies(run)[2]["saved"], False)
            self.assertEqual(left, as_bytes(files))

    def test_they_are_taken_while_a_test_of_the_mapping_shows(self):
        files = show_files(TARGET, picture_file(TARGET, lambda leg, led, frame: WHITE))
        script = asked(0, "mapping test snake 2", "limits snake 2 100", "limits wall 5000", "mapping get") + asked(20) + asked(40, "limits default") + asked(60, "status")
        run, left = support.start_and_keep(files, script)
        answers = replies(run)
        self.assertEqual(answers[:3], [OK] * 3)
        self.assertEqual((answers[3]["test"], answers[3]["snake"]), (True, 2))
        self.assertEqual(answers[4], OK)
        self.assertNotIn(limits.NAME, left)
        shown = pictures(run)
        # The block of the snake's test, limited at level 1 by its budget: every byte of the
        # block 1, the rest of the snake dark.
        for picture in shown[1:3]:
            self.assertEqual(set(picture[2]), {0, 1})
            self.assertEqual(sum(picture[2]), 27)
        self.assertEqual(sum(shown[3][2]), 27 * 255)


class TheSnakeKeepsItsBudget(LimitedTestCase):
    def test_a_budget_stays_with_its_snake_after_mapping_set_and_mapping_cross_on(self):
        # Every snake its own colour, so that the bytes of each leg tell which snake they are.
        clip = picture_file(TARGET, lambda leg, led, frame: bytes([255, 12 * leg, 255 - 12 * leg]))
        budgets = {3: 500, 10: 400}
        files = show_files(TARGET, clip, (0, sorted(budgets.items())))
        swapped = PINS.copy()
        swapped[2], swapped[3] = swapped[3], swapped[2]
        revision = zlib.crc32(bytes(PINS))
        script = asked(0, f"mapping set {revision} {','.join(map(str, swapped))}", "mapping get") + asked(20, "mapping cross on", "mapping get") + polls(2, T0 + 40)
        script += [support.line(T0 + 60, "limits")]
        shown, unlimited = self.assert_limited_as_without(files, script, budgets, 0)
        run, left = support.start_and_keep(files, script)
        answers = replies(run)
        self.assertEqual((answers[0], answers[1]["pins"], answers[2], answers[3]["cross"]), (OK, swapped, OK, True))
        self.assertEqual(answers[4]["legs"][2][2], 500)
        self.assertEqual(answers[4]["legs"][9][2], 400)
        self.assertEqual([entry[0] for entry in answers[4]["legs"] if entry[4]], [3, 10])
        for picture, plain in zip(shown, unlimited):
            self.assertNotEqual(picture[3], plain[3])
            self.assertNotEqual(picture[10], plain[10])
            self.assertEqual({leg: data for leg, data in picture.items() if leg not in budgets}, {leg: data for leg, data in plain.items() if leg not in budgets})
        self.assertEqual(left[limits.NAME], files[limits.NAME])
        # After a restart the snake keeps its budget on its new pin and in its new wiring.
        again = support.start(left, asked(0, "limits"))
        self.assertEqual({leg: pin for leg, pin, _ in again.legs}[3], PINS[3])
        self.assertEqual(pictures(again)[0], shown[-1])
        self.assertEqual(replies(again)[0]["legs"], answers[4]["legs"])


if __name__ == "__main__":
    unittest.main()
