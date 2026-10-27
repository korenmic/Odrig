import json
import pathlib
import tempfile
import threading
import unittest

from odrig import catalog
from tests.core import support as core_support
from tests.emulator import support as emulator_support

from . import support
from .test_messages import refusal
from .test_target import entered
from .test_upload import begun, taken

OK = (200, '{"ok":true}\n')
MAPPING = core_support.mapping_texts()["legs-2"]
WITH_A_CANVAS = '{"ok":true,"on":true,"brightness":128,"playing":"all","animation":1,"fps":50,"error":null,"width":60,"height":6%s}\n'
CARD = {"present": True, "free": 3100000000, "total": 31900000000}


def space(read_only=False):
    """The reply to `space` of a target with two animations of its own and a card in it,
    which it may write unless `read_only`."""
    return (200, json.dumps({"ok": True, "free": 8372224, "total": 10354688, "animations": 2, "external": {**CARD, "read_only": read_only}}) + "\n")


def listed(*external):
    """The reply to `list` of the two animations of the board and these of the card, each
    `(id, file)` or `(id, file, fault)`."""
    items = [{"id": 1, "file": "one.odrg", "bytes": 1138, "ignored": False, "external": False},
             {"id": 2, "file": "two.odrg", "bytes": 1612, "ignored": False, "external": False}]
    for entry in external:
        item = {"id": entry[0], "file": entry[1], "bytes": 2000, "external": True}
        if len(entry) > 2:
            item.update(bytes=None, fault=entry[2])
        items.append(item)
    return (200, json.dumps({"ok": True, "items": items, "next": None}) + "\n")


class Catalogs:
    """A target with catalogs. `catalog` reports them and the rebuild under way, which has
    read `step` more animations at each `catalog` and ends when it has read them all, with
    a catalog of every one; `catalog rebuild <storage>` starts one and `catalog cancel`
    ends it, the catalog as it was. Its `status` says how far the rebuild is."""

    def __init__(self, internal, external, total=84, step=10):
        self.internal = internal
        self.external = external
        self.total = total
        self.step = step
        self.rebuild = None
        self.read = 0
        self.lock = threading.Lock()

    def catalog(self, line):
        words = line.decode("ascii").split(" ")
        with self.lock:
            if words[:2] == ["catalog", "page"]:
                # Its pages hold no line.
                part = self.internal if words[2] == "internal" else self.external
                generation = part["generation"] if part["state"] == "ok" else None
                return (200, json.dumps({"ok": True, "generation": generation, "text": "", "next": None}) + "\n")
            if words == ["catalog", "cancel"]:
                self.rebuild = None
                return OK
            if words[:2] == ["catalog", "rebuild"]:
                self.rebuild = words[2]
                self.read = 0
                return OK
            if self.rebuild is not None:
                self.read = min(self.total, self.read + self.step)
                if self.read == self.total:
                    done = {"state": "ok", "generation": 1, "entries": self.total}
                    if self.rebuild == "internal":
                        self.internal = {**done, "uncataloged": 0}
                    else:
                        self.external = {**done, "writable": True}
                    self.rebuild = None
            rebuild = None if self.rebuild is None else {"storage": self.rebuild, "read": self.read, "to_read": self.total - self.read}
            return (200, json.dumps({"ok": True, "internal": self.internal, "external": self.external, "rebuild": rebuild}) + "\n")

    def status(self, line):
        with self.lock:
            if self.rebuild is None:
                return (200, WITH_A_CANVAS % ',"readiness":"ready","checked":2,"to_check":0,"unavailable":0,"checking":null')
            return (200, WITH_A_CANVAS % (',"readiness":"checking","checked":%d,"to_check":%d,"unavailable":0,"checking":"x.odrg"' % (self.read, self.total - self.read)))

    def replies(self, read_only=False):
        return {"status": self.status, "list": listed((60001, "card.odrg")), "space": space(read_only), "catalog": self.catalog}


INTERNAL_OK = {"state": "ok", "generation": 42, "entries": 84, "uncataloged": 0}
EXTERNAL_OK = {"state": "ok", "generation": 7, "entries": 122, "writable": True}


class TheCatalogsOfSettings(unittest.TestCase):
    """Settings says what each catalog holds, and rebuilds one after a question, with its
    progress and a cancel, while the rest of the app goes on."""

    def sent(self, target, start):
        return [line for _, line in target.lines if line.startswith(start) and not line.startswith(b"catalog page ")]

    def test_each_catalog_is_said_and_a_rebuild_shows_its_progress_while_the_app_goes_on_and_can_be_cancelled(self):
        target = Catalogs(INTERNAL_OK, EXTERNAL_OK, step=5)
        with support.StandIn(target.replies()) as stand_in:
            found = support.run("catalogs", address=stand_in.address, settings={"rebuild": "Rebuild the board's catalog", "answer": "Rebuild", "visit": True, "cancel": True}).seen
            rebuilds = self.sent(stand_in, b"catalog ")
        self.assertEqual(found["first"], {"summary": None, "internal": "Board: 84 animations, cataloged.", "external": "Card: 122 animations, cataloged.", "note": None,
                                          "progress": None, "buttons": ["Rebuild the board's catalog", "Rebuild the card's catalog"]})
        self.assertEqual(found["question"], "Rebuild the catalog of the board? The installation reads every animation of the board whole, which takes a while; it plays on meanwhile.")
        self.assertEqual(found["asking"]["buttons"], ["Rebuild the board's catalog (disabled)", "Rebuild the card's catalog (disabled)", "Rebuild", "Not now"])
        self.assertRegex(found["progress"][0], r"^Rebuilding the catalog of the board: [0-9]+ of 84 animations read\.$")
        self.assertGreaterEqual(len(found["progress"]), 2)
        self.assertEqual(found["during"]["buttons"], ["Rebuild the board's catalog (disabled)", "Rebuild the card's catalog (disabled)", "Cancel the rebuild"])
        self.assertRegex(found["animations"]["readiness"], r"^Reading the animations: [0-9]+ read, [0-9]+ to read\.$")
        self.assertTrue(found["animations"]["pressable"])
        self.assertEqual(rebuilds, [b"catalog rebuild internal", b"catalog cancel"])
        self.assertEqual(found["after"], found["first"])

    def test_a_rebuild_that_reads_every_animation_ends_with_the_storage_cataloged(self):
        target = Catalogs({"state": "none", "uncataloged": 84}, {"state": "absent"}, step=30)
        with support.StandIn(target.replies()) as stand_in:
            found = support.run("catalogs", address=stand_in.address, settings={"rebuild": "Rebuild the board's catalog", "answer": "Rebuild"}).seen
        self.assertEqual((found["first"]["internal"], found["first"]["external"]), ("Board: not cataloged yet; its 84 animations are read whole at every start.", "Card: none in the installation."))
        self.assertEqual(found["first"]["buttons"], ["Rebuild the board's catalog"])
        self.assertEqual(found["progress"][:2], ["Rebuilding the catalog of the board: 30 of 84 animations read.", "Rebuilding the catalog of the board: 60 of 84 animations read."])
        self.assertEqual(found["after"]["internal"], "Board: 84 animations, cataloged.")

    def test_not_now_sends_nothing(self):
        target = Catalogs(INTERNAL_OK, EXTERNAL_OK)
        with support.StandIn(target.replies()) as stand_in:
            found = support.run("catalogs", address=stand_in.address, settings={"rebuild": "Rebuild the card's catalog", "answer": "Not now"}).seen
            rebuilds = self.sent(stand_in, b"catalog ")
        self.assertEqual(found["question"], "Rebuild the catalog of the card? The installation reads every animation of the card whole, which takes a while; it plays on meanwhile.")
        self.assertEqual(rebuilds, [])
        self.assertEqual(found["after"]["buttons"], ["Rebuild the board's catalog", "Rebuild the card's catalog"])

    def test_every_state_of_a_catalog_is_said_in_words(self):
        cases = [
            ({"state": "ok", "generation": 3, "entries": 1, "uncataloged": 2}, "Board: 1 animation, cataloged; 2 more not cataloged yet."),
            ({"state": "none", "uncataloged": 1}, "Board: not cataloged yet; its 1 animation is read whole at every start."),
            ({"state": "none", "uncataloged": 0}, "Board: not cataloged yet."),
            ({"state": "damaged", "detail": "page", "uncataloged": 84}, "Board: catalog damaged (a page); its animations are read whole at every start until a rebuild."),
            ({"state": "damaged", "uncataloged": 84}, "Board: catalog damaged; its animations are read whole at every start until a rebuild."),
            ({"state": "incompatible", "uncataloged": 84}, "Board: catalog of another version; its animations are read whole at every start until a rebuild."),
        ]
        externals = [
            ({"state": "loading", "generation": 7, "entries": 122, "writable": True}, "Card: reading its catalog."),
            ({"state": "none", "writable": True}, "Card: not cataloged yet; its animations are read whole each time it goes in."),
            ({"state": "damaged", "detail": "interrupted", "writable": False}, "Card: catalog damaged (a change was cut off); its animations play only after a rebuild."),
            ({"state": "incompatible", "writable": True}, "Card: catalog of another version; its animations play only after a rebuild."),
            ({"state": "absent"}, "Card: none in the installation."),
        ]
        for (internal, said), (external, card) in zip(cases, externals + [externals[-1]]):
            with self.subTest(internal=internal, external=external):
                target = Catalogs(internal, external)
                with support.StandIn(target.replies()) as stand_in:
                    found = support.run("catalogs", address=stand_in.address).seen
                self.assertEqual((found["first"]["internal"], found["first"]["external"]), (said, card))

    def test_a_card_the_installation_cannot_write_cannot_be_rebuilt_here(self):
        target = Catalogs(INTERNAL_OK, {"state": "none", "writable": False})
        with support.StandIn(target.replies(read_only=True)) as stand_in:
            found = support.run("catalogs", address=stand_in.address).seen
        self.assertEqual(found["first"]["note"], "The installation cannot write this card; a computer can make its catalog.")
        self.assertEqual(found["first"]["buttons"], ["Rebuild the board's catalog", "Rebuild the card's catalog (disabled)"])

    def test_a_refused_rebuild_is_said_in_words(self):
        target = Catalogs(INTERNAL_OK, EXTERNAL_OK)
        replies = target.replies()

        def refusing(line):
            return refusal("busy") if line.startswith(b"catalog rebuild") else target.catalog(line)

        replies["catalog"] = refusing
        with support.StandIn(replies) as stand_in:
            found = support.run("catalogs", address=stand_in.address, settings={"rebuild": "Rebuild the card's catalog", "answer": "Rebuild", "refused": True}).seen
        self.assertEqual(found["message"], "The installation is busy. Try again in a moment. (busy)")
        self.assertEqual(found["after"]["buttons"], ["Rebuild the board's catalog", "Rebuild the card's catalog"])
        self.assertIsNone(found["after"]["progress"])

    def test_a_target_that_keeps_no_catalogs_says_so_and_is_asked_once(self):
        with support.StandIn(support.SOUND) as stand_in:
            found = support.run("catalogs", address=stand_in.address, settings={"wait": 4500}).seen
            asked = [line for _, line in stand_in.lines if line.startswith(b"catalog")]
        self.assertEqual(found["after"], {"summary": "This installation's software keeps no catalogs.", "internal": None, "external": None, "note": None, "progress": None, "buttons": []})
        self.assertEqual(asked, [b"catalog"])

    def test_against_the_emulator_a_board_without_a_catalog_and_with_one(self):
        work = pathlib.Path(entered(self, tempfile.TemporaryDirectory()))
        items = [{"id": 1, "file": "a.odrg"}, {"id": 2, "file": "b.odrg"}]
        files = {"mapping.json": MAPPING, "show.json": json.dumps({"version": 1, "brightness": 128, "items": items}),
                 "a.odrg": core_support.clip(1, 60, 6, (20, 20)), "b.odrg": core_support.clip(2, 60, 6, (20, 20))}
        plain = emulator_support.installed(work / "plain", files)
        with emulator_support.Emulator(plain) as emulator:
            found = support.run("catalogs", address=f"127.0.0.1:{emulator.port}").seen
        self.assertEqual((found["first"]["internal"], found["first"]["external"]), ("Board: not cataloged yet; its 2 animations are read whole at every start.", "Card: none in the installation."))
        cataloged = emulator_support.installed(work / "cataloged", files)
        made, refused = catalog.rebuild(catalog.Storage(cataloged), names=["a.odrg", "b.odrg"], canvas=(60, 6))
        self.assertEqual(refused, [])
        with emulator_support.Emulator(cataloged) as emulator:
            found = support.run("catalogs", address=f"127.0.0.1:{emulator.port}").seen
        self.assertEqual(found["first"]["internal"], "Board: 2 animations, cataloged.")


class TheCard(unittest.TestCase):
    """While the installation may write its card, Upload stores a new animation on the card
    first, and a card's animation can be deleted from its row's menu; while it may not,
    both are as before."""

    @classmethod
    def setUpClass(cls):
        cls.work = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.work.cleanup)
        media = pathlib.Path(cls.work.name, "media")
        media.mkdir()
        cls.media = support.make_media(media)

    def target(self, read_only=False, **upload):
        def answer(line):
            word = line.split(b" ")[1].decode("ascii")
            reply = upload.get(word, OK)
            return reply(line) if callable(reply) else reply

        return {"status": (200, WITH_A_CANVAS % ""), "list": listed((60001, "card.odrg")), "space": space(read_only), "upload": answer}

    def uploaded(self, stand_in, **settings):
        return support.run("uploads", address=stand_in.address, settings={"rows": 3, "file": "clip.gif", **settings}, media=self.media).seen

    def uploads(self, stand_in):
        return [line for _, line in stand_in.lines if line.startswith(b"upload")]

    def test_a_new_animation_goes_to_a_card_that_can_be_written_first(self):
        ended = (200, '{"ok":true,"id":60002}\n')
        with support.StandIn(self.target(begin=begun, data=taken, end=ended)) as stand_in:
            found = self.uploaded(stand_in)
            lines = self.uploads(stand_in)
        self.assertEqual(found["store"], ["The card (chosen)", "This board"])
        self.assertEqual(found["cardSpace"], "External storage: free 3.1 GB of 31.9 GB.")
        self.assertRegex(lines[0].decode("ascii"), r"^upload begin external clip\.odrg [0-9]+$")
        self.assertRegex(lines[-1].decode("ascii"), r"^upload end [0-9a-f]{8}$")
        self.assertEqual(found["message"], "Uploaded to the card as animation 60002 clip.odrg. It plays in the playlist.")
        self.assertEqual(found["after"]["externalSpace"], "External storage: 1 animation, free 3.1 GB of 31.9 GB.")

    def test_this_board_can_be_chosen_instead(self):
        with support.StandIn(self.target(begin=begun, data=taken)) as stand_in:
            found = self.uploaded(stand_in, store="This board")
            lines = self.uploads(stand_in)
        self.assertRegex(lines[0].decode("ascii"), r"^upload begin 3 clip\.odrg [0-9]+$")
        self.assertEqual(found["message"], "Uploaded as animation 3 clip.odrg. It plays in the playlist.")

    def test_a_card_that_cannot_be_written_offers_no_choice(self):
        with support.StandIn(self.target(read_only=True, begin=begun, data=taken)) as stand_in:
            found = self.uploaded(stand_in)
            lines = self.uploads(stand_in)
        self.assertEqual((found["store"], found["cardSpace"]), (None, None))
        self.assertRegex(lines[0].decode("ascii"), r"^upload begin 3 clip\.odrg [0-9]+$")
        self.assertEqual(found["after"]["externalSpace"], "External storage: 1 animation, free 3.1 GB of 31.9 GB (read-only).")

    def test_each_refusal_of_an_upload_to_the_card_is_told_in_words(self):
        cases = (
            ({"begin": refusal("read-only")}, "The card cannot be written now. Choose This board to store the animation on the board. (read-only)"),
            ({"begin": refusal("no-space")}, r"The animation needs [0-9]+ KB, and the card has 3100000 KB free. (no-space)"),
            ({"begin": refusal("busy")}, "The installation is busy. Try again in a moment. (busy)"),
        )
        for replies, sentence in cases:
            with self.subTest(sentence=sentence):
                with support.StandIn(self.target(**replies)) as stand_in:
                    found = self.uploaded(stand_in)
                if "[0-9]" in sentence:
                    self.assertRegex(found["message"], "^" + sentence.replace("(", "\\(").replace(")", "\\)").replace(".", "\\.") + "$")
                else:
                    self.assertEqual(found["message"], sentence)

    def test_an_animation_of_a_card_that_can_be_written_can_be_deleted(self):
        replies = dict(self.target(), list=listed((60001, "card.odrg"), (60002, "bad.odrg", "truncated")), remove=OK)
        with support.StandIn(replies) as stand_in:
            found = support.run("card", address=stand_in.address, settings={"rows": 4, "id": 60001}).seen
            removed = [line for _, line in stand_in.lines if line.startswith(b"remove")]
            broken = support.run("card", address=stand_in.address, settings={"rows": 4, "id": 60002}).seen
        self.assertEqual([(row["badge"], row["described"]) for row in found["badges"]][2:], [("ex", "External storage"), ("ex", "External storage")])
        self.assertEqual(found["external"], "External storage: 2 animations, free 3.1 GB of 31.9 GB.")
        self.assertEqual(found["menu"][-1], "Delete")
        self.assertEqual(found["question"], "Remove animation 60001 card.odrg? Its file is deleted from the card.")
        self.assertEqual(found["message"], "Removed animation 60001 card.odrg.")
        self.assertEqual(removed, [b"remove 60001"])
        # A file of the card with a fault is deleted from its menu, not mended on a computer.
        self.assertIn("Unavailable: the file is damaged (truncated).", broken["text"])
        self.assertNotIn("Fix it on a computer", broken["text"])
        self.assertEqual(broken["menu"][-1], "Delete")

    def test_an_animation_of_a_card_that_cannot_be_written_has_no_delete(self):
        replies = dict(self.target(read_only=True), list=listed((60001, "card.odrg"), (60002, "bad.odrg", "truncated")))
        with support.StandIn(replies) as stand_in:
            found = support.run("card", address=stand_in.address, settings={"rows": 4, "id": 60002}).seen
            removed = [line for _, line in stand_in.lines if line.startswith(b"remove")]
        self.assertEqual(found["badges"][2]["described"], "External storage, read-only")
        self.assertEqual(found["menu"][-1], "External storage is read-only: this animation cannot be ignored or deleted from the app.")
        self.assertIn("Fix it on a computer: the card is read-only here.", found["text"])
        self.assertNotIn("question", found)
        self.assertEqual(removed, [])

    def test_a_refused_removal_from_the_card_is_said_in_words(self):
        replies = dict(self.target(), remove=refusal("read-only"))
        with support.StandIn(replies) as stand_in:
            found = support.run("card", address=stand_in.address, settings={"rows": 3, "id": 60001}).seen
        self.assertEqual(found["message"], "Animation 60001 cannot be removed: the card cannot be written now. (read-only)")


if __name__ == "__main__":
    unittest.main()
