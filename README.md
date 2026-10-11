# odrig

LED animation system for a Midburn installation: ESP32-S3 boards driving a canvas of
addressable LED strips.

## Workstreams

- **Firmware** — the program flashed onto the ESP32 that drives the LEDs and plays stored
  animations.
- **Software** — what is installed on the board on top of the firmware: animation files,
  the list of animations that can be triggered, the playback order, and what starts at
  power-on.
- **Mapping** — the translation between canvas coordinates ((1,1) at the bottom-left LED) and
  the physical LEDs: which data pin, and which position along that pin's snake of rows.
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
- **Agent files** — documents, policies and skills that tell coding agents what this project
  is and how to work in it.

Hardware and power wiring are not a workstream: they are handled on site by the operators.

Decisions made so far, and the questions still open, are in [docs/decisions.md](docs/decisions.md).
The animation file formats are specified in [docs/format.md](docs/format.md), the mapping
between canvas coordinates and physical LEDs in [docs/mapping.md](docs/mapping.md), what a
show is in [docs/show.md](docs/show.md), and the commands in
[docs/commands.md](docs/commands.md). Wi-Fi is covered in [docs/wifi.md](docs/wifi.md) and
the first notes on the operators' app in [docs/android-app.md](docs/android-app.md). Planned
work is in [project-seeds/](project-seeds/).

The converter that turns media and JSON frames into the files the board plays, and how to
set it up, use it and test it, is described in [docs/converter.md](docs/converter.md).
