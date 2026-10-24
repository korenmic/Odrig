# Getting started

From a fresh clone to the demo show playing in the emulator. Nothing on this page needs the
board. The project's words are explained in [vocabulary.md](vocabulary.md). On a Windows
computer read [On Windows](#on-windows) first.

## What you need

- **A Mac, or a Windows computer**; [On Windows](#on-windows) has how the commands are
  written there. The firmware tool runs on macOS only at present.
- **Apple's command-line developer tools**, which bring `make`, the C++ compiler and
  `git`. `xcode-select --install` installs them.
- **Python 3.10 or later, as `python3`.** The Python that comes with the developer tools is
  older. `python3 --version` has to say 3.10 or more before you go on.
- **Node.js 20 or later, as `node`**, with the `npm` that comes with it. The converter
  runs on it. `node --version` has to say v20 or more.
- **A network connection** for the setup, once.
- **Safari or Chrome**, to look at the emulator's page.

## On Windows

The Python library, the core's build, the emulator, the command tool, the app's tool and
their suites work on Windows 10 and 11. The converter's own suite, `npm test --prefix
converter`, passes there too. The firmware tool, the board and the walk-through suite stay
with the first computer. A Windows computer needs git, Python 3.10 or later as `python`,
Node.js 20 or later, and a C++ compiler. The build finds `g++` or `clang++` on the path,
and Microsoft's C++ build tools. With none of them, unpack a GCC for Windows, such as the
WinLibs build of MinGW-w64, into the folder `tools/` of the repository: nothing is
installed. The setup and the suites, in PowerShell:

```text
git clone https://github.com/korenmic/Odrig.git
cd Odrig
python -m venv .venv
npm ci --prefix converter
npm test --prefix converter
.venv\Scripts\python core/build.py shared
.venv\Scripts\python -m unittest discover -s tests/converter -t .
.venv\Scripts\python core/build.py test
.venv\Scripts\python -m unittest discover -s tests/emulator -t .
.venv\Scripts\python -m unittest discover -s tests/onboarding -t .
```

| The rest of this page and the animation guide, on macOS | On Windows |
|---|---|
| `.venv/bin/python` | `.venv\Scripts\python` |
| `make -C core shared`, which builds `core/build/libodrig_core.dylib` | `core/build.py shared` as above, which builds `core/build/odrig_core.dll` |
| `mkdir -p build/demo-20/sources` | `mkdir build\demo-20\sources` |
| `printf '1000 status\n' > FILE` | `Set-Content FILE "1000 status"` |
| The emulator's line `serial:`, and `--port build/emulator/serial` | Its line `tcp: 127.0.0.1:8601`, and `--tcp 127.0.0.1:8601` |

## Set up

Clone the repository, which is private, with
`git clone https://github.com/korenmic/Odrig.git`, and go into its folder, `Odrig`. Every
command of this repository is run from that folder, the repository root.

```sh
python3 -m venv .venv
npm ci --prefix converter
make -C core shared
```

The first command makes a Python environment in the folder `.venv`; nothing is installed
into it, since every Python program of the repository needs only Python's own library. The
second puts the converter's two packages into `converter/node_modules/`; one of them
fetches a decoder program, an ffmpeg built for your computer, with which the converter
reads videos. The third builds the core as the library the emulator loads,
`core/build/libodrig_core.dylib`. Git ignores these three folders. `.venv/bin/python` is
the Python for every command of this repository. The other documents write it as `python`.

## Run the tests

```sh
npm test --prefix converter
.venv/bin/python -m unittest discover -s tests/converter -t .
make -C core test
.venv/bin/python -m unittest discover -s tests/emulator -t .
.venv/bin/python -m unittest discover -s tests/onboarding -t .
```

The first ends with a list of counts, in which `fail 0` says that every test passed. Each
of the others ends with the line `OK`. The emulator's suite leaves out the tests that are
for the other system and says how many, as in `OK (skipped=9)`. None needs the board or
the network.

| Suite | What it checks | Takes about |
|---|---|---|
| `converter/tests` | The converter: its results against the stored answers of the Python package, which converted before it, and its library in Chrome. Without Chrome that one test is skipped. | 25 seconds |
| `tests/converter` | The Python library and the generators, and every tracked document against the tools. | 20 seconds |
| `tests/core` | The core. `make -C core test` builds it first, with the compiler's checks for memory faults switched on, and uses `python3`. | 40 seconds |
| `tests/emulator` | The emulator and the command tool. | 2 minutes |
| `tests/onboarding` | This page and the other pages for newcomers: that every path, link and command in them is real. | 2 seconds |

## Suites that need more

```sh
python3 firmware/fw.py test
python3 -m unittest discover -s tests/app -t .
python3 -m unittest discover -s tests/apk -t .
python3 -m unittest discover -s tests/mapping -t .
.venv/bin/python -m unittest discover -s tests/walkthrough -t .
```

The first is the suite of the firmware tool, `tests/firmware`, and needs no board; its first
run fetches WLED's source and build tools, about 260 MB, into `build/firmware/`. The second,
`tests/app`, runs the web code of the operators' app, `app/www/`, in Chrome without a window
against the emulator; the third, `tests/apk`, checks the app's package once it was built. The
last, `tests/walkthrough`, follows this page and the animation guide in a fresh copy, over the
network, and runs the five suites above: seven minutes. Run it when either page changed.
`tests/mapping` checks pin assignments and the diagonal, with the core test host built.
Two more suites need the board on USB and write to it: `python3 firmware/fw.py test-board`
runs `tests/board`, and `python3 firmware/fw.py test-air --http <address>` runs
`tests/air`. Before either, read "If you have a board" in
[working-rules.md](working-rules.md#if-you-have-a-board) and [firmware.md](../docs/firmware.md).

## Pack the demo show

The demo show, `shows/demo-20/show.json`, is test content for the target and not finished
work: two proof-of-concept animations, the words HELLO WORLD and a square that bounces. It
plays the two in turn from power-on, each for half a minute or more. Its two sources are not
tracked. Two generators write them, and the converter's `pack` turns them and the show
file into an installed file set:

```sh
mkdir -p build/demo-20/sources
.venv/bin/python -m odrig.generators.hello_world build/demo-20/sources/hello.json --mapping mapping/legs-20.json
.venv/bin/python -m odrig.generators.dvd_bounce build/demo-20/sources/dvd.json --mapping mapping/legs-20.json
node converter/odrig.js pack --show shows/demo-20/show.json --mapping mapping/legs-20.json \
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

Open the page's address in the browser. It draws all 3,600 LEDs, twenty legs in twenty
colours: HELLO WORLD upright, then a small square on the diagonal, in turns. The header
shows what plays and two counts of refreshes a second, `core` and `page`, about 50 each.
`Mapping` shows how every leg is wired to the board, `Controller` the operators' app.
`.venv/bin/python -m preview build/demo-20/show/dvd.odrg` shows one file alone.

Send it commands from a second terminal. The first two go through the emulator's serial
port, the way the board takes them over USB, and the third over HTTP, the way the board
takes them over Wi-Fi:

```sh
.venv/bin/python -m odrigctl --port build/emulator/serial status
.venv/bin/python -m odrigctl --port build/emulator/serial play 2
.venv/bin/python -m odrigctl --http 127.0.0.1:8600 brightness 40
```

Each prints the reply, one line of JSON like the one under the next heading. The page
shows every command in its log as it arrives. Stop the emulator with Ctrl-C in its
terminal. [commands.md](../docs/commands.md) has every command and
[emulator.md](../docs/emulator.md) everything about the emulator and its page.

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
reply 1000 {"ok":true,"on":true,"brightness":128,"playing":"all","animation":1,"fps":50,"error":null,"width":60,"height":60}
```

`"error":null` says the show is valid, `"playing":"all"` that the playlist is playing,
and `"animation":1` that Hello world is on the LEDs. With a show that is not valid, `error`
holds the reason, such as `file-missing dvd.odrg`; [reasons.md](../docs/reasons.md) lists them.
The record file holds the colour of every LED at every refresh;
[emulator.md](../docs/emulator.md#record-mode) describes it.

## What to read next

- [animation-guide.md](animation-guide.md), to make an animation and try it here.
- [working-rules.md](working-rules.md), before you change anything.
- [converter.md](../docs/converter.md), [format.md](../docs/format.md) and [show.md](../docs/show.md) for the
  tools and files used above, [python-library.md](../docs/python-library.md) for the generators, and
  [mapping.md](../docs/mapping.md) for how the canvas is wired.
- [decisions.md](../docs/decisions.md) for what has been decided and what is still open.
