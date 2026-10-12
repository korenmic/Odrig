# odrig

LED animation system for a Midburn installation: an ESP32-S3 board driving a canvas of
addressable LED strips. The target is a canvas of 60 x 60 LEDs on twenty legs, each a data
pin of the board with three upright strips of 60 LEDs; the build on the bench today has two
legs of three flat strips, 60 x 6.

## Start here

Read these four pages first, in this order:

1. [agent/getting-started.md](agent/getting-started.md) takes you from a fresh clone to the
   demo show playing in the emulator on your own computer. It needs no board.
2. [agent/vocabulary.md](agent/vocabulary.md) says what the project's words mean.
3. [agent/animation-guide.md](agent/animation-guide.md) shows how to make an animation and
   try it without the board.
4. [agent/working-rules.md](agent/working-rules.md) has the rules that bind every change.
   Read it before you change anything.

[agent/README.md](agent/README.md) introduces these pages. The rest of this page names
the reference documents. Coding agents start at [AGENTS.md](AGENTS.md).

## Workstreams

- **Firmware** — the program flashed onto the ESP32 that drives the LEDs and plays stored
  animations.
- **Software** — what is installed on the board on top of the firmware: animation files,
  the list of animations that can be triggered, the playback order, and what starts at
  power-on.
- **Mapping** — the translation between canvas coordinates ((1,1) at the bottom-left LED) and
  the physical LEDs: which data pin, and which position along that pin's snake of rows or of
  columns.
- **Animations** — the animations themselves and the code that generates them.
- **Formats and conversion** — the defined file formats an animation passes through, from
  computer formats such as video to the format the board plays, and the tools that convert
  between them.
- **Emulator** — a local page that shows what the canvas would display and accepts the same
  commands as the board, so conversions and playback can be tested without the hardware.
- **On-site control** — operating the installation over Wi-Fi at the event, including an
  Android app for operators.
- **Tests** — automated checks for the mapping, the formats, the converters and playback.
- **Git repo** — this repository: its structure, history and workflow.
- **Agent files** — the pages in the folder [agent/](agent/) that tell coding agents and new
  contributors what this project is and how to work in it, with `AGENTS.md` and `CLAUDE.md`
  at the top of the repository as the way in.

Hardware and power wiring are not a workstream: they are handled on site by the operators.

Decisions made so far, and the questions still open, are in [docs/decisions.md](docs/decisions.md).
The animation file formats are specified in [docs/format.md](docs/format.md), the mapping
between canvas coordinates and physical LEDs in [docs/mapping.md](docs/mapping.md), for legs
of rows and legs of columns, with the bench build of two legs and the target build of
twenty upright legs, 60 x 60. What a show is is specified in [docs/show.md](docs/show.md),
and the commands in [docs/commands.md](docs/commands.md). Wi-Fi is covered in [docs/wifi.md](docs/wifi.md) and
the first notes on the operators' app in [docs/android-app.md](docs/android-app.md). Planned
work is in [project-seeds/](project-seeds/).

The converter, the JavaScript tool that turns media and JSON frames into the files the
board plays, with its library that also runs in a web page, and how to set it up, use it
and test it, is described in [docs/converter.md](docs/converter.md). The Python tool that
came first is kept as the reference the converter is compared with; it also holds the
generators of the tracked animations and builds the test vectors, and is described in
[docs/reference-converter.md](docs/reference-converter.md).

The core, the C++ library that plays those files on the board and in the emulator, and how
to build it, test it and host it, is described in [docs/core.md](docs/core.md).

The emulator, the Mac program that runs the core on a packed show and draws the LEDs in a
web page, the demo show for the target build, and the command tool that talks to the
emulator and to the board, are described in [docs/emulator.md](docs/emulator.md).

The firmware, the WLED build that hosts the core on the board and drives one output for
each of the twenty legs, and the tool that builds it, flashes it, installs a show and
restores stock WLED, are described in [docs/firmware.md](docs/firmware.md), with what was
measured on the board and what a person has still to check.
