# Shared runtime core

## Summary

A portable C++ library that plays an installed show. It decodes ODRG files, applies the
mapping file, runs `show.json`, keeps time, and handles commands. It is the single
implementation of all of that, used unchanged by the emulator and by the firmware.

## Priority

- `P0`

## Depends On

- Seed 01, for the test vectors and the reference decoder it is checked against.

## Product Context

The board and the emulator must behave the same. That is only certain if the code that
decides behaviour exists once. The decisions in `docs/decisions.md` require one decoder, one
command front-end, and one mapping file read at runtime by both.

The core is that one implementation. It owns everything that must not differ:

- reading `mapping.json`, `show.json` and `.odrg` files (`docs/mapping.md`, `docs/show.md`,
  `docs/format.md`);
- playback timing, looping, cycles, brightness and on/off;
- the commands and their replies (`docs/commands.md`).

Each host stays thin. It gives the core the time and access to files, passes command lines in
and reply lines out, and takes the LED data the core produces for each leg.

## Technical Constraints

- One code base in C++, compiled unchanged for macOS and for the ESP32-S3 inside the WLED
  16.0.1 build. It keeps to the language level that build's toolchain supports, and uses no
  exceptions, no run-time type information and no threads.
- No platform calls inside the core. Time, file access and logging go through a small host
  interface.
- No heap allocation after startup. Every buffer is sized at startup from the mapping.
- The core carries its own DEFLATE decompressor and its own JSON reader, so every build runs
  the same code. Third-party code brought in for this has a permissive licence.
- Output depends only on the files, the command lines and the timestamps the host supplies.
  The same inputs always give the same output.
- Working memory for a 60 x 30 canvas stays under 128 KB.
- It builds on macOS with the system compiler through one documented command, with nothing
  to install beyond Apple's command-line developer tools.
- `docs/format.md`, `docs/mapping.md`, `docs/show.md` and `docs/commands.md` are the
  authority.
- The test command selects its suite by directory or discovery, never by a list of files.

## Required Behavior

1. At startup the core reads `mapping.json` and `show.json` and checks every `.odrg` file the
   show names. If the show is invalid in any way `docs/show.md` lists, the LEDs stay dark and
   `status` reports the reason. Commands are still answered.
2. With a valid show, power-on state is: on, brightness from `show.json`, and the `start`
   item playing if there is one.
3. The host calls the core with the current time. Every 20 ms the core produces the LED data
   for that moment: for each leg in the mapping, its pin and the colour of each of its LEDs in
   chain order.
4. The picture follows `docs/format.md`: the frame on screen is the one whose time span
   contains the current time, animations loop, and the pixel buffer resets on each loop.
5. Canvas pixels reach LEDs exactly as `docs/mapping.md` defines.
6. A cycle shows each of its animations for its number of seconds, in order, forever, and
   starts each turn from the animation's first frame.
7. Brightness scales every colour value as `docs/commands.md` defines. When switched off,
   every LED is dark and playback time keeps running.
8. Commands and replies are exactly those in `docs/commands.md`, including every error code.
9. `status` reports the number of LED refreshes produced in the last full second.
10. A file is read front to back as a stream. The core never needs a whole file, or a whole
    frame record, in memory.

## Definition Of Done

1. Every valid test vector from seed 01 decodes to its expected frames, and every invalid one
   is rejected for its own reason.
2. For Hello world and DVD bounce on the two-leg mapping, and for a dense 60 x 30 clip on the
   ten-leg mapping, the per-leg LED data at every tick of a full loop equals the reference:
   seed 01's decoder followed by the mapping rule computed independently in the test.
3. A scripted session of timestamps and command lines gives the expected replies and LED
   data. It covers every command, every error code, a cycle switching animations, a turn
   restarting from the first frame, off and on, and brightness changes.
4. Each way a show can be invalid has a test: the LEDs stay dark and `status` names the
   reason.
5. A test build that fails on any heap allocation after startup passes the whole suite.
6. A benchmark on the Mac reports decode time per frame for the dense 60 x 30 clip,
   compressed and uncompressed.
7. The build command and the host interface are documented.

## Open Questions

None. Use the resolved behavior in this seed.
