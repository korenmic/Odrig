# Emulator

## Summary

A Mac program that runs the shared core on an installed file set, shows the physical LEDs in
a local web page, and accepts commands through a virtual serial port. It lets conversions,
shows and playback be tested without the hardware.

## Priority

- `P0`

## Depends On

- Seed 01, for packed shows and the reference it is checked against.
- Seed 02, for the shared core it runs.

## Product Context

The emulator is the project's first priority. Today nothing can be tried without the board,
the LED strips and a power supply on a desk.

The emulator must not be a second implementation of the player. It hosts the same core the
firmware hosts, runs the same folder of files that is uploaded to the board, and accepts the
same command lines.

It also tests the mapping. The page does not draw a picture in canvas coordinates. It takes
the LED data the core produces for each leg, and places every LED by its pin and its position
along the chain, using the mapping file. A mapping mistake in the core then shows as a
scrambled picture.

Commands arrive through a virtual serial port, so the serial tools that talk to the board
work against the emulator with only the port name changed.

## Technical Constraints

- macOS only for now.
- The shared core is compiled natively for the Mac from the same source files the firmware
  uses. There is no browser build of the core in this seed.
- Apart from the core, the emulator uses only the Python standard library.
- It does not depend on any third-party emulator or simulator.
- The page works in current Safari and Chrome with no plug-ins.
- It listens only on 127.0.0.1 and needs no network connection.
- The canvas size comes from `mapping.json` in the file set. The emulator has no size setting.
- The test command selects its suite by directory or discovery, never by a list of files.

## Required Behavior

1. It starts from one argument, the folder holding an installed file set, and prints the
   address of the page and the name of the virtual serial port.
2. It runs the core in real time, asking it for LED data every 20 ms.
3. The page draws every LED of every leg as a dot at the position the mapping gives it, with
   (1,1) at the bottom-left, scaled to fit the window. It marks which rows belong to which
   leg and pin, and shows the measured refresh rate.
4. The page works out each LED's position from the leg's pin, the LED's place along the
   chain, and `mapping.json`.
5. A line written to the virtual serial port goes to the core's command front-end and the
   reply line is written back.
6. The repository's command tool is brought to the commands in `docs/commands.md`: play, on,
   off, brightness and status. It works against the emulator and the board, chosen by port
   name. The generic line sender stays as it is.
7. A record mode runs on a virtual clock without waiting: given a length of time and an
   optional script of timed command lines, it writes the per-leg LED data of every tick to a
   file.
8. When the show is invalid, the page shows the reason the core reports.
9. A wrong folder, a port that cannot be created, or a page address already in use gives a
   clear message and a non-zero exit.

## Definition Of Done

1. On the example show from seed 01, the page shows Hello world readable and the right way up,
   then the bouncing square, alternating every 15 seconds, at 49 or more refreshes per second
   on this Mac.
2. With the ten-leg mapping and a dense 60 x 30 animation, the page holds 49 or more refreshes
   per second.
3. Record-mode output for 60 seconds of the example show, including two cycle switches,
   equals the reference from seed 01 with the mapping rule applied.
4. A session through the virtual serial port with the repository's command tool gives the
   expected reply to every command, and the page changes accordingly.
5. With a mapping file in which one leg's `first_led` is flipped, the recorded picture
   differs from the reference in exactly that leg's rows.
6. How to start it and use it is documented.

## Open Questions

None. Use the resolved behavior in this seed.
