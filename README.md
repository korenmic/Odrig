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

Hardware and power wiring are handled on site by the operators. The approved miniature
test connection below still needs its electrical and powered acceptance checks.

## Miniature display debug mode

The software can project the full 60x60 canvas onto the purchased **Seeed Studio
6x10 RGB MATRIX for XIAO**, SKU 104030107, used landscape as 10 columns by 6 rows.
The square picture occupies the central 6x6 pixels; the two columns at either side
stay black. Each pixel averages a 10x10 block. Text, clocks and animations keep their
normal canvas and timing. This is a temporary output mode, off after every reboot.
Its firmware integration has host tests; it has **not** been built or tried on the
board in this run. Windows firmware compilation is deferred to seed 60.

### Approved connection and orientation

Power off before assembly or changing wires, and disconnect the full wall. Use
the matrix's dedicated pads, with the following intended connection:

| ESP32-S3 board | Matrix pad | Purpose |
|---|---|---|
| **5V** | **5V / VCC** | Approved 5V power connection |
| **GND** | **GND** | Common ground |
| **GPIO1** | **IN / DIN** | LED data input |

Leave **OUT / DOUT**, **3V3**, and the unused XIAO header pins unconnected.
GPIO1 means the ESP board's GPIO number; it is not a XIAO `D1` label. No XIAO
controller or second matrix is part of this connection. Inspect pad labels,
polarity, solder joints and shorts before powering the assembly.

Viewed from the **LED front**, place the IN edge at the **left** and the long
dimension horizontally; viewed from the **rear**, that IN edge is at the **right**.
Coordinates start at bottom left. The first LED is at that bottom-left corner;
chain indices 0..5 run upward, 6..11 up the next column, ending at 59 at top right.
This straight-column order, `index = x * 6 + y`, is derived from the manufacturer's
[schematic and PCB](https://files.seeedstudio.com/wiki/xiao-rgb-matrix/EAGLE_XIAO_MATRIX.zip),
following DIN through LED116 to LED39 and rotating to this landscape front view.
It still needs the powered corner/axis check; it is not an observed orientation.

The [manufacturer's guide](https://wiki.seeedstudio.com/rgb_matrix_for_xiao/)
identifies the part and pads. Its linked
[LED datasheet](https://files.seeedstudio.com/wiki/xiao-rgb-matrix/WS2812B-1010-DATASHEET.pdf),
page 5, gives a 2.8V input-high minimum at 5V. That supports the approved direct 3.3V
data plan for that part; actual part correspondence and signal margin remain to
be checked. This does not establish the ESP board's 5V current capacity.

### Before and during a powered check

1. Have the actual board's 5V supply path, protection, total load and any simultaneous
   USB power path checked, including startup, normal output and failed setup. No
   electrical/current budget or assembly has been accepted by these software tests.
   The mini brightness cap is not a power guarantee and applies only while mini is
   active; boot and restored normal mode use normal output and its selected brightness.
2. With the full wall disconnected and the accepted assembly powered, enable
   **Settings → Miniature display debug mode**, or send `debug mini on` through
   an existing command route. Read `status.mini`: wait for `pending:false`,
   `on:true` and `error:null`. A command's `ok` alone does not confirm output setup.
3. Mini output uses one 60-LED GRB bus on GPIO1 and brightness at most 40. Normal
   brightness and mapping remain unchanged. The app names active mode outside
   Settings; the emulator displays the same core-generated miniature beside its
   normal LEDs view. Failed setup keeps output dark and the reported mode unknown;
   an explicit retry or **Restore normal outputs** requests recovery.
4. Power off before changing back to wall wiring. Reboot returns to normal mode.
   If requesting `debug mini off` with the matrix still attached, first establish
   that the restored normal output's brightness/current is safe for that assembly.
   Do not move connectors while powered or rely on a saved local app switch.

Powered corners/axes, real frame/text/widget playback from internal storage and
microSD, clear transitions, responsive controls, 20–50 FPS, and phone readback and
reconnect remain open. See [the verification record](docs/specs/57-p2-miniature-matrix-debug-mode/verification.md)
and [the retained acceptance task](docs/specs/57-p2-miniature-matrix-debug-mode/tasks.md).

Decisions made so far, and the questions still open, are in [docs/decisions.md](docs/decisions.md).
The animation file formats are specified in [docs/format.md](docs/format.md), the mapping
between canvas coordinates and physical LEDs in [docs/mapping.md](docs/mapping.md), for legs
of rows and legs of columns, with the bench build of two legs and the target build of
twenty upright legs, 60 x 60. What a show is is specified in [docs/show.md](docs/show.md),
and the commands in [docs/commands.md](docs/commands.md). Wi-Fi is covered in [docs/wifi.md](docs/wifi.md) and
the operators' app, with how it is built and installed, in [docs/android-app.md](docs/android-app.md). Planned
work is in [project-seeds/](project-seeds/).

The converter, the JavaScript tool that turns media and JSON frames into the files the
board plays, with its library that also runs in a web page, and how to set it up, use it
and test it, is described in [docs/converter.md](docs/converter.md). The Python package that came
first is now a library for the tests and the tools: it reads and writes the project's
files, holds the generators of the tracked animations and builds the test vectors, and is
described in [docs/python-library.md](docs/python-library.md).

The core, the C++ library that plays those files on the board and in the emulator, and how
to build it, test it and host it, is described in [docs/core.md](docs/core.md).

The emulator, the program for macOS and Windows that runs the core on a packed show and draws the LEDs in a
web page, the demo show for the target build, and the command tool that talks to the
emulator and to the board, are described in [docs/emulator.md](docs/emulator.md).

The firmware, the WLED build that hosts the core on the board and drives one output for
each of the twenty legs, and the tool that builds it, flashes it, installs a show and
restores stock WLED, are described in [docs/firmware.md](docs/firmware.md), with what was
measured on the board and what a person has still to check.
