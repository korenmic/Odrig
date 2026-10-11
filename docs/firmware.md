# The firmware

The firmware is WLED 16.0.1 for the ESP32-S3, built from WLED's own source with one usermod
added that hosts the core of [core.md](core.md). One tool, `firmware/fw.py`, sets up the
tools the build needs, fetches WLED, builds, flashes, restores stock WLED and installs a
show into the board's storage.

This page covers [what the tool needs](#what-the-tool-needs), [the work folder](#the-work-folder),
the [commands](#commands) of the tool, [the probe build](#the-probe-build),
[the regions of the flash](#the-regions-of-the-flash) the tool writes,
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
  storage/         storage images read from the board
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
python3 firmware/fw.py flash [--port P] [--image PATH] [--expect status|wled|probe]
python3 firmware/fw.py restore-stock [--port P] [--full] [--stock-dir DIR]
python3 firmware/fw.py test
python3 firmware/fw.py test-board [--port P]
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
| `verify-failed` | What is in the flash differs from what was written. |
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
| `build` | `odrig` | `odrig-firmware.bin` | The firmware: WLED's environment `esp32s3dev_16MB_opi` with the usermod of `firmware/usermod/` in place of WLED's audio usermod, WLED's serial handling switched off, and the release name `odrig_ESP32-S3_16MB_opi`. |
| `build --probe` | `odrig_probe` | `odrig-probe.bin` | The probe build: the firmware with the flag `ODRIG_PROBE`, which adds the report of [the probe build](#the-probe-build). It is for the board tests and is not what the installation runs. |
| `build --stock` | `esp32s3dev_16MB_opi` | `stock-built.bin` | WLED's own environment from WLED's files as they are at the pinned commit, with no patch applied. |

Before building, the tool brings WLED's tracked files back to the pinned commit, applies
every patch of `firmware/patches/`, and writes `platformio_override.ini` into WLED's folder
from `firmware/platformio_override.ini.in`, with the repository's path in place of
`@REPO@`. That file adds the two environments and changes nothing of WLED's own; everything
it does not name, the board, the platform, the partition table and the flash settings, is
inherited from WLED's environment. The usermod is used where it is, as a library outside
WLED's folder; nothing is copied. A repository path with a space in it is refused.

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
4. It waits up to 20 seconds for the answer: with `--expect wled`, for an image of
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
| `start_ms` | The milliseconds the player took to start. |
| `heap` | The free internal memory of the chip, in bytes. |
| `realtime` | 1 while WLED is held in its live mode with no override, else 0. |
| `loops`, `sent` | The passes of the usermod's loop and the refreshes sent, in the last full second. |
| `gap_ms`, `poll_us`, `send_us` | The longest time between two sends, the longest request for a refresh and the longest send, since the last `#probe`. |
| `overwritten` | The sends before which an output no longer held what it held after the send before it: something else wrote to the outputs. |
| `limited` | The sends since the last `#probe` in which WLED's current limiter dimmed the LEDs. |
| `limit_ma`, `used_ma` | The current the limiter allows the LEDs, WLED's maximum less 120 mA for the chip, and its estimate for the last send. |
| `ap` | 1 while WLED's access point is up, else 0. |
| `outputs` | For each of WLED's outputs: the leg, the pin, the number of LEDs, whether it works, its driver, `rmt` or `parallel`, and `crc`, the CRC-32 of the colours it holds as WLED gives them back: red, green and blue for each LED. |

While the limiter does not dim, an output gives back exactly the bytes it was sent. When it
dims, the output gives back the dimmed colours as WLED restores them, which at the
limiter's lowest level is 128 for a channel that stayed lit and 0 for one that did not.

In this state of the work the usermod has no player yet: it sends a fixed pattern of ten
legs on pins 1 to 10 with 180 LEDs each, no value above 40, and the port answers `#probe`
and nothing else.

**What a person sees with this build.** One 60-LED strip is wired, on leg 1. WLED's maximum
current is 850 mA, and 1,800 LEDs are estimated at 1,800 mA at rest alone, so the limiter
holds every LED at its lowest level: the 60 LEDs show a steady, very faint glow of red and
green that does not move and does not flicker, and nothing else. Nothing of WLED's own show,
the text and the square it played before, appears.

## The regions of the flash

The board has WLED's 16 MB layout. The tool reads the partition table before it writes and
touches these regions only:

| Region | Address | Size | Written by |
|---|---|---|---|
| Bootloader | `0x0` | up to `0x8000` | `restore-stock --full` only |
| Partition table | `0x8000` | `0x1000` | `restore-stock --full` only |
| Boot selection (`otadata`) | `0xE000` | `0x2000` | erased by `flash` and `restore-stock` |
| First application (`app0`) | `0x10000` | `0x300000` | `flash`, `restore-stock` |

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
