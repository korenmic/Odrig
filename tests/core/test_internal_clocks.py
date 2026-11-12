"""The clocks and messages of the board's own storage: the files of its folders `clocks` and
`clocks/message` are faces and messages beside the card's, in Between animations and in
Clocks only, and a copy in both storages plays from the storage `clocks storage` prefers, the
card by default."""

import hashlib
import itertools
import json
import unittest

from odrig import odrgx

from . import support
from .test_clock_modes import distinct, mode_file
from .test_clocks import CARD, CLOCK_FILES, SHOW4, clock_of, states_of
from .test_drive import DONE, a_drive, asked, logged, refusal, replies
from .test_playback import T0
from .test_playlist import loop_of, show_of

WINDOW = 86_400_000

# The board's folders: `art` (number 4, id 23), `clocks` (1, 20), `clocks/message` (2, 21)
# and `clocks/old` (3, 22), in the tree's order; `clocks/empty` (5, 24) in some shows.
FOLDERS = "odrig-folders 1 5\n4 23 0 art\n1 20 0 clocks\n2 21 0 clocks/message\n3 22 0 clocks/old\n"
WITH_EMPTY = FOLDERS.replace("odrig-folders 1 5", "odrig-folders 1 6").replace("2 21 0", "5 24 0 clocks/empty\n2 21 0")
ONLY_CLOCKS = "odrig-folders 1 3\n1 20 0 clocks\n2 21 0 clocks/message\n"

ROOT = {"id": 1, "file": "four.odrg"}
F1 = {"id": 11, "file": "1/f1.odrg"}
F2 = {"id": 12, "file": "1/f2.odrg"}
M1 = {"id": 13, "file": "2/m1.odrg"}
OLD = {"id": 14, "file": "3/old.odrg"}
ART = {"id": 15, "file": "4/art.odrg"}
ITEMS = [ROOT, F1, F2, M1, OLD, ART]
FILES = {"four.odrg": loop_of(4, 1), "1/f1.odrg": loop_of(3, 21), "1/f2.odrg": loop_of(3, 22), "2/m1.odrg": loop_of(1, 23),
         "3/old.odrg": loop_of(3, 24), "4/art.odrg": loop_of(4, 25)}

FACES = {"clocks/f1.odrg", "clocks/f2.odrg"}
MESSAGE = "clocks/message/m1.odrg"
ORDINARY = {"four.odrg", "art/art.odrg"}
CARD_MESSAGE = "clocks/message/m.odrg"
CARD_FACES = {name: data for name, data in CARD.items() if name != CARD_MESSAGE}


def board(items=ITEMS, folders=FOLDERS, clocks=None, more=None, **files):
    """The board's show of these items, their files from FILES or as given, and `folders.txt`;
    `clocks` the mode and the message of `clocks.txt`."""
    wanted = {item["file"] for item in items if "file" in item}
    chosen = {name: data for name, data in {**FILES, **files}.items() if name in wanted}
    source = {**show_of(items, chosen, min_seconds=4), **(more or {})}
    if folders is not None:
        source["folders.txt"] = folders
    if clocks is not None:
        source["clocks.txt"] = mode_file(*clocks)
    return source


def session(source, script, card=None, options=(), check_first=True):
    """A session from a refresh at power-on, with a card of these files when one is given."""
    script = [f"poll {T0}", *script]
    if card is None:
        return support.start(source, script, list(options), check_first=check_first)
    with a_drive(card) as top:
        return support.start(source, script, ["--drive", top, *options], check_first=check_first)


def at_times(*times):
    return [line for time in times for line in asked(time, "status")]


def files_of(run):
    return [state["file"] for state in states_of(run)]


def played(run):
    """The files that played one after another, each with its storage: the ids of these
    tests' shows are 60,000 or less, and a card's file has one of 60,001 or more."""
    seen = [(state["file"], "board" if state["animation"] is not None and state["animation"] <= 60000 else "card")
            for state in states_of(run) if state["file"] is not None]
    return distinct(seen)


def answers(run):
    return [reply for reply in replies(run) if "on" not in reply]


class Recognition(unittest.TestCase):
    def test_the_files_of_clocks_are_faces_and_those_of_clocks_message_messages(self):
        run = session(board(clocks=("only", True)), at_times(*range(100, 60100, 500)))
        states = states_of(run)
        self.assertEqual({state["file"] for state in states}, FACES | {MESSAGE})
        self.assertTrue(all(state["clock_only"] == {"folder": 20, "state": "playing"} for state in states))
        self.assertTrue(all((state["playing"], state["playlist"]) == (20, "clocks") for state in states))
        self.assertTrue(all(state["animation"] in (11, 12, 13) for state in states))
        sequence = distinct(files_of(run))
        for before, after in zip(sequence, sequence[1:]):
            self.assertNotEqual(before in FACES, after in FACES)

    def test_the_root_an_orphan_another_folder_and_a_folder_below_clocks_hold_no_clock(self):
        orphan = {"id": 16, "file": "9/f.odrg"}
        items = [ROOT, OLD, ART, orphan, {"id": 17, "file": "clocks.odrg"}]
        source = board(items, clocks=("only", True), **{"9/f.odrg": loop_of(3, 26), "clocks.odrg": loop_of(3, 27)})
        run = session(source, at_times(100, 10000, 30000))
        self.assertTrue(all(state["clock_only"] == {"folder": 20, "state": "no-clocks"} for state in states_of(run)))
        self.assertTrue(all(state["animation"] is None for state in states_of(run)))

    def test_a_boot_that_cannot_read_folders_txt_has_no_clocks_of_the_board(self):
        damaged = FOLDERS + "bad\n"
        run = session(board(folders=damaged, clocks=("only", True)), at_times(100, 10000))
        self.assertIn("folders unreadable", run.logs)
        self.assertTrue(all(state["clock_only"] == {"folder": None, "state": "no-card"} for state in states_of(run)))
        self.assertTrue(all(state["animation"] is None for state in states_of(run)))
        run = session(board(folders=damaged, clocks=("between", True)), at_times(*range(100, 45100, 500)))
        self.assertEqual(set(files_of(run)), {"four.odrg", "1/f1.odrg", "1/f2.odrg", "2/m1.odrg", "3/old.odrg", "4/art.odrg"})

    def test_the_classes_are_found_again_after_a_folder_is_made_a_file_installed_and_a_folder_pruned(self):
        from .test_internal_folders import upload
        source = board([ROOT], folders=None, clocks=("only", True))
        script = at_times(100) + asked(200, "folder make internal clocks", "folder make internal clocks/message") + at_times(300)
        script += upload(T0 + 400, 31, "clocks/message/w.odrg", loop_of(1, 41)) + at_times(1100)
        script += upload(T0 + 1200, 32, "clocks/f.odrg", loop_of(3, 42)) + at_times(1900, 8000)
        script += asked(8100, "remove 31") + at_times(8200, 15000)
        script += asked(15100, "remove 32", "list") + at_times(15200)
        run = session(source, script)
        states = states_of(run)
        self.assertEqual([state["clock_only"] for state in states], [{"folder": None, "state": "no-card"}] +
                         [{"folder": 2, "state": "no-clocks"}] * 2 + [{"folder": 2, "state": "playing"}] * 4 +
                         [{"folder": None, "state": "no-card"}])
        self.assertEqual([state["file"] for state in states[3:7]], ["clocks/f.odrg", "clocks/message/w.odrg", "clocks/f.odrg", "clocks/f.odrg"])
        self.assertEqual([item["id"] for item in replies(run)[-2]["items"]], [1])

    def test_a_message_is_never_a_face(self):
        source = board([ROOT, M1, ART], clocks=("only", True))
        run = session(source, at_times(100, 10000, 30000))
        self.assertTrue(all(state["clock_only"] == {"folder": 20, "state": "no-clocks"} for state in states_of(run)))
        self.assertTrue(all(state["animation"] is None for state in states_of(run)))
        source = board([ROOT, M1, ART], clocks=("between", True))
        run = session(source, at_times(*range(100, 60100, 500)))
        self.assertEqual(set(files_of(run)), ORDINARY)


# The SHA-256 of the replies of a session of a show without an internal folder `clocks`,
# with the card's clocks, the member `clock_storage` of `status` taken out: what a show of
# the card's clocks alone answers.
FLAT_REPLIES = {
    "flat": "6250818368867805cbb8ffefffb0e4b7f15362ef78db9de55441e2ec869813e7",
    "folders": "72fe3012d09f07e75212fdc8717d3081af000c29b09321b71515a6cf4aee7ccf",
}


def flat_script():
    script = at_times(*range(100, 40100, 700))
    script += asked(40200, "clocks only", "status") + at_times(*range(40400, 70400, 900))
    script += asked(70500, "play 60004", "status", "play 60008", "status", "play 1", "play 23", "play all", "status")
    script += asked(70600, "ignore 60007 1", "status", "ignore 60007 0", "status", "list", "list in 60007")
    script += ["drive pull"] + at_times(70800) + asked(70900, "clocks off", "status") + at_times(*range(71000, 80000, 1100))
    return script


def flat_replies(source):
    with a_drive(CARD) as top:
        run = support.start(source, [f"poll {T0}", *flat_script()], ["--drive", top])
    text = "\n".join(line for line in run.lines if line.startswith("reply "))
    return hashlib.sha256(text.replace(',"clock_storage":"sd"', "").encode("utf-8")).hexdigest()


class AShowWithoutClocks(unittest.TestCase):
    def test_a_flat_show_answers_byte_for_byte_its_recorded_replies(self):
        self.assertEqual(flat_replies({**SHOW4, "clocks.txt": mode_file("between", True)}), FLAT_REPLIES["flat"])

    def test_a_show_whose_folders_hold_no_clocks_answers_byte_for_byte_its_recorded_replies(self):
        source = board([ROOT, ART], folders="odrig-folders 1 5\n4 23 0 art\n", clocks=("between", True))
        self.assertEqual(flat_replies(source), FLAT_REPLIES["folders"])


class Between(unittest.TestCase):
    def test_the_cards_faces_are_followed_by_the_boards_messages(self):
        source = board([ROOT, M1], folders=ONLY_CLOCKS, clocks=("between", True))
        run = session(source, at_times(*range(100, 60100, 250)), card=CARD_FACES)
        sequence = played(run)
        breaks = [at for at, (name, _) in enumerate(sequence) if name in CLOCK_FILES]
        self.assertGreaterEqual(len(breaks), 2)
        for at in breaks:
            self.assertEqual(sequence[at][1], "card")
            if at + 1 < len(sequence):
                self.assertEqual(sequence[at + 1], (MESSAGE, "board"))

    def test_the_boards_faces_are_followed_by_the_cards_messages(self):
        source = board([ROOT, F1], folders="odrig-folders 1 2\n1 20 0 clocks\n", clocks=("between", True))
        card = {"a.odrg": CARD["a.odrg"], CARD_MESSAGE: CARD[CARD_MESSAGE]}
        run = session(source, at_times(*range(100, 60100, 250)), card=card)
        sequence = played(run)
        breaks = [at for at, (name, _) in enumerate(sequence) if name == "clocks/f1.odrg"]
        self.assertGreaterEqual(len(breaks), 2)
        for at in breaks:
            self.assertEqual(sequence[at][1], "board")
            if at + 1 < len(sequence):
                self.assertEqual(sequence[at + 1], (CARD_MESSAGE, "card"))

    def test_without_a_card_the_boards_faces_give_the_breaks_and_its_messages_follow(self):
        run = session(board(clocks=("between", True)), at_times(*range(100, 90100, 250)))
        sequence = [name for name, _ in played(run)]
        self.assertEqual(set(sequence), ORDINARY | FACES | {MESSAGE})
        for at, name in enumerate(sequence):
            if name in FACES and at + 1 < len(sequence):
                self.assertEqual(sequence[at + 1], MESSAGE)
            if name == MESSAGE:
                self.assertIn(sequence[at - 1], FACES)

    def test_with_the_message_off_a_break_is_its_clock_alone(self):
        run = session(board(clocks=("between", False)), at_times(*range(100, 90100, 250)))
        sequence = [name for name, _ in played(run)]
        self.assertEqual(set(sequence), ORDINARY | FACES)

    def test_messages_alone_give_no_break(self):
        source = board([ROOT, M1, ART], clocks=("between", True))
        run = session(source, at_times(*range(100, 60100, 500)), card={"a.odrg": CARD["a.odrg"], CARD_MESSAGE: CARD[CARD_MESSAGE]})
        self.assertEqual({name for name, _ in played(run)}, ORDINARY | {"a.odrg"})

    def test_the_root_and_a_folder_of_the_clocks_pass_over_the_boards_clocks_while_they_are_on(self):
        card = {"a.odrg": CARD["a.odrg"]}
        for folder, path in ((20, "clocks"), (21, "clocks/message"), (22, "clocks/old")):
            with self.subTest(folder=folder):
                run = session(board(clocks=("between", False)), asked(0, f"play {folder}") + at_times(*range(100, 15100, 500)), card=card)
                self.assertEqual(answers(run), [{"ok": True}])
                self.assertTrue(all((state["playing"], state["playlist"]) == (folder, path) for state in states_of(run)))
                self.assertEqual(set(files_of(run)), ORDINARY | {"a.odrg"})

    def test_while_the_clocks_are_off_the_boards_clocks_play_as_any_other_animation(self):
        run = session(board(), asked(0, "play 20") + at_times(*range(100, 30100, 500)), card={"a.odrg": CARD["a.odrg"]})
        self.assertEqual(set(files_of(run)), FACES | {MESSAGE, "clocks/old/old.odrg"})
        run = session(board(), at_times(*range(100, 40100, 500)))
        self.assertEqual(set(files_of(run)), ORDINARY | FACES | {MESSAGE, "clocks/old/old.odrg"})

    def test_the_rotation_passes_over_the_boards_clocks(self):
        times = [time for window in range(1, 6) for time in range(window * WINDOW + 20_000, window * WINDOW + 36_000, 500)]
        run = session(board(clocks=("between", False)), asked(20) + at_times(*times), card={})
        states = states_of(run)
        self.assertEqual(distinct([state["playing"] for state in states]), [23, 20, 21, 22, "all"])
        for state in states:
            if state["playing"] in (20, 21, 22):
                self.assertIn(state["file"], ORDINARY | FACES)

    def test_both_bags_go_through_both_storages_before_a_new_order(self):
        for mode in ("between", "only"):
            with self.subTest(mode=mode):
                run = session(board(clocks=(mode, True)), at_times(*range(100, 400100, 500)), card=CARD)
                sequence = played(run)
                faces = [entry for entry in sequence if entry[0] in FACES | CLOCK_FILES]
                if mode == "only":
                    # The start draws its clock before the card is taken up.
                    faces = faces[1:]
                messages = [entry for entry in sequence if entry[0] in (MESSAGE, CARD_MESSAGE)]
                every_face = {(name, "board") for name in FACES} | {(name, "card") for name in CLOCK_FILES}
                every_message = {(MESSAGE, "board"), (CARD_MESSAGE, "card")}
                self.assertGreaterEqual(len(faces), 10)
                self.assertGreaterEqual(len(messages), 10)
                for values, size, expected in ((faces, 5, every_face), (messages, 2, every_message)):
                    for at in range(0, len(values) - size + 1, size):
                        self.assertEqual(set(values[at:at + size]), expected)
                self.assertNotIn("clocks/old/old.odrg", {name for name, _ in sequence})

    def test_ignoring_the_boards_clock_of_a_break_goes_back_to_the_playlist(self):
        run = session(board(clocks=("between", False)), at_times(*range(100, 21000, 250)))
        before = [name for name, _ in played(run)]
        self.assertEqual(before[-2:], ["four.odrg", before[-1]])
        self.assertIn(before[-1], FACES)
        face = 11 if before[-1] == "clocks/f1.odrg" else 12
        run = session(board(clocks=("between", False)), at_times(*range(100, 21000, 250)) + asked(21000, f"ignore {face} 1", "status"))
        self.assertEqual(states_of(run)[-1]["file"], "art/art.odrg")

    def test_the_boards_clock_taken_back_in_while_nothing_plays_is_passed_over(self):
        for item in (11, 13):
            with self.subTest(item=item):
                script = asked(100, "ignore 1 1", "ignore 15 1", f"ignore {item} 1", f"ignore {item} 0", "status")
                script += at_times(*range(200, 12200, 500)) + asked(12300, "ignore 15 0", "status")
                run = session(board([ROOT, F1, M1, ART], clocks=("between", True)), script)
                states = states_of(run)
                self.assertEqual({(state["animation"], state["file"]) for state in states[:-1]}, {(None, None)})
                self.assertEqual(states[-1]["file"], "art/art.odrg")

    def test_a_message_longer_than_thirty_seconds_plays_its_whole_loop(self):
        from .test_message_clock import message_file
        from .test_mini import files_for
        source = files_for()
        show = json.loads(source["show.json"])
        show["min_seconds"] = 1
        show["items"] += [{"id": 11, "file": "1/c.odrgx"}, {"id": 13, "file": "2/long.odrgx"}]
        source.update({"show.json": json.dumps(show), "folders.txt": ONLY_CLOCKS, "clocks.txt": mode_file("between", True),
                       "1/c.odrgx": clock_of(canvas=(60, 60)), "2/long.odrgx": message_file([("words", 0)] * 9)})
        run = session(source, at_times(100, 5100, 7100, 40000, 61800, 62100))
        self.assertEqual(files_of(run), ["picture.odrg", "clocks/c.odrgx", "clocks/message/long.odrgx", "clocks/message/long.odrgx",
                                         "clocks/message/long.odrgx", "picture.odrg"])
        source["clocks.txt"] = mode_file("only", True)
        run = session(source, at_times(100, 2100, 32000, 56800, 57000))
        self.assertEqual(files_of(run), ["clocks/c.odrgx", "clocks/message/long.odrgx", "clocks/message/long.odrgx",
                                         "clocks/message/long.odrgx", "clocks/c.odrgx"])


class ClocksOnly(unittest.TestCase):
    def test_the_states_with_the_boards_clocks_folder(self):
        cases = (
            (board(clocks=("only", True)), None, {"folder": 20, "state": "playing"}),
            (board([ROOT, M1], folders=ONLY_CLOCKS, clocks=("only", True)), None, {"folder": 20, "state": "no-clocks"}),
            (board(folders=FOLDERS.replace("1 20 0 clocks", "1 20 1 clocks"), clocks=("only", True)), None, {"folder": 20, "state": "no-clocks"}),
            (board([ROOT, M1], folders=ONLY_CLOCKS, clocks=("only", True)), {"a.odrg": CARD["a.odrg"]}, {"folder": 20, "state": "no-clocks"}),
            (board(clocks=("only", True)), {"a.odrg": CARD["a.odrg"]}, {"folder": 20, "state": "playing"}),
            (board([ROOT], folders="odrig-folders 1 2\n1 20 0 clocks\n", clocks=("only", True)), CARD, {"folder": 60007, "state": "playing"}),
            (board(clocks=("only", True)), CARD, {"folder": 60007, "state": "playing"}),
        )
        for source, card, expected in cases:
            with self.subTest(expected=expected, card=card is not None):
                run = session(source, at_times(100, 20000), card=card)
                self.assertEqual([state["clock_only"] for state in states_of(run)], [expected] * 2)
                playing = expected["state"] == "playing"
                self.assertTrue(all((state["animation"] is not None) == playing for state in states_of(run)))
                if playing:
                    self.assertTrue(all((state["playing"], state["playlist"]) == (expected["folder"], "clocks") for state in states_of(run)))

    def test_the_boards_faces_play_while_the_card_is_out_and_beside_its_faces_once_it_is_in(self):
        script = at_times(*range(100, 15100, 500)) + ["drive pull"] + at_times(*range(15300, 40300, 500))
        script += ["drive plug"] + [f"poll {T0 + 40400 + 20 * n}" for n in range(1, 60)] + at_times(*range(41700, 140000, 500))
        with a_drive(CARD) as top:
            run = support.start(board(clocks=("only", False)), [f"poll {T0}", *script], ["--drive", top])
        states = states_of(run)
        middle = states[30:80]
        self.assertTrue(all(state["clock_only"] == {"folder": 20, "state": "playing"} for state in middle))
        self.assertTrue(all(state["file"] in FACES for state in middle))
        after = states[82:]
        self.assertTrue(all(state["clock_only"]["folder"] == 60007 for state in after))
        self.assertTrue({state["file"] for state in after} & CLOCK_FILES)
        self.assertTrue({state["file"] for state in after} & FACES)

    def test_play_inside_the_boards_clocks(self):
        source = board(folders=WITH_EMPTY, clocks=("only", False))
        script = asked(100, "ignore 12 1", "play 12", "status", "play 13", "status") + asked(120)
        script += at_times(1300)
        script += asked(8000, "play 21", "status", "play 22", "status") + asked(8020) + at_times(15000)
        script += asked(15100, "play 20", "status", "play 24", "status")
        run = session(source, script)
        self.assertEqual(answers(run), [{"ok": True}] * 7)
        files = files_of(run)
        self.assertEqual(files[:2], ["clocks/f2.odrg", MESSAGE])
        self.assertEqual(files[2], "clocks/f1.odrg")
        self.assertEqual(files[3:5], [MESSAGE, "clocks/old/old.odrg"])
        self.assertEqual(files[5], "clocks/f1.odrg")
        self.assertEqual(files[6:], ["clocks/f1.odrg"] * 2)
        self.assertTrue(all(state["clock_only"] == {"folder": 20, "state": "playing"} for state in states_of(run)))

    def test_play_outside_the_boards_clocks_is_refused_and_changes_nothing(self):
        source = board(clocks=("only", True), more={"1/bad.odrg": b"bad"},
                       items=[*ITEMS, {"id": 16, "file": "1/bad.odrg"}, {"id": 17, "cycle": [11], "seconds": 3}])
        run = session(source, asked(100, "status", "play 15", "play 23", "play 1", "play 17", "play all", "play 16", "status"))
        self.assertEqual(answers(run), [refusal("in-use")] * 5 + [refusal("unavailable")])
        first, last = states_of(run)
        self.assertEqual((first["file"], first["animation"]), (last["file"], last["animation"]))

    def test_a_removal_plays_the_next_face_and_the_last_one_darkens(self):
        run = session(board(clocks=("only", False)), asked(100, "play 11", "remove 11", "status") + at_times(120, 7000) +
                      asked(7100, "remove 12", "status") + at_times(7120))
        self.assertEqual(answers(run), [{"ok": True}] * 3)
        states = states_of(run)
        self.assertEqual([(state["file"], state["clock_only"]) for state in states[:3]],
                         [("clocks/f2.odrg", {"folder": 20, "state": "playing"})] * 3)
        self.assertEqual([(state["clock_only"], state["animation"]) for state in states[3:]],
                         [({"folder": 20, "state": "no-clocks"}, None)] * 2)

    def test_a_face_whose_length_is_not_known_yet_plays_and_a_fault_gives_way_to_the_next(self):
        run = session(board(clocks=("only", False)), at_times(*range(20, 13000, 500)), check_first=False)
        self.assertEqual(set(files_of(run)), FACES)
        self.assertEqual({state["unavailable"] for state in states_of(run)}, {0})
        broken = {"1/f2.odrg": FILES["1/f2.odrg"][:-3]}
        run = session(board(clocks=("only", False), **broken), at_times(*range(20, 13000, 500)), check_first=False)
        self.assertTrue(any("1/f2.odrg unavailable" in line for line in [*run.logs, *logged(run)]))
        self.assertEqual(files_of(run)[-1], "clocks/f1.odrg")
        self.assertTrue(all(state["clock_only"]["state"] == "playing" for state in states_of(run)))

    def test_the_last_face_at_fault_stays_dark(self):
        from .test_brightness import last_rgb
        broken = {"1/f1.odrg": FILES["1/f1.odrg"][:-3]}
        run = session(board([ROOT, F1, M1], folders=ONLY_CLOCKS, clocks=("only", True), **broken), at_times(20, 8000, 9000), check_first=False)
        self.assertEqual(states_of(run)[-1]["clock_only"], {"folder": 20, "state": "no-clocks"})
        self.assertIsNone(states_of(run)[-1]["animation"])
        self.assertFalse(any(last_rgb(run)))

    def test_leaving_only_plays_the_ordinary_playlist(self):
        run = session(board(clocks=("only", True)), at_times(100) + asked(200, "clocks on") + at_times(*range(300, 15300, 500)))
        self.assertIn(states_of(run)[0]["file"], FACES)
        self.assertEqual(set(files_of(run)[1:]), ORDINARY)
        self.assertTrue(all(state["clock_only"] is None and state["playlist"] is None for state in states_of(run)[1:]))


class OnlyAndIgnore(unittest.TestCase):
    def test_an_ignore_of_the_face_playing_ends_its_turn_at_once(self):
        run = session(board(clocks=("only", False)), at_times(100))
        face = states_of(run)[0]["animation"]
        other = 12 if face == 11 else 11
        run = session(board(clocks=("only", False)), at_times(100) + asked(120, f"ignore {face} 1", "status"))
        self.assertEqual(states_of(run)[-1]["animation"], other)

    def test_a_manual_turn_goes_on_through_its_own_ignore_and_a_fault_of_another_file(self):
        items = [ROOT, F1, F2, {"id": 16, "file": "bad.odrg"}]
        bad = support.clip(9, 3, 2, (1000,) * 200)[:-3]
        source = board(items, clocks=("only", False), **{"bad.odrg": bad})
        script = asked(20, "play 11", "ignore 11 1") + [f"poll {T0 + time}" for time in range(40, 3000, 20)] + at_times(3000, 5800)
        run = session(source, script, check_first=False)
        faulted = next(at for at, line in enumerate(run.lines) if "bad.odrg unavailable" in line)
        ignored = [at for at, line in enumerate(run.lines) if line.startswith("reply ")][1]
        self.assertGreater(faulted, ignored)
        self.assertEqual(files_of(run), ["clocks/f1.odrg"] * 2)

    def test_ignoring_the_boards_clocks_folder_darkens_only_and_taking_it_in_starts_a_clock(self):
        run = session(board(clocks=("only", True)), asked(100, "ignore 20 1", "status", "ignore 20 0", "status"))
        dark, lit = states_of(run)
        self.assertEqual((dark["clock_only"], dark["animation"]), ({"folder": 20, "state": "no-clocks"}, None))
        self.assertEqual(lit["clock_only"], {"folder": 20, "state": "playing"})
        self.assertIn(lit["file"], FACES)

    def test_the_leds_off_let_a_message_play_on_unseen(self):
        run = session(board([ROOT, F1, M1], folders=ONLY_CLOCKS, clocks=("only", True)), asked(100, "off") + at_times(*range(200, 9000, 250)))
        self.assertTrue(all(state["on"] is False for state in states_of(run)))
        self.assertEqual(distinct(files_of(run)), ["clocks/f1.odrg", MESSAGE, "clocks/f1.odrg"])


def copies_card(**more):
    return {**CARD, **more}


class Copies(unittest.TestCase):
    def test_a_copy_on_both_storages_plays_from_the_card(self):
        for same in (True, False):
            with self.subTest(same=same):
                items = [ROOT, {"id": 11, "file": "1/c1.odrg"}, F2, {"id": 13, "file": "2/m.odrg"}]
                files = {"1/c1.odrg": CARD["clocks/c1.odrg"] if same else loop_of(3, 31),
                         "2/m.odrg": CARD[CARD_MESSAGE] if same else loop_of(1, 32)}
                run = session(board(items, folders=ONLY_CLOCKS, clocks=("only", True), **files), at_times(*range(7500, 200100, 500)), card=CARD)
                sequence = played(run)
                self.assertNotIn(("clocks/c1.odrg", "board"), sequence)
                self.assertNotIn((CARD_MESSAGE, "board"), sequence)
                self.assertIn(("clocks/c1.odrg", "card"), sequence)
                self.assertIn(("clocks/f2.odrg", "board"), sequence)

    def test_a_card_copy_that_cannot_play_gives_its_turn_to_the_boards(self):
        items = [ROOT, {"id": 11, "file": "1/c1.odrg"}]
        source = board(items, folders=ONLY_CLOCKS, clocks=("only", False), **{"1/c1.odrg": CARD["clocks/c1.odrg"]})
        ignored = {**source, "ignored.txt": "odrig-ignored 1\nf clocks/c1.odrg\n"}
        held = {**source, "ignored.txt": "odrig-ignored 1\nd clocks\n"}
        cases = ((ignored, CARD), (held, CARD), (source, copies_card(**{"clocks/c1.odrg": b"bad"})),
                 (source, {name: data for name, data in CARD.items() if name != "clocks/c1.odrg"}))
        for files, card in cases:
            with self.subTest(case=cases.index((files, card))):
                run = session(files, at_times(*range(1000, 100000, 500)), card=card)
                self.assertIn(("clocks/c1.odrg", "board"), played(run))
                self.assertNotIn(("clocks/c1.odrg", "card"), played(run))

    def test_a_card_copy_pulled_out_gives_its_turn_to_the_boards(self):
        items = [ROOT, {"id": 11, "file": "1/c1.odrg"}]
        source = board(items, folders=ONLY_CLOCKS, clocks=("only", False), **{"1/c1.odrg": CARD["clocks/c1.odrg"]})
        card = {"clocks/c1.odrg": CARD["clocks/c1.odrg"]}
        run = session(source, at_times(*range(6500, 20100, 500)) + ["drive pull"] + at_times(*range(20300, 40300, 500)), card=card)
        self.assertEqual(played(run), [("clocks/c1.odrg", "card"), ("clocks/c1.odrg", "board")])

    def test_a_copy_on_a_card_with_a_catalog_plays_from_the_card(self):
        from .test_catalog_drive import card as with_catalog, polls
        items = [ROOT, {"id": 11, "file": "1/c1.odrg"}, F2]
        source = board(items, folders=ONLY_CLOCKS, clocks=("only", False), **{"1/c1.odrg": CARD["clocks/c1.odrg"]})
        files = with_catalog(CARD_FACES)
        with a_drive(files) as top:
            run = support.start(source, [f"poll {T0}", *polls(0, 400), *at_times(*range(8500, 100100, 500))], ["--drive", top])
        sequence = played(run)
        self.assertNotIn(("clocks/c1.odrg", "board"), sequence)
        self.assertIn(("clocks/c1.odrg", "card"), sequence)
        self.assertIn(("clocks/f2.odrg", "board"), sequence)

    def test_names_that_differ_in_case_are_copies(self):
        items = [ROOT, {"id": 11, "file": "1/c1.odrg"}, F2]
        source = board(items, folders=ONLY_CLOCKS, clocks=("only", False), **{"1/c1.odrg": loop_of(3, 31)})
        card = {"clocks/C1.ODRG": CARD["clocks/c1.odrg"]}
        sequence = played(session(source, at_times(*range(6500, 100100, 500)), card=card))
        self.assertNotIn(("clocks/c1.odrg", "board"), sequence)
        self.assertIn(("clocks/C1.ODRG", "card"), sequence)

    def test_the_same_name_in_another_folder_is_no_copy(self):
        items = [ROOT, {"id": 13, "file": "2/c1.odrg"}]
        source = board(items, folders=ONLY_CLOCKS, clocks=("only", True), **{"2/c1.odrg": CARD["clocks/c1.odrg"]})
        sequence = played(session(source, at_times(*range(100, 30100, 250)), card=CARD_FACES))
        self.assertIn(("clocks/message/c1.odrg", "board"), sequence)

    def test_the_same_name_with_another_type_is_no_copy(self):
        from .test_message_clock import message_file
        from .test_mini import files_for
        picture = files_for()["picture.odrg"]
        frames = odrgx.wrap(1, 60, 60, 1000, picture)
        for data, copy in ((frames, False), (message_file(), True)):
            with self.subTest(copy=copy):
                source = files_for()
                show = json.loads(source["show.json"])
                show["min_seconds"] = 1
                show["items"] += [{"id": 13, "file": "2/x.odrgx"}]
                source.update({"show.json": json.dumps(show), "folders.txt": ONLY_CLOCKS, "clocks.txt": mode_file("only", True), "2/x.odrgx": data})
                card = {"clocks/c.odrgx": clock_of(canvas=(60, 60)), "clocks/message/x.odrgx": message_file()}
                sequence = played(session(source, at_times(*range(100, 120100, 500)), card=card))
                self.assertEqual(("clocks/message/x.odrgx", "board") in sequence, not copy)
                self.assertIn(("clocks/message/x.odrgx", "card"), sequence)

    def test_a_show_of_more_than_132_items_keeps_its_marks(self):
        root = [{"id": 100 + n, "file": f"r{n}.odrg"} for n in range(140)]
        items = [*root, {"id": 11, "file": "1/c1.odrg"}, F2]
        source = board(items, folders=ONLY_CLOCKS, clocks=("only", False),
                       **{"1/c1.odrg": CARD["clocks/c1.odrg"]}, **{f"r{n}.odrg": loop_of(1, n % 200 + 1) for n in range(140)})
        sequence = played(session(source, at_times(*range(6500, 100100, 500)), card=CARD_FACES))
        self.assertNotIn(("clocks/c1.odrg", "board"), sequence)
        self.assertIn(("clocks/c1.odrg", "card"), sequence)
        self.assertIn(("clocks/f2.odrg", "board"), sequence)

    def test_each_copy_takes_its_own_saved_brightness(self):
        items = [ROOT, {"id": 11, "file": "1/c1.odrg"}]
        source = board(items, folders=ONLY_CLOCKS, clocks=("only", False), **{"1/c1.odrg": CARD["clocks/c1.odrg"]})
        source["brightness.txt"] = "odrig-brightness 1\n30 f 1/c1.odrg\n50 x clocks/c1.odrg\n"
        card = {"clocks/c1.odrg": CARD["clocks/c1.odrg"]}
        run = session(source, at_times(7000, 11000), card=card)
        self.assertEqual([(state["animation"] > 60000, state["dimming"]["saved"]) for state in states_of(run)], [(True, 50)] * 2)
        run = session({**source, "ignored.txt": "odrig-ignored 1\nf clocks/c1.odrg\n"}, at_times(7000, 11000), card=card)
        self.assertEqual([(state["animation"], state["dimming"]["saved"]) for state in states_of(run)], [(11, 30)] * 2)


def storage_file(mode, message, storage):
    """`clocks.txt` of version 3, with the preferred storage of copies."""
    return f"odrig-clocks 3\nmode {mode}\nmessage {'on' if message else 'off'}\nstorage {storage}\n"


def kept_session(source, script, card=None, options=(), check_first=True):
    """A session as `session` gives it, and the files the board's storage holds after it."""
    script = [f"poll {T0}", *script]
    if card is None:
        return support.start_and_keep(source, script, list(options), check_first=check_first)
    with a_drive(card) as top:
        return support.start_and_keep(source, script, ["--drive", top, *options], check_first=check_first)


def settings_of(run):
    """The mode, the message and the preferred storage each `status` of a session reports, with
    `clock_error` when it is there."""
    return [(state["clock_mode"], state["clock_message"], state["clock_storage"], state.get("clock_error")) for state in states_of(run)]


# A show whose board has a copy of the card's face `clocks/c1.odrg` and of its message, and
# a face of its own, `clocks/f2.odrg`.
COPY_ITEMS = [ROOT, {"id": 11, "file": "1/c1.odrg"}, F2, {"id": 13, "file": "2/m.odrg"}]
COPY_FILES = {"1/c1.odrg": CARD["clocks/c1.odrg"], "2/m.odrg": CARD[CARD_MESSAGE]}


def copies(mode="only", message=True, storage="internal", items=COPY_ITEMS, folders=ONLY_CLOCKS, **files):
    source = board(items, folders=folders, **{**COPY_FILES, **files})
    source["clocks.txt"] = storage_file(mode, message, storage) if storage == "internal" else mode_file(mode, message)
    return source


class ThePreferredStorage(unittest.TestCase):
    def test_each_refusal_comes_in_the_order_of_the_message_lines(self):
        run = support.start(support.with_show_fault(SHOW4), asked(100, "clocks storage x", "clocks storage internal", "clocks storage sd"), ["--no-storage"])
        self.assertEqual(answers(run), [refusal("bad-argument")] + [refusal("show-invalid")] * 2)
        run = support.start({**SHOW4, "clocks.txt": "bad"}, [support.line(T0, "clocks storage internal"), support.line(T0, "clocks storage sd")], check_first=False)
        self.assertEqual(replies(run), [refusal("busy")] * 2)
        script = asked(100, "upload begin 9 new.odrg 100", "clocks storage internal", "upload cancel", "catalog rebuild internal", "clocks storage internal")
        script += [f"poll {T0 + time}" for time in range(120, 5000, 20)]
        script += asked(5000, "catalog", "clocks storage internal", "clocks storage sd", "clocks on", "clocks storage internal", "status")
        run, kept = kept_session({**SHOW4, "clocks.txt": "bad"}, script)
        answered = answers(run)
        self.assertEqual(answered[0]["ok"], True)
        self.assertEqual(answered[5]["internal"]["state"], "ok")
        self.assertEqual(answered[1:5] + answered[6:], [refusal("busy"), DONE, DONE, refusal("busy")] + [refusal("storage-error")] * 2 + [DONE] * 2)
        self.assertEqual(settings_of(run), [("between", False, "internal", None)])
        self.assertEqual(kept["clocks.txt"], storage_file("between", False, "internal").encode())
        run = support.start({**SHOW4, "clocks.txt": storage_file("between", True, "internal")},
                            asked(100, "clocks storage sd", "clocks storage internal", "status"), ["--no-storage"])
        self.assertEqual(answers(run), [refusal("storage-error")] * 2)
        self.assertEqual(settings_of(run), [("off", False, "sd", None)])

    def test_a_choice_in_force_writes_nothing(self):
        from .test_clocks import clocks_file
        cases = ((SHOW4, "sd"), ({**SHOW4, "clocks.txt": clocks_file("on", "on")}, "sd"), ({**SHOW4, "clocks.txt": mode_file("only", True)}, "sd"),
                 ({**SHOW4, "clocks.txt": storage_file("between", True, "internal")}, "internal"),
                 ({**SHOW4, "clocks.txt": storage_file("off", False, "sd")}, "sd"))
        for source, storage in cases:
            with self.subTest(file=source.get("clocks.txt"), storage=storage):
                run, kept = kept_session(source, asked(100, f"clocks storage {storage}", "status"), options=["--trace-store"])
                self.assertEqual(answers(run), [DONE])
                self.assertEqual(states_of(run)[0]["clock_storage"], storage)
                self.assertFalse(any(line.startswith("store ") for line in run.lines))
                data = source.get("clocks.txt")
                self.assertEqual(kept.get("clocks.txt"), data.encode() if isinstance(data, str) else data)

    def test_internal_storage_writes_version_3_and_the_sd_card_version_2_byte_for_byte(self):
        source = {**SHOW4, "clocks.txt": mode_file("between", True)}
        run, kept = kept_session(source, asked(100, "status", "clocks storage internal", "status"))
        self.assertEqual(answers(run), [DONE])
        self.assertEqual(settings_of(run), [("between", True, "sd", None), ("between", True, "internal", None)])
        self.assertEqual(kept["clocks.txt"], storage_file("between", True, "internal").encode())
        run, kept = kept_session({**SHOW4, "clocks.txt": kept["clocks.txt"]}, asked(100, "status", "clocks only", "clocks message off", "status"))
        self.assertEqual(answers(run), [DONE] * 2)
        self.assertEqual(settings_of(run), [("between", True, "internal", None), ("only", False, "internal", None)])
        self.assertEqual(kept["clocks.txt"], storage_file("only", False, "internal").encode())
        self.assertEqual(len(storage_file("between", False, "internal")), 57)
        run, kept = kept_session({**SHOW4, "clocks.txt": kept["clocks.txt"]}, asked(100, "status", "clocks off", "clocks storage sd", "status"))
        self.assertEqual(settings_of(run), [("only", False, "internal", None), ("off", False, "sd", None)])
        self.assertEqual(kept["clocks.txt"], mode_file("off", False).encode())
        restarted = support.start({**SHOW4, "clocks.txt": kept["clocks.txt"]}, asked(0, "status"))
        self.assertEqual(settings_of(restarted), [("off", False, "sd", None)])

    def test_versions_1_2_and_3_are_read_strictly(self):
        from .test_clocks import clocks_file
        sound = ((clocks_file("on", "on"), ("between", True, "sd")), (mode_file("only", False), ("only", False, "sd")),
                 (storage_file("between", True, "sd"), ("between", True, "sd")), (storage_file("only", True, "internal"), ("only", True, "internal")),
                 (storage_file("off", False, "internal"), ("off", False, "internal")))
        for data, expected in sound:
            with self.subTest(data=data):
                run = support.start({**SHOW4, "clocks.txt": data}, asked(0, "status"))
                self.assertEqual(settings_of(run), [(*expected, None)])
                self.assertNotIn("clocks unreadable", logged(run))
        whole = storage_file("between", True, "internal")
        bad = ("odrig-clocks 3\nmode between\nmessage on\n", whole + "x", whole + "\n", whole[:-1], whole.replace("internal", "SD"), whole.replace("internal", "card"),
               whole.replace("\n", "\r\n"), whole.replace("storage internal", "storage  internal"), mode_file("between", True) + "storage internal\n",
               clocks_file("on", "on").decode() + "storage sd\n", "odrig-clocks 3\nmode between\nstorage internal\nmessage on\n",
               "odrig-clocks 3\nstorage internal\nmode between\nmessage on\n", whole.replace("odrig-clocks 3", "odrig-clocks 4"),
               "odrig-clocks 3\nclocks on\nmessage on\nstorage internal\n", whole + "storage internal\n")
        for data in bad:
            with self.subTest(data=data):
                run = support.start({**SHOW4, "clocks.txt": data}, asked(0, "status"))
                self.assertEqual(settings_of(run), [("only", False, "sd", "unreadable")])
                self.assertEqual(logged(run).count("clocks unreadable"), 1)
                self.assertEqual(list(states_of(run)[0])[-6:], ["clock_message", "clock_mode", "clock_storage", "clock_only", "clock_error", "left"])

    def test_a_failed_write_keeps_the_file_and_the_choice(self):
        for before, command, storage in ((mode_file("between", True), "clocks storage internal", "sd"),
                                         (storage_file("between", True, "internal"), "clocks storage sd", "internal")):
            files = {**SHOW4, "clocks.txt": before}
            script = [f"poll {T0}"] + asked(1000, command, "status")
            observed = support.start(files, script, ["--trace-store"])
            first = len(observed.stored) + 1
            calls = sum(line.startswith("store ") for line in observed.lines)
            self.assertEqual(calls, 4)
            for at in range(first, first + calls):
                with self.subTest(command=command, at=at):
                    run, kept = support.start_and_keep(files, script, ["--store-fails-at", str(at)])
                    self.assertEqual(answers(run), [refusal("storage-error")])
                    self.assertEqual(settings_of(run), [("between", True, storage, None)])
                    self.assertEqual(kept["clocks.txt"], before.encode())
                    self.assertNotIn("clocks.part", kept)
            with self.subTest(command=command, read_back=True):
                run, kept = support.start_and_keep(files, script, ["--command-read-fails", "clocks.part", "0"])
                self.assertEqual(answers(run), [refusal("storage-error")])
                self.assertEqual(settings_of(run), [("between", True, storage, None)])
                self.assertEqual(kept["clocks.txt"], before.encode())

    def test_a_version_3_found_by_the_retry_after_an_unreadable_start_gives_its_choice(self):
        source = {**SHOW4, "clocks.txt": storage_file("between", True, "internal")}
        script = asked(0, "status", "clocks storage internal") + at_times(*range(500, 6000, 500))
        run = support.start(source, [f"poll {T0}", *script], ["--read-at-fails-first", "clocks.txt", "3"])
        self.assertEqual(logged(run).count("clocks unreadable"), 1)
        settings = settings_of(run)
        self.assertEqual(settings[0], ("only", False, "sd", "unreadable"))
        self.assertEqual(answers(run), [refusal("storage-error")])
        self.assertEqual(settings[-1], ("between", True, "internal", None))
        self.assertEqual(settings[-1], settings[-2])

    def test_a_change_during_a_messages_turn_lets_it_play_its_whole_loop(self):
        source = copies(storage="sd")
        probe = session(source, at_times(*range(100, 30100, 100)), card=CARD)
        times = range(100, 30100, 100)
        message = next(time for time, state in zip(times, states_of(probe)) if state["file"] == CARD_MESSAGE)
        playing = states_of(probe)[times.index(message)]
        self.assertGreater(playing["animation"], 60000)
        whole = list(itertools.takewhile(lambda state: state["animation"] == playing["animation"], states_of(probe)[times.index(message):]))
        self.assertGreaterEqual(len(whole), 5)
        script = at_times(*range(100, message, 100)) + asked(message, "clocks storage internal", "status") + at_times(*range(message + 100, 120000, 100))
        run = session(source, script, card=CARD)
        states = states_of(run)
        at = len(range(100, message, 100))
        self.assertEqual(answers(run), [DONE])
        turn = list(itertools.takewhile(lambda state: state["animation"] == playing["animation"], states[at:]))
        self.assertEqual(len(turn), len(whole))
        self.assertTrue(all(state["file"] == CARD_MESSAGE and state["clock_storage"] == "internal" for state in turn))
        after = distinct([(state["file"], "board" if state["animation"] <= 60000 else "card") for state in states[at + len(turn):] if state["file"] is not None])
        self.assertIn((CARD_MESSAGE, "board"), after)
        self.assertNotIn((CARD_MESSAGE, "card"), after)
        self.assertNotIn(("clocks/c1.odrg", "card"), after)
        self.assertIn(("clocks/c1.odrg", "board"), after)

    def test_with_internal_storage_preferred_the_boards_copy_plays(self):
        for mode, same in (("only", True), ("only", False), ("between", True)):
            with self.subTest(mode=mode, same=same):
                files = {} if same else {"1/c1.odrg": loop_of(3, 31), "2/m.odrg": loop_of(1, 32)}
                times = range(7500, 200100, 500) if mode == "only" else range(100, 400100, 250)
                sequence = played(session(copies(mode, **files), at_times(*times), card=CARD))
                self.assertIn(("clocks/c1.odrg", "board"), sequence)
                self.assertIn((CARD_MESSAGE, "board"), sequence)
                self.assertNotIn(("clocks/c1.odrg", "card"), sequence)
                self.assertNotIn((CARD_MESSAGE, "card"), sequence)
                self.assertIn(("clocks/c2.odrg", "card"), sequence)
                self.assertIn(("clocks/f2.odrg", "board"), sequence)

    def test_a_boards_copy_that_cannot_play_gives_its_turn_to_the_cards(self):
        cases = (("ignored", copies(message=False), asked(100, "ignore 11 1")),
                 ("held", copies(message=False, folders=ONLY_CLOCKS.replace("1 20 0 clocks", "1 20 1 clocks")), []),
                 ("quarantined", copies(message=False, **{"1/c1.odrg": b"bad"}), []),
                 ("removed", copies(message=False), asked(100, "remove 11")))
        for name, source, script in cases:
            with self.subTest(case=name):
                sequence = played(session(source, script + at_times(*range(1000, 100000, 500)), card=CARD_FACES))
                self.assertIn(("clocks/c1.odrg", "card"), sequence)
                self.assertNotIn(("clocks/c1.odrg", "board"), sequence)

    def test_the_boards_copy_plays_on_through_a_card_pulled_out_and_put_in(self):
        source = copies(message=False, items=[ROOT, {"id": 11, "file": "1/c1.odrg"}])
        card = {"clocks/c1.odrg": CARD["clocks/c1.odrg"]}
        script = at_times(*range(6500, 20100, 500)) + ["drive pull"] + at_times(*range(20300, 40300, 500))
        script += ["drive plug"] + at_times(*range(40500, 80500, 500))
        run = session(source, script, card=card)
        self.assertEqual(played(run), [("clocks/c1.odrg", "board")])

    def test_the_copy_that_plays_takes_its_own_saved_brightness(self):
        source = copies(message=False, items=[ROOT, {"id": 11, "file": "1/c1.odrg"}])
        source["brightness.txt"] = "odrig-brightness 1\n30 f 1/c1.odrg\n50 x clocks/c1.odrg\n"
        card = {"clocks/c1.odrg": CARD["clocks/c1.odrg"]}
        run = session(source, at_times(7000, 11000), card=card)
        self.assertEqual([(state["animation"], state["dimming"]["saved"]) for state in states_of(run)], [(11, 30)] * 2)
        run = session(source, asked(100, "ignore 11 1") + at_times(7000, 11000), card=card)
        self.assertEqual([(state["animation"] > 60000, state["dimming"]["saved"]) for state in states_of(run)], [(True, 50)] * 2)


class FolderMovesAndRemovals(unittest.TestCase):
    """`move internal` and `folder remove` of the board's Clocks folders: the classes of their
    files and the state of Clocks only follow, as for a folder made at the new path."""

    def test_a_move_out_of_clocks_message_and_back_makes_its_files_messages_again(self):
        script = at_times(100) + asked(200, "move internal 21 messages") + at_times(*range(5000, 35000, 500))
        script += asked(35100, "move internal 21 clocks/message") + at_times(*range(35200, 70200, 500))
        run = session(board(clocks=("only", True)), script)
        answers = [reply for reply in replies(run) if "moved" in reply]
        self.assertEqual(answers, [{"ok": True, "id": 21, "moved": True}] * 2)
        states = states_of(run)
        out = [state["file"] for state in states[1:61]]
        back = [state["file"] for state in states[61:]]
        self.assertEqual(set(out) - {None}, FACES)
        self.assertIn(MESSAGE, back)

    def test_a_rename_of_clocks_leaves_clocks_only_without_the_boards_clocks_until_it_is_renamed_back(self):
        script = at_times(100) + asked(200, "move internal 20 faces") + at_times(5000) + asked(5100, "move internal 20 clocks") + at_times(5200, 12000)
        run = session(board(clocks=("only", True)), script)
        states = states_of(run)
        self.assertEqual(states[0]["clock_only"], {"folder": 20, "state": "playing"})
        self.assertEqual(states[1]["clock_only"], {"folder": None, "state": "no-card"})
        self.assertIsNone(states[1]["animation"])
        self.assertEqual(states[-1]["clock_only"], {"folder": 20, "state": "playing"})
        self.assertIn(states[-1]["file"], FACES | {MESSAGE})

    def test_an_empty_clocks_folder_of_the_board_is_removed_and_clocks_only_says_so(self):
        source = board([ROOT], folders="odrig-folders 1 3\n1 20 0 clocks\n2 21 0 clocks/message\n", clocks=("only", True))
        script = at_times(100) + asked(200, "folder remove 21") + at_times(300) + asked(400, "folder remove 20") + at_times(500)
        run = session(source, script)
        self.assertEqual([reply for reply in replies(run) if "on" not in reply], [DONE, DONE])
        self.assertEqual([state["clock_only"] for state in states_of(run)],
                         [{"folder": 20, "state": "no-clocks"}] * 2 + [{"folder": None, "state": "no-card"}])
