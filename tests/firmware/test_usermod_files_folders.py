"""The numbered folders of the board's storage in the files host, compiled on this computer over
the file system of test_usermod_files_host: stored names `<n>/<name>`, `make_folder` and
`remove` of `<n>`, and the blocks a folder takes."""

import pathlib
import subprocess
import tempfile
import unittest

from . import FIRMWARE, ROOT
from .compiler import compiled
from .test_usermod_files_host import PLATFORM
from core import build as core_build

PROGRAM = r"""
#include "@FILES@"

namespace program {

void say(const char *name, long value) { printf("%s %ld\n", name, value); }

std::string listed(const std::set<std::string> &items) {
  std::string text;
  for (const std::string &item : items) {
    if (!text.empty()) text += ",";
    text += item;
  }
  return text.empty() ? "-" : text;
}

long freeBytes(const odrig_host &host) {
  uint32_t free = 0, total = 0;
  host.space(host.ctx, &free, &total);
  return (long)free;
}

}  // namespace program

int main(int argc, char **argv) {
  using program::say;
  if (argc != 2) return 2;
  const std::string scenario = argv[1];
  if (scenario == "folder") storage.folders.insert("/odrig");
  odrig_host host = OdrigFiles::host();
  const long before = program::freeBytes(host);
  say("make", host.make_folder(host.ctx, "12"));
  say("made_blocks", (before - program::freeBytes(host)) / 4096);
  say("make_again", host.make_folder(host.ctx, "12"));
  say("make_again_blocks", (before - program::freeBytes(host)) / 4096);
  for (const char *name : {"0", "012", "256", "a", "1a", "12/", "drive/12"}) say((std::string("make_") + name).c_str(), host.make_folder(host.ctx, name));
  say("write_open", host.write_open(host.ctx, "upload.part"));
  const uint8_t bytes[3] = {1, 2, 3};
  say("write", host.write(host.ctx, bytes, sizeof bytes));
  say("write_close", host.write_close(host.ctx));
  say("rename", host.rename(host.ctx, "upload.part", "12/a.odrg"));
  uint8_t buffer[8] = {0};
  say("read_at", host.read_at(host.ctx, "12/a.odrg", 1, buffer, sizeof buffer));
  say("read_at_byte", buffer[0]);
  say("open", host.open(host.ctx, "12/a.odrg"));
  host.close(host.ctx);
  for (const char *name : {"0/a.odrg", "256/a.odrg", "a/b.odrg", "12/A.odrg", "12/x/a.odrg", "/a.odrg"}) say((std::string("open_") + name).c_str(), host.open(host.ctx, name));
  say("write_into_missing", host.write_open(host.ctx, "13/b.odrg"));
  say("remove_full", host.remove(host.ctx, "12"));
  say("remove_file", host.remove(host.ctx, "12/a.odrg"));
  const long emptied = program::freeBytes(host);
  say("remove_empty", host.remove(host.ctx, "12"));
  say("removed_blocks", (program::freeBytes(host) - emptied) / 4096);
  say("remove_none", host.remove(host.ctx, "12"));
  printf("folders %s\n", program::listed(storage.folders).c_str());
  printf("mkdir %u\n", storage.mkdirCalls);
  return 0;
}
"""


class NumberedFolders(unittest.TestCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        if core_build.find().kind != "gnu":
            raise unittest.SkipTest("the files host uses __builtin_ctz, which needs a GNU-style host compiler")
        cls.folder = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.folder.cleanup)
        work = pathlib.Path(cls.folder.name)
        (work / "odrig_platform.h").write_text(PLATFORM, encoding="utf-8", newline="\n")
        source = (FIRMWARE / "usermod" / "odrig_files.cpp").as_posix()
        (work / "main.cpp").write_text(PROGRAM.replace("@FILES@", source), encoding="utf-8", newline="\n")
        cls.binary = compiled([work / "main.cpp"], work / "folders-host", [work, ROOT / "core" / "include"])

    def answers(self, scenario):
        done = subprocess.run([str(self.binary), scenario], capture_output=True, text=True, encoding="utf-8")
        if done.returncode != 0:
            raise AssertionError(f"folders-host {scenario}: status {done.returncode}: {done.stderr[-2000:]}")
        return dict(line.split(" ", 1) for line in done.stdout.splitlines())

    def test_a_numbered_folder_is_made_once_and_takes_two_blocks(self):
        got = self.answers("folder")
        self.assertEqual({name: got[name] for name in ("make", "made_blocks", "make_again", "make_again_blocks")},
                         {"make": "1", "made_blocks": "2", "make_again": "1", "make_again_blocks": "2"})
        for name in ("0", "012", "256", "a", "1a", "12/", "drive/12"):
            self.assertEqual(got[f"make_{name}"], "-1", name)

    def test_a_stored_name_is_a_file_of_its_numbered_folder(self):
        got = self.answers("folder")
        self.assertEqual({name: got[name] for name in ("write_open", "write", "write_close", "rename", "read_at", "read_at_byte", "open", "write_into_missing")},
                         {"write_open": "1", "write": "1", "write_close": "1", "rename": "1", "read_at": "2", "read_at_byte": "2", "open": "1", "write_into_missing": "-1"})
        for name in ("0/a.odrg", "256/a.odrg", "a/b.odrg", "12/A.odrg", "12/x/a.odrg", "/a.odrg"):
            self.assertEqual(got[f"open_{name}"], "-1", name)

    def test_a_numbered_folder_is_removed_only_while_it_is_empty(self):
        got = self.answers("folder")
        self.assertEqual({name: got[name] for name in ("remove_full", "remove_file", "remove_empty", "removed_blocks", "remove_none", "folders")},
                         {"remove_full": "-1", "remove_file": "1", "remove_empty": "1", "removed_blocks": "2", "remove_none": "0", "folders": "/odrig"})

    def test_only_a_write_makes_the_folder_of_the_show(self):
        got = self.answers("fresh")
        self.assertEqual((got["make"], got["mkdir"]), ("-1", "4"))
        self.assertEqual(got["folders"], "/odrig")


if __name__ == "__main__":
    unittest.main()
