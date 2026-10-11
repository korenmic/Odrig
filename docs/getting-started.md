# Getting started

From a fresh clone to the demo show playing in the emulator. Nothing on this page needs the
board. The project's words are explained in [vocabulary.md](vocabulary.md).

## What you need

- **A Mac.** The core's build, the emulator, the command tool and the firmware tool run on
  macOS only at present.
- **Apple's command-line developer tools**, which bring `make`, the C++ compiler and
  `git`. `xcode-select --install` installs them.
- **Python 3.10 or later, as `python3`.** The Python that comes with the developer tools is
  older. `python3 --version` has to say 3.10 or more before you go on.
- **A network connection** for the setup, once.
- **Safari or Chrome**, to look at the emulator's page.

On Windows and Linux only the converter is meant to work: it is written to run there, and
so is its suite, but it has been run on macOS only. There you can do the first two commands
of the setup, run the converter's suite, and make, check and pack animations. You cannot
build the core or run the emulator.

## Set up

Clone the repository from the address the owner gave you, and go into its folder:

```text
git clone <address of the repository> odrig
cd odrig
```

Every command of this repository is run from that folder, the repository root.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
make -C core shared
```

The first command makes a Python environment in the folder `.venv`. The second puts three
libraries into it, numpy, Pillow and PyAV, which the converter needs to read videos and
GIFs. The third builds the core as the library the emulator loads,
`core/build/libodrig_core.dylib`. Git ignores both folders, `.venv/` and `core/build/`.

`.venv/bin/python` is the Python for every command of this repository. The other documents
write it as `python`. On Windows it is `.venv\Scripts\python`.

## Run the tests

```sh
.venv/bin/python -m unittest discover -s tests/converter -t .
make -C core test
.venv/bin/python -m unittest discover -s tests/emulator -t .
.venv/bin/python -m unittest discover -s tests/onboarding -t .
```

Each ends with the line `OK`. None needs the board or the network.

| Suite | What it checks | Takes about |
|---|---|---|
| `tests/converter` | The converter, and every tracked document against the tools. | 20 seconds |
| `tests/core` | The core. `make -C core test` builds it first, with the compiler's checks for memory faults switched on, and uses `python3`. | 40 seconds |
| `tests/emulator` | The emulator and the command tool. | 2 minutes |
| `tests/onboarding` | This page and the other pages for newcomers: that every path, link and command in them is real. | a second |

## Suites that need more

The firmware tool has a suite that needs no board:

```sh
python3 firmware/fw.py test
```

It runs the tests in `tests/firmware`. The first time any command of that tool runs, the
tool fetches WLED's source and installs its build tools into `build/firmware/`: about
260 MB, over the network. Run it when you work on the firmware or on its tool.

One suite, `tests/walkthrough`, follows this page in a fresh copy of the repository, to see
that the commands above and below still work:

```sh
.venv/bin/python -m unittest discover -s tests/walkthrough -t .
```

It clones the repository into a temporary folder, sets it up there as this page says, which
needs the network, runs the four suites above, packs the demo show and checks it. It takes
about four minutes. Run it when you have changed this page or a command it gives.

Two more suites need the board on USB and write to it: `python3 firmware/fw.py test-board`
runs `tests/board`, and `python3 firmware/fw.py test-air --http <address>` runs
`tests/air`. Before either, read "If you have a board" in
[working-rules.md](working-rules.md#if-you-have-a-board) and [firmware.md](firmware.md).

## Pack the demo show

The demo show, `shows/demo-20/show.json`, is made for the target: Hello world, a square
that bounces, and a cycle that plays the two in turn, 15 seconds each, from power-on. Its
two sources are not tracked. Two generators write them, and `pack` turns them and the show
file into an installed file set:

```sh
mkdir -p build/demo-20/sources
.venv/bin/python -m odrig.generators.hello_world build/demo-20/sources/hello.json --mapping mapping/legs-20.json
.venv/bin/python -m odrig.generators.dvd_bounce build/demo-20/sources/dvd.json --mapping mapping/legs-20.json
.venv/bin/python -m odrig pack --show shows/demo-20/show.json --mapping mapping/legs-20.json \
    --sources build/demo-20/sources --out build/demo-20/show
```

`build/demo-20/show` now holds `mapping.json`, `show.json`, `hello.odrg` and `dvd.odrg`.
`pack` refuses a folder that is not empty, so remove `build/demo-20/show` before you pack
again. Git ignores everything under `build/`.

## Run it in the emulator

```sh
.venv/bin/python -m emulator build/demo-20/show
```

The emulator prints two lines and keeps running:

```text
page: http://127.0.0.1:8600/
serial: <the repository root>/build/emulator/serial
```

Open the page's address in the browser. It draws all 3,600 LEDs, with the twenty legs in
twenty colours. The words HELLO WORLD stand upright in the middle; after 15 seconds a
small square runs along the diagonal, and the two take turns. The header shows what is
playing and two counts of refreshes a second, `core` and `page`, both about 50. The tab
`Mapping` shows the board and how every leg is wired to it.

Send it commands from a second terminal. The first two go through the emulator's serial
port, the way the board takes them over USB, and the third over HTTP, the way the board
takes them over Wi-Fi:

```sh
.venv/bin/python -m odrigctl --port build/emulator/serial status
.venv/bin/python -m odrigctl --port build/emulator/serial play 2
.venv/bin/python -m odrigctl --http 127.0.0.1:8600 brightness 40
```

Each prints the reply. The first one's is:

```text
{"ok":true,"on":true,"brightness":128,"playing":3,"animation":1,"fps":50,"error":null}
```

The page shows every command in its log as it arrives. Stop the emulator with Ctrl-C in
its terminal. [commands.md](commands.md) has the five commands and
[emulator.md](emulator.md) everything about the emulator and its page.

## Check it without a screen

A coding agent cannot look at a page, and a script should not have to. In record mode the
emulator plays a show on a clock of its own, without waiting and without a page, gives it
the commands of a script at the times the script says, and prints each reply:

```sh
printf '1000 status\n' > build/demo-20/ask.txt
.venv/bin/python -m emulator build/demo-20/show --record build/demo-20/check.odrr --seconds 2 \
    --script build/demo-20/ask.txt
```

```text
reply 1000 {"ok":true,"on":true,"brightness":128,"playing":3,"animation":1,"fps":50,"error":null}
```

`"error":null` says the show is valid, `"playing":3` that item 3, the cycle, is playing,
and `"animation":1` that Hello world is on the LEDs. With a show that is not valid, `error`
holds the reason, such as `file-missing dvd.odrg`; [reasons.md](reasons.md) lists them.
The record file holds the colour of every LED at every refresh;
[emulator.md](emulator.md#record-mode) describes it.

## What to read next

- [working-rules.md](working-rules.md), before you change anything.
- [converter.md](converter.md), [format.md](format.md) and [show.md](show.md) for the
  tools and files used above, and [mapping.md](mapping.md) for how the canvas is wired.
- [decisions.md](decisions.md) for what has been decided and what is still open.
