"""The keys the app learns from the catalogs' pages: `catalog` at the first answer, after a
silence and after every complete list, the sixteen pages of each storage whose catalog is
`ok`, read again when the catalog changes, the keys kept meanwhile and dropped when they no
longer hold, and a target from before `catalog page` or before catalogs."""

import json
import pathlib
import tempfile
import threading
import time
import unittest
import zlib

from . import support
from .test_messages import refusal
from .test_target import entered

STATUS = (200, '{"ok":true,"on":true,"brightness":128,"playing":"all","animation":1,"fps":50,"error":null,"width":60,"height":60}\n')
NULL_PAGE = {"ok": True, "generation": None, "text": "", "next": None}


def files(prefix, count, seed):
    """Names, sizes and CRC-32s of made-up files."""
    return [(f"{prefix}{number:02d}.odrg", 1000 + 37 * number + seed, f"{zlib.crc32(f'{seed}-{number}'.encode()):08x}") for number in range(count)]


class Paged:
    """A target with two catalogs whose pages it gives `piece` bytes at a time. Each page
    answer can wait, be refused once with `busy`, or always while `busy_always` is set, be
    refused with a code, have a `null` generation, or come with the generation one more
    after `bump_after` pages. Its list names the card's folders of `folders` too."""

    def __init__(self, internal, external, piece=512):
        self.lock = threading.Lock()
        self.files = {"internal": list(internal), "external": list(external)}
        self.generation = {"internal": 3, "external": 5}
        self.state = {"internal": "ok", "external": "ok"}
        self.piece = piece
        self.delay = 0.0
        self.busy_once = set()
        self.busy_always = False
        self.folders = []
        self.refused_at = {}
        self.null_at = set()
        self.bump_after = None
        self.refuse_pages = False
        self.silent = False
        self.asked_pages = []

    def pages(self, storage):
        made = {}
        for number, (name, size, crc) in enumerate(self.files[storage]):
            made.setdefault(number % 16, []).append(f"{crc} {size} 60 60 1000 frames {name}\n")
        return {page: "".join(lines).encode("ascii") for page, lines in made.items()}

    def keys(self, storage):
        return {name: f"{crc}-{size}" for name, size, crc in self.files[storage]}

    def part(self, storage):
        if self.state[storage] != "ok":
            return {"state": self.state[storage], **({"uncataloged": 0} if storage == "internal" else {"writable": True})}
        more = {"uncataloged": 0} if storage == "internal" else {"writable": True}
        return {"state": "ok", "generation": self.generation[storage], "entries": len(self.files[storage]), **more}

    def catalog(self, line):
        words = line.decode("ascii").split(" ")
        if self.silent:
            return None
        if words[:2] != ["catalog", "page"]:
            with self.lock:
                return (200, json.dumps({"ok": True, "internal": self.part("internal"), "external": self.part("external"), "rebuild": None}) + "\n")
        time.sleep(self.delay)
        with self.lock:
            storage, page, offset = words[2], int(words[3]), int(words[4])
            self.asked_pages.append((time.monotonic(), storage, page, offset))
            if self.refuse_pages:
                return refusal("bad-argument")
            if self.busy_always:
                return refusal("busy")
            if (storage, page) in self.busy_once:
                self.busy_once.discard((storage, page))
                return refusal("busy")
            if (storage, page) in self.refused_at:
                return refusal(self.refused_at.pop((storage, page)))
            if (storage, page) in self.null_at or self.state[storage] != "ok":
                self.null_at.discard((storage, page))
                return (200, json.dumps(NULL_PAGE) + "\n")
            generation = self.generation[storage]
            if self.bump_after is not None and len(self.asked_pages) > self.bump_after:
                generation += 1
            content = self.pages(storage).get(page, b"")[offset:offset + self.piece]
            reply = {"ok": True, "generation": generation, "text": content.decode("ascii"), "next": offset + len(content) if content else None}
            return (200, json.dumps(reply) + "\n")

    def status(self, line):
        return None if self.silent else STATUS

    def listed(self, line):
        if self.silent:
            return None
        with self.lock:
            items = [{"id": number + 1, "file": name, "bytes": size, "ignored": False, "external": False} for number, (name, size, crc) in enumerate(self.files["internal"])]
            items += [{"id": 60001 + number, "file": name, "bytes": size, "external": True} for number, (name, size, crc) in enumerate(self.files["external"])]
            items += [{"id": 60501 + number, "playlist": folder, "external": True} for number, folder in enumerate(self.folders)]
        return (200, json.dumps({"ok": True, "items": items, "next": None}) + "\n")

    def space(self, line):
        return None if self.silent else (200, json.dumps({"ok": True, "free": 8372224, "total": 10354688, "animations": 20,
                                                          "external": {"present": True, "free": 3100000000, "total": 31900000000, "read_only": False}}) + "\n")

    def replies(self):
        return {"status": self.status, "list": self.listed, "space": self.space, "catalog": self.catalog, "play": lambda line: (200, '{"ok":true}\n')}


INTERNAL = files("file-", 20, 1)
EXTERNAL = [(f"night/{name}", size, crc) for name, size, crc in files("clip-", 10, 2)]


def sent(stand_in):
    return [line.decode("ascii") for _, line in stand_in.lines]


def page_lines(lines):
    return [line for line in lines if line.startswith("catalog page ")]


class Reading(unittest.TestCase):
    def test_both_storages_are_read_page_by_page_in_order_and_each_row_gets_its_key(self):
        target = Paged(INTERNAL, EXTERNAL, piece=40)
        with support.StandIn(target.replies()) as stand_in:
            seen = support.run("keys", address=stand_in.address, settings={"plan": [{"until": "both", "ms": 20000}, {"snap": "keys"}, {"sleep": 11000}, {"snap": "later"}]}).seen
            lines = sent(stand_in)
        self.assertEqual((seen["keys"]["internal"]["byName"], seen["keys"]["external"]["byName"]), (target.keys("internal"), target.keys("external")))
        self.assertEqual((seen["keys"]["internal"]["generation"], seen["keys"]["internal"]["entries"]), (3, 20))
        self.assertEqual((seen["keys"]["external"]["generation"], seen["keys"]["external"]["entries"]), (5, 10))
        wanted = {**target.keys("internal"), **target.keys("external")}
        self.assertEqual(dict(seen["keys"]["rowKeys"]), wanted)
        # `catalog` after the first list, then every page of the board, then the card's, in order.
        self.assertLess(lines.index("list 0"), lines.index("catalog"))
        asked = [tuple(line.split(" ")[2:]) for line in page_lines(lines)]
        self.assertEqual(asked, sorted(asked, key=lambda words: (words[0] != "internal", int(words[1]), int(words[2]))))
        self.assertEqual([words[1] for words in asked if words[0] == "internal" and words[2] == "0"], [str(page) for page in range(16)])
        self.assertEqual([words[1] for words in asked if words[0] == "external" and words[2] == "0"], [str(page) for page in range(16)])
        # The next list asks `catalog` again, and the same generation and entries read nothing more.
        self.assertGreaterEqual(lines.count("catalog"), 2)
        self.assertEqual(seen["later"]["version"], seen["keys"]["version"])
        self.assertEqual(len(page_lines(lines)), len(asked))

    def test_a_change_of_the_generation_or_the_entries_is_read_again_while_the_keys_stand_and_a_damaged_catalog_drops_them(self):
        target = Paged(INTERNAL, EXTERNAL)

        def new_generation():
            with target.lock:
                target.files["internal"][3] = ("file-03.odrg", 7777, "0badf00d")
                target.generation["internal"] = 4
                target.delay = 0.05

        def more_entries():
            with target.lock:
                target.files["internal"].append(("file-99.odrg", 4242, "12345678"))
                target.delay = 0.0

        def damaged():
            with target.lock:
                target.state["internal"] = "damaged"

        plan = [{"until": "both"}, {"snap": "before"}, {"step": True}, {"press": "Settings"}, {"untilCatalog": "internal", "generation": 4}, {"snap": "during"},
                {"untilKeys": "internal", "generation": 4, "ms": 15000}, {"snap": "after"}, {"step": True}, {"untilKeys": "internal", "entries": 21, "ms": 15000},
                {"snap": "more"}, {"step": True}, {"until": "no-internal"}, {"snap": "damaged"}]
        with support.StandIn(target.replies()) as stand_in:
            seen = support.run("keys", address=stand_in.address, settings={"plan": plan}, steps=[new_generation, more_entries, damaged]).seen
        self.assertEqual(seen["before"]["internal"]["byName"]["file-03.odrg"], f"{INTERNAL[3][2]}-{INTERNAL[3][1]}")
        self.assertEqual(seen["during"]["internal"]["generation"], 3, "the keys stand while the storage is read again")
        self.assertEqual(seen["after"]["internal"]["byName"]["file-03.odrg"], "0badf00d-7777")
        self.assertEqual(seen["more"]["internal"]["byName"]["file-99.odrg"], "12345678-4242")
        self.assertIsNone(seen["damaged"]["internal"])
        self.assertEqual(seen["damaged"]["external"], seen["before"]["external"])

    def test_a_page_of_another_generation_starts_the_read_again(self):
        target = Paged(INTERNAL, EXTERNAL)
        target.bump_after = 5
        with support.StandIn(target.replies()) as stand_in:
            seen = support.run("keys", address=stand_in.address, settings={"plan": [{"untilKeys": "internal", "generation": 4, "ms": 15000}, {"snap": "keys"}]}).seen
            lines = page_lines(sent(stand_in))
        # The sixth page's answer has another generation: the seventh request starts again.
        self.assertEqual(lines[0], "catalog page internal 0 0")
        self.assertNotIn("catalog page internal 0 0", lines[1:6])
        self.assertEqual(lines[6], "catalog page internal 0 0")
        self.assertEqual(seen["keys"]["internal"]["byName"], target.keys("internal"))

    def test_a_busy_page_is_asked_again_two_seconds_later(self):
        target = Paged(INTERNAL, EXTERNAL)
        target.busy_once = {("internal", 2)}
        with support.StandIn(target.replies()) as stand_in:
            seen = support.run("keys", address=stand_in.address, settings={"plan": [{"until": "both", "ms": 15000}, {"snap": "keys"}]}).seen
        asked = [(at, storage, page) for at, storage, page, offset in target.asked_pages if (storage, page, offset) == ("internal", 2, 0)]
        self.assertEqual(len(asked), 2)
        self.assertGreaterEqual(asked[1][0] - asked[0][0], 1.9)
        self.assertEqual(seen["keys"]["internal"]["byName"], target.keys("internal"))

    def test_a_null_generation_and_another_refusal_end_a_read_without_keys_and_say_nothing(self):
        target = Paged(INTERNAL, EXTERNAL)
        target.refused_at = {("internal", 7): "storage-error"}
        target.null_at = {("external", 1)}
        with support.StandIn(target.replies()) as stand_in:
            seen = support.run("keys", address=stand_in.address, settings={"plan": [{"sleep": 3000}, {"snap": "keys"}, {"say": "message", "id": "message-text"}]}).seen
            lines = page_lines(sent(stand_in))
        self.assertEqual((seen["keys"]["internal"], seen["keys"]["external"]), (None, None))
        self.assertNotIn("catalog page internal 8 0", lines)
        self.assertNotIn("catalog page external 2 0", lines)
        self.assertIn("catalog page external 1 0", lines)
        self.assertIsNone(seen["message"])


class AtOnce(unittest.TestCase):
    def test_the_lines_of_each_reply_give_their_rows_keys_and_previews_before_the_storage_is_read_whole(self):
        target = Paged(INTERNAL, EXTERNAL, piece=40)
        target.delay = 0.15
        early = {}

        def look():
            with target.lock:
                early["asked"] = [(storage, page) for _, storage, page, offset in target.asked_pages]

        work = pathlib.Path(entered(self, tempfile.TemporaryDirectory()))
        folder = work / "thumbnails"
        folder.mkdir()
        gif = next(support.THUMBNAILS.glob("*.gif")).read_bytes()
        shown = {name: f"{crc}-{size}" for name, size, crc in INTERNAL[:3]}
        entries = [f'  "{key}": {{"gif": "{key}.gif", "names": ["other-{number}.odrg"]}},' for number, key in enumerate(sorted(shown.values()))]
        (folder / "catalog.js").write_text("\n".join(["export default {", *entries, "};", ""]), encoding="ascii")
        for key in shown.values():
            (folder / f"{key}.gif").write_bytes(gif)
        plan = [{"until": "some-keys", "ms": 20000}, {"snap": "early"}, {"step": True}, {"until": "both", "ms": 40000}, {"snap": "all"}]
        with support.StandIn(target.replies()) as stand_in:
            seen = support.run("keys", address=stand_in.address, settings={"plan": plan}, steps=[look], thumbnails=folder).seen
        self.assertIsNone(seen["early"]["internal"], "the storage's keys wait for its last page")
        given = {name: key for name, key in seen["early"]["rowKeys"] if key is not None}
        self.assertTrue(given)
        self.assertEqual(given, {name: target.keys("internal")[name] for name in given})
        self.assertNotIn(("internal", 15), early["asked"], "keys before the last page was asked")
        for row in seen["early"]["squares"]:
            if row["file"] in given and row["file"] in shown:
                self.assertEqual(row["src"], f"thumbnails/{shown[row['file']]}.gif", row["file"])
            else:
                self.assertIsNone(row["src"], row["file"])
                self.assertEqual(row["background"], "rgb(0, 0, 0)", row["file"])
        self.assertEqual(dict(seen["all"]["rowKeys"]), {**target.keys("internal"), **target.keys("external")})


class OlderTargets(unittest.TestCase):
    def test_a_target_that_refuses_the_pages_is_asked_for_none_again_and_catalog_only_by_settings(self):
        target = Paged(INTERNAL, EXTERNAL)
        target.refuse_pages = True
        plan = [{"until": "pages-refused"}, {"sleep": 11000}, {"snap": "after"}, {"press": "Settings"}, {"sleep": 2500}, {"say": "message", "id": "message-text"}]
        with support.StandIn(target.replies()) as stand_in:
            seen = support.run("keys", address=stand_in.address, settings={"plan": plan}).seen
            lines = sent(stand_in)
        self.assertEqual(len(page_lines(lines)), 1)
        before_settings = lines[:max(at for at, line in enumerate(lines) if line == "list 0") + 1]
        self.assertEqual(before_settings.count("catalog"), 1)
        self.assertGreater(lines.count("catalog"), 1, "Settings still asks")
        self.assertEqual((seen["after"]["internal"], seen["after"]["external"]), (None, None))
        self.assertIsNone(seen["message"])

    def test_a_target_that_keeps_no_catalogs_is_asked_once_and_settings_says_so(self):
        with support.StandIn(support.SOUND) as stand_in:
            seen = support.run("keys", address=stand_in.address, settings={"plan": [{"until": "catalog-none"}, {"press": "Settings"}, {"sleep": 2500},
                                                                                    {"say": "summary", "id": "catalog-summary"}, {"press": "Animations"}, {"sleep": 11000}]}).seen
            lines = sent(stand_in)
        self.assertEqual(seen["summary"], "This installation's software keeps no catalogs.")
        self.assertEqual([line for line in lines if line.startswith("catalog")], ["catalog"])


class Dropped(unittest.TestCase):
    def test_the_keys_go_at_a_silence_and_at_another_target_and_come_back_kept_on_the_phone(self):
        target = Paged(INTERNAL, EXTERNAL)
        marks = []

        def quiet():
            target.silent = True

        def back():
            marks.append(len(stand_in.lines))
            target.silent = False

        with support.StandIn(target.replies()) as stand_in, support.StandIn(support.SOUND) as other:
            plan = [{"until": "both"}, {"snap": "before"}, {"step": True}, {"until": "no-answer", "ms": 15000}, {"step": True}, {"until": "answers", "ms": 15000},
                    {"snap": "again"}, {"until": "both", "ms": 15000}, {"snap": "read"}, {"address": other.address}, {"snap": "other"}]
            seen = support.run("keys", address=stand_in.address, settings={"plan": plan}, steps=[quiet, back]).seen
            after = sent(stand_in)[marks[0]:]
        self.assertIn("catalog", after)
        self.assertEqual(page_lines(after), [], "the kept keys come back with no page read")
        self.assertGreater(seen["again"]["version"], seen["before"]["version"])
        self.assertTrue(seen["again"]["internal"] is None or seen["again"]["version"] >= seen["before"]["version"] + 2)
        self.assertEqual(seen["read"]["internal"]["byName"], target.keys("internal"))
        self.assertEqual((seen["other"]["internal"], seen["other"]["external"]), (None, None))


class KeptOnThePhone(unittest.TestCase):
    def test_after_a_reload_the_keys_come_from_the_phone_and_no_page_is_asked(self):
        target = Paged(INTERNAL, EXTERNAL)
        marks = []

        def mark():
            marks.append(len(stand_in.lines))

        plan = [{"until": "both", "ms": 20000}, {"snap": "first"}, {"step": True}, {"reload": True}, {"until": "both", "ms": 20000}, {"sleep": 1500}, {"snap": "again"}]
        with support.StandIn(target.replies()) as stand_in:
            seen = support.run("keys", address=stand_in.address, settings={"plan": plan}, steps=[mark]).seen
            after = sent(stand_in)[marks[0]:]
        self.assertIn("catalog", after)
        self.assertEqual(page_lines(after), [])
        self.assertEqual(seen["again"]["internal"]["byName"], target.keys("internal"))
        self.assertEqual(seen["again"]["external"]["byName"], target.keys("external"))
        self.assertEqual(dict(seen["again"]["rowKeys"]), dict(seen["first"]["rowKeys"]))

    def test_a_new_generation_is_read_and_kept_and_the_next_start_reads_no_page(self):
        target = Paged(INTERNAL, EXTERNAL)
        marks = []

        def changed():
            with target.lock:
                target.files["internal"][3] = ("file-03.odrg", 7777, "0badf00d")
                target.generation["internal"] = 4
            marks.append(len(stand_in.lines))

        def mark():
            marks.append(len(stand_in.lines))

        plan = [{"until": "both", "ms": 20000}, {"step": True}, {"reload": True}, {"untilKeys": "internal", "generation": 4, "ms": 20000}, {"sleep": 500},
                {"step": True}, {"reload": True}, {"until": "both", "ms": 20000}, {"sleep": 1500}, {"snap": "last"}]
        with support.StandIn(target.replies()) as stand_in:
            seen = support.run("keys", address=stand_in.address, settings={"plan": plan}, steps=[changed, mark]).seen
            lines = sent(stand_in)
        read = page_lines(lines[marks[0]:marks[1]])
        self.assertTrue(read)
        self.assertEqual({line.split(" ")[2] for line in read}, {"internal"}, "the card's kept keys still hold")
        self.assertEqual(page_lines(lines[marks[1]:]), [])
        self.assertEqual(seen["last"]["internal"]["byName"]["file-03.odrg"], "0badf00d-7777")

    def test_loading_and_absent_keep_the_kept_keys_and_damaged_forgets_them(self):
        target = Paged(INTERNAL, EXTERNAL)
        marks = []

        def away():
            with target.lock:
                target.state["internal"] = "damaged"
                target.state["external"] = "absent"
            marks.append(len(stand_in.lines))

        def loading():
            with target.lock:
                target.state["internal"] = "ok"
                target.state["external"] = "loading"
            marks.append(len(stand_in.lines))

        def back():
            with target.lock:
                target.state["external"] = "ok"
            marks.append(len(stand_in.lines))

        plan = [{"until": "both", "ms": 20000}, {"step": True}, {"reload": True}, {"sleep": 2000}, {"step": True}, {"reload": True},
                {"untilKeys": "internal", "ms": 20000}, {"step": True}, {"reload": True}, {"until": "both", "ms": 20000}, {"sleep": 1500}, {"snap": "back"}]
        with support.StandIn(target.replies()) as stand_in:
            seen = support.run("keys", address=stand_in.address, settings={"plan": plan}, steps=[away, loading, back]).seen
            lines = sent(stand_in)
        # On a loaded computer the board's pages may still come after the card is back, so
        # they are looked for from the moment the board's catalog is whole again.
        while_ok_again = page_lines(lines[marks[1]:])
        self.assertTrue(while_ok_again, "the damaged catalog's keys were forgotten and read again")
        self.assertEqual({line.split(" ")[2] for line in while_ok_again}, {"internal"}, "absent and loading kept the card's keys")
        self.assertEqual(seen["back"]["external"]["byName"], target.keys("external"))

    def test_another_address_has_keys_of_its_own(self):
        first = Paged(INTERNAL, EXTERNAL)
        second = Paged(files("other-", 20, 7), [(f"night/{name}", size, crc) for name, size, crc in files("dusk-", 10, 8)])
        with support.StandIn(first.replies()) as one, support.StandIn(second.replies()) as two:
            plan = [{"until": "both", "ms": 20000}, {"address": two.address}, {"until": "both", "ms": 20000}, {"snap": "other"}]
            seen = support.run("keys", address=one.address, settings={"plan": plan}).seen
            asked = page_lines(sent(two))
        self.assertTrue(asked, "the second address reads its own pages")
        self.assertEqual(seen["other"]["internal"]["byName"], second.keys("internal"))
        self.assertEqual(seen["other"]["external"]["byName"], second.keys("external"))


class TheOperatorFirst(unittest.TestCase):
    def test_what_the_operator_asks_goes_out_between_two_pages(self):
        target = Paged(INTERNAL, EXTERNAL, piece=20)
        target.delay = 0.05
        with support.StandIn(target.replies()) as stand_in:
            support.run("keys", address=stand_in.address, settings={"plan": [{"sleep": 2500}, {"press": "Play this folder"}, {"until": "both", "ms": 30000}]})
            lines = sent(stand_in)
        played = lines.index("play all")
        self.assertTrue(page_lines(lines[:played]))
        self.assertTrue(page_lines(lines[played:]))


if __name__ == "__main__":
    unittest.main()
