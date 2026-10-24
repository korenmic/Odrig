import json
import unittest

from . import support
from .test_playback import T0, every_20_ms, playing, refreshes

BLOCK = support.STORAGE_BLOCK
BOARD = support.BOARD_STORAGE


OK = '{"ok":true}'


def refused(code):
    return f'{{"ok":false,"error":"{code}"}}'


def replies(lines):
    return [line[len("reply "):] for line in lines if line.startswith("reply ")]


def invalid_show():
    files = support.example_show()
    del files["dvd.odrg"]
    return files


class Content(unittest.TestCase):
    def run_both(self, files, script, options=(), storage=BOARD, changeable=True):
        """Runs a script on the core, on a folder, and on the reference player, and
        compares every line, and the files of the folder afterwards with the reference
        player's. `storage` is what the reference player reports as the total, or None for
        a host that cannot tell; `changeable` whether its storage can be changed."""
        run, left = support.start_and_keep(files, script, options)
        self.reference = support.ReferencePlayer(files, storage=storage, changeable=changeable)
        expected = self.reference.run(script)
        # With the option --trace-store the test host prints the storage calls as well.
        printed = [line for line in run.lines if not line.startswith("store ")]
        self.stored = [line[len("store "):] for line in run.lines if line.startswith("store ")]
        self.assertEqual(len(printed), len(expected))
        for number, (line, wanted) in enumerate(zip(printed, expected)):
            if line != wanted:
                self.fail(f"line {number} differs: the core printed {line[:160]}, the reference {wanted[:160]}")
        self.assertEqual(sorted(left), sorted(self.reference.files))
        self.assertEqual(left, self.reference.files)
        self.left = left
        self.printed = printed
        return printed

    def space(self, files, options=(), storage=BOARD):
        printed = self.run_both(files, [support.line(T0, "space")], options, storage)
        return json.loads(printed[0][len("reply "):])


class Space(Content):
    def test_it_reports_the_free_and_the_total_bytes_and_the_number_of_animations(self):
        files = support.example_show()
        self.assertEqual(sorted(files), ["dvd.odrg", "hello.odrg", "mapping.json", "show.json"])
        self.assertTrue(all(len(content) <= BLOCK for content in files.values()))
        printed = self.run_both(files, [support.line(T0, "space")])
        self.assertEqual(printed, ['reply {"ok":true,"free":13484032,"total":13500416,"animations":2,"external":{"present":false,"free":null,"total":null,"read_only":true}}'])
        self.assertEqual(BOARD - 4 * BLOCK, 13484032)

    def test_the_total_is_the_one_the_host_reports(self):
        files = support.example_show()
        for total in (0, 1, 4 * BLOCK - 1, 4 * BLOCK, 4 * BLOCK + 1, 1000000, 4294967295):
            with self.subTest(total=total):
                reply = self.space(files, ["--storage", str(total)], total)
                self.assertEqual(reply, {"ok": True, "free": max(0, total - 4 * BLOCK), "total": total, "animations": 2, "external": {"present": False, "free": None, "total": None, "read_only": True}})

    def test_every_file_of_the_folder_takes_whole_blocks(self):
        for size, blocks in ((0, 0), (1, 1), (BLOCK - 1, 1), (BLOCK, 1), (BLOCK + 1, 2), (10 * BLOCK, 10), (10 * BLOCK + 1, 11)):
            with self.subTest(size=size):
                files = support.example_show()
                files["extra.odrg"] = bytes(size)
                reply = self.space(files)
                self.assertEqual(reply["free"], BOARD - (4 + blocks) * BLOCK)
                self.assertEqual(reply["animations"], 2)

    def test_the_files_held_in_memory_give_the_figures_of_a_folder(self):
        files = support.example_show()
        files["extra.odrg"] = bytes(3 * BLOCK + 5)
        script = [support.line(T0, "space")]
        in_memory = support.start_each([files, support.demo_show()], script)
        self.assertEqual(in_memory[0].lines, support.start(files, script).lines)
        self.assertEqual(json.loads(replies(in_memory[0].lines)[0])["free"], BOARD - 8 * BLOCK)
        self.assertEqual(in_memory[1].lines, support.ReferencePlayer(support.demo_show()).run(script))

    def test_the_animations_are_the_animation_items_and_not_the_cycles_or_the_files(self):
        clip = support.clip(3, 60, 6)
        cases = (
            ([{"id": 1, "file": "a.odrg"}], 1),
            ([{"id": 1, "file": "a.odrg"}, {"id": 2, "file": "a.odrg"}, {"id": 9, "file": "a.odrg"}], 3),
            ([{"id": 5, "file": "a.odrg"}, {"id": 6, "cycle": [5, 5], "seconds": 3}, {"id": 7, "cycle": [5], "seconds": 1}], 1),
            ([{"id": number, "file": "a.odrg"} for number in range(1, 41)] + [{"id": 100, "cycle": list(range(1, 41)), "seconds": 9}], 40),
        )
        for items, animations in cases:
            files = {"mapping.json": support.mapping_texts()["legs-2"], "show.json": support.show_text(items), "a.odrg": clip}
            self.assertEqual(self.space(files)["animations"], animations)

    def test_with_an_invalid_show_the_space_is_reported_and_the_animations_are_0(self):
        reply = self.space(invalid_show())
        self.assertEqual(reply, {"ok": True, "free": BOARD - 3 * BLOCK, "total": BOARD, "animations": 0, "external": {"present": False, "free": None, "total": None, "read_only": True}})
        self.assertEqual(self.space({}), {"ok": True, "free": BOARD, "total": BOARD, "animations": 0, "external": {"present": False, "free": None, "total": None, "read_only": True}})
        self.assertEqual(self.space({"mapping.json": "{"})["animations"], 0)
        no_show = support.example_show()
        del no_show["show.json"]
        self.assertEqual(self.space(no_show)["animations"], 0)

    def test_with_a_show_that_became_invalid_while_it_played_the_animations_are_0(self):
        files = playing(support.example_show(), 2)
        script = [support.line(T0, "space"), f"poll {T0}", f"poll {T0 + 20}", support.line(T0 + 30, "space"), support.line(T0 + 30, "status")]
        lines = support.start(files, script, ["--remove-after", "dvd.odrg", "1"]).lines
        first, second, status = (json.loads(reply) for reply in replies(lines))
        self.assertEqual((first["animations"], second["animations"]), (2, 0))
        self.assertEqual(status["error"], "file-missing dvd.odrg")
        self.assertEqual((second["free"], second["total"]), (first["free"], first["total"]))

    def test_space_with_any_argument_is_a_bad_argument(self):
        lines = ["space ", "space  ", "space 1", "space space", "space 0 0", "space a b c d e f g", "space" + " " * 2043]
        for options, storage in (((), BOARD), (("--space-unknown",), None), (("--no-storage",), None)):
            printed = self.run_both(support.example_show(), [support.line(T0, line) for line in lines], options, storage, "--no-storage" not in options)
            self.assertEqual(replies(printed), [refused("bad-argument")] * len(lines))

    def test_other_spellings_are_unknown_commands(self):
        lines = ["Space", "SPACE", " space", "spaces", "spac", "space\t", "free"]
        printed = self.run_both(support.example_show(), [support.line(T0, line) for line in lines])
        self.assertEqual(replies(printed), [refused("unknown-command")] * len(lines))

    def test_a_host_that_cannot_tell_the_space_gives_storage_error(self):
        for files in (support.example_show(), invalid_show(), {}):
            printed = self.run_both(files, [support.line(T0, "space")], ["--space-unknown"], None)
            self.assertEqual(replies(printed), [refused("storage-error")])

    def test_a_host_without_storage_functions_gives_storage_error(self):
        printed = self.run_both(support.example_show(), [support.line(T0, "space"), support.fed(T0, b"space\r\n")], ["--no-storage"], None, False)
        self.assertEqual(replies(printed), [refused("storage-error")] * 2)

    def test_a_host_that_can_only_tell_its_space_answers(self):
        files = support.example_show()
        with_storage = support.start(files, [support.line(T0, "space")])
        only_space = support.start(files, [support.line(T0, "space")], ["--only-space"])
        self.assertEqual(only_space.lines, with_storage.lines)
        self.assertEqual(replies(only_space.lines), ['{"ok":true,"free":13484032,"total":13500416,"animations":2,"external":{"present":false,"free":null,"total":null,"read_only":true}}'])

    def test_of_two_codes_that_apply_the_first_of_the_order_is_given(self):
        lines = {"space" + " " * 2044: "line-too-long", "spaces 1": "unknown-command", "space 1": "bad-argument", "space": "storage-error"}
        printed = self.run_both(support.example_show(), [support.line(T0, line) for line in lines], ["--space-unknown"], None)
        self.assertEqual(replies(printed), [refused(code) for code in lines.values()])

    def test_space_through_the_byte_entry(self):
        printed = self.run_both(support.example_show(), [support.fed(T0, b"spa"), support.fed(T0 + 1, b"ce\r\nspace\n")])
        self.assertEqual(printed[0], f"fed {b'space'.hex()}")
        self.assertEqual(replies(printed), ['{"ok":true,"free":13484032,"total":13500416,"animations":2,"external":{"present":false,"free":null,"total":null,"read_only":true}}'] * 2)

    def test_space_changes_nothing_and_does_not_disturb_playback(self):
        files = playing(support.example_show(), 3)
        plain = every_20_ms(120) + [support.line(T0 + 2400, "status")]
        asked = []
        for number, line in enumerate(every_20_ms(120)):
            asked.append(line)
            if number % 7 == 3:
                asked.append(support.line(T0 + 20 * number + 5, "space"))
        asked.append(support.line(T0 + 2400, "status"))
        with_space = self.run_both(files, asked)
        without = self.run_both(files, plain)
        self.assertEqual([line for line in with_space if not line.startswith('reply {"ok":true,"free"')], without)
        self.assertEqual(len(refreshes([line for line in with_space if not line.startswith("reply")])[0]), 120)
        self.assertEqual(len({line for line in with_space if line.startswith('reply {"ok":true,"free"')}), 1)

    def test_space_makes_no_storage_call(self):
        run = support.start(support.example_show(), [support.line(T0, "space")] * 3, ["--trace-store"])
        self.assertEqual(run.stored, ("remove upload.part 0", "remove show.part 0"))
        self.assertEqual(len(run.lines), 3)
        self.assertTrue(all(line.startswith("reply ") for line in run.lines))


def animation(number, file):
    return {"id": number, "file": file}


def cycle(number, ids, seconds=15):
    return {"id": number, "cycle": list(ids), "seconds": seconds}


def small_show(items, start=None, brightness=128, files=None):
    """A file set on the two-leg mapping: a show of these items, and a seeded clip for
    each file name they use, or the files given."""
    made = {"mapping.json": support.mapping_texts()["legs-2"], "show.json": support.show_text(items, brightness, start)}
    names = sorted({item["file"] for item in items if "file" in item})
    for number, name in enumerate(names):
        made[name] = support.clip(number + 1, 60, 6, (20,) * (3 + number % 4))
    made.update(files or {})
    return made


def long_names(count):
    """A show of `count` animations whose file names have 32 characters, each with a file
    of its own, and a cycle after every tenth of them."""
    items = []
    for number in range(1, count + 1):
        items.append(animation(60000 + number, f"{number:04d}" + "n" * 23 + ".odrg"))
    return items


class List(Content):
    def walk(self, files, options=()):
        """Goes through a show with `list`, `list <next>` and so on, on the core and on
        the reference player. Returns the items and the replies."""
        items, lines, position = [], [], 0
        while position is not None:
            lines.append(f"list {position}" if lines else "list")
            printed = self.run_both(files, [support.line(T0, line) for line in lines], options)
            reply = json.loads(replies(printed)[-1])
            self.assertEqual(reply["ok"], True)
            self.assertLessEqual(len(replies(printed)[-1]) + 1, 1024)
            items += reply["items"]
            if reply["next"] is not None:
                self.assertEqual(reply["next"], len(items))
                self.assertGreater(len(reply["items"]), 0)
            position = reply["next"]
        return items, replies(printed)

    def expected_items(self, files):
        listed = json.loads(files["show.json"])["items"]
        return [dict(item, bytes=len(files[item["file"]]), ignored=item.get("ignored", False)) if "file" in item else item for item in listed]

    def test_the_example_show_is_listed_as_the_document_has_it(self):
        printed = self.run_both(support.example_show(), [support.line(T0, "list"), support.line(T0, "list 0")])
        expected = '{"ok":true,"items":[{"id":1,"file":"hello.odrg","bytes":1138,"ignored":false},{"id":2,"file":"dvd.odrg","bytes":1612,"ignored":false},{"id":3,"cycle":[1,2],"seconds":15}],"next":null}'
        self.assertEqual(replies(printed), [expected, expected])
        text = (support.ROOT / "docs" / "commands.md").read_text(encoding="utf-8")
        self.assertIn(f"list\n{expected}\n", text)

    def test_every_show_of_the_suite_is_listed_from_every_position(self):
        from .test_memory import hundred_items

        shows = {
            "example": support.example_show(),
            "demo": support.demo_show(),
            "hundred items": hundred_items(),
            "one item": small_show([animation(65535, "a.odrg")]),
            "shared file": small_show([animation(5, "a.odrg"), animation(9, "a.odrg"), cycle(2, [9, 5, 9], 65535), animation(7, "b.odrg")], start=2),
        }
        for name, files in shows.items():
            with self.subTest(show=name):
                expected = self.expected_items(files)
                items, _ = self.walk(files)
                self.assertEqual(items, expected)
                lines = [f"list {position}" for position in range(len(expected) + 3)] + ["list 65535", "list 00000", "list 0001"]
                printed = self.run_both(files, [support.line(T0, line) for line in lines])
                for position, reply in enumerate(replies(printed)[:len(expected) + 3]):
                    reply = json.loads(reply)
                    self.assertEqual(reply["items"], expected[position:position + len(reply["items"])])
                    self.assertEqual(reply["next"], None if position + len(reply["items"]) >= len(expected) else position + len(reply["items"]))
                self.assertEqual(json.loads(replies(printed)[len(expected)]), {"ok": True, "items": [], "next": None})
                self.assertEqual(json.loads(replies(printed)[-3]), {"ok": True, "items": [], "next": None})
                self.assertEqual(replies(printed)[-2], replies(printed)[0])
                self.assertEqual(replies(printed)[-1], replies(printed)[1])

    def test_a_show_of_132_items_with_names_of_32_characters_is_gone_through_once(self):
        items = long_names(132)
        files = small_show(items, files={item["file"]: support.clip(1, 60, 6) for item in items})
        self.assertEqual({len(item["file"]) for item in items}, {32})
        listed, given = self.walk(files)
        self.assertEqual([item["id"] for item in listed], [item["id"] for item in items])
        self.assertEqual(len({item["id"] for item in listed}), 132)
        self.assertEqual({item["bytes"] for item in listed}, {len(support.clip(1, 60, 6))})
        self.assertGreater(len(given), 9)
        # Every reply but the last is as full as it can be: the next item would not fit.
        sizes = [len(reply) + 1 for reply in given]
        self.assertTrue(all(size > 1024 - 91 for size in sizes[:-1]), sizes)

    def test_a_reply_is_at_most_1024_bytes_and_one_of_exactly_1024_is_given(self):
        clip = support.clip(1, 60, 6)
        sizes = set()
        exact = None
        # One name of its own length and forty items that share a file under another name:
        # among these shows there is one whose first reply is full to the byte.
        for first in range(6, 33):
            for others in range(6, 33, 2):
                names = ["a" * (first - 5) + ".odrg", "b" * (others - 5) + ".odrg"]
                items = [animation(1, names[0])] + [animation(number, names[1]) for number in range(2, 42)]
                files = small_show(items, files={name: clip for name in names})
                reply = support.ReferencePlayer(files).command(0, b"list")
                sizes.add(len(reply))
                if len(reply) == 1024 and exact is None:
                    exact = files
        self.assertLessEqual(max(sizes), 1024)
        self.assertIsNotNone(exact, sorted(sizes))
        printed = self.run_both(exact, [support.line(T0, "list")])
        self.assertEqual(len(replies(printed)[0]) + 1, 1024)
        self.assertIsNotNone(json.loads(replies(printed)[0])["next"])

    def test_a_cycle_too_long_for_a_reply_is_listed_with_an_empty_list(self):
        animations = [animation(60000 + number, f"{number:03d}.odrg") for number in range(200)]
        clip = support.clip(2, 60, 6)
        clips = {item["file"]: clip for item in animations}
        ids = [item["id"] for item in animations]
        for entries, whole in ((10, True), (150, True), (160, True), (161, False), (200, False), (1000, False)):
            with self.subTest(entries=entries):
                long_cycle = cycle(7, [ids[number % 200] for number in range(entries)], 9)
                files = small_show([animations[0], long_cycle] + animations[1:], files=clips)
                printed = self.run_both(files, [support.line(T0, "list 1")])
                first = json.loads(replies(printed)[0])["items"][0]
                self.assertEqual(first, long_cycle if whole else cycle(7, [], 9))
                listed, _ = self.walk(files)
                self.assertEqual(len(listed), 201)
                self.assertEqual(listed[1], first)
        # The longest cycle that fits by itself, to the byte, and the one that is longer.
        fits = None
        for entries in range(150, 170):
            files = small_show([cycle(7, [ids[number % 200] for number in range(entries)], 9)] + animations, files=clips)
            reply = json.loads(support.ReferencePlayer(files).command(0, b"list"))
            if reply["items"][0]["cycle"]:
                fits = entries
        self.assertEqual(fits, 160)
        text = json.dumps(cycle(7, ids[:160], 9), separators=(",", ":"))
        self.assertLessEqual(len('{"ok":true,"items":[') + len(text) + len('],"next":1}\n'), 1024)
        self.assertGreater(len('{"ok":true,"items":[') + len(text) + 6 + len('],"next":1}\n'), 1024)

    def test_a_show_without_items_gives_no_items_and_null(self):
        files = small_show([])
        printed = self.run_both(files, [support.line(T0, line) for line in ("list", "list 0", "list 1", "list 65535", "space", "status")])
        self.assertEqual(replies(printed)[:4], ['{"ok":true,"items":[],"next":null}'] * 4)
        self.assertEqual(json.loads(replies(printed)[4])["animations"], 0)
        self.assertEqual(json.loads(replies(printed)[5])["error"], None)

    def test_with_an_invalid_show_list_is_refused(self):
        for files in (invalid_show(), {}, {"mapping.json": support.mapping_texts()["legs-2"]}):
            printed = self.run_both(files, [support.line(T0, line) for line in ("list", "list 0", "list 2", "list 65535")])
            self.assertEqual(replies(printed), [refused("show-invalid")] * 4)

    def test_a_from_that_is_no_number_from_0_to_65535_is_a_bad_argument(self):
        lines = ["list ", "list  1", "list 1 ", "list -1", "list +1", "list 65536", "list 99999999999", "list a", "list 1a", "list 0x1", "list 1.0", "list 1 2", "list 0 0 0 0 0 0"]
        for files in (support.example_show(), invalid_show()):
            printed = self.run_both(files, [support.line(T0, line) for line in lines])
            self.assertEqual(replies(printed), [refused("bad-argument")] * len(lines))
        printed = self.run_both(support.example_show(), [support.line(T0, line) for line in ("List", "lists", "list\t1", "ls")])
        self.assertEqual(replies(printed), [refused("unknown-command")] * 4)

    def test_list_changes_nothing_and_does_not_disturb_playback(self):
        files = playing(support.example_show(), 3)
        plain = every_20_ms(120) + [support.line(T0 + 2400, "status")]
        asked = []
        for number, line in enumerate(every_20_ms(120)):
            asked.append(line)
            if number % 5 == 2:
                asked.append(support.line(T0 + 20 * number + 3, f"list {number % 4}"))
        asked.append(support.line(T0 + 2400, "status"))
        with_list = self.run_both(files, asked, ["--trace-store"])
        self.assertEqual(self.stored, [])
        without = self.run_both(files, plain)
        self.assertEqual([line for line in with_list if '"items"' not in line], without)
        self.assertEqual(self.left, {name: content if isinstance(content, bytes) else content.encode() for name, content in files.items()})


class Remove(Content):
    ITEMS = [animation(1, "one.odrg"), animation(2, "two.odrg"), cycle(3, [1, 2], 1), animation(4, "four.odrg"), animation(5, "two.odrg"), cycle(6, [4, 5, 4], 2)]

    def removed(self, files, number, before=(), after=(), options=()):
        """Removes one item in a session with polls before and after, on the core and on
        the reference player. Returns the lines printed."""
        script = list(before) + [support.line(T0 + 500, f"remove {number}"), support.line(T0 + 500, "list"), support.line(T0 + 500, "status"), support.line(T0 + 500, "space")]
        script += every_20_ms(30, T0 + 500) + list(after) + [support.line(T0 + 1200, "status")]
        return self.run_both(files, script, options)

    def listed_ids(self, printed):
        return [item["id"] for item in json.loads(next(line for line in replies(printed) if '"items"' in line))["items"]]

    def test_an_animation_with_a_file_of_its_own_leaves_the_show_and_its_file_is_deleted(self):
        files = small_show(self.ITEMS, start=6)
        printed = self.removed(files, 1, before=[support.line(T0, "remove 3")] + every_20_ms(25))
        self.assertEqual(replies(printed)[:2], [OK, OK])
        self.assertEqual(self.listed_ids(printed), [2, 4, 5, 6])
        self.assertNotIn("one.odrg", self.left)
        self.assertEqual(sorted(self.left), ["four.odrg", "mapping.json", "show.json", "two.odrg"])
        self.assertEqual(self.left["show.json"], b'{"version":1,"brightness":128,"items":[{"id":2,"file":"two.odrg"},{"id":4,"file":"four.odrg"},{"id":5,"file":"two.odrg"},{"id":6,"cycle":[4,5,4],"seconds":2}],"start":6}\n')

    def test_an_animation_whose_file_another_item_names_leaves_the_file(self):
        files = small_show(self.ITEMS, start=1)
        printed = self.removed(files, 5, before=[support.line(T0, "remove 6")] + every_20_ms(25))
        self.assertEqual(self.listed_ids(printed), [1, 2, 3, 4])
        self.assertIn("two.odrg", self.left)
        self.assertEqual(self.left["two.odrg"], files["two.odrg"])
        printed = self.removed(self.left, 3)
        printed = self.removed(self.left, 2)
        self.assertNotIn("two.odrg", self.left)
        self.assertEqual(self.listed_ids(printed), [1, 4])

    def test_a_cycle_leaves_the_show_and_its_animations_stay(self):
        files = small_show(self.ITEMS, start=4)
        for number, left in ((3, [1, 2, 4, 5, 6]), (6, [1, 2, 3, 4, 5])):
            printed = self.removed(files, number, before=every_20_ms(25), after=[support.line(T0 + 1100, "play 6" if number == 3 else "play 3")] + every_20_ms(5, T0 + 1100))
            self.assertEqual(replies(printed)[0], OK)
            self.assertEqual(self.listed_ids(printed), left)
            self.assertEqual(sorted(self.left), ["four.odrg", "mapping.json", "one.odrg", "show.json", "two.odrg"])
            self.assertEqual(json.loads(replies(printed)[-1])["playing"], 6 if number == 3 else 3)

    def test_an_animation_that_a_cycle_lists_is_in_use(self):
        files = small_show(self.ITEMS, start=3)
        lines = [f"remove {number}" for number in (1, 2, 4, 5)] + ["list", "remove 3", "remove 1", "remove 2", "remove 4", "remove 6", "remove 4", "remove 5", "list"]
        printed = self.run_both(files, [support.line(T0, line) for line in lines])
        given = replies(printed)
        self.assertEqual(given[:4], [refused("in-use")] * 4)
        self.assertEqual(given[5:8], [OK, OK, OK])
        self.assertEqual(given[8:12], [refused("in-use"), OK, OK, OK])
        self.assertEqual(json.loads(given[4])["items"], self.reference_items(files))
        self.assertEqual(json.loads(given[12])["items"], [])
        self.assertEqual(sorted(self.left), ["mapping.json", "show.json"])

    def reference_items(self, files):
        listed = json.loads(files["show.json"])["items"]
        return [dict(item, bytes=len(files[item["file"]]), ignored=item.get("ignored", False)) if "file" in item else item for item in listed]

    def test_removing_the_start_item_leaves_the_show_without_start(self):
        # Without a start, the show that is left plays the playlist from its first animation.
        for start, number, first in ((6, 6, 1), (1, 1, 2), (3, 3, 1)):
            files = small_show(self.ITEMS, start=start)
            before = [support.line(T0, "play 4")] + every_20_ms(25)
            if number == 1:
                before = [support.line(T0, "remove 3")] + before
            self.removed(files, number, before=before)
            written = json.loads(self.left["show.json"])
            self.assertNotIn("start", written)
            self.assertEqual(support.start(self.left, [support.line(T0, "status")]).lines,
                             ['reply {"ok":true,"on":true,"brightness":128,"playing":"all","animation":%d,"fps":0,"error":null,"width":60,"height":6}' % first])
        files = small_show(self.ITEMS, start=6)
        self.removed(files, 3, before=every_20_ms(25))
        self.assertEqual(json.loads(self.left["show.json"])["start"], 6)
        self.assertEqual(json.loads(support.start(self.left, [support.line(T0, "status")]).lines[0][6:])["playing"], 6)

    def test_removing_what_plays_leaves_the_playlist_playing(self):
        # A cycle that plays leaves: the playlist plays, from its first animation. The
        # animation whose turn it is leaves: the playlist goes on with the one after it.
        for number, then in ((6, 1), (4, 5), (3, 1)):
            with self.subTest(playing=number):
                files = small_show(self.ITEMS, start=number)
                before = every_20_ms(25)
                if number == 4:
                    before = [support.line(T0, "remove 6")] + before
                printed = self.removed(files, number, before=before)
                produced, _ = refreshes([line for line in printed if line.startswith(("refresh", "data"))])
                lit = [any(any(data) for data in legs.values()) for _, legs in produced]
                self.assertEqual(lit, [True] * 55)
                states = [json.loads(reply) for reply in replies(printed) if '"playing"' in reply]
                self.assertEqual([(state["playing"], state["animation"]) for state in states], [("all", then), ("all", then)])
                self.assertEqual({state["error"] for state in states}, {None})

    def test_removing_another_item_leaves_what_plays_undisturbed(self):
        cases = ((6, 1, [3]), (6, 3, []), (3, 6, []), (4, 3, []), (2, 6, [4]), (5, 3, [1]), (6, 2, [3]))
        for played, number, first in cases:
            with self.subTest(playing=played, removed=number):
                files = small_show(self.ITEMS, start=played)
                before = [support.line(T0, f"remove {other}") for other in first] + every_20_ms(25)
                with_removal = self.removed(files, number, before=before, after=every_20_ms(20, T0 + 1100))
                self.assertEqual(replies(with_removal)[len(first)], OK)
                # The same session without the removal gives the same LED data at every refresh.
                plain = [support.line(T0, f"remove {other}") for other in first] + every_20_ms(25) + every_20_ms(30, T0 + 500) + every_20_ms(20, T0 + 1100)
                without = self.run_both(files, plain)
                self.assertEqual([line for line in with_removal if not line.startswith("reply")], [line for line in without if not line.startswith("reply")])
                # A cycle that was the start plays on; an animation that was the start
                # still has its turn in the playlist.
                state = json.loads(replies(with_removal)[-1])
                if played in (3, 6):
                    self.assertEqual(state["playing"], played)
                else:
                    self.assertEqual((state["playing"], state["animation"]), ("all", played))

    def test_the_last_item_can_be_removed_and_the_show_without_items_is_valid(self):
        files = small_show([animation(9, "only.odrg")], start=9, brightness=77)
        printed = self.removed(files, 9, before=[support.line(T0, "brightness 200")] + every_20_ms(25), after=[support.line(T0 + 1100, "remove 9"), support.line(T0 + 1100, "play 9")])
        self.assertEqual(replies(printed)[1], OK)
        self.assertEqual(replies(printed)[2], '{"ok":true,"items":[],"next":null}')
        self.assertEqual(replies(printed)[-3:-1], [refused("unknown-id")] * 2)
        self.assertEqual(self.left["show.json"], b'{"version":1,"brightness":77,"items":[]}\n')
        self.assertEqual(sorted(self.left), ["mapping.json", "show.json"])
        again = support.start(self.left, [support.line(T0, "status"), support.line(T0, "list"), support.line(T0, "space")])
        self.assertIsNone(again.error)
        self.assertEqual(again.lines[1:], ['reply {"ok":true,"items":[],"next":null}', f'reply {{"ok":true,"free":{BOARD - 2 * BLOCK},"total":{BOARD},"animations":0,"external":{{"present":false,"free":null,"total":null,"read_only":true}}}}'])
        self.assertEqual(json.loads(again.lines[0][6:])["brightness"], 77)

    def test_the_brightness_written_is_the_one_of_the_show_file(self):
        files = small_show(self.ITEMS, start=6, brightness=31)
        self.removed(files, 3, before=[support.line(T0, "brightness 255"), support.line(T0, "off")])
        self.assertEqual(json.loads(self.left["show.json"])["brightness"], 31)

    def test_an_id_that_is_no_number_from_1_to_65535_is_a_bad_argument(self):
        lines = ["remove", "remove ", "remove  1", "remove 1 ", "remove 0", "remove 65536", "remove -1", "remove a", "remove 1 2", "remove 1.0", "remove 0x1", "remove 3 3 3 3 3 3"]
        for files in (small_show(self.ITEMS), invalid_show()):
            printed = self.run_both(files, [support.line(T0, line) for line in lines])
            self.assertEqual(replies(printed), [refused("bad-argument")] * len(lines))

    def test_an_id_that_no_item_has_is_unknown(self):
        printed = self.run_both(small_show(self.ITEMS), [support.line(T0, line) for line in ("remove 7", "remove 65535", "remove 0007", "remove 3", "remove 3", "remove 003")])
        self.assertEqual(replies(printed), [refused("unknown-id")] * 3 + [OK] + [refused("unknown-id")] * 2)

    def test_with_an_invalid_show_remove_is_refused(self):
        printed = self.run_both(invalid_show(), [support.line(T0, line) for line in ("remove 1", "remove 3", "remove 99")])
        self.assertEqual(replies(printed), [refused("show-invalid")] * 3)
        self.assertEqual(sorted(self.left), ["hello.odrg", "mapping.json", "show.json"])

    def test_of_two_codes_that_apply_the_first_of_the_order_is_given(self):
        valid = {"remove" + " 1" * 1022: "line-too-long", "removes 1": "unknown-command", "remove 0": "bad-argument", "remove 99": "unknown-id", "remove 1": "in-use"}
        printed = self.run_both(small_show(self.ITEMS), [support.line(T0, line) for line in valid], ["--no-storage"], None, False)
        self.assertEqual(replies(printed), [refused(code) for code in valid.values()])
        invalid = {"remove 0": "bad-argument", "remove 99": "show-invalid", "remove 1": "show-invalid", "list x": "bad-argument", "list 5": "show-invalid"}
        printed = self.run_both(invalid_show(), [support.line(T0, line) for line in invalid])
        self.assertEqual(replies(printed), [refused(code) for code in invalid.values()])

    def test_a_host_whose_storage_cannot_be_changed_gives_storage_error_and_nothing_changes(self):
        files = small_show(self.ITEMS, start=6)
        for option, storage in (("--no-storage", None), ("--only-space", BOARD)):
            lines = ["remove 3", "remove 6", "remove 99", "remove 1", "list", "status"]
            printed = self.run_both(files, every_20_ms(5) + [support.line(T0 + 100, line) for line in lines] + every_20_ms(5, T0 + 100), [option, "--trace-store"], storage, False)
            self.assertEqual(replies(printed)[:4], [refused("storage-error")] * 2 + [refused("unknown-id"), refused("in-use")])
            self.assertEqual(json.loads(replies(printed)[4])["items"], self.reference_items(files))
            self.assertEqual(json.loads(replies(printed)[5])["playing"], 6)
            self.assertEqual(self.stored, [])

    def test_the_storage_calls_of_a_removal_are_those_of_the_design_in_their_order(self):
        files = small_show(self.ITEMS, start=6)
        cases = {
            3: ["write_open show.part 1", "write {n} 1", "write_close 1", "rename show.part show.json 1"],
            1: ["write_open pending.txt 1", "write 9 1", "write_close 1", "write_open show.part 1", "write {n} 1", "write_close 1", "rename show.part show.json 1", "remove one.odrg 1", "remove pending.txt 1"],
        }
        run, left = support.start_and_keep(files, [support.line(T0, "remove 3"), support.line(T0, "remove 1")], ["--trace-store"])
        self.assertEqual(run.stored, ("remove upload.part 0", "remove show.part 0"))
        stored = [line[len("store "):] for line in run.lines if line.startswith("store ")]
        after_first = len(cases[3])
        sizes = [int(line.split()[1]) for line in stored if line.startswith("write ") and int(line.split()[1]) != 9]
        self.assertEqual(stored[:after_first], [line.format(n=sizes[0]) for line in cases[3]])
        self.assertEqual(stored[after_first:], [line.format(n=sizes[1]) for line in cases[1]])
        self.assertEqual(sizes[1], len(left["show.json"]))
        self.assertEqual([line for line in run.lines if line.startswith("reply")], [f"reply {OK}"] * 2)

    def test_a_show_file_longer_than_a_piece_is_written_in_pieces_of_1500_bytes(self):
        from .test_memory import hundred_items

        files = hundred_items()
        run, left = support.start_and_keep(files, [support.line(T0, "remove 100")], ["--trace-store"])
        writes = [int(line.split()[2]) for line in run.lines if line.startswith("store write ")]
        self.assertGreater(len(left["show.json"]), 3000)
        self.assertEqual(sum(writes), len(left["show.json"]))
        self.assertEqual(writes[:-1], [1500] * (len(writes) - 1))
        self.assertLessEqual(writes[-1], 1500)
        reference = support.ReferencePlayer(files)
        reference.command(T0, b"remove 100")
        self.assertEqual(left, reference.files)

    def test_what_the_core_wrote_is_read_back_by_the_core_and_by_the_converter(self):
        from odrig import show

        files = small_show(self.ITEMS, start=6, brightness=40)
        printed = self.run_both(files, [support.line(T0, "remove 3"), support.line(T0, "remove 1"), support.line(T0, "list")])
        written = show.loads(self.left["show.json"])
        self.assertEqual([item.id for item in written.items], [2, 4, 5, 6])
        self.assertEqual((written.brightness, written.start), (40, 6))
        self.assertEqual(written.items[3], show.Item(6, None, (4, 5, 4), 2))
        again = self.run_both(self.left, [support.line(T0, "list"), support.line(T0, "status")] + every_20_ms(120))
        self.assertEqual(replies(again)[0], replies(printed)[-1])
        self.assertEqual(json.loads(replies(again)[1])["playing"], 6)

    def test_many_removals_in_a_seeded_order_leave_the_show_the_reference_has(self):
        import random

        animations = [animation(number, f"f{number % 9}.odrg") for number in range(1, 31)]
        cycles = [cycle(100 + number, [1 + (number * 7 + step * 3) % 30 for step in range(1 + number % 5)], 1 + number) for number in range(12)]
        items = animations[:10] + cycles[:6] + animations[10:] + cycles[6:]
        files = small_show(items, start=105)
        rng = random.Random(7)
        order = [item["id"] for item in items]
        rng.shuffle(order)
        script = []
        for step, number in enumerate(order * 2):
            script.append(support.line(T0 + 40 * step, f"remove {number}"))
            script.append(support.line(T0 + 40 * step, "list"))
            script.append(f"poll {T0 + 40 * step}")
            if step % 7 == 0:
                script.append(support.line(T0 + 40 * step, f"play {order[(step * 5) % len(order)]}"))
        printed = self.run_both(files, script + [support.line(T0 + 100000, "list"), support.line(T0 + 100000, "space")])
        codes = {json.loads(reply).get("error") for reply in replies(printed)}
        self.assertEqual(codes, {None, "in-use", "unknown-id"})
        self.assertEqual(replies(printed)[-2], '{"ok":true,"items":[],"next":null}')
        self.assertEqual(sorted(self.left), ["mapping.json", "show.json"])


class HostWithoutStorage(Content):
    def test_a_session_runs_as_ever_on_a_host_without_storage_functions(self):
        files = playing(support.example_show(), 3)
        script = every_20_ms(60) + [support.line(T0 + 1200, "play 2"), support.line(T0 + 1200, "status")] + every_20_ms(20, T0 + 1200)
        with_storage = support.start(files, script)
        for option in ("--no-storage", "--only-space"):
            without = support.start(files, script, [option, "--trace-store", "--trace-files"])
            self.assertEqual([line for line in without.lines if not line.startswith("open ")], with_storage.lines, option)
            # It is not asked for the four blocks that only a host with storage needs: the
            # chunk buffer, and the decoders, the pixel buffer and the window of the check.
            # It is asked to remove nothing, and not for the file of leftovers.
            self.assertEqual(without.memory[1], with_storage.memory[1] - 4, option)
            saved = with_storage.memory[0] - without.memory[0]
            self.assertGreater(saved, 1500 + 1080 + 32768 + 2000, option)
            self.assertLess(saved, 1500 + 1080 + 32768 + 3000, option)
            self.assertEqual(without.stored, (), option)
            self.assertNotIn("pending.txt", [name for name, _ in without.opened], option)
            self.assertIsNone(without.error)


class StorageGuards(unittest.TestCase):
    GUARDS = ("write", "write-none", "close-none", "two-files", "name", "rename-open", "remove-open", "read-at", "read-at-offset")

    def test_each_misuse_of_the_storage_functions_stops_the_test_host(self):
        for what in self.GUARDS:
            with self.subTest(what=what):
                result = support.host("guard", what)
                self.assertEqual((result.status, result.out, result.err), (71, "file misuse\n", ""))

    def test_the_guards_are_the_ones_the_test_host_names(self):
        usage = support.host("guard", "no-such-guard")
        self.assertEqual(usage.status, 64)
        for what in self.GUARDS:
            self.assertRegex(usage.err, rf"[ |]{what}[ \n|]")

    def test_an_option_of_storage_without_a_whole_number_in_range_is_a_usage_error(self):
        for option in ("--storage", "--store-fails-at", "--cut-at", "--cut-keeps"):
            self.assertEqual(support.host("session", "/nonexistent", option).status, 64, option)
        for value in ("-1", "4294967296", "1e3", "", "12 "):
            self.assertEqual(support.host("session", "/nonexistent", "--storage", value).status, 64, value)


if __name__ == "__main__":
    unittest.main()
