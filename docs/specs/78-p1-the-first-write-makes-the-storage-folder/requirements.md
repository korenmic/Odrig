# Requirements

Seed 78, `project-seeds/78-p1-the-first-write-makes-the-storage-folder/seed.md`. The
firmware's files host, `firmware/usermod/odrig_files.cpp`, makes the folder `/odrig` of
the board's storage once, inside `write_open`, when a write finds it missing; its tests,
the firmware's page and a drift entry; on pull request #50's branch, with three images
delivered. The core, the host contract, the command list, the app, the emulator, the
firmware tool and every other source of the usermod are not changed.

## 1. The folder made by the first write

1.1 On a storage whose folder `/odrig` does not exist, the firmware's `write_open`,
`beginFile()` of `firmware/usermod/odrig_files.cpp`, makes the folder and answers 1,
and the write goes on: `write`, `write_close`, `rename` and `read_at` answer as on a
storage that had the folder, and the bytes read back are the bytes given. With seed
76's change beside this one, on the spare's combined image, the core's `upload begin` on
such a storage answers `{"ok":true,"chunk":1500,"replacing":false}`; on this branch
alone an empty storage has no `mapping.json`, the core stops at `mapping-missing`
(`core/src/core.cpp:390-393`) and `upload begin` is refused `show-invalid` before the
folder is asked for. That part is shown by the owner's check (3), not by a task.
1.2 The folder is made inside `write_open` and nowhere else, after a failed open: one
call `ODRIG_FS.mkdir(FOLDER_PATH)` and, when it answers true, one more open of the same
path for writing. `openNamed()`, `readAt()`, `removeFile()` and `renameFile()` are not
changed and keep taking a missing folder for missing files.
1.3 A `write_open` calls `mkdir` at most once and opens for writing at most twice;
nothing loops, and nothing of a refusal is kept: a later `write_open` whose open fails
asks for the folder again, once.
1.4 A storage that has the folder pays nothing: a `write_open` whose open succeeds calls
no `mkdir` and opens once, and answers as today.
1.5 A `mkdir` the file system refuses, a folder that cannot be made or a file in its
name, makes `write_open` answer -1 with no second open and nothing written. An open
refused on a storage that has the folder, as by a fault of the flash, gets one `mkdir`,
which answers true, and one more open, which fails again, and `write_open` answers -1
as today, with nothing written.
1.6 `FOLDER_PATH`, `"/odrig"`, lies beside `FOLDER`, which stays `"/odrig/"`, the
prefix of every file path. The comment above it says what is, and no history: that a
storage that was formatted and never had a show has no such folder, and that the file
system makes no folder for a file. The comment above the opens says that a storage
without the folder gets it first.
1.7 Every file the core writes gets the folder, since each begins with `write_open`:
`upload.part` at `upload begin`, `pending.txt`, `mapping.part`, `show.part` and the
`.part` files of the settings. On a storage without the folder the `upload data` lines
and the `upload end` that writes `show.json` beside the file, and with seed 76's change
`mapping.json` before it, pass as they do on a storage with it; the files beside the
upload are shown by the owner's checks (5) and the `read-show` of a computer.
1.8 The change asks for no memory: one more string constant in flash, and the
framework's `mkdir` frees what it takes. The folder takes two blocks of storage once in
the life of the storage, which `usedBlocks` is not told of until the next start. Both
opens and the `mkdir` lie inside the `Timed` of `beginFile()`.

## 2. The start

2.1 The start writes nothing and makes no folder: its two storage calls, `remove
upload.part` and `remove show.part`, answer 0 on a storage without the folder before
they touch the file system, no `write_open` is called at the start, and the usermod's
`setup()` makes no folder.
2.2 On a storage without the folder `open` answers 0 and `read_at` -1, as today.
2.3 `status` on an empty storage answers as it did before the change: with the pull
request's images `mapping-missing`, as on seed 77's; with the spare's combined image the
canvas of 60 x 60 and `"error":null`, as seed 76 has it.
2.4 The firmware writes, renames, deletes and makes a folder only inside one of the
storage functions: nothing of the firmware decides to write.

## 3. What stays as it is

3.1 The core is not changed: `core/`, the host contract of
`core/include/odrig_core.h` and `docs/core.md`, which name no folder and no call to
make one. `python core/build.py test` runs with no test added or changed, 1,051 tests
as seed 77's `verification.md` recorded them.
3.2 No command, reply member or error code is added; `docs/commands.md` is not changed.
3.3 The app and the emulator are not changed, and no APK is built.
3.4 `firmware/fwtool/`, `firmware/usermod/odrig_drive.cpp`,
`firmware/usermod/odrig_usermod.cpp`, both platform headers and the standalone firmware
are not changed; the standalone firmware takes the fix through
`firmware/standalone/src/shared_files.cpp`, which compiles `odrig_files.cpp` as it is.
3.5 Out of this seed: the app's dialog, which does not name the refused command; the
8 KB of the folder outside `usedBlocks` until the next start; the SD reader's
`External storage: absent (read-only).` on the spare; the internal memory reading at
the core's start; a test of the symptom in seed 76's core suite, which has nowhere to
land until both pull requests merge; faults of the flash itself; a storage WLED could
not mount at all; and the merge order of pull requests #49 and #50, with the image with
all three changes built from `master` after both merge. Those the owner must hear of are
named in the hand-over, as 8.3 says.

## 4. The tests

4.1 The text rule of `tests/firmware/test_usermod_files.py`, in
`test_files_are_written_renamed_and_removed_in_one_source_only`: `rmdir` and `format`
stay forbidden in every source of the usermod, and `ODRIG_FS.mkdir` is called exactly
once, in `odrig_files.cpp`, with `FOLDER_PATH`, and in no other source. Seen failing
first on the source as it is, `[] != ['FOLDER_PATH']`. Every other rule of the file
holds as it is.
4.2 `tests/firmware/test_usermod_files_host.py`, new, runs `odrig_files.cpp` on this
computer over a stand-in file system that, like the board's, refuses a file in a folder
that is not there, and has five cases:
`test_the_first_write_into_a_storage_without_the_folder_makes_it`,
`test_a_storage_with_the_folder_is_not_asked_for_it`,
`test_a_folder_the_file_system_refuses_makes_the_write_fail`,
`test_a_write_refused_in_a_present_folder_is_tried_once_more_and_fails` and
`test_a_read_in_the_missing_folder_is_a_missing_file`. The first is seen failing first
with `write_open` -1 and `mkdir` 0, the third and the fourth with `mkdir` 0; the second
and the fifth pass before the fix, as guards. It skips unless the host compiler is
GNU-style.
4.3 `tests/firmware/test_storage.py` gets
`test_a_fresh_storage_refuses_a_file_in_the_folder_until_the_folder_is_made`, a guard
of the file-system rule the fix rests on, which passes before the fix.
4.4 The firmware's suites through the runner,
`python tests/run.py --suites firmware,firmware-host,runner --workers 2`, pass but for
the three failures of `test_env` and `test_paths` under the `hosts/` junction, this
computer's arrangement as seed 77's `verification.md` records; the core's suite, the
onboarding suite and the converter's documentation test,
`python -B -m unittest tests.converter.test_docs`, pass.

## 5. The pages

5.1 `docs/firmware.md`, "What the firmware does": the "At start" paragraph no longer
implies that `install-show` is the only maker of the folder: the files are there as
`install-show` put them there or as the core's changes wrote them, and its long line is
wrapped under 90 columns. The "Storage" paragraph gains, after "nothing of the firmware
decides to write.", the sentence "The folder itself is made by `write_open`, once, when
a write finds it missing: a storage that WLED formatted holds WLED's own files and no
`/odrig` until the first write into it, and the file system makes no folder for a
file." The row of `write_open` in the table says that when the open fails the folder is
asked for once, made if it is missing, and the open tried once more.
5.2 `tests/firmware/test_docs.py` keeps every string it pins in "What the firmware
does" and gains the words "The folder itself is made by `write_open`, once, when a
write finds it missing", seen failing first before the page changes.
5.3 `docs/drifts.md` gains at its end `## Seed 78: who makes the folder`, with its
**Question.**, **Answer.** and **Resolution.**, and says that it shows a gap in a
governing document. The change log of `docs/decisions.md` gets no entry: no decision
changes.
5.4 `docs/core.md` and `docs/commands.md` are not changed.

## 6. The branch, the pull request and the state

6.1 The work lands on the branch `seed-77-firmware-for-the-spare-module` of pull
request #50, after seed 77's task 7, the merge of `master` and this spec's commit, as
one commit per task, `Seed 78 task <n>: <title>`, each ticking its own checkbox in this
spec's `tasks.md`. No new pull request is opened.
6.2 The first task sets the seed's state to `in_progress` and, in the same commit,
rewords this seed's line in `AGENTS.md` to "implemented in open PR #50; ..." beside seed
77's; the state stays `in_progress` until #50 merges. From that commit on the onboarding
suite passes with both seeds `in_progress`, both lines naming the open pull request,
and `AGENTS.md` under the 150 lines the suite allows.
6.3 `gh pr edit 50` gives the pull request a title that names seeds 77 and 78, and a
description that names this seed, its verdict, the folder made by `write_open`, and the
owner's open checks of this seed beside seed 77's.

## 7. The images and their delivery

7.1 Three images are built on this Windows computer with the shared toolchains through
`ODRIG_TOOLS`, each from a clean tree so that its record says `trackedDirty` false, in
this order: the installation's, `python firmware/fw.py build` and
`python firmware/verify_build.py`; the spare's, `python firmware/fw.py build --module
n8r2` and `python firmware/verify_build.py --module n8r2`, both from the pushed head of
the pull request; then the spare's combined image, from a local merge commit of that
head with `seed-76-empty-board-first-animation` at `abc75ea3`, made in a detached
worktree of its own and never pushed, built as `build --module n8r2` and verified as
`--module n8r2`.
7.2 The merge for the combined image keeps the conflicts of `AGENTS.md` and of the
change log of `docs/decisions.md` by hand with both sides, seed 76's entry before seed
77's as the older branch, and merges `docs/drifts.md` by union as `.gitattributes` has
it; its `.build.json` names the merge commit.
7.3 The headers of the spare's image and the combined one say 8 MB and the
installation's 16 MB; the installation's record differs in its inputs from seed 77's
installation record by `firmware/usermod/odrig_files.cpp` alone.
7.4 On the Drive under `odrig archive/seed-78/`:
`odrig-seed78-<commit>-n16r8-at-0x10000.bin` and
`odrig-seed78-<commit>-n8r2-at-0x10000.bin`, `<commit>` the short hash of the pull
request's head, and `odrig-seed78-<commit>-plus-seed76-n8r2-at-0x10000.bin`, `<commit>`
the short hash of the merge commit; each with its `.bin.sha256`, the hash and the
delivered name, its `.bin.build.json`, the tool's record as it is, and its
`-image-info.txt` and `-verification.json`, the files of `verify_build.py` renamed. No
file is named `odrig-firmware.bin` or `odrig-firmware-n8r2.bin`, and nothing above the
folder is touched.
7.5 `README.txt` beside them, LF and ASCII, in the form of seed 77's: the seed's title
and the pull request's address; a block per image with its file, its bytes, its
SHA-256, its environment, its release name and the flash size of its header; the source
commit of each, the merge's two parents for the combined one; what the seed fixes, in
words; how to flash from the phone, the application image at 0x10000 and no other, the
offset field read before `Flash`, the flash settings kept, no erase, neither bootloader
nor table written; that the `Installation:` line is read first, with the four readings
of seed 77's README, and that `reset other` right after a flash and `reset power-on`
after a power cycle are neither a finding; that the combined image is the one to flash
on the spare for the upload check, since it alone holds seed 76's change, the
pull-request images carrying the fix and showing `mapping-missing` on an empty board
until both pull requests merge; what to do when no hotspot shows a minute after a
flash, as seed 77's README says; that no APK is built, the APK of seed 75,
`odrig archive/seed-75/odrig-seed75-f5ad253.apk`, working with every image, and an APK
without an `Installation:` line being older and replaced first; and that the files
above the folder are untouched.
7.6 The subfolder `only-if-the-flash-was-erased/`, from the pull-request head's spare
build: `odrig-seed78-<commit>-n8r2-bootloader-at-0x0.bin` and
`odrig-seed78-<commit>-n8r2-partitions-at-0x8000.bin`, each with its `.sha256`, the
table byte for byte the Drive's `wifi-storage/odrig-8mb-partition-table-at-0x8000.bin`,
and a `README.txt` in the words of seed 77's: for a spare whose flash was erased or
written at 0x0 or 0x8000 by mistake and for nothing else, never on the installation's
board; the order bootloader, table, the spare's image; the settings kept, no erase, the
storage at 0x310000 not written.
7.7 The links sent to the owner are the full links of the files: each of the three
images, and the bootloader and the table of the subfolder; no folder's link.
7.8 The workflow `.github/workflows/firmware-hosts.yml`, unchanged, builds and verifies
both pull-request images on the pushed head, and its checks pass.

## 8. The record, the hand-over and the owner's checks

8.1 `verification.md` of this spec, in the form of seed 77's: the commits by task; the
suites by task with the failures seen first and their text; the three images with their
bytes, SHA-256, ELF SHA-256, header and release name; the merge's two parents; the tool
versions and the build times; the Drive paths and the links; the result of the
workflow's checks on the pull request; and what stays open.
8.2 The owner's checks, with the combined image flashed on the spare from the phone at
0x10000, are the owner's and stay open until the owner reports them; they are listed
in `tasks.md` under "Owner acceptance". Seed 77's own open checks stay as its
`verification.md` has them.
8.3 The hand-over tells the owner in words, in the notification itself, everything left
open; a note in `verification.md` does not count for it. Beside the links of 7.7 it
names the owner's six checks of 8.2 and seed 77's open checks; the core test of the
symptom, `--store-fails-at 3` on `tests/core/test_first_animation.py` in seed 76's
suite, the start's two removes being calls 1 and 2, as a gap proposed for a seed after
both pull requests merge; the merge order of pull requests #49 and #50 as the owner's;
and the image with all three changes, built from `master` after both merge, as the
owner's, the combined image being the one that has them until then. It also proposes,
as a seed of its own if the owner wants it, that the app's dialog name the refused
command, and names the gap of the host contract of `docs/core.md`, which says nothing of
where the files live or who makes the place, recorded in seed 78's drift entry.
