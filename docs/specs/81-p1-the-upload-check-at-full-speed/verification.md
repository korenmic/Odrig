# Verification

Seed 81 on the branch `seed-81-upload-check-at-full-speed` of pull request #54 of
`korenmic/Odrig`, made from `master` at 0a72f895. Everything below ran on this Windows 11
computer, an Intel Core i7-14700, on 2026-11-06, local time UTC+2, except the workflows of
the pull request, on GitHub's runners. No board was flashed or reached by this work: every
physical check is the owner's, and nothing below claims one.

## The commits, by task

- adcc7ab4, "Specify seed 81: the upload check at full speed": the requirements, the
  design and the eight tasks.
- c6a721b7, task 1, "The charge of a call of the decoder": `kWalkDivisor`, `record_mode`
  and `charge_since` of the decoder; `odrig_host decode --taken`; `_taken`, `taken_in`,
  `taken_each` and `fade()` of `tests/core/support.py`; `TheChargeOfACall`; the seed's
  state `in_progress` and its line in `AGENTS.md`.
- de4504b5, task 2, "The check at every refresh, charged and paced": the bit fields of
  `Upload`, the `kUpload*` constants, `upload_refresh` with the internal `upload_step`,
  `pace_down` and `pace_up`, `new_second` in `player_poll`; `--trace-check`; the model of
  the rule and the reference player paced by it; `AtEveryRefresh` and `TheOwnersClock`;
  `Script`, `TheCheck` and `Quiet` counting by the rule; the tests of the core, the
  emulator and the app that counted the old pacing.
- 9d4ce319, task 3, "The rule pinned": `TheFade`, `ThePace` and `TheBounds`, and the drift
  "Seed 81: the files of the tests of the pace and of a debt".
- d7706060, task 4, "The core's pages": `docs/core.md` and `docs/commands.md`.
- d484d7e9, task 5, "The command tool and the emulator's check of the owner's clock":
  `BUSY_SECONDS` 10,800, `docs/emulator.md`, the test of the limit, and
  `tests/emulator/test_upload_check.py`.
- 79247d68, task 6, "The app says that the installation checks": `checking`,
  `checkingText` and `showChecking` of `app/www/upload.js`, the Upload screen and the
  forms, `docs/android-app.md`, and the app's tests and scenarios.
- 965c19a0, task 7, "The firmware's page and the change log": `docs/firmware.md` and the
  entry of 2026-11-06 at the end of the change log of `docs/decisions.md`.
- 2be7742e, the merge of `origin/master` at 4762dffa, which brought seed 82; the one
  conflict, the lines of seeds 81 and 82 in `AGENTS.md`, kept with both lines.
- This commit, task 8: this record, the drift entries, the seed's line in `AGENTS.md`
  naming the pull request, and the checkbox.

## The suites, by task, with the failures seen first

The runner is `python tests/run.py`; the app suite ran without `ODRIG_TOOLS`, the firmware
suite with it, where it fails only the three known tests of this computer's
shared-toolchain junction (`test_env` twice, `test_paths` once).

- Task 1: core 1065 tests OK (1 skipped), mapping 42 OK, onboarding 88 OK. A test of a
  new option: before the host had it, the five tests of `TheChargeOfACall` failed only as
  a usage error, `odrig_host decode --taken ...: status 64`.
- Task 2: core 1069 OK (1 skipped), emulator 657 OK (19 skipped), mapping 42 OK,
  onboarding 88 OK, app 447 with one failure, the gif's sampled texts, mended in the
  commit and run again alone: OK. Seen failing first against the core as it was:
  `AtEveryRefresh`, a host at 45 ms, `{"ok":false,"error":"busy"}` 1,333 times and then
  `no-upload` 10 times, where the reference player has `{"ok":true}` at the 76th refresh;
  `TheOwnersClock` `busy` 382 times at 20 ms, 361 at 30 ms, 1,223 at 45 ms, and at 50 ms
  `busy` 1,199 times and then `no-upload` 1,125 times.
- Task 3: core 1077 OK (1 skipped). Guards of task 2's rule; on their first run two files
  of the design did not do what it said of them (`ThePace` with `dense_clip(60, 6, 10)`:
  its check ended in the third second, `4990 not greater than 7000`; the debt test with
  `dense_clip(60, 60, 1)`: `Items in the second set but not the first: 62400`), and the
  tests took `dense_clip(60, 6, 30)` and ten pictures of noise; no fault of the core.
- Task 4: `tests.core.test_docs`, `tests.app.test_docs`, `tests.emulator.test_docs` 51 OK;
  onboarding 88 OK.
- Task 5: emulator 658 OK (19 skipped), onboarding 88 OK. Seen failing first:
  `AssertionError: 600.0 != 10800`.
- Task 6: app 451 OK, onboarding 88 OK. Seen failing first against the app as it was:
  `'Checking the animation on the installation: 0:02' not found in []` for the line on
  Upload, for a text's upload and for a clock's `Save`; and the cancel while checking,
  `after 10000 ms still not: the check under way`, the line staying at `Sending: 100%,
  117 KB a second`.
- Task 7: firmware 665 with the three known failures; firmware-host 37 OK, its one timing
  test (`test_parent_exit_closes_a_descendant_that_inherits_the_output_pipe`, a timeout of
  2 s) failing once under the parallel run and passing three times alone and in the suite
  run again; onboarding 88 OK; `tests.converter.test_docs` 38 OK.
- Task 8, on the merge 2be7742e: `python tests/run.py --workers 8`: app 451 OK, core 1077
  OK (1 skipped), converter 552 OK, converter-npm 1602 OK, mapping 42 OK, onboarding 88 OK,
  runner 26 OK; emulator 658 and firmware-host 37 each with one test that failed under the
  parallel load (`test_tool.Session.test_the_session_gives_the_replies_of_the_reference_by_each_transport_and_fills_the_log`,
  `KeyError: 'tcp'`, and the timing test above), each passing alone twice and both suites
  then passing whole, emulator 658 OK (19 skipped) and firmware-host 37 OK (1 skipped);
  firmware with `ODRIG_TOOLS` 665 tests, the three known failures and no other.

## The counts of the tests

- `AtEveryRefresh`: `{"ok":true}` at the 76th refresh after the last byte, as the rule
  gives.
- `TheOwnersClock`, the tracked clock (471,095 bytes, 14,401 steps, charge 657,686): at
  the 380th refresh every 20 ms, the 359th every 30 ms, the 1,221st every 45 ms and the
  2,322nd every 50 ms; 14,401 refreshes every 20 ms before.

## The measurements

The test host, a board without show files, `upload end` after every poll, from the last
byte to `{"ok":true}`, the core as it was and as it is:

| Host refreshes | Rotated clock, 498,211 bytes: before | after | Tracked clock: before | after |
|---|---:|---:|---:|---:|
| every 20 ms | 14,402 refreshes, 288.0 s | 374, 7.5 s | 14,402, 288.0 s | 380, 7.6 s |
| every 25 ms | | 361, 9.0 s | | 367, 9.2 s |
| every 30 ms | 28,802, 864.0 s | 353, 10.6 s | 28,802, 864.0 s | 359, 10.7 s |
| every 40 ms | | 1,201, 48.0 s | | 1,221, 48.8 s |
| every 45 ms | discarded after 60 s | 1,201, 54.0 s | discarded after 60 s | 1,221, 54.9 s |
| every 50 ms | discarded after 60 s | 2,289, 114.4 s | discarded after 60 s | 2,322, 116.1 s |

The emulator, the tracked clock over HTTP to an emulator on an empty folder: checked in
7.5 s, `status` reporting 47 to 50 refreshes a second during the check (two runs, 7.5 s
and 7.6 s).

The processor time of the check here, the core's sources at `-O2` in a scratch host that
polls every 20 ms, three runs on an idle computer: the rotated clock's whole check 23.6 to
23.8 ms, the tracked clock's 23.6 to 24.3 ms; a refresh of the rotated clock's check at
pace 1, 2 and 3 a median of 20, 39 and 76 µs and at most 41, 49 and 97 µs. The board, by the seed's basis
(its check of 2026-10-12 is 135 to 167 times slower than this computer, and 1.4 times
slower again beside its sends to twenty outputs: 189 to 234): 4.5 to 5.6 s of work for the
whole file, 3.8 to 4.8 ms a refresh at pace 1 and 14 to 18 ms at pace 3. So the estimate of
the seed stands: about 8 s on a board at 50 with room, within 30 s at 30 or more while a
show that is not dense plays, the rate kept at 20 or more from 22 before, and about 19 from
20 or 21. It stays an estimate until the owner's check below.

## The builds

Both from the pushed head 2be7742e, with a clean tree.

- The APK, built as this computer builds it (the staged web code, Capacitor's sync,
  Gradle without its daemon, the persistent key): `odrig-debug.apk`, 19,083,943 bytes,
  SHA-256 `748c48af71e944171fc476661bc3f8787ae801aa93e7b95d6406c186426bb452`, its
  certificate SHA-256 `5a489ec294e53cdec085d71092cf4e7285ae08d4d43c19929d84130f3649f0f1`,
  `zipalign -c 4` passed.
- The spare's image, `python firmware/fw.py build --module n8r2` (10 min 33 s) and
  `python firmware/verify_build.py --module n8r2`, with `ODRIG_TOOLS`:
  `odrig-firmware-n8r2.bin`, 1,881,712 bytes, SHA-256
  `e0f86e845e8faf5010d6b3f612a96c3f50987bf93041da8bc8c310de6cfa7f00`, environment
  `odrig_microsd_n8r2`, release name `odrig_ESP32-S3_8MB_qspi`, header `Flash size: 8MB`,
  `trackedDirty` false, the ELF 32,911,288 bytes with SHA-256
  `6d7762cacf4b37f758a29b3c30af02f8cc57d63da1b26c1fbf0f13c805cee651`, inputs SHA-256
  `73ca8a00de2be9c36bd1154537771d21cbe4deefb8bb3374394bcbcc10dc9529`; the player's three
  entry points linked. The tools: Python 3.14.2, PlatformIO Core 6.2.0, Node.js v20.18.0,
  npm 10.8.2, WLED v16.0.1 at 29b389df, esptool v5.4.0.

## Where they are

Google Drive, `Artifacts/odrig/odrig archive/seed-81/`
(<https://drive.google.com/drive/folders/1n1Y-c8GtSsziw_v54YNU8yAFi0QEGGji>); nothing above
the folder was touched:

- `odrig-seed81-2be7742.apk`:
  <https://drive.google.com/file/d/1cTBQAzzqPrdf1siM5ukUR8w4hPtWWpNu/view>, its `.sha256`:
  <https://drive.google.com/file/d/1A7dvADKR-7EMvIqOgtZClpgZ_-2jceNg/view>, and its
  `.build.json`.
- `odrig-seed81-2be7742-n8r2-at-0x10000.bin`, the build's `odrig-firmware-n8r2.bin`:
  <https://drive.google.com/file/d/16L8gzhd34ELqvJEgRE_MxXzF8jgypI_l/view>, its `.sha256`:
  <https://drive.google.com/file/d/15CVzRKDZAtBN4d1RHqXJD3JLzbcdtzrL/view>, its
  `.bin.build.json`, `-image-info.txt` and `-verification.json`.
- `README.txt`: <https://drive.google.com/file/d/1WesLLvoRgNQqivP28E2M55BccX7iIPw0/view>,
  what the files are and the owner's check.

## The pull request's checks

Read once on the head 2be7742e, before this commit: `Default firmware (ubuntu-latest)`
passed in 7 min 6 s; `Default firmware (windows-latest)` was still running.

## What stays open

- The owner's check on the spare board with that image and that APK (requirement 14.6):
  (1) what plays and the Show screen's `N refreshes a second`; (2) the rotated clock
  uploaded to `Internal storage`; (3) the Checking line counting from `0:00`; (4) the
  message by `0:30` at 30 or more, `1:00` at 25 to 29, `2:30` below 25, no limit while a
  dense animation plays; (5) the rate while it checks 20 or more from 22 before, the
  lowest noted from 20 or 21; (6) the clock on the LEDs; (7) the same to the card, the time
  and the lowest rate noted. Requirements 4.7 and 4.8 are shown by it.
- The stale `body_read` of a text's fault context at `core/src/upload.cpp`, proposed as a
  seed of its own: the context of a fault met in a text's or a clock's payload names the
  bytes of the body the decoder read for an earlier file, since a text never opens the
  decoder.
