# The agent folder

This folder is where a newcomer starts, a person or a coding agent. It holds the pages that
explain the project to somebody who has just cloned it. The documents that define the
project are in `docs/`.

## What the project is

odrig is the LED animation system of an installation for Midburn. A small board, an
ESP32-S3, drives a canvas of 60 x 60 LEDs and plays animations that are stored on it. The
repository holds everything between a video or an idea and what the LEDs show:

- the **converter**, `converter/`: JavaScript, run with Node.js. It turns a video or a GIF
  into a source that git tracks, a source into the file that is played, and a list of
  animations into a show;
- the **reference converter**, `odrig/`: Python. It was the converter before and does the
  same work. It is kept so that tests can compare the converter with it, and it holds the
  generators, the programs that write animations. Nobody converts with it any more;
- the **core**, `core/`: C++. It is the player, the one piece of code that runs both on the
  board and on a computer;
- the **emulator**, `emulator/`: Python, on macOS today. It runs the core on a computer and
  draws every LED in a web page, so a show can be tried without the board;
- the **command tool**, `odrigctl/`: Python. It sends commands, such as play or
  brightness, to the emulator or to the board;
- the **firmware tool**, `firmware/`: Python. It builds the program for the board, puts
  it there and installs a show.

Only the firmware tool needs the board, and the board stays with the first computer. Most
work, and all work on animations, needs none.

## Read in this order

1. [vocabulary.md](vocabulary.md): what the project's words mean. Everything else uses
   them without explaining them.
2. [working-rules.md](working-rules.md): the rules that bind every change, and how
   several contributors work at once.
3. [getting-started.md](getting-started.md): from a fresh clone to the demo show playing
   in the emulator, and what works on Windows.
4. [animation-guide.md](animation-guide.md): how to make an animation and try it without
   the board.

After these, read the documents in `docs/` that your task needs.
[AGENTS.md](../AGENTS.md#then-read-by-task) lists them by task.

## What each file here is for

| File | What it is for |
|---|---|
| `agent/README.md` | This page: what the project is, what to read and in which order. |
| `agent/vocabulary.md` | The meaning of the project's words, each in a few sentences. |
| `agent/working-rules.md` | How work is planned, recorded, committed and merged; what needs the owner; the rules for anyone who has a board. |
| `agent/getting-started.md` | What a computer needs, the setup, the test suites, and the demo show in the emulator. |
| `agent/animation-guide.md` | Making an animation, by a generator or by an import, and checking it in the emulator. |

`AGENTS.md` and `CLAUDE.md` belong with these pages. They stay at the top of the
repository because the tools of coding agents look for them there. `AGENTS.md` holds the
rules in short and the table from tasks to documents, and `CLAUDE.md` points to it.

## Where everything else is

- `docs/`: the documents that define the project. [decisions.md](../docs/decisions.md)
  says what has been decided, and the others specify the formats, the mapping, the show,
  the commands and each tool.
- `project-seeds/`: the planned work, one folder for each seed.
- `docs/specs/`: the specs made from the seeds, with their task lists.
- `tests/`: the tests, one folder for each suite. The converter's own suite is in
  `converter/tests/`.
