import pathlib
import re
import unittest

from tests.emulator import support as emulator_support

from . import support
from .test_target import BAD_ADDRESS, BAD_REPLY, NO_ANSWER, entered

NOT_UNDERSTOOD = "The installation did not understand the app. Its software and this app do not match. ({})"
REFUSED = "The installation refused the command. ({})"
NO_WIFI = "This phone is not on a Wi-Fi network. Join the network odrig in the phone's Wi-Fi settings. (no-wifi)"
OK = (200, '{"ok":true}\n')


def refusal(code):
    return (200, '{"ok":false,"error":"%s"}\n' % code)


def codes_of_the_command_list():
    """The error codes of docs/commands.md, in the order of its table."""
    text = (support.ROOT / "docs" / "commands.md").read_text(encoding="utf-8")
    table = text.split("\n## Error codes\n")[1].strip().split("\n\n")[0]
    return [row.split("`")[1] for row in table.splitlines() if row.startswith("| `")]


class TheTable(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.codes = codes_of_the_command_list()
        refusals = [[code, "play 2", "file-missing dvd.odrg"] for code in cls.codes]
        refusals += [["unknown-id", "play all", None], ["unknown-id", "play 65535", None], ["show-invalid", "play all", None], ["weird", "on", None], ["toString", "off", None]]
        refusals += [["unknown-id", "remove 7", None], ["busy", "remove 7", None], ["in-use", "remove 7", None], ["storage-error", "space", None]]
        failures = [["bad-address", "x y"], ["no-wifi", "4.3.2.1"], ["no-answer", "4.3.2.1"], ["bad-reply", "192.168.1.23:8600"]]
        cls.found = support.run("texts", settings={"refusals": refusals, "failures": failures}).seen

    def text(self, code, line="play 2", reason="file-missing dvd.odrg"):
        return self.found["refusals"][f"{code} | {line} | {'null' if reason is None else reason}"]

    def test_every_error_code_of_the_command_list_has_a_text_or_is_one_the_app_cannot_get(self):
        self.assertEqual(len(self.codes), 19)
        cannot_get = self.found["notForTheApp"]
        self.assertLessEqual(set(cannot_get), set(self.codes))
        self.assertEqual(len(cannot_get), len(set(cannot_get)))
        for code in self.codes:
            with self.subTest(code=code):
                general = self.text(code) == REFUSED.format(code)
                self.assertEqual(general, code in cannot_get, f"{code}: it needs a text of its own, or a place among the codes the app cannot get")

    def test_the_codes_the_app_cannot_get_are_those_of_the_commands_it_does_not_send(self):
        # The app sends neither `upload begin external` nor `catalog rebuild`.
        self.assertEqual(self.found["notForTheApp"], ["read-only"])

    def test_each_text_of_a_refusal(self):
        for code in ("line-too-long", "unknown-command", "bad-argument"):
            self.assertEqual(self.text(code), NOT_UNDERSTOOD.format(code))
        self.assertEqual(self.text("show-invalid"), "The installed show is invalid: file-missing dvd.odrg. Nothing can be played until a show is installed over USB. (show-invalid)")
        self.assertEqual(self.text("show-invalid", "play all", None), "The installed show is invalid. Nothing can be played until a show is installed over USB. (show-invalid)")
        self.assertEqual(self.text("unknown-id"), "Animation 2 is not installed any more. (unknown-id)")
        self.assertEqual(self.text("unknown-id", "play 65535", None), "Animation 65535 is not installed any more. (unknown-id)")
        self.assertEqual(self.text("unknown-id", "play all", None), "No animation is installed. (unknown-id)")
        self.assertEqual(self.text("unknown-id", "remove 7", None), "Animation 7 is not installed any more. (unknown-id)")
        self.assertEqual(self.text("busy", "remove 7", None), "The installation is busy. Try again in a moment. (busy)")
        self.assertEqual(self.text("in-use", "remove 7", None), "Animation 7 cannot be removed: a cycle plays it, or it is on a USB stick. (in-use)")
        self.assertEqual(self.text("mapping-conflict"), "Mapping changed on the target. Reload before saving. (mapping-conflict)")
        self.assertEqual(self.text("storage-error", "space", None), "The installation could not use its storage. (storage-error)")
        # A code the app does not know, also one that is a word of the language.
        self.assertEqual(self.text("weird", "on", None), REFUSED.format("weird"))
        self.assertEqual(self.text("toString", "off", None), REFUSED.format("toString"))

    def test_each_text_of_a_failure_and_of_silence(self):
        self.assertEqual(self.found["failures"], {"bad-address": BAD_ADDRESS, "no-wifi": NO_WIFI, "no-answer": NO_ANSWER.format("4.3.2.1"), "bad-reply": BAD_REPLY.format("192.168.1.23:8600")})
        self.assertEqual(self.found["silence"], ["The installation has not answered for 0 seconds.", "The installation has not answered for 1 second.",
                                                 "The installation has not answered for 2 seconds.", "The installation has not answered for 75 seconds."])

    def test_every_message_ends_with_its_code_in_brackets(self):
        for key, text in self.found["refusals"].items():
            self.assertRegex(text, rf"\A[A-Z].+[.] \({re.escape(key.split(' | ')[0])}\)\Z")
        for kind, text in self.found["failures"].items():
            self.assertRegex(text, rf"\A[A-Z].+[.] \({kind}\)\Z")


class OnTheScreen(unittest.TestCase):
    def emulator(self, folder):
        started = entered(self, emulator_support.Emulator(folder))
        return started, f"127.0.0.1:{started.port}"

    def test_an_animation_that_is_gone_is_said_so_and_the_list_is_asked_for_again(self):
        emulator, address = self.emulator(entered(self, emulator_support.demo_show()))
        presses = [{"row": 2, "step": True, "wait": 1200}, {"dismiss": True}]
        found = support.run("refusals", address=address, steps=[lambda: emulator.command("remove 2")], settings={"rows": 2, "presses": presses})
        refused, dismissed = found.seen
        self.assertEqual(refused["message"], "Animation 2 is not installed any more. (unknown-id)")
        # The list was asked for again at once, not ten seconds later.
        self.assertEqual([row["text"] for row in refused["rows"]], ["1 hello.odrg"])
        self.assertEqual((refused["playing"], refused["shown"]), ("Playlist", "animations"))
        self.assertIsNone(dismissed["message"])

    def test_the_playlist_of_a_show_without_an_animation(self):
        folder = entered(self, emulator_support.example_show())
        emulator, address = self.emulator(folder)
        for line in ("remove 3", "remove 2", "remove 1"):
            self.assertEqual(emulator.command(line), b'{"ok":true}\n')
        found = support.run("refusals", address=address, settings={"rows": 0, "presses": [{"press": "Playlist from the start"}]})
        self.assertEqual(found.seen[0]["message"], "No animation is installed. (unknown-id)")

    def test_an_invalid_show_is_said_with_its_reason(self):
        folder = entered(self, emulator_support.example_show())
        emulator_support.with_show_fault(folder)
        emulator, address = self.emulator(folder)
        found = support.run("refusals", address=address, settings={"rows": 0, "presses": [{"press": "Playlist from the start", "wait": 1500}]})
        self.assertEqual(found.seen[0]["message"], "The installed show is invalid: undefined-id 99. Nothing can be played until a show is installed over USB. (show-invalid)")
        # The message stays while statuses come and go.
        self.assertEqual(found.seen[0]["playing"], "The installed show is invalid: undefined-id 99.")

    def test_a_target_that_does_not_know_a_command_and_one_that_refuses_with_another_code(self):
        old = entered(self, support.StandIn({**support.SOUND, "play": refusal("bad-argument"), "off": refusal("weird"), "on": OK}))
        presses = [{"press": "Playlist from the start"}, {"press": "Off", "not": NOT_UNDERSTOOD.format("bad-argument")}, {"press": "On", "wait": 800}, {"dismiss": True}]
        found = support.run("refusals", address=old.address, settings={"rows": 2, "presses": presses[:2] + presses[3:]})
        self.assertEqual(found.seen[0]["message"], NOT_UNDERSTOOD.format("bad-argument"))
        # A second message takes the place of the first, and goes when it is dismissed.
        self.assertEqual(found.seen[1]["message"], REFUSED.format("weird"))
        self.assertIsNone(found.seen[2]["message"])
        self.assertEqual([line for _, line in old.lines if line in (b"play all", b"off")], [b"play all", b"off"])

    def test_the_show_screen_says_why_the_target_does_not_answer(self):
        folder = entered(self, emulator_support.demo_show())
        port = support.free_port()
        first = emulator_support.Emulator(folder, port=port)
        self.addCleanup(first.stop)
        steps = [first.stop, lambda: entered(self, emulator_support.Emulator(folder, port=port))]
        found = support.run("unanswered", address=f"127.0.0.1:{port}", steps=steps, settings={"rows": 2})
        self.assertIsNone(found.seen["before"]["why"])
        self.assertEqual(found.seen["first"]["why"], NO_ANSWER.format(f"127.0.0.1:{port}"))
        self.assertIsNone(found.seen["again"]["why"])


if __name__ == "__main__":
    unittest.main()
