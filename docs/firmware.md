# The firmware

The firmware is WLED 16.0.1 for the ESP32-S3, built from WLED's own source with one usermod
added that hosts the core of [core.md](core.md). One tool, `firmware/fw.py`, sets up the
tools the build needs, fetches WLED, builds, flashes, restores stock WLED and installs a
show into the board's storage.

This page covers [what the tool needs](#what-the-tool-needs), [the work folder](#the-work-folder),
the [commands](#commands) of the tool, [from nothing to a playing board](#from-nothing-to-a-playing-board),
[what the firmware does](#what-the-firmware-does),
[what it changes in WLED](#what-the-firmware-changes-in-wled), [the probe build](#the-probe-build),
the [measurements](#measurements-on-the-board) made on the board,
[the regions of the flash](#the-regions-of-the-flash) the tool writes,
[rolling back](#rolling-back), [the owner's checks](#the-owners-checks) and what was
[verified on the board](#verified-on-the-board).

## What the tool needs

On the Mac before the tool runs:

- macOS with Apple's command-line developer tools,
- git,
- Python 3.10 or later, as `python3`.

Everything else the tool installs itself, into the work folder, the first time a command is
run. That first time needs a network connection; later runs do not fetch again.

| What | Version | From |
|---|---|---|
| WLED's source | tag `v16.0.1`, commit `29b389df1c1aaec6ff53aea742d17063b985906c` | `https://github.com/wled/WLED.git` |
| PlatformIO and its Python packages | 6.1.17, as WLED's own `requirements.txt` at the tag pins them | PyPI |
| esptool | 5.4.0 | PyPI |
| littlefs-python | 0.19.0 | PyPI |
| Node.js and npm | 20.18.0 and 10.8.2, the package `nodejs-wheel` 20.18.0 | PyPI |

The last three are pinned in `firmware/requirements.txt`. WLED's build needs Node.js to pack
its web interface; `.nvmrc` of WLED 16.0.1 asks for 20.18.

The tool refuses to work with a WLED folder that is not at the pinned commit
(`wled-mismatch`), and with a Python below 3.10 (`setup-failed`).

WLED's own build then fetches what WLED's files at the tag name. The tool chooses none of
it:

| What | From |
|---|---|
| The platform `espressif32` 2024.06.00 and the Arduino core 2.0.18 | GitHub, `tasmota/platform-espressif32` and `tasmota/arduino-esp32` |
| The compilers `toolchain-xtensa-esp32s3` and `toolchain-riscv32-esp` 8.4.0, `tool-scons`, `tool-mklittlefs` | PlatformIO's registry |
| `tool-esptoolpy` 4.7.4 | GitHub, `tasmota/esptool` |
| The libraries AsyncTCP, AnimatedGIF, AsyncMqttClient, IRremoteESP8266, arduinoFFT and NeoPixelBus | PlatformIO's registry |
| The libraries NeoPixelBus, ESPAsyncWebServer, GifDecoder, esp_dmx and QuickESPNow at the commits WLED pins | GitHub, the repositories `platformio.ini` names |
| The 67 packages of WLED's `package-lock.json`, which pack the web interface | The npm registry |
| The Python packages `zopfli`, `wheel` and `tasmota-metrics`, which the platform installs into the tool's Python environment | PyPI |

## The work folder

The work folder is `build/firmware/` under the repository root. Git ignores it, and removing
it removes everything the tool installed, fetched or built.

```
build/firmware/
  venv/            Python environment: PlatformIO, esptool, littlefs-python, Node.js and npm
  pio/             PlatformIO's platforms, toolchains and packages
  pio-cache/       PlatformIO's build cache
  npm-cache/       npm's cache
  pip-cache/       pip's cache
  WLED/            WLED's source at the pinned commit
  out/             the built images
  storage/         storage images read from the board and written to it, the newest eight
```

Every program the tool starts gets these variables, so that nothing lands in the home
folder. `HOME` is left as it is.

| Variable | Value |
|---|---|
| `PLATFORMIO_CORE_DIR` | `build/firmware/pio` |
| `PLATFORMIO_BUILD_CACHE_DIR` | `build/firmware/pio-cache` |
| `PLATFORMIO_SETTING_ENABLE_TELEMETRY` | `No` |
| `npm_config_cache` | `build/firmware/npm-cache` |
| `npm_config_update_notifier` | `false` |
| `PIP_CACHE_DIR` | `build/firmware/pip-cache` |
| `PATH` | `build/firmware/venv/bin`, then the caller's |

The paths are absolute.

## Commands

Run from the repository root.

```
python3 firmware/fw.py setup
python3 firmware/fw.py build [--stock | --probe] [--verbose]
python3 firmware/fw.py flash [--port P] [--image PATH] [--expect status|wled|probe] [--wait SECONDS]
python3 firmware/fw.py restore-stock [--port P] [--full] [--stock-dir DIR]
python3 firmware/fw.py install-show DIR [--port P] [--no-check] [--wait SECONDS]
python3 firmware/fw.py read-show OUT [--port P]
python3 firmware/fw.py test
python3 firmware/fw.py test-board [--port P]
python3 firmware/fw.py test-air --http ADDRESS [--port P]
```

`fw.py` itself uses only the Python standard library. It checks the command line, makes sure
the work folder holds WLED's source and the Python environment, and then runs the command
with that environment's Python.

| Status | Meaning |
|---:|---|
| 0 | The command did its work. |
| 1 | It could not. One line `error: <reason>: <detail>` is written to standard error. |
| 2 | The command line was not understood. Nothing is set up for such a command line. |

| Reason | Condition |
|---|---|
| `setup-failed` | A tool could not be installed or fetched, or Python is older than 3.10. |
| `wled-mismatch` | `build/firmware/WLED` is not a checkout of its own at the pinned commit. |
| `patch-failed` | A patch file of `firmware/patches/` does not apply. |
| `build-failed` | PlatformIO ended with an error, or left no image. |
| `image-too-large` | An image is larger than the application partition, 3,145,728 bytes. |
| `image-missing` | The image to flash, or the SHA-256 beside it, is not there. |
| `checksum-mismatch` | An image differs from the SHA-256 beside it, or a stock file from `firmware/stock.sha256`. |
| `stock-missing` | A stock file that is about to be written is not there. |
| `no-board` | There is no `/dev/cu.usbmodem*` device, or more than one and none was named. |
| `layout-mismatch` | The board's partition table has no application partition at `0x10000` that the image fits in, or no data partition named `spiffs`. |
| `esptool-failed` | esptool ended with an error, or was asked for an address outside the regions below. |
| `no-reply` | The board did not answer within 20 seconds after its restart. |
| `verify-failed` | What is in the flash differs from what was written, or the new storage image does not hold what it should. |
| `no-space` | The files of a show do not fit into storage. Nothing was written to the board. |
| `not-a-show-folder` | The folder to install is no folder, holds something that is no file, or holds a file the show does not name. |
| `output-not-empty` | The folder `read-show` is to write exists and is not an empty folder. |
| a reason of [reasons.md](reasons.md), "Shows" | The folder to install is not a valid installed file set: `mapping-missing`, `show-malformed`, `file-missing`, `size-mismatch` and the others. |
| `backup-protected` | An output path lies in the factory backup of the board, which no tool writes. |

**The port.** A command that talks to the board uses the port given with `--port`, else the
one in the variable `ODRIG_BOARD_PORT`, else the only `/dev/cu.usbmodem*` device. With no
such device, or with more than one, it stops with `no-board`.

### setup

```
python3 firmware/fw.py setup
```

Puts WLED's source and the tools into the work folder and prints the work folder and the
version each tool reports. Every step is skipped when its result is there: the clone of WLED
when `build/firmware/WLED` exists, the Python environment when `build/firmware/venv` has its
Python, and the packages when the two requirement files are the ones that were installed.
Every other command does the same before its own work, so `setup` never has to be run by
hand.

```
work folder: /Users/you/odrig/build/firmware
python: Python 3.14.6
platformio: PlatformIO Core, version 6.1.17
node: v20.18.0
npm: 10.8.2
esptool: esptool v5.4.0
```

### build

```
python3 firmware/fw.py build
python3 firmware/fw.py build --probe
python3 firmware/fw.py build --stock
```

Builds an image with PlatformIO in `build/firmware/WLED` and keeps it in
`build/firmware/out/` with its SHA-256 in a file beside it, `<image>.sha256`. An image
larger than the application partition, 3,145,728 bytes, is not kept: `image-too-large`.

| Command | Environment | Image | What it is |
|---|---|---|---|
| `build` | `odrig` | `odrig-firmware.bin` | The firmware: WLED's environment `esp32s3dev_16MB_opi` with the usermod of `firmware/usermod/` in place of WLED's audio usermod, the core of `core/`, WLED's serial handling switched off, and the release name `odrig_ESP32-S3_16MB_opi`. |
| `build --probe` | `odrig_probe` | `odrig-probe.bin` | The probe build: the firmware with the flag `ODRIG_PROBE`, which adds the report of [the probe build](#the-probe-build). It is for the board tests and is not what the installation runs. |
| `build --stock` | `esp32s3dev_16MB_opi` | `stock-built.bin` | WLED's own environment from WLED's files as they are at the pinned commit, with no patch applied. |

Before building, the tool brings WLED's tracked files back to the pinned commit, applies
every patch of `firmware/patches/`, and writes `platformio_override.ini` into WLED's folder
from `firmware/platformio_override.ini.in`, with the repository's path in place of
`@REPO@`. That file adds the two environments and changes nothing of WLED's own; everything
it does not name, the board, the platform, the partition table and the flash settings, is
inherited from WLED's environment. The usermod and the core are used where they are, as
libraries outside WLED's folder: the build compiles `core/src/*.cpp` from `core/`, with the
compiler flags of the environment, and nothing is copied. `core/library.json` is what lets
PlatformIO take `core/` as a library. A repository path with a space in it is refused.

A second build reuses what the work folder holds and fetches nothing. `--verbose` shows
every command of the build. PlatformIO's output goes to standard error; the one line on
standard output names the image:

```
/Users/you/odrig/build/firmware/out/odrig-firmware.bin: 1194544 bytes, SHA-256 de6908aa...
```

### flash

```
python3 firmware/fw.py flash --image build/firmware/out/stock-built.bin --expect wled
```

Writes a built image to the board over USB and prints what the board answers afterwards.

1. The image and its `.sha256` must be there and agree, and the image must fit the
   application partition.
2. The tool reads the board's partition table and checks the layout: `layout-mismatch`.
3. It clears the boot selection data, so that the board starts the first application
   partition, and writes the image there. esptool compares a checksum of what it wrote and
   restarts the board.
4. It waits up to 20 seconds, or as long as `--wait SECONDS` says, for the answer: with
   `--expect wled`, for an image of
   `build --stock`, WLED's handshake, the line `WLED ` and a number in answer to the byte
   `v`; with `--expect probe` the probe build's report; without the option the firmware's
   reply to `status`.

Without `--image` the image is `build/firmware/out/odrig-firmware.bin`. The bootloader, the
partition table and storage are not written: WLED's settings and the installed show stay.

### restore-stock

```
python3 firmware/fw.py restore-stock
python3 firmware/fw.py restore-stock --full
```

Brings back the official WLED 16.0.1 build and prints WLED's handshake, for example
`WLED 2606300`. It writes `WLED_16.0.1_ESP32-S3_16MB_opi.bin` to the first application
partition in the way `flash` does. Before it touches the board it checks the SHA-256 of
every file it is about to write against the tracked list `firmware/stock.sha256`; a missing
file is `stock-missing` and a changed one `checksum-mismatch`.

The three stock files are not tracked. They are taken from `firmware/wled-16.0.1/`, or from
the folder given with `--stock-dir`. The application image is the release asset of WLED
16.0.1 and can be fetched again from WLED's release page.

With `--full` the tool also writes `bootloader_s3.bin` at `0x0` and `partitions_s3_16m.bin`
at `0x8000`, in the same esptool call, and checks the layout in the stock partition table
and not in the board's. The bootloader is written with the flash size esptool finds on the
chip in its header, 16 MB on this board; every other file goes to the flash as it is.

Storage is not written, so WLED's settings and the show it played before are still there.

### install-show

```
node converter/odrig.js pack --show shows/example/show.json --mapping mapping/legs-2.json \
    --sources animations --out build/example-show
python3 firmware/fw.py install-show build/example-show
```

Puts a show folder, the installed file set of [show.md](show.md), into the folder `/odrig`
of the board's storage, checks what was written, restarts the board and prints the board's
reply to `status`. The status is 0 when the reply reports a valid show and 1 when it
reports a reason. The tool waits 20 seconds for that reply, or as long as `--wait SECONDS`
says: the core checks every file at start, which takes 38 seconds for 9 MB of animations.

1. The folder is checked before the board is touched: it must be a valid installed file
   set as the readers of the converter judge it, and hold no other file. The reason of a
   refusal is the converter's, for example `file-missing`. `--no-check` installs any flat
   folder of files, for trying what the board does with an invalid show.
2. The tool reads the partition table and takes the place and size of `spiffs` from it.
3. It gets the storage as it is now into `build/firmware/storage/`: it takes the newest
   image it kept there when esptool has the chip confirm that storage has that image's
   checksum, which takes 17 seconds, and reads the whole partition otherwise, which takes
   64 seconds.
4. In that image it removes `/odrig` with everything in it, creates it again and writes the
   files of the folder. The file system keeps the disk version it had. Files that do not
   fit are `no-space`, and nothing has been written to the board then. An image that
   already holds exactly these files is left as it is.
5. It checks the new image: `/odrig` holds exactly the files of the folder, byte for byte,
   and every file outside `/odrig` is as it was.
6. It writes the blocks that changed, neighbouring ones joined, in one esptool call, has
   the chip compare the whole partition with the new image, and restarts the board.
   esptool is told that these blocks are data: it would otherwise take a block that begins
   with the first byte of a program image for a program and refuse it.

A copy of storage from before the write and the new image stay in
`build/firmware/storage/`, named by time; the newest eight images are kept. The new image
is one of them only once the board holds it. Every file of
storage outside `/odrig`, WLED's settings among them, keeps its content.

Every show installed on the board while one 60-LED strip is fed from the board's 3.3 V pin
must have a brightness of 40 or less in its `show.json`. The tool does not check this; the
board tests do, for every show they install.

### read-show

```
python3 firmware/fw.py read-show build/show-from-board
```

Copies the files of `/odrig` on the board into a folder that is new or empty, prints each
name with its size, and restarts the board. The folder can then be compared with the one
the emulator ran:

```
diff -r build/example-show build/show-from-board
```

### test

```
python3 firmware/fw.py test
```

Runs the suite in `tests/firmware/`: every `test_*.py` file there, found by discovery. It
needs no board, no network connection and nothing outside the work folder.

### test-board

```
python3 firmware/fw.py test-board
```

Runs the suite in `tests/board/`, found by discovery in the same way. It needs the board on
USB and writes to it: it flashes the firmware, the probe build and stock WLED, and installs
shows, each with a brightness of 40 or less; a brighter show is refused before the tool is
started. It builds an image the work folder does not hold. Its last step leaves the board
with the firmware and the example show at brightness 32, playing. A run takes about half
an hour. Without a board it stops with `no-board` and runs nothing.

### test-air

```
python3 firmware/fw.py test-air --http 4.3.2.1
```

Runs the suite in `tests/air/`, found by discovery. It needs the board on USB and this Mac
joined to the board's Wi-Fi network; `ADDRESS` is the board's address on that network,
`4.3.2.1` on the board's own access point. Joining the network is done by a person. The
suite sends commands over HTTP and through the port and compares them, asks WLED's own
interface for its information, and once saves WLED's LED settings, with the pin of the last
output changed, to see the mapping's outputs come back; WLED then stores the mapping's
outputs as its LED settings. Without a board, or when the address answers no command, it
stops with `no-board` and runs nothing.

## From nothing to a playing board

With the board on USB, from the repository root:

```
python3 firmware/fw.py build
python3 firmware/fw.py flash
node converter/odrig.js pack --show shows/example/show.json --mapping mapping/legs-2.json \
    --sources animations --out build/example-show
python3 firmware/fw.py install-show build/example-show
python -m odrigctl --port /dev/cu.usbmodem101 status
```

The first command also sets up the tools and fetches WLED, which needs the network once.
`pack` is the converter's command of [converter.md](converter.md), which needs Node.js 20
or later as `node` and nothing else; `shows/example/show.json`
has brightness 128, so for a strip fed from the board's 3.3 V pin pack a copy of it with a
brightness of 40 or less. The example show is for today's build of two legs. The show for
the target build of twenty legs, 60 x 60, is the demo show: [emulator.md](emulator.md),
"Two shows to run", gives the commands that pack it into `build/demo-20/show`. After
`install-show` the board plays the show from every power-on, with no command sent. To go
back to stock WLED:

```
python3 firmware/fw.py restore-stock
```

## What the firmware does

The firmware is WLED with one usermod, `firmware/usermod/`, that hosts the core of
[core.md](core.md). The usermod decides nothing about files, time or commands; it only
carries.

**At start** the usermod starts the core on the files of the folder `/odrig` of storage:
`mapping.json`, `show.json` and the `.odrg` files, as `install-show` put them there. It
gives the core a file in the pieces the core asks for, of at most 512 bytes, and never
holds a whole file. The core's memory comes from the chip's internal memory, and from the
external memory only when the internal memory has none. The time the core is given is the
milliseconds since the chip started, from a 64-bit clock. The firmware never writes,
creates or deletes a file in `/odrig`.

**An invalid show** is the core's matter, as in the emulator: the LEDs stay dark, `status`
reports the reason text of [reasons.md](reasons.md), "The core", and every command is still
answered.

**The port.** Every byte the board receives on its USB serial port goes to the core,
unchanged and in order, and every reply of the core is written back; the firmware writes
nothing else. So the command tool of [emulator.md](emulator.md) works on the board as on
the emulator:

```
python -m odrigctl --port /dev/cu.usbmodem101 status
{"ok":true,"on":true,"brightness":32,"playing":3,"animation":1,"fps":50,"error":null}
```

WLED's own serial handling is switched off: no Adalight, no TPM2, no Improv, no JSON over
serial, no answer to WLED's single-letter commands. The chip's own bootloader still prints
a few lines at a reset; the command tool skips every line that is not a reply.

**Commands over HTTP.** WLED's web server answers `POST /odrig` as
[commands.md](commands.md) defines it and as the emulator does; the body goes to the same
core the port reaches:

```
curl --data-binary 'play 2' -H 'Content-Type: application/octet-stream' http://4.3.2.1/odrig
{"ok":true}
python -m odrigctl --http 4.3.2.1 status
```

| Request | Answer |
|---|---|
| `POST /odrig` | Status 200, content type `application/json`, and the reply line as the core returned it, with its newline, also for a reply with `"ok":false`. |
| Any other method on `/odrig` | Status 405 with `Allow: POST`. |
| A longer path, such as `/odrig/x` | Status 404. |
| `POST /odrig` on a board whose core could not start | Status 503. |

Of a body longer than 128 bytes the first 128 are passed on, which the core answers with
`line-too-long`. What follows a `?` is ignored. WLED adds `Access-Control-Allow-Origin: *`
to every response.

**The content type of a request matters on the board.** WLED's web server takes a body
apart as form fields, before any handler sees it, when the content type is
`application/x-www-form-urlencoded`, and when it is `text/plain` and the body looks like
`name=value`. With any other content type the core gets the body byte for byte. With those
two it gets it byte for byte as long as the body has none of the characters `&`, `=`, `+`
and `%` and no zero byte, which holds for every valid command. `odrigctl` sends
`application/octet-stream`. `curl --data` sends the form type; that works for every valid
command, and `--data-binary` with the header above is exact for every body.

**Wi-Fi is WLED's.** The usermod changes nothing of WLED's Wi-Fi behaviour or settings.
With no network to join configured, WLED opens its access point about two seconds after
start; the board's address on it is `4.3.2.1`. The name and the password of the access
point are WLED's settings. The usermod keeps WLED's captive portal answering, which WLED
itself does only outside its live mode. WLED's pages, its JSON interface and its updates
through its own interface keep working; while WLED writes a new firmware, the usermod reads
no file and sends nothing to the LEDs.

**WLED's information** (`/json/info`, and the Info page of its interface) reports the
access point as active in `wifi.ap`, the release name `odrig_ESP32-S3_16MB_opi`, and three
entries of the usermod:

| Entry | Value |
|---|---|
| `odrig show` | `ok`, or the reason the show is invalid, as `status` reports it. |
| `odrig outputs` | `<working>/<legs>`, and ` leg <n> pin <p>` for each output that does not work. |
| `odrig start` | The milliseconds the core took to start. |

**The outputs** are set from the mapping file. When the core has started with a valid
mapping, the usermod replaces WLED's outputs with one output for each leg, in the order of
the mapping file, on the leg's pin, with the leg's number of LEDs, for WS2812B LEDs with
the colour order green, red, blue. Whatever outputs WLED's stored settings hold, these are
the outputs after start; WLED's settings file is not written for it. When WLED's LED
settings are saved while the firmware runs, the mapping's outputs are put back in the same
pass of WLED's loop. With an invalid mapping the usermod leaves WLED's outputs as they are
and keeps them dark.

On the ESP32-S3 the first four legs of the mapping file get WLED's four RMT outputs and the
next sixteen its parallel driver, so the board can drive 20 legs. Stock WLED uses the
parallel driver for eight outputs; the patch of [What the firmware changes in
WLED](#what-the-firmware-changes-in-wled) switches it to the sixteen it can carry. An output
that cannot be made, for a twenty-first leg or a pin the board cannot use, does not work;
the other outputs do, and the core runs unchanged.

**Playback.** A task of the usermod's own, named `odrig`, on the chip's other processor
core, asks the core for a refresh, again after a millisecond while none is due. When the
core has produced one, WLED's loop copies it into the outputs at once, also while the
refresh before it is still on the wire: an output keeps what it is sending apart from what
it is given. Then the task may ask for the next refresh, and the loop sends the copy as
soon as the outputs can take new data. So the core's work for a frame, reading, decoding
and placing every LED, runs beside the send of the frame before it. The core keeps one
picture of LED data, which is why the task waits for the copy; every refresh the core
counts is so sent to the outputs, and `fps` in `status` is the board's real rate. A refresh goes to the outputs directly: each leg's bytes to that
leg's output, LED number n of the leg to position n of the output. WLED's pixel buffer, LED
map, matrix layout, gamma correction, white balance and segments take no part, and the
outputs are set to WLED's full brightness before every refresh, so the only scaling of a
colour value is the core's.

**WLED is kept from the LEDs.** The usermod holds WLED in its live mode, the one network
pixel senders use, in which WLED runs no effect, no preset, no playlist and no transition,
and checks at every pass that WLED is still in it. WLED's switch, its brightness slider and
its live override therefore do not change the LEDs; only the commands of
[commands.md](commands.md) do.

**The current limiter stays active.** WLED's limiter acts inside every send, with the
maximum current of WLED's LED settings, 850 mA unless it was changed, less 120 mA for the
chip, and 55 mA for one LED at full white. It counts 1 mA for every LED at rest. When its
estimate is above the maximum it dims the refresh; `status` still reports the core's
brightness.

> With the twenty legs of the target, 3,600 LEDs, the estimate at rest alone is 3,600 mA.
> With WLED's maximum of 850 mA the limiter then holds every LED at its lowest level,
> whatever plays: as WLED's source has it, every channel of a colour that is lit is then
> sent as 1 of 255. The same holds for every mapping of 730 LEDs or more. Before twenty
> legs are lit, the maximum current must be raised to what the power supply gives, in
> WLED's LED settings, "Maximum PSU Current". The firmware does not change it. With two
> legs, 360 LEDs, the limiter also dims a bright picture such as Hello world, at any
> brightness at which the estimate passes 730 mA.

The limiter is also part of the time a refresh takes: when it dims, it reads and writes
every LED of every output once more. With 3,600 LEDs that is about 8 ms of the 16.3 ms a
send takes; see [Verified on the board](#verified-on-the-board).

**Calls to the core** are made one at a time: a lock is held for every call after the
start. The task holds it for as long as the core works on a refresh, 9 to 17 ms with a
dense 60 x 60 clip and longer when a file is opened, so a command waits for one request at
most: the port hands the core a whole line under one hold of the lock, and a command over
HTTP is one call. The legs are read from the core once, at the start, so the loop needs no
lock to know them.

## What the firmware changes in WLED

| Changed | Left as it is |
|---|---|
| The LEDs show only the core's data. WLED's effects, presets, playlists, its boot preset and its nightlight do not run. | Wi-Fi, the access point and all network settings. |
| The outputs are the mapping's. WLED's LED output settings are replaced by them when WLED's LED settings are saved. | The web interface, the JSON interface and WebSocket. |
| WLED's switch, its brightness slider and its live override do not change the LEDs. | The current limiter and its maximum in WLED's LED settings. |
| The USB serial port speaks only [commands.md](commands.md): WLED's serial handling, Adalight, TPM2, Improv and JSON over serial, is switched off. | The file system and every file of WLED on it. |
| WLED's information shows the three `odrig` entries and the release name `odrig_ESP32-S3_16MB_opi`. | Updates through WLED's own interface. |
| The audio usermod of the stock build is not included. | Buttons, relay and infrared settings. |
| The web server also answers `POST /odrig`. | Every page and address WLED serves. |

One patch changes files of WLED, `firmware/patches/010-sixteen-parallel-outputs.patch`,
which `build` and `build --probe` apply and `build --stock` does not. Stock WLED drives
twelve LED outputs on the ESP32-S3: four through its RMT driver and eight through its
parallel driver, the chip's LCD unit, used in the eight-lane form of the LED library
NeoPixelBus. The LCD unit has sixteen data lines and the library has the sixteen-lane form
of the same method. The patch changes three files, and nothing for another chip:

| File of WLED | Change |
|---|---|
| `wled00/const.h` | For the ESP32-S3, `WLED_MAX_I2S_CHANNELS` is 16 in place of 8. WLED's limit of digital outputs, the sum with the four RMT channels, so becomes 20. |
| `wled00/bus_wrapper.h` | For the ESP32-S3, the types of the parallel outputs are built on the library's sixteen-lane methods. |
| `wled00/FX_fcn.cpp` | For the ESP32-S3, WLED's estimate of the memory of its outputs counts the common buffer of the parallel driver as sixteen lanes of two bytes. |

The usermod cannot do this from outside: the limits are constants compiled into WLED, and
the type of the parallel outputs is chosen inside WLED. WLED's LED settings page shows the
new limits, which it gets from the firmware.

## The probe build

The probe build exists so that a program can check what the LEDs are given without eyes on
them. It answers the line `#probe` on the port with one JSON line, shown here on several:

```json
{"probe":1,"start_ms":95,"heap":135736,"realtime":1,"loops":235,"sent":50,"gap_ms":20,
 "poll_us":578,"send_us":16525,"poll_total_us":28021,"send_total_us":816291,
 "overwritten":0,"limited":69,"limit_ma":730,"used_ma":3600,"wire_us":[5712,5713],
 "ap":1,"error":null,
 "outputs":[{"leg":1,"pin":1,"count":180,"ok":true,"driver":"rmt","crc":"7b7d9750","pulses":4320}]}
```

| Member | Meaning |
|---|---|
| `start_ms` | The milliseconds the core took to start: to read and check the whole installed file set. |
| `heap` | The free internal memory of the chip, in bytes. |
| `realtime` | 1 while WLED is held in its live mode with no override, else 0. |
| `loops`, `sent` | The passes of the usermod's loop and the refreshes sent, in the last full second. |
| `gap_ms`, `poll_us`, `send_us` | The longest time between two sends, the longest request for a refresh and the longest send, since the last `#probe`. A send is the copy into the outputs and WLED's show together; the wait for the outputs between the two is not in it. |
| `poll_total_us`, `send_total_us` | The time all requests for a refresh and all sends took, in the last full second. |
| `overwritten` | The sends before which an output no longer held what it held after the send before it: something else wrote to the outputs. Some outputs are read back after each send and again before the next, each in its turn: as many as have 200 LEDs together, and one at least. |
| `limited` | The sends since the last `#probe` in which WLED's current limiter dimmed the LEDs. |
| `limit_ma`, `used_ma` | The current the limiter allows the LEDs, WLED's maximum less 120 mA for the chip, and its estimate for the last send. |
| `wire_us` | The shortest and the longest time, since the last `#probe`, from the end of a send until the parallel driver had finished its transfer and could take data again, in microseconds; `null` when no output is on the parallel driver or none was sent. A timer looks at the driver every tenth of a millisecond. An output of 180 LEDs is 570 bytes on the wire with its reset, 5.7 ms. |
| `ap` | 1 while WLED's access point is up, else 0. |
| `error` | The reason the show is invalid, as `status` reports it, or `null`. |
| `outputs` | For each of WLED's outputs: the leg, the pin, the number of LEDs, whether it works, its driver, `rmt`, `parallel` or `none`, and the two members below. |
| `crc` | Of an output: the CRC-32 of the colours it held when it was last read back after a send, as WLED gives them back: red, green and blue for each LED. With twenty outputs of 180 LEDs every output is read back once in twenty sends, 0.4 seconds; an output that was not read back yet is read for the report. |
| `pulses` | Of an output: the number of rising edges on its pin during one refresh, counted by the chip's pulse counter, or `null` before it was counted. A WS2812B bit is one pulse, so an output of 180 LEDs gives 4,320 whatever the colours. One output is counted at each send, each in its turn. The counter is put on the input of the pin's pad and leaves what the pin puts out alone. It counts to 32,767: 1,365 LEDs. |

A `#probe` that arrives between the copy of a refresh into the outputs and its show is
answered right after the show, so that a report never describes colours that were not
sent. The report of twenty outputs is a line of 2,300 characters; the port writes it in the
pieces it takes without waiting and reads no command until it is written.

While the limiter does not dim, an output gives back exactly the bytes it was sent. When it
dims, the output gives back the dimmed colours as WLED restores them, which at the
limiter's lowest level is 128 for a channel that stayed lit and 0 for one that did not.

The port holds bytes at the start of a line back for as long as they are a beginning of
`#probe` and a newline. The complete line is answered by the usermod and does not reach the
core; every other byte is passed on to the core, unchanged and in order.

The probe build plays as the firmware does. Reading the outputs back takes time, so its
own rate can be a refresh or two below the firmware's.

## Measurements on the board

Taken by the board test `tests/board/test_measure.py` with the probe build, at brightness
32, over ten seconds for each show; the test writes them to
`build/firmware/out/measurements.json`. They were taken on 2026-10-12 with the firmware as
it is: the core asked for refreshes by a task of its own, and with the target file twenty
outputs, four through WLED's RMT driver and sixteen through its parallel driver. The one
60-LED strip was wired, on leg 1; the other outputs sent to pins with nothing on them.
WLED's maximum current was 850 mA, so on the target file the limiter dimmed every refresh.

| Show | Working outputs | Files | `install-show` | Start of the core | Passes of the loop a second | Refreshes a second | `fps` in `status` | Longest gap | Request for a refresh, mean | longest | Send, mean | longest | Free internal memory |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Example show, two legs, 360 LEDs | 2 of 2 | 3,096 bytes | 36 s | 171 ms | 2,293 to 2,365 | 50 | 50 | 43 ms | 0.98 ms | 23.3 ms | 1.03 ms | 1.22 ms | 202,760 bytes |
| Demo show, the target file, 3,600 LEDs | 20 of 20 | 3,968 bytes | 37 s | 174 ms | 367 to 420 | 50 | 50 | 42 ms | 1.79 ms | 23.7 ms | 15.7 ms | 16.1 ms | 126,520 bytes |
| Dense 60 x 60 clip of 10 s, compressed, the target file | 20 of 20 | 1,385,398 bytes | 59 s | 6,011 ms | 507 to 851 | 28 to 37 | 33 | 42 ms | 25.9 ms | 48.1 ms | 20.0 ms | 31.8 ms | 126,624 bytes |
| The same clip, uncompressed | 20 of 20 | 1,463,868 bytes | 59 s | 4,183 ms | 140 to 152 | 44 or 45 | 45 | 36 ms | 12.9 ms | 33.6 ms | 19.8 ms | 33.1 ms | 126,592 bytes |
| 9 MB of dense 60 x 60 clips: six of 10 s and one of 5 s, compressed | 20 of 20 | 9,009,652 bytes | 165 s | 38,747 ms | 555 to 982 | 25 to 35 | 32 | 60 ms | 26.6 ms | 68.5 ms | 20.0 ms | 33.3 ms | 126,212 bytes |

The files of a row are the whole show folder. The mean request is the time the core worked
in a second over the refreshes sent in it; at a rate below 50 one request decodes every
frame since the one before, so it is more than the work for one frame.

What the figures say:

- **The firmware drives twenty outputs.** With the target file all twenty work, on pins 1
  to 18, 21 and 47.
- **Every rate is inside the 20 to 50 a second the owner accepts.** A show that is not
  dense plays at 50 on twenty legs as on two. The dense clip, in which every LED changes
  at every frame, plays at 44 or 45 uncompressed and at 28 to 37 compressed in the probe
  build; the firmware itself reports 45 to 47 and 36 to 42, see
  [Verified on the board](#verified-on-the-board). A dense file plays faster uncompressed.
- **A send to twenty outputs** takes 15.7 ms with the limiter's dimming of every LED in
  it, and 20 ms while the core decodes a dense clip on the chip's other processor core.
  The LEDs need 5.7 ms on the wire after that.
- **The long requests** are those in which the core opens a file, at the start of every
  loop of an animation and at every turn of a cycle: 23 ms for a small file, and up to
  69 ms with dense clips, when the frames that came due meanwhile are decoded in the same
  request.
- **The start takes as long as the files are large.** The core checks every file at start
  by decoding it: 174 ms for the demo show, 6.0 s for one dense 60 x 60 clip of 10 seconds
  compressed and 4.2 s uncompressed, and 39 s for a storage filled with 9 MB of such
  clips. For that time the LEDs are dark and the board answers nothing, on the port or on
  the network; WLED opens its access point only afterwards. `install-show` and `flash`
  wait 20 seconds for the board's answer; `--wait SECONDS` makes them wait longer for a
  large show.
- **`install-show`** takes 36 seconds for a small show: twice 17 seconds for the chip to
  work out the checksum of storage, before and after, and the write between. One dense
  clip takes a minute and 9 MB take three.
- **Memory.** 126,000 bytes of the chip's internal memory are free with twenty outputs of
  180 LEDs and the core, 203,000 with two.

Not measured, because the hardware is not wired: light on any leg but the one strip on
pin 1, and the current the LEDs really draw.

**What the firmware of seed 04 measured, kept as a record.** These figures were taken on
2026-10-11, before the target became twenty upright legs: on the bench file, and on a
mapping of ten row legs of three rows of 60, 1,800 LEDs, on pins 1 to 10, with a dense
60 x 30 clip. That firmware asked the core in WLED's loop and drove ten outputs, and the
limiter dimmed every refresh of the ten row legs.

| Show | Files | `install-show` | Start of the core | Passes of the loop a second | Refreshes a second | `fps` in `status` | Longest gap | Request for a refresh, mean | longest | Send, mean | longest |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Example show, two legs, 360 LEDs | 3,096 bytes | 36 s | 171 ms | 2,275 to 2,341 | 49 to 51 | 50 | 39 ms | 0.81 ms | 18.8 ms | 1.04 ms | 1.12 ms |
| Dense 60 x 30 clip of 10 s, compressed, ten row legs, 1,800 LEDs | 725,779 bytes | 48 s | 3,107 ms | 325 to 423 | 49 to 51 | 50 | 41 ms | 6.61 ms | 26.5 ms | 7.67 ms | 7.86 ms |
| The same clip, uncompressed | 766,815 bytes | 48 s | 2,163 ms | 578 to 655 | 49 to 51 | 50 | 37 ms | 4.72 ms | 21.4 ms | 7.68 ms | 7.81 ms |
| 9 MB of dense clips: twelve of 10 s and one of 4 s, compressed | 9,001,905 bytes | 178 s | 37,821 ms | 344 to 426 | 48 to 51 | 50 | 44 ms | 6.63 ms | 29.0 ms | 7.68 ms | 7.85 ms |


With 1,800 LEDs the core's work for one dense frame was 6.6 ms compressed and 4.7 ms
uncompressed and a send to ten outputs 7.7 ms, and both fitted into the 20 ms of a frame
in one loop.

## The regions of the flash

The board has WLED's 16 MB layout. The tool reads the partition table before it writes and
touches these regions only:

| Region | Address | Size | Written by |
|---|---|---|---|
| Bootloader | `0x0` | up to `0x8000` | `restore-stock --full` only |
| Partition table | `0x8000` | `0x1000` | `restore-stock --full` only |
| Boot selection (`otadata`) | `0xE000` | `0x2000` | erased by `flash` and `restore-stock` |
| First application (`app0`) | `0x10000` | `0x300000` | `flash`, `restore-stock` |
| Storage (`spiffs`) | `0x610000` | `0x9E0000` | `install-show`, changed blocks only |

`nvs` at `0x9000`, the second application partition at `0x310000` and the core-dump
partition at `0xFF0000` are never written. The whole flash is never erased, and no tool
writes a fuse of the chip or starts a program that can. esptool is given an address only
after the tool has checked it against this table.

## Rolling back

`python3 firmware/fw.py restore-stock` brings back stock WLED 16.0.1, with its settings and
its show as they were. `--full` also brings back the stock bootloader and partition table,
for a board whose first 64 KB were changed by something else.

The last resort is the factory backup of the board: one image of the whole 16 MB flash with
its own checksum file, kept beside this repository. No tool reads or writes it. It is
written back by hand with esptool, at address `0x0`, after its checksum has been compared.

## The owner's checks

What a program on this Mac cannot establish: what the LEDs show, and what a device joined to
the board's Wi-Fi network gets. Each step says what to do and what must be seen. The number
in brackets is the criterion the step covers: in steps 1 to 4 a criterion of Requirement 16
of `docs/specs/04-p1-firmware-build-with-the-player/requirements.md`, and in steps 5 and 6,
marked `seed 05`, criterion 3 of Requirement 18 of
`docs/specs/05-p0-canvas-60-by-60/requirements.md`.

Seed 04 is completed when steps 1 to 4 are done. Steps 5 and 6 stay listed as open and do
not hold seed 05 open; criterion 4 of that Requirement 18 says so. Nothing a
program can establish holds seed 05 open either: the board tests pass with the target
file, and the rate does not hold it open: the board plays a dense 60 x 60 clip at 36 to 47
refreshes a second, and the owner accepts any rate from 20 to 50. See
[Verified on the board](#verified-on-the-board).

1. **The show plays from power-on (16.1).** Install the example show at the brightness
   chosen for the power supply in use; one strip fed from the board's 3.3 V pin allows 40
   at most. Switch the board's power off and on and send no command. *Seen:* the words
   HELLO WORLD, upright and readable from left to right, and the bouncing square take turns
   every 15 seconds.
2. **49 refreshes a second with two legs wired (16.2).** With legs 1 and 2 wired and the
   example show playing, run `python -m odrigctl --port /dev/cu.usbmodem101 status`.
   *Seen:* `"fps":49` or more, `"error":null`, and the picture across both legs.
3. **Commands over the board's own network (16.7).** After power-on, find the board's Wi-Fi
   network, join it with this Mac, with the board still on USB, and run
   `python3 firmware/fw.py test-air --http 4.3.2.1`. *Seen:* the suite ends with `OK`.
   One of its tests saves WLED's LED settings; see [test-air](#test-air).
4. **WLED's interface beside the player (16.7).** With a phone joined to the board's
   network, open `http://4.3.2.1/`. *Seen:* WLED's interface opens, and its Info page shows
   the entries `odrig show` with `ok`, `odrig outputs` with `2/2` for two legs, and
   `odrig start`.
5. **A strip on the parallel driver shows its picture (seed 05, 18.3).** The one wired
   strip is on pin 1, and pin 1 is the first leg of both tracked mapping files: one of the
   four RMT outputs. The mapping below has twenty legs of one row of 60 and lists the leg
   on pin 1 last. That makes pin 1 the twentieth output, the sixteenth lane of the parallel
   driver. Save it as `build/lane/mapping.json`:

   ```json
   {
     "version": 1,
     "width": 60,
     "legs": [
       {"leg": 2, "pin": 2, "first_led": "right", "rows": [20]},
       {"leg": 3, "pin": 3, "first_led": "right", "rows": [19]},
       {"leg": 4, "pin": 4, "first_led": "right", "rows": [18]},
       {"leg": 5, "pin": 5, "first_led": "right", "rows": [17]},
       {"leg": 6, "pin": 6, "first_led": "right", "rows": [16]},
       {"leg": 7, "pin": 7, "first_led": "right", "rows": [15]},
       {"leg": 8, "pin": 8, "first_led": "right", "rows": [14]},
       {"leg": 9, "pin": 9, "first_led": "right", "rows": [13]},
       {"leg": 10, "pin": 10, "first_led": "right", "rows": [12]},
       {"leg": 11, "pin": 11, "first_led": "right", "rows": [11]},
       {"leg": 12, "pin": 12, "first_led": "right", "rows": [10]},
       {"leg": 13, "pin": 13, "first_led": "right", "rows": [9]},
       {"leg": 14, "pin": 14, "first_led": "right", "rows": [7]},
       {"leg": 15, "pin": 15, "first_led": "right", "rows": [6]},
       {"leg": 16, "pin": 16, "first_led": "right", "rows": [5]},
       {"leg": 17, "pin": 17, "first_led": "right", "rows": [4]},
       {"leg": 18, "pin": 18, "first_led": "right", "rows": [3]},
       {"leg": 19, "pin": 21, "first_led": "right", "rows": [2]},
       {"leg": 20, "pin": 47, "first_led": "right", "rows": [1]},
       {"leg": 1, "pin": 1, "first_led": "right", "rows": [8]}
     ]
   }
   ```

   Its canvas is 60 x 20. Write Hello world for it, pack it at brightness 32 and install
   it:

   ```
   mkdir -p build/lane/sources
   python -m odrig.generators.hello_world build/lane/sources/hello.json --mapping build/lane/mapping.json
   printf '{"version": 1, "brightness": 32, "items": [{"id": 1, "file": "hello.odrg"}], "start": 1}\n' > build/lane/show.json
   node converter/odrig.js pack --show build/lane/show.json --mapping build/lane/mapping.json \
       --sources build/lane/sources --out build/lane/show
   python3 firmware/fw.py install-show build/lane/show
   ```

   The leg on pin 1 has the row y = 8, the bottom row of the letters, and its first LED is
   the right end of that row. *Seen:* the strip shows that row. Read from the end away from
   the board to the wired end, these of its 60 LEDs are lit, `X`, and these are dark, `.`:

   ```
   ...X..X.XXXX.XXXX.XXXX..XX.....X...X..XX..X..X.XXXX.XXX.....
   ```

   The lit LEDs glow faintly, and their colours move along the strip towards the wired
   end: the limiter counts the 1,200 LEDs of this mapping and holds every LED at its lowest
   level. `python -m emulator build/lane/show` shows the same row on its page, as the row
   of leg 1. Afterwards install the example show again, as in step 1.
6. **Twenty wired legs show the demo show (seed 05, 18.3).** With the twenty legs of the
   target wired as [mapping.md](mapping.md) has them, and WLED's maximum current raised to
   what the power supply gives, pack the demo show with the commands of
   [emulator.md](emulator.md), "Two shows to run", giving `pack` a copy of
   `shows/demo-20/show.json` that has the brightness chosen for the power supply. Install
   it with `python3 firmware/fw.py install-show build/demo-20/show`, switch the board's
   power off and on and send no command. *Seen:* the words HELLO WORLD stand upright in the middle of
   the canvas, in the rows 28 to 33, readable from left to right across the legs 2 to 19.
   After 15 seconds a square of four LEDs takes their place and runs along the diagonal,
   from the top-left corner to the bottom-right one and back, over every one of the twenty
   legs. The two take turns every 15 seconds.
   `python -m odrigctl --port /dev/cu.usbmodem101 status` reports `"playing":3` and
   `"error":null`, and WLED's Info page shows `odrig outputs` with `20/20`. The `fps` of
   that reply is worth writing down: the rate of the demo show on the board has not been
   measured.

Before twenty legs are lit, raise WLED's maximum current as [What the firmware
does](#what-the-firmware-does) says.

What a program established without the owner, over USB: the board plays the installed show
from its start with no command sent, as `status` reports `playing` 3 after every restart;
the outputs hold the bytes the emulator records for the same show; `status` reports 49 or
more with the example show, with one strip wired; WLED reports its access point as up; and
the tests of `test-air` that send commands pass against the emulator. For steps 5 and 6:
with twenty legs in the mapping the firmware makes twenty working outputs, each of the
twenty pins carries 24 pulses for every LED of a refresh, and the parallel driver is busy
after a send for the time its LEDs take on the wire. That the pulses have the right widths,
and that an LED on a lane of the parallel driver lights, no program can see. The six steps
above have not been done.

## Verified on the board

What the design assumed and an early task then tried, on this Mac and on the board. The
letters are those of the design's table "Assumed, to be verified by an early task".

The first part, down to "Twenty outputs", is the record of seed 04. It was tried with the
firmware of that seed, before the target became twenty upright legs: on the bench file,
and on mappings of ten row legs on pins 1 to 10, with a dense 60 x 30 clip. From "Twenty
outputs" on, the page has what seed 05 found for the target: twenty legs, 60 x 60.

| # | Assumption | What was found |
|---|---|---|
| A1 | PlatformIO 6.1.17 installs and runs under this Mac's Python, 3.14. | It installs under Python 3.14.6 with every package at the version WLED pins, `pip check` finds nothing broken, and `pio --version` prints `PlatformIO Core, version 6.1.17`. |
| A2 | `nodeenv` puts Node 20.18 into the work folder. | Not tried: `nodeenv` fetches Node.js from nodejs.org, and the tool fetches from PyPI only. The package `nodejs-wheel` 20.18.0 from PyPI is used in its place: `node --version` from the work folder prints `v20.18.0`, and `npm --version` prints `10.8.2`. See "Seed 04: Where Node.js comes from" in [drifts.md](drifts.md). |

| A3 | `PLATFORMIO_CORE_DIR`, `PLATFORMIO_BUILD_CACHE_DIR`, `npm_config_cache` and `PIP_CACHE_DIR` keep everything inside the work folder. | They do. After the first build the work folder held 1.9 GB of PlatformIO's packages, 152 MB of build cache, 3.8 MB of npm's cache and 58 MB of pip's, and the lists of the home folder from before and after differed only in entries of other programs; see below. |
| A4 | WLED's environment builds from source on this Mac and the result runs on the board. | `build --stock` built `stock-built.bin`, 1,232,912 bytes, in 92 seconds the first time, with everything fetched, and in 4 seconds the second time. The release image has 1,232,640 bytes. Flashed, it answered `v` with `WLED 2605010`, the number in WLED's source at the tag; the release image answers `WLED 2606300`. It played the preset the release image had played. |
| A5 | The C++ flag the build really uses. | `-std=gnu++11`, with `-fno-exceptions -fno-rtti -Os`, in the compiler command of every one of the 235 C++ files of the build, `wled00/wled.cpp` among them. C files are compiled with `-std=gnu99`. |
| A6 | Writing only `app0` and erasing `otadata` leaves a board that starts the new image. | It does: `flash` and `restore-stock` each took 15 seconds and the board answered `v` after each. The storage partition, read whole before and after the pair, had the same 10,354,688 bytes. |
| A7 | esptool 5.4.0 reads, writes, erases and verifies this board over its USB serial and JTAG unit, and resets it into and out of the bootloader. | It does. Reading the partition table takes half a second, reading storage 64 seconds. |

| A8 | PlatformIO accepts the usermod as a `symlink://` library outside WLED's folder, and WLED's check of linked modules passes. | It does: the build lists `odrig` with the path `firmware/usermod`, compiles its five files from there, and WLED's check reports one library linked as a module and one usermod entry. The part of A8 about the core is task 5's. |
| A9 | `strip.finalizeInit()` and `strip.makeAutoSegments()` called from a usermod replace the outputs, and ten outputs on pins 1 to 10 are all valid: four RMT and six parallel. | They do. The probe build reports ten working outputs on pins 1 to 10 with 180 LEDs each, the first four `rmt` and the other six `parallel`, in place of the two outputs of WLED's stored settings. |
| A10 | In live mode nothing of WLED writes to the outputs between two refreshes, and the outputs hold exactly the colours written. | Nothing else writes: `overwritten` stayed 0 over 30 seconds, and `realtime` was 1. With ten legs of 180 LEDs the limiter dims every refresh to its lowest level, so the outputs do not hold the bytes written; each holds exactly what that dimming makes of its own leg's bytes, for all ten outputs. Exact bytes are shown in task 6, with fewer LEDs. |
| A11 | With `WLED_DISABLE_ADALIGHT` the firmware writes nothing to the port by itself, and the usermod can read and write the port from its loop. | It does: nothing arrived in 5 seconds without a command, the byte `v` got no answer, and `#probe` was answered every time. |
| A12 | A pass of WLED's loop and the push of 1,800 LEDs fit well inside 20 ms. | They do. Over 20 seconds the loop made 981 to 1,006 passes a second, a send of 1,800 LEDs took 7.2 ms at most with the limiter's dimming in it, the longest time between two sends was 25 ms, and 49 to 51 refreshes were sent in every second. 227,940 bytes of internal memory were free. |

| A13 | littlefs-python 0.19.0 edits the board's storage image so that WLED still mounts it. | As far as task 4 shows: after `install-show` the board started, sent its 49 refreshes a second, and its storage still had the checksum of the image the tool wrote, so WLED mounted the file system and neither formatted nor changed it. The file system has disk version 2.0 and keeps it. That the firmware reads the files of `/odrig` is task 5's. `install-show` took 36 seconds with the kept image taken, plus the wait for the reply. |

The core in the firmware, tried with the firmware and the probe build that host it:

- **The core compiles unchanged** (A8). PlatformIO takes `core/` as the library
  `odrig_core` where it is and compiles every `core/src/*.cpp` with exactly the compiler
  flags of `wled00/wled.cpp`, `-std=gnu++11 -fno-exceptions -fno-rtti -Os` among them, and
  the same macro definitions. The compiler gave no warning for a file of the core. No file
  of `core/src` or `core/include` was changed.
- **The firmware reads the files of `/odrig`** (A13). With the dim example show installed,
  `status` on the board answers `"playing":3,"animation":1,"error":null`, and the four
  invalid folders of the install test each give the reason the emulator gives.
- **The start of the core** took 171 ms for the dim example show, as the probe build
  reports it. 211,696 bytes of internal memory were free afterwards.
- **A request for a refresh** took 0.2 to 0.6 ms at the longest in most seconds, and 18.5 ms
  in the seconds in which the core opened a file: at the start of every loop of an
  animation and at every turn of the cycle. The loop made about 3,100 passes a second with
  nothing sent to the LEDs.
- **The replies** of one session with every command were those of the emulator for the same
  folder, `fps` aside.

The outputs and playback, tried with the probe build and with the firmware:

- **Exact bytes** (A10). With a one-frame show in which every pixel has a colour of its
  own, on the two-leg mapping, each output's CRC-32 was that of the bytes the emulator
  recorded for its leg: at the brightness 40, 32 and 1 of the show file, after every
  `brightness` command from 0 to 40, and after `off` and `on`. The limiter did not dim
  these pictures.
- **Ten outputs.** On a mapping of ten row legs of 18 LEDs for each leg, pins 1 to 10, all
  ten outputs, four `rmt` and six `parallel`, held exactly their own leg's bytes. On a mapping
  of ten row legs of three rows of 60 on the same pins, 180 LEDs for each leg, all ten
  outputs work and each holds what the limiter's lowest level makes of its own leg's
  bytes; `status` still reports the show's brightness.
- **A pin the board cannot use.** With three legs on pins 1, 60 and 2, the outputs of legs 1
  and 3 hold their bytes and are refreshed 49 times a second or more; the output of leg 2
  does not work; `status` reports no reason.
- **An invalid mapping.** WLED's own two outputs stay, dark, and no refresh is sent.
- **Nothing else writes** to the outputs: `overwritten` stayed 0 over 30 seconds of the
  example show, `realtime` 1.
- **The rate.** With the firmware `status` reported 49 or 50 in every one of ten seconds
  for the dim example show, for the dense 60 x 30 clip on ten row legs, compressed and
  uncompressed, and while `status` was asked five times a second.

Measured with the probe build over 25 seconds each, at brightness 32:

| Show | Start of the core | Passes of the loop a second | Refreshes a second | Longest gap | Request for a refresh, mean | longest | Send, mean | longest |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Example show, two legs, 360 LEDs | 171 ms | 2,725 to 2,934 | 49 to 51 | 38 ms | 0.80 ms | 18.8 ms | 0.76 ms | 1.21 ms |
| Dense 60 x 30 clip, compressed, ten row legs, 1,800 LEDs | 3,105 ms | 359 to 475 | 49 to 51 | 41 ms | 6.61 ms | 26.5 ms | 7.67 ms | 7.86 ms |
| Dense 60 x 30 clip, uncompressed, ten row legs, 1,800 LEDs | 2,163 ms | 652 to 746 | 49 to 51 | 38 ms | 4.73 ms | 21.2 ms | 7.68 ms | 7.86 ms |

A request for a refresh is the core's work for one frame: reading the next part of the
file from storage, decoding it, and placing 1,800 LEDs. The long requests are the ones in
which a file is opened or the file system goes on to another block; they delay one refresh
and skip none or one. The sends on ten row legs include the limiter's dimming of all 1,800
LEDs; without it a send is about half as long. With the first form of the loop, which
asked the core only once the outputs were free, the probe build sent 46 to 49 refreshes of
the compressed dense clip a second; see "Seed 04: Asking the core while the LEDs are still
being written" in [drifts.md](drifts.md).

Commands over HTTP were written and not tried on the board: no program on this Mac may join
the board's network. The tests of `tests/air/test_http.py` pass against the emulator, which
answers `POST /odrig` by the same rules; `tests/air/test_wled.py` has not run anywhere. The
probe build reports `ap` 1 within seconds of its start, which a board test checks: WLED's
access point is up. A14 stays the owner's check.

With `BusManager::setBrightness(255)` taken out of the usermod, the outputs were scaled by
WLED's own brightness and the CRC tests failed for every output.

With the usermod's two calls that hold the LEDs taken out, WLED kept its own two outputs and
played its own show: the report had `realtime` 0, two outputs, and `overwritten` rising by
50 a second.

The probe build reported `ap` 1 from the first second after its start: WLED's access point
was up, with no network to join configured.

**Twenty outputs.** What the design of seed 05 assumed, in its table "Assumed, to be
verified by the spike", and what the first task of that seed found. It was tried with the
probe build, the patch of [What the firmware changes in WLED](#what-the-firmware-changes-in-wled)
applied, and a mapping of twenty row legs of three rows on pins 1 to 18, 21 and 47. One
60-LED strip was wired, on pin 1; the other nineteen pins had nothing on them.

| # | Assumption | What was found |
|---|---|---|
| A1 | The library's sixteen-lane method, at the commit WLED pins, sends correct data on all sixteen lanes. | As far as a program can see, it does. On each of the sixteen pins of the parallel driver the chip's pulse counter counted 24 pulses for every LED of a refresh: `pulses` 432 with legs of 18 LEDs and 4,320 with legs of 180. The driver was busy after a send for the time the bytes take on the wire: `wire_us` 812 to 1,019 with 18 LEDs, which are 84 bytes with the reset and 0.84 ms, and 5,677 to 5,952 with 180 LEDs, 570 bytes and 5.7 ms. That the pulses have the right widths, and that LEDs on a lane light, no program can see. |
| A2 | With the patch WLED makes four RMT and sixteen parallel outputs on pins 1 to 18, 21 and 47, and all twenty work. | It does: twenty working outputs in the order of the legs, `rmt` for the first four and `parallel` for the next sixteen. With legs of 18 LEDs, which the limiter does not dim, every output held exactly the bytes the emulator records for its leg. With legs of 180 LEDs the limiter dims every refresh, `used_ma` 3,600 against `limit_ma` 730, and every output held exactly what its lowest level makes of its own leg's bytes. No pin had to be replaced. With the patch file moved out of `firmware/patches/` and the probe build built again, outputs 1 to 12 worked and outputs 13 to 20 did not. |
| A3 | The pulse counter can count a pin an output drives without disturbing the output. | It can, on RMT pins and on pins of the parallel driver, when it is given no pin of its own and the input of the pin's pad is routed to it; the chip's driver would make a pin it is given an input. The counts were the same at every send, and the CRC of what the outputs hold did not change. |
| A4 | Enough internal memory is left for WLED's web server and Wi-Fi; 100 KB free is taken as enough. | `heap` 135,736 with twenty outputs of 180 LEDs, the core and a show of one file; 203,164 with twenty outputs of 18 LEDs. The design expected about 190 KB. WLED's access point came up, `ap` 1. The core's blocks all came from internal memory. |
| A5 | A send to twenty outputs happens 49 times a second or more with a picture that does not change. | Not with the loop of seed 04, which began a send when the outputs could take data: the probe build then sent 41 or 42 a second. A send takes 16.4 ms, 4.1 ms for the copy into the outputs and 12.3 ms for WLED's show with the limiter's dimming of 3,600 LEDs, and the LEDs are on the wire for 5.7 ms after it. With the copy made while the last refresh is still on the wire, as [What the firmware does](#what-the-firmware-does) has it now, 49 to 51 were sent in every one of ten seconds, 20 ms was the longest time between two sends, and `overwritten` stayed 0. |

The dense 60 x 60 clip of 10 seconds on the same twenty legs, with the probe build of that
task, in which the request for a refresh is still made in WLED's loop, over ten seconds
each at brightness 32:

| Clip | File | Start of the core | Refreshes a second | `fps` in `status` | Longest gap | Request for a refresh, mean | longest | Send, mean | longest |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Compressed | 1,383,766 bytes | 6,010 ms | 21 to 23 | 21 | 57 ms | 28.1 ms | 38.8 ms | 16.3 ms | 16.5 ms |
| Uncompressed | 1,462,236 bytes | 4,182 ms | 31 or 32 | 32 | 47 ms | 13.7 ms | 28.7 ms | 16.3 ms | 16.5 ms |

A request is longer than the work for one frame here, because the loop is slower than the
clip: every request decodes all the frames since the one before, 2.3 of them on average
for the compressed file and 1.6 for the uncompressed one. One frame is 12.3 ms of the
core's work compressed and 8.6 ms uncompressed: reading it from storage, decoding it and
placing 3,600 LEDs. With the 16.3 ms of a send that is more than the 20 ms there are, so
the request has to run beside the send. See "Seed 05: What the spike found, and a refresh
that is copied while the last one is on the wire" in [drifts.md](drifts.md).

**The request in a task of its own.** The second task of seed 05 moved the request for a
refresh out of WLED's loop, as the design of that seed plans it for a loop that cannot hold
the rate. `status` of the firmware, in ten seconds for each form of the dense 60 x 60 clip
of 10 seconds, at brightness 32, in refreshes a second:

| Clip | Request in WLED's loop, twenty row legs | Request in the task, the target file |
|---|---:|---:|
| Compressed, 1,383,766 bytes | 22 to 24 | 36 to 42 |
| Uncompressed, 1,462,236 bytes | 32 to 34 | 45 to 47 |

**What the owner accepts.** Any rate from 20 to 50 refreshes a second is fine on the
board, for any content; only a rate above 50 or below 20 is a fault. Every figure of this
page is inside that. A dense file plays faster uncompressed than compressed on the board,
45 to 47 against 36 to 42, and the uncompressed file is 5 percent larger. A show that is
not dense plays at the full rate: the demo show on the target file is refreshed 50 times a
second, and so is the bench show. The board tests assert from 20 to 50 for the demo show
on the target and for the dense 60 x 60 clip in both forms, with one count more allowed at
the top, because a second can count one refresh more than was due in it; they go on
asserting 49 or more for the bench show and for a picture that does not change on twenty
outputs, which the board reaches.

Measured with the probe build and the task over 25 seconds each, at brightness 32, on the
target file except for the bench show:

| Show | Start of the core | Passes of the loop a second | Refreshes a second | `fps` in `status` | Longest gap | The core's work in a second | Longest request | Send, mean | longest |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Bench show, two legs, 360 LEDs | 171 ms | 2,295 to 2,460 | 50 | 50 | 43 ms | 26 to 67 ms | 23.3 ms | 0.75 ms | 1.22 ms |
| Demo show, twenty legs, 3,600 LEDs | 174 ms | 368 to 439 | 49 to 51 | 50 | 43 ms | 61 to 106 ms | 24.0 ms | 15.7 ms | 16.1 ms |
| Dense 60 x 60 clip, compressed | 6,011 ms | 515 to 982 | 26 to 36 | 36 | 57 ms | 765 to 903 ms | 52.3 ms | 20.0 ms | 32.1 ms |
| Dense 60 x 60 clip, uncompressed | 4,183 ms | 134 to 161 | 44 or 45 | 46 | 36 ms | 552 to 607 ms | 33.5 ms | 19.8 ms | 33.4 ms |

126,500 bytes of internal memory were free with the target file. The probe build's own
work costs the compressed clip refreshes that the firmware does not lose: 26 to 36 against
the firmware's 36 to 42.

- The task works: a task on processor core 0 reads the files of `/odrig` while WLED's loop
  runs on core 1, the outputs get every refresh the core counts, `overwritten` stays 0,
  and commands are answered. No watchdog restarted the chip, in these measurements and in
  the whole board suite.
- The two cores slow each other. Side by side a send takes 20 ms where it takes 16.3 ms
  alone, and the core's work for a dense frame 12 to 13 ms uncompressed and 16 to 17 ms
  compressed where it takes 8.6 ms and 12.3 ms alone. On core 0 the core's work and then
  the copy of 4.1 ms have to fit into the 20 ms of a frame; they fit for the uncompressed
  clip and not for the compressed one, and the send of 20 ms on core 1 leaves no room for
  anything else. Once a refresh is late the core decodes every frame up to the one that
  is due, so the rate settles well below what the sums suggest.
- Reading the file is not what takes the time: with the file read 4,096 bytes at a time in
  place of the 512 the core asks for, every figure was the same, and so was the start of
  the core, 6.0 s. The work is the core's decoding and placing, and WLED's show.
- A send is 4.1 ms for the copy and 12.3 ms for WLED's show, of which the limiter's
  dimming of 3,600 LEDs is about 8 ms. On the bench the limiter dims every refresh, because
  WLED's maximum of 850 mA is below the 3,600 mA it counts for 3,600 LEDs at rest.

What could make dense content faster. None of it was tried, and nothing asks for it:

- Raising WLED's maximum current to what the power supply of the installation gives, in
  WLED's LED settings, which has to be done before twenty legs are lit anyway. The limiter
  then dims only a picture that is too bright, and a send that it does not dim is about
  8 ms shorter. The firmware does not change that setting.
- Building the core alone at `-O2`, as a library of its own, and leaving WLED's files at
  the platform's `-Os`. The core is compiled at `-Os` in the firmware and at `-O2` on the
  Mac. The whole firmware must not be built at `-O2`: see the next paragraph.
- Measuring where the cores lose time to each other. The chip's instruction cache has 16
  KB for both.

**A firmware built at another optimisation level took the board off USB.** To see whether
the compiler's level `-O2` in place of the platform's `-Os` buys the missing time, the
probe build was built once with `-O2` for every file and flashed. It does not start: WLED
stops with a null pointer on processor core 1 a moment after its start, and the chip
restarts, several times a second. For the first minute the port showed the restarts. After
that the board no longer answers on its USB port at all, and esptool cannot bring it into
its bootloader: `Failed to connect to ESP32-S3: No serial data received`. The USB device is
still listed by the Mac. WLED counts restarts that follow each other quickly, and after
five it puts its settings file back from its copy, after ten it renames `/cfg.json` to
`/rst.cfg.json`, which leaves WLED with its default settings, and then it writes its
settings files to the port again and again. The change of the build was taken back before
anything was committed; `firmware/platformio_override.ini.in` is as it was, and the images
in `build/firmware/out/` are built from the tracked sources.

What brings a board in that state back, by a person at the desk:

1. Unplug the board's USB cable and plug it in again.
2. At once: `python3 firmware/fw.py flash`, which writes the firmware of
   `build/firmware/out/odrig-firmware.bin`, or `python3 firmware/fw.py restore-stock`.
3. If WLED's settings were renamed, `/rst.cfg.json` in the board's storage holds them, and
   so do the storage images the tool keeps in `build/firmware/storage/`; `install-show`
   leaves every file outside `/odrig` as it finds it.
4. `python3 firmware/fw.py test-board`.

That is how this board came back. The owner unplugged it and plugged it in, it answered at
once, and the firmware as committed was flashed. WLED had renamed its settings file:
storage held `/rst.cfg.json` with the 392 bytes `/cfg.json` had before, WLED's LED outputs
and its start preset and no Wi-Fi setting. The file was given its name back in the board's
storage with the tool's own steps for storage, read, change in the image, check, write the
changed block, compare; afterwards every file outside `/odrig` had the bytes it had before
the trial.

**The target file on the board.** The board tests then ran with `mapping/legs-20.json`,
the column-leg file of the target, with the probe build and the firmware of the second
task of seed 05:

- Twenty working outputs of 180 LEDs on pins 1 to 18, 21 and 47, four `rmt` and sixteen
  `parallel`; each holds exactly what the limiter's lowest level makes of its own leg's
  bytes as the emulator records them for the target file; `pulses` is 4,320 on every pin
  and `wire_us` between 4,500 and 7,500; a picture that does not change is sent 49 times
  or more in every one of ten seconds, and `overwritten` stays 0.
- With a column-leg file of twenty legs of three columns of 6 LEDs, which the limiter does
  not dim, every output holds exactly its leg's bytes as the emulator records them, and
  `pulses` is 432 on every pin. With the `first_led` of leg 7 changed to `"top"` in the
  copy of the mapping the emulator recorded, and not in the one installed, output 7 and no
  other differed from the recording.
- `status` of the firmware in ten seconds each: 50 for the demo show on the target file,
  36 to 42 for the dense 60 x 60 clip compressed and 45 to 47 uncompressed.
- The whole board suite, 30 tests, passes; its last step leaves the firmware and the dim
  example show, playing from its start.

**From nothing.** With `build/firmware/` removed, `python3 firmware/fw.py build` set up the
tools, fetched WLED and built the firmware in 2 minutes. The lists of the home folder from
before and after were the same in every entry. The image has the size it had, 1,211,600
bytes; its bytes are not those of the build before, so its SHA-256 differs from one fresh
work folder to the next, while a build repeated in the same work folder gives the same
bytes. That image was flashed, the dim example show installed, and both suites run.

The board's partition table, read with the tool, is the one WLED's source has for this
environment and byte for byte the stock file `partitions_s3_16m.bin`:

| Name | Type | Offset | Size |
|---|---|---|---|
| `nvs` | data | `0x9000` | `0x5000` |
| `otadata` | data | `0xE000` | `0x2000` |
| `app0` | application | `0x10000` | `0x300000` |
| `app1` | application | `0x310000` | `0x300000` |
| `spiffs` | data | `0x610000` | `0x9E0000` |
| `coredump` | data | `0xFF0000` | `0x10000` |

`restore-stock --full` was not run on the board. In its place esptool compared the board's
flash with the three stock files as the tool would write them, without writing: all three
are what the board holds. The stock bootloader file itself has the flash size 8 MB in its
header, and the board's bootloader 16 MB; that one byte and the checksum that follows from
it are what esptool sets when it writes a bootloader for the chip it finds.

Opening the port as the command tool does, RTS lowered before DTR, does not reset the
board: WLED's uptime went on counting across exchanges.

The home folder was listed before and after the first `setup`, with the modification time of
every entry, and so were the folders in it where caches usually land: `~/.cache`, `~/.npm`,
`~/.config`, `~/.local`, `~/Library/Caches`, `~/Library/Application Support` and
`~/Library/Preferences`. One entry differed: `~/Library/Application Support/Claude`, the
folder of the application that ran the commands. No `~/.platformio` and no `~/.buildcache`
appeared, and `~/.npm` and `~/Library/Caches/pip` kept their times. The same lists from
before and after the first build differed in that entry and in
`~/Library/Preferences/com.apple.xpc.activity2.plist`, a file of macOS.
