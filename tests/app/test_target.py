import json
import pathlib
import unittest

from tests.emulator import support as emulator_support

from . import support

NO_ANSWER = "No answer from {}. Check that the phone is on the installation's Wi-Fi network and that the installation has power. (no-answer)"
BAD_REPLY = "Something answered at {}, but it is not an odrig installation. (bad-reply)"
BAD_ADDRESS = "That is not an address. Write it like 4.3.2.1 or 192.168.1.23:8600. (bad-address)"


def entered(case, context):
    value = context.__enter__()
    case.addCleanup(context.__exit__, None, None, None)
    return value


class Target(unittest.TestCase):
    def emulator(self, folder=None):
        """An emulator on the demo show, or on a folder, and the address the app is given."""
        if folder is None:
            folder = entered(self, emulator_support.demo_show())
        started = entered(self, emulator_support.Emulator(folder))
        return started, f"127.0.0.1:{started.port}"


class TheAddress(Target):
    FORMS = {
        "4.3.2.1": "4.3.2.1",
        " 192.168.1.23:8600 ": "192.168.1.23:8600",
        "http://192.168.1.23:8600/": "192.168.1.23:8600",
        "HTTP://Mac.Local:80": "mac.local:80",
        "mac.local": "mac.local",
        "localhost:8600": "localhost:8600",
        "odrig-mac": "odrig-mac",
        "a-b.c9:08600": "a-b.c9:8600",
        "10.0.0.5:1": "10.0.0.5:1",
        "0.0.0.0:65535": "0.0.0.0:65535",
        "255.255.255.255": "255.255.255.255",
        "4.3.2.1/": "4.3.2.1",
    }
    REFUSED = ["", " ", "4.3.2", "4.3.2.1.5", "256.1.1.1", "1.2.3.4:0", "1.2.3.4:65536", "1.2.3.4:", "1.2.3.4:80:80", "1.2.3.4:123456", "https://1.2.3.4", "http://",
               "1.2.3.4/odrig", "1.2.3.4//", "a b", "-a.b", "a-.b", "a..b", ".a", "a.", "host:port", "[::1]:80", "::1", "user@host", "1.2.3.4?x", "1.2.3.4:8600/odrig",
               "ftp://1.2.3.4", "1.2.3.4:-1", "1.2.3.4:+80", "מחשב", "0001.2.3.4"]

    def test_each_form_of_an_address_is_kept_as_host_or_host_and_port_and_anything_else_is_refused(self):
        texts = [*self.FORMS, *self.REFUSED]
        found = support.run("forms", settings={"texts": texts})
        self.assertEqual(found.seen["kept"], {**self.FORMS, **{text: "refused: bad-address" for text in self.REFUSED}})
        self.assertEqual(found.elsewhere, [])

    def test_the_first_address_is_the_boards(self):
        found = support.run("forms", settings={"texts": []})
        self.assertEqual((found.seen["board"], found.seen["first"]), ("4.3.2.1", "4.3.2.1"))
        # On a new phone the app shows that address and asks it, and nothing else.
        found = support.run("first")
        self.assertEqual((found.seen["field"], found.seen["kept"], found.seen["began"], found.seen["shown"]), ("4.3.2.1", None, "target", "target"))
        self.assertEqual(found.seen["failure"], NO_ANSWER.format("4.3.2.1"))
        sent = support.commands_elsewhere(found)
        self.assertGreaterEqual(len(sent), 1)
        self.assertEqual(set(sent), {("4.3.2.1", b"status"), ("4.3.2.1", b"space")})

    def test_an_address_that_was_set_is_kept_when_the_app_is_opened_again_and_board_puts_the_boards_back(self):
        _, first = self.emulator()
        other = entered(self, support.StandIn(support.SOUND))
        found = support.run("kept", address=first, settings={"other": other.address})
        self.assertEqual(found.seen["reloaded"], {"field": other.address, "kept": other.address})
        self.assertEqual(found.seen["board"], {"field": "4.3.2.1", "kept": "4.3.2.1", "failure": NO_ANSWER.format("4.3.2.1")})
        self.assertEqual(set(support.commands_elsewhere(found)), {("4.3.2.1", b"status"), ("4.3.2.1", b"space")})
        self.assertGreaterEqual(len(other.lines), 2)

    def test_a_text_that_is_no_address_is_refused_with_a_message_and_the_address_in_use_stays(self):
        emulator, address = self.emulator()
        found = support.run("refused", address=address, settings={"text": "the board"})
        self.assertEqual(found.seen["before"], {"message": None, "kept": address})
        self.assertEqual(found.seen["refused"], {"message": BAD_ADDRESS, "kept": address, "field": "the board", "link": "Answers"})
        # The message stays until it is dismissed, and the target that was in use is
        # still the one that is asked.
        self.assertEqual(found.seen["later"], {"message": BAD_ADDRESS, "link": "Answers"})
        self.assertIsNone(found.seen["dismissed"])
        self.assertEqual(found.elsewhere, [])


class WhetherTheTargetAnswers(Target):
    def test_against_an_emulator_it_answers_and_the_app_goes_to_the_show_screen(self):
        emulator, address = self.emulator()
        found = support.run("answers", address=address)
        self.assertEqual(found.seen, {"shown": "target", "link": "Answers", "failure": None, "invalid": None, "route": "Sent from this browser.",
                                      "about": found.seen["about"], "field": address, "kept": address})
        self.assertRegex(found.seen["about"], r"\AWeb view [0-9]+\Z")
        self.assertEqual(found.elsewhere, [])

    def test_the_app_starts_on_the_target_screen_and_a_silent_target_is_no_answer_after_5_seconds(self):
        silent = entered(self, support.StandIn(None))
        found = support.run("silent", address=silent.address)
        self.assertEqual(found.seen["began"], {"shown": "target", "link": "Checking", "failure": None})
        self.assertEqual((found.seen["shown"], found.seen["failure"]), ("target", NO_ANSWER.format(silent.address)))
        self.assertGreater(found.seen["afterMs"], 4500)
        self.assertLess(found.seen["afterMs"], 6500)
        self.assertEqual(set(silent.lines), {("/odrig", b"status")})

    def test_nothing_listens_at_the_address_and_then_an_emulator_starts_there(self):
        port = support.free_port()
        folder = entered(self, emulator_support.demo_show())
        found = support.run("recovers", address=f"127.0.0.1:{port}", steps=[lambda: entered(self, emulator_support.Emulator(folder, port=port))])
        self.assertEqual(found.seen["failure"], NO_ANSWER.format(f"127.0.0.1:{port}"))
        self.assertEqual((found.seen["link"], found.seen["failureAfter"]), ("Answers", None))
        self.assertLess(found.seen["ms"], 3000)

    def test_an_answer_that_is_not_a_reply_of_an_odrig_target_is_a_bad_reply(self):
        answers = {
            "another status than 200": (404, ""),
            "a status of an error with a reply in it": (500, support.PLAYING[1]),
            "a body that is no JSON": (200, "hello"),
            "a JSON value that is no object": (200, "[1]"),
            "null": (200, "null"),
            "an object without ok": (200, '{"on":true}'),
            "ok that is neither true nor false": (200, '{"ok":"yes"}'),
            "a status without its members": (200, '{"ok":true}'),
            "a brightness that is no whole number": (200, support.PLAYING[1].replace("128", "12.5")),
            "something else that plays": (200, support.PLAYING[1].replace('"all"', '"some"')),
            "a refusal without a code": (200, '{"ok":false}'),
        }
        targets = [entered(self, support.StandIn(reply)) for reply in answers.values()]
        sound = entered(self, support.StandIn(support.SOUND))
        addresses = [target.address for target in targets] + [sound.address]
        found = support.run("addresses", address=sound.address, settings={"addresses": addresses})
        for what, target, seen in zip(answers, targets, found.seen):
            with self.subTest(what):
                self.assertEqual((seen["link"], seen["failure"], seen["shown"]), ("No answer", BAD_REPLY.format(target.address), "target"))
                self.assertEqual(target.lines[0], ("/odrig", b"status"))
        # After them a target that answers as odrig does: the app recovers by itself.
        self.assertEqual((found.seen[-1]["link"], found.seen[-1]["failure"]), ("Answers", ""))

    def test_a_target_whose_show_is_invalid_answers_and_the_screen_says_the_reason(self):
        folder = entered(self, emulator_support.example_show())
        pathlib.Path(folder, "dvd.odrg").unlink()
        emulator, address = self.emulator(folder)
        self.assertEqual(emulator.status()["error"], "file-missing dvd.odrg")
        found = support.run("answers", address=address)
        self.assertEqual((found.seen["link"], found.seen["failure"]), ("Answers", None))
        self.assertEqual(found.seen["invalid"], "The installed show is invalid: file-missing dvd.odrg.")


class Requests(Target):
    STATUS = ("/odrig", b"status")
    LIST = ("/odrig", b"list 0")

    def test_status_is_asked_once_a_second(self):
        target = entered(self, support.StandIn(support.SOUND))
        support.run("waits", address=target.address, settings={"ms": 5300})
        self.assertEqual(set(target.lines), {self.STATUS, self.LIST, ("/odrig", b"space")})
        self.assertIn(target.lines.count(self.STATUS), (6, 7), target.lines)
        self.assertEqual(target.together, 1)

    def test_one_request_is_under_way_at_a_time_also_when_a_reply_takes_longer_than_a_second(self):
        slow = entered(self, support.StandIn(support.SOUND, delay=1.6))
        found = support.run("waits", address=slow.address, settings={"ms": 5300})
        self.assertEqual(found.seen["link"], "Answers")
        self.assertEqual(slow.together, 1)
        self.assertEqual(set(slow.lines), {self.STATUS, self.LIST})
        self.assertIn(len(slow.lines), (3, 4), slow.lines)

    def test_the_line_is_sent_as_it_is_with_no_request_before_it(self):
        emulator, address = self.emulator()
        with emulator_support.EventStream(emulator.port) as stream:
            support.run("answers", address=address)
            logged = emulator_support.of_kind(stream.read_until(lambda events: sum(event.kind == "log" for event in events) >= 2, 5), "log")
        self.assertEqual({(entry["line"], entry["transport"]) for entry in logged}, {("status", "http"), ("list 0", "http"), ("space", "http")})
        self.assertTrue(all(json.loads(entry["reply"])["ok"] for entry in logged))


if __name__ == "__main__":
    unittest.main()
