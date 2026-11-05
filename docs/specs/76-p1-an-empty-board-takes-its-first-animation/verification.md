# Verification

Seed 76 on the branch `seed-76-empty-board-first-animation`, pull request #49 of
`korenmic/Odrig` from `master` at 9c13db4. The commits: 2bd26ba the spec, b74934e task
1, e875ab8 task 2, 01f1514 task 3, 7c397c5 task 4; the firmware was built from 7c397c5,
and the last commit adds this record and the line of `AGENTS.md`. Everything below ran on
Windows 11 on 2026-11-05.

## The suites, by task

- Task 1: the core's suite through the runner, 1053 tests with 26 workers. Two tests
  encoded the old rule, an idle refresh and the memory of a missing mapping file, and now
  test a malformed file; every changed module passes. The four tests of `BuiltInMapping`
  and the startup test of a missing mapping file were seen failing against the old core
  with `'mapping-missing' is not None`, `mapping get` answering `editable` false, and
  `mapping set` refused with `show-invalid`.
- Task 2: the core's suite, 1058 tests, one of which encoded the old rule (`list` refused
  on a file set without its files) and now expects the empty list; it passes after the
  change. `test_first_animation` was seen failing against the core of task 1: the first
  upload with `'show-missing' is not None`, and the failing write of `mapping.part`,
  which found no such write to fail.
- Task 3: the emulator's suite, 657 tests, 19 skipped, and the app's suite, 447 tests,
  through the runner, all passing. The events test of an empty folder was seen failing
  against the page server without the fallback, `404 != 200`; the app's first upload was
  seen failing against the core of task 1 with `The installed show is invalid:
  show-missing ... (show-invalid)`.
- Task 4: the documentation tests of the core, the emulator, the converter and the app,
  and the onboarding suite, 88. The core's and the emulator's documentation tests were
  seen failing against the pages as they were. `tests.firmware.test_wifi_docs` cannot
  import `littlefs` in this Python, before this seed as after it.
- Task 5: the firmware's host suites through the runner. With `ODRIG_TOOLS` pointing at
  the shared toolchains below, `firmware-host` passes, 28 tests, and `firmware` runs 647
  tests with three failures of `test_env` and `test_paths`: `paths.inside()` follows
  every link, and the junction of `hosts/` leads into the home folder, outside the shared
  folder, which is this computer's arrangement and not the tool's; the other 644 pass.
  Without `ODRIG_TOOLS` the runner does not run `firmware`, since the tool's Python is
  not set up in `build/`, and `firmware-host` passes, 28 tests, 1 skipped. The onboarding
  suite with the line of `AGENTS.md`.

## The firmware

`build/firmware/out/odrig-firmware.bin`, 1,883,392 bytes, SHA-256
`6582821a821ce21faf3f2f3d0417c0687043d4184f4bca93c062ffd82ac5a0bd`, built by
`python firmware/fw.py build` from commit `7c397c56b232636413890ca65d4e4b2efd921e78`,
WLED's environment `odrig_microsd` on WLED v16.0.1 at 29b389d, PlatformIO 6.2.0, Node.js
20.18.0, esptool 5.4.0, the image's ELF SHA-256 `a8fc5b97e473244ea9a219b0991ca81a7f768543652e11368d0f3c1a2a58173d`.
The build record says the tracked sources were dirty: the one uncommitted change at that
moment was the line of seed 76 in `AGENTS.md`, which this commit carries; a trial build
of the same core and firmware sources earlier in the day gave the same bytes and the same
SHA-256. `firmware/verify_build.py`: the ESP32-S3 header, the checksum and the validation
hash valid, the three entry points of the player linked, `image-info.txt` and
`verification.json` beside the image; `physicalAcceptance` false, as the tool says of
every build.

The toolchains were shared from an earlier build on this computer through `ODRIG_TOOLS`,
set to `scratch/seed76-tools/`, whose `firmware/hosts` is a junction to that build's host
toolchains; `setup` fetched WLED's source afresh there and the checkout's copy was
patched and built in `build/firmware/`. A full build took 12 minutes, the rebuild from the
pushed head 28 seconds.

## Where it is

- Google Drive, `Artifacts/odrig/odrig archive/seed-76/`: `odrig-seed76-7c397c5.bin`, its
  `.sha256`, read back as `6582821a…a5a0bd`, its `.bin.build.json`, `-image-info.txt`,
  `-verification.json` and a `README.txt` that says how it is flashed from the phone: the
  application image at offset 0x10000, the flash settings kept, no erase, the bootloader
  and the partition table not written. The files above the folder are untouched.
- A GitHub pre-release of the image was refused to the agent's run as the creation of a
  public surface, and the record stays truthful rather than worked around. The owner
  publishes it with

  ```
  gh release create firmware-seed-76-7c397c5 --repo korenmic/Odrig --target 7c397c56b232636413890ca65d4e4b2efd921e78 --prerelease --title "Firmware of seed 76 (PR #49), built from 7c397c5" --notes "The odrig firmware from PR #49: a board without mapping.json and show.json takes its first animation. SHA-256 6582821a821ce21faf3f2f3d0417c0687043d4184f4bca93c062ffd82ac5a0bd." "G:\My Drive\Artifacts\odrig\odrig archive\seed-76\odrig-seed76-7c397c5.bin"
  ```

  after which the link is
  `https://github.com/korenmic/Odrig/releases/download/firmware-seed-76-7c397c5/odrig-seed76-7c397c5.bin`.
- No APK: the app is unchanged, and the APK of seed 75,
  `odrig archive/seed-75/odrig-seed75-f5ad253.apk`, works with this firmware.

## Open

- The owner's check on the spare board, with this firmware flashed and the phone:
  `Choose a ready-made animation`, `Internal storage`, `Upload to the installation`,
  `Uploaded as animation 1 <file>. It plays in the playlist.`, and the animation on the
  LEDs. The spare reports no PSRAM; the firmware takes the core's memory from the chip's
  internal memory first, which the original board left 65,000 bytes of with twenty
  outputs, and what the spare leaves is part of that check.
- The pull request's checks, the firmware hosts on Ubuntu and on Windows, were pending
  when this record was written and are read after the push of this commit.
- The seed's state stays `in_progress` until the merge, as `AGENTS.md` counts a seed
  completed when its implementation is merged.
