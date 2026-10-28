"""The collection in git: every animation file the installation has been given, with its
preview and its readme beside it; of a heavy file, a group of a long video or a file over
50,000,000 bytes, only its preview and its readme, its key and its path on the card in the
default preview catalog; and the lines of `.gitignore` that keep the heavy files out."""

import json
import pathlib
import re
import subprocess
import tempfile
import unittest
import zlib

from . import support

COLLECTION = "collection/"
FOLDERS = ("card", "earlier", "others", "long")
LABELS = ("File", "Key", "Animation", "Source", "Platform", "Uploader", "Title", "Media id", "Part", "Crop", "Fit", "Made with",
          "Converted", "Found", "Added", "Notes")
HEAVY_BYTES = 50_000_000
IGNORED = ("/collection/long/**/*.odrg", "/collection/long/**/*.odrgx")
ANIMATION = re.compile(r"\.odrgx?$", re.IGNORECASE)
ENTRY = re.compile(r'^  "([0-9a-f]{8}-[1-9][0-9]*)": (\{.*\}),$')
CARD_PATH = re.compile(r"its path on the card is (\S+)\.$")


def key_of(data):
    return f"{zlib.crc32(data):08x}-{len(data)}"


def catalog():
    """The default preview catalog: each key with its names."""
    text = (support.ROOT / "thumbnails" / "catalog.js").read_text(encoding="ascii")
    return {found.group(1): set(json.loads(found.group(2))["names"]) for found in map(ENTRY.match, text.splitlines()) if found}


def readme(path):
    """The values of a readme by their labels, after a check of its shape: a title line, an
    empty line and the sixteen lines in their order, UTF-8 with LF line ends."""
    data = (support.ROOT / path).read_bytes()
    if b"\r" in data:
        raise AssertionError(f"{path} holds a carriage return")
    lines = data.decode("utf-8").split("\n")
    if not (lines[0].startswith("# ") and lines[0][2:].strip() and lines[1] == ""):
        raise AssertionError(f"{path} does not begin with a title and an empty line")
    values = {}
    for label, line in zip(LABELS, lines[2:18]):
        found = re.fullmatch(rf"- {re.escape(label)}: (.+)", line)
        if found is None or not found.group(1).strip():
            raise AssertionError(f"{path}: the line of {label} is {line!r}")
        values[label] = found.group(1)
    if len(lines) < 18 or any(line != "" for line in lines[18:]):
        raise AssertionError(f"{path} does not end after its sixteen lines")
    return values


def named(value):
    """A value written in backticks."""
    found = re.fullmatch(r"`([^`]+)`", value)
    return None if found is None else found.group(1)


class TheCollection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tracked = support.tracked(COLLECTION)
        cls.files = set(cls.tracked)

    def test_it_holds_its_four_folders_and_its_readme_and_nothing_else(self):
        self.assertIn("collection/README.md", self.files)
        for folder in FOLDERS:
            self.assertTrue(any(path.startswith(f"{COLLECTION}{folder}/") for path in self.tracked), folder)
        for path in self.tracked:
            self.assertRegex(path, r"^collection/(README\.md|(card|earlier|others|long)/.+\.(odrg|odrgx|gif|md))$")

    def test_every_tracked_animation_file_has_its_preview_and_its_readme_beside_it(self):
        animations = [path for path in self.tracked if ANIMATION.search(path)]
        self.assertTrue(animations)
        for path in animations:
            with self.subTest(path=path):
                bare = ANIMATION.sub("", path)
                self.assertIn(f"{bare}.gif", self.files)
                self.assertIn(f"{bare}.md", self.files)
                key = key_of((support.ROOT / path).read_bytes())
                self.assertEqual((support.ROOT / f"{bare}.gif").read_bytes(), (support.ROOT / "thumbnails" / f"{key}.gif").read_bytes())
                values = readme(f"{bare}.md")
                self.assertEqual((named(values["File"]), named(values["Key"])), (pathlib.PurePosixPath(path).name, key))

    def test_a_heavy_file_has_its_preview_its_readme_and_its_path_on_the_card_tracked(self):
        keys = catalog()
        readmes = [path for path in self.tracked if path.startswith(f"{COLLECTION}long/") and path.endswith(".md")]
        gifs = [path for path in self.tracked if path.startswith(f"{COLLECTION}long/") and path.endswith(".gif")]
        self.assertTrue(readmes)
        self.assertEqual(sorted(path[:-3] for path in readmes), sorted(path[:-4] for path in gifs))
        for path in readmes:
            with self.subTest(path=path):
                values = readme(path)
                name, key = named(values["File"]), named(values["Key"])
                self.assertRegex(name, ANIMATION)
                self.assertEqual(ANIMATION.sub("", name), pathlib.PurePosixPath(path).stem)
                self.assertIn(key, keys)
                self.assertEqual((support.ROOT / f"{path[:-3]}.gif").read_bytes(), (support.ROOT / "thumbnails" / f"{key}.gif").read_bytes())
                inside = path[len(f"{COLLECTION}long/"):]
                if "/" in inside:
                    card = "long/" + inside.rsplit("/", 1)[0] + "/" + name
                else:
                    found = CARD_PATH.search(values["Notes"])
                    self.assertIsNotNone(found, values["Notes"])
                    card = found.group(1)
                self.assertIn(card, keys[key])

    def test_no_tracked_file_is_heavy_and_no_animation_file_of_long_is_tracked(self):
        for path in support.tracked():
            if (support.ROOT / path).is_file():
                self.assertLessEqual((support.ROOT / path).stat().st_size, HEAVY_BYTES, path)
        self.assertEqual([path for path in self.tracked if path.startswith(f"{COLLECTION}long/") and ANIMATION.search(path)], [])

    def test_gitignore_keeps_out_the_animation_files_of_long_and_nothing_else(self):
        lines = (support.ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
        for line in IGNORED:
            self.assertIn(line, lines)
        with tempfile.TemporaryDirectory() as work:
            # A git of its own, so that no exclude of one computer counts.
            subprocess.run(["git", "init", "-q", work], check=True)
            empty = pathlib.Path(work, "excluded-nothing")
            empty.write_text("")

            def ignored(path):
                asked = ["git", "-c", f"core.excludesFile={empty}", "--git-dir", str(pathlib.Path(work, ".git")), "--work-tree", str(support.ROOT),
                         "check-ignore", "--no-index", "-q", path]
                return subprocess.run(asked, cwd=support.ROOT).returncode == 0

            for path in ("collection/long/a.odrg", "collection/long/yt-a/a_01.odrg", "collection/long/a.odrgx"):
                self.assertTrue(ignored(path), path)
            for path in ("collection/long/a.gif", "collection/long/a.md", "collection/card/a.odrg", "collection/README.md"):
                self.assertFalse(ignored(path), path)


if __name__ == "__main__":
    unittest.main()
