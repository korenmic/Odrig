# The emulator

The emulator is a Mac program that runs the core of [core.md](core.md) on an installed show,
the folder that [show.md](show.md) describes. It is the Python package `emulator` at the
repository root and uses only the Python standard library. It loads the core as a shared
library, built from the same `core/src/*.cpp` the firmware compiles, and leaves every
decision about files, time and commands to it.

## Commands

Run from the repository root.

| Command | What it does | What it needs |
|---|---|---|
| `make -C core shared` | Builds `core/build/libodrig_core.dylib`, the library the emulator loads, from every `core/src/*.cpp` with the flags of `make -C core`. | Apple's command-line developer tools: `make` and `c++`. |
| `python3 -m unittest discover -s tests/emulator -t .` | Builds the shared library and runs the suite of `tests/emulator/`. | The same, Python 3.10 or later with no added package, and the JavaScript shell that is part of macOS. |

The emulator never builds the library itself. The suite is every `test_*.py` file in
`tests/emulator/`, found by discovery; importing the test package runs `make -C core shared`
first, and when that fails no test runs and make's output is the failure. The suite needs
no hardware, no network connection and no browser. The page's geometry is run in the
JavaScript shell of macOS,
`/System/Library/Frameworks/JavaScriptCore.framework/Versions/Current/Helpers/jsc`.

## Starting

```
python -m emulator SHOW_DIR [--port N] [--serial-link PATH] [--core PATH] [--verbose]
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
emulator runs until it receives an interrupt (Ctrl-C) or a termination signal, and then
removes the link to its port and exits with status 0.

| Option | Meaning | Without it |
|---|---|---|
| `--port N` | The port of the address on 127.0.0.1; 0 takes any free port. | 8600 |
| `--serial-link PATH` | Where the link to the serial port is made. | `build/emulator/serial` under the repository root, whatever folder the command is run from |
| `--core PATH` | The core's shared library. | `core/build/libodrig_core.dylib` under the repository root |
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
- **The drawing**, described below, with a readout at its top right that names what the
  pointer is on: `leg 2, pin 2, LED 61 (1,2)`.
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
window and drawn again when the window changes its size; a 60 x 30 canvas is shown whole in
a window of 1280 x 800.

```
            x=1                                              x=60
 leg 1    | y=6    60  o o o o o o o o o o o o o o o o o o o    1
 pin 1    | y=5    61  o o o o o o o o o o o o o o o o o o o  120
          | y=4   180  o o o o o o o o o o o o o o o o o o o  121
 leg 2    | y=3    60  o o o o o o o o o o o o o o o o o o o    1
 pin 2    | y=2    61  o o o o o o o o o o o o o o o o o o o  120
          | y=1   180  o o o o o o o o o o o o o o o o o o o  121
```

- Each leg has one colour. A bracket in that colour spans the rows of the leg, with the
  leg's number and its pin, and a faint band of the colour lies behind those rows. A leg
  whose rows are not neighbours gets a bracket for each run of rows.
- Every row has its `y` and, at its two ends, the numbers of the LEDs that sit there, so
  the direction of the chain can be read off.
- **The page places the LEDs itself.** A refresh arrives as the bytes the core produced for
  each leg, in chain order, without coordinates. The page works out where LED n of a pin
  is from that pin, n and the show's `mapping.json`, by the rule of
  [mapping.md](mapping.md), and never reorders or corrects the data. A mapping mistake in
  the core therefore shows as a scrambled picture. The rule is in
  `emulator/web/layout.js`, which needs no browser, so the suite compares it with the
  reference for every LED.
- A dark LED is drawn as a faint ring, so every LED can be seen at any time.
- A colour value v is shown as `255 * (v / 255) ^ (1 / 2.2)`, rounded: a screen shows a low
  value much darker than an LED does. This one curve is the only change; the record file
  and the event stream carry the values unchanged.

## The event stream

The page learns everything it shows from one stream of server-sent events, `GET /events`,
and from the mapping file of the show, `GET /show/mapping.json`, which is served byte for
byte (404 when the folder has none). Another program may read both in the same way.

The stream is a response of type `text/event-stream` that stays open. It has four kinds of
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

| Event | What it carries |
|---|---|
| `hello` | First on every connection. `legs` lists `[leg, pin, number of LEDs]` in the core's order; `t0` is the power-on moment, the timestamp of the first request for a refresh; `error` is the reason the show is invalid as the core gives it when the page connects, or `null`. |
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
board, through a serial port or over HTTP. It is a second small Python package at the
repository root, uses only the Python standard library, and treats the two targets alike:
only the port name or the address says which one is meant.

```
python -m odrigctl (--port NAME | --http ADDRESS) [--timeout SECONDS] play ID
python -m odrigctl (--port NAME | --http ADDRESS) [--timeout SECONDS] on
python -m odrigctl (--port NAME | --http ADDRESS) [--timeout SECONDS] off
python -m odrigctl (--port NAME | --http ADDRESS) [--timeout SECONDS] brightness N
python -m odrigctl (--port NAME | --http ADDRESS) [--timeout SECONDS] status
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
- `--http ADDRESS`: `host` or `host:port`, with or without `http://` in front and a `/` at
  the end; without a port it is 80. The tool sends `POST http://ADDRESS/odrig` with the line
  as the body and the content type `application/octet-stream`, and takes the body of a
  response with status 200 as the reply. Any other status counts as not reached.
- The options may stand before or after the command.

Another program can use the two exchanges directly: `odrigctl.client.serial_exchange(port,
data, timeout)` and `odrigctl.client.http_exchange(address, line, timeout)` return the reply
or raise `Unreachable`. `serial_exchange` takes a fourth argument, a function that says
which received line is the answer, for a target whose answer is not a reply of
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

Recording the same folder with the same length and the same script twice gives the same
bytes. The emulator gives the core nothing of its own in this mode: only the requests for
a refresh and the commands of the script.

`--core PATH` names another shared library than `core/build/libodrig_core.dylib`.

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
