# Requirements: Onboarding for agents and contributors (seed 10)

Source seed: `project-seeds/10-p0-onboarding-for-agents-and-contributors/seed.md`. It
depends on seeds 01 to 05, whose tools and documents the new files describe. Seeds 01 and
02 are completed; seeds 03, 04 and 05 are implemented up to what needs a person. These
requirements rely on the repository as it is and change no tool.

`docs/decisions.md` and the other documents under `docs/` define what the new files
describe. Where they and the seed leave a point open, or contradict each other, the answer
used here is recorded in `docs/drifts.md` under "Seed 10".

Terms:

- **the pages**: the six files this seed adds: `AGENTS.md` and `CLAUDE.md` at the top of
  the repository, and `docs/vocabulary.md`, `docs/working-rules.md`,
  `docs/getting-started.md` and `docs/animation-guide.md`.
- **the entry file**: `AGENTS.md`.
- **the governing documents**: `README.md` and every file under `docs/` that is not one of
  the pages and not under `docs/specs/`.
- **a newcomer**: a person or a coding agent who has a fresh clone of the repository on
  another computer and knows nothing else about the project.
- **the owner**: the person who owns the installation and decides what the project does.
- **a fresh copy**: a clone of the repository in a temporary folder, holding what a clone
  would hold if the tracked files of the working tree were committed as they are.
- **the quick suite**: the tests in `tests/onboarding/`, which need no board, no network
  and nothing installed.
- **the walk-through**: the tests in `tests/walkthrough/`, which follow two of the pages in
  a fresh copy and install the converter's three libraries there from PyPI.
- **the four suites**: the converter's, the core's, the emulator's and the firmware tool's
  suite that needs no board, as `docs/converter.md`, `docs/core.md`, `docs/emulator.md` and
  `docs/firmware.md` give their commands.
- **a command block**: a fenced code block of a page marked `sh`, which holds commands as a
  reader types them, one to a line, a line that ends in a backslash going on in the next.

## Requirement 1: One entry file for every coding agent

**User Story:** As a coding agent that has just been pointed at a fresh clone, I want one
file that tells me what this is, what to read for my task and what I may not do, so that I
can start without reading a dozen documents and without breaking a rule nobody told me.

### Acceptance Criteria

1. `AGENTS.md` SHALL exist at the top of the repository and SHALL have at most 150 lines.
2. It SHALL say in its first section what the project is and name its parts: the
   converter, the core, the emulator, the command tool and the firmware tool.
3. It SHALL give a reading order: what every agent reads first, and for each kind of task
   which documents to read next. Every file `docs/*.md` SHALL be linked from it, and it
   SHALL say where the seeds, the specs, the tests and the settled questions are.
4. It SHALL state the rules that bind every change, each in one or two lines, and point to
   `docs/working-rules.md` for the full text.
5. It SHALL list what must never be touched: the folders `esp32-backup/` and
   `firmware/wled-16.0.1/`, which exist untracked on the first computer only; untracked
   files that the agent did not make; and the board, except through the repository's tools
   and under the board's safety rules.
6. It SHALL say, in one section, what is being built next and is not there yet: the
   JavaScript converter, the content commands, the board's Wi-Fi name and password, and
   the operators' app. No other page SHALL describe them.
7. It SHALL say that the owner's workflow skills live outside the repository, what they
   are, and that they are not needed to make animations or to contribute.
8. `CLAUDE.md` SHALL exist at the top of the repository, SHALL point to `AGENTS.md`, and
   SHALL state no rule and no fact of its own.

## Requirement 2: A vocabulary of the project's words

**User Story:** As a newcomer, I want the project's words defined in one place as they are
used now, so that I read the other documents the way their authors meant them.

### Acceptance Criteria

1. `docs/vocabulary.md` SHALL define each of these words: canvas, leg, strip, snake,
   mapping, show, item, cycle, installed file set, JSON frames, ODRG, core, host, emulator,
   firmware, command, drift, seed, spec, bench build and target.
2. Each definition SHALL be one to four sentences in plain words, SHALL use no word of the
   project that the page defines only further down, and SHALL point to the governing
   document that specifies the thing, where there is one.
3. The page SHALL define the further words a newcomer meets on the first day: animation,
   frame, refresh, pin, source, generator, converter, command tool, board, task and owner.
4. The definition of the bench build SHALL say what its mapping file describes and what is
   wired to the board at present, and the definition of the target SHALL say that its legs
   are not wired.

## Requirement 3: The working rules, in this project's own words

**User Story:** As a contributor, I want every rule that binds my changes written in this
repository, so that I can follow rules that until now existed only as references to another
project and as habits.

### Acceptance Criteria

1. `docs/working-rules.md` SHALL state how work is planned and recorded: a seed is a folder
   with `seed.md` and `state.json`, and the states a seed can have; a spec is the three
   files `requirements.md`, `design.md` and `tasks.md`; one seed is one commit; one task is
   one commit that also ticks the task's checkbox; and a question met on the way is
   answered without asking the owner and recorded in `docs/drifts.md`, with the three parts
   an entry has.
2. It SHALL state that the scope of a seed is fixed once its tasks are being implemented,
   that a gap found then becomes a new seed, and that a commitment for later reaches the
   owner in words and is not left only in a file.
3. It SHALL state how commits are made: named paths only, with the four forms that are
   never used; the list of files read after each commit; a test for a fault shown failing
   before the fault is mended, with the failure recorded; no comment in code or tests about
   seeds, tasks, dates or earlier versions; and test commands that select a suite by
   discovery and never list test files.
4. It SHALL state what needs the owner: every addition to the command list, anything that
   changes a decision in `docs/decisions.md`, and anything about hardware or power.
5. It SHALL state the board's safety rules for anyone who has a board: the two untracked
   folders that are never changed or committed; that only the repository's tools talk to
   the board, because of the way they open its serial port; one program on the board at a
   time; the brightness limit of 40 while one strip is fed from the board's 3.3 V pin; that
   the whole flash is never erased and no fuse is written; that the firmware is built only
   as the tool builds it; and that a person cuts the power of a board that stops answering.
6. It SHALL state the frame-rate rule: any refresh rate from 20 to 50 a second is
   acceptable for any content, only a rate outside that range is a fault, and no work is
   proposed to raise a rate inside it.
7. It SHALL state how several contributors work at once: each on a branch of their own, in
   a checkout of their own; the branch is brought up to date with `master` before it is
   merged; it is merged only with every suite that needs no board passing; and
   `docs/drifts.md` and the change log of `docs/decisions.md` are added to at the end only,
   with both contributors' additions kept when two branches meet.
8. It SHALL say what the owner's workflow skills are and that they are not part of the
   repository.

## Requirement 4: From a fresh clone to a running emulator

**User Story:** As a newcomer, I want one page that takes me from a fresh clone to the demo
show playing in the emulator, so that I know my computer is ready before I change
anything.

### Acceptance Criteria

1. `docs/getting-started.md` SHALL list what has to be on the computer: macOS, Apple's
   command-line developer tools, git, and Python 3.10 or later as `python3`. It SHALL say
   that the core's build, the emulator, the command tool and the firmware tool run on macOS
   only at present, and that the converter is written to run on Windows and Linux too and
   has been run on macOS only.
2. It SHALL give the commands that set up a clone: the virtual environment, the three
   libraries of `requirements.txt`, and the core's shared library.
3. It SHALL give, for every folder of `tests/` that holds a suite, the command that runs
   it, what it needs and roughly how long it takes, and SHALL say which suites need the
   board. The suites it gives as the ones to run after setup SHALL need no board and
   nothing beyond what the setup installed.
4. It SHALL give the commands that pack the demo show, start the emulator on it, send it a
   command through its serial port and over HTTP, and stop it, and SHALL say what the page
   in the browser shows.
5. It SHALL give a way to check a packed show without a screen: a run in record mode with a
   script that asks for the status, and what the reply must say.
6. WHEN the command blocks under the headings the walk-through follows are run in order,
   as they are written, from the root of a fresh copy on a Mac that has what criterion 1
   lists and a network connection, THEN each command SHALL exit with status 0.

## Requirement 5: Making an animation and trying it without the board

**User Story:** As a contributor who prepares animations on another computer, I want one
guide from a video file or an idea to an animation playing in the emulator, so that I can
make content that will work on the board without having one.

### Acceptance Criteria

1. `docs/animation-guide.md` SHALL describe the two ways to make an animation: a generator
   in code, with a complete small generator as an example and where it is saved, and an
   import of a video or a GIF, with the three fits and how to take a part of a file.
2. It SHALL give the commands that check a source, pack it into a show with a mapping
   file, start the emulator on it and check it in record mode, and SHALL say what to look
   for on the emulator's page and that the emulator does not show how fast the board plays.
3. It SHALL say where sources, shows, mapping files and build products go, and what is
   committed and what is not.
4. It SHALL say how large sources get, with measured figures for the tracked sources, for
   the demo show's sources, for a dense clip and for an imported GIF and an imported video
   on the 60 x 60 canvas, and SHALL give the limit a hosting service puts on one file.
5. It SHALL say which form of a dense animation plays best on the board, compressed or
   uncompressed, with the rates `docs/firmware.md` records, and how to pack that form.
6. The example generator, run for each tracked mapping file, SHALL write a valid JSON
   frames file with the canvas of that mapping file.
7. WHEN the command blocks under the headings the walk-through follows are run in order
   after those of Requirement 4, with a small GIF at the path the guide names, THEN each
   command SHALL exit with status 0 and the packed folder SHALL hold the imported
   animation.

## Requirement 6: The README and the decisions

**User Story:** As a person who opens the repository, I want the README to tell me what to
read and in what order, and as a contributor I want the decisions to hold the rule that
applies now that several of us work at once.

### Acceptance Criteria

1. `README.md` SHALL give the reading order for people: getting started, the vocabulary,
   the animation guide and the working rules, before the reference documents. It SHALL
   point coding agents to `AGENTS.md`.
2. Everything the suites of seeds 01 to 05 check in `README.md` SHALL still hold.
3. `docs/decisions.md` SHALL state the rule for several contributors of Requirement 3
   criterion 7 in place of the rule that all work is committed directly on `master`, and
   SHALL say that the repository carries the vocabulary and the working rules.
4. The change log of `docs/decisions.md` SHALL have one new entry, at its end, for this
   change. No other entry of the change log SHALL be changed.

## Requirement 7: The pages are true, short and name nothing private

**User Story:** As the owner, I want the pages to stay true as the repository changes, so
that the first thing a new agent reads never sends it the wrong way.

### Acceptance Criteria

1. Every path a page names SHALL exist in a fresh clone, except a path the page gives as
   something to be made, a path under `build/` or `.venv/`, and the two folders of
   Requirement 1 criterion 5, which SHALL NOT be tracked.
2. Every link of a page to a file of the repository SHALL lead to a tracked file, and a
   link to a heading SHALL lead to a heading that file has.
3. Every command a page gives SHALL be understood by the tool it names: a subcommand and
   options the tool's own command line accepts, a target the core's makefile has, a folder
   of tests that exists.
4. Each page other than the entry file SHALL have at most 200 lines.
5. No page SHALL name a person, hold an e-mail address, hold a path into somebody's home
   folder, hold the hardware address of a board, or hold the password of the board's
   network.
6. No line of prose of a page SHALL be a line of a governing document. The pages point to
   the governing documents for everything those specify.
7. A page SHALL describe as present only what the repository holds. What is planned SHALL
   be named in the one section of Requirement 1 criterion 6.

## Requirement 8: Tests, and the seed's state

**User Story:** As a maintainer, I want a test that follows the pages and a test that
checks what they name, so that a page that stops being true fails a test.

### Acceptance Criteria

1. `python3 -m unittest discover -s tests/onboarding -t .` SHALL run the quick suite: every
   `test_*.py` file of that folder, found by discovery. It SHALL check Requirement 1
   criteria 1, 3, 6 and 8, Requirement 2 criterion 1, Requirement 5 criterion 6,
   Requirement 6 criteria 1, 3 and 4, and Requirement 7 criteria 1 to 6, and SHALL finish
   within a minute.
2. `python3 -m unittest discover -s tests/walkthrough -t .` SHALL run the walk-through: it
   makes a fresh copy, runs the command blocks of `docs/getting-started.md` and then those
   of `docs/animation-guide.md` under the headings it follows, and checks what they left:
   the packed demo show, the reply of its run in record mode, the imported source and the
   show packed from it.
3. The walk-through SHALL be a suite of its own, so that no other test command starts it.
   Every heading of the two pages that has a command block SHALL be either followed or
   named in the walk-through with the reason it is not followed.
4. The walk-through SHALL leave nothing behind: no file outside its temporary folder, and
   no running process.
5. WHEN a command of a page fails in the walk-through THEN the failure SHALL name the page,
   the heading and the command, and show what the command printed.
6. The four suites SHALL pass with the pages in place.
7. The first task SHALL set `"state": "in_progress"` and the last task
   `"state": "completed"` in the seed's `state.json`.
