# Decisions

What has been decided for this project, and what is still open. Each decision is stated as
it stands now.

## Scope and process

- The workstreams are the ones listed in the [README](../README.md).
- Hardware and power wiring are out of scope: operators handle them on site.
- On-site control is over Wi-Fi, with an Android app for operators. The board hosts the Wi-Fi
  network and phones join it. See [wifi.md](wifi.md) and the first notes on the app in
  [android-app.md](android-app.md).
- Questions that come up while writing specs or implementing are answered without asking the
  owner, and each one is recorded with its answer and resolution in [drifts.md](drifts.md).
- The operators' app is an Android APK built with Capacitor. A PC version built with Tauri,
  able to use serial as well as Wi-Fi, is intended later. Our own server on the board offers
  commands only and no web page.
- The board's Wi-Fi network is named `odrig` and has a password known to the operators. The
  password may be kept in this repository.
- The owner has accepted the Android SDK's licence terms, so the app's build may accept them
  when it installs the SDK.
- WLED's own web interface stays reachable and unchanged for now; the owner wants to explore
  it.
- Work is planned as seeds. A seed becomes a requirements / design / tasks trio, tasks are
  queued, and each task is one commit. Seeds live in `project-seeds/`, one folder per seed
  with its own state file.
- Several contributors work at once, on separate computers. Each works on a branch of
  their own, and nothing is committed directly on `master`. A branch is brought up to date
  with `master` before it is merged, and it is merged only with every test suite that
  needs no board passing. [drifts.md](drifts.md) and the change log of this file are only
  ever added to at the end, so that two contributors' additions can both be kept. Every
  significant advance is committed. There is no remote yet. See
  [working-rules.md](working-rules.md), "Several contributors at once".
- The repository carries a vocabulary, [vocabulary.md](vocabulary.md), and the working
  rules, [working-rules.md](working-rules.md), which hold the agent policies that are
  relevant to this project.

## Canvas and coordinates

- The canvas is 60 columns wide. A **leg** is one data pin of the board together with the
  three strips of 60 LEDs wired to it as a snake (180 LEDs). Legs are not chained to each
  other.
- A strip lies flat or stands upright, so it is a row or a column of the canvas. The
  mapping file format has both kinds of leg: row legs, whose strips are rows, and column
  legs, whose strips are columns. All legs of one mapping file are of one kind.
- Leg N uses the pin labelled N, except legs 19 and 20, which use pins 21 and 47: the pins
  labelled 19 and 20 carry the board's USB connection.
- The bench build, today's: 2 row legs, a 60 x 6 canvas, 360 LEDs, confirmed working. Leg 1
  holds the top three rows and leg 2 the three rows below them, and each chain starts at
  the right end of its top row. Its mapping file is `mapping/legs-2.json`.
- Target: a 60 x 60 canvas, 3,600 LEDs, on twenty legs. In the target the strips stand
  upright: its legs are column legs, each three columns of 60, and each snake starts at the
  bottom of its first column. Leg 1 is the leftmost and starts at (1,1), and each following
  leg holds the three columns to the right of the previous one. Its mapping file is
  `mapping/legs-20.json`. The mapping file format, the core, the emulator, the demo show
  and the firmware's twenty outputs are at this target; what is not yet reached on the
  board is under [Open questions](#open-questions).
- The mapping is defined by the files in `mapping/` and described in
  [mapping.md](mapping.md). The board and the emulator both read the installed mapping file
  at runtime; it is the only definition of the layout.
- Coordinates are 1-based, with (1,1) at the bottom-left LED. The proof-of-concept scripts in
  `animations/` and `tools/` still use the earlier convention (0-based, origin top-left).
- Playback target: 50 frames per second. On the board any rate from 20 to 50 is accepted;
  see "Firmware".

## Runtime architecture

- One shared core, written in C++, does everything that must behave the same on the board
  and in the emulator: decoding ODRG files, applying the mapping file, running the show,
  keeping time, and handling commands.
- The core is hosted twice: by the emulator on the Mac and by the firmware on the board. A
  host only supplies time, file access and a way to move command lines and LED data.
- Both hosts run the same installed file set: `mapping.json`, `show.json` and the `.odrg`
  files. See [show.md](show.md).

## Firmware

- Board: ESP32-S3-N16R8 (16 MB flash, 8 MB PSRAM), running the official WLED 16.0.1 build.
- WLED stays the base firmware. Stock WLED plays only GIF files, so playing the custom
  runtime format needs a custom WLED build with our player added.
- In the custom build WLED is the platform: LED output, storage and Wi-Fi. Playback and
  commands belong to the shared core, and the USB serial port carries the core's commands.
- On the board any refresh rate from 20 to 50 a second is accepted, for any content. The
  owner only minds a rate above 50 or below 20. Measured on the board on 2026-10-12 with
  the 60 x 60 target file: the demo show and a picture that does not change are refreshed
  50 times a second, and the dense test clip, in which every LED changes at every frame,
  36 to 42 times for the compressed file and 45 to 47 for the uncompressed one. So a dense
  file plays faster uncompressed on the board. The core needs 12.3 ms for a dense
  compressed frame and 8.6 ms for an uncompressed one, a send to twenty outputs 16.3 ms
  with WLED's limiter dimming every LED, and side by side, on the chip's two processor
  cores, both take a quarter to a third longer. See [firmware.md](firmware.md), "Verified
  on the board".

## Conversion

- Converting media to JSON frames and to ODRG runs on phones and PCs, never on the board and
  never in the emulator.
- There is to be one converter that runs from the command line without compiling and inside
  the Capacitor and Tauri apps. It will be written in JavaScript, with the Python converter
  kept as the independent check that tests compare it against.

## Animation formats

| Format | Role |
|---|---|
| JSON frames | The tracked, lossless source of each animation (source code, not runtime). A list of frames; each frame is a duration in milliseconds plus one value per LED, with only the fields that are consumed. |
| Custom binary, compressed | The runtime format the board plays. First choice. |
| Custom binary, uncompressed | Fallback if decompression proves too slow on the board. The player may support both. |
| GIF | Fallback of last resort: the working proof of concept on stock WLED. |

Animated PNG, FSEQ and live streaming from a computer were considered and dropped.

Both formats are specified in [format.md](format.md). The custom binary format is called ODRG.

### Measurements behind the choice

Sizes in bytes of the same animations in each format. Every lossless file was decoded back
and matched the original frames exactly. The dense clip is synthetic (a smooth full-colour
field, every LED lit, 10 seconds). Nothing here was measured on the board. The formats were
compared before the target became twenty upright legs, when it was 60 x 30, and the table
keeps the clip of that size; the sizes of the chosen format on the target of today, 60 x 60,
are in [format.md](format.md), "Measured sizes".

| Format | DVD bounce | Hello world | Square ping-pong | Dense 60x30, 10 s |
|---|---:|---:|---:|---:|
| GIF | 14,705 | 64,296 | 26,565 | 1,180,350 (lossy) |
| Animated PNG | 19,342 | 89,247 | 10,682 | 1,682,224 |
| FSEQ v2, zstd | 5,193 | 28,720 | 1,385 | 2,552,292 |
| JSON frames, integer colours | 176,523 | 366,690 | 48,244 | 7,282,998 |
| Raw RGB frames | 251,042 | 275,928 | 61,806 | 2,701,018 |
| Custom, no compression library | 3,795 | 17,733 | 2,987 | 765,897 |
| Custom with deflate | 1,593 | 1,132 | 1,410 | 723,715 |

- "Custom" here is a per-frame pixel predictor followed by a Rice bit coder with zero runs,
  using a palette when the animation has at most 256 colours. "With deflate" wraps that
  stream in deflate with a 32 KB window.
- Schemes that only store changed pixels or runs stayed at raw size on dense content.
- **What fits.** The board's storage partition has 10,354,688 bytes, and 9,001,905 bytes of
  animations have been installed in it and played. A dense 60 x 60 clip takes 138,377 bytes
  for a second compressed and 146,224 uncompressed, so storage holds 65 to 74 seconds of it
  compressed and 61 to 70 seconds uncompressed: the first figure of each pair is what has
  been shown to fit, the second what the whole partition would hold. A picture that nothing
  predicts is written as a stored frame record, 10,805 bytes for each 20 ms on a 60 x 60
  canvas, which makes 16 to 19 seconds of content stored frame by frame. Content that
  changes less takes less: the two animations of the demo show are 1,210 and 1,052 bytes.

## Commands

- The board and the emulator accept exactly the same commands, handled by the same
  front-end code. There are no emulator-only commands.
- A command exists only if something really uses it. Today those are: play an item by its
  ID, switch on, switch off, set brightness, and report status.
- Commands are plain text lines and every reply is one JSON line. See
  [commands.md](commands.md).
- Commands travel over serial and over HTTP, on the board and on the emulator alike. A
  command-line tool sends them to either target by either route.
- There is one list of commands for every route. A command is added to all routes or to
  none, and the owner approves every addition.

## Emulator

- The emulator is the first priority, so conversions and playback can be tested without the
  hardware.
- It runs on macOS for now; cross-platform comes later.
- It is our own Mac program around the shared core, built natively. It does not depend on
  any third-party emulator.
- Commands reach it through a virtual serial port, so the serial tools that talk to the board
  work against it unchanged, and over HTTP, which stands in for the board's Wi-Fi.
- Its page shows each command as it arrives, and a mapping view: the board and its pins, the
  line from each pin to its leg, and each leg's snake through its three strips, rows or
  columns.
- It draws the physical LEDs in a web view: it takes what the player sends to each leg and
  places every LED using the tracked mapping file, so a wrong mapping is visible.
- It has no size setting of its own. The canvas size comes from the mapping file, the same
  file the board uses.
- A ready-made emulator that runs the real firmware build may be added later as an extra. It
  is only considered if it needs no paid subscription, runs locally, and does not cap the
  emulated chip below the real ESP32-S3's speed.
- Espressif's emulator (version 0.48.0) was tried with the stock WLED 16.0.1 image and is not
  used. WLED boots and plays the installed show, but the emulator runs at about a third of
  real time, does not expose the USB serial console that carries commands, and the firmware
  panics intermittently when its web interface is polled.
- FastLED's browser compiler was tried and is not used. It held 50 frames per second on a
  60 x 30 matrix, the size of the target at the time, before the target became twenty
  upright legs. It has no command input and needs about 4.4 GB of toolchain. The native Mac
  emulator makes it unnecessary.

## Open questions

- Whether large video-derived JSON sources are tracked as they are (the dense 60 x 60 clip
  is 16 MB of JSON per 10 seconds).
- Decode speed of the custom format on the board at 50 frames per second. Measured on the
  board on 2026-10-11, before the target became twenty upright legs, with the firmware of
  seed 04 and a dense 60 x 30 clip on ten row legs, 1,800 LEDs: the core's work for one
  frame, reading from storage, decoding and placing every LED, takes 6.6 ms on average for
  the compressed file and 4.7 ms for the uncompressed one, and the board reported 49 or 50
  refreshes in every second for both. For the target, a dense 60 x 60 clip on twenty legs,
  3,600 LEDs, the same work takes 12.3 ms for a compressed frame and 8.6 ms for an
  uncompressed one, and the board plays that clip at 36 to 47 frames per second, inside the
  20 to 50 the owner accepts; see "Firmware" above. What stays open is the
  time at power-on: every file is checked by decoding it, which takes 6.0 seconds for one
  dense 60 x 60 clip of 10 seconds, 4.2 seconds for the same clip uncompressed, and took 38
  seconds for 9 MB of dense 60 x 30 clips, with the LEDs dark meanwhile. See
  [firmware.md](firmware.md), "Measurements on the board" and "Verified on the board".
- Twenty wired legs. One strip is wired, on pin 1; the other legs of the target are not
  wired. What stays open until twenty legs are wired: that LEDs light on pins 2 to 18, 21
  and 47, pin 3 being one of the chip's boot-mode pins and sixteen of the twenty legs
  being on WLED's parallel driver, which no LED of this project has been on; that the
  picture stands on the installation as the mapping file has it, leg 1 at the left with its
  first LED at the bottom; and the current. WLED's current limiter counts 3,600 mA for
  3,600 LEDs at rest, so with WLED's maximum of 850 mA it holds twenty legs at their lowest
  level until that maximum is raised in WLED's LED settings to what the power supply
  gives. The owner's checks 5 and 6 of [firmware.md](firmware.md) are the steps.
- Whether one board can drive twenty LED outputs. Stock WLED drives twelve on this chip;
  seed 05 tries for twenty and reports. Measured on the board on 2026-10-11: with one
  patch to WLED the firmware makes twenty working outputs, four through WLED's RMT driver
  and sixteen through its parallel driver, on pins 1 to 18, 21 and 47, and every pin
  carries the signal of a whole refresh. See [firmware.md](firmware.md), "Verified on the
  board".

## Change log

- 2026-10-08: Workstreams agreed. Hardware and power wiring ruled out of scope. Seed-based
  process, vocabulary file and project-relevant agent policies adopted.
- 2026-10-09: Runtime format direction chosen: a custom binary format with our own player,
  for the smallest size per animation.
- 2026-10-11: Format roles fixed (JSON source, custom binary runtime with and without
  compression, GIF fallback). Coordinates changed to 1-based with (1,1) at the bottom-left;
  they were 0-based from the top-left before.
- 2026-10-11: Command rule and emulator decisions added (shared command front-end, virtual
  serial port, physical LEDs drawn from the mapping file, size from the mapping file, filters
  for ready-made emulators).
- 2026-10-11: Format specification and mapping written. The runtime format is named ODRG.
  Leg N is on pin N, leg 1 is at the top of the canvas.
- 2026-10-11: All work goes directly on `master`; no remote yet. The mapping file is read
  at runtime by the board and the emulator. Runtime architecture fixed: one shared C++ core
  hosted by the emulator and by the firmware, plain-text commands with JSON replies, and the
  emulator as our own native Mac program. Show and command specifications written. Seeds
  created for the converter, the shared core, the emulator and the firmware build.
- 2026-10-11: Local trials of ready-made emulators finished. Espressif's emulator and
  FastLED's browser compiler are not used; the reasons are in the Emulator section.
- 2026-10-11: Scope widened by the owner. Commands also travel over HTTP on the emulator and
  the board; the emulator page gains a live command log and a mapping view of the board, legs
  and snakes; the command tool reaches the board or the emulator by serial or HTTP. The board
  hosts the Wi-Fi network. Seeds 03 and 04 were updated before any work on them began.
  Questions met along the way are answered without asking and recorded in drifts.md.
- 2026-10-11: The target canvas changed from 60 x 30 to 60 x 60. The operators' app is an
  Android APK built with Capacitor, with no web page served by our own server. Conversion
  runs only on phones and PCs, in one JavaScript converter. Every command exists on all
  routes and additions need the owner's approval. The Wi-Fi password may be kept in git.
- 2026-10-11: Seeds 05 to 09 created: the 60 x 60 canvas, the JavaScript converter, the
  content commands, the Wi-Fi name and password, and the operators' app. Two points were
  put to the owner and, with no objection, settled as recommended: the 60 rows go on ten
  pins with six rows each, and the commands `space`, `list`, `remove` and `upload` take the
  form written in seed 07. WLED's web interface stays as it is.
- 2026-10-11: The owner corrected the target again. A leg stays three strips of 60 (180
  LEDs), so 60 x 60 means twenty legs, and the strips stand upright with each snake starting
  at the bottom. This replaces the ten-pins-of-six-rows reading recorded earlier today. Seed
  05 was rewritten before any work on it began. The owner supplied a Wi-Fi password of valid
  length and accepted the Android SDK licence terms.
- 2026-10-11: The firmware of seed 04 measured on the board. The two open questions about
  the board, decode speed and ten outputs, have what was measured; what needs ten wired
  legs stays open.
- 2026-10-12: Seed 05 brought the project to the target of twenty upright legs, 60 x 60.
  The mapping file format has column legs beside row legs, `mapping/legs-20.json` and the
  demo show `shows/demo-20` take the place of the ten-leg file and its show, the core, the
  emulator and its page read both kinds, and with one patch to WLED the firmware makes
  twenty outputs. Measured on the board: twenty working outputs, and a dense 60 x 60 clip
  at 36 to 42 refreshes a second compressed and 45 to 47 uncompressed. The owner ruled that
  any rate from 20 to 50 a second is fine on the board, for any content. What fits into storage is computed again for 60 x 60:
  65 to 74 seconds of the dense clip. The open question about legs 3 to 10 is now the one
  about twenty wired legs.
- 2026-10-12: Several contributors now work at once, on separate computers. The rule that
  all work goes directly on `master` gives way to a branch for each contributor, brought
  up to date with `master` and merged only with every suite that needs no board passing.
  `drifts.md` and this change log are added to at the end only. The repository carries the
  vocabulary and the working rules.
