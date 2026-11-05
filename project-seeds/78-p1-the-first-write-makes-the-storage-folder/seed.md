# The first write makes the storage folder

## Summary

The spare board, an ESP32-S3 N8R2 running seed 77's firmware for its module, refuses the
first upload from the phone with `storage-error`. The cause is in the firmware's files
host, `firmware/usermod/odrig_files.cpp`: the folder `/odrig` of the board's storage does
not exist on the spare, because only `python firmware/fw.py install-show` from a computer
has ever made that folder, the spare only ever got application images, and WLED formats a
fresh root with its own files and no `/odrig`. The host's `write_open`, `beginFile()`,
opens `/odrig/upload.part` for writing with the file system's `create` left false,
LittleFS refuses a file in a folder that is not there, `beginFile()` answers -1, and
`upload begin` answers `storage-error`. Seed 76 made the read side take a missing folder
for missing files, which is why the board looks healthy, a canvas, `0 animations` and
`5.1 MB` free, until the press. This seed has the host make the folder once, inside
`write_open`, when a write finds it missing: one `mkdir` of `/odrig` after a failed open,
then the open again. A storage with the folder pays nothing, a refused `mkdir` ends in -1
as today, the start still writes nothing, and every file the core writes gets the folder,
since all of them begin with `write_open`. The core is not changed, no command is added,
the app is unchanged. The work lands on seed 77's branch, pull request #50, as further
task commits, and three images are built from it: the two pull-request images, and the
spare's combined image, a local merge with seed 76's branch, which the owner flashes for
the upload check.

## Priority

- `P1`

## Depends On

- Seed 77, pull request #50, branch `seed-77-firmware-for-the-spare-module` at
  `43a62587`, not merged, a pull request of its own from `master` at `bb0658e5`: the
  spare's environment `odrig_microsd_n8r2`, its image `odrig-firmware-n8r2.bin`, the 8 MB
  layout of the firmware tool and the host text with `external` and `internal`. This
  seed's commits go on that branch after its task 7. Nothing of seed 77 touches the files
  host: `git diff bb0658e5 43a62587 -- firmware/usermod` changes `odrig_usermod.cpp`
  only, so nothing is undone.
- Seed 76, pull request #49, branch `seed-76-empty-board-first-animation` at `abc75ea3`,
  not merged: the core plays a board without `mapping.json` and without `show.json`,
  which the empty spare needs for its canvas, and the first change that writes the show
  file writes the mapping file first. It is not on pull request #50's branch: the merge
  base of the two heads is `9c13db4f`, so the spare's deliverable is a local merge of the
  two, as "Where it lands" says.
- Seed 07, commit `41fe820c`: `beginFile()` of `firmware/usermod/odrig_files.cpp`, the
  three host functions of a write, and the rule of `tests/firmware/test_usermod_files.py`
  that forbids `ODRIG_FS.mkdir`, `rmdir` and `format` in every source of the usermod,
  both from that commit.
- Seed 04, commit `08e435cf`: `odrig_files.cpp` itself, `FOLDER`, `pathOf()` and
  `openNamed()`; and commit `72d7849d`: `firmware/fwtool/storage.py`, its `FOLDER`,
  `has_folder()`, `show_of()` and the `system.mkdir(FOLDER)` of `_changed()`, the one
  maker of the folder so far.
- Seed 12, commit `d8d4054e`: the platform header `odrig_platform.h`, one for each
  firmware, through which the shared sources reach `ODRIG_FS`, and
  `firmware/standalone/src/shared_files.cpp`, which compiles `odrig_files.cpp` as it is.
- Seed 22, commit `bddc2ce8`: `allocate()` and its 192 KB reserve, by which the spare's
  memory is accounted for and ruled out as the cause.
- Seed 34, in the change log of [decisions.md](../../docs/decisions.md): `install-show`
  changes only the files of `/odrig` that differ. Untouched.
- Seed 60: the shared toolchains, `firmware/verify_build.py`, the build records of
  `firmware/fwtool/provenance.py` and the workflow `.github/workflows/firmware-hosts.yml`,
  which build and verify both images.
- The Arduino framework of the newer software, `framework-arduinoespressif32` 3.3.12:
  `FS::open(path, mode, create = false)` and `FS::mkdir(path)` of `libraries/FS/src/FS.h`
  (lines 91 and 103), and `VFSImpl::open()` and `VFSImpl::mkdir()` of
  `libraries/FS/src/vfs_api.cpp` (lines 25-84 and 165-216).
- `tests/firmware/compiler.py`, `compiled()`, and the stand-in pattern of
  `tests/firmware/test_usermod_sd.py`; littlefs-python 0.19.0 of the firmware's venv,
  on which `tests/firmware/test_storage.py` runs.

## Product Context

On 2026-11-05 at 22:17 the owner, at the installation with the spare board and the phone,
flashed on the spare an image of seed 77's task 3 merged with seed 76's change, a local
merge `06cad803` built as `odrig_microsd_n8r2`, and used the operators' app, the APK of
seed 75, over the board's hotspot. The Animations page said `Connected`,
`Internal storage: 0 animations, free 5.1 MB of 5.1 MB`,
`External storage: absent (read-only).` and `Root: No animation is installed.`; the
Upload page offered `Ready-made animation, 60 x 60, 26 KB`, `Internal storage`, the file
name `time-standalone-6-melting-c.odrg` and the button `Upload to the installation`
enabled; after the press both pages showed the dialog
`The installation could not use its storage. (storage-error)`. Nothing else is known:
not which command was refused, not the Target page's lines, not the board's log. The
owner's order, in words, after the dialog: find out why this still happens, and make a
fixed seed, implemented on top of the previous seed's branch, pull request #50, ready for
seed-to-spec with zero open questions, every question answered on its own; then the
spec, the queue and the implementation on that branch; then the images rebuilt, uploaded
to the Drive, and the file links sent.

The diagnosis was made on the code of pull request #50's branch and of seed 76's, on the
framework the spare's image is built with, on WLED's sources and on a probe of
littlefs-python on this computer; no board was reached. Three readers tried to refute it
and could not. Every line number below is of pull request #50's branch at `43a62587`;
`odrig_files.cpp` is the same there as on `master`.

What the code does, read on 2026-11-05:

- The app sends `upload begin 1 time-standalone-6-melting-c.odrg <bytes> <crc>`.
  `upload_begin()` of `core/src/upload.cpp` (lines 154-220) refuses `storage-error` at
  lines 192-193 when `told` is false, `storage_changes()` is false, `core.checker` is
  null, `catalog_settle()` is false, or `host.write_open(host.ctx, "upload.part")` is
  not 1; the probe `host.read_at(name, 0, ...)` at lines 182-184 only tells a name in
  use. The preflight's `space` is refused with the same code by `content_space()` of
  `core/src/content.cpp` (lines 164-169) when `host.space` does not answer 1.
- `write_open` of the firmware is `beginFile()` of `firmware/usermod/odrig_drive.cpp`
  (lines 737-745), which hands a name that is not a drive's to `files.write_open`, that
  is `beginFile()` of `firmware/usermod/odrig_files.cpp` (lines 185-208): `pathOf()`
  (137-142) makes `/odrig/upload.part` from `FOLDER`, `"/odrig/"` (line 7); `sizeAt()`
  (84-91) finds nothing; line 202 is `writtenFile = ODRIG_FS.open(path, "w");` and line
  203 `if (!writtenFile) return -1;`.
- `ODRIG_FS` is `WLED_FS` (`firmware/usermod/wled/odrig_platform.h:8`), which is
  `LittleFS`. `FS::open(path, mode, create = false)` reaches `VFSImpl::open()`
  (`vfs_api.cpp:25-84`), which makes the folders of a path for a write mode only when
  `create` is true (lines 38-75) and otherwise goes straight to `fopen` (`VFSFileImpl`,
  316-321); `operator bool` is the file handle (352-354). LittleFS creates a file and
  never the folder it lies in. On a fresh file system of 1,248 blocks, littlefs-python
  0.19.0 of the firmware's venv raises `FileNotFoundError`, cause `LFS_ERR_NOENT`, for
  `open("/odrig/upload.part", "wb")` and for a read of `/odrig/mapping.json`; after
  `mkdir("/odrig")` the write and a rename inside the folder succeed; a second `mkdir`,
  and `mkdir("/odrig/")`, raise `FileExistsError`, cause `LFS_ERR_EXIST`; the folder
  takes two blocks, 2 in use after the format, 4 after the folder, 11 after a 26,000-byte
  file. The firmware tool rests on the same rule: `_changed()` of
  `firmware/fwtool/storage.py` runs `system.mkdir(FOLDER)` before it writes into
  `/odrig` (lines 151-152), `has_folder()` tells the folder apart (97-101) and
  `show_of()` answers `{}` without it (104-109).
- Nothing on the board makes the folder. No source of `firmware/usermod/` names `mkdir`,
  and `tests/firmware/test_usermod_files.py:386` forbids `ODRIG_FS.(mkdir|rmdir|format)`
  in every one of them. The only maker of `/odrig` is `install-show` from a computer over
  USB; `docs/firmware.md:910-911` says the files are there "as `install-show` put them
  there". The spare never had that: it was flashed with the firmware alone and answered
  `mapping-missing` (`project-seeds/76-p1-an-empty-board-takes-its-first-animation/
  seed.md:65-69`). `flash` writes the application only, `write_application()` of
  `firmware/fwtool/cli.py` (lines 128-148); from the phone only the application image is
  flashed, at 0x10000. WLED mounts its storage with `WLED_FS.begin(true)`
  (`wled00/wled.cpp:457`), which formats one it cannot mount, before the usermods start:
  a fresh root with WLED's own files and no `/odrig`. The tool's own fresh storage is the
  same shape: `with_settings()` of `storage.py` (lines 270-303) holds every file outside
  `/odrig` and checks that `show_of()` is empty; `big-storage` on the installation's
  board left `/odrig` empty, and `status` answered `mapping-missing`
  (`docs/firmware.md:2274-2276`).
- Why the start looked healthy. `openNamed()` (lines 144-154) answers 0 when the open
  fails and `ODRIG_FS.exists(path)` is false, which `VFSImpl::exists()` (86-98) answers
  for any path that neither opens nor is a folder: a missing folder reads as missing
  files. Seed 76 then takes the built-in mapping and the empty show, and `status` answers
  `"error":null` with a canvas of 60 x 60. The start writes nothing, seed 76's
  requirement 3.1: its two storage calls are `remove upload.part` and `remove show.part`
  (`core/src/storage.cpp:144-148`; seed 76's `tests/core/test_startup.py:181`), and
  `removeFile()` answers 0 before it touches the file system when `exists()` is false
  (line 255). `space` comes from `tellSpace()` (263-269) on the numbers `askSpace()`
  (94-100) took once from `totalBytes()` and `usedBytes()` when `OdrigFiles::host()` was
  made (line 301): 5,111,808 bytes, the spare's `spiffs` partition, which the app shows
  as `5.1 MB`. So every line the owner saw before the press is what an empty, mounted,
  folderless storage gives, and the first write the core ever asks for is the one that
  fails.
- Why no suite saw it. Every host the suites run on has its folder before the core
  starts: the core's test host writes into the session folder, the emulator's host into
  a folder that must exist, and the board suite installs a show first with
  `install-show`, whose image has the `mkdir`. Seed 76 tested the first upload into an
  empty folder (`tests/core/test_first_animation.py:34-59` on its branch), never a
  missing one. `odrig_files.cpp` is run by no suite: its tests read its text
  (`test_usermod_files.py:354-490`).
- What rules the other causes out. `told` false, `tellSpace()` answering -1, needs a
  storage not mounted when `host()` asked, and the `5.1 MB` line is `space`'s reply.
  `core.checker` null is `out-of-memory` at the start, `core/src/core.cpp:407`, taken
  after `read_mapping()` (line 390) has set `leg_count`, which `core_fail()` (805-826)
  leaves as it is: the show is invalid, `status` answers `"error":"out-of-memory"` and
  `"readiness":"recovery"` with the canvas of 60 x 60 still reported
  (`core/src/commands.cpp:197-204`, `206-210`, `217`), the Target page shows
  `The installed show is invalid: out-of-memory.` (`app/www/screens/target.js:101-102`)
  and the Animations page says `animations not known` in place of `0 animations`, since
  `counts()` of `app/www/capacity.js` gives null while `status.error` is set; the
  owner's `0 animations` line rules it out. The core asks for no memory after its start
  (`core/src/arena.h`), and the `n8r2` build has room many times over: the core's 21
  blocks sum to 130,303 bytes against 2 MB of external memory, with at most 288 KB asked
  of it in all.
  `catalog_settle()` is true on an empty storage, which can hold no `catalog.do` without
  the folder. A write or a close that failed after a good `write_open`, or a check that
  read the file back wrong, need the folder and seconds of a climbing `Sending:` line,
  which the dialog hides; nothing points at them, and they stay what
  `docs/commands.md:464` says, a fault of the storage refused in words. Nothing is in the
  log: `upload.cpp:192-193` logs nothing, `fault` answers null, since `note_fault()` runs
  only inside the check (`upload.cpp:150`), and the framework's `log_e("fopen(%s)
  failed")` is compiled out of WLED's builds, `CORE_DEBUG_LEVEL=0`.

So the fault is the firmware's files host. `write_open` promises the core a new, empty
file of a name, `core/include/odrig_core.h:42-45`, and on a storage that never had
`install-show` it cannot keep the promise, because the place of the files was never made
and nothing on the board makes it. Seed 76's change is right and brought the board to the
press; seed 77's brought it the memory; this seed brings the folder.

## Technical Constraints

- **The folder is made by the host, inside `write_open`, once.** In
  `firmware/usermod/odrig_files.cpp`, beside `FOLDER` (line 7), a second constant names
  the folder as the file system names it, without the slash:
  `const char FOLDER_PATH[] = "/odrig";`, with a comment that says what is now and no
  more: that a storage that was formatted and never had a show has no such folder, and
  that the file system makes no folder for a file. In `beginFile()` (lines 185-208) the
  open at line 202, `writtenFile = ODRIG_FS.open(path, "w");`, is followed by one line,
  `if (!writtenFile && ODRIG_FS.mkdir(FOLDER_PATH))` and then
  `writtenFile = ODRIG_FS.open(path, "w");`, before line 203's
  `if (!writtenFile) return -1;`. `sizeAt(path)` before the opens, `blocksFreed(before)`
  after them and everything else of the function stay as they are, and the comment above
  the opens says that a storage without the folder gets it first. Nothing else of the
  source changes: `openNamed()`, `readAt()`, `removeFile()` and `renameFile()` keep
  taking a missing folder for missing files, which is what lets the start pass.
- **At most one `mkdir` and one second open in a `write_open`.** `mkdir` is tried only
  after an open failed, so a storage with the folder pays nothing: no call, no time. The
  framework's `VFSImpl::mkdir()` (`vfs_api.cpp:165-216`) answers true for a folder that
  exists, false for a file of that name, and else what `::mkdir` answers; littlefs's own
  rule refuses a folder that exists, `LFS_ERR_EXIST`, but the chip's VFS is another layer
  and hides it. So an open that failed for another reason on a storage with the folder
  gets one `mkdir` that answers true and one more open that fails again, then -1 as
  today; a `mkdir` the file system refuses ends in -1 at once; nothing loops, and no
  state of the file is kept across the calls. Both opens and the `mkdir` lie inside the
  `Timed` of `beginFile()` (line 186), so the pacing of `holding()` (330-344) holds the
  next command line for twice their time, once, as for any storage call.
- **The start still writes nothing.** The two storage calls of the start are
  `remove upload.part` and `remove show.part`, which `removeFile()` answers 0 before
  touching the file system when `exists()` is false (line 255); no `write_open` is called
  at the start. So seed 76's requirement 3.1 holds as it is, a host whose storage cannot
  be written still reports the canvas, and the folder comes to be at the first change the
  core makes, which is a decision of the core, not of the firmware: `docs/firmware.md`'s
  sentence that the firmware writes only inside one of the storage functions and that
  nothing of the firmware decides to write stays true. A `mkdir` at the usermod's
  `setup()` would make it false and is not made.
- **Every file the core writes gets the folder.** Every file the core writes begins with
  `write_open`, `core/include/odrig_core.h:42-45`: `upload.part` at `upload begin`,
  `pending.txt` in `write_pending()` (`core/src/storage.cpp:44-51`), `mapping.part` of
  seed 76's `mapping_materialize()`, `show.part` of the show's commit, and the
  `.part` files of the settings; `rename` and `read_at` then find the folder the write
  made. So the fix covers the first wall, `upload begin`, and the walls behind it, the
  `upload data` lines and the `upload end` that writes `mapping.json` and `show.json`
  beside the file, at once. A fix that made the folder for `upload.part` alone, or at
  the start alone, would fail at the next write or break requirement 3.1.
- **The path is `/odrig`, not `/odrig/`.** `FOLDER` stays `"/odrig/"`, the prefix of
  every file path, pinned by `test_usermod_files.py:374`; `FOLDER_PATH` is the folder as
  `VFSImpl::mkdir()` and littlefs document it, without the slash. The probe accepted both
  forms, but the chip's VFS is another layer, and the form both document is the one
  given. The two constants lie side by side, 8 and 7 bytes of flash.
- **The core is not changed, and the host contract neither.** `write_open`'s duty is the
  host's: `docs/core.md:86` says it begins a new, empty file of the name, and nothing of
  the contract (`docs/core.md:80-137`) names a folder or a call to make one. The core
  knows no paths; the test host of `tests/core/host/` and the emulator's host of
  `emulator/host.py` have their folders before the core starts; a folder call in the
  contract would be added to every host for one platform's rule. So `core/`,
  `odrig_core.h`, `docs/core.md` and `docs/commands.md` are untouched, and
  `python core/build.py test` runs unchanged, 1,051 tests as seed 77's `verification.md`
  recorded them.
- **What it costs.** Memory: nothing; one more string constant in flash. Storage: the
  folder takes two blocks, 8,192 bytes, once in the life of the storage; `usedBlocks`
  (line 35) is not told, so `tellSpace()` reports 8 KB more free than there is until the
  next start, when `askSpace()` reads `usedBytes()` again; `blocksTaken()` counts file
  bytes and not folders by design, and the figure the app shows is rounded to 0.1 MB and
  does not move for it. Time: on a storage with the folder nothing; on one without it one
  failed open, one `mkdir`, which is one metadata commit of littlefs, and one open, once.
  No allocation of the usermod's: `VFSImpl::mkdir()` builds one path on the heap and
  frees it.
- **The text rule.** `tests/firmware/test_usermod_files.py:386`, in
  `test_files_are_written_renamed_and_removed_in_one_source_only`, which loops over every
  source of the usermod, becomes two assertions per source: `rmdir` and `format` stay
  forbidden everywhere, `assertNotRegex(text, r"ODRIG_FS\.(rmdir|format)\b", path.name)`,
  and `mkdir` is called exactly once, in `odrig_files.cpp`, with `FOLDER_PATH`:
  `assertEqual(re.findall(r"ODRIG_FS\.mkdir\(([^)]*)\)", text), ["FOLDER_PATH"] if
  path.name == "odrig_files.cpp" else [], path.name)`. Seen failing first on the source
  as it is: `[] != ['FOLDER_PATH']` for `odrig_files.cpp`. The other rules of the file
  hold with the fix as they are, which the implementer sees by running them: line 374
  keeps `FOLDER`; 379-383 find writes and `ODRIG_FS` in `odrig_files.cpp` only; 390-395
  collect `open|exists|remove|rename` only, and the second open passes `path`; 397-398
  see the same `strcpy` and `pathOf` targets; 402 allows `"/odrig"`; 409-412 find
  `pathOf(` in `beginFile()`; 458-468 find `blocksFreed(before);` after the `remove` of
  the given-up file; 543-547 find `Timed timed;` first in `beginFile()`.
- **The host test, the one that models the board.**
  `tests/firmware/test_usermod_files_host.py`, new, found by discovery, compiles
  `firmware/usermod/odrig_files.cpp` with
  `tests/firmware/compiler.py`'s `compiled()`, as `tests/firmware/test_usermod_kept.py`
  uses it, through a program of its own that includes the source by its absolute path,
  as `tests/firmware/test_usermod_sd.py` includes `odrig_drive.cpp`. The includes are a
  work folder first, so that `#include "odrig_platform.h"` (`odrig_files.cpp:3`), which
  no file beside the sources answers (`test_usermod_files.py:101-102`), takes a stand-in
  the test writes there, and `core/include` for `odrig_core.h` (`odrig_files.h:8`). The
  stand-in supplies what the source takes from `wled.h` on the board: `<algorithm>`,
  `<string.h>`, `<stdint.h>`; `esp_timer_get_time()`; `portMUX_TYPE`,
  `portMUX_INITIALIZER_UNLOCKED`, `portENTER_CRITICAL()` and `portEXIT_CRITICAL()`;
  `ESP_IDF_VERSION_MAJOR` 5, `heap_caps_get_free_size()`, `heap_caps_aligned_alloc()`,
  `MALLOC_CAP_INTERNAL`, `MALLOC_CAP_SPIRAM` and `MALLOC_CAP_8BIT`; a `File` with
  `operator bool`, `read(uint8_t *, size_t)` giving `int`, `write(const uint8_t *,
  size_t)` giving `size_t`, `seek(uint32_t)` giving `bool`, `size()`, `close()` and
  `isDirectory()`; and `ODRIG_FS`, an object with `open(path, mode)`, `exists()`,
  `remove()`, `rename()`, `mkdir()`, `totalBytes()` and `usedBytes()` over a map of files
  and a set of folders, whose `open(path, "w")` and `rename()` refuse a path whose folder
  is not in the set, as littlefs does, whose `exists()` is true for a file or a folder it
  has, as the VFS's is, whose `mkdir()` answers true for a folder it has, as the VFS's
  does, makes it otherwise, refuses it when the scenario says so, and counts its calls,
  and which refuses every open for writing when the scenario says so, as a storage that
  fails does. The program takes `OdrigFiles::host()` on the file system of a scenario
  named on its command line and prints what `space`, `open("mapping.json")`,
  `read_at("a.odrg")`, `write_open("upload.part")`, `write` of 100 bytes, `write_close`,
  `rename("upload.part", "a.odrg")`, `read_at("a.odrg")` of the bytes back,
  `remove("a.odrg")` and a second `write_open("upload.part")` answer, and at two points,
  right after the first `write_open` and at the end, the folders, the files held and the
  count of `mkdir` calls so far; the test reads the lines. The fix keeps nothing of a
  refusal, so a `mkdir` the file system refused is asked again by the next `write_open`
  whose open fails, and the count at the end is one for each such `write_open`. Five
  cases:
  `test_the_first_write_into_a_storage_without_the_folder_makes_it`, on a fresh file
  system without `/odrig`: `space` 1, `write_open` 1, the folders `{"/odrig"}` and
  `mkdir` called once at the first point, the chain to `read_at` answering the 100 bytes
  and `remove` 1, and the second `write_open` 1 with the folders and the count the same
  at the end, 1 at both points; seen failing first, `write_open` -1, no folder, `mkdir`
  0. `test_a_storage_with_the_folder_is_not_asked_for_it`: with `/odrig` present,
  `write_open` 1 and `mkdir` 0 at both points; it passes before the fix and guards what
  must stay. `test_a_folder_the_file_system_refuses_makes_the_write_fail`: `mkdir`
  always refused, `write_open` -1 both times, `mkdir` called once at the first point and
  twice at the end, no folder and no file at either point; seen failing first, `mkdir` 0
  at both. `test_a_write_refused_in_a_present_folder_is_tried_once_more_and_fails`: with
  `/odrig` present and every open for writing refused, `write_open` -1 both times,
  `mkdir` called once at the first point and twice at the end, each answering true, the
  folders still `{"/odrig"}` and no file; seen failing first, `mkdir` 0 at both.
  `test_a_read_in_the_missing_folder_is_a_missing_file`: on the fresh file system,
  before any write, `open` 0 and `read_at` -1; it passes before the fix and pins what
  lets the start pass. The test skips unless
  `core_build.find().kind == "gnu"`, as `test_usermod_sd.py:865-867` does, because
  `odrig_files.cpp:74` uses `__builtin_ctz`, which MSVC lacks; this computer's toolchain
  is GNU. The stand-in is C++11 and warning-free under `-Wall -Wextra -Werror`, with no
  signed and unsigned comparison and no bare `__attribute__`, as the rules of code that
  runs on every computer say; the files it writes go through `newline="\n"`.
- **The littlefs rule test.** `tests/firmware/test_storage.py` gets
  `test_a_fresh_storage_refuses_a_file_in_the_folder_until_the_folder_is_made`: on
  `storage.mount(storage.with_settings(support.storage_image(), size))`, a fresh storage
  with WLED's files and no `/odrig` (`storage.py:270-303`, `support.py:278-289`),
  `open("/odrig/upload.part", "wb")` raises `FileNotFoundError`, `mkdir("/odrig")` then
  makes the same write succeed, a second `mkdir` raises `FileExistsError`, and
  `_changed()` writes into the folder (`storage.py:141-152`). It catches
  `FileNotFoundError` and `FileExistsError`, which are `OSError`s whose `__cause__` is
  the `LittleFSError`, and not `LittleFSError` itself, which littlefs-python 0.19.0 does
  not raise for these. It passes before the fix: it pins the file-system rule the fix
  rests on, and it is named in `tasks.md` as a guard, not as a test of a fault.
- **The pages.** `docs/firmware.md`, "What the firmware does", on the branch: the "At
  start" paragraph (lines 910-915), whose line 911 is 100 columns today and is wrapped
  under 90 while it is edited, no longer implies that `install-show` is the only way the
  folder comes to be: the files are there as `install-show` put them there or as the
  core's changes wrote them. The "Storage" paragraph (917-924) gains, after "nothing of
  the firmware decides to write.", the sentence: "The folder itself is made by
  `write_open`, once, when a write finds it missing: a storage that WLED formatted holds
  WLED's own files and no `/odrig` until the first write into it, and the file system
  makes no folder for a file." The row of `write_open` in the table (928) says that when
  the open fails, the folder is asked for once, made if it is missing, and the open tried
  once more. `tests/firmware/test_docs.py:251-258` keeps every string it pins,
  "**Storage.**", "Every path is `/odrig/<name>`", "The firmware writes, renames and
  deletes a file only there", `upload.part`, `show.part`, `pending.txt` and the seven
  rows, and gains among its `expected` the words "The folder itself is made by
  `write_open`, once, when a write finds it missing", seen failing first before the page
  changes. `docs/core.md` and `docs/commands.md` are not changed: the contract and the
  refusal are as they were.
- **The drift entry.** At the end of `docs/drifts.md`, after seed 77's last entry,
  `## Seed 78: who makes the folder`, in the form **Question.**, **Answer.**,
  **Resolution.**: the host contract of `docs/core.md` names no folder and no call to
  make one, `docs/firmware.md` implied that `install-show` is its only maker, and a
  storage WLED formatted has none; the answer is the host, inside `write_open`, once,
  after a failed open, and neither the core, which knows no paths and whose contract
  would then grow for every host, nor the start, which seed 76 decided writes nothing;
  the resolution `firmware/usermod/odrig_files.cpp` and `docs/firmware.md`. The entry
  says that it shows a gap in a governing document: the contract says nothing of where
  the files live or who makes the place. No entry in the change log of `decisions.md`:
  no decision changes, and the owner's words are in this seed, as seed 76's are in its.
- **The standalone firmware.** Not changed, and it takes the fix: `shared_files.cpp`
  compiles `odrig_files.cpp` as it is, its platform header gives `ODRIG_FS LittleFS`
  (`firmware/standalone/platform/odrig_platform.h:11`), the same Arduino `FS` class
  with `mkdir`. The `SHARED` tuple of `test_usermod_files.py:15` names the source
  already, and the shared source still names neither `wled.h` nor `WLED_FS`.
- **What is out of scope.** The app's dialog does not name the refused command
  (`app/www/messages.js:131` takes the line and ignores it), so `storage-error` at
  begin, at data and at end read alike on the phone; naming the command's first words
  in `ofRefusal()` is an app change for a seed of its own, if the owner wants it. The
  8 KB of the folder is not in `usedBlocks` until the next start. `External storage:
  absent (read-only).` is the SD reader finding no card on the spare, `odrig_drive.cpp`
  as it is, which seed 77 left as its 5.3 and this seed does not touch. Memory on the
  spare: the `internal <N>` reading at the core's start is the owner's, as seed 77 left
  it; under about 327 KB some blocks of the core land in external memory, which is fine,
  and `external 0` on the spare's own image is seed 77's module finding, not this fault.
  The core is unchanged and no folder call joins the host contract. A test in seed 76's
  core suite of the symptom as the owner met it, `--store-fails-at 3` on
  `tests/core/test_first_animation.py`, the start's two removes being calls 1 and 2,
  belongs to seed 76's branch, which pull request #50 does not hold, and is not part of
  this seed; it is named in the hand-over as a gap for a seed after the merge. Faults of
  the flash itself stay refused in words and discarded; a storage WLED could not mount
  at all would show no `5.1 MB` line and is not covered. The merge order of pull
  requests #49 and #50, and the image with all three changes built from `master` after
  both merge, are the owner's.
- **Where the work goes.** `firmware/usermod/odrig_files.cpp`: `FOLDER_PATH` beside
  `FOLDER` at line 7, and in `beginFile()` (185-208) the open at 202 tried once more
  after `ODRIG_FS.mkdir(FOLDER_PATH)`; `tests/firmware/test_usermod_files.py:386`, the
  rule in its new form; `tests/firmware/test_usermod_files_host.py`, new, with its
  stand-in and its five cases; `tests/firmware/test_storage.py`, the littlefs rule;
  `docs/firmware.md:910-911`, `917-924` and `928`; `tests/firmware/test_docs.py:251-258`;
  `docs/drifts.md` at its end; `AGENTS.md`, the line of this seed, which on the branch
  names the open pull request as seed 77's line does; the spec in
  `docs/specs/78-p1-the-first-write-makes-the-storage-folder/`, with `verification.md`
  written by the last task in the form of seed 77's. What stays: `core/`, `app/`,
  `emulator/`, `firmware/fwtool/`, `firmware/usermod/odrig_drive.cpp`,
  `firmware/usermod/odrig_usermod.cpp`, both platform headers, the standalone firmware,
  `docs/core.md`, `docs/commands.md`, and `tests/firmware/test_usermod_files.py` but for
  line 386.
- **Where it lands.** On the branch `seed-77-firmware-for-the-spare-module` of pull
  request #50, after `43a62587`, seed 77's task 7, as further commits: first `git merge
  origin/master` on the branch, `master`'s head being the branch's base and the commit of
  this seed, which brings this seed's folder, without conflict, its `AGENTS.md` line, and
  nothing else. That merge is not clean: it conflicts in `AGENTS.md`, in "What is coming",
  because the branch reworded seed 77's line to "implemented in open PR #50; ..." and
  `master` adds this seed's line right after seed 77's line as `master` has it, two
  changes side by side; a dry `git merge-file` of the three versions ends in one block
  over those lines and nothing else. It is kept by hand with both lines: seed 77's as the
  branch has it, then this seed's as `master` has it, "planned; ...", 147 lines in all,
  under the 150 the onboarding suite allows. The merge commit holds that resolution and
  nothing else, and the onboarding suite is run on it before the next commit, with seed 77
  `in_progress` and this seed `remaining`. Then the spec commit; then one commit per task,
  `Seed 78 task <n>: <title>`, each ticking its checkbox in this seed's `tasks.md`, the
  first setting the state `in_progress` and, in the same commit, rewording this seed's
  `AGENTS.md` line to "implemented in open PR #50; ..." beside seed 77's; the state stays
  so until #50 merges, when it is `completed`, as seed 77's. No new pull request. `gh pr
  edit 50` gives the pull request a title that names both seeds and a description that
  names this seed, its verdict, the folder, and the owner's open checks of this seed
  beside seed 77's. From the first task on, the onboarding suite passes with both seeds
  `in_progress` and both lines naming the open pull request. Three images, built on this
  Windows computer with the shared toolchains through `ODRIG_TOOLS`, each from a clean
  tree so that its record says `trackedDirty` false, in this order: the installation's,
  `python firmware/fw.py build` and `python firmware/verify_build.py`, then the spare's,
  `build --module n8r2` and `verify_build.py --module n8r2`, both from the pushed head of
  the pull request, the installation's first because its build removes the spare's ELF
  (seed 77's `verification.md`); then the spare's combined image, from a local merge
  commit of that head with `seed-76-empty-board-first-animation` at `abc75ea3`, made in a
  detached worktree of its own and never pushed, the conflicts of `AGENTS.md` and of the
  change log of `docs/decisions.md` kept by hand with both sides, seed 76's entry before
  seed 77's as the older branch, `docs/drifts.md` merged by union as `.gitattributes` has
  it, none of which the build reads, built as `build --module n8r2` and verified as
  `--module n8r2`, its `.build.json` naming the merge commit. All on the Drive under
  `odrig archive/seed-78/`, every file named by the seed, the commit, the module and its
  offset, none named `odrig-firmware.bin` or `odrig-firmware-n8r2.bin`, which the
  archive's root and the tool use: `odrig-seed78-<commit>-n16r8-at-0x10000.bin` and
  `odrig-seed78-<commit>-n8r2-at-0x10000.bin`, `<commit>` the short hash of the pull
  request's head, and `odrig-seed78-<commit>-plus-seed76-n8r2-at-0x10000.bin`, `<commit>`
  the short hash of the merge commit, each with its `.bin.sha256`, the hash and the
  delivered name, its `.bin.build.json`, the tool's record as it is, and its
  `-image-info.txt` and `-verification.json`, the files of `verify_build.py` renamed, as
  seed 77's delivery named them. `README.txt` beside them, LF and ASCII, in the form of
  seed 77's: the seed's title and the pull request's address; a block per image with its
  file, its bytes, its SHA-256, its environment, its release name and the flash size of
  its header; the source commit of each, the merge's two parents named for the combined
  one; what the seed fixes, in words; how to flash from the phone, the application image
  at 0x10000 and no other, the offset field read before `Flash`, the flash settings kept,
  no erase, neither bootloader nor table written; that the `Installation:` line is read
  first, with the four readings as seed 77's README has them, and that `reset other` right
  after a flash and `reset power-on` after a power cycle are neither a finding; which
  image to flash on the spare for the upload check, the combined one, since it alone holds
  seed 76's change, the pull-request images carrying the fix and showing `mapping-missing`
  on an empty board until both pull requests merge; what to do when no hotspot shows a
  minute after a flash, as seed 77's README says; that no APK is built, the APK of seed
  75, `odrig archive/seed-75/odrig-seed75-f5ad253.apk`, working with every image, and an
  APK without an `Installation:` line being older and replaced first; and that the files
  above the folder are untouched. The subfolder `only-if-the-flash-was-erased/` is
  delivered again from the pull-request head's spare build, self-contained as seed 77's
  convention has it: `odrig-seed78-<commit>-n8r2-bootloader-at-0x0.bin` and
  `odrig-seed78-<commit>-n8r2-partitions-at-0x8000.bin`, each with its `.sha256`, the
  table byte for byte the Drive's `wifi-storage/odrig-8mb-partition-table-at-0x8000.bin`,
  and `only-if-the-flash-was-erased/README.txt` in the words of seed 77's: for a spare
  whose flash was erased or written at 0x0 or 0x8000 by mistake and for nothing else,
  never on the installation's board, the order bootloader, table, the spare's image, the
  settings kept, no erase, the storage at 0x310000 not written. The links sent to the
  owner are those of the files, in the owner's words "not of the folder but of the files":
  the full link of each of the three images, and of the bootloader and the table of the
  subfolder. After both pull requests merge, the image with all three changes is built
  from `master`; until then the combined image is the one that has them, and its record
  says what it is.

## Required Behavior

1. On a storage whose folder `/odrig` does not exist, the firmware's `write_open`
   makes the folder once and answers 1, and the write goes on: `write`, `write_close`,
   `rename` and `read_at` answer as on a storage that had the folder, and the bytes read
   back are the bytes given. The core's `upload begin` on such a storage answers
   `{"ok":true,"chunk":1500,"replacing":false}`.
2. On a storage that has the folder, a `write_open` whose open succeeds calls `mkdir`
   never and answers as today; one whose open fails there calls it once, which answers
   true, opens once more and answers -1 as today. A `mkdir` the file system refuses
   makes `write_open` answer -1, as a failed open does today, with nothing written.
3. The start writes nothing and makes no folder: `status` on an empty storage answers as
   seed 76 has it, and `open` and `read_at` on a missing folder answer 0 and -1 as today.
4. The core, the host contract of `core/include/odrig_core.h` and `docs/core.md`, the
   command list, the app and the emulator are unchanged; `docs/firmware.md` says who
   makes the folder and when.
5. The usermod names `ODRIG_FS.mkdir` once, in `odrig_files.cpp`, with `FOLDER_PATH`, and
   `rmdir` and `format` nowhere, which the text rule of
   `tests/firmware/test_usermod_files.py` checks; the host test of
   `tests/firmware/test_usermod_files_host.py` runs the source on this computer; the
   littlefs rule is pinned in `tests/firmware/test_storage.py`.
6. The two pull-request images and the spare's combined image build and verify, and the
   installation's image differs from seed 77's by the fix alone.
7. With the combined image on the spare, the first upload from the phone is accepted,
   the animation plays, and `mapping.json` and `show.json` lie beside its file, as seed
   76's requirement 3.3 says; a second upload makes no folder.

## Definition Of Done

1. The host suites: `tests/firmware/test_usermod_files_host.py` with its five cases, the
   first seen failing first with `write_open` -1 and `mkdir` 0, the third and the fourth
   with `mkdir` 0, and the second and the fifth passing before as guards; the text rule of
   `tests/firmware/test_usermod_files.py:386` seen failing first,
   `[] != ['FOLDER_PATH']`; `tests/firmware/test_docs.py` with the new sentence, seen
   failing first; `tests/firmware/test_storage.py` with the littlefs rule, a guard. Each
   failure seen goes into its commit message, and `tasks.md` says which task adds a test
   of a fault.
2. The firmware's suites through the runner,
   `python tests/run.py --suites firmware,firmware-host,runner --workers 2`, the three
   junction failures of `test_env` and `test_paths` being this computer's arrangement,
   as seed 77's `verification.md` records; `python core/build.py test` with no test
   added or changed; the onboarding suite,
   `python -B -m unittest discover -s tests/onboarding -t .`, for the `AGENTS.md` line;
   the converter's documentation test, `python -B -m unittest tests.converter.test_docs`,
   after the page changes; the workflow building and verifying both pull-request images.
3. The three images built on Windows with the shared toolchains, in the order the
   installation's, the spare's, the combined one, each verified by `verify_build.py` with
   its module, the spare's and the combined one's headers saying 8 MB, the installation's
   16 MB, every record `trackedDirty` false, the combined one's naming the merge commit.
4. The Drive, `odrig archive/seed-78/`: the three images with their `.bin.sha256`,
   `.bin.build.json`, `-image-info.txt` and `-verification.json`, the README, and the
   subfolder `only-if-the-flash-was-erased/` with the bootloader, the table, their
   `.sha256` and their README; no file named `odrig-firmware.bin` or
   `odrig-firmware-n8r2.bin`; nothing above the folder touched. The full links of the
   files sent to the owner, each of the three images and the two files of the subfolder,
   and no folder's link.
5. `verification.md` of the spec in the form of seed 77's: the commits by task, the
   suites by task with the failures seen first and their text, the three images with
   their bytes, SHA-256, ELF SHA-256, header and release name, the merge's two parents,
   the tool versions and the build times, the Drive paths and links, the result of the
   workflow's checks on the pull request, and what stays open. Pull request #50's title
   and description edited to name this seed; the branch's `AGENTS.md` line naming the
   open pull request; the state `in_progress` until the merge.
6. The owner, with the combined image flashed on the spare from the phone at 0x10000, the
   checks only a person can make, open until the owner reports them: (1) the Target page
   shows `Installation: odrig_ESP32-S3_8MB_qspi <date> <time> internal+microsd external
   2097152 internal <N> reset other` right after the flash, or `reset power-on` after a
   power cycle, neither a finding, no `The installed show is invalid` line and no `Last
   fault` line; `external 0` means the wrong image or seed 77's module finding. (2) The
   Animations page shows `Internal storage: 0 animations, free 5.1 MB of 5.1 MB`. (3) The
   Upload page offers `Choose a ready-made animation`, `Internal storage` and `Upload to
   the installation`, shows `Sending: N%, K KB a second` while it goes, then `Uploaded as
   animation 1 time-standalone-6-melting-c.odrg. It plays in the playlist.`, and the
   animation is on the LEDs. (4) The Animations page shows `1 animation`, free `5.0 MB` or
   `5.1 MB` of 5.1 MB, and the item listed at the root. (5) After the board is powered off
   and on and the phone connects again, the same item is listed and plays, and the Target
   page has no invalid-show line, which shows that `show.json` was written beside the
   file; a missing `mapping.json` would not show there, the core playing the built-in
   mapping without it. (6) A second upload of another ready-made animation ends with
   `Uploaded as animation 2 ...`. With a computer, when one reaches the spare: `python
   firmware/fw.py read-show build/spare-show` lists `mapping.json`, byte for byte
   `mapping/legs-20.json`, `show.json` with the items, and the `.odrg` files, which is
   what shows the mapping file. Seed 77's own open checks stay as its `verification.md`
   has them.

## Open Questions

None. The owner asked for a fixed seed on top of the previous seed's branch with zero
open questions, answered on its own; what is decided here is that the fault is the
firmware's files host, the folder `/odrig` never made on a board that only ever got
application images, and that the host makes it, inside `write_open`, once, when a write
finds it missing, by one `mkdir` after a failed open and the open again, rather than by
`open(path, "w", true)` of the framework, which would walk and make the folders of the
path at every write of every board and hide the call from the text rule, where the
`mkdir` costs a storage with the folder nothing and is counted exactly once by the rule;
that the path given is `/odrig` without the slash, the form `VFSImpl::mkdir()` and
littlefs document, beside `FOLDER` which keeps its slash as the prefix of every file
path; that the folder is the host's to make and not the core's, since the host contract
names no folder and no call to make one, the core knows no paths, every other host has
its folder, and a call added to the contract would reach every host for one platform's
rule; that it is not made at the start, which seed 76 decided writes nothing, and not by
the usermod's `setup()`, which would make the firmware decide to write; that the text
rule of `tests/firmware/test_usermod_files.py` becomes `mkdir` exactly once, in
`odrig_files.cpp`, with `FOLDER_PATH`, and `rmdir` and `format` still forbidden; that
the host is run on this computer by a new test with a stand-in file system that refuses
a file in a missing folder, beside a littlefs test that pins the rule; that the work
lands on pull request #50's branch as further task commits after seed 77's task 7, the
branch first brought up to date with `origin/master`, whose one conflict, the two lines
of `AGENTS.md`, is kept by hand with seed 77's line as the branch has it and this seed's
after it, reworded by the first task; no new pull request, the pull request's title and
description naming this seed; that the delivery is three images on the Drive under
`odrig archive/seed-78/`, the two pull-request images and the spare's combined image
from a local merge with seed 76's branch at `abc75ea3`, never pushed, named
`odrig-seed78-<commit>-plus-seed76-n8r2-at-0x10000.bin`, the one the owner flashes
for the upload check, with the bootloader and the table delivered again in the
subfolder under this seed's names, and the file links sent in words; that a core test of
the symptom in seed 76's suite is not part of this seed, having nowhere to land until
both pull requests merge, and is named in the hand-over; and that the app's dialog, the
SD reader's `read-only`, the memory reading at the core's start and the merge order of
the two pull requests are not this seed's. Nothing here needs the owner: no command is
added, nothing of hardware or power is touched, and no decision of
[decisions.md](../../docs/decisions.md) changes, the folder's place being seed 04's drift
and the host's duty to supply file access being the runtime architecture as it stands;
the only checks left to the owner are those a person makes on the phone and the LEDs.
