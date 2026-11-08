import pathlib
import subprocess
import tempfile
import unittest

from . import FIRMWARE, ROOT
from .compiler import compiled
from core import build as core_build

# What the files host takes from its platform on the board, over a file system that keeps
# its files and folders in memory. Like the board's, it makes no folder for a file: a file
# whose folder is not there is refused.
PLATFORM = r"""
#pragma once
#include <algorithm>
#include <map>
#include <set>
#include <string>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

// A clock that goes on by a millisecond at every call.
inline int64_t esp_timer_get_time() {
  static int64_t now = 0;
  now += 1000;
  return now;
}

typedef int portMUX_TYPE;
#define portMUX_INITIALIZER_UNLOCKED 0
#define portENTER_CRITICAL(guard) ((void)(guard))
#define portEXIT_CRITICAL(guard) ((void)(guard))

#define ESP_IDF_VERSION_MAJOR 5
#define MALLOC_CAP_INTERNAL (1u << 0)
#define MALLOC_CAP_SPIRAM (1u << 1)
#define MALLOC_CAP_8BIT (1u << 2)
inline size_t heap_caps_get_free_size(unsigned) { return 0; }
inline void *heap_caps_aligned_alloc(size_t, size_t, unsigned) { return nullptr; }

// A file or a folder of the file system, open or closed. A default one is closed.
class File {
 public:
  File() : place(0), opened(false), folder(false) {}
  File(const std::string &named, bool isFolder) : path(named), place(0), opened(true), folder(isFolder) {}
  operator bool() const { return opened; }
  int read(uint8_t *buffer, size_t capacity);
  size_t write(const uint8_t *bytes, size_t length);
  bool seek(uint32_t offset);
  size_t size();
  void close() { opened = false; }
  bool isDirectory() { return folder; }

 private:
  std::string path;
  size_t place;
  bool opened;
  bool folder;
};

// Everything before the last slash of a path; empty for a path at the root.
inline std::string folderOf(const std::string &path) {
  const size_t slash = path.rfind('/');
  return slash == std::string::npos ? std::string() : path.substr(0, slash);
}

struct Storage {
  // The bytes of each file by its full path.
  std::map<std::string, std::string> files;
  // The folders besides the root, which is always there.
  std::set<std::string> folders;
  // The folders whose making is refused.
  std::set<std::string> unmakeable;
  // Every open for writing is refused, as by a storage that fails.
  bool writesRefused = false;
  unsigned mkdirCalls = 0;
  unsigned writeOpens = 0;

  bool hasFolder(const std::string &folder) const { return folder.empty() || folder == "/" || folders.count(folder) != 0; }

  File open(const char *path, const char *mode) {
    if (strcmp(mode, "w") == 0) {
      writeOpens++;
      if (writesRefused || !hasFolder(folderOf(path))) return File();
      files[path] = std::string();
      return File(path, false);
    }
    if (files.count(path) != 0) return File(path, false);
    if (hasFolder(path)) return File(path, true);
    return File();
  }

  bool exists(const char *path) const { return files.count(path) != 0 || hasFolder(path); }

  bool remove(const char *path) { return files.erase(path) != 0; }

  bool rename(const char *from, const char *to) {
    if (files.count(from) == 0 || !hasFolder(folderOf(to))) return false;
    const std::string bytes = files[from];
    files.erase(from);
    files[to] = bytes;
    return true;
  }

  bool mkdir(const char *path) {
    mkdirCalls++;
    if (folders.count(path) != 0) return true;
    if (files.count(path) != 0 || unmakeable.count(path) != 0 || !hasFolder(folderOf(path))) return false;
    folders.insert(path);
    return true;
  }

  size_t totalBytes() const { return 5111808; }
  size_t usedBytes() const { return 8192; }
};

static Storage storage;
#define ODRIG_FS storage

inline int File::read(uint8_t *buffer, size_t capacity) {
  if (!opened || folder || storage.files.count(path) == 0) return -1;
  const std::string &bytes = storage.files[path];
  const size_t count = place < bytes.size() ? std::min(capacity, bytes.size() - place) : 0;
  memcpy(buffer, bytes.data() + place, count);
  place += count;
  return (int)count;
}

inline size_t File::write(const uint8_t *bytes, size_t length) {
  if (!opened || folder || storage.files.count(path) == 0) return 0;
  std::string &held = storage.files[path];
  place = std::min(place, held.size());
  held.replace(place, length, reinterpret_cast<const char *>(bytes), length);
  place += length;
  return length;
}

inline bool File::seek(uint32_t offset) {
  if (!opened || folder || storage.files.count(path) == 0 || offset > storage.files[path].size()) return false;
  place = offset;
  return true;
}

inline size_t File::size() {
  if (folder || storage.files.count(path) == 0) return 0;
  return storage.files[path].size();
}
"""

# Runs the host functions on the file system of a scenario and prints each answer, and at
# three points the folders, the files, and the calls of `mkdir` and of opens for writing.
PROGRAM = r"""
#include "@FILES@"

namespace program {

std::string listed(const std::set<std::string> &items) {
  std::string text;
  for (const std::string &item : items) {
    if (!text.empty()) text += ",";
    text += item;
  }
  return text.empty() ? "-" : text;
}

void say(const char *name, long value) { printf("%s %ld\n", name, value); }

void sayPoint(const char *point) {
  std::set<std::string> held;
  for (const auto &file : storage.files) held.insert(file.first);
  printf("%s_folders %s\n", point, listed(storage.folders).c_str());
  printf("%s_files %s\n", point, listed(held).c_str());
  printf("%s_mkdir %u\n", point, storage.mkdirCalls);
  printf("%s_write_opens %u\n", point, storage.writeOpens);
}

}  // namespace program

int main(int argc, char **argv) {
  using program::say;
  using program::sayPoint;
  if (argc != 2) {
    fprintf(stderr, "usage: files-host <scenario>\n");
    return 2;
  }
  const std::string scenario = argv[1];
  storage.files["/cfg.json"] = "{}";
  if (scenario == "fresh") {
  } else if (scenario == "folder") {
    storage.folders.insert("/odrig");
  } else if (scenario == "refused") {
    storage.unmakeable.insert("/odrig");
  } else if (scenario == "failing") {
    storage.folders.insert("/odrig");
    storage.writesRefused = true;
  } else {
    fprintf(stderr, "no such scenario: %s\n", argv[1]);
    return 2;
  }
  odrig_host host = OdrigFiles::host();
  uint32_t freeBytes = 0, totalBytes = 0;
  uint8_t buffer[128];
  say("space", host.space(host.ctx, &freeBytes, &totalBytes));
  say("open", host.open(host.ctx, "mapping.json"));
  host.close(host.ctx);
  say("read_at", host.read_at(host.ctx, "a.odrg", 0, buffer, sizeof buffer));
  say("remove_before", host.remove(host.ctx, "upload.part"));
  sayPoint("start");
  say("write_open", host.write_open(host.ctx, "upload.part"));
  sayPoint("first");
  uint8_t given[100];
  for (size_t i = 0; i < sizeof given; i++) given[i] = (uint8_t)(i * 7 + 1);
  say("write", host.write(host.ctx, given, sizeof given));
  say("write_close", host.write_close(host.ctx));
  say("rename", host.rename(host.ctx, "upload.part", "a.odrg"));
  memset(buffer, 0, sizeof buffer);
  const int32_t back = host.read_at(host.ctx, "a.odrg", 0, buffer, sizeof buffer);
  say("read_back", back);
  say("read_back_same", back == (int32_t)sizeof given && memcmp(buffer, given, sizeof given) == 0 ? 1 : 0);
  say("remove", host.remove(host.ctx, "a.odrg"));
  say("write_open_again", host.write_open(host.ctx, "upload.part"));
  sayPoint("end");
  return 0;
}
"""


class TheStorageFolder(unittest.TestCase):
    """The files host of the board, compiled on this computer over a file system that, like
    the board's, makes no folder for a file."""

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
        cls.binary = compiled([work / "main.cpp"], work / "files-host", [work, ROOT / "core" / "include"])

    def answers(self, scenario):
        done = subprocess.run([str(self.binary), scenario], capture_output=True, text=True, encoding="utf-8")
        if done.returncode != 0:
            raise AssertionError(f"files-host {scenario}: status {done.returncode}: {done.stderr[-2000:]}")
        return dict(line.split(" ", 1) for line in done.stdout.splitlines())

    def pinned(self, scenario, expected):
        got = self.answers(scenario)
        self.assertEqual({name: got.get(name) for name in expected}, expected)

    def test_the_first_write_into_a_storage_without_the_folder_makes_it(self):
        self.pinned("fresh", {
            "space": "1", "write_open": "1",
            "first_folders": "/odrig", "first_files": "/cfg.json,/odrig/upload.part", "first_mkdir": "1", "first_write_opens": "2",
            "write": "1", "write_close": "1", "rename": "1", "read_back": "100", "read_back_same": "1", "remove": "1",
            "write_open_again": "1",
            "end_folders": "/odrig", "end_files": "/cfg.json,/odrig/upload.part", "end_mkdir": "1", "end_write_opens": "3",
        })

    def test_a_storage_with_the_folder_is_not_asked_for_it(self):
        self.pinned("folder", {
            "write_open": "1", "first_folders": "/odrig", "first_mkdir": "0", "first_write_opens": "1",
            "read_back": "100", "read_back_same": "1",
            "write_open_again": "1", "end_mkdir": "0", "end_write_opens": "2",
        })

    def test_a_folder_the_file_system_refuses_makes_the_write_fail(self):
        self.pinned("refused", {
            "write_open": "-1", "first_folders": "-", "first_files": "/cfg.json", "first_mkdir": "1", "first_write_opens": "1",
            "write": "-1", "write_close": "-1", "write_open_again": "-1",
            "end_folders": "-", "end_files": "/cfg.json", "end_mkdir": "2", "end_write_opens": "2",
        })

    def test_a_write_refused_in_a_present_folder_is_tried_once_more_and_fails(self):
        self.pinned("failing", {
            "write_open": "-1", "first_folders": "/odrig", "first_files": "/cfg.json", "first_mkdir": "1", "first_write_opens": "2",
            "write": "-1", "write_close": "-1", "write_open_again": "-1",
            "end_folders": "/odrig", "end_files": "/cfg.json", "end_mkdir": "2", "end_write_opens": "4",
        })

    def test_a_read_in_the_missing_folder_is_a_missing_file(self):
        self.pinned("fresh", {
            "space": "1", "open": "0", "read_at": "-1", "remove_before": "0",
            "start_folders": "-", "start_files": "/cfg.json", "start_mkdir": "0", "start_write_opens": "0",
        })


if __name__ == "__main__":
    unittest.main()
