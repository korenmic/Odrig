# Decisions

What has been decided for this project, and what is still open. Each decision is stated as
it stands now.

## Scope and process

- The workstreams are the ones listed in the [README](../README.md).
- Hardware and power wiring are out of scope: operators handle them on site.
- On-site control is over Wi-Fi, with an Android app for operators.
- Work is planned as seeds. A seed becomes a requirements / design / tasks trio, tasks are
  queued, each task is one commit, and implementation goes through a pull request that a
  human merges. Each seed keeps its own state file.
- The repository will carry a vocabulary file and agent policies, limited to the policies
  that are relevant to this project.

## Canvas and coordinates

- The canvas is 60 columns wide. A **leg** is one data pin of the board together with the
  three 60-LED rows wired to it as a snake (180 LEDs).
- Leg N uses the pin labelled N. Leg 1 holds the top three rows and each following leg holds
  the three rows below the previous one. Every leg's chain starts at the right end of its
  top row.
- Today: 2 legs, 6 rows, 360 LEDs, confirmed working.
- Target: 10 legs, 30 rows, 1,800 LEDs.
- The mapping is defined by the files in `mapping/` and described in
  [mapping.md](mapping.md).
- Coordinates are 1-based, with (1,1) at the bottom-left LED. The proof-of-concept scripts in
  `animations/` and `tools/` still use the earlier convention (0-based, origin top-left).
- Playback target: 50 frames per second.

## Firmware

- Board: ESP32-S3-N16R8 (16 MB flash, 8 MB PSRAM), running the official WLED 16.0.1 build.
- WLED stays the base firmware. Stock WLED plays only GIF files, so playing the custom
  runtime format needs a custom WLED build with our player added.
- The decoder for the runtime format has one implementation, shared by the board and the
  emulator.

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
field, every LED lit, 10 seconds). Nothing here was measured on the board.

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
- The board has about 10 MB of file storage. That holds roughly 130 to 140 seconds of the
  dense 60x30 clip in the custom format, and about 78 seconds when the content is noisy.

## Commands

- The board and the emulator accept exactly the same commands, handled by the same
  front-end code. There are no emulator-only commands.
- A command exists only if something really uses it. Today those are: play an animation by
  its ID, switch on, switch off, set brightness, and report status.

## Emulator

- The emulator is the first priority, so conversions and playback can be tested without the
  hardware.
- It runs on macOS for now; cross-platform comes later.
- It plays the runtime format through the shared decoder.
- Commands reach it through a virtual serial port, so the serial tools that talk to the board
  work against it unchanged. A Wi-Fi channel is added when the Android app needs it.
- It draws the physical LEDs in a web view: it takes what the player sends to each leg and
  places every LED using the tracked mapping file, so a wrong mapping is visible.
- It has no size setting of its own. The canvas size comes from the mapping file, the same
  file the board uses.
- If running the real firmware inside an emulator proves too hard, a PC build of our player
  shown in the web view is an acceptable emulator.
- Ready-made emulators are only considered if they need no paid subscription, run locally,
  and do not cap the emulated chip below the real ESP32-S3's speed.

## Open questions

- Whether large video-derived JSON sources are tracked as they are (the dense clip is 7 MB of
  JSON per 10 seconds).
- Decode speed of the custom format on the board at 50 frames per second for 1,800 LEDs.
- Legs 3 to 10 on pins 3 to 10, and 10 outputs in the firmware, are untested on the
  hardware.
- Which ready-made emulator, if any, to build on. Local trials are in progress.

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
