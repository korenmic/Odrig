# Firmware build with the player

## Summary

A custom WLED 16.0.1 build for the ESP32-S3 that hosts the shared core, with the tools to
build it, flash it, install a show on the board, and roll back to stock WLED.

## Priority

- `P1`

## Depends On

- Seed 01, for packed shows.
- Seed 02, for the shared core it hosts.

## Product Context

The board runs the official WLED 16.0.1 build, which plays only GIF files. Playing ODRG files
needs our player inside the firmware.

WLED stays as the platform: it drives the LED outputs, stores files and provides Wi-Fi.
Playback and commands belong to the shared core, the same code the emulator runs. A show
that works in the emulator then behaves the same on the board, from the same folder of files.

The board reads `mapping.json` when it starts. The firmware's LED outputs are set from that
file, so the mapping file is the only place the layout is defined.

## Technical Constraints

- Target: ESP32-S3-N16R8, 16 MB flash, 8 MB PSRAM, on the storage layout WLED's 16 MB build
  uses.
- The shared core's source files are used as they are. There is no copy or fork of them in
  the firmware build.
- The code added to WLED is thin: storage access, the serial transport, and passing the
  core's LED data to WLED's outputs.
- WLED's source is not stored in this repository. The build fetches it at the pinned tag
  v16.0.1. Any change to WLED's own files is kept as a small patch file.
- Build tools install into a project-local environment, with nothing installed system-wide.
- The factory backup is never deleted or overwritten. No eFuse is written.
- Tests that need the board say so and are kept apart from tests that do not.
- Hardware and power wiring are out of scope.

## Required Behavior

1. One command builds the firmware image from the repository.
2. One command flashes it over USB. One command restores stock WLED 16.0.1 from files whose
   checksums are verified.
3. At startup the core loads the installed file set from the board's storage.
4. The LED outputs are set from `mapping.json` at startup: one output per leg, on the leg's
   pin, with the leg's number of LEDs. WLED's own output settings are not a second source.
5. Every 20 ms the LED data the core produces for each leg is sent to that leg's output.
   WLED's effects, presets and playlists take no part in playback.
6. Only the core scales brightness. WLED's current limiter stays active.
7. The USB serial port carries the core's commands and replies as in `docs/commands.md`.
   WLED's own serial commands are switched off in this build.
8. WLED's Wi-Fi and web interface are left as they are. This seed adds no network commands.
9. One command installs a packed show folder into the board's storage over USB, verifies what
   was written, and restarts the board.
10. `status` reports the real refresh rate measured on the board.

## Definition Of Done

All on the real board.

1. With the example show installed, the board starts it at power-on with no command sent:
   Hello world and the bouncing square alternate every 15 seconds, confirmed by eye.
2. `status` reports 49 or more refreshes per second with the example show on the two wired
   legs.
3. The repository's command tool gives the same replies on the board as on the emulator for
   every command.
4. The show folder installed on the board is byte-identical to the one the emulator ran.
5. With the ten-leg mapping installed and a dense 60 x 30 animation playing, `status` reports
   49 or more refreshes per second, for the compressed file and for the uncompressed file.
   Only legs 1 and 2 need to be wired for this.
6. Restoring stock WLED works and the board answers WLED's handshake afterwards.
7. Building, flashing, installing a show and rolling back are documented.

## Open Questions

None. Use the resolved behavior in this seed.
