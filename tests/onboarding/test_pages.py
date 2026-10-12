import re
import shlex
import unittest

from . import support

# The four ways of staging that no commit of this repository uses.
BROAD_STAGING = (["git", "add", "-A"], ["git", "add", "."], ["git", "add", "-u"], ["git", "commit", "-a"])

# What a page must not hold: a path into a home folder, an address of a person or of a
# board, and a serial device with its number.
PRIVATE = {
    "a path into a home folder": re.compile(r"/Users/|/home/|~/|[A-Za-z]:\\Users"),
    "an e-mail address": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+\.[A-Za-z]{2,}"),
    "a hardware address": re.compile(r"\b[0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5}\b"),
    "a numbered serial device": re.compile(r"usbmodem[0-9]"),
}

# Words for what is planned and not yet in the repository.
PLANNED = re.compile(r"Android|Capacitor|Tauri|\bseeds? 0?[7-9]\b")
WHERE_THE_PLANNED_IS_NAMED = (support.ENTRY, "What is coming")

# A command that converts, checks or packs with the reference converter, which no page gives.
WITH_THE_REFERENCE = re.compile(r"\S*python\S* -m odrig (?:import|encode|decode|check|pack)\b")

COPIED_FROM = 60


def paths_named(text):
    """Every path a page names: in a code span of its prose, or as a word of a command."""
    words = [span for span in support.spans(text) if " " not in span]
    for _, command in support.page_commands(text):
        words += shlex.split(command)
    for span in support.spans(text):
        if support.is_command(span):
            words += shlex.split(span)
    return sorted({word for word in words if support.is_path(word) and support.looked_for(word)})


def broken_links(page, text):
    """The links of a page that lead to no file of the repository, or to no heading of it."""
    broken = []
    folder = (support.ROOT / page).parent
    for target in support.links(text):
        if re.match(r"[a-z]+:", target):
            continue
        name, _, part = target.partition("#")
        path = (folder / name).resolve() if name else support.ROOT / page
        inside = path == support.ROOT or support.ROOT in path.parents
        if not inside or not support.exists(str(path.relative_to(support.ROOT))):
            broken.append(target)
        elif part and part not in [support.anchor(heading) for heading in support.headings(path.read_text(encoding="utf-8"))]:
            broken.append(target)
    return broken


def given(text):
    """Every command a page gives: in a command block, or as a code span of its prose."""
    return [command for _, command in support.page_commands(text)] + [span for span in support.spans(text) if support.is_command(span)]


def refused(text):
    """`command: what is wrong` for every command of a page that its tool does not take."""
    found = []
    for command in given(text):
        wrong = support.refusal(command)
        if wrong is not None:
            found.append(f"{command}: {wrong}")
    return found


class EveryPage(unittest.TestCase):
    def pages(self):
        self.assertGreaterEqual(len(support.PAGES), 1)
        return [(page, support.read(page)) for page in support.PAGES]

    def test_every_path_it_names_exists(self):
        for page, text in self.pages():
            with self.subTest(page=page):
                missing = [word for word in paths_named(text) if not support.exists(word)]
                self.assertEqual(missing, [])

    def test_every_link_leads_to_a_file_of_the_repository_and_to_a_heading_it_has(self):
        for page, text in self.pages():
            with self.subTest(page=page):
                self.assertEqual(broken_links(page, text), [])

    def test_every_command_is_understood_by_the_tool_it_names(self):
        for page, text in self.pages():
            with self.subTest(page=page):
                self.assertEqual(refused(text), [])

    def test_every_command_that_converts_checks_or_packs_starts_the_converter(self):
        converting = 0
        for page, text in self.pages():
            with self.subTest(page=page):
                self.assertEqual([command for command in given(text) if WITH_THE_REFERENCE.match(command)], [])
                converting += sum(command.startswith(f"{support.NODE} {support.CONVERTER} ") for command in given(text))
        self.assertGreaterEqual(converting, 4)

    def test_no_command_block_stages_broadly(self):
        for page, text in self.pages():
            with self.subTest(page=page):
                for _, command in support.page_commands(text):
                    words = shlex.split(command)
                    for form in BROAD_STAGING:
                        self.assertFalse(words[:2] == form[:2] and form[2] in words, command)

    def test_it_is_short_enough_to_be_read_in_full(self):
        for page, text in self.pages():
            with self.subTest(page=page):
                limit = support.ENTRY_LINES if page == support.ENTRY else support.PAGE_LINES
                self.assertLessEqual(len(text.splitlines()), limit)

    def test_it_names_nothing_private(self):
        for page, text in self.pages():
            with self.subTest(page=page):
                for what, shape in PRIVATE.items():
                    self.assertIsNone(shape.search(text), what)

    def test_no_line_of_its_prose_is_a_line_of_a_governing_document(self):
        theirs = set()
        for name in support.governing():
            theirs.update(line.strip() for line in support.read(name).splitlines())
        for page, text in self.pages():
            with self.subTest(page=page):
                copied = [line.strip() for line in support.prose(text).splitlines() if len(line.strip()) >= COPIED_FROM and line.strip() in theirs]
                self.assertEqual(copied, [])

    def test_what_is_planned_is_named_in_one_place(self):
        for page, text in self.pages():
            with self.subTest(page=page):
                if page == WHERE_THE_PLANNED_IS_NAMED[0]:
                    heading = WHERE_THE_PLANNED_IS_NAMED[1]
                    text = text.replace(support.section(text, heading), "")
                self.assertIsNone(PLANNED.search(text))


class TheChecks(unittest.TestCase):
    """The checks above find what they look for."""

    def test_a_path_is_told_from_other_words(self):
        for word in ("mapping/legs-2.json", "docs/", "requirements.txt", "show.json", "animations/NAME.json", "docs/specs/<seed>/tasks.md"):
            self.assertTrue(support.is_path(word) and support.exists(word), word)
        for word in ("docs/nothing.md", "nothing.json", "mapping/legs-NAME.txt", "tests/nothing/"):
            self.assertTrue(support.is_path(word) and not support.exists(word), word)
        for word in ("status", ".odrg", "(x, y)", "127.0.0.1:8600", "--mapping", "/odrig", "<id>"):
            self.assertFalse(support.is_path(word), word)
        for word in ("build/demo-20/show", ".venv/bin/python", "converter/node_modules/", "esp32-backup/", "firmware/wled-16.0.1/", "mapping.json", "origin/master"):
            self.assertFalse(support.looked_for(word), word)

    def test_a_seed_that_is_named_ahead_of_this_branch_is_on_master(self):
        for folder in support.SEEDS_ON_MASTER:
            self.assertFalse(support.looked_for(folder))
            self.assertTrue(support.exists(folder) or support.on_master(folder), folder)
        self.assertFalse(support.on_master("project-seeds/00-nothing/"))

    def test_the_two_folders_of_the_first_computer_are_not_tracked(self):
        self.assertEqual(support.tracked(*support.FIRST_COMPUTER_ONLY), [])

    def test_a_link_is_followed_to_its_file_and_its_heading(self):
        page = "agent/vocabulary.md"
        good = "[a](../docs/format.md) [b](../docs/format.md#json-frames) [c](../mapping/legs-2.json) [d](https://example.org/x) [e](#the-programs) [f](working-rules.md)"
        self.assertEqual(broken_links(page, good), [])
        bad = "[a](format.md) [b](../docs/format.md#no-such-heading) [c](../../elsewhere.md) [d](#no-such-heading)"
        self.assertEqual(broken_links(page, bad), ["format.md", "../docs/format.md#no-such-heading", "../../elsewhere.md", "#no-such-heading"])
        self.assertEqual(support.anchor("The owner's checks"), "the-owners-checks")

    def test_a_command_is_given_to_its_tool(self):
        for command in (
            "node converter/odrig.js pack --show shows/demo-20/show.json --mapping mapping/legs-20.json --sources build/s --out build/o",
            "node converter/odrig.js import build/x.gif build/x.json --mapping mapping/legs-20.json --fit fit --start 12.5 --duration 4",
            "node converter/odrig.js check build/x.json",
            "node converter/odrig.js",
            "node --version",
            "npm ci --prefix converter",
            "npm test --prefix converter",
            ".venv/bin/python -m odrig pack --show shows/demo-20/show.json --mapping mapping/legs-20.json --sources build/s --out build/o",
            ".venv/bin/python -m emulator build/demo-20/show --record build/x.odrr --seconds 2",
            ".venv/bin/python -m odrigctl --port build/emulator/serial play 2",
            ".venv/bin/python -m odrig.generators.hello_world build/hello.json --mapping mapping/legs-20.json",
            "python3 -m unittest discover -s tests/onboarding -t .",
            "python3 -m venv .venv",
            ".venv/bin/python -m pip install -r requirements.txt",
            "python3 firmware/fw.py test",
            "make -C core test",
            "make -C core shared",
            "git add <path> ...",
            "git clone https://github.com/korenmic/Odrig.git",
            "git fetch origin",
            "git merge --ff-only origin/master",
            "git push origin master",
            "printf '1000 status\\n' > build/ask.txt",
            "python -m odrig",
        ):
            self.assertIsNone(support.refusal(command), command)
        for command, said in (
            ("node converter/odrig.js check build/x.json --nope", "there is no option --nope"),
            ("node converter/odrig.js pack --show shows/demo-20/show.json", "--mapping, --sources and --out are missing"),
            ("node converter/odrig.js bake", "there is no subcommand bake"),
            ("node converter/odrig.js import build/x.gif build/x.json --mapping mapping/legs-20.json --fit wide", "which is not fill, fit or stretch"),
            ("node build/x.js", "node starts the converter"),
            ("npm install", "npm is run as npm ci --prefix converter"),
            ("npm test", "npm is run as npm ci --prefix converter"),
            (".venv/bin/python -m odrig check build/x.json --nope", "unrecognized arguments: --nope"),
            (".venv/bin/python -m odrig pack --show shows/demo-20/show.json", "arguments are required"),
            (".venv/bin/python -m odrig bake", "invalid choice"),
            (".venv/bin/python -m emulator build/show --seconds 2", "belong to record mode"),
            (".venv/bin/python -m odrigctl --port build/emulator/serial play", "takes one argument"),
            (".venv/bin/python -m odrig.generators.nothing build/x.json", "no module"),
            ("python3 -m unittest tests/onboarding/test_pages.py", "by discovery"),
            ("python3 -m unittest discover -s tests/nothing -t .", "holds no test"),
            ("python3 firmware/fw.py bake", "invalid choice"),
            ("make -C core everything", "no target everything"),
            ("brew install python", "does not know"),
        ):
            self.assertIn(said, support.refusal(command) or "", command)

    def test_a_command_of_the_reference_converter_is_told_from_the_other_commands_of_python(self):
        for command in (".venv/bin/python -m odrig pack --show build/show.json", "python -m odrig import build/x.gif build/x.json", "python3 -m odrig check build/x.json"):
            self.assertIsNotNone(WITH_THE_REFERENCE.match(command), command)
        for command in ("python -m odrig", ".venv/bin/python -m odrig.generators.dvd_bounce build/dvd.json --mapping mapping/legs-20.json",
                        ".venv/bin/python -m odrigctl --port build/emulator/serial play 2", "node converter/odrig.js pack --show build/show.json"):
            self.assertIsNone(WITH_THE_REFERENCE.match(command), command)

    def test_the_text_of_a_page_is_split_into_prose_blocks_and_commands(self):
        text = "# T\n\n## One\n\nSee `a/b` and `python -m odrig`.\n\n```sh\nmkdir -p build/x\npython3 -m odrig check \\\n    build/x/a.json\n```\n\n## Two\n\n```text\nprinted\n```\n"
        self.assertEqual([(block.heading, block.mark) for block in support.blocks(text)], [("One", "sh"), ("Two", "text")])
        self.assertEqual(support.page_commands(text), [("One", "mkdir -p build/x"), ("One", "python3 -m odrig check build/x/a.json")])
        self.assertEqual(support.spans(text), ["a/b", "python -m odrig"])
        self.assertNotIn("printed", support.prose(text))
        self.assertEqual(support.section(text, "One").count("```"), 2)


if __name__ == "__main__":
    unittest.main()
