# Tasks

Each task is one commit on the branch `seed-77-firmware-for-the-spare-module` of pull
request #50, after seed 77's task 7, the merge of `master` and this spec's commit, named
`Seed 78 task <n>: <title>`, with only its own checkbox ticked. Every test of a fault is
seen failing before the change, and the failure seen goes into the commit message. Code
carries no history.

- [x] 1. The folder made by `write_open`
  - `tests/firmware/test_usermod_files_host.py`, new, `TheStorageFolder`: the stand-in
    `odrig_platform.h` with its file system of folders and files, its `mkdir` and
    write-open counters and its two refusals, `unmakeable` and `writesRefused`; the
    program `files-host <scenario>` and its lines; the five cases. A test of a fault:
    run against the source as it is first, and seen failing:
    `test_the_first_write_into_a_storage_without_the_folder_makes_it` with `write_open`
    -1, no folder and `mkdir` 0,
    `test_a_folder_the_file_system_refuses_makes_the_write_fail` and
    `test_a_write_refused_in_a_present_folder_is_tried_once_more_and_fails` with `mkdir`
    0; `test_a_storage_with_the_folder_is_not_asked_for_it` and
    `test_a_read_in_the_missing_folder_is_a_missing_file` passing, as guards.
  - `tests/firmware/test_usermod_files.py:386`, in
    `Host.test_files_are_written_renamed_and_removed_in_one_source_only`: `rmdir` and
    `format` forbidden everywhere, `ODRIG_FS.mkdir` exactly once, in `odrig_files.cpp`,
    with `FOLDER_PATH`. A test of a fault: seen failing first, `[] != ['FOLDER_PATH']`.
  - `firmware/usermod/odrig_files.cpp`: `FOLDER_PATH` with its comment after `FOLDER`,
    and in `beginFile()` the open tried once more after `ODRIG_FS.mkdir(FOLDER_PATH)`,
    with the comment above the opens; then both tests pass, and every other rule of
    `test_usermod_files.py` holds as it is.
  - `tests/firmware/test_storage.py`, `FreshStorage`:
    `test_a_fresh_storage_refuses_a_file_in_the_folder_until_the_folder_is_made`, a guard
    of the file-system rule, which passes before and after the fix; the commit message
    says it is a guard, not a test of a fault.
  - Set the seed's state to `in_progress`, and in the same commit reword this seed's
    line of `AGENTS.md`, "What is coming", from "planned; ..." to "implemented in open
    PR #50; ..." with the rest of its words, beside seed 77's line.
  - Run the firmware's suites through the runner,
    `python tests/run.py --suites firmware,firmware-host,runner --workers 2`, the three
    junction failures of `test_env` and `test_paths` being this computer's arrangement,
    and the onboarding suite, `python -B -m unittest discover -s tests/onboarding -t .`.
  - Requirements: 1.1-1.8, 2.1-2.4, 3.1-3.4, 4.1-4.3, 6.1, 6.2.

- [x] 2. The pages
  - `tests/firmware/test_docs.py`, `Firmware`,
    `test_it_says_what_the_firmware_writes_how_it_paces_and_what_an_upload_measured`: "The
    folder itself is made by `write_open`, once, when a write finds it missing" among its
    `expected`, every string it pins kept. A test of a fault: seen failing first before
    the page changes: `'The folder itself is made by `write_open`, once, when a write
    finds it missing' not found in ...`.
  - `docs/firmware.md`, "What the firmware does": the "At start" paragraph, the files
    there as `install-show` put them there or as the core's changes wrote them, its long
    line wrapped under 90 columns; the "Storage" paragraph's new sentence after "nothing
    of the firmware decides to write."; the row of `write_open`, the folder asked for
    once when the open fails, made if it is missing, and the open tried once more.
  - `docs/drifts.md`, at its end: `## Seed 78: who makes the folder`, with its
    **Question.**, **Answer.** and **Resolution.**, saying that it shows a gap in a
    governing document. No entry in the change log of `docs/decisions.md`;
    `docs/core.md` and `docs/commands.md` unchanged.
  - Run the firmware's suites through the runner, the converter's documentation test,
    `python -B -m unittest tests.converter.test_docs`, and the onboarding suite.
  - Requirements: 5.1-5.4.

- [ ] 3. The pull request and the three images
  - Push the branch. `gh pr edit 50` with a title that names seeds 77 and 78 and a
    description that keeps seed 77's and names this seed, its verdict, the folder made by
    `write_open` and the owner's open checks of this seed beside seed 77's. No new pull
    request.
  - From the pushed head, on this computer with the shared toolchains through
    `ODRIG_TOOLS` and a clean tree, in this order: `python firmware/fw.py build` and
    `python firmware/verify_build.py`, then `python firmware/fw.py build --module n8r2`
    and `python firmware/verify_build.py --module n8r2`; the spare's header saying 8 MB,
    the installation's 16 MB, both records `trackedDirty` false, and the installation's
    `inputs` differing from seed 77's installation record by
    `firmware/usermod/odrig_files.cpp` alone. Run the firmware's suites through the
    runner, `python core/build.py test`, unchanged, the converter's documentation test
    and the onboarding suite.
  - The combined image: a detached worktree of its own under `scratch/` at the pushed
    head, a local merge commit there of `seed-76-empty-board-first-animation` at
    `abc75ea3`, never pushed, the conflicts of `AGENTS.md` and of the change log of
    `docs/decisions.md` kept by hand with both sides, seed 76's entry before seed 77's,
    `docs/drifts.md` merged by union; `python firmware/fw.py build --module n8r2` and
    `python firmware/verify_build.py --module n8r2` there, its header saying 8 MB, its
    `.build.json` naming the merge commit with `trackedDirty` false.
  - The Drive, `odrig archive/seed-78/`: `odrig-seed78-<head>-n16r8-at-0x10000.bin`,
    `odrig-seed78-<head>-n8r2-at-0x10000.bin` and
    `odrig-seed78-<merge>-plus-seed76-n8r2-at-0x10000.bin`, each with its `.bin.sha256`,
    its `.bin.build.json`, its `-image-info.txt` and its `-verification.json`; the
    `README.txt` as the design gives it; `only-if-the-flash-was-erased/` with
    `odrig-seed78-<head>-n8r2-bootloader-at-0x0.bin` and
    `odrig-seed78-<head>-n8r2-partitions-at-0x8000.bin`, their `.sha256` and their
    `README.txt`. No file named `odrig-firmware.bin` or `odrig-firmware-n8r2.bin`;
    nothing above the folder touched.
  - Write `verification.md` of this spec in the form of seed 77's, with the commits,
    the suites and the failures seen first, the three images, the merge's two parents,
    the tool versions and build times, the Drive paths and the links of the files, the
    workflow's result and what stays open. The state stays `in_progress`. Commit, push,
    read the workflow's checks on the pull request, and notify the owner in words with
    the full link of each of the three images and of the bootloader and the table of the
    subfolder, no folder's link; the owner's six checks of this seed and seed 77's open
    checks; the core test of the symptom, `--store-fails-at 3` on
    `tests/core/test_first_animation.py` in seed 76's suite, proposed as a seed after
    both pull requests merge; the merge order of #49 and #50 as the owner's; the image
    with all three changes, built from `master` after both merge, as the owner's; the
    proposal of a seed in which the app's dialog names the refused command; and the gap
    of the host contract of `docs/core.md` recorded in seed 78's drift entry.
  - Requirements: 3.5, 4.4, 6.3, 7.1-7.8, 8.1-8.3.

## Owner acceptance (not claimed by automated tasks)

On the phone, with the combined image,
`odrig-seed78-<merge>-plus-seed76-n8r2-at-0x10000.bin`, flashed on the spare from the
phone at 0x10000: (1) the Target page shows `Installation: odrig_ESP32-S3_8MB_qspi
<date> <time> internal+microsd external 2097152 internal <N> reset other` right after
the flash, or `reset power-on` after a power cycle, neither a finding, no `The installed
show is invalid` line and no `Last fault` line; `external 0` means the wrong image or
seed 77's module finding. (2) The Animations page shows `Internal storage: 0
animations, free 5.1 MB of 5.1 MB`. (3) The Upload page offers `Choose a ready-made
animation`, `Internal storage` and `Upload to the installation`, shows `Sending: N%, K
KB a second` while it goes, then `Uploaded as animation 1
time-standalone-6-melting-c.odrg. It plays in the playlist.`, and the animation is on
the LEDs. (4) The Animations page shows `1 animation`, free `5.0 MB` or `5.1 MB` of
5.1 MB, and the item listed at the root. (5) After the board is powered off and on and
the phone connects again, the same item is listed and plays, and the Target page has no
invalid-show line, which shows that `show.json` was written beside the file; a missing
`mapping.json` would not show there, the core playing the built-in mapping without it.
(6) A second upload of another ready-made animation ends with `Uploaded as animation 2
...`. With a computer, when one reaches the spare: `python firmware/fw.py read-show
build/spare-show` lists `mapping.json`, byte for byte `mapping/legs-20.json`,
`show.json` with the items, and the `.odrg` files, which is what shows the mapping file.
Seed 77's own open checks stay as its `verification.md` has them. These remain open
until the owner reports them.
