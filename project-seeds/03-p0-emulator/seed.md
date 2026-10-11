# Emulator

## Summary

A Mac program that runs the shared core on an installed file set, shows the physical LEDs in
a local web page, and accepts commands through a virtual serial port and over HTTP. The page
also shows how the legs, their snakes and the board's pins map onto the canvas. A command-line
tool sends the commands to the emulator or to the real board. Together they let conversions,
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
work against the emulator with only the port name changed. They also arrive over HTTP, which
stands in for the board's Wi-Fi: a phone app or a script talks to the emulator the way it
will talk to the board.

When a command arrives, the page shows it at once: the command, how it arrived, the reply,
and the LEDs changing.

The mapping is easier to trust when it can be seen. The page draws the board and its pins,
and shows which pin feeds which leg and how each leg's 180 LEDs snake through its three rows.

## Technical Constraints

- macOS only for now.
- The shared core is compiled natively for the Mac from the same source files the firmware
  uses. There is no browser build of the core in this seed.
- Apart from the core, the emulator uses only the Python standard library.
- It does not depend on any third-party emulator or simulator.
- The page works in current Safari and Chrome with no plug-ins.
- It listens only on 127.0.0.1 and needs no network connection.
- The command tool uses only the Python standard library.
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
   off, brightness and status. It reaches its target over serial, given a port name, or over
   HTTP, given an address, and works the same against the emulator and the board. It prints
   the reply and exits with a non-zero status when the reply is not ok or the target cannot
   be reached. The generic line sender stays as it is.
7. A record mode runs on a virtual clock without waiting: given a length of time and an
   optional script of timed command lines, it writes the per-leg LED data of every tick to a
   file.
8. When the show is invalid, the page shows the reason the core reports.
9. A wrong folder, a port that cannot be created, or a page address already in use gives a
   clear message and a non-zero exit.
10. The page's address also accepts commands over HTTP as `docs/commands.md` defines. They go
    to the same command front-end as serial lines.
11. The page shows a live command log: for each command, when it arrived, whether it came by
    serial or HTTP, the line, and the reply. It also shows the current status: on or off,
    brightness, the item playing and the animation on the LEDs.
12. The page has a mapping view, drawn from `mapping.json`:
    - a drawing of the ESP32-S3 board with its two rows of pins labelled as on the real board;
    - for every leg in the mapping, a line from its pin to the first LED of its snake;
    - the path of each snake through its three rows, with its direction and the LED numbers
      at the row ends;
    - one colour per leg, used for its pin, its line and its outline on the canvas;
    - pointing at a leg, its pin or its rows highlights that leg everywhere.
    The LEDs in this view are live: they show the animation as it plays.
13. A tracked demo show for the ten-leg mapping: Hello world and DVD bounce made for the
    60 x 30 canvas, alternating every 15 seconds and starting at power-on. The generators
    take the canvas size from a mapping file.

## Definition Of Done

1. On the example show from seed 01, the page shows Hello world readable and the right way up,
   then the bouncing square, alternating every 15 seconds, at 49 or more refreshes per second
   on this Mac.
2. With the ten-leg mapping and a dense 60 x 30 animation, the page holds 49 or more refreshes
   per second.
3. Record-mode output for 60 seconds of the example show, including two cycle switches,
   equals the reference from seed 01 with the mapping rule applied.
4. A session through the virtual serial port with the repository's command tool gives the
   expected reply to every command, and the page changes accordingly. The same session over
   HTTP gives the same replies.
5. With a mapping file in which one leg's `first_led` is flipped, the recorded picture
   differs from the reference in exactly that leg's rows.
6. Each command sent, by either transport, appears in the page's command log with its
   reply, and the status shown matches what `status` returns.
7. With the ten-leg demo show, the mapping view shows the board, ten legs on pins 1 to 10,
   and each leg's snake across its three rows, with the animation playing on the LEDs.
8. How to start the emulator and use the command tool is documented.

## Open Questions

None. Use the resolved behavior in this seed.
