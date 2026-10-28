# The emulator

The emulator is a program for macOS and Windows that runs the core of [core.md](core.md) on an installed show,
the folder that [show.md](show.md) describes. It is the Python package `emulator` at the
repository root and uses only the Python standard library and the repository's own
`odrig` package, pure Python, which reads the catalogs. It loads the core as a shared
library, built from the same `core/src/*.cpp` the firmware compiles, and leaves every
decision about files, time and commands to it. So it plays texts and clocks as the board
does, drawn by the core at every refresh, a clock with the seed `status` reports; its
suite finds every reference picture of `tests/vectors/procedural/` on its LEDs.

This page covers the [commands](#commands) that build and test it, the
[two shows](#two-shows-to-run) to run, [starting](#starting) it, its
[serial port](#the-serial-port), [commands over HTTP](#commands-over-http), the
[command tool](#the-command-tool), [previewing one animation](#previewing-one-animation),
[the page](#the-page) with its three views, the
[event stream](#the-event-stream), [record mode](#record-mode), the
[exit statuses](#exit-statuses), what is [open after the work on Windows](#on-windows) and
the [check list by eye](#the-check-list-by-eye).

## Commands

Run from the repository root.

| Command | What it does | What it needs |
|---|---|---|
| `make -C core shared` | Builds `core/build/libodrig_core.dylib`, the library the emulator loads, from every `core/src/*.cpp` with the flags of `make -C core`. | Apple's command-line developer tools: `make` and `c++`. |
| `python3 -m unittest discover -s tests/emulator -t .` | Builds the shared library and runs the suite of `tests/emulator/`. | The same, Python 3.10 or later with no added package, the JavaScript shell that is part of macOS, and Node.js 20 or later as `node`, for the test that runs the pack commands of this page. |

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

The emulator runs a packed show: the folder that `node converter/odrig.js pack` writes,
described in [converter.md](converter.md). `pack` needs Node.js 20 or later and nothing
else. Two shows are tracked. `python` on this page is any Python 3.10 or later, `python3`
on a Mac; nothing here needs a library outside Python's own. `pack` refuses an output
folder that is
not empty, so remove the folder before packing again.

**The example show**, for today's build of two legs, 60 x 6: Hello world and the bouncing
square, alternating every 15 seconds. Its sources are tracked in `animations/`.

```
node converter/odrig.js pack --show shows/example/show.json --mapping mapping/legs-2.json \
    --sources animations --out build/example-show
python -m emulator build/example-show
```

**The demo show**, for the target build of twenty legs, 60 x 60: the same two animations
made for that canvas, and nothing else: no cycle and no `start`. So it plays its
playlist, as [show.md](show.md#the-playlist) describes it: Hello world for six loops,
30.6 seconds, then the bouncing square for two loops, 41.8 seconds, and then from the
start again. Only `shows/demo-20/show.json` is tracked. The two sources come to 4.2 MB,
so they are written by the generators into `build/`, which git ignores:

```
mkdir -p build/demo-20/sources
python -m odrig.generators.hello_world build/demo-20/sources/hello.json --mapping mapping/legs-20.json
python -m odrig.generators.dvd_bounce  build/demo-20/sources/dvd.json   --mapping mapping/legs-20.json
node converter/odrig.js pack --show shows/demo-20/show.json --mapping mapping/legs-20.json \
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

The sizes are those the converter gives, on every computer. The generators are programs
of the Python library of [python-library.md](python-library.md).

## Starting

```
python -m emulator SHOW_DIR [--port N] [--serial-link PATH] [--tcp-port N] [--core PATH] [--verbose] [--storage BYTES] [--lan] [--drive DIR [--drive-read-only]] [--parent PID]
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
| `--storage BYTES` | The size of the storage the core is told of, as the total space of `space`: a whole number from 0 to 4,294,967,295. | 13,500,416, the size of the board's storage on its bigger layout |
| `--lan` | The page and the commands over HTTP are reachable on every IPv4 address of this computer, so that a phone on the same network reaches the emulator. See [From a phone](#from-a-phone). | 127.0.0.1 only |
| `--drive DIR` | The folder `DIR` stands for the top of a USB drive of animations. See [A drive](#a-drive). | No drive |
| `--drive-read-only` | With `--drive`: the core may not change the drive's files, as on a USB stick. | The core may change them, as on the card |
| `--parent PID` | The emulator ends, as on an interrupt, within a second or two after the process with this id ends, even when that process was killed without ending it. The preview and the tests give their own id, so that no emulator outlives them. | It runs until it is stopped |

There is no option for the size of the canvas and none that names an address: the canvas
is the one of `mapping.json` in the folder, and the emulator listens on 127.0.0.1, or
with `--lan` on every address this computer has.

**Storage.** The emulator gives the core the storage functions of [core.md](core.md) on
the folder it was started on, and on nothing else: a name with a path separator, or one
that is not made of the characters the core uses for a file name, is refused. For `space`
it reports the board's storage and not the Mac's disk: as the total 13,500,416 bytes, the
board's storage on its bigger layout, or the number given with `--storage`, and as the
free space the total less the sizes of the files of the folder, each rounded up to 4,096
bytes, and not below 0. `remove` and `upload` change the folder as they change the board's
storage: an upload is written into `upload.part` of the folder piece by piece and takes
its name when `upload end` succeeds, `show.json` is written again through `show.part`, and
a file no item names any more is deleted. To keep a show, run a copy of its folder. A
folder the emulator was stopped on during an upload holds `upload.part` until the emulator
is started on it again; `install-show` of the firmware tool refuses such a folder, as it
refuses any file the show does not name. The emulator paces nothing: its file operations
take microseconds, and the check of an uploaded file takes one frame of it for each
refresh, as on the board.

**After a start.** The show plays from the first refresh, however much is installed: the
core reads only the first 16 bytes of every animation before it plays. It reads the
animations to their ends while the show plays, as [core.md](core.md) describes under
"The check after the start", and until it has, `list`, `remove` and `upload begin` are
answered with `{"ok":false,"error":"busy"}`. A client asks again a moment later; every
other command works at once. For the example show that is over within a second. A fault
the core finds in an animation on the way makes the show invalid then: the LEDs go dark
and `status` gives the reason. The emulator has no code of its own for any of this, and
neither has the command tool, which prints `busy` as it prints every refusal and ends
with status 1. In record mode the core reads at the pace of the ticks, so a script that
lists, removes or uploads does so after the first second.

Any folder starts the emulator. Whether it holds a valid show is the core's judgement: with
an invalid show the LEDs stay dark, `status` gives the reason and every command is still
answered.

### A drive

With `--drive DIR` the emulator gives the core a USB drive of animations, as
[show.md](show.md#animations-from-a-usb-drive) describes, and the folder `DIR` stands
for its top:

```
python -m emulator build/demo-20/show --drive build/stick
```

- The emulator looks for the folder `DIR/odrig` once a second. When it appears, a drive
  is plugged in; when it goes, the drive is pulled out. A folder `DIR` that is not there
  yet is no error: the drive is plugged in once `DIR/odrig` is.
- The folder is listed when the core asks, for a drive without a catalog: the files whose
  names end in `.odrg` or `.odrgx`, in any case, and do not begin with a dot, of `odrig`
  and of its sub-folders to three levels, depth first, a folder's files by the bytes of
  their names and then its sub-folders by the bytes of their names, at most 256 files and
  32 sub-folders; a file in a sub-folder is named by its path, as `night/comet.odrg`. A
  folder whose name begins with a dot, ends with a space or a dot, holds a character a
  name may not, or is `System Volume Information` is passed over. The folder is not listed
  again while it stays. To take up files added to it, move the folder `odrig` away for two
  seconds and back.
- The core may change the drive's files, by their names, unless `--drive-read-only` is
  given: the files a change of the drive writes go into `DIR/odrig`.
- The core reads the drive's files after the installed ones, while the show plays. Each
  sound one joins the playlist and `list` with an id from 60001 up once it has been read;
  one that is not is left out, and with `--verbose` the reason is printed, as
  `core: drive file broken.odrg left out: truncated`.
- `space` counts the folder of the show only.
- The page's header names the folder `DIR` after `drive`.

`--drive` does not go with `--record`: record mode has no drive.

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
| `POST /seek` | The page's seek, see [Seeking](#seeking): the body is `{"ms": <point>}`, the point of the loop in milliseconds, and the answer is `{"ok":true,"animation":1,"start":40020,"turn":40020,"length":5100,"position":3000,"moved":2980}` or `{"ok":false,"error":"<reason>"}`, status 200 in both cases, with `Allow: POST` and 405 for another method and 411 without a `Content-Length` that is a whole number, as `/odrig`. It is no command of the core: the command list is unchanged. |
| Any other path | Status 404. |

- The body is the command line, with or without a final newline. A body of up to 4,096
  bytes reaches the core as it is; a line of more than 2,048 characters is answered by the
  core with `line-too-long`. Of a body longer than 4,096 bytes the first 4,096 are passed
  on, which the core answers in the same way.
- The content type of the request is not looked at.
- The path is `/odrig` exactly. What follows a `?` is ignored.
- The response that carries a reply has the header `Access-Control-Allow-Origin: *`.
- An answer without a body closes its connection.

## From a phone

A phone cannot reach 127.0.0.1 of a computer. Started with `--lan`, the emulator listens
for HTTP on every IPv4 address of this computer, and prints one more line with the
address a phone on the same network is given:

```
python -m emulator build/demo-20/show --lan
```

```
page: http://127.0.0.1:8600/
serial: /Users/you/odrig/build/emulator/serial
lan: http://192.168.1.23:8600/
```

The address is the one this computer has on the network that carries its default route.
On a computer that is on no network the line is `lan: no address`. Before it starts, the
emulator writes this to standard error:

```
warning: --lan: anyone on the local network can send commands to this emulator and open its page
```

- The whole HTTP server is on the network then: the commands, the page, the event stream
  and the mapping file. The emulator has no password.
- The serial port and the [line port](#the-line-port) stay on this computer.
- macOS may ask whether Python may accept incoming connections. A phone reaches the
  emulator only when that is allowed.
- `--lan` does not go with `--record`: record mode opens no address.

## The page

The address the emulator prints is a web page: open it in Safari or Chrome. It is made of
plain files in `emulator/web/`, loads nothing from another host, and works without a
network connection. The page itself only shows: it sends no command, and its one
control, the seek bar, asks the emulator to move playback, which is no command. Every
change on it comes from the [event stream](#the-event-stream), so a command sent by any
tool is seen at once. Its third view holds the operators' app, which does send commands,
as it does on a phone.

From top to bottom the page has:

- **The header.** The show folder and the serial port, whether the event stream is
  connected, and the current status as `status` returns it: on or off, brightness, what
  is playing, which reads `playlist` for the playlist and is the id of a cycle otherwise,
  and the id of the animation on the LEDs. `core` is the `fps` the core
  reports: its refreshes in the last full second. `page` is the page's own count: the
  refreshes it drew in the last full second.
- **The reason band.** When the core reports that the show is invalid, a red band shows the
  reason text exactly as the core gives it, for example `show-missing`. With a
  valid mapping the LEDs are still drawn, all dark. With an invalid mapping there are no
  LEDs to draw, and the page says so.
- **The drawing**, in the views chosen by the tabs `LEDs`, `Mapping` and `Controller`,
  each described below, with a readout at its top right that names what the pointer is
  on: `leg 2, pin 2, LED 61 (1,2)`.
- **The seek bar**, under the drawing in every view that shows it: the id of the
  animation on the LEDs, a bar of where it is in its loop, and `m:ss / m:ss`, the time
  played and the loop's length, `h:mm:ss` from one hour. It says `length unknown` while
  the length is not known, and shows nothing while nothing plays or a cycle plays.
  Dragging the bar, or pressing on it, moves playback to that point, see
  [Seeking](#seeking); for three seconds after it the row says by how much the
  emulator's clock moved, `clock +12 s`.
- **The command log.** One line for each command that arrived, by the serial port or over
  HTTP: the time it arrived, how it came, the line, and the reply. A line of more than
  200 characters is shown with its first 200, the mark `…` and the number of characters it
  has; for a line of more than 2,048 characters, which the core cuts, the mark says
  `more than 2048 characters`. A byte outside printable ASCII is shown as `\xNN`. The log
  keeps the newest line in sight, and a page opened later shows the last 500 entries the
  emulator kept.

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
  [mapping.md](mapping.md) for the kind of the file, a leg's `starts` included, and never
  reorders or corrects the data. A mapping mistake in the core therefore shows as a scrambled picture. The rule is
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

### The controller view

The third tab, `Controller`, shows the LEDs as the LEDs view does and, beside them, the
operators' app of [android-app.md](android-app.md). The address
`http://127.0.0.1:8600/#controller` opens it directly. The app stands in a frame as wide
as a phone, 390 points; in a window narrower than 760 points it lies under the LEDs.

- **The same code.** What runs in the frame is the app's web code, the files of
  `app/www/`, which the emulator serves under `/app/` as they are, with the scripts of
  the converter's library, `converter/lib/`, under `/app/converter/`, and the default
  preview catalog, `thumbnails/`, its `catalog.js` and its GIFs as `image/gif`, under
  `/app/thumbnails/`. The table of what it serves is made when it starts. The APK holds the
  same files, so what a button does here is what it does on a phone. One thing differs: on a
  phone a piece of Android code carries each line to the target, and here the browser
  does.
- **Its target is this emulator.** The page gives the app its own address before the app
  starts, so the app answers at once and goes to its show screen. The app's target
  screen shows that address, and takes another as it does on a phone.
- **What it sends.** `status` once a second, `list` now and then, and a line for each
  press: `play <id>`, `play all`, `on`, `off`, `brightness <n>`. The lines are in the
  command log as lines over HTTP, and the LEDs beside the app show what they did.
- **Only while it is shown.** The frame is made when the tab is chosen and removed when
  another tab is: on the other two views the app does not run, and nothing is sent.

With `--lan` the browser of a phone opens the same view at the address of the `lan:`
line with `#controller` at its end.

The emulator serves `app/www/` from the repository it runs in. Where that folder is not
there, the frame is empty.

The Controller view is the app itself: the files of `app/www/` as they are in the checkout
the emulator runs from, the same files the APK is built from. A difference between what
the Controller view shows and what the phone shows is a fault, by the working rules, "One
app, in the emulator and on the phone"; the first thing to check is that the emulator and
the APK come from one commit.

### Seeking

The emulator knows where the animation on the LEDs stands, which the core does not tell:
the core opens the file it plays through the emulator's host anew at the start of every
loop and of every turn, and so the emulator takes the grid time of the refresh in which
the played file was opened as the start of the loop that shows, and the first such open
after the animation changed, after a command was answered, or after a restart of the
emulator's own as the start of the turn. The position is the time since the loop's start
on the clock of the frames' timestamps.

The loop's length comes from three sources, the first that answers: the catalog of the
storage the file is in, when it has one; the converter's `check` of the file, run once
per file in a thread of the emulator, when Node.js is on the path; and the loop itself,
once the emulator has seen two consecutive opens of the same file with no command
answered and no seek between them. A text or a clock without a catalog entry has no
length. Reading a catalog or running the converter never delays a refresh.

What the emulator knows goes to the page as the `position` event of the
[event stream](#the-event-stream). A cycle shows nothing: the emulator tells a cycle's id
in `playing` from a folder's of the card, whose playlist shows its animation as the
playlist does, by the cycles that `list` names, asked of the core when `playing` holds a
number not yet told apart since the last command answered.

A seek names a point of the loop, from 0 to the length less two grid steps, and the
emulator moves playback there with what it has. When the point is at or after the
position, it moves its own clock forward by the difference, rounded down to whole grid
steps, in strides of 400 ms with a refresh asked of the core at each, so that the core,
which decodes a bounded part of a file at one refresh, comes to the picture of each
stride at once and the LEDs show the frame of the point as soon as the move is done;
nothing is replayed. When the point is before the
position, the emulator first restarts the animation with a `play <id>` of its own, which
the log shows with the transport `seek`, moves its clock one grid step so that the core
takes the refresh that begins the turn, and then moves to the point. A move of the clock
is running time for the core: the turn and whatever else the core counts in time advance
by it, and the clock never goes back. A seek backward begins a new turn with its `play
<id>`, and so drops the count that `repeat <id> <n>` gave the turn; a saved repeat stays.
The answer to a seek is refused with
`nothing-plays` while no animation is on the LEDs, `cycle` while a cycle plays,
`length-unknown` while the length is unknown, `beyond-length` for a point out of reach,
and `bad-argument` for a body that is not `{"ms": <whole number>}`.

## The event stream

The page learns everything it shows from one stream of server-sent events, `GET /events`,
and from the mapping file of the show, `GET /show/mapping.json`, which is served byte for
byte (404 when the folder has none). Another program may read both in the same way.

The stream is a response of type `text/event-stream` that stays open. It has five kinds of
event:

```
event: hello
data: {"show":"/abs/path/of/show","drive":null,"page":"http://127.0.0.1:8600/","serial":"/abs/path/build/emulator/serial","tcp":null,"legs":[[1,1,180],[2,2,180]],"t0":3,"error":null}

event: log
data: {"seq":17,"ms":123456,"time":"14:03:22.512","transport":"serial","line":"play 2","length":6,"cut":false,"reply":"{\"ok\":true}"}

event: status
data: {"ok":true,"on":true,"brightness":128,"playing":3,"animation":1,"fps":50,"error":null,"width":60,"height":6,"seed":null,"left":86399}

event: position
data: {"animation":1,"start":40020,"turn":40020,"length":5100}

event: frame
data: 123460 <base64 of the refresh>
```

| Event | What it carries |
|---|---|
| `hello` | First on every connection. `drive` is the folder of `--drive`, or `null` without it. `serial` is the link of the serial port and `tcp` the address of the line port, each `null` when the emulator has none. `legs` lists `[leg, pin, number of LEDs]` in the core's order; `t0` is the power-on moment, the timestamp of the first request for a refresh; `error` is the reason the show is invalid as the core gives it when the page connects, or `null`. |
| `log` | One command that arrived: `ms` is the timestamp given to the core, `time` the local time of day, `transport` is `serial`, `tcp`, `http` or, for a restart the emulator made for a seek, `seek`, `line` the first 200 characters of the line as the core read it, `length` the number of characters of that line, and `reply` the reply without its newline. A line of more than 2,048 characters, which the core cuts to its first 2,048, has `"length":2048` and `"cut":true`. A byte outside printable ASCII is written as `\xNN`. |
| `status` | The core's reply to `status`, unchanged. The emulator asks for it after every command that arrived and once a second. These requests of its own are not commands that arrived and are not in the log. |
| `frame` | One refresh: its timestamp, a space, and the refresh in base64: every leg's LED bytes in chain order, the legs in the order of `hello`. There are no coordinates in it: placing the LEDs is the page's work. |
| `position` | Where the animation on the LEDs stands, for the [seek bar](#seeking): its id, the start of the loop that shows and the start of its turn, both on the clock of the frames' timestamps, and the loop's length in milliseconds; each `null` while unknown, and all four `null` while nothing plays or a cycle plays. It is sent to a new connection after the latest status, and at every change: a turn's start, a loop's start, a seek, a length learned. |

A new connection gets `hello`, the log entries kept so far, the latest status, the latest
position, and then everything that happens. The emulator keeps the last 500 log entries.

Log, status and position events are never dropped. Refreshes do not queue: each connection has one
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
python -m odrigctl (--port NAME | --tcp ADDRESS | --http ADDRESS) [--timeout SECONDS] fault
python -m odrigctl (--port NAME | --tcp ADDRESS | --http ADDRESS) [--timeout SECONDS] space
python -m odrigctl (--port NAME | --tcp ADDRESS | --http ADDRESS) [--timeout SECONDS] list
python -m odrigctl (--port NAME | --tcp ADDRESS | --http ADDRESS) [--timeout SECONDS] read ID OFFSET
python -m odrigctl (--port NAME | --tcp ADDRESS | --http ADDRESS) [--timeout SECONDS] catalog [OPERATION]
python -m odrigctl (--port NAME | --tcp ADDRESS | --http ADDRESS) [--timeout SECONDS] remove ID
python -m odrigctl (--port NAME | --tcp ADDRESS | --http ADDRESS) [--timeout SECONDS] ignore ID VALUE
python -m odrigctl (--port NAME | --tcp ADDRESS | --http ADDRESS) [--timeout SECONDS] mapping OPERATION
python -m odrigctl (--port NAME | --tcp ADDRESS | --http ADDRESS) [--timeout SECONDS] order OPERATION
python -m odrigctl (--port NAME | --tcp ADDRESS | --http ADDRESS) [--timeout SECONDS] repeat ID N [save]
python -m odrigctl (--port NAME | --tcp ADDRESS | --http ADDRESS) [--timeout SECONDS] upload ID FILE
python -m odrigctl (--port NAME | --tcp ADDRESS | --http ADDRESS) [--timeout SECONDS] upload --external FILE
```

Through the serial port, here the emulator's; for the board the name is its USB serial
port, such as `/dev/cu.usbmodem101`:

```
python -m odrigctl --port build/emulator/serial play 2
python -m odrigctl --port build/emulator/serial on
python -m odrigctl --port build/emulator/serial off
python -m odrigctl --port build/emulator/serial brightness 40
python -m odrigctl --port build/emulator/serial status
python -m odrigctl --port build/emulator/serial fault
python -m odrigctl --port build/emulator/serial space
python -m odrigctl --port build/emulator/serial list
python -m odrigctl --port build/emulator/serial read 1 0
python -m odrigctl --port build/emulator/serial catalog
python -m odrigctl --port build/emulator/serial catalog rebuild internal
python -m odrigctl --port build/emulator/serial catalog page internal 0 0
python -m odrigctl --port build/emulator/serial upload 9 build/hello-bench.odrg
python -m odrigctl --port build/emulator/serial upload --external build/hello-card.odrg
python -m odrigctl --port build/emulator/serial remove 9
python -m odrigctl --port build/emulator/serial remove many 9,10
python -m odrigctl --port build/emulator/serial ignore 9 1
python -m odrigctl --port build/emulator/serial order get
python -m odrigctl --port build/emulator/serial order move 2805384113 9 1
python -m odrigctl --port build/emulator/serial repeat 1 8
python -m odrigctl --port build/emulator/serial repeat 1 8 save
python -m odrigctl --port build/emulator/serial repeat 1 default
```

Over TCP, to the emulator's [line port](#the-line-port), which is how the emulator takes
lines on Windows:

```
python -m odrigctl --tcp 127.0.0.1:8601 play 2
python -m odrigctl --tcp 127.0.0.1:8601 on
python -m odrigctl --tcp 127.0.0.1:8601 off
python -m odrigctl --tcp 127.0.0.1:8601 brightness 40
python -m odrigctl --tcp 127.0.0.1:8601 status
python -m odrigctl --tcp 127.0.0.1:8601 fault
python -m odrigctl --tcp 127.0.0.1:8601 space
python -m odrigctl --tcp 127.0.0.1:8601 list
python -m odrigctl --tcp 127.0.0.1:8601 read 1 0
python -m odrigctl --tcp 127.0.0.1:8601 catalog
python -m odrigctl --tcp 127.0.0.1:8601 catalog cancel
python -m odrigctl --tcp 127.0.0.1:8601 catalog page external 3 0
python -m odrigctl --tcp 127.0.0.1:8601 upload 9 build/hello-bench.odrg
python -m odrigctl --tcp 127.0.0.1:8601 upload --external build/hello-card.odrg
python -m odrigctl --tcp 127.0.0.1:8601 remove 9
python -m odrigctl --tcp 127.0.0.1:8601 remove many 9,10
python -m odrigctl --tcp 127.0.0.1:8601 ignore 9 1
python -m odrigctl --tcp 127.0.0.1:8601 order get
python -m odrigctl --tcp 127.0.0.1:8601 order move 2805384113 9 1
python -m odrigctl --tcp 127.0.0.1:8601 repeat 1 8
python -m odrigctl --tcp 127.0.0.1:8601 repeat 1 8 save
python -m odrigctl --tcp 127.0.0.1:8601 repeat 1 default
```

Over HTTP, here to the emulator's address; for the board the address is the one it has on
its Wi-Fi network:

```
python -m odrigctl --http 127.0.0.1:8600 play 2
python -m odrigctl --http 127.0.0.1:8600 on
python -m odrigctl --http 127.0.0.1:8600 off
python -m odrigctl --http 127.0.0.1:8600 brightness 40
python -m odrigctl --http 127.0.0.1:8600 status
python -m odrigctl --http 127.0.0.1:8600 fault
python -m odrigctl --http 127.0.0.1:8600 space
python -m odrigctl --http 127.0.0.1:8600 list
python -m odrigctl --http 127.0.0.1:8600 read 1 0
python -m odrigctl --http 127.0.0.1:8600 catalog
python -m odrigctl --http 127.0.0.1:8600 catalog rebuild external
python -m odrigctl --http 127.0.0.1:8600 catalog page external 3 512
python -m odrigctl --http 127.0.0.1:8600 upload 9 build/hello-bench.odrg
python -m odrigctl --http 127.0.0.1:8600 upload --external build/hello-card.odrg
python -m odrigctl --http 127.0.0.1:8600 remove 9
python -m odrigctl --http 127.0.0.1:8600 remove many 9,10
python -m odrigctl --http 127.0.0.1:8600 ignore 9 1
python -m odrigctl --http 127.0.0.1:8600 order get
python -m odrigctl --http 127.0.0.1:8600 order move 2805384113 9 1
python -m odrigctl --http 127.0.0.1:8600 repeat 1 8
python -m odrigctl --http 127.0.0.1:8600 repeat 1 8 save
python -m odrigctl --http 127.0.0.1:8600 repeat 1 default
```

`status` names the emulator as its host: `"host":"odrig emulator on Darwin arm64"`, with the
system and the processor of the computer.

The tool prints the reply line to standard output:

```
{"ok":true,"on":true,"brightness":40,"playing":"all","animation":2,"fps":50,"error":null,"width":60,"height":6,"seed":null,"left":86399}
```

| Status | Meaning |
|---:|---|
| 0 | The reply has `"ok":true`: for `list` every reply, and for `upload` the reply to `upload end`, or the reply `unchanged` to `upload begin`. |
| 1 | A reply has `"ok":false`. It is printed all the same. An upload the tool had opened is cancelled first. |
| 2 | The command line was not understood, or the file to upload cannot be read: then one line `error: not-found: <detail>` is written to standard error and nothing is sent. |
| 3 | The target could not be reached, or no reply arrived within the time limit. One line `error: unreachable: <detail>` is written to standard error. |

- The line sent is `play <ID>`, `on`, `off`, `brightness <N>`, `status`, `fault`, `space`, `list` or
  `remove <ID>`, followed by a newline. ID and N are sent as they were typed and are not
  checked: `play abc` is sent and the reply says `bad-argument`. Every judgement is the
  command front-end's.
- `list` prints the reply, and for as long as the reply names a `next` position it sends
  `list <next>` and prints that reply too: a line of output for each part of a long show.
  It stops at a reply that is not ok.
- `--timeout SECONDS` is how long the tool waits for a reply; 2 seconds without it.
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

**`--log`** prints the lines of a target's log as they arrive, and sends nothing. It goes
with `--port` or `--tcp` and no command. The board writes its log on the socket marked
COM, as [firmware.md](firmware.md#the-log) describes; the emulator writes none.

```
python -m odrigctl (--port NAME | --tcp ADDRESS) [--timeout SECONDS] --log
python -m odrigctl --port /dev/cu.usbmodem5C831043631 --log
#log 5.012 usb: no computer on the port within 5 s
#log 5.020 usb: host started
```

- Every received line that begins with `#log ` is printed as it arrives, without its line
  end; every other line, a reply or a line of the chip's loader, is passed over. The port
  is opened as for a command, and the connection made as for one.
- It goes on until it is stopped with Ctrl-C, on Windows Ctrl-C or Ctrl-Break, which is
  status 0. A port that goes away,
  or a TCP target that closes the connection, is status 3 with one line
  `error: unreachable: <detail>`. `--log` with `--http` or with a command is status 2.
- A command takes only a reply as its answer, whatever lines of the log come before it.

**`upload ID FILE`** sends an animation as the commands of [commands.md](commands.md),
"Uploading an animation", describe it. The file is one the converter made for the canvas
of the show, here Hello world for the bench file:

```
node converter/odrig.js encode animations/hello.json build/hello-bench.odrg
python -m odrigctl --port build/emulator/serial upload 9 build/hello-bench.odrg
upload: 100% 1138/1138 bytes 1206147 B/s
upload: checking
upload: committed: 1138 bytes sent and checked by the target
{"ok":true}
python -m odrigctl --port build/emulator/serial upload 9 build/hello-bench.odrg
upload: unchanged: the target holds this file already; nothing was sent
{"ok":true,"unchanged":true}
```

The emulator takes a small file in a thousandth of a second, which is the speed shown
here; the board's is in [firmware.md](firmware.md).

- The tool reads the whole file before it sends anything. It sends `upload begin <ID>
  <name> <bytes> <crc32>`, where the name is the last part of the path as it is and the
  CRC-32 is the file's, then the file in pieces of the size the reply names, each as one
  `upload data` line, and then `upload end` with the CRC-32 of the file. ID and the name
  are not checked by the tool.
- A reply `{"ok":true,"unchanged":true}` to `upload begin` ends the upload: the item holds
  this file already, and nothing more is sent. A reply `bad-argument` to it is followed by
  `upload begin <ID> <name> <bytes>` once, for a target older than the CRC-32 there.
- Progress goes to standard error: the percentage, the bytes acknowledged and the total,
  and the speed, which is the bytes acknowledged over the time since `upload begin` was
  answered. A report is written when half a second has passed since the one before, and
  for the last piece; a long upload gives lines such as
  `upload: 45% 613500/1362000 bytes 21400 B/s`. When standard error is a terminal, one line
  is written over again.
- After the last piece the tool writes `upload: checking` once. While the reply to
  `upload end` is `busy`, the target is checking the file, and the tool sends
  `upload end` again every 0.2 seconds. After 600 seconds of `busy` it sends
  `upload cancel`, prints the last reply and exits with status 1.
- After an upload that ended well, one more line on standard error says what it came to:
  `upload: committed: <bytes> bytes sent and checked by the target`, or `upload:
  unchanged: the target holds this file already; nothing was sent`. A reply that was not
  ok leaves the show as it was. When `upload end` went out and no reply came, the line
  `upload: not known: the target did not answer; the same upload again sends nothing when
  the file was installed` comes before the error line: the same command run again finds
  the file unchanged when the target installed it.
- Standard output gets the reply that ended the command: the `{"ok":true}` of
  `upload end`, the reply `unchanged` of `upload begin`, or the first reply that was not
  ok. After such a reply to a piece or to
  `upload end` the tool sends `upload cancel`, unless the reply says that the upload is
  gone. A refused `upload begin` is not followed by a cancel: the upload that is open
  then is someone else's.
- When no reply to an `upload data` line arrives in time, the tool sends the same line
  once more. `bad-offset` for that second line means that the first one was taken, and the
  tool goes on. Without a reply to the second line either, it exits with status 3. No
  other line is sent twice, but for `upload begin` after `bad-argument` as above.
- Through a serial port the tool keeps the port open for the whole upload.

Another program can use the exchanges directly. `odrigctl.client.serial_exchange(port,
data, timeout)` and `odrigctl.client.http_exchange(address, line, timeout)` are one
exchange each: they return the reply or raise `Unreachable`. `serial_exchange` takes a
fourth argument, a function that says which received line is the answer, for a target
whose answer is not a reply of [commands.md](commands.md).
`odrigctl.client.tcp_exchange(address, data, timeout)` is the same exchange over TCP, with
the address as `host:port`.
`odrigctl.client.Session(port=..., http=..., timeout=...)` is several exchanges with one
target: `exchange(line)` returns the reply to a line, and `close()` ends the session. Over
the port it opens the port once, as `serial_exchange` does, and keeps it open, and with
`tcp=...` in the place of `port=...` it does the same with a connection; a line that
arrived whole before a line is sent is no answer to it and is dropped. Over HTTP every
exchange is one request. `odrigctl.content.list_all(session, show)` and
`odrigctl.content.upload(session, item, name, data, progress)` run the two commands that
take more than one exchange through a session; `progress(sent, total, seconds)` is called
after every piece that was acknowledged.

**`catalog`** prints the reply of `catalog`: the state of the catalog of the target's own
storage and of its drive, and a rebuild's progress. **`catalog rebuild internal`** and
**`catalog rebuild external`** start a rebuild of one of them, and **`catalog cancel`** ends
one; each prints the reply, which comes at once: the rebuild goes on in the target, and
`catalog` asked again shows how far it is. **`catalog page internal PAGE OFFSET`** and
**`catalog page external PAGE OFFSET`** print the reply of `catalog page`: up to 512 bytes
of a page of that storage's catalog from the offset, with the storage's generation and the
offset to ask for next. Another operation is status 2, and nothing is sent.

**`upload --external FILE`** sends an animation to the target's drive, a card the core may
write, as `upload ID FILE` sends one with an id: the same pieces, progress and replies, with
`upload begin external <name> <bytes> <crc32>` in the place of `upload begin`, and the reply
of `upload end` gives the id the card's animation got, `{"ok":true,"id":60003}`. A target
whose drive cannot be written answers `read-only`, which is status 1. With the emulator,
`--drive DIR` without `--drive-read-only` is such a drive once `DIR/odrig` has a catalog:
the PC tool's `python3 -m odrig.catalog DIR import` writes one, and so does `catalog rebuild
external`. What the emulator wrote there the PC tool reads, and a change the PC tool makes
there the emulator takes up within ten seconds, when it reads the marker again.

The mapping operation is `get`, `set REV PINS`, or `test on` / `test off`.
The pin list is twenty comma-separated GPIO numbers, in snake order.

```
python -m odrigctl --port build/emulator/serial mapping get
python -m odrigctl --tcp 127.0.0.1:8601 mapping get
python -m odrigctl --http 127.0.0.1:8600 mapping get
```

## Previewing one animation

```
python -m preview FILE [--mapping FILE] [--no-browser] [--core PATH]
```

Shows one finished `.odrg` or `.odrgx` file in the emulator, alone, until Ctrl-C: frames,
a text or a clock. The path may be
absolute or relative, and the file may have any name: it is not changed. `preview` is a
small program of its own, beside the emulator and the command tool, and holds no
converter logic.

1. The converter's `check` reads the file. A file it refuses ends the command with the
   reason, `preview: <file> is refused: bad-magic` for example, before anything starts.
2. The converter packs `shows/preview/show.json`, a show without items at brightness
   255, with the mapping into `build/preview/<process id>/`. The mapping is
   `mapping/legs-20.json`, the installation's 60 x 60, unless `--mapping` names another.
3. The emulator starts on that folder, on port 8600, or on a free port when that is
   taken: the command then says `preview: port 8600 is taken; the page is on <port>`.
   It has a serial port and a line port of its own, so it runs beside another emulator.
4. The file is uploaded as item 1, `preview.odrgx` when its name ends in `.odrgx` and
   `preview.odrg` otherwise, as the operators' app will upload one
   to the board: the core checks it whole. A file of another canvas ends the command with
   `preview: <file> is 60 x 60, and the mapping <mapping> is 60 x 6`.
5. `page: <address>` is printed and the page opens in the default browser, unless
   `--no-browser` is given. The playlist is the one animation, in loops.

Ctrl-C, on Windows Ctrl-C or Ctrl-Break, or a termination, stops the emulator and removes
the folder; the command then ends with 0. A refusal ends it with 1 and one line on
standard error, with nothing left running. Without the core's library, or without Node.js,
it says which step of [getting-started.md](../agent/getting-started.md) is missing and
starts nothing.

## Record mode

```
python -m emulator SHOW_DIR --record OUT --seconds S [--script FILE] [--core PATH] [--storage BYTES]
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
| `--storage BYTES` | The size of the storage the core is told of, as in real time. |

Recording the same folder with the same length and the same script twice gives the same
bytes. A script may hold the content commands of [commands.md](commands.md): they act on
the folder as in real time, so the folder is changed afterwards, and "the same folder"
means a folder with the same files as before the first recording. The emulator gives the
core nothing of its own in this mode: only the requests for a refresh and the commands of
the script. The options `--port`, `--serial-link`, `--tcp-port` and `--verbose` belong to
real time and do not go with `--record`.

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
reply 1010 {"ok":true,"on":false,"brightness":128,"playing":3,"animation":1,"fps":50,"error":null,"width":60,"height":6,"seed":null,"left":86399}
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
node converter/odrig.js pack --show build/dense/show.json --mapping mapping/legs-20.json \
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
   playing playlist, animation 2. Send `python -m odrigctl --http 127.0.0.1:8600 off`: the header
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
    `build/example-broken`, remove `show.json` from the copy and start
    `python -m emulator build/example-broken`. *Seen:* a band under the header shows
    `show-missing`, in the LEDs view and in the mapping view, and every LED is
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

### What has been checked on Windows

The work on Windows was checked on one computer: Windows 11, with Python 3.14.2 and, in a
fresh clone, Python 3.12.10; GCC 16.1 of WinLibs and Microsoft's compiler 14.50; and
Node.js 24.13. The page was read in Chrome 154 and in Edge 151, both without a window, by a
program that drives the browser through its remote-debugging port, as on the Mac. The
program and its screenshots are in `scratch/`, which git ignores.

- **The suites.** With Python 3.14: the converter suite, 622 tests; the core suite, 246,
  and with Microsoft's compiler 246 of which 10 are skipped; the suite of the emulator and
  the command tool, 450 of which 15 are skipped; the onboarding suite, 75. In a fresh
  clone, made with git set to convert line endings and set up with Python 3.12 as the
  getting-started page says, no file had a carriage return and the same four suites
  passed, after one test of a time limit was made to allow for the clock of that Python,
  which counts in steps of 1/64 of a second.
- **The demo show.** Packed with the commands of Windows, `dvd.odrg` has 1,052 bytes and
  `hello.odrg` 1,213, three more than in the table above, which was made with another
  zlib. Record mode prints the reply the getting-started page shows. The emulator prints
  its `page:` and its `tcp:` line. `status`, `play 2`, `brightness 40`, `play 3` and
  `play 99` gave the replies of [commands.md](commands.md) over HTTP and over the line
  port, with the exit statuses 0 and 1, and each stood in the log of the page as `http` or
  `tcp`.
- **The page.** In both browsers the LEDs view shows HELLO WORLD upright in the rows 28 to
  33 and the twenty legs in their colours, and the mapping view the board beside the
  canvas with a line from every pin. `core` was 50 and `page` 49 to 51 in every second
  read: eight seconds in the LEDs view and six in the mapping view, in a window of
  1280 x 800 in both browsers and of 756 x 900 in Chrome. Neither browser reported an
  error of the page. The header shows `tcp 127.0.0.1:8601` in the place of the serial port.
- **An import.** A GIF of 40 x 40 with 36 pictures and a video of three seconds, H.264 at
  25 pictures a second, were imported for the target, checked, packed with the bouncing
  square and played, as the animation guide describes. `core` and `page` stayed at 50.
- **A show of 113 animations**, made from GIFs with the converter on another computer,
  was read by the core without a complaint and played, in a cycle and one by one.
- **A serial port.** The computer has a port `COM1` with nothing connected. The command
  tool opened it; afterwards the system reported 115200 baud, 8 data bits, DTR off and RTS
  off for it, where it had reported 1200, 7, on and on; and the tool ended with status 3,
  `no reply within 1 seconds`. The port was set back.

What is left on Windows:

- The 22 steps of the list above were not gone through one by one there. What is said
  above was seen; the pointing of step 18 and the invalid show of step 22 were not looked
  at on Windows, and the suite covers both.
- A person at a screen has not gone through the list on Windows either, and Python 3.10
  and 3.11 were not installed on that computer.
- The two lists under [On Windows](#on-windows): what only the first computer can see, and
  what needs a board on a Windows computer.

After `master` brought the content commands and the converter in JavaScript, on the merged
branch and with Python 3.14: the suite of the Python package, 638 tests; the core suite,
364, and with Microsoft's compiler 364 of which 10 are skipped; the suite of the emulator
and the command tool, 523 of which 17 are skipped; the onboarding suite, 81. `space`,
`list`, `remove` and `upload` are part of those suites and run over the line port. The
converter's own suite, `npm test --prefix converter`, does not pass on Windows: of 499
tests 288 pass and 208 fail, 73 of them with one error, where the suite starts a helper in
Python that is written for macOS; the others were not looked into. That is not mended here;
it was afterwards, outside seed 11: "The converter on Windows" at the end of
[drifts.md](drifts.md).

## Live output assignments

The shared app's Mapping screen reads and saves the target's twenty-snake pin
assignment through the same mapping commands as serial and TCP clients. A committed
save updates the core binding's leg metadata, emits a `mapping` stream event and
refreshes the page's Mapping view without restarting the emulator. The event carries
one complete array of `[leg, pin, LED count]` entries. New connections receive current
routing in their hello event. The mapping file endpoint returns the committed file.

For a serial client, `python3 -m odrigctl --port build/emulator/serial mapping get`
reads the assignment. Use `mapping set REV PINS` to save the complete comma-separated
pin list, `mapping test on` or `mapping test off` for the packaged diagonal, and
`mapping test snake N` for the test of snake N.

`order get` prints the saved playlist order, a reply for each part, and
`order move REV ID BEFORE` moves one animation, with `BEFORE` an id or `end`; the tool
sends the words as they are typed. The emulator keeps the order in `order.txt` of its show
folder, as the board does in its storage, and plays its playlist in that order.

`repeat ID N` gives the turn in progress of an animation `N` loops, `repeat ID N save`
keeps them for every later turn and `repeat ID default` brings its own count back; the
tool sends the words as they are typed. The emulator keeps the saved repeats in
`repeats.txt` of its show folder through its host, as the board does in its storage: it
has no code of its own for them.

The shared core handles `ignore ID 0|1` and `remove many IDS` unchanged on HTTP, serial and TCP; odrigctl accepts both. Space reports internal quota and optional external capacity from the mounted folder filesystem. External files are changed only on a drive with a catalog that the emulator may write (`--drive` without `--drive-read-only`).
