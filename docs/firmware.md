# The firmware

The firmware is WLED 16.0.1 for the ESP32-S3, built from WLED's own source with one usermod
added that hosts the core of [core.md](core.md). One tool, `firmware/fw.py`, sets up the
tools the build needs, fetches WLED, builds, flashes, restores stock WLED and installs a
show into the board's storage.

This page covers [what the tool needs](#what-the-tool-needs), [the work folder](#the-work-folder),
the [commands](#commands) of the tool, [what the firmware does](#what-the-firmware-does),
[the probe build](#the-probe-build), the [measurements](#measurements-on-the-board) made
on the board, [the regions of the flash](#the-regions-of-the-flash) the tool writes,
[rolling back](#rolling-back) and what was [verified on the board](#verified-on-the-board).

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
python -m odrig pack --show shows/example/show.json --mapping mapping/legs-2.json \
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
USB and writes to it: it flashes images and restores stock WLED. Without a board it stops
with `no-board` and runs nothing.

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
next eight its parallel driver, so the board can drive 12 legs. An output that cannot be
made, for a thirteenth leg or a pin the board cannot use, does not work; the other outputs
do, and the core runs unchanged.

**Playback.** The usermod asks the core for a refresh in every pass of its loop, until the
core has produced one; that refresh is sent as soon as the outputs can take new data, and
only then is the core asked again. Every refresh the core counts is so sent to the
outputs, and `fps` in `status` is the board's real rate. A refresh goes to the outputs
directly: each leg's bytes to that leg's output, LED number n of the leg to position n of
the output. WLED's pixel buffer, LED map, matrix layout, gamma correction, white balance
and segments take no part, and the outputs are set to WLED's full brightness before every
refresh, so the only scaling of a colour value is the core's.

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

> With ten legs of 180 LEDs the estimate at rest alone is 1,800 mA. With WLED's maximum of
> 850 mA the limiter then holds every LED at its lowest level, whatever plays. Before ten
> legs are lit, the maximum current must be raised to what the power supply gives, in
> WLED's LED settings, "Maximum PSU Current". The firmware does not change it. With two
> legs, 360 LEDs, the limiter also dims a bright picture such as Hello world, at any
> brightness at which the estimate passes 730 mA.

**Calls to the core** are made one at a time: a lock is held for every call after the
start.

## The probe build

The probe build exists so that a program can check what the LEDs are given without eyes on
them. It answers the line `#probe` on the port with one JSON line, shown here on several:

```json
{"probe":1,"start_ms":0,"heap":227940,"realtime":1,"loops":1003,"sent":50,"gap_ms":21,
 "poll_us":13,"send_us":7213,"overwritten":0,"limited":67,"limit_ma":730,"used_ma":1800,
 "ap":1,"error":null,
 "outputs":[{"leg":1,"pin":1,"count":180,"ok":true,"driver":"rmt","crc":"54135885"}]}
```

| Member | Meaning |
|---|---|
| `start_ms` | The milliseconds the core took to start: to read and check the whole installed file set. |
| `heap` | The free internal memory of the chip, in bytes. |
| `realtime` | 1 while WLED is held in its live mode with no override, else 0. |
| `loops`, `sent` | The passes of the usermod's loop and the refreshes sent, in the last full second. |
| `gap_ms`, `poll_us`, `send_us` | The longest time between two sends, the longest request for a refresh and the longest send, since the last `#probe`. |
| `poll_total_us`, `send_total_us` | The time all requests for a refresh and all sends took, in the last full second. |
| `overwritten` | The sends before which an output no longer held what it held after the send before it: something else wrote to the outputs. One send in five is checked. |
| `limited` | The sends since the last `#probe` in which WLED's current limiter dimmed the LEDs. |
| `limit_ma`, `used_ma` | The current the limiter allows the LEDs, WLED's maximum less 120 mA for the chip, and its estimate for the last send. |
| `ap` | 1 while WLED's access point is up, else 0. |
| `error` | The reason the show is invalid, as `status` reports it, or `null`. |
| `outputs` | For each of WLED's outputs: the leg, the pin, the number of LEDs, whether it works, its driver, `rmt` or `parallel`, and `crc`, the CRC-32 of the colours it holds as WLED gives them back: red, green and blue for each LED. |

While the limiter does not dim, an output gives back exactly the bytes it was sent. When it
dims, the output gives back the dimmed colours as WLED restores them, which at the
limiter's lowest level is 128 for a channel that stayed lit and 0 for one that did not.

The port holds bytes at the start of a line back for as long as they are a beginning of
`#probe` and a newline. The complete line is answered by the usermod and does not reach the
core; every other byte is passed on to the core, unchanged and in order.

The probe build plays as the firmware does. Reading the outputs back takes time, so its
own rate can be a refresh or two below the firmware's.

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

## Measurements on the board

Taken by the board test `tests/board/test_measure.py` with the probe build, at brightness
32, over ten seconds for each show; the test writes them to
`build/firmware/out/measurements.json`. The one 60-LED strip was wired, on leg 1; the other
outputs sent to pins with nothing on them. WLED's maximum current was 850 mA, so on ten legs
the limiter dimmed every refresh.

| Show | Files | `install-show` | Start of the core | Passes of the loop a second | Refreshes a second | `fps` in `status` | Longest gap | Request for a refresh, mean | longest | Send, mean | longest |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Example show, two legs, 360 LEDs | 3,096 bytes | 36 s | 171 ms | 2,275 to 2,341 | 49 to 51 | 50 | 39 ms | 0.81 ms | 18.8 ms | 1.04 ms | 1.12 ms |
| Dense 60 x 30 clip of 10 s, compressed, ten legs, 1,800 LEDs | 725,779 bytes | 48 s | 3,107 ms | 325 to 423 | 49 to 51 | 50 | 41 ms | 6.61 ms | 26.5 ms | 7.67 ms | 7.86 ms |
| The same clip, uncompressed | 766,815 bytes | 48 s | 2,163 ms | 578 to 655 | 49 to 51 | 50 | 37 ms | 4.72 ms | 21.4 ms | 7.68 ms | 7.81 ms |
| 9 MB of dense clips: twelve of 10 s and one of 4 s, compressed | 9,001,905 bytes | 178 s | 37,821 ms | 344 to 426 | 48 to 51 | 50 | 44 ms | 6.63 ms | 29.0 ms | 7.68 ms | 7.85 ms |

What the figures say:

- **Decoding keeps up.** The core's work for one frame of the dense clip on 1,800 LEDs,
  reading from storage, decoding and placing every LED, takes 6.6 ms on average for the
  compressed file and 4.7 ms for the uncompressed one. The firmware's `status` reported 49
  or 50 refreshes in every second for both, on ten outputs. The uncompressed format is not
  needed for speed.
- **Ten outputs work.** A send to ten outputs of 180 LEDs takes 7.7 ms with the limiter's
  dimming of every LED in it. The LEDs need 5.4 ms on the wire after that; the core works
  on the next frame meanwhile.
- **The long requests** are those in which the core opens a file, at the start of every
  loop of an animation and at every turn of a cycle, or in which the file system goes on
  to another block. They delay one refresh by up to 29 ms and cost one refresh of a second
  at most.
- **The start takes as long as the files are large.** The core checks every file at start
  by decoding it: 171 ms for the example show, 3.1 s for one dense clip of 10 seconds, and
  38 s for a storage filled with 9 MB of dense clips. For that time the LEDs are dark and
  the board answers nothing, on the port or on the network; WLED opens its access point
  only afterwards. `install-show` and `flash` wait 20 seconds for the board's answer;
  `--wait SECONDS` makes them wait longer for a large show.
- **`install-show`** takes 36 seconds for a small show: twice 17 seconds for the chip to
  work out the checksum of storage, before and after, and the write between. 9 MB take
  three minutes.

Not measured, because the hardware is not wired: light on legs 2 to 10, and the current the
LEDs really draw.

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

## Verified on the board

What the design assumed and an early task then tried, on this Mac and on the board. The
letters are those of the design's table "Assumed, to be verified by an early task".

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
- **Ten outputs.** On a ten-leg mapping of 18 LEDs for each leg, pins 1 to 10, all ten
  outputs, four `rmt` and six `parallel`, held exactly their own leg's bytes. On
  `mapping/legs-10.json`, 180 LEDs for each leg, all ten outputs work and each holds what
  the limiter's lowest level makes of its own leg's bytes; `status` still reports the
  show's brightness.
- **A pin the board cannot use.** With three legs on pins 1, 60 and 2, the outputs of legs 1
  and 3 hold their bytes and are refreshed 49 times a second or more; the output of leg 2
  does not work; `status` reports no reason.
- **An invalid mapping.** WLED's own two outputs stay, dark, and no refresh is sent.
- **Nothing else writes** to the outputs: `overwritten` stayed 0 over 30 seconds of the
  example show, `realtime` 1.
- **The rate.** With the firmware `status` reported 49 or 50 in every one of ten seconds
  for the dim example show, for the dense 60 x 30 clip on the ten-leg mapping, compressed
  and uncompressed, and while `status` was asked five times a second.

Measured with the probe build over 25 seconds each, at brightness 32:

| Show | Start of the core | Passes of the loop a second | Refreshes a second | Longest gap | Request for a refresh, mean | longest | Send, mean | longest |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Example show, two legs, 360 LEDs | 171 ms | 2,725 to 2,934 | 49 to 51 | 38 ms | 0.80 ms | 18.8 ms | 0.76 ms | 1.21 ms |
| Dense 60 x 30 clip, compressed, ten legs, 1,800 LEDs | 3,105 ms | 359 to 475 | 49 to 51 | 41 ms | 6.61 ms | 26.5 ms | 7.67 ms | 7.86 ms |
| Dense 60 x 30 clip, uncompressed, ten legs, 1,800 LEDs | 2,163 ms | 652 to 746 | 49 to 51 | 38 ms | 4.73 ms | 21.2 ms | 7.68 ms | 7.86 ms |

A request for a refresh is the core's work for one frame: reading the next part of the
file from storage, decoding it, and placing 1,800 LEDs. The long requests are the ones in
which a file is opened or the file system goes on to another block; they delay one refresh
and skip none or one. The sends on ten legs include the limiter's dimming of all 1,800
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
