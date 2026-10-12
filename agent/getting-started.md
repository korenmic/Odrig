# Getting started

From a fresh clone to the demo show playing in the emulator. Nothing on this page needs the
board. The project's words are explained in [vocabulary.md](vocabulary.md). On a Windows
computer read [On Windows](#on-windows) first.

## What you need

- **A Mac.** The core's build, the emulator, the command tool and the firmware tool run on
  macOS only at present.
- **Apple's command-line developer tools**, which bring `make`, the C++ compiler and
  `git`. `xcode-select --install` installs them.
- **Python 3.10 or later, as `python3`.** The Python that comes with the developer tools is
  older. `python3 --version` has to say 3.10 or more before you go on.
- **Node.js 20 or later, as `node`**, with the `npm` that comes with it. The converter
  runs on it. `node --version` has to say v20 or more.
- **A network connection** for the setup, once.
- **Safari or Chrome**, to look at the emulator's page.

## On Windows

Only a part of the project works on Windows today, and none of it has been tried there:

| What | On Windows today |
|---|---|
| The converter and its suite | Written to run there. They have been run on macOS only. |
| The reference converter, the generators and their suite | The same: written to run there, run on macOS only. |
| The core's build, the emulator, the command tool | macOS only. |
| The firmware tool and the board | They stay with the first computer. |

Making the emulator and the tools run on Windows is seed 11,
`project-seeds/11-p0-emulator-and-tools-on-windows/`. It is the first job of the
contributor on Windows, who takes it through its spec, its tasks and their implementation
on the Windows computer. Until then this is the setup as far as it is known. It needs git,
Python 3.10 or later and Node.js 20 or later; `python` stands for however Python is started:

```text
git clone https://github.com/korenmic/Odrig.git
cd Odrig
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
npm ci --prefix converter
npm test --prefix converter
.venv\Scripts\python -m unittest discover -s tests/converter -t .
```

With that, the converter and the generators can be tried on Windows, with the commands of
this page and of the animation guide; a generator is started with `.venv\Scripts\python`
in place of `.venv/bin/python`. What fails there is a finding for seed 11, which also runs
the converter's suite on Windows. Everything else, from `make -C core shared` on, is what
seed 11 provides: the core's build, the other suites, the emulator, its record mode and
the command tool. Linux is in the same position, and nobody has tried it.

## Set up

Clone the repository, which is private, with
`git clone https://github.com/korenmic/Odrig.git`, and go into its folder, `Odrig`. Every
command of this repository is run from that folder, the repository root.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
npm ci --prefix converter
make -C core shared
```

The first command makes a Python environment in the folder `.venv`. The second puts three
libraries into it, numpy, Pillow and PyAV, with which the reference converter reads videos
and GIFs. The third puts the converter's two packages for the same job into
`converter/node_modules/`; one of them fetches a decoder program, an ffmpeg built for your
computer. The fourth builds the core as the library the emulator loads,
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
of the others ends with the line `OK`. None needs the board or the network.

| Suite | What it checks | Takes about |
|---|---|---|
| `converter/tests` | The converter: its results against those of the reference converter, and its library in Chrome. Without Chrome that one test is skipped. | 25 seconds |
| `tests/converter` | The reference converter and the generators, and every tracked document against the tools. | 20 seconds |
| `tests/core` | The core. `make -C core test` builds it first, with the compiler's checks for memory faults switched on, and uses `python3`. | 40 seconds |
| `tests/emulator` | The emulator and the command tool. | 2 minutes |
| `tests/onboarding` | This page and the other pages for newcomers: that every path, link and command in them is real. | 2 seconds |

## Suites that need more

```sh
python3 firmware/fw.py test
.venv/bin/python -m unittest discover -s tests/walkthrough -t .
```

The first is the suite of the firmware tool, `tests/firmware`, and needs no board. The
first time that tool runs, it fetches WLED's source and its build tools into
`build/firmware/`: about 260 MB, over the network. Run it when you work on the firmware.

The second, `tests/walkthrough`, follows this page and the animation guide in a fresh copy:
it sets up a clone in a temporary folder as this page says, which needs the network, runs
the five suites above, packs and checks the demo show, and makes an animation as the guide
says. It takes about four minutes. Run it when you have changed either page.

Two more suites need the board on USB and write to it: `python3 firmware/fw.py test-board`
runs `tests/board`, and `python3 firmware/fw.py test-air --http <address>` runs
`tests/air`. Before either, read "If you have a board" in
[working-rules.md](working-rules.md#if-you-have-a-board) and [firmware.md](../docs/firmware.md).

## Pack the demo show

The demo show, `shows/demo-20/show.json`, is test content for the target and not finished
work: two proof-of-concept animations, the words HELLO WORLD and a square that bounces, and
a cycle that plays the two in turn, 15 seconds each, from power-on. Its two sources are not
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

Each prints the reply, one line of JSON like the one under the next heading. The page
shows every command in its log as it arrives. Stop the emulator with Ctrl-C in its
terminal. [commands.md](../docs/commands.md) has the five commands and
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
reply 1000 {"ok":true,"on":true,"brightness":128,"playing":3,"animation":1,"fps":50,"error":null}
```

`"error":null` says the show is valid, `"playing":3` that item 3, the cycle, is playing,
and `"animation":1` that Hello world is on the LEDs. With a show that is not valid, `error`
holds the reason, such as `file-missing dvd.odrg`; [reasons.md](../docs/reasons.md) lists them.
The record file holds the colour of every LED at every refresh;
[emulator.md](../docs/emulator.md#record-mode) describes it.

## What to read next

- [animation-guide.md](animation-guide.md), to make an animation and try it here.
- [working-rules.md](working-rules.md), before you change anything.
- [converter.md](../docs/converter.md), [format.md](../docs/format.md) and [show.md](../docs/show.md) for the
  tools and files used above, [reference-converter.md](../docs/reference-converter.md) for the generators, and
  [mapping.md](../docs/mapping.md) for how the canvas is wired.
- [decisions.md](../docs/decisions.md) for what has been decided and what is still open.
