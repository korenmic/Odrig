# The emulator

The emulator is a program for macOS and Windows that runs the core of [core.md](core.md) on an installed show,
the folder that [show.md](show.md) describes. It is the Python package `emulator` at the
repository root and uses only the Python standard library. It loads the core as a shared
library, built from the same `core/src/*.cpp` the firmware compiles, and leaves every
decision about files, time and commands to it.

This page covers the [commands](#commands) that build and test it, the
[two shows](#two-shows-to-run) to run, [starting](#starting) it, its
[serial port](#the-serial-port), [commands over HTTP](#commands-over-http), the
[command tool](#the-command-tool), [the page](#the-page) with its two views, the
[event stream](#the-event-stream), [record mode](#record-mode), the
[exit statuses](#exit-statuses), what is [open after the work on Windows](#on-windows) and
the [check list by eye](#the-check-list-by-eye).

## Commands

Run from the repository root.

| Command | What it does | What it needs |
|---|---|---|
| `make -C core shared` | Builds `core/build/libodrig_core.dylib`, the library the emulator loads, from every `core/src/*.cpp` with the flags of `make -C core`. | Apple's command-line developer tools: `make` and `c++`. |
| `python3 -m unittest discover -s tests/emulator -t .` | Builds the shared library and runs the suite of `tests/emulator/`. | The same, Python 3.10 or later with no added package, and the JavaScript shell that is part of macOS. |

On Windows the two commands are these. `python` there is the Python of the virtual
environment, `.venv\Scripts\python`.

| Command | What it does | What it needs |
|---|---|---|
| `python core/build.py shared` | Builds `core/build/odrig_core.dll`, the same library for Windows, from every `core/src/*.cpp`. It builds again only what changed. | A C++ compiler: `g++` or `clang++`, on the path or unpacked under the folder `tools/`, or Microsoft's C++ build tools. No GNU Make. |
| `python -m unittest discover -s tests/emulator -t .` | Builds the shared library with the build script and runs the suite of `tests/emulator/`. | The same, Python 3.10 or later with no added package, and Node.js as the JavaScript shell. |

Windows does not let a library be written while a running emulator has it loaded. A build
with nothing to do leaves the library alone, so the suite runs beside an open emulator.
When a source of the core has changed, stop the emulator first: the build script says so.

The emulator never builds the library itself. The suite is every `test_*.py` file in
`tests/emulator/`, found by discovery; importing the test package runs `make -C core shared`
first, and when that fails no test runs and make's output is the failure. The suite needs
no hardware, no network connection and no browser. The page's geometry is run in the
JavaScript shell of macOS,
`/System/Library/Frameworks/JavaScriptCore.framework/Versions/Current/Helpers/jsc`.
Where that shell is not there, the suite builds with the build script and takes Node.js
with `tests/emulator/js/shell.js`, a small program that takes the command line of `jsc`.
A test that needs the pseudo-terminal is skipped on Windows, and a test that only sends
lines beside HTTP sends them through the [line port](#the-line-port) there.

## Two shows to run

The emulator runs a packed show: the folder that `python -m odrig pack` writes, described in
[converter.md](converter.md). Two shows are tracked. `python` on this page is any Python
3.10 or later, `python3` on a Mac; nothing here needs the libraries of the converter's
virtual environment. `pack` refuses an output folder that is not empty, so remove the
folder before packing again.

**The example show**, for today's build of two legs, 60 x 6: Hello world and the bouncing
square, alternating every 15 seconds. Its sources are tracked in `animations/`.

```
python -m odrig pack --show shows/example/show.json --mapping mapping/legs-2.json \
    --sources animations --out build/example-show
python -m emulator build/example-show
```

**The demo show**, for the target build of twenty legs, 60 x 60: the same two animations
made for that canvas, alternating every 15 seconds and starting at power-on. Only
`shows/demo-20/show.json` is tracked. The two sources come to 4.2 MB, so they are written
by the generators into `build/`, which git ignores:

```
mkdir -p build/demo-20/sources
python -m odrig.generators.hello_world build/demo-20/sources/hello.json --mapping mapping/legs-20.json
python -m odrig.generators.dvd_bounce  build/demo-20/sources/dvd.json   --mapping mapping/legs-20.json
python -m odrig pack --show shows/demo-20/show.json --mapping mapping/legs-20.json \
    --sources build/demo-20/sources --out build/demo-20/show
python -m emulator build/demo-20/show
```

The canvas size comes from `mapping/legs-20.json` in every one of these commands; none
names 60. The generators centre Hello world on the canvas, where it stands in the rows 28
to 33. On a canvas as wide as it is high the square runs to and fro along one diagonal,
from the top-left corner to the bottom-right one, and so passes over every leg.

| Packed file | Frames | Bytes |
|---|---:|---:|
| `hello.odrg`, 5.1 s | 255 | 1,210 |
| `dvd.odrg`, 20.9 s | 116 | 1,052 |

The sizes are those the converter gives with zlib 1.2.12.

## Starting

```
python -m emulator SHOW_DIR [--port N] [--serial-link PATH] [--tcp-port N] [--core PATH] [--verbose]
```

Started from the repository root with the folder of an installed show, the emulator starts
the core on that folder, opens its virtual serial port and its address on 127.0.0.1, and
prints exactly these two lines:

```
page: http://127.0.0.1:8600/
serial: /Users/you/odrig/build/emulator/serial
```

It then asks the core for a refresh at every grid time, 20 ms apart, with a timestamp in
whole milliseconds from a clock that does not go backwards. When a request is late it
carries the current time; the grid times that were missed are not asked for again. The
emulator runs until it receives an interrupt (Ctrl-C) or a termination signal, on Windows
Ctrl-C or Ctrl-Break, and then removes the link to its port and exits with status 0.

| Option | Meaning | Without it |
|---|---|---|
| `--port N` | The port of the address on 127.0.0.1; 0 takes any free port. | 8600 |
| `--serial-link PATH` | Where the link to the serial port is made. | `build/emulator/serial` under the repository root, whatever folder the command is run from |
| `--tcp-port N` | The port of the [line port](#the-line-port) on 127.0.0.1; 0 takes any free port. | On a Mac there is no line port; on Windows it is 8601 |
| `--core PATH` | The core's shared library. | `core/build/libodrig_core.dylib` under the repository root; on Windows `core/build/odrig_core.dll` |
| `--verbose` | Prints the core's diagnostic lines to standard error, each after `core: `. | They are kept, not printed. |

There is no option for a size and none for an address: the canvas is the one of
`mapping.json` in the folder, and the address is always 127.0.0.1.

Any folder starts the emulator. Whether it holds a valid show is the core's judgement: with
an invalid show the LEDs stay dark, `status` gives the reason and every command is still
answered.

## The serial port

The emulator creates a pseudo-terminal and a symbolic link to it, so the port has the same
name on every run although the device behind it, such as `/dev/ttys012`, changes. A serial
tool that talks to the board talks to the emulator with only the port name changed:

```
python -m odrigctl --port build/emulator/serial status
```

- Every byte written to the port reaches the core's entry for bytes, unchanged and in
  order, and every reply of the core is written back. A line may arrive in pieces, and
  several lines may arrive at once.
- The port passes bytes unchanged in both directions. It does not echo, and it adds,
  removes and changes no newline and no carriage return.
- A program may open and close the port any number of times while the emulator runs. One
  emulator has one port: a line begun by one program is ended by the next.
- A pseudo-terminal has no speed and no modem lines. Setting a speed succeeds and changes
  nothing; a request to change DTR or RTS is refused by the system or does nothing.
- Replies that no program reads wait in the port, about a thousand bytes of them. When
  that room is full and stays full for a second, what waits is dropped to make room for the
  newer replies, as the output of a board is lost when nobody listens. A program should
  discard what is waiting when it opens the port, as the command tool does.

A link left at the path by an earlier run is replaced. If the path holds anything that is
not a symbolic link, the emulator refuses to start and leaves it untouched. Two emulators
at once need two link paths and two page ports.

## The line port

Windows has no pseudo-terminal. There the emulator offers the line protocol of the serial
port on a TCP port of 127.0.0.1 instead, the line port, and prints its address in place of
the serial port's:

```
page: http://127.0.0.1:8600/
tcp: 127.0.0.1:8601
```

On a Mac the serial port stays, and `--tcp-port N` opens the line port beside it; the
emulator then prints `tcp:` as a third line. On Windows `--serial-link` ends the emulator
with the reason `serial-unavailable`.

```
python -m odrigctl --tcp 127.0.0.1:8601 status
```

- A program connects, writes command lines and reads the replies. Every byte it writes
  reaches the core's entry for bytes, unchanged and in order, and every reply to a line
  those bytes finish is written back to the same connection. A line may arrive in pieces,
  and several lines may arrive at once.
- The port does not echo, and it adds, removes and changes no newline and no carriage
  return.
- A program may connect and leave any number of times, and several may be connected at
  once. As with the serial port, one emulator reads one stream of lines: a line begun on
  one connection and not ended is ended by the next bytes that arrive, on whichever
  connection. A program sends whole lines.
- A command that arrived this way has `tcp` as its transport in the log.
- Stopping the emulator closes every connection.

Two emulators at once need two line ports and two page ports.

## Commands over HTTP

The address accepts the commands of [commands.md](commands.md) as that document defines
them for HTTP, and hands each to the core's entry for one line:

```
curl --data-binary 'play 2' http://127.0.0.1:8600/odrig
{"ok":true}
```

| Request | Answer |
|---|---|
| `POST /odrig` | Status 200, content type `application/json`, and the reply line as the core returned it, with its newline. The status is 200 for a reply with `"ok":false` too. |
| Any other method on `/odrig` | Status 405 with `Allow: POST` and no body. The core is not called. |
| `POST /odrig` without a `Content-Length` that is a whole number | Status 411. The core is not called. |
| `GET /`, `GET /<name>` for a file of `emulator/web/` | The page and its files. See [The page](#the-page). |
| `GET /events`, `GET /show/mapping.json` | See [The event stream](#the-event-stream). |
| Any other path | Status 404. |

- The body is the command line, with or without a final newline. Of a body longer than 128
  bytes the first 128 are passed on, which the core answers with `line-too-long`.
- The content type of the request is not looked at.
- The path is `/odrig` exactly. What follows a `?` is ignored.
- The response that carries a reply has the header `Access-Control-Allow-Origin: *`.
- An answer without a body closes its connection.

## The page

The address the emulator prints is a web page: open it in Safari or Chrome. It is made of
plain files in `emulator/web/`, loads nothing from another host, and works without a
network connection. The page only shows: it sends no command. Every change on it comes
from the [event stream](#the-event-stream), so a command sent by any tool is seen at once.

From top to bottom the page has:

- **The header.** The show folder and the serial port, whether the event stream is
  connected, and the current status as `status` returns it: on or off, brightness, the id
  of the item playing and the id of the animation on the LEDs. `core` is the `fps` the core
  reports: its refreshes in the last full second. `page` is the page's own count: the
  refreshes it drew in the last full second.
- **The reason band.** When the core reports that the show is invalid, a red band shows the
  reason text exactly as the core gives it, for example `file-missing dvd.odrg`. With a
  valid mapping the LEDs are still drawn, all dark. With an invalid mapping there are no
  LEDs to draw, and the page says so.
- **The drawing**, in two views chosen by the tabs `LEDs` and `Mapping`, both described
  below, with a readout at its top right that names what the pointer is on:
  `leg 2, pin 2, LED 61 (1,2)`.
- **The command log.** One line for each command that arrived, by the serial port or over
  HTTP: the time it arrived, how it came, the line, and the reply. A line of more than 64
  characters is shown with its first 64 and the mark `…`. A byte outside printable ASCII is
  shown as `\xNN`. The log keeps the newest line in sight, and a page opened later shows
  the last 500 entries the emulator kept.

In a light appearance of the system the header and the log are light. The drawing always
stands on a dark stage, so the LEDs and the leg colours look the same either way.

### The LEDs view

The drawing shows every LED of every leg as a dot at its canvas position, with (1,1) at
the bottom-left, x growing to the right and y growing upward. It is scaled to fit the
window and drawn again when the window changes its size. A mapping file has legs of rows
or legs of columns ([mapping.md](mapping.md)), and the labels round the canvas follow the
kind of the file.

- **The page places the LEDs itself.** A refresh arrives as the bytes the core produced for
  each leg, in chain order, without coordinates. The page works out where LED n of a pin
  is from that pin, n and the show's `mapping.json`, by the rule of
  [mapping.md](mapping.md) for the kind of the file, and never reorders or corrects the
  data. A mapping mistake in the core therefore shows as a scrambled picture. The rule is
  in `emulator/web/layout.js`, which needs no browser, so the suite compares it with the
  reference for every LED.
- Each leg has one colour, and a faint band of the colour lies behind its rows or its
  columns. There are twenty colours; a twenty-first leg takes the first again.
- A dark LED is drawn as a faint ring, so every LED can be seen at any time.
- A colour value v is shown as `255 * (v / 255) ^ (1 / 2.2)`, rounded: a screen shows a low
  value much darker than an LED does. This one curve is the only change; the record file
  and the event stream carry the values unchanged.
- The page draws a dot again only when its bytes changed.

**Row legs**, as in today's build of two legs:

```
            x=1                                              x=60
 leg 1    | y=6    60  o o o o o o o o o o o o o o o o o o o    1
 pin 1    | y=5    61  o o o o o o o o o o o o o o o o o o o  120
          | y=4   180  o o o o o o o o o o o o o o o o o o o  121
 leg 2    | y=3    60  o o o o o o o o o o o o o o o o o o o    1
 pin 2    | y=2    61  o o o o o o o o o o o o o o o o o o o  120
          | y=1   180  o o o o o o o o o o o o o o o o o o o  121
```

- A bracket in the leg's colour spans the rows of the leg, with the leg's number and its
  pin. A leg whose rows are not neighbours gets a bracket for each run of rows.
- Every row has its `y` and, at its two ends, the numbers of the LEDs that sit there, so
  the direction of the chain can be read off.

**Column legs**, as in the target build of twenty legs:

```
           x=1       10        20        30        40        50      x=60
  leg       1   2   3   4   5   6   7  ...                      19  20
  pin       1   2   3   4   5   6   7  ...                      21  47
           .-. .-. .-. .-. .-. .-. .-.                          .-. .-.
  y=60     ooo ooo ooo ooo ooo ooo ooo ...                      ooo ooo
           ooo ooo ooo ooo ooo ooo ooo                          ooo ooo
  50       ooo ooo ooo ooo ooo ooo ooo                          ooo ooo
   :
  y=1      ooo ooo ooo ooo ooo ooo ooo ...                      ooo ooo
```

- **The feed edge** of a column-leg file is the edge of the canvas at which most of its
  legs have their first LED: the bottom, or the top. It is the bottom when as many legs
  start at the top as at the bottom.
- **The leg band** lies along the canvas on the side away from the feed edge: above the
  canvas when the snakes start at the bottom. For every leg it has a bracket that spans the
  leg's columns, with the leg's number and, under it, its pin, both in the leg's colour.
  The words `leg` and `pin` stand once, at the left end of the band. A leg whose columns
  are not neighbours gets a bracket with both numbers for each run of neighbouring columns.
- **Rows and columns.** At the left of the canvas the rows y = 1, every tenth row and the
  top row are marked, the first and the last with `y=`. The header marks the columns
  x = 1, every tenth column and the last one in the same way. A tenth row or column
  fewer than three from the last one is left out, so that no mark stands on another.
- **The LED numbers** at the two ends of every column stand in a band above and a band
  below the canvas, written upright, to be read from bottom to top. They are drawn where
  the cells, the squares of the drawing that one LED has, are 9 pixels or more. Below that
  the two bands are left out, and the mapping view is the place to read the numbers.
- **The cell** is the largest from 4 to 28 pixels at which the whole drawing fits the
  window, with nothing to scroll. For the target file in a window of 1280 x 800 that is 8
  pixels, a canvas of 480 x 480, without the LED numbers; the sizes in other windows are
  in the table under [The mapping view](#the-mapping-view).

### The mapping view

The second tab, `Mapping`, shows how the installation is wired: the board, which pin feeds
which leg, and how each leg's chain runs through its rows or its columns. The address
`http://127.0.0.1:8600/#mapping` opens it directly. It is the LEDs view with the board and
the wiring added, and its LEDs are live in the same way.

- **The board** is drawn as it lies on the desk in [mapping.md](mapping.md): the antenna at
  the top, the two USB sockets at the bottom, and its two rows of pins with their labels in
  that order. The labels are a small table in `emulator/web/board.js`; a test compares it
  with the drawing of that document. Everything about the legs comes from the show's
  `mapping.json`: other pins, another first side or end, another order or number of rows
  or columns are drawn without a change to the page.
- **One colour for each leg**, used for its pad on the board, the line from the pad, the
  path of its chain, the outline of its rows or columns, its numbers and its labels.
- **A line from each used pin to the first LED of its chain**, made of level and upright
  pieces and ending in an arrow head at that LED. The number 1 of that LED sits on the
  line as a tag. No two lines lie on each other, and no line passes through the board or
  over an LED.
- **The path of each chain** runs through the centres of the LEDs of every strip, behind
  the dots, with small arrows along the strip that point the way the LED numbers grow, a
  turn outside the edge of the canvas into the next strip, an arrow head where the chain
  comes back into the canvas, and a bar where the chain ends. The numbers at the two ends
  of every strip are the LED numbers there.
- **A pin the board does not have** gets a pad of its own beyond the end of the board,
  labelled `GPIO <pin>`.
- **Pointing** at a leg's label, its pin, its line or its rows or columns highlights that
  leg in all these places and fades the other legs. The readout names the leg and the
  pin, and over an LED also the LED number and its canvas coordinates.

**Row legs.** The board stands on the side of the canvas where most legs have their first
LED, and the lines run side by side in a channel between the canvas and the board, each on
a track of its own:

```
  labels and canvas, as in the LEDs view        channel             board
                                              +------------over the board-----------+
                                              |  +-------------------------------+  |
 leg 1 | y=6    60 o-o-o-<-o-o-o (1)<---------+  |      +-----------+            |  |
 pin 1 | y=5    61 o-o-o->-o-o-o 120             |      |  antenna  |            |  |
       | y=4   180 o-o-o-<-o-o-o 121             |  3V3 o           o GND        |  |
 leg 2 | y=3    60 o-o-o-<-o-o-o (1)<------------+  RST o           o RX         |  |
 pin 2 | y=2    61 o-o-o->-o-o-o 120                  4 o         1 (o)----------|--+  leg 1
       | y=1   180 o-o-o-<-o-o-o 121                  5 o         2 (o)----------+     leg 2
                                                        |  ESP32-S3 |
                                                        | [USB][USB]|
                                                        +-----------+
```

A pin in the row away from the canvas is reached round the board, over its top or under
its bottom, so that no line hides a pin or its label. A first LED at the far edge of the
canvas is reached through the gap above the leg's first row. A pad for a pin the board
lacks stands under the board. In a window too narrow for the board beside the canvas, the
canvas takes the width and the board stands below it; the drawing is then higher than the
window and scrolls. Where the pins of a file are out of the order of its legs on the
board, lines must cross. For the bench file in a window of 1280 x 800 the canvas has cells
of 13 pixels beside the board, and its two lines cross once: both pins are in the row away
from the canvas, and pin 1 lies above pin 2 there.

**Column legs.** Two channels carry the lines: the **level channel** along the feed edge of
the canvas, with one level track for each leg, and the **upright channel** beside the
board, with one upright track for each leg that needs one. The page has two arrangements
and takes the one that the width of the window allows.

*Wide: the board beside the canvas.* Used where the window is wide enough for cells of 9
pixels with the board beside the canvas; for the target file that is a drawing area 960
pixels wide or more. The level channel lies under the canvas and reaches on under the
upright channel, the board and the far zone, where the lines of the right row of pads
turn.

```
   header: x=1, 10, 20 ... x=60
   leg band: the number and the pin of every leg
   number band: 60 61 180 ...
  +----------------------------------------+  +---------+       +-------+  +------+
  |                                        |  | upright | names |       |  | far  |
  |           canvas, 60 x 60              |  | channel | of    | board |  | zone |
  |                                        |  |         | legs  |       |  |      |
  +----------------------------------------+  |         |       +-------+  |      |
   number band: (1) 120 121 ...               |         |                  |      |
  +-------------------------------------------+---------+------------------+------+
  |                              level channel                                    |
  +-------------------------------------------------------------------------------+
```

*Narrow: the board below the canvas.* Used where the window is narrower. The level channel
lies between the canvas and the board. The board stands at the left under it, with the
upright channel at its left, and the canvas begins to the right of the upright channel, so
that every first LED is to the right of every upright track. The margin this leaves at the
left of the canvas holds the marks of the rows.

```
              header, leg band, number band
  +---------+----------------------------------------+
  | marks   |                                        |
  | of the  |           canvas, 60 x 60              |
  | rows    |                                        |
  +---------+----------------------------------------+
              number band: (1) 120 121 ...
  +--------------------------------------------------+
  |                  level channel                   |
  +---------+-------+-------+------+-----------------+
  | upright | names |       | far  |
  | channel | of    | board | zone |
  |         | legs  |       |      |
  +---------+-------+-------+------+
```

In both arrangements the cells are kept at 9 pixels or more as long as the width allows
it, which for the target file is a drawing area 696 pixels wide or more. The drawing may
then be higher than the window, and the stage scrolls up and down.

**The line of a leg** runs from the pad of its pin, level, to its upright track; along the
upright track to its level track; along the level track to the x of the leg's first LED;
and upright to that LED at the feed edge, where it ends in an arrow head. The tag with the
number 1 is on this last piece. The name of the leg stands beside the board, in the row of
its pad.

**Which track.** The rules are the same in both arrangements. They keep two lines from
lying on each other and from crossing twice.

- *Level tracks.* The lines reach the level channel from one side: from the right in the
  wide arrangement, from the left in the narrow one. The leg whose first LED is farthest
  from that side takes the level track farthest from the canvas, and so on inward. So no
  line crosses another between its level track and its first LED.
- *Upright tracks of the left row of pads*, the row that faces the upright channel. The
  pad nearest the level channel takes the upright track nearest the board. So no line
  crosses another between its pad and its upright track. The lines of this row cross where
  an upright track passes a level track, in the corner between the two channels, and
  nowhere else.
- *The right row of pads.* A line from it goes round the board in a loop, one of two ways.
  **The short way** is round the end of the board that faces the level channel; the line
  reaches its level track from the far side of the board. **The long way** is round the
  other end of the board and then along the left side of the board, on a track beyond
  every other upright track. A leg takes the short way when its level track is in the half
  of the level channel farthest from the canvas, and the long way otherwise. In the narrow
  arrangement it takes the short way only when its first LED is also to the right of every
  loop: its line would otherwise turn back along its level track and cross another line
  twice. The loops of each way nest, so that they do not cross each other.
- A leg whose pin the board does not have gets a pad of its own beyond the end of the
  board that faces the level channel, labelled `GPIO <pin>`, and is treated as the pad
  nearest the level channel.
- A leg whose first LED is at the far edge of the canvas, at the top when the feed edge is
  the bottom, is reached through the gap at the left of the leg's first column: the last
  piece of its line runs in that gap from the feed edge to the far edge and turns into the
  LED from outside the canvas. Its tag stands in the number band at the far edge, over the
  column of the first LED, where the number 1 would stand.
- When the feed edge is the top, both arrangements are turned over from top to bottom, all
  but the board itself: the level channel lies above the canvas, the leg band below it,
  and in the narrow arrangement the board stands above the canvas.

For the target file the legs 1 and 2, on the pads of pins 1 and 2 in the right row, take
the short way in the wide arrangement, and the legs 19 and 20, on pins 21 and 47, the long
way. In the narrow arrangement it is the other way round.

**Crossings cannot be avoided.** Going down the left row of pads, the board has the pins
4, 5, 6, 7, 15, 16, 17, 18, 8, 3, 9, 10, 11, 12, 13, 14, while the legs stand in the order
of their numbers. Lines that start in one order and must end in another cross, whatever
the routing. With the rules above the lines of the target file cross 88 times, in both
arrangements, and no two lines cross more than once: 83 pairs of lines of the left row
whose upper pad has the lower leg number, four pairs of a short-way and a long-way line in
the far zone, and the lines of legs 19 and 20. Every crossing is at a right angle between
two tracks, every line has its leg's colour, the name of its leg stands beside its pad,
and pointing at a leg fades all the others.

**The snake of a leg**, for three columns that start at the bottom:

```
      60 | 61   180        the number band above the canvas
      .--.      ==         a turn outside the top edge; a bar where the chain ends
      ^  |      ^
      |  |      |          the path, behind the dots, with small arrows
      ^  v      ^          along every column, between two LEDs
      |  |      |
      |  `--.   |
      o  o  `---'          a turn outside the bottom edge
     (1) 120   121         the number band below; 1 is the tag on the leg's line
      ^
      |                    the line from the pad
```

- The path runs through the centres of the LEDs of the first column from its first LED to
  its last, turns outside the edge of the canvas into the second column, and so on. An
  arrow head marks where the chain comes back into the canvas after a turn, and a bar
  marks its end.
- Three small arrows along every column, between two LEDs, point the way the numbers grow.
- The outline of the leg is a rounded frame round each run of its columns, in its colour.
- The numbers at the ends of every column are written upright in the two number bands, in
  the leg's colour, clear of the turns. Where the columns of a leg are not neighbours, a
  turn passes the columns between them, outside the canvas.

**Sizes.** A level or an upright track takes 7 pixels. With the twenty legs of the target
file the level channel is 150 pixels deep and the upright channel 136 pixels wide. The
turns of the chains are 6 pixels outside the canvas, and the number bands are 30 pixels
high. The pads of the board are 10 to 20 pixels apart. The drawing area is what the header,
the tabs and the log leave of the window: in Chrome 1280 x 546 of a window of 1280 x 800,
and 756 x 627 of a window of 756 x 900. For the target file, in pixels:

| Drawing area | LEDs view | Mapping view |
|---|---|---|
| 1280 x 546 | cells of 8, without the LED numbers | wide, cells of 9, the drawing 1075 x 810 |
| 756 x 627 | cells of 8, without the LED numbers | narrow, cells of 9, the drawing 696 x 1263 |
| 1920 x 1000 | cells of 14, with the LED numbers | wide, cells of 12, the drawing 1255 x 990 |
| 600 x 546 | cells of 8, without the LED numbers | narrow, cells of 7, the drawing 576 x 1143 |

## The event stream

The page learns everything it shows from one stream of server-sent events, `GET /events`,
and from the mapping file of the show, `GET /show/mapping.json`, which is served byte for
byte (404 when the folder has none). Another program may read both in the same way.

The stream is a response of type `text/event-stream` that stays open. It has four kinds of
event:

```
event: hello
data: {"show":"/abs/path/of/show","page":"http://127.0.0.1:8600/","serial":"/abs/path/build/emulator/serial","tcp":null,"legs":[[1,1,180],[2,2,180]],"t0":3,"error":null}

event: log
data: {"seq":17,"ms":123456,"time":"14:03:22.512","transport":"serial","line":"play 2","cut":false,"reply":"{\"ok\":true}"}

event: status
data: {"ok":true,"on":true,"brightness":128,"playing":3,"animation":1,"fps":50,"error":null}

event: frame
data: 123460 <base64 of the refresh>
```

| Event | What it carries |
|---|---|
| `hello` | First on every connection. `serial` is the link of the serial port and `tcp` the address of the line port, each `null` when the emulator has none. `legs` lists `[leg, pin, number of LEDs]` in the core's order; `t0` is the power-on moment, the timestamp of the first request for a refresh; `error` is the reason the show is invalid as the core gives it when the page connects, or `null`. |
| `log` | One command that arrived: `ms` is the timestamp given to the core, `time` the local time of day, `transport` is `serial` or `http`, `line` the line as the core read it, and `reply` the reply without its newline. A line of more than 64 characters is given with its first 64 and `"cut":true`. A byte outside printable ASCII is written as `\xNN`. |
| `status` | The core's reply to `status`, unchanged. The emulator asks for it after every command that arrived and once a second. These requests of its own are not commands that arrived and are not in the log. |
| `frame` | One refresh: its timestamp, a space, and the refresh in base64: every leg's LED bytes in chain order, the legs in the order of `hello`. There are no coordinates in it: placing the LEDs is the page's work. |

A new connection gets `hello`, the log entries kept so far, the latest status, and then
everything that happens. The emulator keeps the last 500 log entries.

Log and status events are never dropped. Refreshes do not queue: each connection has one
place for the newest refresh, and a newer one replaces it, so a page that cannot keep up
skips refreshes and does not fall behind. What the system has already taken for a
connection, about half a megabyte on a Mac, is sent as it is. A connection with nothing to
send for 15 seconds is sent the comment line `: keep-alive`.

## The command tool

`odrigctl` sends the commands of [commands.md](commands.md) to the emulator or to the
board, through a serial port, over TCP or over HTTP. It is a second small Python package
at the repository root, uses only the Python standard library, and treats the two targets
alike: only the port name or the address says which one is meant.

```
python -m odrigctl (--port NAME | --tcp ADDRESS | --http ADDRESS) [--timeout SECONDS] play ID
python -m odrigctl (--port NAME | --tcp ADDRESS | --http ADDRESS) [--timeout SECONDS] on
python -m odrigctl (--port NAME | --tcp ADDRESS | --http ADDRESS) [--timeout SECONDS] off
python -m odrigctl (--port NAME | --tcp ADDRESS | --http ADDRESS) [--timeout SECONDS] brightness N
python -m odrigctl (--port NAME | --tcp ADDRESS | --http ADDRESS) [--timeout SECONDS] status
```

Through the serial port, here the emulator's; for the board the name is its USB serial
port, such as `/dev/cu.usbmodem101`:

```
python -m odrigctl --port build/emulator/serial play 2
python -m odrigctl --port build/emulator/serial on
python -m odrigctl --port build/emulator/serial off
python -m odrigctl --port build/emulator/serial brightness 40
python -m odrigctl --port build/emulator/serial status
```

Over TCP, to the emulator's [line port](#the-line-port), which is how the emulator takes
lines on Windows:

```
python -m odrigctl --tcp 127.0.0.1:8601 play 2
python -m odrigctl --tcp 127.0.0.1:8601 on
python -m odrigctl --tcp 127.0.0.1:8601 off
python -m odrigctl --tcp 127.0.0.1:8601 brightness 40
python -m odrigctl --tcp 127.0.0.1:8601 status
```

Over HTTP, here to the emulator's address; for the board the address is the one it has on
its Wi-Fi network:

```
python -m odrigctl --http 127.0.0.1:8600 play 2
python -m odrigctl --http 127.0.0.1:8600 on
python -m odrigctl --http 127.0.0.1:8600 off
python -m odrigctl --http 127.0.0.1:8600 brightness 40
python -m odrigctl --http 127.0.0.1:8600 status
```

The tool prints the reply line to standard output:

```
{"ok":true,"on":true,"brightness":40,"playing":2,"animation":2,"fps":50,"error":null}
```

| Status | Meaning |
|---:|---|
| 0 | The reply has `"ok":true`. |
| 1 | The reply has `"ok":false`. It is printed all the same. |
| 2 | The command line was not understood. |
| 3 | The target could not be reached, or no reply arrived within the time limit. One line `error: unreachable: <detail>` is written to standard error. |

- The line sent is `play <ID>`, `on`, `off`, `brightness <N>` or `status`, followed by a
  newline. ID and N are sent as they were typed and are not checked: `play abc` is sent and
  the reply says `bad-argument`. Every judgement is the command front-end's.
- `--timeout SECONDS` is how long the tool waits for the reply; 2 seconds without it.
- `--port NAME`: the tool opens the port without resetting the board. It sets 115200 baud,
  8 data bits and no parity, lowers RTS before it lowers DTR, waits 0.2 seconds, discards
  what arrives in the next 0.1 seconds, and sends the line. The reply is the first received
  line that is a JSON object with a member `ok`; every other line, such as a boot message,
  is ignored. A port without modem lines, which the emulator's is, refuses the two requests,
  and the tool goes on.
- `--port NAME` on Windows: the name is that of a real serial port, such as `COM3`. The
  tool opens it through the system's own library, lowers RTS before it lowers DTR, and
  then sets 115200 baud, 8 data bits, no parity and one stop bit, with DTR and RTS left
  low, so that opening the port again raises neither. Windows has no virtual serial port:
  the emulator is reached there with `--tcp` or `--http`.
- `--tcp ADDRESS`: `host:port`; the port has to be given. The tool connects, sends the
  line and takes the first received line that is a reply, as through a serial port.
- `--http ADDRESS`: `host` or `host:port`, with or without `http://` in front and a `/` at
  the end; without a port it is 80. The tool sends `POST http://ADDRESS/odrig` with the line
  as the body and the content type `application/octet-stream`, and takes the body of a
  response with status 200 as the reply. Any other status counts as not reached.
- The options may stand before or after the command.

Another program can use the three exchanges directly: `odrigctl.client.serial_exchange(port,
data, timeout)`, `odrigctl.client.tcp_exchange(address, data, timeout)` and
`odrigctl.client.http_exchange(address, line, timeout)` return the reply or raise
`Unreachable`. `serial_exchange` and `tcp_exchange` take a fourth argument, a function that
says which received line is the answer, for a target whose answer is not a reply of
[commands.md](commands.md).

## Record mode

```
python -m emulator SHOW_DIR --record OUT --seconds S [--script FILE] [--core PATH]
```

Record mode runs the core on a virtual clock, without waiting for real time, and writes
what the core gives every leg at every tick into the record file `OUT`. It opens no page
and no serial port. A tick is one grid time of that clock: 0 ms, 20 ms, 40 ms and so on,
every one below the length. `S` is a decimal number of seconds; the length is rounded to
the nearest millisecond.

```
python -m emulator build/example-show --record build/example.odrr --seconds 60
```

| Option | Meaning |
|---|---|
| `--record OUT` | Starts record mode and names the record file to write. |
| `--seconds S` | The length of the recording. It must be above 0. |
| `--script FILE` | Timed command lines to give the core. Without it no command is given. |
| `--core PATH` | Another shared library than `core/build/libodrig_core.dylib`. |

Recording the same folder with the same length and the same script twice gives the same
bytes. The emulator gives the core nothing of its own in this mode: only the requests for
a refresh and the commands of the script. The options `--port`, `--serial-link`,
`--tcp-port` and `--verbose` belong to real time and do not go with `--record`.

### The script

`--script FILE` names a UTF-8 text file of timed command lines:

```
# switch off after a second, and ask
1000 off
1010 status
2000 on
```

- A line is a time in whole milliseconds, written in decimal digits, one space, and the
  command line. The command line is given to the core as it is, so it may be any text,
  also one that is no command.
- Empty lines and lines that start with `#` are skipped.
- The times do not go backwards, and every time is below the length of the recording.

A command is given to the core with its own time as the timestamp, before the first tick
that is not earlier than that time: a command at 1000 is seen in the refresh of the tick at
1000, and a command at 1010 in the one at 1020. A command later than the last tick is given
after it. For each command the emulator prints one line to standard output, `reply`, the
time and the reply:

```
reply 1010 {"ok":true,"on":false,"brightness":128,"playing":3,"animation":1,"fps":50,"error":null}
```

The whole script is checked before the core starts. A script that breaks a rule is refused
and nothing is recorded.

### The record file

The file is binary. All integers are little-endian.

| Offset | Size | Field | Value |
|---:|---:|---|---|
| 0 | 4 | Magic | The bytes `4F 44 52 52` ("ODRR"). |
| 4 | 1 | Version | 1. |
| 5 | 1 | | Zero. |
| 6 | 2 | Leg count | L, as the core reports it. |
| 8 | 4 | Tick length | 20. |
| 12 | 4 | LED bytes | B: 3 times the number of LEDs of all legs. |
| 16 | 8 * L | Legs | For each leg, in the core's order: leg number (2), pin (2), number of LEDs (4). |

Then comes one tick record for every tick, each of `9 + B` bytes:

| Size | Field | Value |
|---:|---|---|
| 8 | Time | The tick's time in milliseconds. |
| 1 | Refresh | 1 when the core produced a refresh at this tick, 0 when it did not. |
| B | LED data | Each leg's bytes in chain order, red, green and blue for each LED, the legs in the order of the header. All zero when no refresh was produced. |

The number of ticks is the rest of the file divided by `9 + B`. With a mapping the core
refuses there are no legs, B is 0 and no tick has a refresh. The bytes are the values the
LEDs are given, with brightness applied, as [core.md](core.md) describes under "LED data".

The file is written as `OUT.part` and takes the place of `OUT` when it is complete.
`emulator/recfile.py` reads and writes the format; `recfile.read(path)` gives the legs and
the ticks to a Python program.

## Exit statuses

| Status | Meaning |
|---:|---|
| 0 | The emulator did its work. |
| 1 | It could not start. One line `error: <reason>: <detail>` is written to standard error, and no link, no listening address and no partly written file is left behind. |
| 2 | The command line was not understood. A usage message is written to standard error. |

| Reason | Condition |
|---|---|
| `not-a-folder` | `SHOW_DIR` does not exist or is not a folder. |
| `core-not-built` | The core's shared library is not found or cannot be loaded. The detail names the command that builds it. |
| `serial-unavailable` | The pseudo-terminal or its link cannot be created, or the link's path holds something that is not a symbolic link. |
| `address-in-use` | The address is already in use or cannot be opened. |
| `bad-length` | In record mode, the length is not above 0. |
| `bad-script` | In record mode, the script cannot be read or breaks one of its rules. |
| `cannot-write` | In record mode, the record file cannot be written, for example because its folder does not exist. |

Whether the folder holds a valid show is not the emulator's judgement but the core's: any
folder is recorded, and with an invalid show the LED data is dark and `status` gives the
reason.

## On Windows

The emulator, the command tool and the suite of both work on Windows 10 and 11. What is
different there is said where it belongs on this page: the [build](#commands), the
[line port](#the-line-port) in place of the serial port, and `--tcp` and a `COM` name in
the [command tool](#the-command-tool). Two lists are open after that work.

**Open for the first computer.** The work was done on a Windows computer, and nothing of
it could be run on macOS. To be seen there:

- The suites pass as before: `make -C core test`, the emulator suite, the converter
  suite and the onboarding suite. The tests that used the serial port as the transport
  beside HTTP now take it through a helper, and the tests of the JavaScript shell start
  `jsc` through one.
- The emulator opens its serial port and prints its two lines as before, and with
  `--tcp-port 0` prints `tcp:` as a third line and answers on that port.
- The command tool reaches the emulator and the board through `--port` as before:
  `odrigctl/client.py` kept its functions for the serial port of macOS and gained a
  choice between them and the port of Windows.
- The core suite passes with the name `_strlen` in `tests/core/allowed_symbols.txt`,
  which Apple's compiler does not use.
- `python3 core/build.py shared` is not how macOS builds, and has not been run there.

**Open for whoever has a board on a Windows computer.** No board was connected to the
Windows computer. To be seen with one:

- `python -m odrigctl --port COM<n> status` prints the board's status.
- The board does not restart when the port is opened, the first time after it is plugged
  in and the times after. Windows raises DTR and RTS when a port is opened that has not
  been set otherwise, before a program can say anything; the tool lowers RTS, then DTR,
  and leaves the port set so that the next opening raises neither. Whether the first
  opening restarts the board is not known.
- The firmware tool, `firmware/fw.py`, has not been run on Windows at all.

## The check list by eye

The suite checks everything a program can check without a browser. How the page looks is
checked by a person, or by a tool that drives a browser, with this list. Every step is done
twice: once in current Safari and once in current Chrome. The number in brackets is the
requirement and the criterion the step covers: of
`docs/specs/03-p0-emulator/requirements.md`, and where the brackets say `seed 05`, of
`docs/specs/05-p0-canvas-60-by-60/requirements.md`.

Before the first step, build the library and pack three shows: the example show and the
demo show as under [Two shows to run](#two-shows-to-run), and a dense 60 x 60 clip of 10
seconds on the target file:

```
make -C core shared
mkdir -p build/dense/sources
python -m odrig.generators.dense build/dense/sources/dense.json --mapping mapping/legs-20.json --seconds 10
printf '{"version": 1, "brightness": 255, "items": [{"id": 1, "file": "dense.odrg"}], "start": 1}\n' > build/dense/show.json
python -m odrig pack --show build/dense/show.json --mapping mapping/legs-20.json \
    --sources build/dense/sources --out build/dense/show
```

Give the browser a window of 1280 x 800. Steps 19 and 20 are about the size of the window;
in a narrower window the mapping view of every other step has the arrangement of step 20.

1. **The words are upright (4.8).** Start `python -m emulator build/example-show` and open
   the page. *Seen:* the words HELLO WORLD stand upright and read from left to right.
   After 15 seconds the bouncing square takes their place, and the two alternate every 15
   seconds.
2. **Dark LEDs are visible (4.6).** With the same show. *Seen:* every LED that is not lit
   is a faint ring, so all 360 positions can be made out.
3. **The page keeps up (4.9).** With the same show, watch the header for ten seconds.
   *Seen:* `page` shows 49 or more in every second, and so does `core`.
4. **A command is seen at once (8.1).** Send
   `python -m odrigctl --port build/emulator/serial brightness 40` and then
   `python -m odrigctl --http 127.0.0.1:8600 play 2`. *Seen:* without reloading, each
   command appears as a new line of the log as it is sent, with its time, `serial` or
   `http`, the line, and the reply `{"ok":true}`.
5. **The status follows (8.4).** After step 4. *Seen:* the header reads brightness 40,
   playing 2, animation 2. Send `python -m odrigctl --http 127.0.0.1:8600 off`: the header
   reads off and every LED is dark. Send `on`: the square is back.
6. **Row legs are drawn as before (seed 05, 10.1).** With the same show. *Seen:* in the
   LEDs view, at the left of the canvas, a bracket for each of the two legs with `leg 1`,
   `pin 1` and `leg 2`, `pin 2`, the `y` of every row from `y=6` down to `y=1`, and at the
   two ends of the rows of each leg the LED numbers 60 and 1, 61 and 120, 180 and 121.
   Choose `Mapping`: the board stands at the right of the canvas, and the lines of the two
   legs run from the pads of pins 1 and 2 over the top of the board and down the channel
   between the board and the canvas to the first LED of each leg, at the right end of its
   top row. In a window too narrow for the board beside the canvas, the board stands below
   the canvas. Choose `LEDs` again.
7. **The drawing fits and follows the window (4.2).** Stop the emulator and start
   `python -m emulator build/dense/show`. *Seen:* the whole 60 x 60 canvas is in the
   window, with nothing to scroll. Make the window smaller and larger: the drawing is drawn
   again at the new size each time.
8. **The page keeps up with a dense picture (4.9).** With the dense show, watch the header
   for ten seconds. *Seen:* `page` shows 49 or more in every second.
9. **Upright legs, each with its colour (seed 05, 8.2).** Stop the emulator and start
   `python -m emulator build/demo-20/show`. *Seen:* twenty legs side by side, each three
   columns wide, in twenty different colours. A faint band of the leg's colour lies behind
   its three columns. Above the canvas every leg has a bracket over its three columns, with
   the leg's number and under it its pin: the legs 1 to 20, on the pins 1 to 18, 21 and
   47. HELLO WORLD stands upright in the middle of the canvas.
10. **The whole target canvas with its labels (seed 05, 8.6).** With the same view. *Seen:*
    the whole canvas, 60 LEDs wide and 60 high, is in the window with the marks of its
    columns, from `x=1` to `x=60`, the band of the legs, and the marks of its rows, from
    `y=1` at the bottom to `y=60` at the top. Nothing scrolls, and every LED is a ring or a
    dot of its own, clear of its neighbours.
11. **The board (9.1).** Choose `Mapping`. *Seen:* a drawing of the board with the antenna
    at the top, the two USB sockets at the bottom, and two rows of pins labelled, from the
    top, 3V3, 3V3, RST, 4, 5, 6, 7 ... on the left and GND, TX, RX, 1, 2, 42 ... on the
    right, as in [mapping.md](mapping.md).
12. **Twenty legs with the animation on them (14.5).** With the same view. *Seen:* twenty
    legs on the pins 1 to 18, 21 and 47, each with a line from its pin to the first LED of
    its chain and the path of the chain up and down its three columns, and HELLO WORLD
    playing on the LEDs of this view.
13. **A line from every pin to its first LED (seed 05, 9.2).** With the same view, scrolled
    to the bottom of the canvas. *Seen:* from the pad of each of the twenty pins a line in
    the leg's colour runs to the bottom LED of the left column of its leg. It ends there in
    an arrow head that points up into the column, and just below the canvas it carries the
    number 1 of that LED in a small frame.
14. **The lines can be followed (seed 05, 9.3).** With the same view. *Seen:* every line is
    made of level and upright pieces. No two lines lie on each other, no line passes
    through the board or over an LED, and where two lines cross they cross once, at a
    right angle.
15. **The snakes (seed 05, 9.4).** With the same view. *Seen:* in every leg a path in the
    leg's colour runs behind the dots: up the left column, down the middle one and up the
    right one, with three small arrows along every column that point the way the chain
    runs. The turn from the left column into the middle one lies above the top edge of the
    canvas and the turn into the right column below its bottom edge, each with an arrow
    head where the chain comes back into the canvas. A short bar above the right column
    marks the end of the chain.
16. **The LED numbers (seed 05, 9.5).** With the same view. *Seen:* above the three columns
    of every leg stand the numbers 60, 61 and 180, and below them the tag with 1 and the
    numbers 120 and 121: written upright, in the leg's colour, each at the end of its
    column. No number is drawn over another or over a turn of a chain.
17. **Everything can be read (9.8).** With the same view, scrolling up and down. *Seen:* all
    twenty legs, their lines, their paths and the two end numbers of all 60 columns can be
    read, and no label is drawn over another.
18. **Pointing highlights one leg (9.5).** Point in turn at a leg's number above the
    canvas, at its pin on the board, at its line and at its columns. *Seen:* each time that
    leg stands out in all these places and the other legs fade. Over an LED the readout
    also names the leg, the pin, the LED number and the canvas coordinates.
19. **A wide window: the board beside the canvas (seed 05, 9.8).** With the same view, in
    the window of 1280 x 800. *Seen:* the board stands at the right of the canvas, with the
    upright pieces of the lines between the two and their level pieces under the canvas.
    Every LED is a ring or a dot of its own. The drawing is no wider than the window, so
    nothing scrolls sideways; it is higher than the window and scrolls up and down.
20. **A narrow window: the board below the canvas (seed 05, 9.9).** Make the window
    756 x 900. *Seen:* the canvas takes the width of the window and the board stands below
    it, at the left, with the level pieces of the lines between the canvas and the board
    and their upright pieces at the left of the board. The LEDs are as large as in the wide
    window, and nothing scrolls sideways. Make the window 1280 x 800 again.
21. **The page keeps up with 3,600 LEDs (seed 05, 8.9).** With the demo show, watch the
    header for ten seconds in the mapping view and for ten seconds in the LEDs view. Stop
    the emulator, start `python -m emulator build/dense/show`, and watch for ten seconds
    in the mapping view. *Seen:* `page` shows 49 or more in every second, each time.
22. **An invalid show says why (10.1).** Stop the emulator. Copy `build/example-show` to
    `build/example-broken`, remove `dvd.odrg` from the copy and start
    `python -m emulator build/example-broken`. *Seen:* a band under the header shows
    `file-missing dvd.odrg`, in the LEDs view and in the mapping view, and every LED is
    dark.

### What has been checked

Every step has been gone through in Chrome 154.0.8037.98 without a window (headless), on
this Mac, by a program that drives the browser through its remote-debugging port: it opens
the page, sends the commands of steps 4 and 5, clicks the tabs, changes the size of the
window, scrolls the drawing, moves the pointer, reads the header and the readout, and
takes screenshots. The list was gone through twice: once as it is written, in a window of
1280 x 800, and once in a window of 756 x 900 from the first step on, where the mapping
view has the arrangement of step 20 throughout and the board of the example show stands
below its canvas.

The 86 screenshots are in `build/t10/shots/`, which git ignores, beside the program and
the lists of its steps: `w-` for the wide window and `n-` for the narrow one, then the
number of the step. Each was looked at. The mapping view was also looked at in enlarged
parts: the corners of the canvas with the turns, the bars and the numbers, the first LEDs
with their tags, the corner where the lines cross, and the two rows of pads. All 22 steps
were as described in both windows, and Chrome reported no error of the page.

The page's own count, `page` in the header, was read for ten seconds at a time. It was 49
to 51 in every second with the example show, with the demo show and with the dense 60 x 60
clip, in the LEDs view and in the mapping view, in both windows. Chrome's animation frames
kept coming 60 times a second while the dense clip was drawn, and a second run of Chrome
without its graphics processor gave the same figures. So every LED is still drawn as a
circle: the page did not have to be made cheaper for 3,600 LEDs.

What is left for a person:

- No step has been gone through in Safari. The scripts of the page are valid for the
  JavaScript engine of Safari, which the suite checks in the JavaScript shell of macOS;
  that is all that is known about Safari.
- A person at a screen has not gone through the list in either browser. A browser without
  a window has no screen to keep up with: that `page` holds 49 on a real screen is still
  to be seen.
- Whether twenty lines with 88 crossings are clear enough to wire by. In the screenshots
  every line can be followed, most easily with the pointer on its leg, which fades the
  other nineteen; the tracks are 7 pixels apart.
- Whether the twenty colours can be told apart on the owner's screen. Some are close: the
  greens of legs 5 and 6, the greys of legs 12 and 18, the reds of legs 1, 11 and 20. Every
  leg also has its number at its columns, at its pad and in the readout.
- The page in a light appearance of the system, and a file whose legs start at the top or
  whose pins the board lacks: the list has no step for them. The suite covers the
  geometry of such files, and nobody looked at them in this pass.
