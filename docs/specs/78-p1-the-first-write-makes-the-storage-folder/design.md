# Design

## Boundaries

One source, one function, one constant: `firmware/usermod/odrig_files.cpp` gets
`FOLDER_PATH` beside `FOLDER`, and its `beginFile()`, the board's `write_open`, tries
the open once more after `ODRIG_FS.mkdir(FOLDER_PATH)` when the first open fails. The
folder is the host's to make: the host contract of `docs/core.md` (lines 80-137) and
`core/include/odrig_core.h` (lines 42-45, `write_open` "Begins a new, empty file of this
name") names no folder and no call to make one, the core knows no paths, and the test
host of `tests/core/host/` and the emulator's host of `emulator/host.py` have their
folders before the core starts. So `core/`, `odrig_core.h`, `docs/core.md`,
`docs/commands.md`, `app/`, `emulator/`, `firmware/fwtool/`,
`firmware/usermod/odrig_drive.cpp`, `firmware/usermod/odrig_usermod.cpp`, both platform
headers and the standalone firmware are not changed; no command, reply member or error
code is added; no wiring, power or LED is touched; no APK is built. The tests are a
text rule in its new form, a new host test that runs the source on this computer, and a
guard of the file-system rule; the pages are `docs/firmware.md` and a drift entry.

## The folder made by `write_open`

`firmware/usermod/odrig_files.cpp`, lines 7 and after, verbatim, the constant and its
comment added after `FOLDER`:

```cpp
const char FOLDER[] = "/odrig/";
// The folder itself, as the file system names it. A storage that was formatted and never
// had a show has none, and the file system makes no folder for a file.
const char FOLDER_PATH[] = "/odrig";
```

In `beginFile()` (lines 185-208), lines 200-203 become, verbatim, the comment's second
sentence and the third line added:

```cpp
  // A file that has the name is emptied. A storage without the folder gets it first.
  const size_t before = sizeAt(path);
  writtenFile = ODRIG_FS.open(path, "w");
  if (!writtenFile && ODRIG_FS.mkdir(FOLDER_PATH)) writtenFile = ODRIG_FS.open(path, "w");
  if (!writtenFile) return -1;
```

- `Timed timed;` stays the first line of `beginFile()`, the given-up file is removed as
  today, and `pathOf(name, path)`, `dropSecond(name)`, `blocksFreed(before)`,
  `strcpy(writtenName, name)` and `writtenBytes = 0` stay where they are. Nothing else
  of the source changes: `openNamed()`, `readAt()`, `removeFile()`, `renameFile()`,
  `sizeAt()`, `askSpace()` and `tellSpace()` keep taking a missing folder for missing
  files, which is what lets the start pass.
- Why this is enough. On the board `ODRIG_FS` is `WLED_FS`, `LittleFS`
  (`firmware/usermod/wled/odrig_platform.h:8`); `FS::open(path, mode, create = false)`
  (`libraries/FS/src/FS.h:91` of `framework-arduinoespressif32` 3.3.12) makes no folder
  for a write without `create` and goes to `fopen` (`vfs_api.cpp:316-321`), which
  littlefs refuses for a path whose folder is missing. `FS::mkdir()` (`FS.h:103`) is
  `VFSImpl::mkdir()` (`vfs_api.cpp:165-216`): it `stat`s the path and answers true for a
  folder that exists and false for a file (190-197), and otherwise, after an `opendir`
  that fails on littlefs for a missing folder (206-211), what `::mkdir` answers
  (213-215). Littlefs's own `LFS_ERR_EXIST` is never reached from here. So:
  - on a storage without the folder: one failed open, one `mkdir` that makes it, one
    open that succeeds; `write_open` answers 1;
  - on a storage with the folder: one open that succeeds; no `mkdir`, no time;
  - on a storage with the folder whose open fails, as by a fault of the flash: one
    `mkdir` that answers true, one more open that fails, -1 as today;
  - when `mkdir` is refused, a folder that cannot be made or a file of that name: no
    second open, -1 as today.

  There is no loop: one `mkdir` at most, two opens at most, and no state kept across
  calls, so the next `write_open` whose open fails asks again.
- Every file the core writes gets the folder, requirement 1.7. Each begins with
  `write_open` (`core/include/odrig_core.h:42-45`), and `beginFile()` puts every name
  under `FOLDER` through `pathOf()` (line 137), whatever the name: `upload.part` at
  `upload begin` (`core/src/upload.cpp:192`); `pending.txt` in `write_pending()`
  (`core/src/storage.cpp:44-51`); `mapping.part` of `persist()`
  (`core/src/mapping_control.cpp:97`) and of seed 76's `mapping_materialize()`;
  `show.part` in `content_write_show()` (`core/src/content.cpp:505`); and the `.part`
  files of the settings, `brightness.part`, `clocks.part`, `ignored.part`,
  `order.part`, `playlist.part` and `repeats.part`. `renameFile()` and `readAt()` (lines
  234 and 271) then find the folder the first write made. So on a storage without the
  folder the `upload data` lines, which add bytes to the `upload.part` that
  `upload begin` opened, and the `upload end`, whose `storage_install_upload()`
  (`core/src/storage.cpp:244`) writes `pending.txt`, puts the file in place and writes
  `show.part` before renaming it to `show.json`, with seed 76 `mapping.json` beside it,
  pass as they do on a storage with the folder. The host test pins this with
  `upload.part`, the first wall, and its write, rename and read; no case per name is
  added, since `beginFile()` treats every name alike.
- The path given to `mkdir` is `/odrig`, without the slash, the form `VFSImpl::mkdir()`
  and littlefs document; `FOLDER` keeps its slash as the prefix of every file path,
  pinned by `tests/firmware/test_usermod_files.py:374`.
- Not chosen: `open(path, "w", true)`, which walks and makes the folders of the path at
  every write of every board and hides the call from the text rule; a `mkdir` at the
  start or in the usermod's `setup()`, which would make the firmware decide to write and
  break seed 76's requirement 3.1, that the start writes nothing; a folder made for
  `upload.part` alone, which would fail at the next write of another name until an
  upload has made the folder: a mapping or a setting saved from the phone first writes
  its `.part` into the missing folder and is refused, as `upload begin` is now; a folder
  call in the host contract, which would reach every host for one platform's rule.
- What it costs. Memory: one more string constant in flash; `VFSImpl::mkdir()` builds one
  path on the heap and frees it on every return. Storage: two blocks, 8,192 bytes, once;
  `usedBlocks` (line 35) is not told, so `tellSpace()` reports 8 KB more free than there
  is until the next start, within the 0.1 MB the app shows. Time: both opens and the
  `mkdir` lie inside the `Timed` of `beginFile()` (line 186), so the pacing of
  `holding()` (lines 330-344) holds the next command line for twice their time, once.
- The standalone firmware compiles the same source through
  `firmware/standalone/src/shared_files.cpp`, its platform header giving `ODRIG_FS
  LittleFS` (`firmware/standalone/platform/odrig_platform.h:11`), the same Arduino `FS`
  class with `mkdir`; the shared source still names neither `wled.h` nor `WLED_FS`.

## The host test

`tests/firmware/test_usermod_files_host.py`, new, found by discovery, class
`TheStorageFolder`, docstring "The files host of the board, compiled on this computer
over a file system that, like the board's, makes no folder for a file."

- The build, in `setUpClass`, after the pattern of `tests/firmware/test_usermod_sd.py`
  (its `WLED` stand-in, lines 15-69, its program, 195-841, the source included at 202 and
  `main` at 333, and its build, 844-877), with `compiled()` of
  `tests/firmware/compiler.py` as `tests/firmware/test_usermod_kept.py` uses it: when
  `core_build.find().kind` is not `"gnu"`, `unittest.SkipTest`, "the files host uses
  __builtin_ctz, which needs a GNU-style host compiler", as `test_usermod_sd.py:865-867`
  skips, since `odrig_files.cpp:74` uses `__builtin_ctz`; a
  `tempfile.TemporaryDirectory()` cleaned up with the class; `odrig_platform.h` and
  `main.cpp` written into it with `encoding="utf-8", newline="\n"`; then `compiled([work /
  "main.cpp"], work / "files-host", [work, ROOT / "core" / "include"])`, so that `#include
  "odrig_platform.h"` (`odrig_files.cpp:3`), which no file beside the sources answers
  (`test_usermod_files.py:101-102`), takes the stand-in, `#include "odrig_files.h"` is
  found beside the source, and `odrig_core.h` (`odrig_files.h:8`) in `core/include`.
  `compiled()` gives `-std=c++11 -Wall -Wextra -Werror` and the core's runtime checks: the
  stand-in has no signed and unsigned comparison, no unused parameter that is named and no
  bare `__attribute__`.
- The stand-in `odrig_platform.h`, C++11, supplies what the source takes from `wled.h`
  on the board:
  - `<algorithm>`, `<map>`, `<set>`, `<string>`, `<stddef.h>`, `<stdint.h>`,
    `<stdio.h>` and `<string.h>`;
  - `int64_t esp_timer_get_time()`, a clock that goes on by 1,000 at every call;
  - `typedef int portMUX_TYPE;`, `portMUX_INITIALIZER_UNLOCKED` 0, and
    `portENTER_CRITICAL(guard)` and `portEXIT_CRITICAL(guard)` as `((void)(guard))`;
  - `ESP_IDF_VERSION_MAJOR` 5, `MALLOC_CAP_INTERNAL`, `MALLOC_CAP_SPIRAM` and
    `MALLOC_CAP_8BIT` as distinct bits, `size_t heap_caps_get_free_size(unsigned)`
    answering 0 and `void *heap_caps_aligned_alloc(size_t, size_t, unsigned)` answering
    `nullptr`, never called by the program;
  - `File`: a path, a place, whether it is open, whether it is a folder; a default
    `File` is closed; `operator bool() const`, `int read(uint8_t *, size_t)`, `size_t
    write(const uint8_t *, size_t)`, `bool seek(uint32_t)`, `size_t size()`, `void
    close()` and `bool isDirectory()`, reading and writing the bytes the file system
    holds for the path, `read` answering -1 for a file that is gone;
  - the file system, a `struct Storage` with `std::map<std::string, std::string> files`,
    the bytes of each file by its full path; `std::set<std::string> folders`, the folders
    it has besides the root, which is always there; `std::set<std::string> unmakeable`,
    the folders whose `mkdir` it refuses; `bool writesRefused`; and the counters
    `unsigned mkdirCalls` and `unsigned writeOpens`; one object of it, `storage`, and
    `#define ODRIG_FS storage`. Its functions model the Arduino layer the firmware
    calls, not littlefs beneath it:
    - `File open(const char *path, const char *mode)`: for `"r"`, the file of the path,
      a folder `File` for a folder, a closed `File` otherwise; for `"w"`, counts one in
      `writeOpens`, and gives a closed `File` while `writesRefused` is set or when the
      folder of the path, everything before its last `/`, is neither the root nor in
      `folders`, as littlefs refuses a file in a missing folder through `fopen`;
      otherwise it empties or makes the file and gives it open for writing;
    - `bool exists(const char *)`: true for a file or a folder it has, as the VFS's is;
    - `bool remove(const char *)`: removes a file it has, else false;
    - `bool rename(const char *from, const char *to)`: false when `from` is no file or
      the folder of `to` is missing, else the file takes the new name, replacing one
      that had it;
    - `bool mkdir(const char *)`: counts one in `mkdirCalls`; true for a folder it has,
      as `VFSImpl::mkdir()` answers; false for a file of that name or a folder in
      `unmakeable`; otherwise makes the folder and answers true;
    - `size_t totalBytes()` 5,111,808, the spare's storage, and `size_t usedBytes()`
      8,192.
  The members of `File` that read the file system are defined after `storage`.
- The program `main.cpp`: `#include` of `firmware/usermod/odrig_files.cpp` by its
  absolute path, as `test_usermod_sd.py` includes `odrig_drive.cpp`; `main(argc, argv)`
  takes one scenario on its command line, `files-host <scenario>`, sets up `storage`,
  each scenario holding `/cfg.json`, `{}`, at the root as WLED's own file:
  - `fresh`: no folder, as a storage WLED formatted;
  - `folder`: `/odrig` in `folders`;
  - `refused`: no folder, and `/odrig` in `unmakeable`;
  - `failing`: `/odrig` in `folders`, and `writesRefused` set;
  - any other: a line on standard error and exit status 2.

  Then it takes `odrig_host host = OdrigFiles::host();` and prints one line per answer,
  `<name> <value>`, in this order, a list being its items joined by `,` in their sorted
  order, or `-` when empty:

  ```
  space <host.space answer>
  open <host.open("mapping.json")>
  read_at <host.read_at("a.odrg", 0, 128 bytes)>
  remove_before <host.remove("upload.part")>
  start_folders <folders>
  start_files <files>
  start_mkdir <mkdirCalls>
  start_write_opens <writeOpens>
  write_open <host.write_open("upload.part")>
  first_folders <folders>
  first_files <files>
  first_mkdir <mkdirCalls>
  first_write_opens <writeOpens>
  write <host.write of 100 bytes>
  write_close <host.write_close>
  rename <host.rename("upload.part", "a.odrg")>
  read_back <host.read_at("a.odrg", 0, 128 bytes)>
  read_back_same <1 when the bytes read are the 100 given, else 0>
  remove <host.remove("a.odrg")>
  write_open_again <host.write_open("upload.part")>
  end_folders <folders>
  end_files <files>
  end_mkdir <mkdirCalls>
  end_write_opens <writeOpens>
  ```

  `host.close` follows the `open`. The 100 bytes are `(uint8_t)(i * 7 + 1)`. The three
  points, `start`, `first` and `end`, are the state before any write, right after the
  first `write_open`, and at the end. The `writeOpens` counter is the second open made
  visible: a `write_open` that opens twice did so because `mkdir` answered true.
- The helper `answers(scenario)` runs the binary with the scenario,
  `subprocess.run(..., capture_output=True, text=True)`, raises `AssertionError` with
  the status and the end of standard error when the status is not 0, and returns the
  lines as a dict of name to value text. Each case compares a dict of the names it pins
  with `assertEqual`, so that a failure shows every value that differs.
- The five cases, each with its scenario, the values it pins after the fix, and the
  values that differ before it:
  1. `test_the_first_write_into_a_storage_without_the_folder_makes_it`, `fresh`:
     `space` 1, `write_open` 1, `first_folders` `/odrig`, `first_files`
     `/cfg.json,/odrig/upload.part`, `first_mkdir` 1, `first_write_opens` 2, `write` 1,
     `write_close` 1, `rename` 1, `read_back` 100, `read_back_same` 1, `remove` 1,
     `write_open_again` 1, `end_folders` `/odrig`, `end_files`
     `/cfg.json,/odrig/upload.part`, `end_mkdir` 1, `end_write_opens` 3. Before the fix,
     seen failing first: `write_open` -1, `first_folders` `-`, `first_files`
     `/cfg.json`, `first_mkdir` 0, `first_write_opens` 1, `write` -1, `write_close` -1,
     `rename` -1, `read_back` -1, `read_back_same` 0, `remove` 0, `write_open_again`
     -1, `end_folders` `-`, `end_files` `/cfg.json`, `end_mkdir` 0, `end_write_opens` 2.
  2. `test_a_storage_with_the_folder_is_not_asked_for_it`, `folder`: `write_open` 1,
     `first_folders` `/odrig`, `first_mkdir` 0, `first_write_opens` 1, `read_back` 100,
     `read_back_same` 1, `write_open_again` 1, `end_mkdir` 0, `end_write_opens` 2. The
     same before the fix: a guard.
  3. `test_a_folder_the_file_system_refuses_makes_the_write_fail`, `refused`:
     `write_open` -1, `first_folders` `-`, `first_files` `/cfg.json`, `first_mkdir` 1,
     `first_write_opens` 1, `write` -1, `write_close` -1, `write_open_again` -1,
     `end_folders` `-`, `end_files` `/cfg.json`, `end_mkdir` 2, `end_write_opens` 2.
     Before the fix, seen failing first: `first_mkdir` 0 and `end_mkdir` 0.
  4. `test_a_write_refused_in_a_present_folder_is_tried_once_more_and_fails`,
     `failing`: `write_open` -1, `first_folders` `/odrig`, `first_files` `/cfg.json`,
     `first_mkdir` 1, `first_write_opens` 2, `write` -1, `write_close` -1,
     `write_open_again` -1, `end_folders` `/odrig`, `end_files` `/cfg.json`,
     `end_mkdir` 2, `end_write_opens` 4. Before the fix, seen failing first:
     `first_mkdir` 0, `first_write_opens` 1, `end_mkdir` 0 and `end_write_opens` 2.
  5. `test_a_read_in_the_missing_folder_is_a_missing_file`, `fresh`: `space` 1, `open`
     0, `read_at` -1, `remove_before` 0, `start_folders` `-`, `start_files`
     `/cfg.json`, `start_mkdir` 0, `start_write_opens` 0. The same before the fix: a
     guard, and the start's own call, the remove of `upload.part`, makes no folder.

  The third and the fourth count one `mkdir` at the first point and two at the end: the
  fix keeps nothing of a refusal, so the second `write_open` asks again. In the fourth,
  `first_write_opens` 2 and `end_write_opens` 4 show that each `mkdir` answered true.

## The text rule

- `tests/firmware/test_usermod_files.py:386`, in
  `Host.test_files_are_written_renamed_and_removed_in_one_source_only`, which loops over
  every source of the usermod, becomes two assertions:

  ```python
  self.assertNotRegex(text, r"ODRIG_FS\.(rmdir|format)\b", path.name)
  self.assertEqual(re.findall(r"ODRIG_FS\.mkdir\(([^)]*)\)", text),
                   ["FOLDER_PATH"] if path.name == "odrig_files.cpp" else [], path.name)
  ```

  Seen failing first on the source as it is: `AssertionError: Lists differ: [] !=
  ['FOLDER_PATH']` for `odrig_files.cpp`.
- The other rules of the file hold with the fix as they are, which the implementer sees
  by running them: line 374 keeps `const char FOLDER[] = "/odrig/";`; 379-383 find
  writes and `ODRIG_FS` in `odrig_files.cpp` only; 390-395 collect
  `open|exists|remove|rename` only, and the second open passes `path`; 397-398 see the
  same `strcpy` and `pathOf` targets; 402 allows `"/odrig"`; 409-412 find `pathOf(` in
  `beginFile()`; 458-468 find `blocksFreed(before);` after the `remove` of the given-up
  file; 543-547 find `Timed timed;` first in `beginFile()`. The `SHARED` tuple of line
  15 names `odrig_files.cpp` already.

## The littlefs rule

- `tests/firmware/test_storage.py`, a new class `FreshStorage`, docstring "The rule of
  the file system the board's files host rests on: a file is refused in a folder that is
  not there.", with
  `test_a_fresh_storage_refuses_a_file_in_the_folder_until_the_folder_is_made`:
  - `fresh = storage.with_settings(support.storage_image(), 0x4E0000)`, a storage of the
    spare's size, 1,248 blocks, with WLED's files and no `/odrig`
    (`firmware/fwtool/storage.py:270-303`, `tests/firmware/support.py:278-289`);
    `storage.show_of(fresh)` is `{}`;
  - on `system = storage.mount(fresh)`: `storage.has_folder(system, storage.FOLDER)` is
    false; `system.open("/odrig/upload.part", "wb")` raises `FileNotFoundError`;
    `system.mkdir("/odrig")`; the same open then writes 100 bytes, and `has_folder()` is
    true; a second `system.mkdir("/odrig")` raises `FileExistsError`;
  - `storage.with_show(fresh, {"upload.part": data})`, whose `_changed()` runs
    `system.mkdir(FOLDER)` first (`storage.py:150-152`), gives an image whose
    `show_of()` is that one file.

  It catches `FileNotFoundError` and `FileExistsError`, the `OSError`s whose
  `__cause__` is the `LittleFSError` in littlefs-python 0.19.0, not `LittleFSError`
  itself. It passes before the fix: a guard of the rule, not a test of a fault.

## The tests

- `tests/firmware/test_usermod_files_host.py`, `TheStorageFolder`, new: the five cases
  above. Seen failing first against the source as it is:
  `test_the_first_write_into_a_storage_without_the_folder_makes_it` with `write_open`
  -1, no folder and `mkdir` 0;
  `test_a_folder_the_file_system_refuses_makes_the_write_fail` and
  `test_a_write_refused_in_a_present_folder_is_tried_once_more_and_fails` with
  `mkdir` 0 at both points. `test_a_storage_with_the_folder_is_not_asked_for_it` and
  `test_a_read_in_the_missing_folder_is_a_missing_file` pass before the fix, guards of
  what must stay. The `AssertionError` text of each failure goes into the commit message.
- `tests/firmware/test_usermod_files.py`, `Host`: the text rule above, seen failing
  first, `[] != ['FOLDER_PATH']`.
- `tests/firmware/test_storage.py`, `FreshStorage`: the littlefs rule, a guard.
- `tests/firmware/test_docs.py`, `Firmware`: the new sentence below, seen failing first.
- `python core/build.py test`: unchanged, no test added or changed.

## The documentation

- `docs/firmware.md`, "What the firmware does":
  - the "At start" paragraph, lines 910-915, whose line 911 is 100 columns and is
    wrapped under 90: "**At start** the usermod starts the core on the files of the
    folder `/odrig` of storage: `mapping.json`, `show.json` and the `.odrg` and
    `.odrgx` files, as `install-show` put them there or as the core's changes wrote
    them." The rest of the paragraph stays;
  - the "Storage" paragraph, lines 917-924, after "nothing of the firmware decides to
    write." on line 921: "The folder itself is made by `write_open`, once, when a write
    finds it missing: a storage that WLED formatted holds WLED's own files and no
    `/odrig` until the first write into it, and the file system makes no folder for a
    file." The paragraph is wrapped again under 90 columns;
  - the row of `write_open`, line 928: "A file that was being written is closed and
    removed. The named file is opened for writing, which empties one that has the name;
    when the open fails, the folder is asked for once, made if it is missing, and the
    open tried once more. One file is written at a time."
- `tests/firmware/test_docs.py:251-258`, `Firmware`,
  `test_it_says_what_the_firmware_writes_how_it_paces_and_what_an_upload_measured`:
  its `expected` keeps "**Storage.**", "Every path is `/odrig/<name>`", "The firmware
  writes, renames and deletes a file only there", `upload.part`, `show.part`,
  `pending.txt` and the rest, and the seven rows, and gains "The folder itself is made by
  `write_open`, once, when a write finds it missing". Seen failing first before the page
  changes: `AssertionError: 'The folder itself is made by `write_open`, once, when a
  write finds it missing' not found in ...`.
- `docs/drifts.md`, at its end after seed 77's last entry,
  `## Seed 78: who makes the folder`:
  - **Question.** The host contract of `docs/core.md` names no folder and no call to
    make one; `docs/firmware.md` said the files are there "as `install-show` put them
    there", as if `install-show` were the folder's only maker; and a storage WLED
    formatted has none, so a board that was only ever flashed refused its first upload
    with `storage-error`. Who makes the folder, and when? The entry says that this
    shows a gap in a governing document: the contract says nothing of where the files
    live or who makes the place.
  - **Answer.** The host, inside `write_open`, once, after a failed open: one `mkdir` of
    `/odrig` and the open again. Not the core, which knows no paths and whose contract
    would then grow for every host for one platform's rule; not the start, which seed 76
    decided writes nothing; not the usermod's `setup()`, which would make the firmware
    decide to write. No decision of `docs/decisions.md` changes, so its change log gets
    no entry.
  - **Resolution.** `firmware/usermod/odrig_files.cpp` and `docs/firmware.md`.
- `docs/core.md` and `docs/commands.md`: not changed.
- `AGENTS.md`, "What is coming": the line of this seed, "planned; ..." after the merge of
  `master`, becomes "implemented in open PR #50; ..." with the rest of its words, in the
  first task's commit; 147 lines in all, under the 150 the onboarding suite allows.

## Delivery

- The branch `seed-77-firmware-for-the-spare-module`, pull request #50, after
  `03071daf`, the merge of `master` that brought this seed, and this spec's commit; one
  commit per task, `Seed 78 task <n>: <title>`; no new pull request. `gh pr edit 50
  --title "Seeds 77 and 78: a firmware for the spare board's module, and the first write
  makes the storage folder"` and a `--body` that keeps seed 77's description and adds
  this seed: its verdict, the folder `/odrig` never made on a board that only ever got
  application images, the fix in `write_open`, and the owner's open
  checks of this seed beside seed 77's.
- Three images, built on this Windows computer with the shared toolchains through
  `ODRIG_TOOLS`, each from a clean tree so that its record says `trackedDirty` false, in
  this order, `docs/firmware.md:98-110`:
  1. the installation's, `python firmware/fw.py build` and
     `python firmware/verify_build.py`, from the pushed head;
  2. the spare's, `python firmware/fw.py build --module n8r2` and
     `python firmware/verify_build.py --module n8r2`, from the same head; the
     installation's first, because its build removes the spare's ELF, as seed 77's
     `verification.md` found;
  3. the combined image: a detached worktree of its own under `scratch/` at the pushed
     head, a local merge commit there of `seed-76-empty-board-first-animation` at
     `abc75ea3`, never pushed; the conflicts kept by hand with both sides: in
     `AGENTS.md`, "What is coming", seed 76's line as its branch has it beside seed 77's
     and this seed's as the head has them; in the change log of `docs/decisions.md`,
     seed 76's entry before seed 77's, as the older branch; `docs/drifts.md` merged by
     union as `.gitattributes` has it; none of these files is read by the build. Then
     `python firmware/fw.py setup` there if its work folder is new,
     `python firmware/fw.py build --module n8r2` and
     `python firmware/verify_build.py --module n8r2`; its `.build.json` names the merge
     commit, `trackedDirty` false.

  The spare's and the combined image's headers say 8 MB, the installation's 16 MB. The
  installation's record differs in its `inputs` from seed 77's installation record,
  `odrig-seed77-4ee8992-n16r8-at-0x10000.bin.build.json` of `odrig archive/seed-77/`,
  by `firmware/usermod/odrig_files.cpp` alone.
- The Drive, `Artifacts/odrig/odrig archive/seed-78/`, on this computer
  `G:\My Drive\Artifacts\odrig\odrig archive\seed-78\`, as seed 77's `verification.md`
  names its folder:
  - `odrig-seed78-<head>-n16r8-at-0x10000.bin`,
    `odrig-seed78-<head>-n8r2-at-0x10000.bin`, `<head>` the short hash of the pull
    request's head, and `odrig-seed78-<merge>-plus-seed76-n8r2-at-0x10000.bin`,
    `<merge>` the short hash of the merge commit;
  - beside each, `<file>.sha256`, the hash and the delivered name, `<file>.build.json`,
    the tool's record as it is, and `<stem>-image-info.txt` and
    `<stem>-verification.json`, the `image-info*.txt` and `verification*.json` of
    `verify_build.py` renamed, `<stem>` the file's name without `.bin`;
  - `README.txt`, LF and ASCII, in the form of seed 77's: the seed's title and the pull
    request's address; a block per image with its file, its bytes, its SHA-256, its
    environment, its release name and the flash size of its header; the source commit
    of each, the merge's two parents named for the combined one; what the seed fixes, in
    words: a board that was only ever flashed has no folder `/odrig`, and its first
    upload was refused with `storage-error`, which the first write now mends by making
    the folder; how to flash from the phone: the application image at 0x10000 and no
    other, the offset field read before `Flash`, the flash settings kept, no erase,
    neither bootloader nor table written; that the `Installation:` line is read first,
    with the four readings as seed 77's README has them, and that `reset other` right
    after a flash and `reset power-on` after a power cycle are neither a finding; that
    the combined image is the one to flash on the spare for the upload check, since it
    alone holds seed 76's change, the pull-request images carrying the fix and showing
    `mapping-missing` on an empty board until both pull requests merge; what to do when
    no hotspot shows a minute after a flash, as seed 77's README says; that no APK is
    built, the APK of seed 75, `odrig archive/seed-75/odrig-seed75-f5ad253.apk`,
    working with every image, an APK without an `Installation:` line being older and
    replaced first; and that the files above the folder are untouched;
  - `only-if-the-flash-was-erased/`, from the pull-request head's spare build:
    `odrig-seed78-<head>-n8r2-bootloader-at-0x0.bin`, `bootloader.bin` of
    `.pio/build/odrig_microsd_n8r2/`, and
    `odrig-seed78-<head>-n8r2-partitions-at-0x8000.bin`, its `partitions.bin`, byte for
    byte the Drive's `wifi-storage/odrig-8mb-partition-table-at-0x8000.bin`, SHA-256
    `dc19fc0fcd52efb130e273d9e69a3cfec1b86f1595a0f24bd74c0656f3efd17f`, each with its
    `.sha256`, and a `README.txt` in the words of seed 77's: for a spare whose flash was
    erased or written at 0x0 or 0x8000 by mistake and for nothing else, never on the
    installation's board; the bootloader at 0x0, the table at 0x8000 and the spare's
    image at 0x10000, in that order; the settings kept, no erase, the storage at
    0x310000 not written.

  No file is named `odrig-firmware.bin` or `odrig-firmware-n8r2.bin`; nothing above
  `seed-78/` is touched; no storage image is read or printed. The Drive ids of the files
  are read once the client has synced them.
- The links sent to the owner, in words: the full link of each of the three images and
  of the bootloader and the table of the subfolder, in the owner's words "not of the
  folder but of the files"; no folder's link.
- The rest of the hand-over, in the same notification and in words, since a note in a
  file does not count: the owner's six checks and seed 77's open checks; the core test
  of the symptom in seed 76's suite, `--store-fails-at 3` on
  `tests/core/test_first_animation.py`, the start's two removes being calls 1 and 2,
  proposed as a seed after both pull requests merge; the merge order of #49 and #50 as
  the owner's; and the image with all three changes, built from `master` after both
  merge, as the owner's, the combined image being the one that has them until then; the
  proposal of a seed in which the app's dialog names the refused command; and the gap of
  the host contract of `docs/core.md`, recorded in seed 78's drift entry.
- `verification.md` of this spec, written by the last task in the form of seed 77's:
  "The commits, by task"; "The suites, by task", with the failures seen first and their
  text; "The three images", with their bytes, SHA-256, ELF SHA-256, header, release
  name, the merge's two parents, the tool versions and the build times; "Where it is",
  the Drive paths and the links of the files; "The workflow", the result of the checks
  on the pull request; and "Open": the owner's six checks, seed 77's open checks, the
  merge order of #49 and #50 and the image with all three changes built from `master`
  after both merge, and the core test of the symptom in seed 76's suite, a gap for a
  seed after the merge.
- The seed's state is `in_progress` from the first task on and stays so until #50
  merges, when it is `completed`, as seed 77's.
