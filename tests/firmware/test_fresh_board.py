"""Fresh firmware storage is initialized through the production transaction."""
import functools
import json
import pathlib
import subprocess
import tempfile
import unittest

from . import ROOT
from .compiler import compiled

PROGRAM = r'''
#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <map>
#include <set>
#include <string>
#include <iostream>
#include "odrig_bootstrap.h"

struct Interrupted {};
struct Store {
    std::map<std::string, std::string> files;
    std::set<std::string> folders;
    int cut = -1, fail = -1, operations = 0, badRead = -1, reads = 0;
    void changed() { if (operations++ == cut) throw Interrupted(); }
    bool allowed() { return operations != fail; }
    int kind(const char *name) {
        if (files.count(name)) return 1;
        return folders.count(name) ? 2 : 0;
    }
    bool only(const char *const *names, size_t count) {
        for (const auto &file : files) {
            bool found = false;
            for (size_t i = 0; i < count; ++i) if (file.first == names[i]) found = true;
            if (!found) return false;
        }
        for (const auto &folder : folders) {
            if (folder.empty()) continue;
            bool found = false;
            for (size_t i = 0; i < count; ++i) if (folder == names[i]) found = true;
            if (!found) return false;
        }
        return true;
    }
    bool empty(const char *name) {
        const std::string prefix = std::string(name) + "/";
        for (const auto &file : files) if (file.first.compare(0, prefix.size(), prefix) == 0) return false;
        for (const auto &folder : folders) if (folder.compare(0, prefix.size(), prefix) == 0) return false;
        return kind(name) == 2;
    }
    bool mkdir(const char *name) {
        if (!allowed()) return false;
        folders.insert(name); changed(); return true;
    }
    bool equals(const char *name, const char *bytes, size_t length) {
        if (reads++ == badRead) return false;
        return files.count(name) && files[name] == std::string(bytes, length);
    }
    bool write(const char *name, const char *bytes, size_t length) {
        if (!allowed()) { files[name] = std::string(bytes, length / 2); return false; }
        files[name] = std::string(bytes, length); changed(); return true;
    }
    bool rename(const char *from, const char *to) {
        if (!allowed() || kind(to) != 0 || kind(from) != 1) return false;
        files[to] = files[from]; files.erase(from); changed(); return true;
    }
    bool remove(const char *name) {
        if (!allowed()) return false;
        files.erase(name); changed(); return true;
    }
    bool rmdir(const char *name) {
        if (!allowed() || !empty(name)) return false;
        folders.erase(name); changed(); return true;
    }
};

int main(int argc, char **argv) {
    Store store;
    store.cut = argc > 1 ? atoi(argv[1]) : -1;
    store.fail = argc > 2 ? atoi(argv[2]) : -1;
    store.badRead = argc > 3 ? atoi(argv[3]) : -1;
    size_t count = 0;
    std::cin >> count;
    for (size_t i = 0; i < count; ++i) {
        std::string kind, name;
        size_t length = 0;
        std::cin >> kind >> name >> length; std::cin.get();
        if (name == ".") name.clear();
        if (kind == "dir") store.folders.insert(name);
        else {
            std::string value(length, '\0');
            if (length) std::cin.read(&value[0], length);
            store.files[name] = value;
        }
    }
    int result = -1;
    try { result = static_cast<int>(OdrigBootstrap::initialize(store)); } catch (Interrupted &) {}
    printf("result %d\noperations %d\nreads %d\n", result, store.operations, store.reads);
    for (const auto &folder : store.folders) printf("dir %s\n", folder.empty() ? "." : folder.c_str());
    for (const auto &file : store.files) {
        printf("file %s ", file.first.c_str());
        for (unsigned char byte : file.second) printf("%02x", byte);
        puts("");
    }
}
'''

_folder = tempfile.TemporaryDirectory(prefix="odrig-fresh-host-")


@functools.lru_cache(maxsize=1)
def fixture():
    work = pathlib.Path(_folder.name)
    source = work / "fresh.cpp"
    source.write_text(PROGRAM, encoding="utf-8", newline="\n")
    return compiled([source], work / "fresh", [ROOT / "firmware" / "usermod"])


def initialize(files=None, folders=(), cut=-1, fail=-1, bad_read=-1):
    """Run the production transaction and return its exact persisted file bytes."""
    files = {} if files is None else files
    pieces = [f"{len(files) + len(folders)}\n".encode()]
    for folder in folders:
        pieces.append(f"dir {folder or '.'} 0\n".encode())
    for name, value in files.items():
        pieces.extend((f"file {name} {len(value)}\n".encode(), value))
    done = subprocess.run([str(fixture()), str(cut), str(fail), str(bad_read)], input=b"".join(pieces), capture_output=True)
    if done.returncode:
        raise AssertionError(done.stderr.decode("utf-8", "replace"))
    result = {"files": {}, "folders": set()}
    for line in done.stdout.decode("ascii").splitlines():
        kind, _, rest = line.partition(" ")
        if kind == "file":
            name, _, value = rest.partition(" ")
            result["files"][name] = bytes.fromhex(value)
        elif kind == "dir":
            result["folders"].add("" if rest == "." else rest)
        else:
            result[kind] = int(rest)
    return result


def materialize(folder):
    """Create a native-emulator fixture from production bootstrap, without show fixtures."""
    result = initialize()
    folder = pathlib.Path(folder)
    if folder.exists() and any(folder.iterdir()):
        raise ValueError("the fresh-board fixture folder must be empty")
    folder.mkdir(parents=True, exist_ok=True)
    for name, value in result["files"].items():
        (folder / name).write_bytes(value)
    return result


class FreshBoard(unittest.TestCase):
    def test_empty_store_gets_the_canonical_square_and_a_dark_valid_empty_show(self):
        result = initialize()
        self.assertEqual(set(result["files"]), {"mapping.json", "show.json"})
        self.assertEqual(json.loads(result["files"]["mapping.json"]), json.loads((ROOT / "mapping" / "legs-20.json").read_bytes()))
        self.assertEqual(json.loads(result["files"]["show.json"]), {"version": 1, "brightness": 32, "items": []})
        self.assertEqual(result["folders"], {""})

    def test_each_interruption_recovers_without_replacing_existing_files(self):
        finished = initialize()
        for cut in range(finished["operations"]):
            with self.subTest(cut=cut):
                broken = initialize(cut=cut)
                recovered = initialize(broken["files"], broken["folders"])
                self.assertEqual(recovered["files"], finished["files"])
                self.assertEqual(recovered["folders"], {""})

    def test_failed_storage_operations_retry_including_short_writes(self):
        finished = initialize()
        for fail in range(finished["operations"]):
            with self.subTest(fail=fail):
                broken = initialize(fail=fail)
                recovered = initialize(broken["files"], broken["folders"])
                self.assertEqual(recovered["files"], finished["files"])

    def test_failed_readback_does_not_publish_unverified_files_and_retries(self):
        finished = initialize()
        for bad_read in range(finished["reads"]):
            with self.subTest(bad_read=bad_read):
                broken = initialize(bad_read=bad_read)
                recovered = initialize(broken["files"], broken["folders"])
                self.assertEqual(recovered["files"], finished["files"])

    def test_existing_complete_partial_and_unrelated_data_are_never_modified(self):
        cases = [{"mapping.json": b"operator map"}, {"show.json": b"operator show"},
                 {"saved.odrg": b"animation"}, {"cfg.json": b"WLED"},
                 {"rotation.txt": b"1 90\n"},
                 {"mapping.json": b"operator map", "show.json": b"operator show"}]
        for files in cases:
            with self.subTest(files=files):
                result = initialize(files, ("",))
                self.assertEqual(result["files"], files)
                self.assertEqual(result["operations"], 0)

    def test_own_interrupted_marker_does_not_replace_operator_changes(self):
        broken = initialize(cut=2)
        broken["files"]["mapping.json"] = b"operator mapping"
        result = initialize(broken["files"], broken["folders"])
        self.assertEqual(result["files"], broken["files"])
        self.assertEqual(result["operations"], 0)

    def test_rotation_saved_during_interrupted_initialization_is_preserved(self):
        broken = initialize(cut=1)
        broken["files"]["rotation.txt"] = b"1 90\n"
        broken["files"]["rotation.part"] = b"partial"
        result = initialize(broken["files"], broken["folders"])
        self.assertEqual(set(result["files"]), {"mapping.json", "show.json", "rotation.txt", "rotation.part"})
        self.assertEqual(result["files"]["rotation.txt"], b"1 90\n")
        self.assertEqual(result["files"]["rotation.part"], b"partial")
        self.assertEqual(result["folders"], {""})

    def test_foreign_folder_or_marker_contents_are_preserved(self):
        for files, folders in (({}, ("", "other")), ({"fresh-init/keep.txt": b"keep"}, ("", "fresh-init"))):
            with self.subTest(folders=folders):
                result = initialize(files, folders)
                self.assertEqual(result["files"], files)
                self.assertEqual(result["folders"], set(folders))
                self.assertEqual(result["operations"], 0)
