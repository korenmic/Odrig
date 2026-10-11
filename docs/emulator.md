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
| `python3 -m unittest discover -s tests/emulator -t .` | Builds the shared library and runs the suite of `tests/emulator/`. | The same, and Python 3.10 or later with no added package. |

The emulator never builds the library itself. The suite is every `test_*.py` file in
`tests/emulator/`, found by discovery; importing the test package runs `make -C core shared`
first, and when that fails no test runs and make's output is the failure. The suite needs
no hardware, no network connection and no browser.

## Starting

```
python -m emulator SHOW_DIR [--port N] [--core PATH] [--verbose]
```

Started from the repository root with the folder of an installed show, the emulator starts
the core on that folder, opens its address on 127.0.0.1 and prints it:

```
page: http://127.0.0.1:8600/
```

It then asks the core for a refresh at every grid time, 20 ms apart, with a timestamp in
whole milliseconds from a clock that does not go backwards. When a request is late it
carries the current time; the grid times that were missed are not asked for again. The
emulator runs until it receives an interrupt (Ctrl-C) or a termination signal, and then
exits with status 0.

| Option | Meaning | Without it |
|---|---|---|
| `--port N` | The port of the address on 127.0.0.1; 0 takes any free port. | 8600 |
| `--core PATH` | The core's shared library. | `core/build/libodrig_core.dylib` under the repository root |
| `--verbose` | Prints the core's diagnostic lines to standard error, each after `core: `. | They are kept, not printed. |

There is no option for a size and none for an address: the canvas is the one of
`mapping.json` in the folder, and the address is always 127.0.0.1.

Any folder starts the emulator. Whether it holds a valid show is the core's judgement: with
an invalid show the LEDs stay dark, `status` gives the reason and every command is still
answered.

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
| Any other path | Status 404. |

- The body is the command line, with or without a final newline. Of a body longer than 128
  bytes the first 128 are passed on, which the core answers with `line-too-long`.
- The content type of the request is not looked at.
- The path is `/odrig` exactly. What follows a `?` is ignored.
- The response that carries a reply has the header `Access-Control-Allow-Origin: *`.
- An answer without a body closes its connection.

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
| 1 | It could not start. One line `error: <reason>: <detail>` is written to standard error, and no partly written file is left behind. |
| 2 | The command line was not understood. A usage message is written to standard error. |

| Reason | Condition |
|---|---|
| `not-a-folder` | `SHOW_DIR` does not exist or is not a folder. |
| `core-not-built` | The core's shared library is not found or cannot be loaded. The detail names the command that builds it. |
| `address-in-use` | The address is already in use or cannot be opened. |
| `bad-length` | In record mode, the length is not above 0. |
| `bad-script` | In record mode, the script cannot be read or breaks one of its rules. |
| `cannot-write` | In record mode, the record file cannot be written, for example because its folder does not exist. |

Whether the folder holds a valid show is not the emulator's judgement but the core's: any
folder is recorded, and with an invalid show the LED data is dark and `status` gives the
reason.
