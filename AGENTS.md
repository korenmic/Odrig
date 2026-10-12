# AGENTS.md

The entry file for every coding agent that works in this repository. Read all of it before
you do anything else.

## What this is

odrig is the LED animation system of an art installation. A small board, an ESP32-S3,
drives a canvas of 60 x 60 LEDs and plays animations that are stored on it. This repository
holds everything between a video or an idea and what the LEDs show:

- the **converter**, `odrig/`: Python. It turns a video or a GIF into a source that git
  tracks, a source into the file that is played, and a list of animations into a show;
- the **core**, `core/`: C++. It is the player, the one piece of code that runs both on the
  board and on a computer;
- the **emulator**, `emulator/`: Python, on macOS. It runs the core on a computer and
  draws every LED in a web page, so a show can be tried without the board;
- the **command tool**, `odrigctl/`: Python. It sends commands, such as play or
  brightness, to the emulator or to the board;
- the **firmware tool**, `firmware/`: Python. It builds the program for the board, puts
  it there and installs a show.

Only the firmware tool needs the board. Most work, and all work on animations, needs none.

## Read first

1. [docs/vocabulary.md](docs/vocabulary.md): what the project's words mean. The other
   documents use them without explaining them.
2. [docs/working-rules.md](docs/working-rules.md): the rules below, in full.
3. [docs/getting-started.md](docs/getting-started.md), when this clone is not set up yet:
   what the computer needs, the setup, the tests, and the demo show in the emulator.

## Then read, by task

| Your task | Read |
|---|---|
| Make or change an animation or a show | [docs/animation-guide.md](docs/animation-guide.md), then [docs/format.md](docs/format.md) and [docs/show.md](docs/show.md) |
| Change the converter | [docs/converter.md](docs/converter.md), [docs/format.md](docs/format.md), [docs/reasons.md](docs/reasons.md) |
| Change the core | [docs/core.md](docs/core.md), [docs/format.md](docs/format.md), [docs/show.md](docs/show.md), [docs/commands.md](docs/commands.md) |
| Change the emulator or the command tool | [docs/emulator.md](docs/emulator.md), [docs/commands.md](docs/commands.md) |
| Change how the LEDs are laid out | [docs/mapping.md](docs/mapping.md) |
| Change the firmware, or do anything with the board | [docs/firmware.md](docs/firmware.md), [docs/wifi.md](docs/wifi.md), and "If you have a board" in the working rules |
| Find out what was decided, and why | [docs/decisions.md](docs/decisions.md), then [docs/drifts.md](docs/drifts.md) |

`docs/drifts.md` is long: it holds every question that was settled on the way. Search it
for your subject; do not read it through. Planned work is in `project-seeds/`, one folder
for each seed, and the specs made from the seeds are in `docs/specs/`. The tests are in
`tests/`, one folder for each suite.

## Rules you may not break

1. **Your own branch, your own checkout.** Never commit on `master`, and never work in a
   checkout that another contributor uses. Before a commit, `git branch --show-current`
   names your branch.
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
11. **Any refresh rate from 20 to 50 a second on the board is acceptable.** Do no work to
    raise a rate inside that range.

[docs/working-rules.md](docs/working-rules.md) has each of these with its reason.

## Never touch

- `esp32-backup/` and `firmware/wled-16.0.1/`. They exist, untracked, on the first
  computer only, and they are what brings a board back. Never change, move, delete or
  commit them.
- An untracked file that you did not make. The checkout on the first computer holds some.
- The board, except through `firmware/fw.py` and `odrigctl`, and then under the rules "If
  you have a board": a brightness of 40 or less, one program at a time, the flash never
  erased, and the firmware built only as the tool builds it.

What you make under `build/` and `.venv/` is yours to make and to remove, and never to
commit.

## What needs the owner

Do not decide these, and do not work on a guess. Ask in words and wait.

- Every addition to the command list.
- Anything that changes a decision in `docs/decisions.md`.
- Anything about hardware or power.
- A check that only a person can make: what the LEDs show, or what a phone gets.

## Commands you will use

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
make -C core shared
.venv/bin/python -m unittest discover -s tests/converter -t .
make -C core test
.venv/bin/python -m unittest discover -s tests/emulator -t .
.venv/bin/python -m unittest discover -s tests/onboarding -t .
```

The first three set up a clone, once, on a Mac. The other four are the suites that need no
board. All are run from the repository root. You cannot look at the emulator's page: check
a show in the emulator's record mode, as "Check it without a screen" in
[docs/getting-started.md](docs/getting-started.md) shows.

## What is coming

These are planned as seeds and are not in the repository yet. Do not describe them as
present, and do not build on them.

- **A converter in JavaScript**, seed 06. It is to become the converter people use, from
  the command line and inside the apps. The Python tool stays as the reference that tests
  compare it with. Today the Python tool is the converter.
- **Four more commands**, seed 07: report the free storage, list what is installed,
  remove an animation, and upload one.
- **The board's Wi-Fi name and password**, seed 08, set from a tracked settings file.
  Today the board's network has the defaults of WLED; see [docs/wifi.md](docs/wifi.md).
- **An app for the operators, for Android**, seed 09. The first notes are in
  [docs/android-app.md](docs/android-app.md).

Seeds 03, 04 and 05 are built and still `in_progress`: they wait for checks on the board
or by a person.

## The owner's workflow

The owner plans and runs the work with workflow skills for coding agents: seed to spec,
enqueue, implement, a task runner and notify. They live outside this repository. You do
not need them to make animations or to contribute: the working rules describe everything
they produce.
