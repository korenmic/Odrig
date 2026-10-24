import json
import pathlib
import tempfile
import unittest

from tests.core import support as core_support
from . import support


def options_of(route, emulator):
    """The options of the command tool that reach this emulator by a route."""
    if route == "http":
        return ["--http", f"127.0.0.1:{emulator.port}"]
    if route == "tcp":
        return ["--tcp", emulator.tcp]
    return ["--port", emulator.serial]


def routes():
    return ("http", "tcp", *(("serial",) if support.HAS_SERIAL else ()))


class OrderAndSnakeTestsOnEveryRoute(unittest.TestCase):
    def test_order_get_and_order_move_through_the_command_tool(self):
        items = [{"id": number, "file": "a.odrg"} for number in range(1, 4)]
        files = {"mapping.json": core_support.mapping_texts()["legs-2"], "show.json": core_support.show_text(items), "a.odrg": core_support.clip(1, 60, 6)}
        for route in routes():
            with self.subTest(route=route), tempfile.TemporaryDirectory() as work:
                folder = support.installed(pathlib.Path(work, "show"), files)
                with support.Emulator(folder, tcp_port=0) as emulator:
                    options = options_of(route, emulator)
                    result = support.run_tool(*options, "order", "get")
                    self.assertEqual(result.status, 0, result.err)
                    reply = json.loads(result.out)
                    self.assertEqual(reply["ids"], [1, 2, 3])
                    self.assertEqual(reply, json.loads(emulator.command("order get")))
                    result = support.run_tool(*options, "order", "move", str(reply["revision"]), "3", "1")
                    self.assertEqual((result.status, json.loads(result.out)), (0, {"ok": True}), result.err)
                    self.assertEqual(json.loads(emulator.command("order get"))["ids"], [3, 1, 2])
                    self.assertEqual((folder / "order.txt").read_text(), "odrig-order 1\ni 3\ni 1\ni 2\n")
                    result = support.run_tool(*options, "order", "move", str(reply["revision"]), "1", "end")
                    self.assertEqual((result.status, json.loads(result.out)), (1, {"ok": False, "error": "order-conflict"}), result.err)

    def test_order_get_without_a_position_prints_every_part(self):
        items = [{"id": number, "file": "a.odrg"} for number in range(1, 301)]
        files = {"mapping.json": core_support.mapping_texts()["legs-2"], "show.json": core_support.show_text(items), "a.odrg": core_support.clip(1, 60, 6)}
        with tempfile.TemporaryDirectory() as work:
            folder = support.installed(pathlib.Path(work, "show"), files)
            with support.Emulator(folder) as emulator:
                result = support.run_tool("--http", f"127.0.0.1:{emulator.port}", "order", "get")
                self.assertEqual(result.status, 0, result.err)
                parts = [json.loads(line) for line in result.out.splitlines()]
                self.assertGreater(len(parts), 1)
                self.assertEqual([number for part in parts for number in part["ids"]], list(range(1, 301)))
                result = support.run_tool("--http", f"127.0.0.1:{emulator.port}", "order", "get", "250")
                self.assertEqual(json.loads(result.out)["ids"], list(range(251, 301)))

    def test_the_snake_tests_through_the_command_tool(self):
        with tempfile.TemporaryDirectory() as work:
            folder = support.installed(pathlib.Path(work, "show"), core_support.demo_show())
            for route in routes():
                with self.subTest(route=route), support.Emulator(folder, tcp_port=0) as emulator:
                    options = options_of(route, emulator)
                    result = support.run_tool(*options, "mapping", "test", "snake", "12")
                    self.assertEqual((result.status, json.loads(result.out)), (0, {"ok": True}), result.err)
                    got = json.loads(emulator.command("mapping get"))
                    self.assertEqual((got["test"], got["snake"]), (True, 12))
                    result = support.run_tool(*options, "mapping", "test", "off")
                    self.assertEqual(result.status, 0, result.err)
                    got = json.loads(emulator.command("mapping get"))
                    self.assertEqual((got["test"], got["snake"]), (False, None))

    def test_the_tool_refuses_malformed_forms_without_sending_them(self):
        for argv, said in ((["order"], "order takes get [FROM], or move REV ID BEFORE"), (["order", "move", "1", "2"], "order takes get"),
                           (["order", "put"], "order takes get"), (["mapping", "test", "snake"], "mapping takes get"),
                           (["order", "get", "1\n"], "a command is one line")):
            result = support.run_tool("--port", "a", *argv)
            self.assertEqual(result.status, 2, argv)
            self.assertIn(said, result.err)


if __name__ == "__main__":
    unittest.main()
