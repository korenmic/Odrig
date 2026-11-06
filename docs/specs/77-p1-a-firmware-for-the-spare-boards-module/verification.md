# Verification

Seed 77 on the branch `seed-77-firmware-for-the-spare-module`, pull request #50 of
`korenmic/Odrig` from `master` at bb0658e5, a pull request of its own beside #49, seed
76's. The commits: 73e566c0 the spec, ae4a2ca2 task 1, 6d974f7b task 2, a70fb837 task 3,
fcaf4aeb task 4, 71c92456 task 5, 4ee89921 task 6; both images were built from 4ee89921,
the pull request's head, and this commit, task 7, adds this record, ticks its checkbox
and sets the line of seed 77 in `AGENTS.md` to the open pull request. Everything below
ran on this Windows 11 computer on 2026-11-05, except the workflow's run, on GitHub's
runners. No board was flashed or reached by this work: every physical check is the
owner's, and nothing below claims one.

## The commits, by task

- 73e566c0, "Specify seed 77: a firmware for the spare board's module": the
  requirements, the design and the seven tasks; the seed, its state and its `AGENTS.md`
  line say the branch is a pull request of its own beside #49.
- ae4a2ca2, "Seed 77 task 1: The second environment and the spare's table":
  `[env:odrig_microsd_n8r2]` in `firmware/platformio_override.ini.in`, the table
  `firmware/partitions/odrig-8mb.csv`, the `8 MB` layout of `fwtool/partitions.py`,
  named by the end of a one-slot table, and the table among the provenance's inputs;
  the seed's state set to `in_progress`.
- 6d974f7b, "Seed 77 task 2: The commands on the 8 MB layout": `installations_layout()`
  of `fwtool/cli.py` refuses `restore-stock` and `install-firmware` on the spare's table
  before anything is written; `flash` and the other commands work on it as on the
  bigger layout.
- a70fb837, "Seed 77 task 3: The kind `n8r2` and `--module` on `build`": the kind in
  `KINDS` and `ON_NEWER`, `module_of()`, the field `module` of the build record,
  `--module n16r8|n8r2` on `build` with its conflicts, and the synopsis line of
  `docs/firmware.md`.
- fcaf4aeb, "Seed 77 task 4: `verify_build.py --module`": `MODULES`, the flash size of
  the header and the release name checked for the module, and `image-info-n8r2.txt`
  and `verification-n8r2.json` beside the spare's image.
- 71c92456, "Seed 77 task 5: The host text": `aboutHost()` names `external` and
  `internal`, the internal memory read in `setup()` before the core begins;
  `kAboutSize` of the core 128.
- 4ee89921, "Seed 77 task 6: The workflow and the documentation": the workflow builds
  and inspects the spare's image and keeps its ELF; the pages, the change log of
  `docs/decisions.md` and `docs/drifts.md`. Amended before the push so that the
  external-0 sentence of `docs/firmware.md` names the PSRAM's failed test beside the
  PSRAM not found, a reviewer's finding.
- This commit, task 7: this record, the checkbox and the line of `AGENTS.md`.

## The suites, by task

The runner is `python tests/run.py` with `ODRIG_TOOLS` pointing at the shared toolchains
below. `firmware` fails the same three tests on every run, the junction failures named
after the tasks, and nothing else; every new test passes.

- Task 1: `firmware-host: 28 tests, 7 s, OK`; `firmware: 650 tests, 110 s, FAILED
  (failures=3)`, the three; the spec commit ran 647 with the same three; onboarding
  `Ran 88 tests in 5.962s`, `OK`. Seen failing first: `test_wled.Override`,
  `Regex didn't match: '(?m)^\[env:odrig_microsd_n8r2\]\nextends = env:odrig_microsd$'`;
  `test_layouts.Tables` and `test_partitions.Parse`, `module 'fwtool.partitions' has no
  attribute 'EIGHT_MB'`, `'bigger' != '8 MB'` and `Failure not raised` for the one-slot
  table whose coredump lies at 0xBF0000; `test_layouts.OnEachLayout` with
  `layout='8 MB'`, `'layout: bigger, storage 262144 bytes' != 'layout: 8 MB, storage
  262144 bytes'`; `test_provenance.SourceIdentity`, `['core/player.cpp'] !=
  ['core/player.cpp', 'firmware/partitions/odrig-8mb.csv']`.
- Task 2: `firmware-host: 28 tests, 6 s, OK`; `firmware: 653 tests, 115 s, FAILED
  (failures=3)`, the three; onboarding `Ran 88 tests in 6.131s`, `OK`. Seen failing
  first: `test_layouts.RefusedOnTheSpare`, `restore-stock` with `Tuples differ: (0,
  'layout: 8 MB, storage 5111808 bytes\n[89 chars]}\n') != (1, '')`, the stock files
  written on the spare's table, `install-firmware` with `KeyError: 3211264`, the image
  written and the storage at 0x310000 read from a stand-in that holds none, and the
  table that cannot be read with `['read-flash', 'erase-region', 'write-flash'] !=
  ['read-flash', 'read-flash', 'erase-region', 'write-flash']`, the sequence without
  the first `read-flash`, which `test_flasher.RestoreStock`,
  `test_wifi_commands.InstallFirmware` and `test_limit_commands.InstallFirmware` saw
  too, and `[3, 8] != [4, 9]` for the reads of the storage after the firmware's answer.
- Task 3: `firmware-host: 28 tests, 6 s, OK`; `firmware: 657 tests, 112 s, FAILED
  (failures=3)`, the three; onboarding `Ran 88 tests in 5.745s`, `OK`. Seen failing
  first: `test_cli.Images`, `KeyError: 'n8r2'`; `test_cli.Building` and
  `test_cli.TheModule`, `error: unrecognized arguments: --module n8r2`, the refusal
  text and `invalid choice: 'n4r2'` not found in it; `test_microsd_build`, `'does not
  go with' not found`; `test_newer_software.TheImages`, `('firmware', 'probe',
  'microsd') != ('firmware', 'probe', 'microsd', 'n8r2')`; `test_build.VariantBuilds`
  of the host suite, `Items in the second set but not the first: 'n8r2'`;
  `test_provenance.SourceIdentity`, `KeyError: 'module'` and `write() got an unexpected
  keyword argument 'module'`; `test_docs.Firmware`, with the option in the code and the
  synopsis unchanged, `Regex didn't match: '(?m)^python3 firmware/fw\.py
  build\b.*\-\-module\b'`.
- Task 4: `firmware-host: 37 tests, 7 s, OK`; `firmware: 657 tests, 114 s, FAILED
  (failures=3)`, the three; onboarding `Ran 88 tests in 5.843s`, `OK`. Seen failing
  first: `test_verify.Modules`, `module 'verify_build' has no attribute 'Module'`; the
  six tests of `test_verify.Checked` and the one of `test_verify.Inspect`, `module
  'verify_build' has no attribute 'MODULES'`; `test_verify.TheOption`, the script
  taking no option and
  inspecting the installation's image, `1 != 2 : build inspection failed:
  image-missing: ...\build\firmware\out\odrig-firmware.bin is not there; build it
  first`.
- Task 5: the core's suite, `python core/build.py test`, `Ran 1051 tests in 389.880s`,
  `OK (skipped=1)`; `firmware-host: 37 tests, 8 s, OK`; `firmware: 658 tests, 163 s,
  FAILED (failures=3)`, the three; onboarding `Ran 88 tests in 5.382s`, `OK`. Seen
  failing first: `test_usermod_kept.TheAbout`,
  `'heap_caps_get_total_size(MALLOC_CAP_SPIRAM)' not found in '// The usermod that makes
  WLED the platform of the player. ...'`; `tests.core.test_readiness.TheHostsName`,
  against the core of 96 bytes, `'xxxx[61 chars]xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx' !=
  'xxxx[61 chars]xxxxxxxx...'`, 95 characters where 127 were expected.
- Task 6: `firmware-host: 37 tests, 8 s, OK`; `firmware: 659 tests, 133 s, FAILED
  (failures=3)`, the three; the core's documentation tests `Ran 18 tests in 0.341s`,
  `OK`; the converter's documentation test `Ran 38 tests in 13.088s`, `OK`; onboarding
  `Ran 88 tests in 6.648s`, `OK`. Seen failing first:
  `test_docs.Firmware.test_it_lists_the_regions_the_tools_write`, ``Regex didn't match:
  '(?m)^\| `spiffs` \| `0x310000` \| `0x4E0000`, 5,111,808 bytes'``;
  `test_it_names_the_spares_image_in_the_table_of_kinds`, ``Regex didn't match:
  '(?m)^\| `build --module n8r2` \| `odrig_microsd_n8r2` \| `odrig\-firmware\-n8r2\.bin`
  \| ...'``.
- Task 7, from the head 4ee89921, beside the builds below. While the spare's first
  build ran, 21:19 to 21:27: `python core/build.py test`, `Ran 1051 tests in 422.652s`,
  `OK (skipped=1)`; `python -B -m unittest tests.converter.test_docs`, `Ran 38 tests in
  13.459s`, `OK`; `python -B -m unittest discover -s tests/onboarding -t .`, `Ran 88
  tests in 6.682s`, `OK`. From 21:37, during the spare's build again and after it:
  `python tests/run.py --suites firmware,firmware-host,runner --workers 2`,
  `firmware-host: 37 tests, 7 s, OK`, `runner: 26 tests, 10 s, OK`, `firmware: 659
  tests, 128 s, FAILED (failures=3)`, the three. Then the onboarding suite again, 88,
  `OK`, with the line of `AGENTS.md`.

The three failures of `firmware` are the same on every run, and the spec commit had them
before any change: `tests.firmware.test_env.ChildEnvironment`, its
`test_each_folder_variable_is_an_absolute_path_inside_the_shared_toolchains` with
`PLATFORMIO_CORE_DIR is ...\seed76-tools\firmware\hosts\win32-x86_64\pio` and its
`test_no_variable_names_a_folder_in_the_home_folder`, which names one of the four
folder variables by the run, `PIP_CACHE_DIR is ...\seed76-tools\firmware\pip-cache` or
`PLATFORMIO_CORE_DIR is ...\seed76-tools\firmware\hosts\win32-x86_64\pio`, and
`tests.firmware.test_paths.WorkFolder`, its
`test_every_folder_of_the_tool_is_inside_the_work_folder_or_the_shared_toolchains` with
`...\seed76-tools\firmware\hosts\win32-x86_64\venv`. The cause: `ODRIG_TOOLS` is
`C:\Users\koren\src\Odrig\scratch\seed76-tools`, in the `scratch/` of the clone this
worktree lies in, whose `firmware/hosts` is a junction to the host toolchains of an
earlier build under the home folder. `paths.inside()` follows the link and so resolves
the folders of the first and the third test outside the shared folder; the second test
asks that every folder lie inside the checkout, which the shared folder itself does
not. That is an arrangement of this computer, not a fault of the branch: the workflow
runs without either and passes, below.

## The two images

Both were built from commit `4ee899219317b209d5115204065aedbde938b532` with a clean tree,
`trackedDirty` false in both records, the toolchains shared through `ODRIG_TOOLS` as in
seed 76's delivery. The tools, from the records: Python 3.14.2, PlatformIO Core 6.2.0,
Node.js v20.18.0, npm 10.8.2, WLED v16.0.1 at 29b389df, and esptool v5.4.0 in the
image-info texts; the host Windows-11-10.0.26200-SP0, win32 x86_64; the inputs' SHA-256
`2377f3d5ea46c2002a97fb0afadf77b266576192e41490c4bdc5a3a73bcee2b4` in both. Each
`verify_build.py` run found the ESP32-S3 header, the checksum and the validation hash
valid, the module's flash size and release name, and the three entry points of the
player linked; `physicalAcceptance` false in both verification files, as the tool says
of every build.

- The spare's, module `n8r2`: `odrig-firmware-n8r2.bin`, delivered as
  `odrig-seed77-4ee8992-n8r2-at-0x10000.bin`, 1,877,328 bytes, SHA-256
  `4411276b374bcf43d0ee8517880c6cabc119a303096fd0673ccdd189d926b90b`, built by
  `python firmware/fw.py build --module n8r2`, WLED's environment `odrig_microsd_n8r2`,
  the release name `odrig_ESP32-S3_8MB_qspi`, the header `Flash size: 8MB`, the ELF
  32,889,024 bytes with SHA-256
  `43b3fcf403242b6cf442583f0da05d48899a87e4aa01e6cd6657b500118dc5f2`; verified by
  `python firmware/verify_build.py --module n8r2`, `image-info-n8r2.txt` and
  `verification-n8r2.json` beside the image.
- The installation's, module `n16r8`: `odrig-firmware.bin`, delivered as
  `odrig-seed77-4ee8992-n16r8-at-0x10000.bin`, 1,879,856 bytes, SHA-256
  `2d4c426c2eac3cc7e91bc18c7516d9b3df99f342671c59bc956b08cc158c2691`, built by
  `python firmware/fw.py build`, WLED's environment `odrig_microsd`, the release name
  `odrig_ESP32-S3_16MB_opi`, the header `Flash size: 16MB`, the ELF 32,903,932 bytes
  with SHA-256 `7a6ada5d404606cf7c09470619111ddf4d4d5b2717e8a00db67ee6f12a95c192`;
  verified by `python firmware/verify_build.py`, `image-info.txt` and
  `verification.json` beside the image.

The builds, in the order they ran, in this computer's local time, UTC+2: the spare's
first, 9 minutes 23 seconds, 21:18 to 21:27, the framework compiled again for its
environment; then the installation's, 7
minutes 55 seconds, 21:27 to 21:35, and its `verify_build.py` ok. The installation's
build removed the spare's ELF from `.pio/build/odrig_microsd_n8r2/`, so the spare's
`verify_build.py --module n8r2` failed once, the symbol inspector finding no ELF; the
spare's build again from the same sources, 28 seconds, 21:36 to 21:37, then its
`verify_build.py --module n8r2` ok. The lesson for the next delivery: build the
installation's image first and the spare's after it, as the workflow does.

The subfolder `only-if-the-flash-was-erased/` holds the two files of the spare's build
that no command writes: `odrig-seed77-4ee8992-n8r2-bootloader-at-0x0.bin`, 19,968 bytes,
SHA-256 `883bb1e4765f12902e56b4bb901d0504df2ea2396bba8d79a7b29ae87d4b3658`, the
`bootloader.bin` of `.pio/build/odrig_microsd_n8r2/`, and
`odrig-seed77-4ee8992-n8r2-partitions-at-0x8000.bin`, 3,072 bytes, SHA-256
`dc19fc0fcd52efb130e273d9e69a3cfec1b86f1595a0f24bd74c0656f3efd17f`, its
`partitions.bin`, byte for byte the Drive's
`wifi-storage/odrig-8mb-partition-table-at-0x8000.bin`, the table read from the spare on
2026-11-03, the same SHA-256; each with its `.sha256`, and a `README.txt` of their own.

## Where it is

- Google Drive, `Artifacts/odrig/odrig archive/seed-77/`, on this computer
  `G:\My Drive\Artifacts\odrig\odrig archive\seed-77\`: the two images, each with its
  `.bin.sha256`, read back as the hashes above, its `.bin.build.json`, the tool's
  record as it is, and its `-image-info.txt` and `-verification.json`, the files of
  `verify_build.py` renamed; `README.txt`, which says which image is for which module,
  that only the application image is flashed, at offset 0x10000, the flash settings
  kept, no erase, the bootloader and the partition table not written, that the
  `Installation:` line is read first after the flash with its four readings, what is
  flashed when no hotspot shows, and what the subfolder is for; and the subfolder with
  its two files, their `.sha256` and their `README.txt`. No file of the delivery is
  named `odrig-firmware.bin` or `odrig-firmware-n8r2.bin`; the files above the folder
  are untouched; no storage image was read or printed. The folder:
  https://drive.google.com/drive/folders/1soAcG-jSuVO5nF9YiqNPCadib5liDjyP. The
  spare's image:
  https://drive.google.com/file/d/1oI39b1a-PWD5WGA-xvFkLAEwx24WEhKF/view. The
  installation's image:
  https://drive.google.com/file/d/1LPMm870Bx-fvcvUuLlxBdlCXQNZZLfgu/view. The
  subfolder:
  https://drive.google.com/drive/folders/16486U-2f6mm9QPMcfu02lExOHbrlqttJ. The two
  images and the subfolder's files lie again in `odrig archive/seed-77-final/`, copies
  made while the Drive client stalled on the folder; it synced since.
- The early images, in `seed-77/early-task-3/`, made during the run so that the owner
  could try the spare the same evening, before the pull request's head existed:
  `odrig-seed77-a70fb83-n8r2-at-0x10000.bin`, 1,877,296 bytes, SHA-256
  `c201a2eef0540032962e90531314075dafdb2ec4b551f698675af22300881d56`, built from task
  3's commit a70fb837 in a detached build worktree and verified with task 4's
  `verify_build.py` run from a copy,
  https://drive.google.com/file/d/1s621KsIj2o396KNRxBFzGQeiuMuEZw4g/view; and
  `odrig-seed77-06cad80-plus-seed76-n8r2-at-0x10000.bin`, 1,880,864 bytes, SHA-256
  `9bbdb12231fa5e1f7690f219222203f85f57208f26a9d8e7f5f68f25d3f09268`, built from a
  local merge commit 06cad803 of a70fb837 with seed 76's branch at abc75ea3, never
  pushed, the `AGENTS.md` conflict resolved with seed 77's line, so that the spare can
  be tried with both changes before the two pull requests merge,
  https://drive.google.com/file/d/1RshZ2Ar7mfiTt1RpoVY3qnTuykZ3Fshh/view. The folder:
  https://drive.google.com/drive/folders/1Uj75mW2zE1H0akTmG76TG6dW_9Vklzpm. The
  combined image lies again in `seed-77/early-combined/` and in
  `odrig archive/seed-77-early/`, copies made while the Drive client stalled, all three
  synced since. Neither early image is from a pull request's head; both are superseded
  by the images above once both seeds are merged.
- No APK: the app is unchanged, and the APK of seed 75,
  `odrig archive/seed-75/odrig-seed75-f5ad253.apk`, works with both images.

## The workflow

GitHub Actions run 42092451576, "Firmware hosts", on the head 4ee89921: `Default
firmware (windows-latest)` success, 19:17 to 19:36 UTC, and `Default firmware
(ubuntu-latest)` success, 19:17 to 19:24 UTC; both checks of the pull request passing
and its merge state `CLEAN` before the push of this commit. Each job builds and
verifies both images on a runner without the junction, so the three failures above are
this computer's only. The run after the push of this commit is read after it.

## Open

- The owner's checks of 7.4, none of which this work made: no board was flashed or
  reached. First with the spare board as it is, on the phone: the Target page's
  `Installation:` line and its invalid-show line, `out-of-memory` beside seed 76's build
  date confirming the starved core, `mapping-missing` or another date meaning the image
  that runs is not seed 76's. Then with the spare flashed with the spare's image at
  0x10000 from the phone: `Installation: odrig_ESP32-S3_8MB_qspi ... external <bytes>
  internal <bytes> reset <reason>`, the external bytes not 0, 2097152 expected, the
  reason `other` or `power-on`, and `The installed show is invalid: mapping-missing.`
  until seed 76's change is on the board too. Then, with a firmware that has both:
  `Choose a ready-made animation`, `Internal storage`, `Upload to the installation`,
  `Uploaded as animation 1 <file>. It plays in the playlist.`, and the animation on the
  LEDs. `external 0` beside `odrig_ESP32-S3_16MB_opi` means the installation's image
  was flashed and the spare's is flashed again; `external 0` beside
  `odrig_ESP32-S3_8MB_qspi` on the spare is a finding about the module for a seed of
  its own. No hotspot a minute after a flash: the spare's image again, then the
  installation's, then the subfolder, as the README says.
- Pull requests #49 and #50 are both open; the merge order is the owner's. After both
  merge, a firmware with both changes is built from `master`; until then the early
  combined image is the one that has both, and it is not from a pull request's head.
- The pull request's checks after the push of this commit are read after it.
- The three junction failures on this computer, as above.
- The seed's state stays `in_progress` until the merge, as `AGENTS.md` counts a seed
  completed when its implementation is merged. Nothing else: no new command, no
  decision about hardware, no APK.
