import json
import pathlib
import tempfile
import time
import unittest

from tests.core import support as core_support
from tests.core.support import BOARD_STORAGE, STORAGE_BLOCK, ReferencePlayer

from . import support


def over_serial(emulator, line):
    with support.lines(emulator) as port:
        return port.ask(line)


def over_http(emulator, line):
    return emulator.command(line)


ROUTES = {support.LINES: over_serial, "http": over_http}


class Space(unittest.TestCase):
    def setUp(self):
        self.folder = pathlib.Path(support.entered(self, support.example_show()))

    def started(self, *options):
        return support.entered(self, support.Emulator(self.folder, *options))

    def test_space_gives_the_reply_of_the_reference_over_serial_and_over_http(self):
        emulator = self.started()
        expected = ReferencePlayer(support.files_of(self.folder)).command(0, b"space")
        self.assertEqual(expected, b'{"ok":true,"free":13484032,"total":13500416,"animations":2,"external":{"present":false,"free":null,"total":null,"read_only":true}}\n')
        for route, ask in ROUTES.items():
            self.assertEqual(ask(emulator, "space"), expected, route)
            self.assertEqual(ask(emulator, "space 1"), b'{"ok":false,"error":"bad-argument"}\n', route)

    def test_the_total_is_the_boards_storage_and_the_free_space_is_counted_in_blocks_of_the_files(self):
        (self.folder / "extra.odrg").write_bytes(bytes(STORAGE_BLOCK + 1))
        emulator = self.started()
        for route, ask in ROUTES.items():
            reply = json.loads(ask(emulator, "space"))
            self.assertEqual(reply, {"ok": True, "free": BOARD_STORAGE - 6 * STORAGE_BLOCK, "total": BOARD_STORAGE, "animations": 2, "external": {"present": False, "free": None, "total": None, "read_only": True}}, route)
        (self.folder / "more.odrg").write_bytes(bytes(3 * STORAGE_BLOCK))
        self.assertEqual(json.loads(over_http(emulator, "space"))["free"], BOARD_STORAGE - 9 * STORAGE_BLOCK)
        (self.folder / "more.odrg").unlink()
        (self.folder / "extra.odrg").unlink()
        self.assertEqual(json.loads(over_serial(emulator, "space"))["free"], BOARD_STORAGE - 4 * STORAGE_BLOCK)

    def test_the_storage_option_sets_the_total(self):
        for total in (0, 10000, 4 * STORAGE_BLOCK, 4 * STORAGE_BLOCK + 7, 4294967295):
            with self.subTest(total=total):
                emulator = support.Emulator(self.folder, "--storage", total)
                try:
                    expected = ReferencePlayer(support.files_of(self.folder), storage=total).command(0, b"space")
                    for route, ask in ROUTES.items():
                        self.assertEqual(ask(emulator, "space"), expected, route)
                    self.assertEqual(json.loads(expected), {"ok": True, "free": max(0, total - 4 * STORAGE_BLOCK), "total": total, "animations": 2, "external": {"present": False, "free": None, "total": None, "read_only": True}})
                finally:
                    emulator.stop()

    def test_space_with_an_invalid_show_reports_no_animations(self):
        (self.folder / "dvd.odrg").unlink()
        support.with_show_fault(self.folder)
        emulator = self.started()
        for route, ask in ROUTES.items():
            self.assertEqual(json.loads(ask(emulator, "space")), {"ok": True, "free": BOARD_STORAGE - 3 * STORAGE_BLOCK, "total": BOARD_STORAGE, "animations": 0, "external": {"present": False, "free": None, "total": None, "read_only": True}}, route)
        self.assertEqual(emulator.status()["error"], "undefined-id 99")

    def test_space_changes_no_file_of_the_folder(self):
        before = support.files_of(self.folder)
        emulator = self.started()
        for ask in ROUTES.values():
            ask(emulator, "space")
        emulator.stop()
        self.assertEqual(support.files_of(self.folder), before)
        self.assertEqual(sorted(path.name for path in self.folder.iterdir()), sorted(before))


class ListAndRemove(unittest.TestCase):
    def setUp(self):
        self.work = pathlib.Path(support.entered(self, tempfile.TemporaryDirectory()))
        self.folder = support.installed(self.work / "show", core_support.example_show())
        (self.work / "beside.txt").write_bytes(b"not of the show")

    def started(self, *options):
        return support.entered(self, support.Emulator(self.folder, *options))

    def reference(self):
        return ReferencePlayer(support.files_of(self.folder))

    def test_list_gives_the_reply_of_the_reference_over_serial_and_over_http(self):
        emulator = self.started()
        player = self.reference()
        for line in ("list", "list 0", "list 1", "list 2", "list 3", "list 65535", "list x", "list 1 2"):
            expected = player.command(0, line.encode())
            for route, ask in ROUTES.items():
                self.assertEqual(ask(emulator, line), expected, (route, line))
        self.assertEqual(
            player.command(0, b"list"),
            b'{"ok":true,"items":[{"id":1,"file":"hello.odrg","bytes":1138,"ignored":false},{"id":2,"file":"dvd.odrg","bytes":1612,"ignored":false},{"id":3,"cycle":[1,2],"seconds":15}],"next":null}\n',
        )

    def test_remove_changes_the_show_and_the_folder_as_the_reference_has_them_by_each_route(self):
        for first, second in ((support.LINES, "http"), ("http", support.LINES)):
            with self.subTest(first=first):
                support.installed(self.folder, core_support.example_show())
                player = self.reference()
                emulator = support.Emulator(self.folder)
                try:
                    session = (
                        (first, "remove 1"), (second, "list"), (first, "remove 3"), (second, "status"), (second, "list"), (second, "remove 1"), (first, "remove 9"),
                        (first, "space"), (second, "remove 2"), (first, "list"), (second, "space"), (first, "remove 2"),
                    )
                    for route, line in session:
                        expected = player.command(0, line.encode())
                        reply = ROUTES[route](emulator, line)
                        if line == "status":
                            self.assertEqual(support.without_fps(reply), support.without_fps(expected), line)
                        else:
                            self.assertEqual(reply, expected, (route, line))
                finally:
                    emulator.stop()
                self.assertEqual(support.files_of(self.folder), player.files)
                self.assertEqual(sorted(support.files_of(self.folder)), ["mapping.json", "show.json"])
                self.assertEqual((self.folder / "show.json").read_bytes(), b'{"version":1,"brightness":128,"items":[]}\n')

    def test_a_removal_is_there_after_the_emulator_was_started_again(self):
        emulator = support.Emulator(self.folder)
        try:
            self.assertEqual(emulator.status()["playing"], 3)
            self.assertEqual(over_serial(emulator, "remove 3"), b'{"ok":true}\n')
            # The cycle that played is gone: the playlist plays, from its first animation.
            state = emulator.status()
            self.assertEqual((state["playing"], state["animation"]), ("all", 1))
            self.assertEqual(over_http(emulator, "remove 2"), b'{"ok":true}\n')
            listed = over_http(emulator, "list")
        finally:
            emulator.stop()
        self.assertEqual(sorted(support.files_of(self.folder)), ["hello.odrg", "mapping.json", "show.json"])
        again = self.started()
        self.assertEqual(over_serial(again, "list"), listed)
        self.assertEqual(listed, b'{"ok":true,"items":[{"id":1,"file":"hello.odrg","bytes":1138,"ignored":false}],"next":null}\n')
        state = again.status()
        self.assertEqual((state["playing"], state["animation"], state["error"]), ("all", 1, None))
        self.assertEqual(over_http(again, "play 1"), b'{"ok":true}\n')
        self.assertEqual(again.status()["animation"], 1)
        self.assertEqual(json.loads(over_http(again, "space"))["animations"], 1)

    def test_the_commands_write_in_the_folder_and_nowhere_else(self):
        emulator = self.started()
        for line in ("remove 3", "remove 1", "list", "space"):
            over_http(emulator, line)
        emulator.stop()
        self.assertEqual(sorted(path.name for path in self.work.iterdir()), ["beside.txt", "show"])
        self.assertEqual((self.work / "beside.txt").read_bytes(), b"not of the show")
        self.assertEqual(sorted(path.name for path in self.folder.iterdir()), ["dvd.odrg", "mapping.json", "show.json"])

    def test_what_an_interrupted_change_left_is_removed_when_the_emulator_starts(self):
        (self.folder / "upload.part").write_bytes(b"half")
        (self.folder / "show.part").write_bytes(b"{")
        (self.folder / "pending.txt").write_bytes(b"stray.odrg\nhello.odrg\n")
        (self.folder / "stray.odrg").write_bytes((self.folder / "hello.odrg").read_bytes())
        emulator = self.started()
        self.assertEqual(emulator.status()["error"], None)
        self.assertEqual(sorted(path.name for path in self.folder.iterdir()), ["dvd.odrg", "hello.odrg", "mapping.json", "show.json"])


BUSY = b'{"ok":false,"error":"busy"}\n'
DONE = b'{"ok":true}\n'


def upload(emulator, routes, number, name, data, piece=1500, seconds=30):
    """Sends an upload to an emulator, each command by the next of some routes in turn, and
    sends `upload end` again for as long as the file is being checked. Returns the replies
    to the lines before `upload end`, and the last reply to `upload end`."""
    lines = core_support.upload_lines(number, name, data, piece)
    given = [ROUTES[routes[position % len(routes)]](emulator, line) for position, line in enumerate(lines)]
    deadline = time.monotonic() + seconds
    while True:
        ended = ROUTES[routes[-1]](emulator, core_support.upload_end(data))
        if ended != BUSY or time.monotonic() > deadline:
            return given, ended
        time.sleep(0.05)


class Uploads(unittest.TestCase):
    def setUp(self):
        self.work = pathlib.Path(support.entered(self, tempfile.TemporaryDirectory()))
        self.folder = support.installed(self.work / "show", core_support.example_show())
        self.clip = core_support.dense_clip(60, 6, 1)

    def started(self, *options):
        return support.entered(self, support.Emulator(self.folder, *options))

    def test_an_upload_over_each_route_and_over_the_two_mixed_installs_the_file_and_its_item(self):
        self.assertGreater(len(self.clip), 9000)
        for number, routes in enumerate(((support.LINES,), ("http",), (support.LINES, "http"), ("http", support.LINES)), start=10):
            with self.subTest(routes=routes):
                support.installed(self.folder, core_support.example_show())
                for stale in set(support.files_of(self.folder)) - set(core_support.example_show()):
                    (self.folder / stale).unlink()
                emulator = support.Emulator(self.folder)
                try:
                    given, ended = upload(emulator, routes, number, "clip.odrg", self.clip)
                    self.assertEqual(given[0], b'{"ok":true,"chunk":1500}\n')
                    self.assertEqual([json.loads(reply)["received"] for reply in given[1:]], [min(len(self.clip), 1500 * count) for count in range(1, len(given))])
                    self.assertEqual(ended, DONE)
                    listed = json.loads(over_http(emulator, "list"))["items"]
                    self.assertEqual(listed[-1], {"id": number, "file": "clip.odrg", "bytes": len(self.clip), "ignored": False})
                    self.assertEqual(over_serial(emulator, f"play {number}"), DONE)
                    state = emulator.status()
                    self.assertEqual((state["playing"], state["animation"], state["error"]), ("all", number, None))
                    self.assertEqual(json.loads(over_serial(emulator, "space"))["animations"], 3)
                finally:
                    emulator.stop()
                files = support.files_of(self.folder)
                self.assertEqual(sorted(files), ["clip.odrg", "dvd.odrg", "hello.odrg", "mapping.json", "show.json"])
                self.assertEqual(files["clip.odrg"], self.clip)
                self.assertEqual(json.loads(files["show.json"])["items"][-1], {"id": number, "file": "clip.odrg"})
                player = ReferencePlayer(core_support.example_show())
                for line in core_support.upload_lines(number, "clip.odrg", self.clip):
                    player.command(0, line.encode())
                for tick in range(0, 20 * 60, 20):
                    player.poll(tick)
                self.assertEqual(player.command(2000, core_support.upload_end(self.clip).encode()), DONE)
                self.assertEqual(files, player.files)

    def test_an_uploaded_animation_is_there_after_the_emulator_was_started_again_and_can_be_replaced_and_removed(self):
        emulator = support.Emulator(self.folder)
        try:
            self.assertEqual(upload(emulator, ("http",), 9, "clip.odrg", self.clip)[1], DONE)
        finally:
            emulator.stop()
        again = self.started()
        self.assertEqual(json.loads(over_serial(again, "list"))["items"][-1], {"id": 9, "file": "clip.odrg", "bytes": len(self.clip), "ignored": False})
        self.assertEqual(over_http(again, "play 9"), DONE)
        self.assertEqual((again.status()["playing"], again.status()["animation"]), ("all", 9))
        smaller = core_support.clip(5, 60, 6)
        self.assertEqual(upload(again, (support.LINES,), 9, "smaller.odrg", smaller)[1], DONE)
        self.assertEqual(json.loads(over_http(again, "list"))["items"][-1], {"id": 9, "file": "smaller.odrg", "bytes": len(smaller), "ignored": False})
        self.assertEqual((again.status()["playing"], again.status()["animation"]), ("all", 9))
        self.assertEqual(over_http(again, "remove 9"), DONE)
        again.stop()
        self.assertEqual(support.files_of(self.folder), {name: content if isinstance(content, bytes) else content.encode() for name, content in core_support.example_show().items()} | {"show.json": support.files_of(self.folder)["show.json"]})
        self.assertEqual([item["id"] for item in json.loads(support.files_of(self.folder)["show.json"])["items"]], [1, 2, 3])

    def test_a_file_of_another_canvas_is_refused_with_bad_file_and_its_reason(self):
        emulator = self.started()
        wrong = core_support.clip(5, 60, 60)
        given, ended = upload(emulator, ("http", support.LINES), 9, "wrong.odrg", wrong)
        self.assertEqual(ended, b'{"ok":false,"error":"bad-file","reason":"size-mismatch"}\n')
        self.assertEqual(over_http(emulator, "upload cancel"), b'{"ok":false,"error":"no-upload"}\n')
        self.assertEqual(sorted(support.files_of(self.folder)), ["dvd.odrg", "hello.odrg", "mapping.json", "show.json"])

    def test_a_file_that_does_not_fit_the_storage_given_is_no_space(self):
        emulator = self.started("--storage", 4 * STORAGE_BLOCK + 16384 + 1000)
        self.assertEqual(over_http(emulator, "upload begin 9 clip.odrg 1000"), b'{"ok":false,"error":"no-space"}\n')
        self.assertEqual(over_serial(emulator, "upload begin 9 clip.odrg 996"), b'{"ok":true,"chunk":1500}\n')
        self.assertEqual(over_http(emulator, "upload begin 8 other.odrg 5"), b'{"ok":false,"error":"busy"}\n')
        self.assertEqual(over_http(emulator, "upload cancel"), DONE)
        self.assertEqual(sorted(support.files_of(self.folder)), ["dvd.odrg", "hello.odrg", "mapping.json", "show.json"])

    def test_an_upload_that_was_not_ended_leaves_nothing_after_the_next_start(self):
        emulator = support.Emulator(self.folder)
        try:
            lines = core_support.upload_lines(9, "clip.odrg", self.clip)
            for line in lines[:3]:
                over_http(emulator, line)
            self.assertEqual(support.files_of(self.folder)["upload.part"], self.clip[:3000])
        finally:
            emulator.stop()
        self.assertIn("upload.part", support.files_of(self.folder))
        again = self.started()
        self.assertEqual(over_http(again, "upload cancel"), b'{"ok":false,"error":"no-upload"}\n')
        self.assertEqual(sorted(support.files_of(self.folder)), ["dvd.odrg", "hello.odrg", "mapping.json", "show.json"])


if __name__ == "__main__":
    unittest.main()
