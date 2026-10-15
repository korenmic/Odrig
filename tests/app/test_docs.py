import json
import re
import unittest

from . import support

from apptool import cli, paths  # noqa: E402

PAGE = support.ROOT / "docs" / "android-app.md"


def flat(text):
    return " ".join(text.split())


def section(text, heading):
    """The text under a heading of the second level, to the next one."""
    return text.split(f"\n## {heading}\n")[1].split("\n## ")[0]


def blocks(text):
    """The lines of the code blocks of a text."""
    return [line for block in re.findall(r"(?ms)^```[a-z]*\n(.*?)^```", text) for line in block.splitlines()]


def anchor(heading):
    return re.sub(r"[^a-z0-9 -]", "", heading.lower()).replace(" ", "-")


class TheAppsPage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = PAGE.read_text(encoding="utf-8")
        cls.said = flat(cls.text)

    def test_its_sections_are_what_the_app_is_how_it_is_built_installed_and_used_and_what_was_checked(self):
        headings = re.findall(r"(?m)^## (.+)$", self.text)
        self.assertEqual(headings, ["What it is", "What you need", "The tool", "Installing on a phone", "Using it", "Messages", "The phone and the installation's network",
                                    "The check on a phone", "The suites", "What is verified", "What is open"])

    def test_every_command_of_the_tool_has_an_example(self):
        commands = next(action for action in cli.parser()._actions if action.dest == "command").choices
        self.assertEqual(sorted(commands), ["build", "install", "serve", "setup"])
        given = blocks(section(self.text, "The tool"))
        for name in commands:
            self.assertIn(f"python3 app/app.py {name}", given, name)
            self.assertIn(f"\n### {name}\n", self.text)
        self.assertIn("python3 app/app.py serve [--port N]", given)
        self.assertIn(f"http://127.0.0.1:{cli.webserver.PORT}/", self.said)

    def test_every_reason_of_the_error_line_is_in_its_table(self):
        raised = set()
        for path in sorted((support.APP / "apptool").glob("*.py")):
            raised |= set(re.findall(r'Failure\(\s*"([a-z-]+)"', path.read_text(encoding="utf-8")))
            raised |= set(re.findall(r'reason="([a-z-]+)"', path.read_text(encoding="utf-8")))
        table = section(self.text, "The tool").split("\n### ")[0]
        listed = [row.split("`")[1] for row in table.splitlines() if row.startswith("| `")]
        self.assertEqual(sorted(listed), sorted(raised))
        self.assertEqual(len(listed), len(set(listed)))

    def test_the_versions_are_those_of_the_tracked_files(self):
        listed = json.loads(paths.TOOLCHAIN.read_text(encoding="utf-8"))
        package = json.loads(paths.PACKAGE.read_text(encoding="utf-8"))
        setup = section(self.text, "The tool").split("\n### setup\n")[1].split("\n### ")[0]
        for expected in (listed["jdk"]["version"], listed["command-line-tools"]["version"], package["dependencies"]["@capacitor/core"], f"`{listed['licence']}`",
                         *(f"`{name}`" for name in listed["sdk-packages"]), "`@capacitor/core`", "`@capacitor/cli`", "`@capacitor/android`"):
            self.assertIn(expected, setup)
        wrapper = (support.APP / "android" / "gradle" / "wrapper" / "gradle-wrapper.properties").read_text(encoding="utf-8")
        gradle = re.search(r"gradle-([0-9.]+)-all\.zip", wrapper).group(1)
        self.assertIn(f"Gradle {gradle}", setup)
        for folder in ("`app/node_modules/`", "`build/app/jdk/`", "`build/app/android-sdk/`", "`build/app/downloads/`", "`build/app/gradle/`"):
            self.assertIn(folder, setup)
        self.assertIn("accepts that one licence and no other", flat(setup))

    def test_the_lines_the_app_sends_are_the_ten_of_its_table(self):
        table = section(self.text, "What it is")
        lines = [span for row in table.splitlines() if row.startswith("| ") for span in re.findall(r"`([^`]+)`", row.split("|")[2])]
        self.assertEqual(lines, ["status", "list 0", "list <next>", "play <id>", "play all", "on", "off", "brightness <n>", "space", "remove <id>"])
        self.assertIn("It sends ten command lines and no other", self.said)

    def test_every_message_of_the_app_is_on_the_page(self):
        refusals = [["line-too-long", "on", None], ["show-invalid", "play all", "`<reason>`"], ["unknown-id", "play `<id>`", None], ["unknown-id", "play all", None], ["weird", "on", None],
                    ["busy", "remove `<id>`", None], ["in-use", "remove `<id>`", None], ["storage-error", "space", None]]
        failures = [["bad-address", ""], ["no-wifi", ""], ["no-answer", "`<address>`"], ["bad-reply", "`<address>`"]]
        found = support.run("texts", settings={"refusals": refusals, "failures": failures}).seen
        messages = section(self.text, "Messages")
        said = flat(messages)
        for text in [*found["refusals"].values(), *found["failures"].values()]:
            sentence = re.sub(r" \([a-z-]+\)\Z", "", text)
            self.assertIn(f"| {sentence} |", said)
        self.assertIn(found["silence"][3].replace("75", "12"), said)
        self.assertIn("The installed show is invalid: <reason>.", said)
        rows = [row.split("`")[1] for row in messages.splitlines() if row.startswith("| `")]
        self.assertEqual(rows, ["bad-address", "no-wifi", "no-answer", "bad-reply", "line-too-long", "show-invalid", "unknown-id", "unknown-id", "busy", "in-use", "storage-error"])
        self.assertIn("`Removed animation <id> <file>.`", said)

    def test_every_line_of_how_requests_travel_is_explained(self):
        screen = (support.WWW / "screens" / "target.js").read_text(encoding="utf-8")
        function = screen.split("function routeLine(found) {")[1].split("\n}\n")[0]
        sentences = [flat(sentence) for sentence in re.findall(r'"\s?([A-Z][^"]+)"', function)]
        self.assertEqual(len(sentences), 6)
        network = flat(section(self.text, "The phone and the installation's network"))
        for sentence in sentences:
            if sentence.startswith("This Wi-Fi network has no internet"):
                self.assertIn(f"`Sent over Wi-Fi. {sentence}`", network)
            else:
                self.assertIn(f"`{sentence}`", network)

    def test_the_check_on_a_phone_is_numbered_steps_that_say_what_must_be_seen(self):
        check = section(self.text, "The check on a phone")
        steps = re.findall(r"(?m)^([0-9]+)\. \*\*([^*]+)\*\*", check)
        self.assertEqual([int(number) for number, _ in steps], list(range(1, 11)))
        self.assertEqual(check.count("*Seen:*"), 9)
        for expected in ("This is the owner's. No program can do it.", "python3 app/app.py install", "python -m emulator build/demo-20/show --lan", "`lan:` line",
                         "press `Board`", "Leave mobile data on", "Switch mobile data off"):
            self.assertIn(expected, flat(check))

    def test_it_says_what_is_verified_and_what_is_open(self):
        verified = flat(section(self.text, "What is verified"))
        for expected in ("in Chrome against the emulator", "write nothing outside the repository's folder", "`INTERNET`, `ACCESS_NETWORK_STATE` and `CHANGE_NETWORK_STATE`"):
            self.assertIn(expected, verified)
        still_open = flat(section(self.text, "What is open"))
        for expected in ("No program has run the app on a phone, and no test runs the sender.", "macOS on Apple Silicon", "converting and uploading on the phone, is planned"):
            self.assertIn(expected, still_open)

    def test_every_link_of_the_page_leads_somewhere(self):
        own = {anchor(heading) for heading in re.findall(r"(?m)^#{2,3} (.+)$", self.text)}
        links = re.findall(r"\]\(([^)]+)\)", self.said)
        self.assertGreaterEqual(len(links), 6)
        for link in links:
            path, _, part = link.partition("#")
            if path == "":
                self.assertIn(part, own, link)
                continue
            target = PAGE.parent / path
            self.assertTrue(target.is_file(), link)
            if part:
                headings = {anchor(heading) for heading in re.findall(r"(?m)^#{2,3} (.+)$", target.read_text(encoding="utf-8"))}
                self.assertIn(part, headings, link)

    def test_the_other_pages_point_to_it(self):
        for name, expected in (("docs/emulator.md", "## From a phone"), ("docs/wifi.md", "## A phone on a network without internet"), ("README.md", "(docs/android-app.md)"),
                               ("AGENTS.md", "| Change the operators' app | [docs/android-app.md](docs/android-app.md)"), ("agent/README.md", "the **operators' app**, `app/`")):
            self.assertIn(expected, (support.ROOT / name).read_text(encoding="utf-8"), name)
        self.assertIn("--lan", (support.ROOT / "docs" / "emulator.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
