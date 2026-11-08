# AGENTS.md

The entry file for every coding agent that works in this repository. Read all of it before
you do anything else.

## What this is

odrig is the LED animation system of an art installation: a small board drives a canvas of
60 x 60 LEDs and plays animations that are stored on it. This repository holds the tools
that make the animations, the player, an emulator that shows them without the board, and
the program for the board. The pages for newcomers are in the folder `agent/`.

The converter is the JavaScript tool in `converter/`, started as `node converter/odrig.js`,
and the only one: convert and pack with it. The Python package `odrig/` was the converter
before it. It is now a library that reads and writes the project's files for the tests and
the tools, and it holds the generators; what it answered to the converter's tests is
stored with them.

## Read first

1. [agent/README.md](agent/README.md): what the project is and what its parts are.
2. [agent/vocabulary.md](agent/vocabulary.md): what the project's words mean. The other
   documents use them without explaining them.
3. [agent/working-rules.md](agent/working-rules.md): the rules below, in full.
4. [agent/getting-started.md](agent/getting-started.md), when this clone is not set up
   yet: what the computer needs, the setup, the tests, and the demo show in the emulator.

## Then read, by task

| Your task | Read |
|---|---|
| Make or change an animation or a show | [agent/animation-guide.md](agent/animation-guide.md), then [docs/format.md](docs/format.md) and [docs/show.md](docs/show.md) |
| Change the converter | [docs/converter.md](docs/converter.md), [docs/format.md](docs/format.md), [docs/reasons.md](docs/reasons.md) |
| Change the Python library, a generator or the test vectors | [docs/python-library.md](docs/python-library.md), [docs/format.md](docs/format.md), [docs/catalog.md](docs/catalog.md) |
| Change the core | [docs/core.md](docs/core.md), [docs/format.md](docs/format.md), [docs/show.md](docs/show.md), [docs/commands.md](docs/commands.md), [docs/catalog.md](docs/catalog.md) |
| Change the emulator or the command tool | [docs/emulator.md](docs/emulator.md), [docs/commands.md](docs/commands.md) |
| Change the operators' app | [docs/android-app.md](docs/android-app.md), [docs/commands.md](docs/commands.md) |
| Change how the LEDs are laid out | [docs/mapping.md](docs/mapping.md) |
| Change the firmware, or do anything with the board | [docs/firmware.md](docs/firmware.md), [docs/firmware-prerequisites.md](docs/firmware-prerequisites.md), [docs/firmware-additions.md](docs/firmware-additions.md), [docs/microsd.md](docs/microsd.md), [docs/wifi.md](docs/wifi.md), and "If you have a board" in the working rules |
| Find out what was decided, and why | [docs/decisions.md](docs/decisions.md), then [docs/drifts.md](docs/drifts.md) |

`docs/drifts.md` is long: it holds every question that was settled on the way. Search it
for your subject; do not read it through. Planned work is in `project-seeds/`, one folder
for each seed, and the specs made from the seeds are in `docs/specs/`. The tests are in
`tests/`, one folder for each suite, and the converter's own are in `converter/tests/`;
the getting-started page has the command of each.

## Rules you may not break

1. **Your own branch, your own clone.** Never commit on `master` directly, and never work
   in a checkout that another contributor uses, nor switch its branch: the emulator serves
   the app of the checkout it runs from, and the APK is built from the same files, one
   code. Before a commit, `git branch --show-current` names your branch.
2. **One task, one commit.** The commit also ticks the task's checkbox in its `tasks.md`.
3. **Stage named paths only.** Never `git add -A`, `git add .`, `git add -u` or
   `git commit -a`. After a commit, read `git show --stat`.
4. **A test for a fault is seen failing first**, before the fault is mended, and the
   failure you saw goes into the commit message.
5. **Code carries no history**: no comment about a seed, a task, a date or an earlier
   version.
6. **A suite is selected by discovery.** Nothing lists test files. Run the suites your
   task names before you commit.
7. **A question the documents leave open is answered, not asked**: decide it, and record
   it at the end of `docs/drifts.md`. This does not hold for what needs the owner.
8. **The scope of a seed is fixed once its tasks are being done.** A gap you find becomes
   a new seed, proposed to the owner.
9. **What you leave open, you tell the owner in words.** A note in a file does not count.
10. **`docs/drifts.md` and the change log of `docs/decisions.md` are added to at the end
    only.**
11. **Before you merge, bring your branch up to date with `origin/master`** and run every
    suite that works on your computer. Never rewrite history that has been pushed.
12. **Any refresh rate from 20 to 50 a second on the board is acceptable.** Do no work to
    raise a rate inside that range.

[agent/working-rules.md](agent/working-rules.md) has each of these with its reason.

## Never touch

- `esp32-backup/` and `firmware/wled-16.0.1/`. They exist, untracked, on the first
  computer only, and they are what brings a board back. Never change, move, delete or
  commit them.
- An untracked file that you did not make. The checkout on the first computer holds some.
- The board, except through `firmware/fw.py` and `odrigctl`, and then under the rules "If
  you have a board": a brightness of 40 or less, one program at a time, the flash never
  erased, and the firmware built only as the tool builds it.

What you make under `build/`, `.venv/` and `converter/node_modules/` is yours to make and
to remove, and never to commit.

## What needs the owner

Do not decide these, and do not work on a guess. Ask in words and wait.

- Every addition to the command list.
- Anything that changes a decision in `docs/decisions.md`.
- Anything about hardware or power.
- A check that only a person can make: what the LEDs show, or what a phone gets. The
  operators' app has such a check, in [docs/android-app.md](docs/android-app.md).

## If you work on Windows

The Python library, the core's build, the emulator, the command tool and the app's tool
work on Windows 10 and 11, and every suite that runs there passes: the converter's, the
Python library's, the core's, the emulator's and the command tool's, the app's and the
onboarding suite. That was seed 11, `project-seeds/11-p0-emulator-and-tools-on-windows/`,
and seed 26 for the work that came after it.

- The core is built there by `python core/build.py shared`, not by `make`.
- Windows has no virtual serial port. The emulator takes command lines on a TCP port, and
  the command tool reaches it with `--tcp` or `--http`.
- The converter's own suite, `npm test --prefix converter`, passes on Windows too. Its
  test in Chrome starts Chrome there without a window, as everywhere.
- Firmware setup/build and its host-only tests run on Windows x64; the board stays with its operator.
  Read [host builds](docs/firmware.md#host-builds-and-verification) for cache paths and coverage.
- Nothing is installed in the system. A compiler or another program that is fetched is
  unpacked into `tools/`, and a trial goes into `scratch/`. Git ignores both.
- Code runs on macOS, Linux and Windows alike: [the rules](agent/working-rules.md#code-that-runs-on-every-computer).

[agent/getting-started.md](agent/getting-started.md#on-windows) has the setup and the
commands of Windows.

## What is coming

These entries cover features not in the repository yet or not yet merged, and the
cancelled fallback. A seed's merged implementation is completed. Unperformed
physical checks remain recorded in its spec and verification documents without
keeping the seed in progress.

- **A second firmware that does not use WLED**, seed 12: cancelled by the owner; do not resume its unfinished tasks.
- **Current limits for the wall and each snake**, seed 45: implemented in open PR #15; not yet merged.
- **Internal-storage clocks and messages**, seed 61: planned; recognize matching clock/message paths in internal storage and SD, with a later managed upload attempt of the seven approved messages. A persistent dropdown chooses SD card (default) or Internal storage for matching path/type duplicates; owner product questions are resolved.
- **Board time and a daily on/off schedule**, seed 64: ready for S2S; read/set time over existing transports, default On 18:00/Off 06:00, and ignore scheduling while time is invalid. APK auto-sync defaults on and waits for the next connection at least 15 minutes after the last confirmed sync. Follow the phone's zone/DST; manual On/Off overrides until explicitly returned to scheduling. No open product questions remain.
- **Complete Snake10 cross-wire retirement**, seed 71: finish removing dedicated emulator observers, counters and remaining product paths after seed69; preserve ordinary snake10, generic installed geometry and historical records. No open product questions remain.
- **Persistent mapping checkbox and typed pin edits**, seed 72: expose the lock directly in Settings, retain its confirmed app-local value across restarts, and make GPIO assignments editable text fields through the existing validated mapping save path. No firmware or hardware change and no open product questions.
- **An archive of animations uploaded from the app**, seed 73: one zip picked on the phone, opened in the app, its animations ticked and uploaded one by one through the existing upload to the board's storage or its card; no new command.
- **Phone storage explorer and animation backups**, seed 74: planned; select installed files and folders on the phone, single or batch, save their original bytes or one verified ZIP backup, create real folders and playlist folders, and move files and folders within and between the board's storage and the card; new board commands for folders, moves, jobs and readback, approved by the owner in advance on 2026-11-06.
- **The Upload button says why it is disabled**, seed 75: the Upload screen names the lock that disables `Upload to the installation` beside it; the destination line blames the card only after a reply said it is absent; a failed request keeps the last capacity and moves the form nowhere; Internal is never disabled for the card. App only, no new command.
- **The preview of an upload, made on the phone as it starts**, seed 79: planned; the app starts the preview of the bytes it sends with the upload, writes it to the phone's own catalog only on success, and keeps the upload's place (target, storage, name) so the row shows it at once, on a storage without a catalog too; ready-made files of any size are previewed through a DEFLATE stream with bounded memory. Phone only, no command or firmware change.
- **Ready-made animations uploaded as a batch**, seed 80: planned; the Upload screen's chooser takes several `.odrg`/`.odrgx` files, each checked as a single file and named as a converted file, and one press sends them one after another to one destination while the operator uses the app, a line on every screen showing the run; failures are marked and skipped, a lost link or a hidden app waited out, `Stop` and `Try the failed again`; built after pull request #48, a run seed 73 can feed. App only, no new command.
- **The upload check at full speed**, seed 81: implemented in open PR #54; after the last byte the core checks the whole file at every refresh, in step or late, within a budget of 256 to 2,048 bytes of body a refresh, each step charged by its work and the refreshes after a larger record resting for at most 3,840 of it; the budget is set once a second by the refresh rate, so a board at 22 or more stays at 20 or more; verdicts unchanged. The app says `Checking the animation on the installation: m:ss` until `upload end` answers; odrigctl waits 10,800 s. No new command or reply.
- **The app over the board's USB serial port**, seed 82: planned; a switch on the Target screen between Wi-Fi and USB serial, one `Connect over Wi-Fi` control in place of `Use` and `Board`, and every command line of the app sent over the board's USB serial port with the same replies, the port opened without a reset; APK only, no command, firmware, wiring or power change.
- **Display tests whenever play, and a kept mapping lock**, seeds 83 and 84: planned; seed 83 (core only) stops answering the diagonal and snake tests `busy` while the board reads its animations after a start or while an upload is open, the open upload going on to its end, and `mapping set` no longer waits for that reading; seed 84 (app only) keeps `Lock mapping edits` on the phone, one value for every link, target and board, changed only by the operator's confirmed press, never by leaving Settings, another app, a lost reply, a reconnection or a restart.

The state of every seed is in the `state.json` of its folder.

## The owner's workflow

The owner plans and runs the work with workflow skills for coding agents: seed to spec,
enqueue, implement, a task runner and notify. They live outside this repository. You do
not need them to make animations or to contribute: the working rules describe everything they produce.
