# The firmware

The firmware is WLED 16.0.1 for the ESP32-S3, built from WLED's own source with one usermod
added that hosts the core of [core.md](core.md). One tool, `firmware/fw.py`, sets up the
tools the build needs, fetches WLED, builds, flashes, restores stock WLED and installs a
show into the board's storage. [firmware-additions.md](firmware-additions.md) lists what
the firmware adds to WLED, every line of which every firmware of the project gets.

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

For `build --stick` and `build --stock`, WLED's own build then fetches what WLED's files
at the tag name. The tool chooses none of it:

| What | From |
|---|---|
| The platform `espressif32` 2024.06.00 and the Arduino core 2.0.18 | GitHub, `tasmota/platform-espressif32` and `tasmota/arduino-esp32` |
| The compilers `toolchain-xtensa-esp32s3` and `toolchain-riscv32-esp` 8.4.0, `tool-scons`, `tool-mklittlefs` | PlatformIO's registry |
| `tool-esptoolpy` 4.7.4 | GitHub, `tasmota/esptool` |
| The libraries AsyncTCP, AnimatedGIF, AsyncMqttClient, IRremoteESP8266, arduinoFFT and NeoPixelBus | PlatformIO's registry |
| The libraries NeoPixelBus, ESPAsyncWebServer, GifDecoder, esp_dmx and QuickESPNow at the commits WLED pins | GitHub, the repositories `platformio.ini` names |
| The 67 packages of WLED's `package-lock.json`, which pack the web interface | The npm registry |
| The Python packages `zopfli`, `wheel` and `tasmota-metrics`, which the platform installs into the tool's Python environment | PyPI |

### The newer software

`build` and `build --probe` build the firmware on newer software of Espressif than WLED
16.0.1 names: Arduino-ESP32 3.3.12 on ESP-IDF 5.5.5, with pioarduino's platform
55.03.312-1 and PlatformIO 6.2.0. The firmware reads its external animations from a
microSD card on that software; the USB stick's build, `build --stick`, stays on the
software known good, which WLED's files name. The newer software lives in
`build/firmware/newer/`, so the build known good and its tools stay as they are. The first
`build` fetches it; nothing of it is on a computer before. The sizes are those the sources state, about 700 MB in all; a line *named by its
manifest* is a small manifest that names the real download, which is given as its release
offers it for a Mac with Apple's processor.

| What | Version | From | Bytes |
|---|---|---|---:|
| PlatformIO, into `newer/venv`, with the packages of `firmware/requirements-newer.txt`, which pins the others at the versions WLED pins and takes them from pip's cache | 6.2.0 | `https://files.pythonhosted.org/packages/bf/98/6c5cc249129c72b076ca238a435c48b48568d866c12890e01ee50fb8f322/platformio-6.2.0-py3-none-any.whl` | 418,578 |
| PlatformIO's own SCons | `tool-scons` 4.41101.0 | `https://dl.registry.platformio.org/download/platformio/tool/tool-scons/4.41101.0/tool-scons-4.41101.0.tar.gz` | 523,448 |
| The platform | 55.03.312-1 | `https://github.com/pioarduino/platform-espressif32/releases/download/55.03.312-1/platform-espressif32.zip` | 2,128,229 |
| Arduino-ESP32 | 3.3.12 | `https://github.com/espressif/arduino-esp32/releases/download/3.3.12/esp32-core-3.3.12.tar.xz` | 42,843,632 |
| Arduino-ESP32's compiled libraries | 3.3.12 | `https://github.com/espressif/arduino-esp32/releases/download/3.3.12/esp32-core-3.3.12-libs.tar.xz` | 347,236,084 |
| The installer of ESP-IDF's tools, `tool-esp_install` | 5.3.5 | `https://github.com/pioarduino/esp_install/releases/download/v5.3.5/esp_install-v5.3.5.zip` | 54,139 |
| The compiler, `toolchain-xtensa-esp-elf`, named by its manifest | 14.2.0+20260121 | `https://github.com/pioarduino/registry/releases/download/0.0.1/xtensa-esp-elf-14.2.0_20260121.zip`, then `https://github.com/espressif/crosstool-NG/releases/download/esp-14.2.0_20260121/xtensa-esp-elf-14.2.0_20260121-aarch64-apple-darwin.tar.xz` | 1,601 and 170,666,656 |
| The debugger, `tool-xtensa-esp-elf-gdb`, which the platform installs with the compiler; named by its manifest | 17.1_20260402 | `https://github.com/pioarduino/registry/releases/download/0.0.1/xtensa-esp-gdb-17.1_20260402.zip`, then `https://github.com/espressif/binutils-gdb/releases/download/esp-gdb-v17.1_20260402/xtensa-esp-elf-gdb-17.1_20260402-aarch64-apple-darwin24.5.tar.gz` | 1,550 and 46,924,973 |
| esptool, `tool-esptoolpy`, named by its manifest | 5.4.0 | `https://github.com/pioarduino/registry/releases/download/0.0.1/esptoolpy-v5.4.0.zip`, then `https://github.com/espressif/esptool/releases/download/v5.4.0/esptool-v5.4.0-macos-arm64.tar.gz` | 989 and 62,531,864 |
| PlatformIO's home page, which the platform installs at every build | `contrib-piohome` 3.4.4 | `https://github.com/pioarduino/registry/releases/download/0.0.1/contrib-piohome-3.4.4.tar.gz` | 922,895 |
| The platform's own Python environment, `newer/pio/penv`: `uv` first, by pip | 0.13.1 | `https://files.pythonhosted.org/packages/3b/31/fad7fd2ac81954d02d33765bf8535eb320fcc2d71f2603a5c1ba0b13b8ef/uv-0.13.1-py3-none-macosx_11_0_arm64.whl` | 14,391,237 |
| Then, by `uv`, the newest that PyPI has of `pioarduino` 6.2.0 or later, `littlefs-python`, `fatfs-ng`, `pyyaml`, `rich-click`, `zopfli`, `intelhex`, `rich`, `cryptography`, `certifi`, `ecdsa`, `bitstring`, `reedsolo`, `esp-idf-size`, `esp-coredump`, `pyelftools` and `freertos-gdb`, and what they need | at the time of fetching | PyPI | about 12,000,000 |

Arduino's `SD` library, which reads the card, is part of Arduino-ESP32, and nothing of
ESP-IDF's own source is fetched.

WLED's libraries can be copied from `.pio/libdeps/odrig` to `.pio/libdeps/odrig_microsd`
and `.pio/libdeps/odrig_microsd_probe` in WLED's folder before the first build; what is
missing there PlatformIO fetches at the versions WLED names, which on 2026-10-16 were those
of the build known good. The platform takes the other compiler, `toolchain-riscv32-esp`,
only for a project with a folder `ulp`, and CMake, Ninja and ESP-IDF itself only to compile
ESP-IDF's libraries again, which the firmware's build does not do.

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
  newer/           the newer software of `build`, `build --probe` and `build --microsd`
    venv/          its Python environment: PlatformIO 6.2.0, Node.js and npm
    pio/           its PlatformIO folder: the platform, Arduino-ESP32, the compilers and
                   the platform's own Python environment
    pio-cache/     its build cache
```

Every program the tool starts gets these variables, so that nothing lands in the home
folder. `HOME` is left as it is. For `build`, `build --probe` and `build --microsd` the two folders of PlatformIO are
`build/firmware/newer/pio` and `build/firmware/newer/pio-cache`, and `PATH` begins with
`build/firmware/newer/venv/bin`; pip's and npm's caches are the same.

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

**Shared toolchains.** With the environment variable `ODRIG_TOOLS` set to a folder, its
`firmware/` folder holds what checkouts can share: `venv/`, `pio/`, `pio-cache/`,
`npm-cache/`, `pip-cache/`, `newer/`, and WLED's source as fetched, `WLED/`, which is never
patched there. Each checkout keeps `build/firmware/WLED/`, `out/`, `storage/` and
`standalone/`: its WLED copy is made from the shared one by `cp -c -R` on macOS, a
copy-on-write clone on APFS, with whatever build folder the source holds, and is patched
and built in the checkout. `ODRIG_TOOLS/setup.lock` makes a second setup wait for the
first, which `setup` says, and then skip what it did; `setup` prints the folder as
`toolchains:`. The variables above then name the shared folders. The first computer's
toolchains are in its checkout's `build/`: `ODRIG_TOOLS` set to that folder lets another
checkout build without fetching anything.

## Commands

Run from the repository root.

```
python3 firmware/fw.py setup
python3 firmware/fw.py build [--stock | --probe] [--standalone | --stick | --microsd] [--verbose]
python3 firmware/fw.py flash [--port P] [--image PATH] [--standalone] [--expect status|wled|probe] [--wait SECONDS]
python3 firmware/fw.py restore-stock [--port P] [--full] [--stock-dir DIR]
python3 firmware/fw.py big-storage [--port P] [--wait SECONDS]
python3 firmware/fw.py install-show DIR [--port P] [--no-check] [--wait SECONDS] [--dry-run] [--keep-copies DIR]
python3 firmware/fw.py set-wifi [--port P] [--settings FILE] [--wait SECONDS]
python3 firmware/fw.py set-limit [--port P] [--settings FILE] [--wait SECONDS]
python3 firmware/fw.py read-limit [--port P]
python3 firmware/fw.py install-firmware [--port P] [--settings FILE] [--limit FILE] [--wait SECONDS]
python3 firmware/fw.py read-show OUT [--port P]
python3 firmware/fw.py recover-storage [--port P] [--whole] [--wait SECONDS]
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
| `check-not-done` | The board answered, but was still reading its installed animations when the time of `--wait` was over. Nothing is wrong with what was written: the command gave up waiting. |
| `verify-failed` | What is in the flash differs from what was written, or the new storage image does not hold what it should. |
| `no-space` | The files of a show do not fit into storage. Nothing was written to the board. |
| `not-a-show-folder` | The folder to install is no folder, holds something that is no file, or holds a file the show does not name. |
| `output-not-empty` | The folder `read-show` is to write, or the folder of `install-show --keep-copies`, exists and is not an empty folder. |
| `wifi-settings-missing` | The settings file to read is not there or is not a file. |
| `wifi-settings-malformed` | The settings file is not a JSON object with exactly the strings `name` and `password`. |
| `wifi-name-invalid` | The name does not have 1 to 32 characters of printable ASCII. |
| `wifi-password-invalid` | The password does not have 8 to 63 characters of printable ASCII. |
| `wled-settings-malformed` | `/cfg.json` or `/wsec.json` in the board's storage is not a JSON object, or its `ap`, its `hw` or its `hw.led` is not an object. Nothing was written to the board. |
| `limit-settings-missing` | The limit file to read is not there or is not a file. |
| `limit-settings-malformed` | The limit file is not a JSON object with exactly the whole number `milliamps`. |
| `limit-invalid` | The limit is not from 0 to 65,535. |
| a reason of [reasons.md](reasons.md), "Shows" | The folder to install is not a valid installed file set: `mapping-missing`, `show-malformed`, `file-missing`, `size-mismatch` and the others. |
| `backup-protected` | An output path lies in the factory backup of the board, which no tool writes. |
| `cancelled` | An interrupt from the keyboard, Ctrl-C, ended the command before a change of storage was committed. The board holds its storage from before. |
| `recovery-needed` | A change of the board's storage was cut while the blocks its file system uses were written or compared, or the journal of such a change is in the work folder: run `recover-storage`. Until then every command that reads or writes the board refuses with this reason before it looks for the board. |
| `storage-changed` | `recover-storage` found the board's storage changed outside the blocks of the change it is to finish. Nothing was written. |

**The layout.** A command that reads the board's partition table, `flash`,
`install-firmware`, `install-show`, `set-wifi`, `set-limit`, `read-limit` and `read-show`,
prints first which of the two layouts of [The regions of the flash](#the-regions-of-the-flash)
it found, and the size of the storage there: `layout: WLED's, storage 10354688 bytes` or
`layout: bigger, storage 13500416 bytes`. It works on either, and writes the storage where
the table puts it.

**The port.** A command that talks to the board uses the port given with `--port`, else the
one in the variable `ODRIG_BOARD_PORT`, else the only `/dev/cu.usbmodem*` device. With no
such device, or with more than one, it stops with `no-board`. Either of the board's two
USB sockets does; see "The two USB sockets" under [What the firmware does](#what-the-firmware-does).

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
python3 firmware/fw.py build --stick
python3 firmware/fw.py build --stick --probe
python3 firmware/fw.py build --stock
```

Builds an image with PlatformIO in `build/firmware/WLED` and keeps it in
`build/firmware/out/` with its SHA-256 in a file beside it, `<image>.sha256`. An image
larger than the application partition, 3,145,728 bytes, is not kept: `image-too-large`.

| Command | Environment | Image | What it is |
|---|---|---|---|
| `build` | `odrig_microsd` | `odrig-firmware.bin` | The firmware: WLED's environment `esp32s3dev_16MB_opi` with the usermod of `firmware/usermod/` in place of WLED's audio usermod, the core of `core/`, WLED's serial handling switched off, and the release name `odrig_ESP32-S3_16MB_opi`, on [the newer software](#the-newer-software), with the code of the microSD card on GPIO39 to GPIO42 as its external storage. |
| `build --probe` | `odrig_microsd_probe` | `odrig-probe.bin` | The probe build: the firmware with the flag `ODRIG_PROBE`, which adds the report of [the probe build](#the-probe-build). It is for the board tests and is not what the installation runs. |
| `build --stick` | `odrig` | `odrig-stick.bin` | The USB stick's firmware: the same on the software known good, with the USB host for a stick on the chip's own socket in place of the card. |
| `build --stick --probe` | `odrig_probe` | `odrig-stick-probe.bin` | Its probe build. |
| `build --stock` | `esp32s3dev_16MB_opi` | `stock-built.bin` | WLED's own environment from WLED's files as they are at the pinned commit, with no patch applied. |

The firmware and its probe build are built on [the newer software](#the-newer-software):
the tool makes the newer software's Python environment first, when
`build/firmware/newer/venv` is not there or `firmware/requirements-newer.txt` changed, and
runs that environment's PlatformIO in WLED's folder, with WLED's files and the patches. The
environment `odrig_microsd` is `odrig` on the newer platform, with the card's flag
`ODRIG_DRIVE_SD_SPI` and the reader's four pins, GPIO39 for SCK, GPIO40 for MISO, GPIO41
for MOSI and GPIO42 for CS; `odrig_microsd_probe` adds `ODRIG_PROBE`. The card's code
takes the place of the USB host, and the chip's own socket stays a serial port.
[microsd.md](microsd.md) has the card, the reader's wiring, what the board sessions gave
and what is open. `build --stick` and `build --stick --probe` build the USB stick's
firmware and its probe build on the software known good, as the firmware was built until
2026-10-24; `--stick` goes with neither `--stock` nor `--standalone`, and
`flash --image build/firmware/out/odrig-stick.bin` writes it to the board.

```
python3 firmware/fw.py build --microsd
```

`build --microsd` builds the same firmware as `build` and keeps it as `odrig-microsd.bin`,
the name the board sessions of 2026-10-22 and 2026-10-23 used; it does not go with
`--stock`, `--probe`, `--stick` or `--standalone`. The image of 2026-10-22, which the board
runs, has 1,765,808 bytes and the SHA-256
`fd089753d86c92d9cbfbb2e4823d49428e4b037213b656736636b9dd9a1950a5`.

Before building, the tool brings WLED's tracked files back to the pinned commit, applies
every patch of `firmware/patches/`, and writes `platformio_override.ini` into WLED's folder
from `firmware/platformio_override.ini.in`, with the repository's path in place of
`@REPO@`. That file adds the two environments and changes nothing of WLED's own; everything
it does not name, the board, the platform, the partition table and the flash settings, is
inherited from WLED's environment. The usermod and the core are used where they are, as
libraries outside WLED's folder: the build compiles `core/src/*.cpp` from `core/`, with the
compiler flags of the environment, and nothing is copied. `core/library.json` is what lets
PlatformIO take `core/` as a library. A repository path with a space in it is refused.

`build --standalone` builds the standalone firmware, a program without WLED, as a
project of its own in `build/firmware/standalone/`, and keeps `odrig-standalone.bin`;
with `--probe` it builds its probe build, `odrig-standalone-probe.bin`. The tool writes
that project's `platformio.ini` from `firmware/standalone/platformio.ini.in`, with the
repository's path and the path of WLED's checkout filled in: the platform, the board, the
flash settings and the libraries are the ones WLED has for this board, and the partition
table is WLED's own file. WLED's files are not patched for it and none is compiled.
`--standalone` does not go with `--stock`. The standalone firmware is being built; for
now it is a trial program, see [Verified on the board](#verified-on-the-board).

WLED 16.0.1 is not made for Arduino-ESP32 3. The firmware builds on it after these
changes, none of which touches a driver of the LEDs, the Wi-Fi or the storage, and none of
which the stick's build sees:

- Left out of the firmware, as this installation uses none of it: WLED's DMX input with its
  library `esp_dmx`, the infrared remote with `IRremoteESP8266`, and WLED's own RMT driver
  `NeoESP32RmtHI`; the four RMT outputs take NeoPixelBus's RMT driver, by
  `WLED_USE_SHARED_RMT`.
- `ESP32_ARDUINO_NO_RGB_BUILTIN` keeps Arduino-ESP32's newer RMT driver out, which ESP-IDF
  does not let start beside the older one that NeoPixelBus uses.
- `firmware/newer/odrig_newer.h`, read first by every source of the firmware, and
  `firmware/patches/020-newer-software.patch`, whose every change is held by
  `ESP_IDF_VERSION_MAJOR >= 5`: the names the newer software changed, and what its checks
  stop at the start: the legacy ADC driver beside the new one, lwIP's raw API without its
  lock, and an address compared with `0U`.

On 2026-10-16 the firmware with the USB host built on the newer software, for a trial of
a stick through a hub: 1,822,304 bytes, 56.2% of the firmware slot, with 21.5% of the
static memory, and its probe build 1,748,992 bytes. On 2026-10-22 the firmware with the
card built as `odrig-microsd.bin`, 1,765,808 bytes. On 2026-10-24, with the card's free and
total space, `build` made `odrig-firmware.bin` of 1,771,808 bytes, SHA-256
`1752f8216be641f0c60907f96a64bf2cd3669ed4e25923d34e0e795c596e19bf`, and `build --microsd`
the same bytes; `build --probe` made `odrig-probe.bin` of 1,758,624 bytes and
`build --stick` `odrig-stick.bin` of 1,289,264 bytes. None of them was flashed.

With the texts and clocks of [core.md](core.md), "Texts" and "Clocks", on the seeds of
2026-10-24 joined, `build` made `odrig-firmware.bin` of 1,799,040 bytes on 2026-10-25,
SHA-256 `d3b4c516b8d6f7df55cfd7240fd876335bc751554569544c71fdda8909faa022`: 19,760 bytes
more than the 1,779,280 of the same seeds without them, 55.4% of the firmware slot. Of them 5,464 bytes are the tables of the fonts
and of the sine, 1,464 for `small`, 1,952 for `medium` and 2,048 for the sine, which stay
in the flash; the static memory is the same, 70,012 bytes, 21.4%. It was not flashed.

With the folders of the card, the window and the saved playlist of seed 41, `build` made
`odrig-firmware.bin` of 1,827,264 bytes on 2026-10-26, SHA-256
`5b487c68492a25e133f604a2cf666e4c866ed2b1fef33ed307317f0b67ecffd3`. It was not flashed.

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

Without `--image` the image is `build/firmware/out/odrig-firmware.bin`, and with
`--standalone` it is `odrig-standalone.bin`. The bootloader, the
partition table and storage are not written: WLED's settings and the installed show stay.
So `flash` leaves the name and the password of the board's network as storage has them;
for a board that never got them, `install-firmware` is the command.

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
On a board of the bigger layout, `--full` puts WLED's layout back, and a storage of WLED's
size has to come with it: the tool reads the board's storage, keeps it in
`build/firmware/storage/` and prints `kept: <path>`, makes a storage of 10,354,688 bytes
that holds the board's settings, every file outside `/odrig`, and no show, and writes it at
`0x610000` in the same esptool call. The show is not kept; it may not fit, and installing it
again is the owner's.

### big-storage

```
python3 firmware/fw.py big-storage
```

Moves a board of WLED's layout to the bigger one of
[The regions of the flash](#the-regions-of-the-flash), keeping the board's settings, and
prints the layout it found, `kept: <path>`, and the board's reply to `status`. The show is
not kept: the board starts with `/odrig` empty, and the show is installed again with
`install-show`.

1. It reads the partition table. On a board of the bigger layout it prints
   `nothing to do: the board has the bigger layout`, writes nothing and ends with 0. A
   table that is not WLED's own, entry for entry, is `layout-mismatch`.
2. It reads the board's storage as `install-show` does, keeps it in
   `build/firmware/storage/`, and prints its path.
3. It makes the new storage of 13,500,416 bytes: a file system of the disk version of the
   old one, made at 3,145,728 bytes, the room of WLED's second firmware slot, with the
   settings in it, and then grown to its whole size. All it holds lies in those first
   3 MB, and the tool checks that, the settings and that there is no `/odrig`.
4. It writes those first 3 MB at `0x310000`, as data, and has the chip compare them. The
   board still has WLED's layout whole: nothing of it lies there.
5. It erases the boot selection, writes the bigger layout's table at `0x8000`, has the
   chip compare it and restarts the board. Beyond its first 3 MB the new storage holds
   what was WLED's storage; the file system knows those blocks as free and erases a block
   before it writes one.
6. It waits 20 seconds, or as long as `--wait SECONDS` says, for the reply to `status`.

When step 4 fails, the board has its old layout and its old storage. Step 5 writes one
sector; when it fails, `restore-stock --full` brings the board back, and `set-wifi` and
`set-limit`, or the kept image, its settings.

### install-show

```
node converter/odrig.js pack --show shows/example/show.json --mapping mapping/legs-2.json \
    --sources animations --out build/example-show
python3 firmware/fw.py install-show build/example-show
```

Puts a show folder, the installed file set of [show.md](show.md), into the folder `/odrig`
of the board's storage, checks what was written, restarts the board, waits until the
board has read every installed animation to its end, and prints the board's reply to
`status` then and a line with the outcome:

- `outcome: healthy`: the show is valid and every animation can be played;
- `outcome: degraded: <n> unavailable`: the show is valid and plays, and `<n>` animations
  had a fault and are unavailable until the next start or an upload that replaces them;
  `list` names them with their reasons;
- `outcome: recovery: <reason>`: the show is invalid.

The status is 0 for healthy and degraded, as the board plays, and 1 for recovery.

The board plays right after its restart and reads the animations while it plays. A
firmware that reports its `readiness` is asked for its status every half second until the
readiness is no longer `checking`. One from before seed 33 answers `list` with `busy`
until it has read them all, and a fault it finds in one of them shows in `status` only
then: the tool waits for the first reply to `status`, asks for the list every half second
until it is no longer refused with `busy`, and then asks for the status it prints. All of that has 300 seconds, or as long as `--wait SECONDS` says:
the board reads a storage full of dense animations for some minutes while one of them
plays, and a small show within a few seconds; see
[Measurements on the board](#measurements-on-the-board). A board that is still reading
when the time is over ends the command with `check-not-done`: the show is installed, and
whether it is sound is not known yet.

1. The folder is checked before the board is touched: it must be a valid installed file
   set as the readers of the converter judge it, and hold no other file. The reason of a
   refusal is the converter's, for example `file-missing`. The check is a rebuild of the
   internal catalog of [catalog.md](catalog.md), on the computer: each animation is read
   once, in the show's order, for the mapping's canvas, and the catalog's marker and pages
   go into the board with the show, so that the board need not read the animations at its
   start. A catalog the folder holds, as `read-show` copies it, is made anew. The marker
   names the generation after the board's catalog, or 1, and is the board's own when the
   board's catalog has the same pages: the same folder installed again changes nothing.
   `--no-check` installs any flat folder of files, without a catalog, for trying what the
   board does with an invalid show.
2. The tool reads the partition table and takes the place and size of `spiffs` from it.
3. It gets the storage as it is now into `build/firmware/storage/`: it takes the newest
   image it kept there when esptool has the chip confirm that storage has that image's
   checksum, which takes 17 seconds, and reads the whole partition otherwise, which takes
   64 seconds.
4. It prints how the show changes: the number of files of `/odrig` it keeps, and each
   file it adds, replaces or removes with its bytes, as `show: kept 56 files`,
   `show: added new.odrg, 120000 bytes`, `show: replaced mapping.json, 184 bytes, was 16`,
   `show: removed bad.odrg, 65262 bytes`; for a folder that the board holds already,
   `show: kept 4 files; nothing added, replaced or removed`. The saved playlist order,
   `order.txt` of [show.md](show.md#the-saved-playlist-order), the saved playlist,
   `playlist.txt` of [core.md](core.md#the-saved-playlist), the saved repeats,
   `repeats.txt` of [show.md](show.md#the-saved-repeats), and the clocks' two settings,
   `clocks.txt` of `clocks on|off` and `clocks message on|off` in
   [commands.md](commands.md), may be files of the folder; a folder without them keeps the
   board's, as installing animations does not change the order, the playlist, the repeats
   or the clocks' settings the operator chose.
5. In that image it changes only what differs. A file of the folder that `/odrig` holds
   with the same bytes stays where it is, neither read nor written. A new file is written
   under its name, and a changed one under a spare name, `~0`, `~1` and so on, which then
   takes the place of the old file by a rename; the files the folder does not hold are
   removed last. So the bytes of the new files go into blocks that the file system before
   did not use. When there is no room for the new files beside the old ones, the files
   that go and the old files of the changed ones are removed first. The file system keeps
   the disk version it had. Files that do not fit even so are `no-space`, and nothing has
   been written to the board then. An image that already holds exactly these files is
   left as it is.
6. It checks the new image: `/odrig` holds exactly the files of the folder, byte for byte,
   every file outside `/odrig` is as it was, and every file outside `/odrig` and every file
   it kept lies in the blocks it lay in.
7. It writes the blocks that changed, neighbouring ones joined, in two esptool calls, and
   prints how many first: `storage: 33 blocks to write, 135168 bytes: 31 free first, then
   2 in use`. The first call writes the blocks the board's file system does not use; a
   failure of esptool there, or Ctrl-C, ends the command with the board's file system as
   it was, and the board is restarted. The second call writes the blocks the file system
   uses: the commit. Then the chip compares every written block with the new image. During
   the commit and the comparison Ctrl-C waits for their end. A failure there ends with
   `recovery-needed`, and the chip stays in its bootloader: WLED formats a file system it
   cannot read when it starts. No call of the write resets the chip, as esptool would
   after a failure too; once the comparison has passed, the board is restarted and the
   tool prints `storage: committed: 135168 bytes written and compared; the board
   restarts`. A folder that the board holds already writes and compares nothing:
   `storage: unchanged: nothing written; the board restarts`. esptool is told that these
   blocks are data: it would otherwise take a block that begins with the first byte of a
   program image for a program and refuse it. The rest of the partition is not compared:
   it is the image the chip confirmed, or that was read whole, in step 3.

Removing, adding or replacing one animation of a storage 80 % full changes the blocks of
the files written and two blocks of the file system's records, where the folder rebuilt
whole changed 8.4 MB of WLED's layout and 10.9 MB of the bigger one;
`tests/firmware/test_incremental.py` measures it at both layouts.

`--dry-run` does steps 1 to 6, prints the blocks it would write,
`storage: 33 blocks to write, 135168 bytes: 31 free first, then 2 in use`, and
`storage: dry run: nothing written; the board restarts`, writes nothing and restarts the
board. `--keep-copies DIR` copies every file the install removes or replaces, as the board
holds it, into `DIR`, a folder that is new or empty, before anything is written, and
prints `kept copies: 2 files in DIR`: a file kept for a look at why it failed.

From its first write to the comparison the change is named by the journal
`build/firmware/storage/change.json`: the storage region, the new image and the blocks of
each call, and the step reached. `set-wifi`, `set-limit` and `install-firmware` write their
change of storage in the same way.

A copy of storage from before the write and the new image stay in
`build/firmware/storage/`, named by time; the newest eight images are kept. The new image
is one of them only once the board holds it. Every file of
storage outside `/odrig`, WLED's settings among them, keeps its content.

Every show installed on the board while one 60-LED strip is fed from the board's 3.3 V pin
must have a brightness of 40 or less in its `show.json`. The tool does not check this; the
board tests do, for every show they install.

### set-wifi

```
python3 firmware/fw.py set-wifi
```

Puts the name and the password of the board's Wi-Fi network into the board's storage,
checks what was written, restarts the board, and prints three lines: `name: <name>`,
`password: set`, and the board's reply to `status`. [wifi.md](wifi.md) describes the
network.

The two values come from the settings file, `firmware/wifi.json`, a JSON object with
exactly the strings `name` and `password`, and from nowhere else: no option and no
variable carries either. `--settings FILE` reads another file of the same format. A name
has 1 to 32 characters and a password 8 to 63, all of them printable ASCII; a file that
is refused stops the command before the board is touched. The password is never printed:
not by this command, and not in the detail of a refusal.

The network is WLED's, and WLED keeps its name in `/cfg.json` and its password in
`/wsec.json`, two files in the top folder of storage. The command edits those two files
the way `install-show` writes a show:

1. It reads the partition table and gets storage as it is, as `install-show` does.
2. In `/cfg.json` it sets `ap.ssid` to the name and `ap.pskl` to the number of characters
   of the password, and removes `ap.psk` when it is there. In `/wsec.json` it sets
   `ap.psk` to the password. A file or an `ap` object that is missing is made. Every
   other member keeps its value and its place, and a file that needs no change keeps its
   bytes. A file that is not a JSON object is `wled-settings-malformed`, and nothing has
   been written to the board then.
3. It checks the new image: both files hold the settings, differ from the old ones in
   nothing else, and every other file is as it was.
4. It writes the blocks that changed, has the chip compare the whole partition with the
   new image, and restarts the board. On a board that holds the settings already nothing
   is written.

The command takes 36 seconds on the bench board. The tool waits 20 seconds for the reply
to `status`, or as long as `--wait SECONDS` says.
The reply shows that the firmware runs again; the command does not look into it, and its
status is 0 also when the reply reports an invalid show. On a board that answers no
`status`, stock WLED for one, the command ends with `no-reply` after the settings were
stored and checked.

`flash`, `restore-stock` and `install-show` leave the name and the password as storage
has them.

### set-limit

```
python3 firmware/fw.py set-limit
```

Puts the limit on LED current into the board's storage, checks what was written, restarts
the board, and prints two lines: `limit: <N> mA`, or `limit: off` for a limit of 0, and
the board's reply to `status`.

The limit comes from the limit file, `firmware/limit.json`, a JSON object with exactly
the whole number `milliamps`, from 0 to 65,535. It is the maximum for all LEDs together
that WLED's limiter works with, and 0 switches the limiter off; see
[The current limiter stays active](#what-the-firmware-does). `--settings FILE` reads
another limit file. A file that is refused stops the command before the board is touched.

WLED keeps the number as `hw.led.maxpwr` of `/cfg.json`. The command edits that file the
way `set-wifi` does: every other member keeps its value and its place, a `hw` or a
`hw.led` object that is missing is made, the new image is checked, the blocks that
changed are written, and the chip compares the whole partition. On a board that holds
the limit already nothing is written. The tool waits 20 seconds for the reply to
`status`, or as long as `--wait SECONDS` says.

### read-limit

```
python3 firmware/fw.py read-limit
```

Reads the board's storage, restarts the board, and prints the limit it holds in one line:
`limit: <N> mA`, `limit: off`, or `limit: not stored; WLED uses 850 mA` when `/cfg.json`
holds no `hw.led.maxpwr`. It writes nothing.

### install-firmware

```
python3 firmware/fw.py install-firmware
```

The command for a board from scratch: one that runs stock WLED or an earlier build, or
whose storage does not hold the network's name and password yet. It writes the built
firmware to the board as `flash` does, waits for the firmware's reply to `status`, and
then does what `set-wifi` and `set-limit` do, in one write: it puts the name and the
password of the settings file and the limit of the limit file into storage, restarts the
board again, waits as `install-show` does until the board has read its installed
animations, and prints `name: <name>`, `password: set`, the line of the limit and the
reply to `status`. A reason in that reply does not fail this command: a board from
scratch has no show yet.

The settings file and the limit file are read and checked first, and then the image
`build/firmware/out/odrig-firmware.bin` and the SHA-256 beside it. When one of them is
refused, the board has not been touched. `--settings FILE` reads another settings file,
`--limit FILE` another limit file,
and `--wait SECONDS` is the time the command waits after each of its two restarts, 300
seconds without it; it goes on as soon as the board has answered, and after the second
restart as soon as the board has read its animations. The command takes 50 seconds on
the bench board.

When the command fails after the firmware was written, the board runs the firmware with
the name and the password its storage had. Running the command again, or `set-wifi`,
finishes the work. `flash` and `restore-stock` do not apply the settings: they leave
storage as it is.

### read-show

```
python3 firmware/fw.py read-show build/show-from-board
```

Copies the files of `/odrig` on the board into a folder that is new or empty, among them
`order.txt`, `playlist.txt`, `repeats.txt` and `clocks.txt` when the board has them, prints each name with
its size, and restarts the board. The folder can then be compared with the one
the emulator ran:

```
diff -r build/example-show build/show-from-board
```

### recover-storage

```
python3 firmware/fw.py recover-storage
```

Finishes or gives up the change of the board's storage that the journal
`build/firmware/storage/change.json` names, after a command ended with `recovery-needed`.
Without a journal it prints `storage: nothing to recover: no change of the board's storage
is unfinished` and touches nothing.

- A change that was cut before its commit, as when the computer lost power while the free
  blocks were written, is given up: the board holds its storage from before. The journal
  and the new image are removed, the board is restarted, and the tool prints
  `storage: given up: ...` and the board's reply to `status`.
- Otherwise the chip first compares the board's storage outside the blocks of the change
  with the new image. When it is the same, the tool writes the change again, the free
  blocks and then the blocks in use, has the chip compare them, keeps the new image as the
  board's, removes the journal, restarts the board, and prints
  `storage: committed: the change was finished: ... bytes written and compared; the board
  restarts` and the reply to `status`. Ctrl-C waits for the end of the writing.
- When the storage outside the change differs, something else wrote it since, for
  example the board started on the half-written storage and formatted it. The command
  ends with `storage-changed`, writes nothing, and leaves the chip in its bootloader.
  `recover-storage --whole` writes the new image whole, every block of storage: the last
  resort, which brings back the settings and the show the new image holds and loses what
  the board wrote since.
- A recovery that is cut keeps the journal; the same command finishes it later.

`--wait SECONDS` is how long it waits for the board's reply after the restart (default:
20).

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
started. It also changes the installed show with the commands of
[commands.md](commands.md): it uploads animations and removes them again. It builds an
image the work folder does not hold: the firmware and the probe build are those of the
microSD card, `odrig-firmware.bin` and `odrig-probe.bin`. Its last step leaves the board
with the firmware and the example show at brightness 32, playing, with no file of a test in
`/odrig`. A run takes about 55 minutes. Without a board it stops with `no-board` and runs
nothing.

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
outputs as its LED settings. It uploads an animation over HTTP, plays it and removes it,
and it uploads a dense bench clip of ten seconds and writes the speed and the rates of
that upload to `build/firmware/out/upload-air.json`. For these it expects the example
show on the board, as `test-board` leaves it. Without a board, or when the address answers
no command, it stops with `no-board` and runs nothing.

## From nothing to a playing board

With the board on USB, from the repository root:

```
python3 firmware/fw.py build
python3 firmware/fw.py install-firmware
node converter/odrig.js pack --show shows/example/show.json --mapping mapping/legs-2.json \
    --sources animations --out build/example-show
python3 firmware/fw.py install-show build/example-show
python -m odrigctl --port /dev/cu.usbmodem101 status
```

The first command also sets up the tools and fetches WLED, which needs the network once.
`install-firmware` writes the firmware and gives the board's network the name and the
password of `firmware/wifi.json`; see [wifi.md](wifi.md).
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
`mapping.json`, `show.json` and the `.odrg` and `.odrgx` files, as `install-show` put them there. It
gives the core a file in the pieces the core asks for, of at most 512 bytes, and never
holds a whole file. The core's memory comes from the chip's internal memory, and from the
external memory only when the internal memory has none. The time the core is given is the
milliseconds since the chip started, from a 64-bit clock.

**Storage.** The usermod gives the core the seven storage functions of
[core.md](core.md), on WLED's file system. Every path is `/odrig/<name>`, and a name is
checked before it is used: 1 to 32 characters of `a`-`z`, `0`-`9`, `-`, `_` and `.`, and
not dots alone. The firmware writes, renames and deletes a file only there, and only
inside one of these functions: nothing of the firmware decides to write. What is written
is the core's matter: an uploaded animation, first as `upload.part`, the show file,
first as `show.part`, and `pending.txt`; see [show.md](show.md) and [core.md](core.md),
"The files the core writes".

| Function | On the board |
|---|---|
| `write_open` | A file that was being written is closed and removed. The named file is opened for writing, which empties one that has the name. One file is written at a time. |
| `write` | The bytes go to the open file in one write. |
| `write_close` | The file is closed, and it is whole when storage then holds as many bytes as were given. |
| `rename` | The file system's rename. A file that has the new name is replaced by it. |
| `remove` | The file is deleted; a name that has no file is told apart from a failure. |
| `space` | The total size, and the free bytes in whole blocks of 4,096. |
| `read_at` | A second file is read beside the one the player has open, and stays open from one call to the next while the calls go on where the last one ended. |

The free space is not asked from the file system at every command: the file system walks
its blocks for it, which takes 30 ms with a small show and 377 ms with 9 MB of files. The
usermod asks once, before the core starts, and keeps the number of used blocks up from
then on by the sizes of what it writes, replaces and removes: no block for a file of 512
bytes or less, and for a longer file the blocks the file system needs for it, the
pointers at the start of every block counted. `space` is answered from that number
without a call to the file system. The number is taken again at every start.

**Storage calls are paced.** A write to storage takes the file system up to a few hundred
milliseconds, and the player waits for the same lock. So after storage calls that took a
time d together, the board takes no command line for the longer of 20 ms and twice d,
counted from the end of the last call: the port leaves what arrives in its queue, and a
command over HTTP waits before it is handed to the core. Refreshes go on meanwhile. A
sender needs no pause of its own: it sends the next line when it has the reply to the
last one.

**An invalid show** is the core's matter, as in the emulator: the LEDs stay dark, `status`
reports the reason text of [reasons.md](reasons.md), "The core", and every command is still
answered.

**The port.** In the firmware the chip's own USB socket is this serial port for as long
as the board runs. In the USB stick's build, as the board starts, the socket stays this
serial port when a computer is plugged into it, and otherwise becomes the socket of a
[USB drive](#the-external-storage); its probe build keeps it a serial port always. Every byte the
board receives on its USB serial port goes to the core,
unchanged and in order, and every reply of the core is written back; the firmware writes
nothing else. The port's queue for what arrives has 4,096 bytes, so that a line of 2,048
characters written in one piece arrives whole, also while the pacing holds lines back.
Two such lines written together do not fit: a sender waits for the reply to a line before
it sends the next. So the command tool of [emulator.md](emulator.md) works on the board
as on the emulator:

```
python -m odrigctl --port /dev/cu.usbmodem101 status
{"ok":true,"on":true,"brightness":32,"playing":3,"animation":1,"fps":50,"error":null,"width":60,"height":6,"seed":null,"left":86400}
```

WLED's own serial handling is switched off: no Adalight, no TPM2, no Improv, no JSON over
serial, no answer to WLED's single-letter commands. The chip's own bootloader still prints
a few lines at a reset; the command tool skips every line that is not a reply.

**The two USB sockets.** The board has two. The chip's own USB unit is behind one; that is
the port above, which a Mac names by its place, `/dev/cu.usbmodem101`. The other socket,
marked COM, reaches the chip's UART, on its pins 43 and 44, through a bridge chip; a Mac
names it by the bridge's serial number, as `/dev/cu.usbmodem5C831043631`. The firmware
takes command lines on the UART as well, at 115,200 bits a second, and writes each reply
there, and between the replies the lines of [the log](#the-log). It keeps the line that is arriving there apart from the one of the other socket,
and hands it to the core as the web server hands a line, so a line on one way never
disturbs a line on another; of a line of more than 2,048 characters it keeps one more,
and the core refuses it as `line-too-long`. The command tool opens either socket at
115,200 bits a second. The chip's loader prints its start-up lines on the UART, which the
tool skips.

esptool reaches the chip through either socket; the tool tells it 921,600 bits a second,
which the bridge uses and the chip's own USB unit ignores. When the chip's own socket has
become a drive's, in the USB stick's build, it reaches the chip only in its loader's download mode, which the
button BOOT held while the board is plugged in brings up; the socket marked COM flashes
it as before. The suite of the board passes only with the board on the chip's own
socket: stock WLED, which the suite flashes and restores, and the probe build answer there
and not on the UART.

### The external storage

The firmware plays the animations of an external storage after the installed ones, as
[show.md](show.md#animations-from-a-usb-drive) describes for a drive. In the firmware that
`build` makes it is a microSD card in a reader on GPIO39 to GPIO42, and nothing of the USB
host is compiled: [microsd.md](microsd.md) says how a card is prepared, taken up and
dropped, and what WLED's information says of it. In the USB stick's build,
`build --stick`, it is a USB flash drive on the chip's own socket, as the rest of this
section says.

- **A computer or a drive.** As the board starts, the firmware looks at the chip's own
  socket for 5 seconds. A computer plugged into it sends a start-of-frame packet each
  millisecond to the board, and when one comes the socket stays a serial port, for
  commands and flashing, until the next start; WLED's information then says
  `odrig drive: computer`. When none comes, the socket becomes the drive's for as long
  as the board runs, and a drive may be plugged in and pulled out at any time. The LEDs
  do not wait for the choice: the show plays from the start. So, to use the socket for a
  computer, plug the computer in before the board gets power, or press its reset button
  afterwards; for a drive, start the board without a computer on that socket.
- **The wait** is 5 seconds, `COMPUTER_WAIT_MS` of `firmware/usermod/odrig_drive.cpp`,
  unless WLED's settings say otherwise: the page "Usermods" of WLED's settings shows it
  as `computer_wait_s` under `odrig`, from 0 to 60 seconds, kept in `/cfg.json` of the
  board's storage. A value outside that range leaves 5. A change takes effect at the next
  start, and 0 gives the socket to a drive at once.
- **The USB host** of ESP-IDF serves the socket, Espressif's driver of flash drives,
  `usb_host_msc` 1.1.1 in `firmware/usb_host_msc/`, reads the drive, and its file system
  is mounted at `/usb`. The drive is read and never written or formatted.

- **Preparing a drive.** FAT32 or FAT16, with a folder `odrig` at its top that holds the
  `.odrg` files, made for the board's canvas as the installed ones are. Names are kept
  to the letters `a`-`z` and `A`-`Z`, digits, `-`, `_` and `.`: the firmware's file
  system reads names in the code page 850, so Hebrew letters, for one, come out as `?`,
  and such a file cannot be opened by its name and is left out. Other files are passed
  over. Sub-folders of `odrig` are listed too, to three levels down, depth first: a
  folder's files in the order of their names, then each of its sub-folders in the order
  of their names; at most 256 files and 32 sub-folders are taken, the first in that
  order, and [microsd.md](microsd.md#preparing-a-card) has the rule in full.
- **The adapter and the sockets.** The chip's own socket gives a plugged device no power:
  plugged in directly, a drive is not seen. Between that socket and the drive goes a
  USB-C adapter or hub with a power input of its own, which is powered. The computer
  reaches the board on the socket marked COM, for commands and for flashing.
- **Plugging in and pulling out** work while the board runs. A drive is taken up when it
  comes: mounted, and read from its catalog when it has one; otherwise its folder is
  listed once, when the core asks, and its files are read and added to the playlist one
  by one while the show plays. When it goes, its animations leave the playlist.
- WLED's information has `odrig drive`: `looking for a computer` during the wait,
  `computer`, `none`, the number of animation files of the drive, `not readable` for a
  drive that did not mount, or `no USB host` when the host did not start.
- The list's names take 64 KB of the external memory, and the two files that are read
  4 KB each of the internal memory. The rate while a file of the drive is read has not
  been measured yet.

### The log

The firmware writes a log on the socket marked COM, between the replies to commands: a
line for every event of the card, or in the USB stick's build of the chip's own socket,
and every line the player logs. A line is
one line of printable ASCII: `#log`, the seconds since the start with three decimals, the
kind of the line, and its text.

```
#log 5.012 usb: no computer on the port within 5 s
#log 5.020 usb: host started
#log 31.407 usb: a device came: maker 0781, product 5581, a stick
#log 31.884 usb: stick mounted
#log 31.902 usb: stick opened: 12 animation files in odrig
#log 32.115 player: drive file clip.odrg left out: size-mismatch
#log 58.230 usb: a device went: maker 0781, product 5581, a stick
```

**The line kept across a reset.** The firmware keeps the latest line the player logged,
which names a reason (an invalid show, `file <name> unavailable: <reason>`,
`drive file <name> left out: <reason>`), in memory that a software or watchdog reset
leaves as it was and a power cut clears, with a CRC-32 of its length and its text, cut to
95 bytes. Nothing of it is written to flash or to the card. At its next start, before the
player starts, the firmware writes `#log <seconds> odrig: before this start: <text>` when
that memory holds a sound line, and clears it either way: a damaged record is passed over
and holds nothing up.

**The name in `status`.** The firmware gives the core a text that names it, which
`status` reports as `host`: WLED's release name, the date and the time of the build, its
storage, `internal+microsd` for the microSD build and `internal+usb` otherwise, and
`reset` with the reason of the chip's last reset as ESP-IDF tells it: `power-on`,
`software`, `panic`, `task-watchdog`, `interrupt-watchdog`, `brownout`, `deep-sleep` or
`other`.

The lines of the kind `usb`, which only the USB stick's build writes:

- After the look for a computer: `a computer is on the port, which stays a serial port`,
  or `no computer on the port within 5 s`, with the wait of the settings.
- The USB host: `host started`, or `host did not start: <error>`, with the error of
  ESP-IDF.
- A device: `a device came: maker <four hex digits>, product <four hex digits>, <kind>`,
  where the kind is that of its first interface, or of the device when it has none:
  `a hub` for the class 9, `a stick` for the class 8, `another device (class <n>)` for any
  other; `a device came that could not be opened (<error>)`; and
  `a device went: maker <four hex digits>, product <four hex digits>, <kind>`, which names
  the device as its line of coming did. The maker's and the product's numbers are those of
  the device's descriptor; they are only written, and the firmware treats no maker and no
  product apart. The log keeps up to eight devices at once, a hub and what is plugged into
  it among them, to say when each goes; a ninth has its line of coming only.
- A stick mounted: `stick mounted`, `the stick has no folder odrig`,
  `stick not opened: no file system it reads (<error>)`, or
  `stick not opened: a fault in reading (<error>)`. Its folder listed, when the core asks
  for a stick without a catalog: `stick opened: <n> animation files in odrig`, or
  `stick opened: <n> animation files in <m> folders of odrig` when sub-folders were
  taken, with `; <k> files and <f> folders passed over` at its end when something was
  left out; or `stick not opened: a fault in reading the folder odrig`.

The lines of the kind `sd` are those of the firmware, which reads the card and has no
line of the kind `usb`:

- A card mounted: `card mounted`, or `the card has no folder odrig`. Its folder listed,
  when the core asks for a card without a catalog: `card opened: <n> animation files in
  odrig`, or `card opened: <n> animation files in <m> folders of odrig`, with `; <k>
  files and <f> folders passed over` at its end when something was left out; or `card
  folder odrig could not be read`.
- No card: `card not mounted; no card or unreadable file system`, once for each spell
  without a card; and `card unavailable; files closed, waiting for a card` when a card
  went.
- The reader not started: `SPI did not start on the configured pins; reader disabled`,
  or `SD pins or SPI frequency not configured safely; reader disabled`.

The lines of the kind `player` are what the player logs: a file of a drive that is left
out, `drive file <name> left out: <reason>`, also for a file of the card, and the reason
the show became invalid, as WLED's information shows it.

- **Never in the way.** A line is added from any task without waiting, into a queue of 32
  lines of up to 160 bytes; a longer text is cut, and every byte outside printable ASCII
  is written as `?`. The UART's code writes a waiting line only when the UART's queue of
  2,048 bytes takes it whole at once, so the log holds back neither the LEDs nor the
  commands, and a line never breaks into a reply. When lines come faster than the socket
  takes them, the oldest give way, and the next line written says how many:
  `#log 40.100 log: 7 lines dropped`.
- **Reading it.** The command tool prints it, with
  `python -m odrigctl --port /dev/cu.usbmodem5C831043631 --log`, until it is stopped with
  Ctrl-C, as [emulator.md](emulator.md#the-command-tool) describes; so does any serial
  terminal on the socket marked COM at 115,200 bits a second, eight data bits, no parity,
  one stop bit. The tool's commands take only replies as replies and pass over the log's
  lines, so a command may be sent while the log is read, from another terminal.
- **Where it is not.** The log goes to the socket marked COM only: not to the chip's own
  socket, not over Wi-Fi, and not into the board's storage. It names nothing of the Wi-Fi
  settings. The probe builds, which start neither the card's reader nor the USB host,
  have the player's lines only.

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

Of a body longer than 4,096 bytes the first 4,096 are passed on, which the core answers
with `line-too-long`. The body and the reply of a request are kept in memory of the
request's own, which is given back with it, and not on the stack of the network task.
What follows a `?` is ignored. WLED adds `Access-Control-Allow-Origin: *` to every
response.

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
point are WLED's settings; `set-wifi` and `install-firmware` put them there from the
settings file, `firmware/wifi.json`, and [wifi.md](wifi.md) describes the network. The
usermod keeps WLED's captive portal answering, which WLED
itself does only outside its live mode. WLED's pages, its JSON interface and its updates
through its own interface keep working; while WLED writes a new firmware, the usermod reads
no file and sends nothing to the LEDs.

**WLED's information** (`/json/info`, and the Info page of its interface) reports the
access point as active in `wifi.ap`, the release name `odrig_ESP32-S3_16MB_opi`, and the
entries of the usermod:

| Entry | Value |
|---|---|
| `odrig show` | `ok`, or the reason the show is invalid, as `status` reports it. |
| `odrig outputs` | `<working>/<legs>`, and ` leg <n> pin <p>` for each output that does not work. |
| `odrig start` | The milliseconds the core took to start. |
| `odrig drive` | What there is of the external storage: of the microSD card, as [microsd.md](microsd.md#the-log-and-wleds-information) says, or in the USB stick's build of a USB drive, as [The external storage](#the-external-storage) says. |
| `odrig update` | `refused: no second slot` on a board of the bigger layout, where an update over Wi-Fi is refused; `WLED's` on WLED's layout, where WLED's own update works. |

**An update over Wi-Fi.** On a board of the bigger layout of
[The regions of the flash](#the-regions-of-the-flash) there is no second firmware slot, and
the firmware is updated over the USB cable only. An update sent to WLED's page, its own
form or `POST /update`, is answered with WLED's message page, status 501, `Update refused`
and *This board has no second firmware slot: that room holds animations. Its firmware is
updated over the USB cable with python3 firmware/fw.py flash.* Nothing is written, the
LEDs go on playing, and the upload is thrown away as it arrives. The layout itself keeps
any other update from writing: its one slot is a factory slot, for which the update
library finds no slot to write, so WLED's own update, and ArduinoOTA when it is on, fail
before they write. On WLED's layout the firmware registers nothing, and WLED's update works
as it does in stock WLED.

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

The maximum is the limit of `firmware/limit.json`, which `set-limit` and
`install-firmware` put into WLED's stored settings; `read-limit` prints what a board
holds. The firmware itself never sets it. A limit of 0 switches the limiter off: WLED
then estimates nothing and dims nothing.

| Limit | The bench: one strip fed from the board's 3.3 V pin | The installation: the LEDs fed from the supply |
|---|---|---|
| 850 mA, the tracked value | The limiter is what keeps a `brightness 255` on a white picture from asking the pin for more than it gives. | Every LED is held at its lowest level: 3,600 LEDs count as 3,600 mA at rest. Nothing can be shown. |
| What the supply gives | Not for the bench. | The limiter dims a picture that would ask the supply for more. |
| 0, the limiter off | Not for the bench: nothing protects the pin then. | Nothing is dimmed. No LED current passes through the board, so the board is not at risk; what the supply and the wiring bear is not the tool's to judge. |

The limit stays 850 for as long as a strip is fed from the board. Which value the
installation gets is the owner's to say: it is about power. The tool takes every whole
number from 0 to 65,535.

> With the twenty legs of the target, 3,600 LEDs, the estimate at rest alone is 3,600 mA.
> With WLED's maximum of 850 mA the limiter then holds every LED at its lowest level,
> whatever plays: as WLED's source has it, every channel of a colour that is lit is then
> sent as 1 of 255. The same holds for every mapping of 730 LEDs or more. Before twenty
> legs are lit, the limit must be raised to what the power supply gives, or switched off:
> edit `firmware/limit.json` and run `set-limit`. With two
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

No call of the core does unbounded work on a file: it settles a defect in slices of 32 KiB
and decodes at most 128 KiB of a body at a refresh, as [core.md](core.md#bounded-work)
says. On the board a call is to take 50 ms at most, so a command never waits longer, and a
read of the microSD card or of a USB drive 250 ms at most. ESP-IDF's task watchdog, whose
five seconds restarted the board in the investigation of 2026-10-24, stays on: the
firmware changes none of its settings, and no task feeds it while it waits for the lock,
so a call that held the lock for seconds would still restart the chip. WLED's own watchdog
of its loop is off (`WLED_WATCHDOG_TIMEOUT=0`), as it has been since seed 04. The board
session of seed 31 measures these budgets.

## What the firmware changes in WLED

| Changed | Left as it is |
|---|---|
| The LEDs show only the core's data. WLED's effects, presets, playlists, its boot preset and its nightlight do not run. | Wi-Fi, the access point and all network settings. |
| The outputs are the mapping's. WLED's LED output settings are replaced by them when WLED's LED settings are saved. | The web interface, the JSON interface and WebSocket. |
| WLED's switch, its brightness slider and its live override do not change the LEDs. | The current limiter and its maximum in WLED's LED settings. |
| The USB serial port speaks only [commands.md](commands.md): WLED's serial handling, Adalight, TPM2, Improv and JSON over serial, is switched off. | The file system and every file of WLED on it. |
| WLED's information shows the `odrig` entries and the release name `odrig_ESP32-S3_16MB_opi`. | Updates through WLED's own interface, on WLED's layout. |
| The audio usermod of the stock build is not included. | Buttons, relay and infrared settings. |
| The web server also answers `POST /odrig`, and on the bigger layout it answers `POST /update` with the refusal. | Every other page and address WLED serves. |

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

A second patch, `firmware/patches/020-newer-software.patch`, is for the firmware on
[the newer software](#the-newer-software). Every change in it is held by
`ESP_IDF_VERSION_MAJOR >= 5`, so on the software known good WLED compiles as before:

| File of WLED | Change |
|---|---|
| `wled00/src/dependencies/network/Network.h` | WLED's global `Network` takes the name `WLEDNetwork`: Arduino-ESP32 3 has a global `Network` of its own. |
| `wled00/bus_manager.cpp` | The PWM outputs use `ledcAttachChannel` and `ledcDetach`, which take the place of `ledcSetup`, `ledcAttachPin` and `ledcDetachPin`. |
| `wled00/util.cpp` | SHA-1 by the calls of the newer mbedTLS, which have no `_ret`; `esp_chip_info.h` and `esp_mac.h` included; the chip's revision as `revision`; the device's fingerprint without the legacy ADC driver's calibration, as ESP-IDF 5 stops a firmware at its start that holds the legacy ADC driver beside the new one Arduino-ESP32 3 uses. |
| `wled00/wled.cpp` | The static address is compared as a number: Arduino-ESP32 3 takes the literal `0U` for a null byte pointer and reads through it, which stopped the trial at its first connection. |
| `wled00/network.cpp` | lwIP's core is locked around the raw API that blocks the router advertisements of IPv6, which ESP-IDF 5 asserts at the first call. |
| `wled00/src/dependencies/e131/ESPAsyncE131.cpp` | lwIP's core is locked around `igmp_joingroup`, as above. |

## The probe build

The probe build exists so that a program can check what the LEDs are given without eyes on
them. It answers the line `#probe` on the port with one JSON line, shown here on several:

```json
{"probe":1,"start_ms":95,"heap":135736,"realtime":1,"loops":235,"sent":50,"gap_ms":20,
 "poll_us":578,"send_us":16525,"poll_total_us":28021,"send_total_us":816291,
 "overwritten":0,"limited":69,"limit_ma":730,"used_ma":3600,"wire_us":[5712,5713],
 "space_us":29110,
 "store":{"calls":0,"longest_us":0,"total_us":0,"check_steps":0,"check_longest_us":0,"check_total_us":0},
 "ap":1,"ap_name":"odrig","ap_auth":3,"error":null,
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
| `limited` | The sends since the last `#probe` in which WLED's current limiter dimmed the LEDs. With the limiter off it stays 0. |
| `limit_ma`, `used_ma` | The current the limiter allows the LEDs, WLED's maximum less 120 mA for the chip, and its estimate for the last send. Both are 0 while the limiter is off, which is a maximum of 0. |
| `wire_us` | The shortest and the longest time, since the last `#probe`, from the end of a send until the parallel driver had finished its transfer and could take data again, in microseconds; `null` when no output is on the parallel driver or none was sent. A timer looks at the driver every tenth of a millisecond. An output of 180 LEDs is 570 bytes on the wire with its reset, 5.7 ms. |
| `space_us` | The time the file system took to tell its size and its used bytes, when the usermod asked before the core started, in microseconds. |
| `store` | The storage calls since the last `#probe`, reads aside: their number in `calls`, the longest in `longest_us` and their sum in `total_us`, in microseconds. And the requests for a refresh in which the core read a second file, which is how it checks an uploaded file: their number in `check_steps`, the longest in `check_longest_us` and their sum in `check_total_us`. |
| `ap` | 1 while WLED's access point is up, else 0. |
| `ap_name` | The name in the configuration the radio holds for its access point: the first `ssid_len` bytes of `ssid`, or up to the first zero byte when `ssid_len` is 0. `null` while `ap` is 0. A byte outside printable ASCII, a quotation mark and a backslash are written as `\u00XX`. |
| `ap_auth` | The protection in that configuration, as the chip numbers it: 0 open, 3 WPA2 with a password. `null` while `ap` is 0. |
| `error` | The reason the show is invalid, as `status` reports it, or `null`. |
| `outputs` | For each of WLED's outputs: the leg, the pin, the number of LEDs, whether it works, its driver, `rmt`, `parallel` or `none`, and the two members below. |
| `crc` | Of an output: the CRC-32 of the colours it held when it was last read back after a send, as WLED gives them back: red, green and blue for each LED. With twenty outputs of 180 LEDs every output is read back once in twenty sends, 0.4 seconds; an output that was not read back yet is read for the report. |
| `pulses` | Of an output: the number of rising edges on its pin during one refresh, counted by the chip's pulse counter, or `null` before it was counted. A WS2812B bit is one pulse, so an output of 180 LEDs gives 4,320 whatever the colours. One output is counted at each send, each in its turn. The counter is put on the input of the pin's pad and leaves what the pin puts out alone. It counts to 32,767: 1,365 LEDs. |

A `#probe` that arrives between the copy of a refresh into the outputs and its show is
answered right after the show, so that a report never describes colours that were not
sent. The report of twenty outputs is a line of 2,400 characters; the port writes it in the
pieces it takes without waiting and reads no command until it is written.

While the limiter does not dim, an output gives back exactly the bytes it was sent. When it
dims, the output gives back the dimmed colours as WLED restores them, which at the
limiter's lowest level is 128 for a channel that stayed lit and 0 for one that did not.

The probe build has a second line, `#store <bytes>`, the store trial: it tries the
storage functions as the core would use them, without the core. It writes a small file
`probe.odrg` into `/odrig`, writes `<bytes>` bytes into `probe.part` in pieces of 1,500,
renames that onto `probe.odrg`, reads the file back through `read_at` in pieces of 512,
and removes it; a step in each pass of the loop that the pacing allows, with the lock
held. Then it answers with one line:

```json
{"store":1,"bytes":1000000,"ok":true,"failed":null,"written":1000000,"read":1000000,
 "writes":667,"write_us":[131,31421,151866],"write_ms":71502,"bytes_per_second":13985,
 "seed_us":109863,"open_us":13945,"close_us":13914,"rename_us":43065,
 "reads":1955,"read_us":[10,226,13126],"remove_us":37723}
```

`ok` is true when every step succeeded and the bytes read back are the bytes written, so
when the rename replaced the small file. `failed` names the step that did not: `seed`,
`open`, `write`, `close`, `rename`, `read`, `read-back` or `delete`. `write_us` and
`read_us` are the shortest, the mean and the longest time of one call, `write_ms` the
time from the first write to the last with the pacing's waits in it, and
`bytes_per_second` the bytes written over that time. The show plays on during the trial.

The port holds bytes at the start of a line back for as long as they are a beginning of
`#probe` and a newline, or of `#store`, a number and a newline. The complete line is
answered by the usermod and does not reach the core; every other byte is passed on to the
core, unchanged and in order.

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
| Example show, two legs, 360 LEDs | 2 of 2 | 3,096 bytes | 37 s | 216 ms | 1,989 to 2,052 | 50 | 50 | 44 ms | 1.12 ms | 24.5 ms | 1.03 ms | 1.24 ms | 150,940 bytes |
| Demo show, the target file, 3,600 LEDs | 20 of 20 | 3,913 bytes | 37 s | 217 ms | 319 to 363 | 50 | 50 | 43 ms | 1.91 ms | 24.4 ms | 15.6 ms | 16.0 ms | 64,956 bytes |
| Dense 60 x 60 clip of 10 s, compressed, the target file | 20 of 20 | 1,385,398 bytes | 58 s | 6,109 ms | 580 to 928 | 24 to 33 | 32 | 52 ms | 30.4 ms | 48.4 ms | 20.0 ms | 31.9 ms | 64,940 bytes |
| The same clip, uncompressed | 20 of 20 | 1,463,868 bytes | 58 s | 4,279 ms | 134 to 154 | 44 or 45 | 44 | 36 ms | 13.1 ms | 34.0 ms | 19.8 ms | 33.2 ms | 64,952 bytes |
| 9 MB of dense 60 x 60 clips: six of 10 s and one of 5 s, compressed | 20 of 20 | 9,009,652 bytes | 176 s | 39,173 ms | 656 to 924 | 24 to 32 | 27 | 61 ms | 31.3 ms | 70.2 ms | 20.0 ms | 32.9 ms | 64,940 bytes |

The files of a row are the whole show folder. The mean request is the time the core worked
in a second over the refreshes sent in it; at a rate below 50 one request decodes every
frame since the one before, so it is more than the work for one frame.

What the figures say:

- **The firmware drives twenty outputs.** With the target file all twenty work, on pins 1
  to 18, 21 and 47.
- **Every rate is inside the 20 to 50 a second the owner accepts.** A show that is not
  dense plays at 50 on twenty legs as on two. The dense clip, in which every LED changes
  at every frame, plays at 44 or 45 uncompressed and at 24 to 33 compressed in the probe
  build; the firmware itself reports 45 to 47 and 36 to 42, see
  [Verified on the board](#verified-on-the-board). A dense file plays faster uncompressed.
- **A send to twenty outputs** takes 15.6 ms with the limiter's dimming of every LED in
  it, and 20 ms while the core decodes a dense clip on the chip's other processor core.
  The LEDs need 5.7 ms on the wire after that.
- **The long requests** are those in which the core opens a file, at the start of every
  loop of an animation and at every turn of the playlist or of a cycle: 24 ms for a small
  file, and up to 70 ms with dense clips, when the frames that came due meanwhile are decoded in the same
  request.
- **The show plays at once after a restart.** The core reads the first 16 bytes of every
  file at its start, and the rest while the show plays. Measured through the socket
  marked COM: `status` answered 0.48 s after a restart with the demo show, 0.72 s with
  two dense 60 x 60 clips, and 1.31 s with 9 MB of dense clips behind a small animation,
  each time with the playlist playing; before, the board was dark and silent for 39 s
  with 9 MB.
- **Reading the files after the start** took 1.9 s for the demo show, at 47 or 48
  refreshes a second. For the 9 MB behind a small animation it took 491 s: while the
  small animation played its turn the rate was 36 to 48, and while a dense clip played
  it was 20 to 33, 30.5 on average, because the check then gives way and reads one frame
  record in ten refreshes. Until it has read everything, `list`, `remove` and
  `upload begin` answer `busy`; `install-show` and `install-firmware` wait for it.
- **`install-show`** takes 37 seconds for a small show: twice 17 seconds for the chip to
  work out the checksum of storage, before and after, and the write between. One dense
  clip takes a minute and 9 MB take three.
- **Memory.** 65,000 bytes of the chip's internal memory are free with twenty outputs of
  180 LEDs and the core, 151,000 with two. Before the content commands these were 126,000
  and 203,000: the core now takes at its start what the check of an uploaded file needs,
  a second window of 32,768 bytes and a second picture of the canvas, and tables with
  room for 128 items. It takes them from the internal memory first and from the external
  memory only when the internal memory has none. WLED's pages and its interface over
  Wi-Fi have not been tried with the memory that is left.

**An upload over USB.** Taken by `tests/board/test_upload.py` on 2026-10-12 with the probe
build, with the example show at brightness 32 playing on the bench file; the test writes
the figures to `build/firmware/out/upload.json`. The file was the dense bench clip of 60
seconds: 60 x 6, 3,000 frames, 868,712 bytes. The command tool's upload sent it through
the port and asked for `status` once a second through the same session.

- **The speed** was 12,674 bytes a second: 69 seconds for the file. It is the speed of
  storage with its pacing, not of the port.
- **While the data arrived** `status` reported 36 to 44 refreshes a second.
- **The check** took 60.2 seconds: one frame of the file for each refresh, so as long as
  the animation lasts. `status` reported 47 to 50 meanwhile. The core read the file back
  in 1,698 of its requests for a refresh, and the longest of those requests took 27 ms.
- **After `upload end`** `status` reported 50 in each of the ten seconds but the first,
  which had 41: it is the second in which the file is put in place, with its storage
  calls in a row. The longest time between two sends was 216 ms, there.
- **The storage calls** of the whole upload were 591, 18.4 seconds together, and the
  longest took 156 ms.
- **The space.** `space` reported 872,448 bytes fewer free with the file in place, 213
  blocks for 868,712 bytes, and the 10,211,328 of before once the item was removed.
- **A small file**, Hello world for the bench file, 1,138 bytes and 255 frames, was
  uploaded, checked and in place 6.1 seconds after the tool was started, with the
  firmware; 5.1 of them are the check.
- **While a dense clip plays** an upload costs more. Tried once, outside the suite, with
  the firmware and the dense 60 x 60 clip playing compressed on the target file, at 40 to
  42 refreshes a second before the upload: a file of 285,360 bytes arrived at 4,714 bytes
  a second, and `status` reported 16 to 27 meanwhile, below 20 in 13 of the 60
  seconds. Its check of 100 frames took 17 seconds, at 25 to 29 refreshes a second: a
  step of the check follows only a refresh that came in step, about six a second there.
  In the second in which a file was put in place, `status` reported 6 or 7. Hello world
  for that canvas, 1,210 bytes, took 11 seconds in all. Every upload succeeded.

Not measured, because the hardware is not wired: light on any leg but the one strip on
pin 1, and the current the LEDs really draw. Not measured either: an upload over Wi-Fi,
which needs a person to join the board's network; see step 7 of [The owner's
checks](#the-owners-checks).

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

## Changing what the board holds

Five kinds of work change or judge what the board holds, and each does its own part only.

| Work | Tool | What it writes | When it is the one |
|---|---|---|---|
| Flashing | `flash`, `install-firmware` | The program in the first firmware slot; `install-firmware` also the network's name and password and the limit on LED current into storage. | A new firmware. It never removes, adds or repairs an animation: storage keeps what it had. |
| A change by command | `odrigctl upload`, `remove`, `remove many`, `ignore`, `order move`; the operators' app | One animation file and the show file, or the saved order, through the core's own file system calls. | Adding, replacing, removing, leaving out or moving one animation, also while others are unavailable. The first choice. |
| A change by image | `install-show` | The blocks of storage in which the board's file system changes. | A whole show at once, or when the board does not answer commands. |
| Quarantine | the core, at every start | Nothing. | A file that cannot be played is unavailable for the boot and listed with its reason; it is repaired by a change by command. |
| The board's check | the core, after every start | Nothing. | Every installed animation is read to its end while the show plays; `list` gives its size once it is read. |
| The recovery of storage | `recover-storage` | The blocks of a change by image that was cut. | Only after a change by image that ended with `recovery-needed`. |

**A change by command.** The core writes the new file as `upload.part`, checks it and
renames it onto its name; for a new name or a removal it also writes the show file as
`show.part` and renames it onto `show.json`, with the names concerned in `pending.txt`
until the old file is gone; [core.md](core.md), "The files the core writes", has every
step. A power cut at any step leaves the old show or the new one, whole; the change is
committed by one rename. Moving an animation in the saved order writes `order.part` and
renames it onto `order.txt` the same way, saving or restoring a repeat writes
`repeats.part` and renames it onto `repeats.txt`, switching the clocks or their message on
or off writes `clocks.part` and renames it onto `clocks.txt`, and the choice of a playlist
writes `playlist.part` and renames it onto `playlist.txt`. What one change writes:

| Change | What is written | Bytes |
|---|---|---|
| Removing one animation | `pending.txt` and the show file | the file's name and a line feed, and the show file |
| Adding one animation | the file, `pending.txt` and the show file | the file, its name and a line feed, and the show file |
| Replacing one under its name | the file | the file |
| The same file again (`odrigctl upload`) | nothing | 0 |

`odrigctl upload` sends the CRC-32 of the file with `upload begin`, and a target whose last
upload installed that file answers `unchanged`: nothing is sent or written. So an upload
whose last reply did not arrive is run again safely. A cleanup that a change could not finish is finished by the next change, or by
the next start.

**A change by image.** `install-show` changes only the files that differ, writes the
blocks of the change in two parts and compares what it wrote:

1. The blocks the board's file system does not use: the bytes of the new and changed
   files. A cut here, by a failure of esptool, a cable pulled or Ctrl-C, leaves the board's
   file system as it was before; the tool says `the change was not made` and restarts the
   board.
2. The blocks the board's file system uses: its records, one to four blocks for the
   change of one file. This is the commit. Ctrl-C waits for its end. A cut here, or a
   comparison that fails, ends with `recovery-needed`: the board stays in its bootloader,
   because WLED formats a file system it cannot read when it starts, and
   `recover-storage` finishes the change.
3. The chip compares every written block with the new image, and the board restarts.

Measured on a storage 80 % full of animations of 50 to 250 KB (the tests of
`tests/firmware/test_incremental.py`):

| Change of one animation | WLED's layout, 57 files | The bigger layout, 75 files |
|---|---|---|
| Removal | 3 blocks, 12,288 bytes, 2 in use | 3 blocks, 12,288 bytes, 2 in use |
| Addition of 120,000 bytes | 33 blocks, 135,168 bytes, 2 in use | 33 blocks, 135,168 bytes, 2 in use |
| Replacement by 140,000 bytes | 37 blocks, 151,552 bytes, 2 in use | 37 blocks, 151,552 bytes, 2 in use |
| The same folder again | nothing | nothing |
| A removal as `/odrig` was rebuilt before | 2,046 blocks, 8,380,416 bytes | 2,653 blocks, 10,866,688 bytes |

**What the kept images bring back.** `build/firmware/storage/` keeps the newest eight
images of the board's storage: the one before each change by image and the one after.
`recover-storage` uses the new image of a change that was cut. The others are a record:
no command writes one back, and none holds what the board changed itself since, by
command or by WLED's settings. A file the change removes or replaces is copied before the
write when `install-show --keep-copies DIR` asks for it; `read-show` copies every file of
`/odrig`. The last resort for the whole flash stays the factory backup, written by hand.

**What cannot be cancelled.** A change by command is committed by one rename on the
board; `upload cancel` and an upload left for 60 seconds leave the show as it was. A
change by image can be cancelled until its commit; from then on it is finished, by the
same command or by `recover-storage`. Neither `install-show` nor `recover-storage`
promises to go back to the storage from before: the kept image from before is a record,
and `recover-storage --whole` writes the new image, not the old one.

`tests/core/test_incremental.py` and `tests/core/test_powercut.py` cut the power at every
storage call of the changes by command; `tests/firmware/test_recovery.py` cuts a change by
image at each of its steps, at both layouts.

## The regions of the flash

The board has WLED's 16 MB layout. The tool reads the partition table before it writes and
touches these regions only:

| Region | Address | Size | Written by |
|---|---|---|---|
| Bootloader | `0x0` | up to `0x8000` | `restore-stock --full` only |
| Partition table | `0x8000` | `0x1000` | `restore-stock --full` and `big-storage` only |
| Boot selection (`otadata`) | `0xE000` | `0x2000` | erased by `flash`, `install-firmware` and `restore-stock` |
| First application (`app0`) | `0x10000` | `0x300000` | `flash`, `install-firmware`, `restore-stock` |
| Storage (`spiffs`) | `0x610000` | `0x9E0000` | `install-show`, `set-wifi`, `set-limit` and `install-firmware`, changed blocks only |

`nvs` at `0x9000`, the second application partition at `0x310000` and the core-dump
partition at `0xFF0000` are never written. The whole flash is never erased, and no tool
writes a fuse of the chip or starts a program that can. esptool is given an address only
after the tool has checked it against this table.

The tool knows a second layout, the bigger one, which gives the room of the second firmware
slot to the storage. Its one firmware slot is a factory slot, for which an update over
Wi-Fi finds no slot to write; the tool names a table by its firmware slots: with a second
one it is WLED's layout, with one alone the bigger one.

| Partition | Address | Size |
|---|---|---|
| `nvs`, `otadata` | `0x9000`, `0xE000` | `0x5000`, `0x2000`, as in WLED's |
| `app0`, a factory slot | `0x10000` | `0x300000` |
| `spiffs` | `0x310000` | `0xCE0000`, 13,500,416 bytes; its first 3 MB written by `big-storage`, and changed blocks by the commands that write storage |
| `coredump` | `0xFF0000` | `0x10000` |

On a board of WLED's layout `restore-stock --full` writes no storage. On one of the bigger
layout it writes WLED's storage whole, holding the board's settings, as it puts WLED's
layout back.

**Why the bigger layout.** On 2026-10-15 the owner's show of 113 animations for the 60 x 60
canvas, 10.1 MB of files, did not fit WLED's storage: the file system keeps every file in
blocks of 4,096 bytes with records of its own, and was short by about 0.2 MB, so six of the
smallest animations were left out. The firmware is updated over the USB cable with this tool
only, and the second firmware slot is needed only by an update over Wi-Fi; the owner gave
those up, and the bigger layout gives the slot's 3,145,728 bytes to the storage. What is
given up: an update over Wi-Fi, which the firmware refuses with its reason, as "An update
over Wi-Fi" under [What the firmware does](#what-the-firmware-does) says. A board is moved
with `big-storage` and back with `restore-stock --full`; after either, the show is
installed again.

## Rolling back

`python3 firmware/fw.py restore-stock` brings back stock WLED 16.0.1, with its settings and
its show as they were. `--full` also brings back the stock bootloader and partition table,
for a board whose first 64 KB were changed by something else, and WLED's layout for a board
of the bigger one, with its settings and without its show; `big-storage` moves it again.

The last resort is the factory backup of the board: one image of the whole 16 MB flash with
its own checksum file, kept beside this repository. No tool reads or writes it. It is
written back by hand with esptool, at address `0x0`, after its checksum has been compared.

## Capturing evidence

When the board refuses an animation, restarts, or does something nobody can explain, the
evidence is gathered before anything is changed, so that the cause can be told apart from
what was done afterwards.

1. **Say what is there.** Write down the app's version, the show (`list`, every page of it)
   and which medium is in: `space` says whether a card or a stick is present.
2. **Read without restarting.** Ask `status` and `fault` with `odrigctl` over the serial
   port or HTTP, and read the log with `python -m odrigctl --port <port> --log`: a restart
   would clear what the core keeps, and the kept line of a reset is written once. `status`
   says `host`, which names the build and the reason of the last reset.
3. **Keep the bytes.** Copy the animation that is unavailable, as it is on the card or as
   `read-show` gets it from the board's storage, before anything removes or replaces it.
   Its reason names what the decoder found in the bytes it was given; whether the storage
   is damaged or a read went wrong on the way is found by reading the copy again
   (`node converter/odrig.js check`).
4. **Change one thing at a time,** and write down what each trial was meant to show and
   what it showed. Do not alternate broad writes, removals and reinstalls without a
   question each of them answers.

## The owner's checks

What a program on this Mac cannot establish: what the LEDs show, and what a device joined to
the board's Wi-Fi network, `odrig`, gets. Its password is in `firmware/wifi.json`, and
[wifi.md](wifi.md) has the check of the network itself. Each step says what to do and what
must be seen. The number
in brackets is the criterion the step covers: in steps 1 to 4 a criterion of Requirement 16
of `docs/specs/04-p1-firmware-build-with-the-player/requirements.md`, in steps 5 and 6,
marked `seed 05`, criterion 3 of Requirement 18 of
`docs/specs/05-p0-canvas-60-by-60/requirements.md`, and in step 7, marked `seed 07`,
criterion 5 of Requirement 21 of `docs/specs/07-p1-content-commands/requirements.md`.

Seed 04 is completed when steps 1 to 4 are done, and seed 07 when step 7 is done. Steps 5
and 6 stay listed as open and do not hold seed 05 open; criterion 4 of that Requirement 18
says so. Nothing a
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
   After half a minute a square of four LEDs takes their place and runs along the diagonal,
   from the top-left corner to the bottom-right one and back, over every one of the twenty
   legs, for 42 seconds. The two go on taking turns so: the show has no cycle, and this is
   its playlist.
   `python -m odrigctl --port /dev/cu.usbmodem101 status` reports `"playing":"all"` and
   `"error":null`, and WLED's Info page shows `odrig outputs` with `20/20`. The `fps` of
   that reply is worth writing down: the rate of the demo show on the board has not been
   measured.
7. **An animation uploaded over the board's network (seed 07, 21.5).** With the example
   show installed as in step 1 and playing, make Hello world for the bench file under a
   name no item of the show has, join the board's network with a computer, and send it:

   ```
   node converter/odrig.js encode animations/hello.json build/hello-bench.odrg
   python -m odrigctl --http 4.3.2.1 upload 9 build/hello-bench.odrg
   python -m odrigctl --http 4.3.2.1 list
   python -m odrigctl --http 4.3.2.1 play 9
   python -m odrigctl --http 4.3.2.1 remove 9
   python -m odrigctl --http 4.3.2.1 play 3
   ```

   *Seen:* `upload` writes a line with the percentage and the speed, then
   `upload: checking`, and after about five seconds `{"ok":true}`, while the show plays
   on; `list` shows `{"id":9,"file":"hello-bench.odrg","bytes":1138}` as the last item;
   after `play 9` the words HELLO WORLD begin again and stay for half a minute, which is
   the turn of the new item in the playlist; `remove 9`, sent within that half minute,
   answers `{"ok":true}` and the playlist goes on with its first animation, the same
   words; `play 3` brings the cycle back, in which the words and the bouncing square take
   turns every 15 seconds. The speed is worth writing down: no program has measured an
   upload over Wi-Fi. With this Mac joined and the board on USB,
   `python3 firmware/fw.py test-air --http 4.3.2.1` of step 3 runs the same session by
   itself and writes the speed to `build/firmware/out/upload-air.json`.

Before twenty legs are lit, raise WLED's maximum current as [What the firmware
does](#what-the-firmware-does) says.

What a program established without the owner, over USB: the board plays the installed show
from its start with no command sent, as `status` reports `playing` 3 after every restart,
and `"all"` for a show that names no start;
the outputs hold the bytes the emulator records for the same show; `status` reports 49 or
more with the example show, with one strip wired; WLED reports its access point as up; and
the tests of `test-air` that send commands pass against the emulator. For steps 5 and 6:
with twenty legs in the mapping the firmware makes twenty working outputs, each of the
twenty pins carries 24 pulses for every LED of a refresh, and the parallel driver is busy
after a send for the time its LEDs take on the wire. That the pulses have the right widths,
and that an LED on a lane of the parallel driver lights, no program can see. For step 7:
over USB the command tool uploads Hello world to the board, `list` shows it, `play` plays
it, it is there after a restart, and `remove` removes it, with the replies the emulator
gives; and the session of `test-air` passes with the emulator in the place of the board's
network. The seven steps above have not been done.

## Verified on the board

What the design assumed and an early task then tried, on this Mac and on the board. The
letters are those of the design's table "Assumed, to be verified by an early task".

The first part, down to "Twenty outputs", is the record of seed 04. It was tried with the
firmware of that seed, before the target became twenty upright legs: on the bench file,
and on mappings of ten row legs on pins 1 to 10, with a dense 60 x 30 clip. From "Twenty
outputs" on, the page has what seed 05 found for the target: twenty legs, 60 x 60. The
part "Files written while the show plays" is what seed 07 tried for the commands that
change the content. "The network's name and password" is what seed 08 tried, "The limit
on LED current" what seed 15 tried, and the last part, "A program without WLED", what
seed 12 tried first.

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

**Files written while the show plays.** What the design of the content commands assumed,
tried on 2026-10-12 with the probe build by `tests/board/test_upload.py`, with the store
trial of [The probe build](#the-probe-build). The show was the dim example show on the
bench file, two outputs of 180 LEDs. The letters are those of that design's table
"Assumed, to be verified on the board". The test writes the trial's figures to
`build/firmware/out/store.json`.

| # | Assumption | What was found |
|---|---|---|
| B1 | A rename onto a name that has a file replaces it, when neither file is open. | It does: after the rename of a file of a megabyte onto a file of 16 bytes, the name gave the megabyte back, byte for byte. The rename took 43 ms. |
| B2 | A file can be written, renamed and read with a second handle while the player has another file open and reads it. | It can. The show played through the whole trial, `overwritten` stayed 0, and `read-show` afterwards gave the installed files back unchanged. A read of 512 bytes through the second handle took 0.23 ms in the mean and 13 ms at the longest. |
| B3 | A write of 1,500 bytes takes a few milliseconds, and one in three some tens. With the pacing, `status` reports 25 or more with the bench show playing. | The writes are slower than assumed: 0.13 ms at the shortest, 31 ms in the mean and 152 ms at the longest; about one in three takes 87 ms, when the file system erases a block. With the pacing the board sent 34 to 46 refreshes in every second of the megabyte's 72 seconds, and 50 in each of the ten seconds after it; the longest time between two sends in a second was 90 to 161 ms. With the pacing taken out, the same trial ran at 44,148 bytes a second and the board sent 10 or 11 refreshes a second. The owner accepts 20 to 50, so the pacing stays as designed, and the writes need no task of their own. |
| B4 | A line of 2,048 characters written to the port in one piece arrives whole with a queue of 4,096 bytes. | It does, twenty times out of twenty, and a line of 2,049 characters was answered with `line-too-long` twenty times. Two lines of 2,048 characters in one write, 4,098 bytes, do not fit the queue: the end of the second is lost. The command tool sends a line after the reply to the one before, so it never does that. |
| B5 | `usedBytes` takes under 100 ms with storage nearly full. | It does not: 30 ms with the example show, 79 ms with one dense clip of 1.4 MB, and 377 ms with 9 MB of clips. So the usermod asks once, before the core starts, and keeps the number up itself, as [What the firmware does](#what-the-firmware-does) describes under "Storage"; `space` then makes no call to the file system. After a megabyte was written, renamed and removed, the number kept and the number the file system told after a restart were within 16,384 bytes of each other, which is what the test allows. |
| B6 | An upload over USB carries 10,000 bytes a second or more. | It does: the command tool's upload of a file of 868,712 bytes ran at 12,674 bytes a second, see [Measurements on the board](#measurements-on-the-board). The storage side alone carries 13,985 bytes a second with the pacing: a megabyte in 72 seconds. |

The other calls of the trial: opening a file for writing 14 ms, closing it 14 ms, removing
the megabyte 38 ms, and writing the small file of 16 bytes, its open and its close with
it, 36 ms in one run and 110 ms in another. With the example show 10,211,328 of the
10,354,688 bytes of storage are free.

A storage call stops the player for as long as it takes, because both wait for the same
lock, and the player then decodes every frame that came due meanwhile in one request.
With the example show nothing of that is seen. With a dense 60 x 60 clip playing it is:
[Measurements on the board](#measurements-on-the-board) has what an upload does to the
rate there. While `space` still asked the file system at every call, one call of 376 ms
with the 9 MB show made `fps` in `status` fall to 3 for that second.

**The network's name and password.** What the design of seed 08 assumed, in its table
"Assumed, to be verified by an early task", and what was found with the probe build on
the board. The letters are those of that table.

| # | Assumption | What was found |
|---|---|---|
| A1 | `esp_wifi_get_config(WIFI_IF_AP, ...)` compiles in the usermod with `wled.h` alone, can be called from the loop task, and gives the name and the protection of the access point WLED opened. Before any setting is applied it gives `WLED-AP` and 3. | It does. The probe build was built with no other header, and the call is made from the loop task for every report. After a restart the reports had `ap` 0 with `ap_name` and `ap_auth` `null`, and from the first report with `ap` 1 on, `ap_name` `WLED-AP` and `ap_auth` 3. The firmware is not changed by the two members: built before and after in the same work folder, its image has the same SHA-256. |
| A2 | WLED on the board reads the `/cfg.json` to which the tool added `ap` and the `/wsec.json` the tool created, opens the access point under that name with that password, and is otherwise as before. | It does. After `set-wifi` with settings made for the test the probe build reported `ap` 1, `ap_name` the test's name and `ap_auth` 3, and after `set-wifi` with the settings file `ap_name` `odrig` and `ap_auth` 3. `status` reported the same show playing as before, with no error. That the password is the one of the file is established from storage, read back; that a device joins with it is the owner's check. |
| A3 | WLED does not write its settings files at a start because of the edit: storage read back after the restart is the image the tool wrote. | It does not. After the restart, with the access point up, the chip confirmed the checksum of the image the tool kept, and the image read back was that image, byte for byte. |
| A4 | A file littlefs-python wrote into the top folder of the file system is read by WLED, a new `/wsec.json` among them. | It is: the access point is protected with the password that only `/wsec.json` holds, by A2 and by how WLED reads its settings. |

`set-wifi` took 36.5 seconds, the wait for the board's reply in it. Between storage
before the first run and after the second, every file other than `/cfg.json` and
`/wsec.json` kept its bytes, and `/cfg.json` differed in `ap` only.

`install-firmware`, on a board whose storage held another name and password, took 50.2
seconds. Afterwards the firmware answered `status` with the show playing, and storage
read back held the name and the password of the settings file and the same show.

**The limit on LED current.** What the design of seed 15 assumed and the probe build then
showed on the board, with Hello world for the target file at brightness 40.

| Assumption | What was found |
|---|---|
| WLED takes `hw.led.maxpwr` of the `/cfg.json` the tool edited at its start. | It does. After `set-limit` with a limit of 850 the report had `limit_ma` 730 and `used_ma` 3,600, and after `set-limit` with 0 both were 0. |
| With a limit of 0 nothing is dimmed. | Nothing was: over five seconds every report had `limited` 0, and 50 sends in the second. With 850 every send was dimmed: `limited` 49 to 51 from one report to the next, a second apart. |
| The probe build's count is right with the limiter off. | It was not: it counted every send as dimmed, 49 to 67 in a report, because it compared an estimate of 0 with a limit of 0. It now counts only while WLED's maximum is above 0. The firmware has none of that code: built before and after, its image has the same SHA-256. |

`set-limit` took 36 seconds. Storage read back held 0 and then 850, and between the two
only `hw.led.maxpwr` of `/cfg.json` differed. `read-limit` printed `limit: off` and then
`limit: 850 mA`.

**A program without WLED.** What the design of the standalone firmware assumed, in its
table "Assumed, to be verified by task 1", and what a trial program found on the board.
The trial is `firmware/standalone/src/main.cpp` as that task left it: it mounts the
storage, makes twenty outputs of 180 LEDs on the pins of the target file, sends a dim
point of light along each 50 times a second, counts the pulses on one pin at each send,
and answers `#probe`. The letters are those of that table.

| # | Assumption | What was found |
|---|---|---|
| S1 | PlatformIO in the work folder builds a project that lies outside WLED's folder, with WLED's platform and libraries. | It does, in 12 seconds for the first build: the platform was there, and the libraries were taken into the project's own folder. The image has 175,104 bytes. |
| S2 | Without WLED, sixteen outputs of the LED library's sixteen-lane parallel method and four of its RMT method work side by side, 180 LEDs each. | They do. Every one of the twenty pins carried 4,320 pulses in a send, which is 24 for each of 180 LEDs, and the program made 50 sends in every second of six, the longest taking 7.8 ms. The RMT method is the library's own, not the one WLED adds to it. |
| S3 | `LittleFS.begin(false)` mounts the file system WLED made, and the files of `/odrig` are read. | It does: the mount succeeded, and `/odrig` held `dvd.odrg` with 1,612 bytes, `hello.odrg` with 1,138, `mapping.json` with 184 and `show.json` with 162, the installed example show. Nothing was formatted or written. |
| S4 | A source file of the usermod is compiled into the standalone program through a file of one line that includes it. | It is. The three sources that both firmwares share, the files, the port and the HTTP transport, reach their platform through `odrig_platform.h`, of which each firmware has its own, and the trial was built with them: 238,064 bytes, and on the board it sent as before, 4,320 pulses on every pin and 50 sends a second. The WLED-based firmware is the same code after the change: its image differs from the one before in 65 bytes of 1,221,568, the hash of the build's own program file at `0xB0` and the checksum and hash at its end, because that file names the new header. |
| S5 | The parallel driver's buffer for sixteen lanes of 180 LEDs fits the memory it can use. | It does: with the twenty outputs made, 343,904 bytes of internal memory were free, and 8,386,091 of the external. |
| S6 | The pulse counter counts the rising edges on a pin that an output drives. | It does, on RMT pins and on pins of the parallel driver alike. |

The WLED-based firmware gives legs 1 to 4 to RMT and legs 5 to 20 to the parallel driver:
its probe build reports `rmt` for the first four outputs of the target file and `parallel`
for the other sixteen. The trial did the same.

Afterwards the WLED-based firmware was flashed again, and the board answered `status`
with the example show playing: the switch there and back left the show in storage.

**The playlist.** What the firmware gave on the board over USB on 2026-10-12, built with
the core that plays the playlist. No source of the usermod changed: the firmware and the
probe build were built again with the core and flashed.

- A show of two animations without `start`, at brightness 32: after a restart `status`
  answered `"playing":"all","animation":1`. The first animation, a loop of one second
  with a `repeat` of 4, had turns of 4 seconds, and the second, a loop of 3 seconds in a
  show with a `min_seconds` of 5, turns of 6 seconds: each as long as that within 0.6
  seconds, as `status` asked four times a second saw them over 26 seconds.
- The firmware from before, given the same show, answered `status` with the error
  `show-malformed`, brightness 0 and nothing playing: it does not know the members
  `repeat`, `max_seconds` and `min_seconds`. A show that has one of them goes on a board
  together with this firmware.
- The session of commands, with `play all` and `play` of an animation in it, got the
  replies the emulator gives.
- The demo show on the target file, which now plays its playlist, is refreshed 50 times
  a second, and so is the example show. The dense 60 x 60 clip compressed had 24 to 33
  sends a second in the probe build, where the run before this core recorded 29 to 36;
  uncompressed it had 44 or 45, as before. Every rate is inside the 20 to 50 the owner
  accepts, and what made the compressed clip slower in this run was not looked for.
- The whole board suite, 53 tests, passes in 55 minutes. Its last step leaves the
  firmware and the dim example show, whose cycle plays from its start.

**The bigger layout on the board.** What the board gave on 2026-10-16, with the firmware of
`master` installed over the socket marked COM:

- `big-storage` found WLED's layout with 10,354,688 bytes of storage, kept the settings
  and left `/odrig` empty: `status` answered `mapping-missing`, as a board without a show
  does.
- The way back: `restore-stock --full` wrote stock WLED with WLED's layout. Stock WLED
  answers no handshake on the socket marked COM, so the command ended with `no-reply`
  after it had written; `install-firmware` then put the firmware back on WLED's layout,
  with the network's name, its password and the limit of 850 mA, and `big-storage` moved
  the board again. Each step took one to three minutes.
- The owner's show of 2026-10-15, all 113 animations, together with three later ones,
  116 animations and 12,978,156 bytes, was installed with `install-show`: `space`
  answered 116 animations and 139,264 bytes free of 13,500,416, and the show's cycle
  played at 46 to 50 refreshes a second. Two later files were renamed for the board,
  whose names are at most 32 characters of small letters, and four later ones did not
  fit.
- Not seen yet: `status` over the board's Wi-Fi and the refusal of an update on WLED's
  page, which need a device on the board's network.

**The trial on the newer USB software.** What the board gave on 2026-10-16 with
`odrig-trial.bin` (SHA-256 `fed8357a…`), on the bigger layout with the owner's show of 116
animations, all through the socket marked COM:

- The bootloader of the software known good starts the trial. Its first three builds
  stopped at their start, as the raw output of the socket marked COM showed: the legacy ADC
  driver beside the new one, lwIP's raw API without its lock, and an address compared with
  `0U`. The patch `020-newer-software.patch` has the three changes.
- Then: `status` at 46 to 50 refreshes a second over 30 samples, and again after a
  restart; `space` 116 animations and 258,048 bytes free of 13,500,416; the settings kept.
  After a start, `list` answered `busy` for about 8 minutes while the 13 MB were read; the
  firmware known good took 491 s for 9 MB.
- The chip's own socket, with the Mac on it, logged `usb: a computer is on the port, which
  stays a serial port`; so the USB host, and with it a hub, is tried only without a
  computer there.
- The way back: `flash --image` of the firmware known good, and the trial again, each with
  the show and the settings kept. The trial's file system can raise the storage's disk
  version from 2.0 to 2.1 when it writes, and did so once while it stopped at its start
  again and again; the firmware known good then cannot mount the storage and WLED formats
  it, so the way back after that is `install-firmware` and `install-show`, which the trial's
  script did.
- The board suite with `ODRIG_BOARD_IMAGES=trial`, run from the seed's worktree: 16
  tests, 7 failures and 14 errors, none of them the trial's. The worktree lacks the stock
  image of `firmware/wled-16.0.1/`, which exists only in the first checkout, and the Mac,
  which reaches the chip's own socket through the hub of a USB-C display adapter, lost that
  socket during restarts, so esptool could not open it.
- The board was left on the trial, playing the owner's show.
- Not tried yet: a hub with its own power and a stick on the chip's own socket, without
  the Mac there.

**The microSD card.** What the board gave with the card's build, `odrig-microsd.bin` of
1,765,808 bytes, SHA-256 `fd089753d86c92d9cbfbb2e4823d49428e4b037213b656736636b9dd9a1950a5`,
on the bigger layout, with the owner's card of 122 animations, 16,475,328 bytes, in the
reader. [microsd.md](microsd.md#the-board-sessions) has both sessions in full.

- 2026-10-22, the Mac on the chip's own socket only: `flash --image` there, the show and
  the settings kept; the card mounted, 60001 and 60002 listed, and `play 60001` at 41
  refreshes a second. Then listed entries disappeared and were found again, in one open
  session, at 4 MHz, 1 MHz and 400 kHz alike. The 4 MHz image was built again with the
  same SHA-256 and flashed back.
- 2026-10-23, both sockets on the Mac and the commands through the socket marked COM,
  nothing flashed: all 122 animations listed as 60001 to 60122 after the installed one,
  and no entry lost in 161 samples over fifteen minutes. Four of them played past a
  loop boundary at 26 to 50 refreshes a second, the largest at 26 to 48, and the
  playlist went on to the card's animations by itself.
- Why the first day dropped out and the second did not is not known. The board was left
  on that image, playing, at brightness 32.

**The run of 2026-10-25.** What the board gave with the firmware of the run, built by
`python3 firmware/fw.py build` from the branch `seeds-28-to-39-unified`: first from
8aa68b9, which held seeds 28 to 34, 36, 37 and the rest of 38, `odrig-firmware.bin` of
1,801,536 bytes, SHA-256 `d57fea4f3b7f24ce158eb09c4778456d5e141461a81c82014157813a88effd22`,
then from ea73e23, which holds seed 35 too, 1,821,168 bytes, SHA-256
`868bce6ff06910d780c45ad3088d7255059af1e26ba49bbed975a5b346f7d262`, each written with
`flash --image` through the socket marked COM, the show and the settings kept, at
brightness 32. The board held 84 installed animations and no card: `space` gave
`"external":{"present":false,...}` and the log `sd: card not mounted; no card or unreadable
file system` at every start, so nothing of the card was tried.

- **Readiness (seed 33).** With the firmware of 8aa68b9, restarted by `read-limit` through
  COM: the first reply came within a second of the tool's end, already
  `"readiness":"checking"` with `"to_check":84`; `list` was answered during the check, all
  84 animations, 35 of them still with `"bytes":null`; the first refreshes were counted
  within two seconds; the check ended `ready` about 250 seconds after the restart (02:06:30
  to 02:10:40). `host` gave `odrig_ESP32-S3_16MB_opi Oct 25 2026 02:01:23 internal+microsd
  reset power-on`. A file that is no ODRG file, `broken-test.odrg`, installed with
  `--no-check`, was quarantined: `install-show` printed `outcome: degraded: 1 unavailable`,
  `list` gave it `"bytes":null` and `"fault":"bad-palette-size"`, `play 120` was refused
  with `unavailable`, and `fault` gave
  `{"work":"start","file":"broken-test.odrg","record":0,"bytes":0,"reason":"bad-palette-size"}`.
  A restart through the chip's own socket (`host` then said `reset other`) left on COM
  `#log 0.368 odrig: before this start: file broken-test.odrg unavailable:
  bad-palette-size` before the player's own line of that start. The install that took the
  file away printed `outcome: healthy`. With the firmware of ea73e23 `status`, `host` and
  `fault` were the same, and the reproducer of seed 31 ended `degraded`.
- **Content changes (seed 34).** With the firmware of 8aa68b9: `odrigctl remove 84` was
  answered in 0.95 s; `odrigctl upload 101 hebrew.marquee.odrgx`, 113 bytes, `committed`
  in 2.7 s; the same upload again `unchanged: the target holds this file already; nothing
  was sent`, `{"ok":true,"unchanged":true}`, in 0.69 s. `install-show --no-check
  --keep-copies` of a folder without the other 20 line tests and with a bad file wrote 18
  blocks, 73,728 bytes, 2 free first and then 16 in use, committed and compared, 280 s in
  all with the board's check after it, and kept 22 copies; the install that took the bad
  file away wrote 5 blocks, 20,480 bytes. `read-show` gave the manifests before (84
  animations), between (93 items, with the texts, the clocks and `order.txt`) and after
  (73 items). With the firmware of ea73e23, which keeps the catalog: `remove 107` in 2.2 s,
  the catalog's generation from 1 to 2 and its entries from 73 to 72; the upload of the
  same file in 2.4 s, generation 3, 73 entries; the same upload again `unchanged`; a
  checked `install-show --keep-copies` that took the reproducer of seed 31 away wrote 9
  blocks, 36,864 bytes, the catalog with them, in 68 s, `outcome: healthy`. The app was not
  flashed.
- **Bounded decoding (seed 31).** With no card, the reproducer, `python3 -m
  tests.core.huge_tail` (65,263 bytes that inflate to 64 MiB of zeros after a bad record),
  went into the board's own storage as item 130 with `install-show --no-check`, firmware
  of ea73e23. The check reached it after the 73 others and read it for about three and a
  half minutes (06:12:53 to 06:16:23). Meanwhile 29 samples of `status` over the chip's
  own socket took 0.43 to 0.61 s each through the command tool, 0.43 to 0.46 s before it,
  the refreshes stayed at 31 to 50 a second, and `host` kept `reset power-on`: no watchdog
  reset. The check ended `degraded`, the file quarantined with `bad-palette-index` after
  67,112,475 bytes of its body. Open: the reproducer on the card, and the time of each of
  the core's calls on the board, which the command tool's round trip does not show.
- **Quarantine (seed 32).** A bad file in the board's storage, and the reproducer: the
  board started, answered at once, played the rest at 49 refreshes a second, and `list`
  marked each with its `fault`. Open: a bad file on the card, and the owner's look at the
  app and the LEDs.
- **The saved order and the tests (seed 36).** The 21 line tests went: `lines-test.odrg`
  and `rainbow-lines-01` to `-20`, id 84 by `remove` and the others by `install-show`.
  `order move <revision> 101 1` put 101 first and `play all` began with it; 110 before
  101 likewise. `mapping test snake 1` to `20` were each `{"ok":true}`, with `mapping get`
  giving `"snake":<n>`, and `snake 21` was `bad-argument`; `mapping test on` and `off`
  likewise. Open: a card entry absent and back, and Snake 1 to 20 and the diagonal seen on
  the LEDs, which is the owner's look.
- **Texts and clocks (seed 37).** Ten files of `tests/vectors` uploaded as ids 101 to 110:
  the texts `hebrew.marquee`, `mixed.pan`, `finals.slide`, `english.static`, `rtl.down`,
  `tall.up` and `multiline.wrap`, and the clocks `analog`, `digital` and `melting`. Played
  one by one, `status` three seconds later gave 41, 50, 42, 50, 50, 50 and 32 refreshes a
  second for the texts and 28, 48 and 23 for the clocks, each clock with its `seed`, and
  `list` gave `"type":"text"` and `"type":"widget"`; with the firmware of ea73e23, 40, 38
  and 23 for 101, 108 and 110. Open: the owner's look at the LEDs and at the app.
- **The catalogs (seed 35).** With the firmware of ea73e23 `catalog` first gave
  `"internal":{"state":"none","uncataloged":73},"external":{"state":"absent"}`. `catalog
  rebuild internal` read the 73 files, its progress in `catalog`, and ended
  `"state":"ok","generation":1,"entries":73`. A restart then answered `ready`, 73
  checked, at its first reply, about two seconds after the tool's end, gave `list` with
  every size at once, and played within four seconds, where without the catalog the
  check had ended about 250 seconds after a restart. A checked `install-show` writes the
  catalog too, and an unchecked one that names no catalog removes it. Open: everything of
  the card, its catalog, uploads to it and removals from it, and the board keeping only one
  or two small animations inside, which waits for the card.
- **The card (seed 38).** Not mounted at any start of the run: tasks 8 and 9 are open.
- **Not explained.** The first `catalog rebuild internal`, sent through COM while the check
  after a start was under way, was followed by a restart whose reason `host` gave as
  `panic`; five rebuilds after it, two of them cancelled and two begun as that one was,
  through either socket while the check of a start without a catalog was under way, ran
  without one, and the panic's text was not captured. While a rebuild runs, `status` counts the files it has still to
  read in `to_check` (60 became 72). After a `read-limit` failed because another program
  had the COM socket open, every restart through the chip's own socket started the chip in
  its download mode (`rst:0x15 (USB_UART_CHIP_RESET),boot:0x0`), so that it answered on
  neither socket; a reset through COM with the boot line released started it normally
  (`boot:0x8`), and `flash` through COM put the firmware back.
- **The board was left** on the firmware of ea73e23 with 73 animations, the ten texts and
  clocks among them, the internal catalog `ok` at generation 1 after a last rebuild, the
  order beginning with 101, playing at brightness 32. Long reads of the storage through
  COM broke off at 5 to 8 percent several times late in the session, where they had not
  before; through the chip's own socket they did not, and its restart was followed by a
  reset through COM.

## Live pin assignments

The shared core durably commits a whole pin permutation through the mapping command
family. WLED keeps its startup physical outputs and driver channels; cached RGB
pointers are resolved to the logical leg currently assigned to each physical pin.
Both command transports and a complete refresh copy use the core lock, so a save
cannot split a frame between two assignments. The standalone output adapter follows
the same pin lookup contract. Its current main program remains a seed-12 trial,
not a complete standalone player or evidence that app control works on that trial.

The shared core handles `ignore ID 0|1` and atomic `remove many IDS` over serial and HTTP. The WLED drive adapter supplies optional external free/total bytes from FAT free clusters under its mutex. It never formats removable media, never writes a USB stick, and changes only files of a card's folder `odrig`, as the core asks ([microsd.md](microsd.md#plugging-in-and-pulling-out)). Unsupported hosts report unavailable capacity; the standalone image remains its existing trial, not a complete player.
