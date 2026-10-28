import json
import pathlib
import tempfile
import unittest

from tests.core import support as core_support
from tests.emulator import support as emulator_support

from . import support
from .test_target import entered

MAPPING = core_support.mapping_texts()["legs-2"]
HINT = "Hold a row to move it, or use Move up and Move down in its menu."


class TheSavedOrder(unittest.TestCase):
    def folder(self, count=4, order=None, drive=None):
        work = pathlib.Path(entered(self, tempfile.TemporaryDirectory()))
        items = [{"id": number, "file": "a.odrg"} for number in range(1, count + 1)]
        files = {"mapping.json": MAPPING, "show.json": json.dumps({"version": 1, "brightness": 32, "items": items}), "a.odrg": core_support.clip(1, 60, 6)}
        if order is not None:
            files["order.txt"] = "odrig-order 1\n" + "".join(f"{entry}\n" for entry in order)
        folder = emulator_support.installed(work / "show", files)
        options = ()
        if drive is not None:
            emulator_support.installed(work / "card" / "odrig", {name: core_support.clip(7, 60, 6) for name in drive})
            options = ("--drive", str(work / "card"))
        return folder, options

    def emulator(self, count=4, order=None, drive=None):
        folder, options = self.folder(count, order, drive)
        started = entered(self, emulator_support.Emulator(folder, *options))
        return started, folder

    def order_of(self, emulator):
        return json.loads(emulator.command("order get"))["ids"]

    def test_the_rows_stand_in_the_saved_order_and_the_cards_after_them(self):
        # The line that names a file of the card is passed over: the card's files follow the
        # show's animations in the order of their names.
        emulator, _ = self.emulator(3, ["x b.odrg", "i 3", "i 1"], drive=["a.odrg", "b.odrg"])
        found = support.run("order", address=f"127.0.0.1:{emulator.port}", settings={"rows": 5}).seen
        self.assertEqual(found["first"], [3, 1, 2, 60001, 60002])
        self.assertEqual(found["first"], self.order_of(emulator))
        self.assertEqual(found["note"], HINT)

    def test_a_row_dragged_by_a_finger_is_saved_where_it_was_let_go(self):
        emulator, folder = self.emulator()
        settings = {"rows": 4, "drag": {"id": 4, "before": 2, "kind": "touch", "expected": [1, 4, 2, 3]}}
        found = support.run("order", address=f"127.0.0.1:{emulator.port}", settings=settings).seen
        self.assertTrue(found["lifted"])
        self.assertTrue(found["placeholder"])
        self.assertEqual(found["saving"], "Saving…")
        self.assertEqual(found["after"], [1, 4, 2, 3])
        self.assertEqual(self.order_of(emulator), [1, 4, 2, 3])
        self.assertEqual((folder / "order.txt").read_text(), "odrig-order 1\ni 1\ni 4\ni 2\ni 3\n")
        # Letting go of a dragged row plays nothing.
        self.assertNotEqual(found["played"], 4)

    def test_a_mouse_drags_as_a_finger_does(self):
        emulator, _ = self.emulator()
        settings = {"rows": 4, "drag": {"id": 1, "before": 4, "kind": "mouse", "expected": [2, 3, 1, 4]}}
        found = support.run("order", address=f"127.0.0.1:{emulator.port}", settings=settings).seen
        self.assertEqual(found["after"], [2, 3, 1, 4])
        self.assertEqual(self.order_of(emulator), [2, 3, 1, 4])

    def test_in_a_long_list_the_page_scrolls_while_a_row_is_held_near_the_tabs(self):
        emulator, _ = self.emulator(40)
        found = support.run("order", address=f"127.0.0.1:{emulator.port}", settings={"rows": 40, "toEnd": True, "kind": "touch"}).seen
        self.assertGreater(found["scrolled"], 200)
        self.assertEqual(found["after"], list(range(2, 41)) + [1])
        self.assertEqual(self.order_of(emulator), list(range(2, 41)) + [1])

    def test_a_drag_let_go_where_it_began_or_cancelled_moves_nothing(self):
        emulator, folder = self.emulator()
        with emulator_support.EventStream(emulator.port) as stream:
            found = support.run("order", address=f"127.0.0.1:{emulator.port}", settings={"rows": 4, "back": True, "cancel": True}).seen
            events = stream.read_for(1)
        self.assertTrue(found["unmoved"])
        self.assertTrue(found["cancelled"])
        self.assertEqual([entry["line"] for entry in emulator_support.of_kind(events, "log") if entry["line"].startswith("order move")], [])
        self.assertFalse((folder / "order.txt").exists())

    def test_move_up_and_move_down_in_the_menu(self):
        emulator, _ = self.emulator()
        found = support.run("order", address=f"127.0.0.1:{emulator.port}", settings={"rows": 4, "menu": [3, "Move up", [1, 3, 2, 4]]}).seen
        self.assertEqual(found["menu"], ["Ignore in playlist", "Move up", "Move down", "Select", "Delete"])
        self.assertEqual(found["after"], [1, 3, 2, 4])
        found = support.run("order", address=f"127.0.0.1:{emulator.port}", settings={"rows": 4, "menu": [1, "Move down", [3, 1, 2, 4]]}).seen
        self.assertEqual(found["after"], [3, 1, 2, 4])
        found = support.run("order", address=f"127.0.0.1:{emulator.port}", settings={"rows": 4, "menu": [2, "Move down", [3, 1, 4, 2]]}).seen
        self.assertEqual(found["after"], [3, 1, 4, 2])
        self.assertEqual(self.order_of(emulator), [3, 1, 4, 2])

    def test_the_first_row_cannot_move_up_nor_the_last_down(self):
        emulator, _ = self.emulator(2, drive=["c.odrg"])
        found = support.run("order", address=f"127.0.0.1:{emulator.port}", settings={"rows": 3, "look": 60001}).seen
        self.assertEqual(found["menu"], ["Move up", "Move down (disabled)", "External storage is read-only: this animation cannot be ignored or deleted from the app."])
        found = support.run("order", address=f"127.0.0.1:{emulator.port}", settings={"rows": 3, "menu": [2, "Move up", [2, 1, 60001]]}).seen
        self.assertEqual(self.order_of(emulator), [2, 1, 60001])
        found = support.run("order", address=f"127.0.0.1:{emulator.port}", settings={"rows": 3, "older": True}).seen
        self.assertEqual(found["menu"][1:3], ["Move up (disabled)", "Move down"])

    def test_a_conflict_a_refusal_and_a_lost_reply_are_said_and_read_again_without_a_second_move(self):
        emulator, _ = self.emulator()
        for reply, said in (('{"ok":false,"error":"order-conflict"}', "The order changed on the installation since the app read it. The list is read again; move the animation again. (order-conflict)"),
                            ('{"ok":false,"error":"busy"}', "The installation is busy. Try again in a moment. (busy)"),
                            ("", "The order is read again before another move.")):
            with self.subTest(reply=reply):
                moves = []

                def forward(line):
                    if line.startswith(b"order move"):
                        moves.append(line)
                        return 200, reply
                    return 200, emulator.command(line.decode())
                with support.StandIn({word: forward for word in ("status", "list", "space", "order")}) as target:
                    found = support.run("order", address=target.address, settings={"rows": 4, "refused": True}).seen
                self.assertEqual(len(moves), 1)
                self.assertEqual(found["saving"], "Saving…")
                self.assertIn(said, found["message"])
                self.assertEqual(found["after"], [1, 2, 3, 4])
        self.assertEqual(self.order_of(emulator), [1, 2, 3, 4])

    def test_an_older_target_without_an_order_keeps_the_list_in_its_order_and_moves_nothing(self):
        listed = {"ok": True, "items": [{"id": number, "file": f"{number}.odrg", "bytes": 1000, "ignored": False} for number in (3, 1, 2)], "next": None}
        replies = {"status": support.PLAYING, "list": (200, json.dumps(listed)), "space": (200, '{"ok":true,"free":8372224,"total":10354688,"animations":3}')}
        with support.StandIn(replies) as target:
            found = support.run("order", address=target.address, settings={"rows": 3, "older": True}).seen
            lines = [line for _, line in target.lines]
        self.assertEqual(found["first"], [3, 1, 2])
        self.assertEqual(found["note"], "This installation's software keeps no order of its own: the list is in the order of its show.")
        self.assertEqual(found["menu"], ["Ignore in playlist", "Move up (disabled)", "Move down (disabled)", "Select", "Delete"])
        self.assertEqual([line for line in lines if line.startswith(b"order move")], [])

    def test_while_selecting_dragging_and_moving_are_off_and_say_why(self):
        emulator, _ = self.emulator()
        found = support.run("order", address=f"127.0.0.1:{emulator.port}", settings={"rows": 4, "blocked": True}).seen
        self.assertEqual(found["selecting"]["note"], "Leave the selection with Done to move animations.")
        self.assertIn("Move up (disabled)", found["selecting"]["menu"])
        self.assertFalse(found["selecting"]["lifted"])
        self.assertEqual(found["done"], HINT)

    def test_a_move_of_another_controller_appears(self):
        emulator, _ = self.emulator()

        def other():
            revision = json.loads(emulator.command("order get"))["revision"]
            self.assertEqual(json.loads(emulator.command(f"order move {revision} 4 1")), {"ok": True})
        found = support.run("order", address=f"127.0.0.1:{emulator.port}", settings={"rows": 4, "other": [4, 1, 2, 3]}, steps=[other]).seen
        self.assertEqual(found["after"], [4, 1, 2, 3])


if __name__ == "__main__":
    unittest.main()
