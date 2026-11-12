# Verification

## Software

Seed 87 is on the branch `seed-87-live-mirror`, pull request #68, made from
`all-unmerged-seeds` a19499fc, the branch of pull request #63, with `master`'s commit of the
seed, a66c1cd2, merged as 41f802a5. These are its commits, in order:

| Commit | What it is |
|---|---|
| d6f72cd2 | The spec |
| 2f10d58f | Task 1: planning and the plan in the core |
| 6700727d | Task 2: the ways and the push in the core |
| 9bf7ae8a | Task 3: the mirror's entry in the core |
| 33e8a86b | Task 4: `#plan` lines in the firmware |
| ff2a40e7 | Task 5: the emulator's ports as a board's |
| d94416bf | Task 6: `plan` in the command tool |
| a77a4610 | Task 7: the mirror's link and the man in the middle |
| ac0a13f9 | Task 8: the plan kept and shown, and the files |
| 570c0743 | Task 9: the page of a mirror |

- Tasks 1 to 3: `tests/core/test_plan.py`, the reply's members, planning off as before,
  every planned turn found in `status` at its start with its seed, over turns, a break, a
  cycle, Clocks only and a jump, the stops, the versions, and the push on the ways of the
  test host; `tests/core/test_mirror.py`, the mirror's turn on 60 x 60 with its seed, its
  brightness, its rotation, a test, the LEDs off, a turn joined late and the show going on
  after it. The core object grows by 24 bytes: the target file asks 131,069 bytes with a
  drive, below 131,072, and every frame stays under 512 bytes.
- Task 4: `tests/firmware/test_usermod_plan.py`, the two sockets' ways and their `#plan`
  lines, the lock tried and never waited for; the installation's image built then.
- Task 5: `tests/emulator/test_plan_push.py`, the push of the line port's connections, and
  the ways of `tests/emulator/test_lineport.py`.
- Task 6: the six forms of `plan` in `tests/emulator/test_tool.py`, by each transport.
- Task 7: `tests/emulator/test_middle.py`, the man in the middle with stand-ins of a stream
  and of HTTP, and an emulator as the board behind a mirror over its line port and over
  HTTP: lines and replies, the log, the options and their refusals, a lost link.
- Task 8: `tests/emulator/test_mirror.py`, two emulators over the line port and over HTTP,
  every change of picture of the mirror within two refreshes of the board's, joined late,
  after a `play` through the mirror and through the board, a file found nowhere fetched with
  `read` and kept, a lost link and the board's restart; the keeper and the driver with
  stand-ins; `tests/emulator/test_files.py`, the lookup of a key in the collections and the
  fetch.
- Task 9: `tests/emulator/test_mirror_page.py`, `hello`'s `mirror`, the `mirror` events, the
  board's marks in the log, a board of another canvas and the refused seek; the page's
  script and markup.

The suites at the head 570c0743, the head the files below were built from, run together by
`python tests/run.py`:

| Suite | Tests |
|---|---:|
| core | 1,341 |
| emulator | 763 |
| app | 712 |
| firmware | 696 |
| firmware host | 37 |
| converter | 552 |
| `npm test --prefix converter` | 1,606 |
| onboarding | 88 |
| mapping | 49 |
| runner | 26 |

They pass but for the failures known on this computer, which are not faults of the code:
`tests.app.test_message_source`, for Pillow is not installed here; the firmware suite's two
tests of `test_env` and its `test_paths`, for the toolchains are reached through a junction;
tests that failed on time under the load of the whole run and passed when run alone
(`tests.firmware_host.test_process`'s two, `tests.emulator.test_preview`'s refusal before
anything starts, `tests.app.test_folders`' levels and `tests.app.test_only_both`'s move);
and the app's five tests of a GIF and a video, which found the converter's packages missing
in this worktree and passed once `npm ci --prefix converter` had installed them. The
emulator's `tests.emulator.test_http` has a race of Windows' sockets, a 404 or 405 to a
request whose body is left unread, which fails about one run in five on the fused branch's
own head too; it passed in this run.

## Two emulators, one as the board

An emulator as the board on the demo show of 60 x 60, and two mirrors of it, each on a copy
of the show: one over the board's line port, `--mirror-tcp`, and one over HTTP,
`--mirror-http`. Commands went to the board and through both mirrors, by `odrigctl` over the
line port and over HTTP; after each, both mirrors' pictures were compared with the board's
over the same three seconds, each change of picture matched within two refreshes.

| What was done | What was seen |
|---|---|
| Both mirrors started after the board, joined late | `mirror: tcp 127.0.0.1:<port>` and `mirror: http 127.0.0.1:<port>`; both showing within 1 s; 100% and 99.3% of their changes of picture matched the board's |
| `plan` through the HTTP mirror | the board's plan, planning on, 8 items: the demo show's two animations by their keys, 30.6 s and 41.8 s turns, within 10 minutes |
| `odrigctl brightness 40` and `play 1` through the TCP mirror's line port | `{"ok":true}` each; the board's status at brightness 40; both mirrors 99.3% |
| `odrigctl play 2` through the HTTP mirror | `{"ok":true}`; both mirrors 100% |
| `play 1` straight at the board | both mirrors 99.3% |
| `off` straight at the board | the board and both mirrors dark, 150 frames each |
| `odrigctl on` through the TCP mirror over HTTP | both mirrors 100% |
| `POST /seek` on a mirror | `{"ok":false,"error":"mirror"}` |
| The board stopped | both mirrors go on with the plan they have, lit; the state `lost`; `odrigctl status` through a mirror over HTTP has its request closed, status 3 |
| The board started again on the same ports | both mirrors joined again, `linked`, 99.3% |
| The mirrors stopped | status 0; the board's planning off again, as they had found it |

Where a share is below 100%, one change of picture in about 150 was not matched within two
refreshes. The mirror's page showed the link, `linked`, the plan's version, the
board's status and picture, and the log's lines marked `board`.

## Builds

Built on Windows from the pushed head 570c0743 with a clean tree; each build record names
that commit and `trackedDirty` false. The installation's image first, then the spare's,
each passed `verify_build.py` for its module. The APK is signed with the persistent key;
`apksigner` confirmed the certificate of SHA-256
`5a489ec294e53cdec085d71092cf4e7285ae08d4d43c19929d84130f3649f0f1`, and `zipalign -c 4`
passed. They are in the Drive folder `odrig archive/seed-87-570c0743/`, each copy checked
against its SHA-256:

| File | Bytes | SHA-256 | Link |
|---|---:|---|---|
| `odrig-seed87-570c0743-n16r8-installation.bin`, the installation's board, `odrig_microsd` | 1,928,080 | `a61511be8f2d7ca7a4eaa65cdbb7fabfd026eee378a4b14f7dcb0ccbb4fcccdc` | [download](https://drive.google.com/uc?export=download&id=1y_1GoR2N7RG0HjHytnDGFJ5zjNK5dHBH) |
| `odrig-seed87-570c0743-n8r2-spare.bin`, the spare, `odrig_microsd_n8r2` | 1,925,552 | `1f72bff21d0c02acd88921756894c2f5761c853f9e9935e2a1663494909f4721` | [download](https://drive.google.com/uc?export=download&id=1obicZ5DwO-3WPm2L7rdgwD79srNrVvW1) |
| `odrig-seed87-570c0743.apk`, signed with the persistent key | 19,269,713 | `3512604bdccb19ae2e2ef9c13cf37dbd40acd845b4cb83a1cb455ca243821133` | [download](https://drive.google.com/uc?export=download&id=1heSEcW-fefKEJFwioq9QBJZ9F4wXWhsB) |

The app's files are unchanged by the seed.

## CI

The firmware workflow runs for pull requests into `master`; it was started on the branch by
hand, run 42944240846 of `seed-87-live-mirror` at 570c0743: the default firmware built and
its host tests passed on Windows and on Ubuntu.

## Open

- [ ] The owner's checks of "A mirror, by eye" in `docs/emulator.md`: the emulator beside
  the wall over USB and over Wi-Fi, showing what the wall shows turn by turn, a clock and a
  message with the wall's time and words, the LEDs dark while the wall's are off, and a
  display test; the Controller view and a phone through `--lan` steering the board through
  the emulator, and a phone straight at the board while the mirror runs.
- [ ] The firmware's `#plan` lines on the board's two sockets, seen on the board in a board
  session.
