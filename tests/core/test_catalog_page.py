"""`catalog page`: the lines of a page of the board's catalog or the card's, read with one
`read_at` a call, and what it answers for a storage without a catalog, during a rebuild,
on a host that cannot change its storage, and for a form it does not know."""

import json
import pathlib
import tempfile
import unittest

from odrig import catalog

from . import support
from .test_catalog_drive import card, polls
from .test_catalog_start import with_catalog
from .test_drive import SHOW, a_drive, asked, replies
from .test_playlist import loop_of, show_of

# A show of 120 animations with long names, so that a page holds more than one reply's
# worth of lines, cataloged by the PC library.
NAMES = [f"an-animation-of-the-show{number:03d}.odrg" for number in range(120)]
ITEMS = [{"id": number + 1, "file": name} for number, name in enumerate(NAMES)]
FILES = {name: loop_of(2, number) for number, name in enumerate(NAMES)}
CATALOGED = with_catalog(show_of(ITEMS, FILES, min_seconds=2))

# A card of 120 animations in folders, its lines longer than the board's.
CARD = {f"night/folder-{number % 3}/a-long-name-of-an-animation-on-the-card-{number:03d}.odrg": loop_of(2, 100 + number) for number in range(120)}

MOST = 4294967295


def pages(files, prefix=""):
    return {page: files.get(prefix + catalog.page_name(page), b"") for page in range(16)}


def page_replies(run):
    return [reply for reply in replies(run) if "text" in reply or reply.get("ok") is False]


def text_bytes(reply):
    """The bytes a reply's text stands for: every character, `\\u00XX` among them, as one byte."""
    return bytes(ord(character) for character in reply["text"])


class Pages(unittest.TestCase):
    def check_every_offset(self, content, found, offsets, generation):
        """Each reply gives the bytes of the page from its offset, `next` after them, and an
        empty text with `next` null at or after the page's end."""
        self.assertEqual(len(found), len(offsets))
        for offset, reply in zip(offsets, found):
            self.assertEqual(reply["ok"], True)
            self.assertEqual(reply["generation"], generation)
            given = text_bytes(reply)
            if offset >= len(content):
                self.assertEqual((given, reply["next"]), (b"", None), offset)
                continue
            self.assertGreater(len(given), 0, offset)
            self.assertLessEqual(len(given), 512)
            self.assertEqual(given, content[offset:offset + len(given)], offset)
            self.assertEqual(reply["next"], offset + len(given))

    def test_the_boards_pages_are_given_from_any_offset_and_their_lines_are_the_catalogs(self):
        contents = pages(CATALOGED)
        self.assertGreater(max(len(content) for content in contents.values()), 512)
        script = asked(0)
        offsets = {}
        for page, content in contents.items():
            offsets[page] = sorted(set(range(0, len(content) + 2, 1 if page < 2 else 97)) | {len(content), len(content) + 5, MOST})
            script += asked(20, *(f"catalog page internal {page} {offset}" for offset in offsets[page]))
        run = support.start(CATALOGED, script, check_first=False)
        found = page_replies(run)
        at = 0
        for page, content in contents.items():
            self.check_every_offset(content, found[at:at + len(offsets[page])], offsets[page], 1)
            at += len(offsets[page])
        lines = b"".join(contents.values()).decode("ascii").splitlines()
        self.assertEqual(sorted(line.split(" ", 6)[6] for line in lines), sorted(NAMES))

    def test_read_whole_page_by_page_the_lines_give_every_key(self):
        """Reading on from each `next`, as the app does, gives each page whole; the key of
        each line is the CRC-32 and the size of its file."""
        contents = pages(CATALOGED)
        for page in (0, 5, 15):
            content = contents[page]
            read = b""
            offset = 0
            for _ in range(40):
                run = support.start(CATALOGED, asked(0, f"catalog page internal {page} {offset}"), check_first=False)
                reply = page_replies(run)[0]
                read += text_bytes(reply)
                if reply["next"] is None:
                    break
                offset = reply["next"]
            self.assertEqual(read, content)
            for line in content.decode("ascii").splitlines():
                crc, size, *rest = line.split(" ", 6)
                name = rest[-1]
                self.assertEqual((int(crc, 16), int(size)), (catalog.crc(FILES[name]), len(FILES[name])))

    def test_the_cards_pages_are_given_through_its_folder_and_its_generation(self):
        files = card(CARD)
        contents = pages(files)
        self.assertGreater(max(len(content) for content in contents.values()), 1024)
        script = polls(0, 400)
        offsets = {}
        for page, content in contents.items():
            offsets[page] = sorted(set(range(0, len(content) + 1, 131)) | {len(content), MOST})
            script += asked(8000, *(f"catalog page external {page} {offset}" for offset in offsets[page]))
        with a_drive(files) as top:
            run = support.start(SHOW, script, ["--drive", top], check_first=False)
        found = page_replies(run)
        at = 0
        for page, content in contents.items():
            self.check_every_offset(content, found[at:at + len(offsets[page])], offsets[page], 1)
            at += len(offsets[page])
        names = [line.split(" ", 6)[6] for content in contents.values() for line in content.decode("ascii").splitlines()]
        self.assertEqual(sorted(names), sorted(CARD))

    def test_each_call_reads_once_and_asks_for_no_memory(self):
        script = asked(0) + asked(20, *(f"catalog page internal {page} 0" for page in range(16)))
        run = support.start(CATALOGED, script, ["--trace-read-at", "--trace-calls"], check_first=False)
        reads = [line for line in run.lines if line.startswith("read_at catalog-")]
        self.assertEqual(len(reads), 16)
        self.assertEqual([line.split(" ")[1] for line in reads], [catalog.page_name(page) for page in range(16)])
        self.assertTrue(all(int(line.split(" ")[3]) <= 512 for line in reads))

    def test_a_page_without_entries_is_an_empty_text_with_the_generation(self):
        files = with_catalog(show_of([{"id": 1, "file": "one.odrg"}], {"one.odrg": loop_of(2, 1)}, min_seconds=2))
        empty = [page for page in range(16) if catalog.page_name(page) not in files]
        self.assertTrue(empty)
        run = support.start(files, asked(0, f"catalog page internal {empty[0]} 0"), check_first=False)
        self.assertEqual(page_replies(run), [{"ok": True, "generation": 1, "text": "", "next": None}])


class WithoutAnOkCatalog(unittest.TestCase):
    NULL = {"ok": True, "generation": None, "text": "", "next": None}

    def test_a_storage_without_a_catalog_and_a_card_that_is_out_answer_null(self):
        files = show_of([{"id": 1, "file": "one.odrg"}], {"one.odrg": loop_of(2, 1)}, min_seconds=2)
        run = support.start(files, asked(0, "catalog page internal 0 0", "catalog page external 3 0"), check_first=False)
        self.assertEqual(page_replies(run), [self.NULL, self.NULL])

    def test_a_damaged_catalog_answers_null(self):
        files = dict(CATALOGED)
        files[catalog.page_name(0)] = files[catalog.page_name(0)][:-5]
        run = support.start(files, asked(0, "catalog", "catalog page internal 0 0"), check_first=False)
        self.assertEqual(replies(run)[0]["internal"]["state"], "damaged")
        self.assertEqual(page_replies(run), [self.NULL])

    def test_a_card_without_a_catalog_answers_null(self):
        with a_drive({"a.odrg": loop_of(2, 5)}) as top:
            run = support.start(SHOW, polls(0, 100) + asked(4000, "catalog page external 0 0"), ["--drive", top], check_first=False)
        self.assertEqual(page_replies(run), [self.NULL])


class Refusals(unittest.TestCase):
    def test_a_rebuild_of_that_storage_makes_it_busy_and_nothing_else_does(self):
        script = asked(0, "catalog rebuild internal", "catalog page internal 0 0", "catalog page external 0 0", "catalog cancel",
                       "upload begin 99 new.odrg 1000", "catalog page internal 0 0")
        run = support.start(CATALOGED, script, check_first=False)
        found = replies(run)
        self.assertEqual(found[0], {"ok": True})
        self.assertEqual(found[1], {"ok": False, "error": "busy"})
        self.assertEqual(found[2], WithoutAnOkCatalog.NULL)
        self.assertEqual(found[4]["ok"], True)
        self.assertEqual(found[5]["generation"], 1)
        self.assertTrue(found[5]["text"])

    def test_a_host_that_cannot_change_its_storage_answers_storage_error(self):
        run = support.start(CATALOGED, asked(0, "catalog page internal 0 0", "catalog page external 0 0"), ["--no-storage"], check_first=False)
        self.assertEqual(page_replies(run), [{"ok": False, "error": "storage-error"}] * 2)

    def test_every_other_form_is_a_bad_argument(self):
        forms = ["catalog page", "catalog page internal", "catalog page internal 0", "catalog page internal 16 0", "catalog page internal 0 4294967296",
                 "catalog page internal a 0", "catalog page internal 0 -1", "catalog page both 0 0", "catalog page internal 0 0 0", "catalog pages internal 0 0",
                 "catalog page Internal 0 0"]
        run = support.start(CATALOGED, asked(0, *forms), check_first=False)
        self.assertEqual(replies(run), [{"ok": False, "error": "bad-argument"}] * len(forms))
        run = support.start(CATALOGED, asked(0, "catalog page internal 15 4294967295", "catalog page external 0 0"), check_first=False)
        self.assertEqual([reply["ok"] for reply in replies(run)], [True, True])


class Escaping(unittest.TestCase):
    def test_bytes_a_json_string_cannot_hold_are_escaped_and_the_text_stops_where_the_reply_ends(self):
        """A page that is changed behind the core's back is given as its bytes are: a quote, a
        backslash, a line end, and bytes outside printable ASCII each escaped, as many as
        fit into one reply, `next` counting the bytes given."""
        files = card(CARD)
        page = next(page for page in range(16) if catalog.page_name(page) in files)
        odd = bytes(range(256)) * 2 + b'"\\\n' * 40
        with a_drive(files) as top, tempfile.TemporaryDirectory() as other:
            changed = pathlib.Path(other, "odrig")
            changed.mkdir()
            for name, content in files.items():
                path = changed.joinpath(*name.split("/"))
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(odd if name == catalog.page_name(page) else content)
            offsets = list(range(0, len(odd) + 1, 37))
            script = polls(0, 400) + [f"drive replace {other}"] + asked(8000, *(f"catalog page external {page} {offset}" for offset in offsets))
            run = support.start(SHOW, script, ["--drive", top], check_first=False)
        lines = [line for line in run.lines if line.startswith("reply ")]
        found = page_replies(run)
        self.assertEqual(len(found), len(offsets))
        self.assertTrue(all(len(line) - len("reply ") + 1 <= 1024 for line in lines))
        shorter = 0
        for offset, reply in zip(offsets, found):
            given = text_bytes(reply)
            if offset >= len(odd):
                self.assertEqual((given, reply["next"]), (b"", None))
                continue
            self.assertEqual(given, odd[offset:offset + len(given)], offset)
            self.assertEqual(reply["next"], offset + len(given))
            shorter += 1 if len(given) < min(512, len(odd) - offset) else 0
        self.assertGreater(shorter, 0)
        raw = [line[len("reply "):] for line in lines if '"text"' in line]
        self.assertTrue(any('\\"' in line and "\\\\" in line and "\\n" in line and "\\u00ff" in line for line in raw))


if __name__ == "__main__":
    unittest.main()
