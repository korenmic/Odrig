# Design: Onboarding for agents and contributors (seed 10)

## Overview

Six pages are added, two documents are changed and two suites of tests are added. No tool
and no governing document other than `README.md` and `docs/decisions.md` is changed.

- `AGENTS.md`, the entry file, and `CLAUDE.md`, which points to it.
- `docs/vocabulary.md`, `docs/working-rules.md`, `docs/getting-started.md` and
  `docs/animation-guide.md`.
- `README.md` gains the reading order for people and a pointer for agents.
  `docs/decisions.md` gets the rule for several contributors.
- `tests/onboarding/`, the quick suite, checks what the pages name. `tests/walkthrough/`
  follows the getting-started page and the animation guide in a fresh copy.

The pages are written for a reader who knows nothing of the project: plain words, whole
sentences, a word defined before it is used, commands that can be copied. They state what
is so now and tell no story of how it came to be. Decisions taken where the seed left a
point open are listed in `docs/drifts.md` under "Seed 10".

## What this design relies on

The repository as it is. A task that finds one of these different follows what it finds and
records the difference in `docs/drifts.md`.

| From | Used here |
|---|---|
| `odrig/cli.py` | `build_parser()` and `SUBCOMMANDS`, to check a converter command a page gives. |
| `odrig/generators/__init__.py` | `run` and `picture`, which the example generator of the guide uses. |
| `odrig/jsonframes.py`, `odrig/mapping.py` | `read`, to check what the example generator writes. |
| `emulator/app.py` | `parse(argv)`, to check an emulator command. |
| `odrigctl/cli.py` | `parser()`, to check a command of the command tool. |
| `firmware/fwtool/cli.py` | `parser()`, to check a command of the firmware tool. It needs only the standard library. |
| `core/Makefile` | The targets `all`, `test`, `bench`, `shared` and `clean`. |
| `requirements.txt` | The three pinned libraries the walk-through installs in its fresh copy. |
| `shows/demo-20/show.json`, `mapping/legs-20.json` | The demo show the getting-started page packs. |
| The record mode of the emulator | A run without a page and without waiting, whose script prints the reply to `status`. |

## Repository layout

```
AGENTS.md                          the entry file, at most 150 lines
CLAUDE.md                          points to AGENTS.md
docs/vocabulary.md
docs/working-rules.md
docs/getting-started.md
docs/animation-guide.md
tests/onboarding/__init__.py
tests/onboarding/support.py        the pages, their sections, links, code blocks and commands
tests/onboarding/test_pages.py     what holds for every page
tests/onboarding/test_vocabulary.py
tests/onboarding/test_rules.py     the working rules and docs/decisions.md
tests/onboarding/test_start.py     the getting-started page
tests/onboarding/test_guide.py     the animation guide
tests/onboarding/test_entry.py     AGENTS.md, CLAUDE.md and README.md
tests/walkthrough/__init__.py
tests/walkthrough/support.py       the fresh copy, and running a command in it
tests/walkthrough/make_gif.py      writes the small GIF the guide's import reads
tests/walkthrough/test_fresh_copy.py
```

## Facts the pages state, and where each comes from

The pages repeat a fact only where a newcomer needs it on the first day, and point to the
document that holds it. These are the facts and their sources; a task checks each against
its source when it writes the page.

| Fact | Source |
|---|---|
| The canvas, the leg, the two kinds of leg, the pins of the twenty legs | `docs/decisions.md`, "Canvas and coordinates"; `docs/mapping.md` |
| The bench build is two row legs, 60 x 6, `mapping/legs-2.json`; the target is twenty column legs, 60 x 60, `mapping/legs-20.json`, not wired | The same; `docs/mapping.md`, "What is confirmed" |
| One strip of 60 LEDs is wired at present, on pin 1, fed from the board's 3.3 V pin; a show installed then has a brightness of 40 or less | `docs/firmware.md`, "install-show" and "test-board" |
| The serial port is opened with RTS lowered before DTR, which does not reset the board | `docs/emulator.md`, "The command tool"; `docs/firmware.md`, "Verified on the board" |
| The regions of the flash the tool writes; the whole flash never erased; no fuse written; the factory backup | `docs/firmware.md`, "The regions of the flash" and "Rolling back" |
| A whole firmware built at another optimisation level stopped the board answering; a person has to cut its power | `docs/firmware.md`, "Verified on the board" |
| Any refresh rate from 20 to 50 a second is accepted, for any content | `docs/decisions.md`, "Firmware" |
| On the board the demo show is refreshed 50 times a second; a dense 60 x 60 clip 36 to 42 times compressed and 45 to 47 uncompressed; the uncompressed file is 5 percent larger | `docs/firmware.md`, "Verified on the board" |
| Storage holds 65 to 74 seconds of a dense 60 x 60 clip compressed and 61 to 70 uncompressed | `docs/format.md`, "Measured sizes" |
| The five commands, and that every addition needs the owner | `docs/commands.md`; `docs/decisions.md`, "Commands" |
| The tracked sources are 461,337 and 262,637 bytes | The files `animations/hello.json` and `animations/dvd.json` |
| For the 60 x 60 canvas: Hello world is 2,939,938 bytes of JSON, DVD bounce 1,258,994, the dense clip of 10 seconds 16,405,608 | Measured for this spec with the generators |
| A GIF of 5.1 seconds, imported for the 60 x 60 canvas with the default fit, gave 255 frames and 3,786,708 bytes of JSON | Measured for this spec |
| A video of 5 seconds in which every pixel changes at every frame gave 4,161,666 bytes at 25 frames a second and 4,994,025 at 30 | Measured for this spec, with a video made for the measurement |
| Large hosting services refuse a single file above 100 MB and warn above 50 MB | Given with the task |
| The emulator and the firmware tool run on macOS only; the converter has no code for one system and has been run on macOS only | `docs/emulator.md`; `docs/firmware.md`; `docs/converter.md`, "Setup" |
| What is coming: seeds 06 to 09 | `project-seeds/` |

## The pages

A page is Markdown, wrapped as the other documents are. A fenced block marked `sh` holds
commands exactly as a reader types them from the repository root. A block marked `text`
holds what a command prints or a placeholder a reader fills in, `json` a file's content and
`python` a module. Only `sh` blocks are run by the walk-through.

Commands name the Python of the virtual environment as `.venv/bin/python`. The
getting-started page says once that the other documents write `python` for it and what it
is on Windows. `make -C core test` and `python3 firmware/fw.py` are given as their own
documents give them.

### `AGENTS.md`

Headings, in this order: `What this is`; `Read first`; `Then read, by task`, a table from
the kind of task to the documents; `Rules you may not break`; `Never touch`; `What needs
the owner`; `Commands you will use`; `What is coming`; `The owner's workflow`. Each rule is
one or two lines and the section ends with the pointer to `docs/working-rules.md`.

### `CLAUDE.md`

A heading, one sentence that says the entry file for every coding agent is `AGENTS.md`,
and the line `@AGENTS.md`, which makes Claude Code load that file with this one.

### `docs/vocabulary.md`

Four groups, each a list of entries `**word**: definition`, ordered so that a definition
uses only words defined above it: `The installation` (board, pin, canvas, strip, leg,
snake, mapping, bench build, target); `What is played` (animation, frame, refresh, source,
JSON frames, ODRG, generator, show, item, cycle, installed file set, command); `The
programs` (converter, core, host, emulator, firmware, command tool); `How the work is
organised` (owner, seed, spec, task, drift).

### `docs/working-rules.md`

Headings: `How work is planned and recorded`; `How commits are made`; `What needs the
owner`; `If you have a board`; `The frame rate`; `Several contributors at once`; `The
owner's workflow skills`. The rules adopted from the other project are written here in
this project's words: nothing is copied, and that project is not named.

### `docs/getting-started.md`

| Heading | Content | Walk-through |
|---|---|---|
| `What you need` | Requirement 4 criterion 1. | no command block |
| `Set up` | Clone, as a `text` block with a placeholder; then the environment, the libraries and the shared library. | followed |
| `Run the tests` | The three suites that need what `Set up` installed, and the quick suite. A table of every suite. | followed |
| `Suites that need more` | The firmware tool's suite, which fetches its tools on its first run; the walk-through; the two suites that need the board. | not followed |
| `Pack the demo show` | The two generators and `pack`. | followed |
| `Run it in the emulator` | Start, the two lines it prints, the page, three commands from a second terminal, stop. | not followed |
| `Check it without a screen` | A script with one `status` line and a run in record mode. | followed |
| `What to read next` | Pointers. | no command block |

### `docs/animation-guide.md`

| Heading | Content | Walk-through |
|---|---|---|
| `Two ways to make an animation` | What a source is, and the two ways. | no command block |
| `A generator` | The example generator as a `python` block, where it is saved and how its test is added; a generator run into `build/try/sources/`. | followed |
| `An import` | `import` of `build/try/clip.gif` for the target canvas, the fits, a part of a file. | followed |
| `Check a source` | `check` and its lines. | followed |
| `Pack it into a show` | A show file written with `printf`, and `pack`. | followed |
| `Look at it in the emulator` | Start, and what to look for. | not followed |
| `Check it without a screen` | Record mode with a script. | followed |
| `Where things go` | Sources, generators, shows, mapping files, build products; what is committed. | no command block |
| `How large sources get` | The figures and the hosting limit. | no command block |
| `Dense animations on the board` | The rates, the form to pack, and how. | no command block |

## The quick suite

`python3 -m unittest discover -s tests/onboarding -t .` It needs Python alone.

`support.py` knows the pages and reads them: the sections of a page by heading; the fenced
blocks with their mark and the heading they stand under; the commands of the `sh` blocks,
with a line that ends in a backslash joined to the next; the code spans of the prose; and
the links.

`test_pages.py`, for every page:

- **Paths.** A code span or a word of a command is taken for a path when it has a `/` or
  ends as a file of the repository does. It must exist; a capital word in it, such as
  `NAME`, stands for any name. Not looked for: a path under `build/`, `.venv/`, `.codex/`
  or `/dev/`, and a bare file name that a page gives as the name of an installed or built
  file. `esp32-backup/` and `firmware/wled-16.0.1/` must be named by the working rules
  and must not be tracked.
- **Links.** A link that is not `http` leads to a tracked file, and its `#part` to a
  heading of that file.
- **Commands.** Each command of a `sh` block, and each code span that begins like a
  command, is given to the parser of the tool it names, or checked against the makefile's
  targets or the folders of `tests/`. A program the test does not know fails it. No `sh`
  block holds `git add -A`, `git add .`, `git add -u` or `git commit -a`.
- **Length.** `AGENTS.md` at most 150 lines, every other page at most 200.
- **Nothing private.** No `/Users/`, `/home/`, `~/` or `C:\Users`, no e-mail address, no
  hardware address, no numbered `usbmodem` device.
- **Nothing copied.** No line of prose of 60 characters or more is a line of a governing
  document.
- **What is coming, once.** The words that name seeds 06 to 09 stand in `AGENTS.md`, under
  `What is coming`, and in no other page.

`test_vocabulary.py`: the words of Requirement 2 each have an entry, and an entry is not
empty. `test_rules.py`: the seven headings; the four forms of staging that are never used;
`20 to 50`; the brightness of 40; in `docs/decisions.md` the rule for several contributors
stands above the change log, the old rule does not, and the last entry of the change log
is the new one. `test_start.py`: the headings of the table above; every folder of `tests/`
that holds a `test_*.py` file is named with a command that runs it. `test_guide.py`: the
headings; the example generator, run in the test for both mapping files; the sizes of the
two tracked sources and of the demo show's two sources as the files and the generators
give them; the two rates as `docs/firmware.md` has them. `test_entry.py`: Requirement 1
criteria 1, 3, 6 and 8 and Requirement 6 criterion 1.

## The walk-through

`python3 -m unittest discover -s tests/walkthrough -t .` It needs what the getting-started
page lists and a network connection, for pip.

**The fresh copy.** `git clone` of the repository into a temporary folder. Then every file
git tracks in the working tree is compared with the copy, and one that differs, is new or
is gone is brought over and committed in the copy, with an identity made for the test. With
a clean working tree the copy is a plain clone. So a change to a page is followed before it
is committed, once its new files are staged, and nothing untracked or ignored reaches the
copy.

**Following.** The test knows, for each of the two pages, the headings it follows and the
headings it does not, each of those with its reason. A heading with a command block that
is in neither list fails the test. The commands under the followed headings are run in the
order of the page, each by `/bin/sh -c` from the root of the copy, with the caller's
environment less `VIRTUAL_ENV` and `PYTHONPATH`. A command that does not end with status 0
fails the test with the page, the heading, the command and what it printed. Before the
guide's import the test writes a GIF of ten frames to the path the guide names, with
`make_gif.py` run by the copy's own Python, which has Pillow by then.

**Not followed, and why.**

- `Run it in the emulator`, `Look at it in the emulator`: they need a second terminal and
  somebody to look. The quick suite gives their commands to the tools' parsers, and the
  emulator's own suite, which the walk-through runs, covers the program.
- `Suites that need more`: the firmware tool's suite fetches WLED's source and its build
  tools on its first run, the walk-through would start itself, and two suites need the
  board.

**What it checks afterwards.** `build/demo-20/show` holds exactly `mapping.json`,
`show.json`, `hello.odrg` and `dvd.odrg`. The record run of the demo show printed a reply
with `"playing":3` and `"error":null`. `check` printed `canvas: 60x60` for the imported
source. `build/try/show` holds `clip.odrg`, and its record run printed `"error":null`.

**Kept out of the quick run.** The walk-through is a folder of its own, so no command that
names another folder of `tests/` starts it. It takes about five minutes: the emulator's
suite alone takes two.

**Leaves nothing.** The copy, its environment and everything it builds are in one
temporary folder that is removed at the end. Each command runs in a process group of its
own with a time limit; when the limit passes, that group is ended by the number the test
recorded when it started the command.

## `README.md` and `docs/decisions.md`

`README.md` gets a section `Start here` after its first paragraph: the four pages in
reading order for people, one line each, and the sentence that coding agents start at
`AGENTS.md`. The rest stays; the suites of seeds 01 to 05 check phrases of it and count
its links to `docs/emulator.md`, so the new section links none of the reference documents.

In `docs/decisions.md`, under "Scope and process", the entry that all work is committed
directly on `master` becomes the rule of Requirement 3 criterion 7, with a pointer to
`docs/working-rules.md`, and the entry that the repository will carry a vocabulary and
agent policies says that it carries them and where. One entry is added at the end of the
change log.

## Testing strategy

| What | Checked by |
|---|---|
| A page names something that does not exist, links nowhere, or gives a command its tool refuses | the quick suite |
| A page's commands no longer work from a fresh clone | the walk-through |
| A word the seed lists has no definition; a rule's section is gone | the quick suite |
| The pages are plain, complete and in the right order for a newcomer | the writer, by reading each page once as a newcomer after writing it |
| The four suites still pass | each task, as the tasks say |

## Risks

- **The network.** The walk-through installs three libraries from PyPI. Without a
  connection it fails at that command and says so. It is not skipped: a page that cannot
  be followed is what it reports.
- **Time.** The walk-through runs three suites and takes minutes. It is run by the tasks
  that change the two pages it follows and by the last task, not by every task.
- **A page that is right today.** A page says what the repository holds. When a seed
  changes a tool, its tasks change the page; the quick suite fails where a command or a
  path is gone, and says which.
