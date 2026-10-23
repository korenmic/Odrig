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
| Change the Python library, a generator or the test vectors | [docs/python-library.md](docs/python-library.md), [docs/format.md](docs/format.md) |
| Change the core | [docs/core.md](docs/core.md), [docs/format.md](docs/format.md), [docs/show.md](docs/show.md), [docs/commands.md](docs/commands.md) |
| Change the emulator or the command tool | [docs/emulator.md](docs/emulator.md), [docs/commands.md](docs/commands.md) |
| Change the operators' app | [docs/android-app.md](docs/android-app.md), [docs/commands.md](docs/commands.md) |
| Change how the LEDs are laid out | [docs/mapping.md](docs/mapping.md) |
| Change the firmware, or do anything with the board | [docs/firmware.md](docs/firmware.md), [docs/firmware-prerequisites.md](docs/firmware-prerequisites.md), [docs/firmware-additions.md](docs/firmware-additions.md), [docs/wifi.md](docs/wifi.md), and "If you have a board" in the working rules |
| Find out what was decided, and why | [docs/decisions.md](docs/decisions.md), then [docs/drifts.md](docs/drifts.md) |

`docs/drifts.md` is long: it holds every question that was settled on the way. Search it
for your subject; do not read it through. Planned work is in `project-seeds/`, one folder
for each seed, and the specs made from the seeds are in `docs/specs/`. The tests are in
`tests/`, one folder for each suite, and the converter's own are in `converter/tests/`;
the getting-started page has the command of each.

## Rules you may not break

1. **Your own branch, your own clone.** Never commit on `master` directly, and never work
   in a checkout that another contributor uses. Before a commit,
   `git branch --show-current` names your branch.
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

The Python library, the core's build, the emulator and the command tool work on Windows 10
and 11, and their suites pass there. That was seed 11,
`project-seeds/11-p0-emulator-and-tools-on-windows/`.

- The core is built there by `python core/build.py shared`, not by `make`.
- Windows has no virtual serial port. The emulator takes command lines on a TCP port, and
  the command tool reaches it with `--tcp` or `--http`.
- The converter's own suite, `npm test --prefix converter`, passes on Windows too. Its
  test in Chrome starts Chrome there without a window, as everywhere.
- The firmware tool and the board stay with the first computer.
- Nothing is installed in the system. A compiler or another program that is fetched is
  unpacked into `tools/`, and a trial goes into `scratch/`. Git ignores both.

[agent/getting-started.md](agent/getting-started.md#on-windows) has the setup and the
commands of Windows.

## What is coming

These are planned as seeds and are not in the repository yet. Do not describe them as
present, and do not build on them.

- **Animations from a USB drive**, seed 20: the board plays the animations of a stick's
  folder `odrig`. The core, the emulator and the app do; the board has read no stick yet.
- **One USB port for a computer or a stick**, seed 21: the chip's own port is a
  computer's when one is plugged in as the board starts; built, not tried on the board.
- **A USB stick through a hub**, seed 22: newer USB software that knows hubs. Today the
  board reads no stick through a hub.
- **A USB log on the serial port**, seed 23: what the board's own USB port sees.
- **A bigger animation space**, seed 24: about 13.5 MB in place of 10.35 MB, by giving
  up firmware updates over Wi-Fi; the tool and the firmware have it, and no board has been
  moved to it yet.
- **A second firmware that does not use WLED**, seed 12, as a fallback for the event.
- **Every suite passes on Windows again**, seed 26: today seven tests of the emulator's
  suite and two of the app's fail on Windows, and the stop of `odrigctl --log` is not
  tested there.
- **The app's count of installed and stick animations**, seed 28: the dashboard will show
  how many animations are in the board's own storage and how many come from a USB stick.
- **Toggle animations in the playlist**, seed 29: persistently exclude installed animations
  through the shared app, emulator controller or serial; keep files and explicit play.
- **App mapping and a diagonal check**, seed 30: save pin-to-snake assignments from the
  shared app and show a diagonal test line for the owner's visual check on the real LEDs.

The state of every seed is in the `state.json` of its folder.

## The owner's workflow

The owner plans and runs the work with workflow skills for coding agents: seed to spec,
enqueue, implement, a task runner and notify. They live outside this repository. You do
not need them to make animations or to contribute: the working rules describe everything
they produce.
