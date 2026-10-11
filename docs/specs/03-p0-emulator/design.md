# Design: Emulator (seed 03)

## Overview

The emulator is a Python package named `emulator` at the repository root, run as
`python -m emulator SHOW_DIR`. It loads the core as a shared library through `ctypes`, gives
it the files of the show folder, and asks it for a refresh every 20 ms. It carries command
lines to the core from a pseudo-terminal and from HTTP, and sends every refresh, every
command and the status to a web page over one server-sent event stream. The page draws the
LEDs, the command log, the status and the mapping view. A record mode runs the same core on
a virtual clock and writes every refresh to a file.

The command tool is a second small package, `odrigctl`, run as `python -m odrigctl`.

Both packages use only the Python standard library. Neither is part of the package `odrig`:
seed 01's suite forbids network and serial modules there.

Decisions taken where the seed and the documents left a point open are listed in
`docs/drifts.md` under "Seed 03".

## What this design relies on

Seeds 01 and 02 are not implemented when this is written. This design uses the following
from their `design.md` files, and a task that finds one of them different records the
difference in `docs/drifts.md` and follows the real code.

| From | Used here |
|---|---|
| Seed 01 | `python -m odrig pack --show S --mapping M --sources DIR --out DIR [--uncompressed]`; the generators `python -m odrig.generators.hello_world`, `.dvd_bounce` and `.dense`, each taking `OUT --mapping MAPPING`, `dense` also `--seconds N`; `shows/example/show.json`, `animations/hello.json`, `animations/dvd.json`; `odrig.mapping.read`; the error line `error: <reason>: <detail>`; `/build/` in `.gitignore`. |
| Seed 02 | `core/include/odrig_core.h` exactly as its design prints it; `core/Makefile` with sources found by `$(wildcard src/*.cpp)` and output in `core/build/`; the rules of use of the host interface; the reference player in `tests/core/support.py`, which answers the input lines `poll <ms>` and `line <ms> <text>` with `refresh`, `data <leg> <hex>`, `idle` and `reply <json>` lines. |

## Repository layout

```
emulator/
  __init__.py
  __main__.py            runs app.main()
  app.py                 arguments, start order, the two printed lines, exit statuses
  failure.py             Failure(reason, detail) and the reason names
  binding.py             ctypes declarations for odrig_core.h; the only module that imports ctypes
  host.py                the files of a show folder, as the core asks for them
  engine.py              owns the core and its lock; the real-time loop
  hub.py                 hands refreshes, log entries and status to the page connections
  serialport.py          the pseudo-terminal, its link and its reader
  httpd.py               the HTTP server: page files, /odrig, /events, /show/mapping.json
  record.py              record mode: script reader, virtual clock, record file writer
  recfile.py             reader and writer of the record file format
  web/
    index.html
    style.css
    board.js             the board's two pin rows
    layout.js            positions, paths, colours, sizes: no browser needed
    view.js              drawing: canvas for the LEDs, SVG for everything else
    app.js               the event stream, the status, the log, the two views
odrigctl/
  __init__.py
  __main__.py            runs cli.main()
  cli.py                 arguments, the printed reply, exit statuses
  client.py              serial and HTTP exchange
shows/
  demo-10/
    show.json            the ten-leg demo show
tests/
  emulator/
    __init__.py          builds the core's shared library once
    test_*.py            the suite of this seed
    support.py           starts the emulator, packs shows, talks to the port and to HTTP
    js/
      dump_layout.js     prints what layout.js computes for a mapping, for the JavaScript shell
docs/
  emulator.md
```

`core/Makefile` gains one target, `shared`. No file of `core/src` or `core/include` changes.

The folder `tools/` holds untracked proof-of-concept scripts (`wled.py`, `wled_send.py`,
`wled_deploy.py`). They speak WLED's own serial protocol. No task moves, edits, deletes or
stages them; `wled_send.py`, the generic line sender, sends any line to any serial port and
works against the emulator's port as it is.

## Command line

```
python -m emulator SHOW_DIR [--port N] [--serial-link PATH] [--core PATH] [--verbose]
python -m emulator SHOW_DIR --record OUT --seconds S [--script FILE] [--core PATH]
```

| Option | Meaning | Without it |
|---|---|---|
| `--port N` | The page's port on 127.0.0.1; 0 takes any free port. | 8600 |
| `--serial-link PATH` | Where the link to the port is made. | `build/emulator/serial` under the repository root |
| `--core PATH` | The core's shared library. | `core/build/libodrig_core.dylib` under the repository root |
| `--verbose` | Prints the core's diagnostic lines to standard error. | They are kept, not printed. |
| `--record OUT`, `--seconds S`, `--script FILE` | Record mode. | Real-time mode. |

The repository root is the folder that holds the package `emulator`, so the defaults do not
depend on the folder the command is run from. There is no option for a size and none for an
address: the canvas comes from `mapping.json`, and the address is always 127.0.0.1.

## Running the core

### The shared library

`make -C core shared` builds `core/build/libodrig_core.dylib` from `core/src/*.cpp` with
the compiler flags of the static library, linked with `-dynamiclib`. The library exports the
`odrig_core_*` functions and nothing else of interest. The emulator loads this file; the
option `--core PATH` names another one.

The emulator does not build the library. When the file is missing or does not load, it stops
with `core-not-built` and names the command.

### `binding`

`binding.py` declares the two structs, the callback types and the eight functions of
`odrig_core.h` with `ctypes`:

```python
ALLOC = CFUNCTYPE(c_void_p, c_void_p, c_size_t)
OPEN  = CFUNCTYPE(c_int, c_void_p, c_char_p)
READ  = CFUNCTYPE(c_int32, c_void_p, POINTER(c_uint8), c_size_t)
CLOSE = CFUNCTYPE(None, c_void_p)
LOG   = CFUNCTYPE(None, c_void_p, c_char_p)
REPLY = CFUNCTYPE(None, c_void_p, POINTER(c_char), c_size_t, POINTER(c_char), c_size_t)

class Core:
    def __init__(self, library_path, host): ...   # loads the library, calls odrig_core_begin
    legs: tuple[Leg, ...]                          # Leg(leg, pin, led_count), in the core's order
    led_bytes: int                                 # 3 * the sum of led_count
    def poll(self, now_ms: int) -> bool
    def frame(self) -> bytes                       # every leg's rgb, joined in the core's order
    def command(self, now_ms: int, line: bytes) -> bytes
    def feed(self, now_ms: int, data: bytes) -> list[tuple[bytes, bytes, bool]]
                                                   # (line, reply, cut) for every finished line
    def error(self) -> str | None
```

`frame` copies `led_count * 3` bytes from each leg's `rgb` with `ctypes.string_at`. `feed`
collects the calls of its `on_reply` function; `cut` is true when the reply is
`line-too-long`, the only case in which the kept line is shorter than what arrived.
`command` passes a reply buffer of `ODRIG_REPLY_MAX` bytes. If `odrig_core_begin` returns
NULL the emulator stops with `core-not-built` and the detail `the core could not start`.

`Core` makes the five functions of `odrig_host` and keeps a reference to each for as long
as it lives. Its `alloc` returns the address of a new `ctypes` byte array of the asked size
and keeps the array in a list, so the memory is never released while the core is in use.
Its `open`, `read`, `close` and `log` call the methods of the host object below; `read`
copies the returned bytes into the core's buffer with `ctypes.memmove`.

### `host`

`FolderHost(folder)` is plain Python and knows nothing of `ctypes`:

| Method | Behaviour |
|---|---|
| `open(name) -> int` | Refuses a name that holds a path separator (-1). Returns 0 when the folder has no file of that name, 1 after opening it for reading in binary mode, -1 on any other error. |
| `read(capacity) -> bytes or None` | Up to `capacity` bytes of the open file, empty at its end, `None` on an error, which the core is told as -1. |
| `close()` | Closes the open file. |
| `log(text)` | Appends the text to a list of at most 100 lines. `--verbose` also prints each line to standard error. |

### `engine`

`Engine(core, hub)` is the only caller of the core once it has started. It holds one
`threading.Lock`; every method takes it for the length of one call to the core, which makes
the calls strictly one after another whichever thread asks. The timestamp of a call is read
after the lock is taken, so timestamps reach the core in order.

```python
class Engine:
    def tick(self) -> None                 # poll; on a refresh, hand ms and frame to the hub
    def line(self, data: bytes, transport: str) -> bytes     # one line (HTTP)
    def feed(self, data: bytes, transport: str) -> bytes     # bytes (serial); all replies joined
    def refresh_status(self) -> None       # status for the page; not logged
```

`line` and `feed` hand a log entry to the hub for every finished line and then call
`refresh_status`. `refresh_status` sends the line `status` to the core and hands the reply
to the hub. The real-time loop also calls it once a second.

**Clock.** `now_ms` is `(time.monotonic_ns() - start_ns) // 1_000_000`, with `start_ns`
taken when the engine is made.

**Real-time loop** (`RealTime`, one thread). The first `tick` is made before the page
address opens; its timestamp is the power-on moment `t0`, which the engine keeps. Then, for
ever: compute the next grid time `t0 + ((now - t0) // 20 + 1) * 20`, sleep until 0.2 ms
after it, call `tick`. A late wake-up simply polls with the current time; the core skips
the grid times that were missed. Nothing is replayed.

## The virtual serial port

`serialport.py`:

1. `os.openpty()` gives the two ends of a pseudo-terminal. The emulator keeps both open for
   its whole life, so the port stays in place while programs open and close it.
2. `tty.setraw` on the far end switches off echo, line editing and every translation of
   newlines and carriage returns.
3. The link path's folder is created if needed. A symbolic link already at the path is
   removed. Anything else at the path, or a failure of `os.symlink`, is `serial-unavailable`.
   The link points at `os.ttyname` of the far end, for example `/dev/ttys012`.
4. A reader thread blocks in `os.read` on the near end, passes each chunk to
   `Engine.feed(chunk, "serial")` and writes the returned replies back with `os.write`. An
   `OSError` from `os.read` is followed by a pause of 50 ms and another try.
5. At exit the link is removed if it still points at this pseudo-terminal.

A pseudo-terminal has no speed and no modem lines. Setting a speed succeeds and changes
nothing. A request to change DTR or RTS may fail with an error; the command tool ignores
that error, which is what makes the same tool work on both targets.

## The HTTP server

`httpd.py` uses `http.server.ThreadingHTTPServer` bound to `("127.0.0.1", port)`, with
daemon threads, HTTP/1.1 and request logging switched off. A failure to bind is
`address-in-use`.

| Request | Answer |
|---|---|
| `GET /` | `web/index.html`. |
| `GET /<name>` for a file of `emulator/web/` | That file. The table of names is made once at start by listing the folder; nothing outside it can be asked for. |
| `GET /show/mapping.json` | The bytes of `mapping.json` in the show folder, `application/json`; 404 when the file does not exist. |
| `GET /events` | The event stream. |
| `POST /odrig` | The command transport. |
| Any other method on `/odrig` | 405, `Allow: POST`, no body. |
| Anything else | 404. |

The path is what comes before a `?`. Page files are sent with `Cache-Control: no-store`
and the content types `text/html; charset=utf-8`, `text/css`, `text/javascript` and
`application/json`.

### `POST /odrig`

1. `Content-Length` missing, not a whole number or below 0: status 411, the core is not
   called.
2. Read the whole body. Keep its first 128 bytes.
3. `reply = engine.line(kept, "http")`.
4. Answer 200 with `Content-Type: application/json`,
   `Access-Control-Allow-Origin: *` and the reply bytes as the core returned them, newline
   included.

The request's content type is not read. A body of more than 66 bytes is always answered
with `line-too-long` by the core, so keeping 128 bytes never changes a reply. The firmware
of seed 04 does the same, and its web server adds the same `Access-Control-Allow-Origin`
header to every response.

### `GET /events`

The response has `Content-Type: text/event-stream`, `Cache-Control: no-store`, no length,
and stays open. Each event is written and flushed at once. The stream has four kinds of
event:

```
event: hello
data: {"show":"/abs/path/of/show","page":"http://127.0.0.1:8600/","serial":"/abs/path/build/emulator/serial","legs":[[1,1,180],[2,2,180]],"t0":3,"error":null}

event: log
data: {"seq":17,"ms":123456,"time":"14:03:22.512","transport":"serial","line":"play 2","cut":false,"reply":"{\"ok\":true}"}

event: status
data: {"ok":true,"on":true,"brightness":128,"playing":3,"animation":1,"fps":50,"error":null}

event: frame
data: 123460 <base64 of the refresh>
```

- `hello` comes first on every connection. `legs` lists `[leg, pin, led_count]` in the
  core's order; `t0` is the power-on moment; `error` is `odrig_core_error`.
- `log`: `ms` is the timestamp given to the core, `time` the local time of day, `line` the
  kept bytes of the line as text, with every byte outside printable ASCII written as
  `\xNN`, and `reply` the reply without its newline.
- `status` carries the core's reply to `status`, unchanged.
- `frame`: the timestamp of the refresh, a space, and the refresh in base64: every leg's LED
  bytes in the order of `legs`, `led_bytes` bytes in all.

`hub.py` keeps the last 500 log entries and the latest status. A new connection gets
`hello`, the kept entries, the latest status, and then everything that happens. Each
connection has its own queue for log and status events, which are never dropped, and one
slot for the newest refresh, which a newer refresh replaces. A connection that has had
nothing to send for 15 seconds is sent the comment line `: keep-alive`. A failed write
ends the connection's thread.

## Record mode

`python -m emulator SHOW_DIR --record OUT --seconds S [--script FILE]`

`record.py` makes the core on the show folder, with no page, no port and no thread, and
runs this loop with `T = floor(S * 1000 / 20)` ticks:

```
for k in 0 .. T - 1:
    t = 20 * k
    for every script command not yet sent whose time is <= t, in file order:
        reply = core.command(command.time, command.line)
        print("reply", command.time, reply)
    produced = core.poll(t)
    write the tick record
```

`--seconds` is a decimal number; the length in milliseconds is rounded to the nearest whole
number. A length that gives no tick is `bad-length`.

**Script.** A UTF-8 text file. Empty lines and lines starting with `#` are skipped. Every
other line is a time in decimal digits, one space, and the command line, which is passed to
the core as it is. `bad-script` covers: a file that cannot be read, a line without digits
and a space at its start, a time smaller than the one before it, and a time of `20 * T` or
more. The whole script is checked before the core is started.

**Record file.** Binary, all integers little-endian:

| Offset | Size | Field | Value |
|---:|---:|---|---|
| 0 | 4 | Magic | The bytes `4F 44 52 52` ("ODRR"). |
| 4 | 1 | Version | 1. |
| 5 | 1 | | Zero. |
| 6 | 2 | Leg count | L, as the core reports it. |
| 8 | 4 | Tick length | 20. |
| 12 | 4 | LED bytes | B: 3 times the number of LEDs of all legs. |
| 16 | 8 * L | Legs | For each leg: leg number (2), pin (2), number of LEDs (4). |

Then one tick record for every tick, each `9 + B` bytes: the tick's time in milliseconds
(8), a byte that is 1 when the core produced a refresh and 0 when it did not, and B bytes
of LED data, each leg's bytes in chain order, the legs in header order, all zero when no
refresh was produced. The number of ticks is the rest of the file divided by `9 + B`.

The file is written to `OUT.part` and moved into place with `os.replace` at the end.
`recfile.py` has `write` and `read`; the suite uses `read`.

## The page

The page is plain files: no framework, no build step, nothing fetched from another host.
`layout.js` and `board.js` are ordinary scripts that define one global object each and use
nothing a browser provides, so the JavaScript shell of macOS can run them for the tests.

### Structure

```
+--------------------------------------------------------------------------------+
| odrig emulator   show: build/example-show   serial: build/emulator/serial      |
| on  brightness 128  playing 3  animation 1  core 50 fps  page 50 fps           |
+--------------------------------------------------------------------------------+
| [ LEDs ] [ Mapping ]                                 leg 2, pin 2, LED 61 (1,2)|
|                                                                                |
|   the drawing: LEDs view or mapping view                                       |
|                                                                                |
+--------------------------------------------------------------------------------+
| time          via     command            reply                                 |
| 14:03:22.512  serial  play 2             {"ok":true}                           |
| 14:03:25.001  http    brightness 300     {"ok":false,"error":"bad-argument"}   |
+--------------------------------------------------------------------------------+
```

- The header shows what `hello` and the latest `status` carry, the page's own count of
  refreshes drawn in the last full second, and whether the event stream is connected.
- A reason from `hello` or from `status` is shown in a red band under the header in both
  views, with the core's text unchanged. When `legs` is empty, which is what an invalid
  mapping gives, the page draws no LEDs and no mapping view, only the band, the status and
  the log.
- The log is a table that grows downward and keeps the newest line in sight. A cut line
  ends in `…`.
- The readout at the right of the tabs shows what the pointer is on.
- Colours: page background `#101214`, panels `#181b1f`, text `#d8dee9`, a dark LED
  `#2a2f36` as an outline. Text is the system font at 13 px; numbers, the log and the
  readout use the system's fixed-width font.

`app.js` opens `EventSource("/events")`. On `hello` it fetches `/show/mapping.json`, calls
`OdrigLayout.read`, and builds the drawing. `EventSource` connects again by itself when the
emulator restarts, and a new `hello` rebuilds everything.

### `board.js`

```js
var OdrigBoard = {
  name: "ESP32-S3 N16R8",
  left:  ["3V3","3V3","RST","4","5","6","7","15","16","17","18","8","3","46","9","10",
          "11","12","13","14","5Vin","GND"],
  right: ["GND","TX","RX","1","2","42","41","40","39","38","37","36","35","0","45","48",
          "47","21","20","19","GND","GND"]
};
```

Both lists run from the antenna end to the USB end, as in the drawing of
`docs/mapping.md`. A label made of digits is the GPIO of that number. The board's pin order
is a fact of the hardware and is not in `mapping.json`; a test compares these lists with the
drawing in `docs/mapping.md`.

### `layout.js`

One global object, `OdrigLayout`, with pure functions. Canvas coordinates are those of
`docs/format.md`: x from 1 to W, y from 1 to H.

| Function | Result |
|---|---|
| `read(text)` | The mapping: `width`, `height` (the number of rows of all legs) and `legs`, each with `leg`, `pin`, `first_led`, `rows` and `count = width * rows.length`. |
| `position(m, pin, n)` | `[x, y]` of LED n of the leg on that pin, or `null`. With `r = floor((n - 1) / W)` and `i = (n - 1) mod W`: `y = rows[r]`; the row starts on the `first_led` side when r is even and on the other side when r is odd; `x = W - i` when it starts on the right and `1 + i` when it starts on the left. |
| `find(m, x, y)` | The leg index and LED number at a canvas position, or `null`. Used for pointing. |
| `rows(m, i)` | For each row of leg i in chain order: `y`, the side it starts on, and the LED numbers at its start and its end. |
| `path(m, i)` | The corner points of leg i's chain in canvas coordinates, two for each row, in chain order. |
| `colour(i)` | The colour of the leg at index i of the file: entry `i mod 12` of the list below. |
| `side(m)` | `"right"` or `"left"`: the side of the canvas on which most legs have their first LED; `"right"` when equal. The board is drawn on this side. |
| `place(board, pin)` | The row of pins (`"left"` or `"right"`) and the place in it of the pad for that GPIO, or `null` when the board has no such pad. |
| `tracks(m)` | For each leg, its track in the channel between the board and the canvas: the legs ordered by the y of their first row, highest first, get tracks 0, 1, 2 and so on, track 0 nearest the canvas. |
| `fit(m, width, height, board)` | The cell size in pixels and the place of every part, for a drawing area of that size, with or without the board. |
| `shown(v)` | The display value of a colour value: `round(255 * (v / 255) ^ (1 / 2.2))`. |

Leg colours, readable on the dark background and apart from each other:

```
#ff6b6b #ffa94d #ffd43b #a9e34b #51cf66 #38d9a9 #3bc9db #4dabf7 #748ffc #b197fc #f783ac #ced4da
```

`fit` chooses `cell = floor(min(free width / W, free height / H))`, between 4 and 28
pixels, where the free width is the area's width less the two gutters, the label column
and, in the mapping view, the channel and the board.

### LEDs view

```
            x=1                                              x=60
 leg 1    | y=6    60  o o o o o o o o o o o o o o o o o o o    1 |
 pin 1    | y=5    61  o o o o o o o o o o o o o o o o o o o  120 |
          | y=4   180  o o o o o o o o o o o o o o o o o o o  121 |
 leg 2    | y=3    60  o o o o o o o o o o o o o o o o o o o    1 |
 pin 2    | y=2    61  o o o o o o o o o o o o o o o o o o o  120 |
          | y=1   180  o o o o o o o o o o o o o o o o o o o  121 |
```

- The LEDs are drawn on one `<canvas>`. LED n of a pin is a filled circle of radius
  `0.38 * cell` centred at `((x - 0.5) * cell, (H - y + 0.5) * cell)` for the `[x, y]` that
  `position` gives. Its fill is `rgb(shown(r), shown(g), shown(b))` of its three bytes. An
  LED whose three bytes are 0 is drawn as an outline.
- For each `frame` event the page splits the bytes by the `led_count` of `legs`, keeps
  them as the newest refresh, and asks for one redraw with `requestAnimationFrame`. A
  redraw paints the newest refresh once. The page counts the refreshes it painted in each
  full second.
- Everything else is one `<svg>` laid over the canvas: for each leg, a bracket over its
  rows in the leg colour with `leg N` and `pin P`; `y=` labels; and the LED numbers at the
  two ends of each row, from `rows`. Rows of one leg that are not next to each other get
  one bracket for each run of neighbouring rows.

### Mapping view

The mapping view is the LEDs view with the board and the wiring added and a smaller cell
size. With the board on the right:

```
  labels and canvas, as in the LEDs view        channel        board
                                                           +-----------+
 leg 1 | y=30   60 o o o o <------------   1 |--+          |  antenna  |
 pin 1 | y=29   61 o o o o ------------> 120 |  |      3V3 o           o GND
       | y=28  180 o o o o <------------ 121 |  |      3V3 o           o TX
 leg 2 | y=27   60 o o o o <------------   1 |-----+   RST o           o RX
 pin 2 | y=26   61 ...                       |  |  +-----------------( 1 ) leg 1
                                             |  +--------------------( 2 ) leg 2
                                                           |  ESP32-S3 |
                                                           | [USB][USB]|
                                                           +-----------+
```

- **Board.** An SVG group: a rounded body, the antenna area at the top, the module with
  the text of `OdrigBoard.name`, two USB sockets at the bottom, and one pad for each entry
  of `left` and `right`, 16 pixels apart, with its label printed inside the body next to
  the pad. A pad that a leg uses is filled with the leg colour and has `leg N` printed
  outside the board, as in `docs/mapping.md`. The other pads are grey.
- **A pin that is not on the board.** A leg whose pin `place` does not find gets a pad of
  its own under the board, labelled `GPIO <pin>`.
- **Lines.** The channel has one vertical track for each leg, 9 pixels apart, from
  `tracks`. A leg's line leaves its pad, runs level to its track, along the track to the
  height of the leg's first row, and level to the first LED, where it ends in an arrow
  head. A line from a pad on the far row of pins passes behind the board body, which is
  drawn over it at 85 percent opacity. When the first LED is on the side of the canvas
  away from the board, the last level part runs in the gap above the leg's first row,
  between the rows of dots, to the far edge and turns down to the LED. Lines are 2 pixels
  wide, in the leg colour, with rounded corners.
- **Paths.** For each leg a polyline through the points of `path`, in the leg colour at 60
  percent opacity, drawn over the dots: along each row through the centres of its LEDs,
  with an arrow head at the row's end, and joined to the next row by a short piece outside
  the canvas edge.
- **Outline.** Each run of neighbouring rows of a leg has a rounded outline in the leg
  colour.
- **Pointing.** Every part of a leg carries the leg's index: its pad, its `leg N` text,
  its line, its path, its outlines, its bracket and labels. When the pointer enters one of
  them, or an LED of the leg, the drawing gets the class of that leg: the leg's parts are
  drawn at full opacity and double width, the parts of all other legs at 20 percent, and a
  veil of 50 percent black covers the rows of the other legs. The readout shows
  `leg N, pin P`, and over an LED also `LED n (x,y)`.

The LEDs in this view are the same canvas and the same code as in the LEDs view.

For the ten-leg mapping in a window of 1280 x 800 the mapping view comes to a cell of 12
pixels (a canvas of 720 x 360), a channel of 100 pixels and a board about 190 pixels wide
and 420 high; the LEDs view comes to a cell of 17 pixels.

## The command tool

```
python -m odrigctl (--port NAME | --http ADDRESS) [--timeout SECONDS] play ID
python -m odrigctl (--port NAME | --http ADDRESS) [--timeout SECONDS] on
python -m odrigctl (--port NAME | --http ADDRESS) [--timeout SECONDS] off
python -m odrigctl (--port NAME | --http ADDRESS) [--timeout SECONDS] brightness N
python -m odrigctl (--port NAME | --http ADDRESS) [--timeout SECONDS] status
```

`cli.py` builds the line from the command name and, for `play` and `brightness`, the one
argument as typed. It prints the reply line and exits with 0 or 1 by the reply's `ok`. An
`Unreachable` from the client becomes `error: unreachable: <detail>` on standard error and
status 3. `argparse` gives status 2.

`client.py`:

```python
class Unreachable(Exception): ...

def is_reply(line: bytes) -> bool                 # a JSON object that has a member "ok"
def serial_exchange(port: str, data: bytes, timeout: float, accept=is_reply) -> bytes
def http_exchange(address: str, line: bytes, timeout: float) -> bytes
```

**`serial_exchange`**, in this order, which is the order of the proof-of-concept sender
that is known not to reset the board:

1. `os.open(port, O_RDWR | O_NOCTTY | O_NONBLOCK)`.
2. `termios`: raw, 8 data bits, no parity, receiver on, modem status ignored, 115200 in
   both directions, `VMIN` 0 and `VTIME` 0.
3. Lower RTS with `TIOCMBIC`, then lower DTR with `TIOCMBIC`. An `OSError` from either is
   ignored.
4. Wait 0.2 seconds, then read and discard what arrives for 0.1 seconds.
5. Write the data.
6. Read until a complete line for which `accept` is true has arrived, and return it without
   its newline. Lines that are not accepted are dropped. No such line within the time
   limit, or any `OSError` before step 6, raises `Unreachable`.

`accept` is a parameter so that seed 04 can use the same function for WLED's handshake,
whose answer is not JSON.

**`http_exchange`**: ADDRESS is `host`, `host:port`, or either with `http://` in front and
an optional `/` at the end. It sends `POST /odrig` with `http.client`, the line with its
newline as the body, and the header `Content-Type: application/octet-stream`. A response
with status 200 gives its body without the final newline. Any other status, a refused
connection or a timeout raises `Unreachable`.

The content type is `application/octet-stream` because the web server library of the board
takes bodies of the types `application/x-www-form-urlencoded` and, in some cases,
`text/plain` apart as form fields before any handler sees them (seed 04's design gives the
details). With `application/octet-stream` the board passes every body on unchanged, as the
emulator does with any type.

## The ten-leg demo show

`shows/demo-10/show.json`, tracked:

```json
{
  "version": 1,
  "brightness": 128,
  "items": [
    {"id": 1, "file": "hello.odrg"},
    {"id": 2, "file": "dvd.odrg"},
    {"id": 3, "cycle": [1, 2], "seconds": 15}
  ],
  "start": 3
}
```

Its sources are generated, not tracked: for the 60 x 30 canvas the two JSON frames files
come to about 10 MB (Hello world 255 frames, DVD bounce 1,624 frames of 1,800 pixels each).
They are written into `build/`, which is ignored:

```
mkdir -p build/demo-10/sources
python -m odrig.generators.hello_world build/demo-10/sources/hello.json --mapping mapping/legs-10.json
python -m odrig.generators.dvd_bounce  build/demo-10/sources/dvd.json   --mapping mapping/legs-10.json
python -m odrig pack --show shows/demo-10/show.json --mapping mapping/legs-10.json \
    --sources build/demo-10/sources --out build/demo-10/show
python -m emulator build/demo-10/show
```

The canvas size comes from `mapping/legs-10.json` in every one of these commands; none
names 60 or 30. Seed 01's generators centre Hello world on the canvas and let the square of
DVD bounce use all of it.

## Start, stop and failures

`app.main` does these steps in order, and a failure at any step undoes the earlier ones:

1. Parse the arguments (status 2 on a usage error).
2. `SHOW_DIR` is an existing folder, or `not-a-folder`.
3. In record mode: check the length and the script, then record, then exit.
4. Load the library and start the core (`core-not-built`). A show the core calls invalid
   is not a failure: the emulator goes on.
5. Make the engine and its first `tick`.
6. Create the port and its link (`serial-unavailable`).
7. Bind the page address (`address-in-use`).
8. Print the two lines and flush standard output.
9. Start the reader thread, the real-time loop and the server.
10. Wait for `SIGINT` or `SIGTERM`; then stop the server and the loop, remove the link and
    exit with status 0.

`failure.Failure(reason, detail)` is turned into `error: <reason>: <detail>` on standard
error and status 1. Bytes that a client sends are never an error of the emulator: every
line goes to the core and gets the core's reply. A broken connection of a page or a client
ends only that connection. A programming error ends the emulator with a traceback.

## Testing strategy

The suite is `unittest`, in `tests/emulator/`, run from the repository root with

```
python3 -m unittest discover -s tests/emulator -t .
```

`tests/emulator/__init__.py` runs `make -C core shared` once when the package is imported
and fails with make's output when that fails, so the one command builds what it tests.
Discovery picks up every `test_*.py`; no command, script or document lists test files.

`support.py` packs shows into temporary folders with `python -m odrig pack`, starts the
emulator as a child process on port 0 with a link in the temporary folder, reads its two
lines, and ends it with `SIGTERM`. It also wraps seed 02's reference player
(`tests.core.support`) so that a test can ask for the LED data of every leg at a list of
timestamps with a list of timed commands.

| File | What it proves |
|---|---|
| `test_binding.py` | The library loads; `binding.py` declares every function that `core/include/odrig_core.h` declares and no other; the legs of the example show; `poll`, `frame`, `command`, `feed` and `error` on the example show and on an empty folder. |
| `test_record.py` | 60 seconds of the example show equal the reference at every tick, with the cycle changing at 15, 30 and 45 seconds; a script with every command gives the reference's replies and LED data; the flipped mapping of Requirement 11 criterion 8, leg by leg and row by row; an invalid mapping gives a file with no legs and no refresh; two runs give identical bytes; 600 seconds of a small show are recorded in under 60 seconds; each `bad-script` and `bad-length` case leaves no file; no `.part` file remains. |
| `test_start.py` | The two printed lines; exit status 0 and the link gone after `SIGTERM`; `not-a-folder`; `core-not-built` with a wrong `--core`; `serial-unavailable` with a regular file at the link path; a stale link is replaced; `address-in-use` with the port taken by the test, and no link left behind; a usage error gives status 2; a folder without a show starts and reports `mapping-missing`. |
| `test_serial.py` | Each command through the port gives the reference's reply; bytes arrive unchanged and nothing is echoed; a line split over three writes; two lines in one write give two replies in order; 10,000 bytes without a newline, then a newline, give one `line-too-long`; the port is opened and closed 20 times; setting a speed and changing DTR and RTS do no harm. |
| `test_http.py` | `POST /odrig` for each command, with and without the final newline: status 200, `application/json`, the reply bytes; `"ok":false` replies have status 200; `GET`, `PUT`, `DELETE`, `HEAD` and `OPTIONS` give 405 with `Allow: POST` and leave the state unchanged; no `Content-Length` gives 411; an empty body, a body of 65 characters and one of 10,000 bytes; `/odrig?x=1` is served and `/odrig/x` is 404; three request content types give the same reply; a command over HTTP changes what `status` over the port reports, and the other way round; the server's address is 127.0.0.1. |
| `test_events.py` | `hello` first, with the legs and `t0`; 100 `frame` events in a row each equal the reference for their timestamp; at least 147 refreshes arrive in 3 seconds; a command by each transport gives one `log` event with the transport, the line, the reply and a later `status` event equal to the reply of `status`, `fps` aside; the emulator's own status requests give no `log` event; a late connection receives the kept entries; a line of 80 characters is logged with 64 and `cut`; a connection that reads nothing for 2 seconds then receives the newest refresh, not an old one; on a folder without a show `hello` carries no legs and the reason `mapping-missing`, and `/show/mapping.json` is 404; `/show/mapping.json` of the example show has the bytes of the file. |
| `test_realtime.py` | With the example show, and with the ten-leg mapping and a dense 60 x 30 clip of 10 seconds, `status` reports 49 or more for five full seconds in a row. |
| `test_tool.py` | Each command through `--port` and through `--http` prints the reply and exits with 0; `play 99` prints `unknown-id` and exits with 1; `play abc` is sent as typed and gives `bad-argument`; a port path that does not exist and a closed HTTP port exit with 3 and one line on standard error; a usage error exits with 2; the session of Requirement 13 criterion 9; `serial_exchange` asks for RTS to be lowered before DTR, seen through a stand-in for `fcntl.ioctl`, and goes on when both requests fail; a line that is not a reply, sent by a stand-in port before the reply, is skipped. |
| `test_layout.py` | Run through the JavaScript shell: for both tracked mappings and for made-up ones (a leg starting on the left, legs of two and four rows, legs in another order, rows of one leg apart from each other), `position` of every LED equals the rule of `docs/mapping.md` computed in Python, `find` is its inverse, `rows` gives the end numbers of the tables in `docs/mapping.md`, and `path` passes through every LED in chain order; `side`, `tracks` and `place`, with a pin that is not on the board; `colour` gives ten different colours for ten legs; `shown(0)` is 0, `shown(255)` is 255 and the curve never falls; `fit` for the ten-leg mapping at 1280 x 800 gives the sizes named above with every part inside the area. |
| `test_board.py` | The two lists of `board.js` equal, in order, the pin labels of the board drawing in `docs/mapping.md`, read from that file. |
| `test_page_files.py` | Every file of `emulator/web/` is served with its content type and no other file is; no page file names another host (`http://`, `https://`, `//`); `index.html` loads every script and style of the folder. |
| `test_demo.py` | The tracked `shows/demo-10/show.json` has the content of Requirement 14; the generators and `pack` with `mapping/legs-10.json` give a 60 x 30 show; 31 seconds of it equal the reference; the emulator started on it reports ten legs on pins 1 to 10 in `hello`. |
| `test_scope.py` | Every module of `emulator/` and `odrigctl/` imports only modules of the standard library and of its own package, so neither holds or borrows a decoder, a show reader or a mapping rule from `odrig`; only `binding.py` imports `ctypes`; no source names an address other than `127.0.0.1` to listen on; none of the proof-of-concept scripts in `tools/` is tracked. |
| `test_docs.py` | `docs/emulator.md` names the start command, the record options, every command of the tool, both transports, the test command and every item of the check list. |

The JavaScript shell is
`/System/Library/Frameworks/JavaScriptCore.framework/Versions/Current/Helpers/jsc`, part
of macOS. It was checked on this Mac while this design was written: it runs a script file,
`read(path)` returns a file's text, `arguments` holds what follows `--`, and `print` writes
a line. `test_layout.py` runs `jsc emulator/web/board.js emulator/web/layout.js
tests/emulator/js/dump_layout.js -- MAPPING` and reads one JSON document from its output.
When the shell is missing the tests that need it fail with a message that names the path.

Tests that depend on the speed of this Mac (`test_realtime.py`, the count in
`test_events.py`) say so in their names and messages.

**What a program does not check.** How the page looks is checked by a person, or by a tool
that drives a browser, in Safari and in Chrome, from the list in `docs/emulator.md`: the
drawing fits the window and follows its size; dark LEDs are visible; HELLO WORLD is upright
and readable and alternates with the square every 15 seconds; the page counts 49 or more
refreshes a second for the example show and for the dense 60 x 30 clip; a command sent by
each transport appears in the log at once and the status follows; the mapping view of the
demo show has the board, ten legs on pins 1 to 10, lines, paths, end numbers and no label
over another; pointing highlights one leg everywhere; an invalid show shows its reason.

## Documentation

- `docs/emulator.md`: building the shared library; packing and starting the example show
  and the demo show; the page's two views, the log and the status; the port and its link;
  the HTTP address with a `curl` example; the record mode, the script format and the record
  file format; the command tool with one example for each command and each transport; the
  failures at start; the test command and what it needs; the check list.
- `README.md`: one sentence pointing to `docs/emulator.md`.

## What seed 04 takes from this one

- `odrigctl`, unchanged, for the board: over the USB serial port and over HTTP.
- `odrigctl.client.serial_exchange` for every exchange with the board's serial port,
  WLED's handshake included.
- The HTTP rules of "POST /odrig", which the firmware follows.
- The emulator and the reference session of `test_tool.py`, to compare the board's replies
  with.
- The record mode, to state what the board should show.
