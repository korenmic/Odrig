# Verification

Seed 78 on the branch `seed-77-firmware-for-the-spare-module` of pull request #50 of
`korenmic/Odrig`, after seed 77's task 7 (43a62587). The commits: 03071daf the merge of
`master` that brought the seed, fce609d7 the spec, 9e95af45 task 1, 478912d8 task 2;
the two pull-request images were built from 478912d8, the spare's combined image from a
local merge of 478912d8 with seed 76's branch, and this commit, task 3, adds this record
and ticks its checkbox. Everything below ran on this Windows 11 computer on 2026-11-06,
local time UTC+2, except the workflow's run, on GitHub's runners. No board was flashed or
reached by this work: every physical check is the owner's, and nothing below claims one.

## The commits, by task

- 03071daf, "Merge master into seed 77's branch: seed 78's seed": `master` at 390f47b7
  holds the seed; the one conflict, the lines of seeds 77 and 78 in `AGENTS.md`, kept
  with both lines.
- fce609d7, "Specify seed 78: the first write makes the storage folder": the
  requirements, the design and the three tasks.
- 9e95af45, "Seed 78 task 1: The folder made by `write_open`": `FOLDER_PATH`, `"/odrig"`,
  beside `FOLDER` in `firmware/usermod/odrig_files.cpp`, and in `beginFile()` one
  `ODRIG_FS.mkdir(FOLDER_PATH)` after a failed open and, when it answers true, the open
  once more; `tests/firmware/test_usermod_files_host.py`, new, the class
  `TheStorageFolder` with its stand-in file system and five cases; the text rule of
  `tests/firmware/test_usermod_files.py`; the guard `FreshStorage` of
  `tests/firmware/test_storage.py`; the seed's state `in_progress` and its `AGENTS.md`
  line naming the open pull request.
- 478912d8, "Seed 78 task 2: The pages": `docs/firmware.md`, the "At start" and
  "Storage" paragraphs and the row of `write_open`; `tests/firmware/test_docs.py`; the
  entry "Seed 78: who makes the folder" at the end of `docs/drifts.md`.
- This commit, task 3: this record and the checkbox.

## The suites, by task

The runner is `python tests/run.py` with `ODRIG_TOOLS` pointing at the shared toolchains.
`firmware` fails the same three tests on every run, the junction failures of this
computer that seed 77's `verification.md` explains, and nothing else.

- Task 1: `runner: 26 tests, OK`; `firmware-host: 37 tests, OK`; `firmware: 665 tests,
  FAILED (failures=3)`, the three, 659 before the task; onboarding `Ran 88 tests`, `OK`.
  Seen failing first against the source as it was:
  `test_the_first_write_into_a_storage_without_the_folder_makes_it`, `write_open` -1, no
  folder, `mkdir` 0 and every later call -1 where 1, `/odrig` and 1 were wanted;
  `test_a_folder_the_file_system_refuses_makes_the_write_fail`, `mkdir` 0 at both points
  where 1 and 2 were wanted;
  `test_a_write_refused_in_a_present_folder_is_tried_once_more_and_fails`, `mkdir` 0 and
  one open for writing where 1 and 2 were wanted, 0 and 2 at the end where 2 and 4 were;
  `Host.test_files_are_written_renamed_and_removed_in_one_source_only`,
  `Lists differ: [] != ['FOLDER_PATH']` for `odrig_files.cpp`. The guards
  `test_a_storage_with_the_folder_is_not_asked_for_it`,
  `test_a_read_in_the_missing_folder_is_a_missing_file` and `FreshStorage` passed before
  and after.
- Task 2: `runner: 26 tests, OK`; `firmware-host: 37 tests, OK`; `firmware: 665 tests,
  FAILED (failures=3)`, the three; the converter's documentation test `Ran 38 tests`,
  `OK`; onboarding `Ran 88 tests`, `OK`. Seen failing first: `test_docs.Firmware`, its
  test of what the firmware writes, how it paces and what an upload measured,
  `'The folder itself is made by `write_open`, once, when a write finds it missing' not
  found in ...`.
- Task 3, from the head 478912d8: `python tests/run.py --suites
  firmware,firmware-host,runner --workers 2`, `runner: 26 tests, 12 s, OK`,
  `firmware-host: 37 tests, 7 s, OK`, `firmware: 665 tests, 130 s, FAILED (failures=3)`,
  the three; `python core/build.py test`, `Ran 1051 tests in 316.771s`, `OK (skipped=1)`,
  no core test added or changed; `python -B -m unittest tests.converter.test_docs`, `Ran
  38 tests in 12.579s`, `OK`; the onboarding suite, `Ran 88 tests in 6.096s`, `OK`.

## The three images

The tools, from the records: Python 3.14.2, PlatformIO Core 6.2.0, Node.js v20.18.0,
npm 10.8.2, WLED v16.0.1 at 29b389df, esptool v5.4.0 in the image-info texts; the host
Windows-11-10.0.26200-SP0, win32 x86_64. Every record says `trackedDirty` false, and each
`verify_build.py` run found the ESP32-S3 header valid, the module's flash size and
release name, and the player's three entry points linked. Built in this order, the
installation's first because its build removes the spare's ELF: the installation's,
57 seconds, 01:57 to 01:58; the spare's, 40 seconds, 01:58 to 01:59; the combined one,
43 seconds, 02:00, each from build caches of earlier builds of this computer.

- The installation's, module `n16r8`, from 478912d8:
  `odrig-seed78-478912d-n16r8-at-0x10000.bin`, 1,880,048 bytes, SHA-256
  `975bca8a7258af8ef5253b0bc4392f8d16a8d8fb7358dc1e8c3f74b7f8dd440b`, environment
  `odrig_microsd`, release name `odrig_ESP32-S3_16MB_opi`, header `Flash size: 16MB`,
  the ELF 32,906,376 bytes with SHA-256
  `ed8d7cadfbafff08ab03c6a48d7e78714d8f310b67e022d1e8a0984444e6cd2f`; inputs SHA-256
  `a233311ab65418a062cd49e7b9fb389b36e4b9237595e030d6992a78015250e0`.
- The spare's, module `n8r2`, from 478912d8:
  `odrig-seed78-478912d-n8r2-at-0x10000.bin`, 1,877,504 bytes, SHA-256
  `ce0b734ec95d09504f250ea437af970aad6a00b1e2badc6ad7d6c62a30dc94fd`, environment
  `odrig_microsd_n8r2`, release name `odrig_ESP32-S3_8MB_qspi`, header
  `Flash size: 8MB`, the ELF 32,891,480 bytes with SHA-256
  `7d94e829d0490588854864bcb91668e069948671a4d25dada0450a1700f7cb82`; the same inputs.
- The spare's combined image, module `n8r2`, from 96a65d9e, a local merge never
  pushed, its parents 478912d8, the head of #50, and abc75ea3, seed 76's branch of #49;
  `AGENTS.md` kept with the three seeds' lines, the change log of `docs/decisions.md`
  with seed 76's section before seed 77's bullet, `docs/drifts.md` merged on its own:
  `odrig-seed78-96a65d9-plus-seed76-n8r2-at-0x10000.bin`, 1,881,056 bytes, SHA-256
  `a22ac2f5baadad088e35187628d649465042f6b0cff4e51a62baf05e9ca6cba2`, environment
  `odrig_microsd_n8r2`, release name `odrig_ESP32-S3_8MB_qspi`, header
  `Flash size: 8MB`, the ELF 32,903,152 bytes with SHA-256
  `c73339bad2bf80a30dee9142fd15c559e2f2654ee5e77d96e69863223424dbcc`; inputs SHA-256
  `e3ca142c89d61ebb8fa8d50d409b22a98505130d5490cf90ae358d533f5ab7ea`. It holds the
  built-in mapping of seed 76, the spare's environment and host text of seed 77 and the
  folder of seed 78.

The subfolder `only-if-the-flash-was-erased/`, from the spare's build of 478912d8:
`odrig-seed78-478912d-n8r2-bootloader-at-0x0.bin`, 19,968 bytes, SHA-256
`883bb1e4765f12902e56b4bb901d0504df2ea2396bba8d79a7b29ae87d4b3658`, and
`odrig-seed78-478912d-n8r2-partitions-at-0x8000.bin`, 3,072 bytes, SHA-256
`dc19fc0fcd52efb130e273d9e69a3cfec1b86f1595a0f24bd74c0656f3efd17f`, byte for byte the
Drive's `wifi-storage/odrig-8mb-partition-table-at-0x8000.bin`.

## Where it is

Google Drive, `Artifacts/odrig/odrig archive/seed-78/`: the three images, each with its
`.bin.sha256`, its `.bin.build.json`, its `-image-info.txt` and its
`-verification.json`; `README.txt`, which says to flash the combined image for the upload
check, how to flash at 0x10000 only, the four readings of the `Installation:` line, the
upload check and what to do without a hotspot; and the subfolder with its two files,
their `.sha256` and its `README.txt`. No file is named `odrig-firmware.bin` or
`odrig-firmware-n8r2.bin`; nothing above the folder was touched. The links of the files,
the owner's order being the files and not the folder:

- `odrig archive/seed-78/odrig-seed78-96a65d9-plus-seed76-n8r2-at-0x10000.bin`, the one
  for the upload check:
  https://drive.google.com/file/d/1lI7jBBoi4enJ0KVjVDhC7FjV9HWr8EMX/view
- `odrig archive/seed-78/odrig-seed78-478912d-n8r2-at-0x10000.bin`:
  https://drive.google.com/file/d/1hBekrkzAe765FwoycDBEjmgjC8YzeyGf/view
- `odrig archive/seed-78/odrig-seed78-478912d-n16r8-at-0x10000.bin`:
  https://drive.google.com/file/d/1_u2RQoBC8MXlUBS4Am-VkZixRkBsM8kh/view
- in `odrig archive/seed-78/only-if-the-flash-was-erased/`:
  `odrig-seed78-478912d-n8r2-bootloader-at-0x0.bin`,
  https://drive.google.com/file/d/1V3Ucr_mqzSmABWpsaZmO6VxW99R0c3Oz/view, and
  `odrig-seed78-478912d-n8r2-partitions-at-0x8000.bin`,
  https://drive.google.com/file/d/1Q547bajeps94Da4JSh8Kqka7ZtOHsnod/view

Google Drive for desktop on this computer, version 133.0.2.0 since its own update at
22:45 UTC on 2026-11-05, uploaded the files but never wrote their Drive ids into its
database: there every one stayed a `local-` id of size 0, with its create operation kept
and an operation queue the client reported empty. The ids above come from the client's
own structured log, from the records in which Drive answered each create: each names the
file, its folder (`seed-78`, or its subfolder for the last two) and a size equal to the
file's on this computer, 1,881,056, 1,877,504, 1,880,048, 19,968 and 3,072 bytes. Each
link answers 401, sign-in required, to a request without an account, where an id that
does not exist answers 400. A second copy of the files, in
`odrig archive/seed-78-files/`, has ids of its own and is not linked. The combined image
was handed to the owner directly as well.

## The workflow

GitHub Actions run 42133276016, "Firmware hosts", on the head 478912d8: `Default
firmware (ubuntu-latest)` success, 23:57 to 00:07 UTC, and `Default firmware
(windows-latest)` success, 23:57 to 00:15 UTC. Each job builds and verifies both
pull-request images and runs the firmware suite on a runner without the junction. The
run after the push of this commit is read after it.

## Open

- The owner's checks, with the combined image flashed on the spare at 0x10000: the
  `Installation:` line `odrig_ESP32-S3_8MB_qspi ... external 2097152 internal <N> reset
  other`, or `reset power-on` after a power cycle, with no invalid-show line and no
  `Last fault` line; `Internal storage: 0 animations, free 5.1 MB of 5.1 MB`; the first
  upload of a ready-made animation to Internal storage ending with `Uploaded as animation
  1 <file>. It plays in the playlist.` and the animation on the LEDs; `1 animation`
  listed; after a power cycle still listed and playing; a second upload ending with
  `Uploaded as animation 2 ...`; with a computer, `read-show` listing `mapping.json`,
  `show.json` and the files. Seed 77's own open checks stay as its `verification.md` has
  them.
- On this branch alone an empty board still stops at `mapping-missing`: seed 76's change
  is on pull request #49. The merge order of #49 and #50, and the image with all three
  changes built from `master` after both merge, are the owner's; until then the combined
  image, from a local merge, is the one that has them.
- A core test of the symptom in seed 76's suite, `--store-fails-at 3` on
  `tests/core/test_first_animation.py`, proposed as a seed after both pull requests merge.
- A seed in which the app's dialog names the refused command, proposed if the owner
  wants it; and the gap of the host contract of `docs/core.md`, which says nothing of
  where the files live or who makes the place, recorded in the drift entry.
- The three junction failures on this computer.
- The seed's state stays `in_progress` until #50 merges.
