# Design: a USB stick through a hub

## Overview

The work goes in three stages, and each waits for the one before it.

1. **The trial build, without the board.** The firmware tool learns to build the
   firmware on the newer software, in a folder of the work folder of its own, beside the
   build known good and without touching it. The firmware gets a USB host library of its
   own, ESP-IDF 5.5.5's, compiled with its hub support on, and the log names what comes
   and goes. Nothing of the newer software is fetched before the owner approves the list
   of downloads below.
2. **The trial on the board**, in the owner's board session: the last firmware known good
   is kept, the trial build is flashed, everything the firmware does is checked without a
   hub and then with the owner's hub and stick. When anything is worse, the board is
   flashed back at once.
3. **The move**, only after the trial passed: the firmware, its probe build and the
   standalone firmware of seed 12 are built on the newer software, and the documents say
   what changed.

## What this design relies on

- The firmware's USB code is `firmware/usermod/odrig_drive.cpp`: the USB host library of
  ESP-IDF, a second client of it that says what comes and goes (seed 23), and Espressif's
  driver of flash drives, `usb_host_msc` 1.1.1, in `firmware/usb_host_msc/` (seed 20).
- The tool builds in WLED's folder with the environments of
  `firmware/platformio_override.ini.in`; `fwtool/env.py` gives every program it starts
  PlatformIO's folders inside the work folder.
- Arduino-ESP32 3.3.12 is built on ESP-IDF 5.5.5, and its libraries come compiled. ESP-IDF
  5.5's USB host serves hubs only with the option `USB_HOST_HUBS_SUPPORTED`, which is off
  unless switched on and which the configuration of Arduino-ESP32's libraries does not
  switch on. With it on, the library compiles two more sources, `ext_hub.c` and
  `ext_port.c`: the hub class driver of the USB standard and its ports.
- `usb_host_device_info` of ESP-IDF 5.5 gives a device's parent, the hub it is on and the
  port number, or none for a device on the port itself.
- The platform that carries Arduino-ESP32 3.3.12 in PlatformIO, pioarduino's
  `platform-espressif32` 55.03.312-1, needs PlatformIO 6.2.0 or later; WLED 16.0.1 pins
  6.1.17. The platform installs its tools and its own Python environment into
  PlatformIO's folder.

Where the trial shows otherwise, the code follows what was found, and the difference is
recorded in `docs/drifts.md`.

## The newer software

| What | Version |
|---|---|
| PlatformIO | 6.2.0 |
| The platform | pioarduino `platform-espressif32` 55.03.312-1 |
| Arduino-ESP32 | 3.3.12, built on ESP-IDF 5.5.5 |
| The compiler | `xtensa-esp-elf` 14.2.0 of 2026-01-21 |
| The USB host library | ESP-IDF 5.5.5's `components/usb`, commit `ff1bac0aeecdd2b797b9c3a558c6bd03629bc013`, with its hub support on |

It lives in `build/firmware/newer/`:

```
build/firmware/newer/
  venv/       its Python environment, with PlatformIO 6.2.0 and Node.js
  pio/        its PlatformIO folder: the platform, Arduino-ESP32, the compilers, and the
              platform's own Python environment
  pio-cache/  its build cache
```

Pip's and npm's caches are shared with the build known good: they only keep what was
fetched. `rm -rf build/firmware/newer` removes the newer software whole.

## The tool

- `fwtool/paths.py`: `NEWER`, `NEWER_VENV`, `NEWER_PYTHON`, and
  `NEWER_REQUIREMENTS = firmware/requirements-newer.txt`.
- `firmware/requirements-newer.txt`: PlatformIO 6.2.0 and every package it needs, pinned
  at the versions WLED's own `requirements.txt` pins where those fit, and
  `nodejs-wheel` 20.18.0, which WLED's build needs to pack its pages.
- `fwtool/env.py`: `child(caller, newer=False)`. With `newer`, PlatformIO's two folders
  are those of `build/firmware/newer/` and the programs of its `venv/bin` come first.
- `fwtool/toolchain.py`: `newer_environment()` makes the Python environment of the newer
  software when it is not there and installs `requirements-newer.txt` into it, again only
  when that file changed, as `python_environment()` does for the build known good.
- `fwtool/build.py`: the kinds `trial`, environment `odrig_trial`, image
  `odrig-trial.bin`, and `trial-probe`, environment `odrig_trial_probe`, image
  `odrig-trial-probe.bin`. Their build makes sure of WLED's source and of the newer
  software's Python environment, brings WLED's files back and applies the patches, writes
  the override file, and runs the newer software's PlatformIO with `newer=True`.
- `fwtool/cli.py`: `build --trial`, and with `--probe` the trial's probe build;
  `--stock` and `--standalone` do not go with it.
- `firmware/platformio_override.ini.in`:

  ```ini
  [env:odrig_trial]
  extends = env:odrig
  platform = https://github.com/pioarduino/platform-espressif32/releases/download/55.03.312-1/platform-espressif32.zip
  platform_packages =

  [env:odrig_trial_probe]
  extends = env:odrig_trial
  build_flags = ${env:odrig_trial.build_flags}
    -D ODRIG_PROBE
  ```

  The trial build then adds the USB host library and its flags to `odrig_trial`.
- `tests/board/support.py`: with the variable `ODRIG_BOARD_IMAGES=trial`, the board's
  suite flashes and builds the trial build and its probe build where it takes the
  firmware and the probe build, so that it runs on the newer software. Without the
  variable it is as it is.

`flash --image build/firmware/out/odrig-trial.bin` writes the trial build; `flash`
without `--image` writes `odrig-firmware.bin`, which the trial never replaces.

## The USB host library with hubs

Arduino-ESP32 3.3.12 comes with ESP-IDF's USB host library compiled, and compiled with its
hub support on: every memory variant of the ESP32-S3 in its libraries, `qio_opi` of this
board among them, has `CONFIG_USB_HOST_HUBS_SUPPORTED 1` and
`CONFIG_USB_HOST_HUB_MULTI_LEVEL 1` in its `sdkconfig.h`. The trial takes that library as
it is: nothing of ESP-IDF's source is in the repository or fetched for it, and no flag
sets its options. The support is the USB standard's own, and nothing of it names a hub of
one maker or model.

- **The driver of flash drives** stays `usb_host_msc` 1.1.1, which builds on the newer
  software unchanged.
- **WLED's libraries** are those of the build known good, at the same versions.

## What the trial leaves out, and why

WLED 16.0.1 is not made for Arduino-ESP32 3, and the trial changes no driver of the LEDs,
the Wi-Fi or the storage. What does not build there is left out of the trial, or given
the names the newer software uses:

- **Left out**, none of it used by this installation: WLED's DMX input and its library
  `esp_dmx`, the infrared remote and its library `IRremoteESP8266`, and WLED's own
  interrupt-driven RMT driver `NeoESP32RmtHI`. Its four RMT outputs take NeoPixelBus's own
  RMT driver instead, by WLED's switch `WLED_USE_SHARED_RMT`.
- **`ESP32_ARDUINO_NO_RGB_BUILTIN`** keeps Arduino-ESP32's driver of the board's RGB LED,
  and so its new RMT driver, out of the firmware: ESP-IDF stops a firmware at its start
  that holds both RMT drivers, and NeoPixelBus 2.8.4 uses the older one.
- **`firmware/newer/odrig_newer.h`**, read first by every source of the trial, gives
  NeoPixelBus's parallel driver the register macro for a call ESP-IDF 5.5 no longer has.
- **`firmware/patches/020-newer-software.patch`** changes WLED where the newer software
  renamed or moved something: its global `Network` takes the name `WLEDNetwork`, the LED
  PWM calls of Arduino-ESP32 3, SHA-1 without `_ret`, and the chip's information from its
  own headers. Every change is held by `ESP_IDF_VERSION_MAJOR >= 5`, so the build known
  good is the same.
- **The usermod** includes `soc/gpio_periph.h` in the probe build on the newer software.

## The log of what comes and goes

`odrig_drive.cpp`, the watcher of devices, works on both the software known good and the
newer software:

- It keeps every device that comes open, up to eight, each with its maker's and its
  product's number and its kind, so that it is told when each one goes: the library tells
  only the clients that opened a device. A ninth is described and closed at once.
- `a device came: maker 0781, product 5581, a stick` as today; on the newer software,
  when `usb_host_device_info` names a parent, `, on port <n> of a hub` is added. The
  part that asks for the parent is held by `#if ESP_IDF_VERSION_MAJOR >= 5`.
- `a device went: maker 0781, product 5581, a stick`: the line of a device that goes
  names it as its line of coming did; for a hub, `a hub`.
- The kind is that of the first interface, or of the device when it has none: `a hub`
  for the class 9, `a stick` for 8, `another device (class <n>)` for any other. No
  number of a maker or a product is compared with anything: it is only written.

The driver of flash drives keeps one stick: a second one that comes while one is read is
passed over until the first goes, as today.

## The trial on the board

The owner's board session does it, with the rules of "If you have a board":

1. **Keep the last firmware known good.** Before the board is touched, the image the
   board runs is kept with its SHA-256 in `build/firmware/out/known-good/`: the
   `odrig-firmware.bin` it was flashed with, or, when that is not certain, the firmware
   built again from `master` at the commit the board runs.
2. **Without a hub.** The trial build is flashed over the socket marked COM, with
   `flash --image build/firmware/out/odrig-trial.bin`. Then: it starts; `status`
   answers with a rate from 20 to 50; `ODRIG_BOARD_IMAGES=trial python3 firmware/fw.py
   test-board` passes, whose probe tests say that the twenty outputs carry their signal;
   the Wi-Fi network and WLED's page answer. The board's suite needs a computer on the
   port as the board starts, as it does today.
3. **With the hub and the stick.** The owner plugs the hub, fed by its power bank, into
   the port, and the stick into the hub. `odrigctl --port <COM> --log` shows the hub,
   the stick on a port of it, and the stick opened with its number of files; `list`
   shows the stick's animations. Then a stick on the owner's adapter without a hub,
   when the owner has one.
4. **The rollback.** When anything the firmware did before is worse, the board is
   flashed back at once with
   `flash --image build/firmware/out/known-good/odrig-firmware.bin`, and only then is the
   owner told. The seed's state becomes `suspended` until the owner decides.

What was seen goes into `docs/firmware.md`, "Verified on the board".

## The move

Only after the trial passed:

- `platformio_override.ini.in`: `odrig` and `odrig_probe` take the newer platform, the
  USB host library and its flags; `odrig_trial` and `odrig_trial_probe` go, and with them
  `build --trial` and the board suite's `ODRIG_BOARD_IMAGES`.
- The tool: `build` and `build --probe` build with the newer software's folder;
  `build --stock` stays with the software known good, on which stock WLED 16.0.1 is
  built, and so do `restore-stock` and the board's suite's stock image.
- The usermod: the parts held by `#if ESP_IDF_VERSION_MAJOR >= 5` lose the condition,
  and what was only for the software known good goes.
- The standalone firmware of seed 12: `firmware/standalone/platformio.ini.in` takes the
  newer platform and the same USB host library. Its trial on the board belongs to seed
  12's open tasks.
- `docs/firmware-additions.md`: the line "Reads a stick through any USB hub that has
  power of its own, on Espressif's newer USB software", seeds 20 and 22, done by
  `odrig_drive.cpp` and `firmware/usb_host/`, written again in another firmware, column
  "Seed 12" *No* until its spec takes it; the section "Coming" loses seed 22.

## Tests

- `tests/firmware/`: the environment `odrig_trial` and its pinned platform; the
  requirements of the newer software pinned exactly; `env.child(newer=True)` with its
  folders inside `build/firmware/newer/` and the build known good's untouched; that
  `build --trial` runs the newer software's PlatformIO on `odrig_trial` and keeps
  `odrig-trial.bin`, `build --trial --probe` on `odrig_trial_probe`, and that `--stock`
  and `--standalone` do not go with it; the library's sources
  and licence, `libArchive` false and the hub option among the flags; that no source of
  `firmware/usermod/` or `firmware/usb_host/` compares `idVendor` or `idProduct`; the
  watcher keeping up to eight devices, and the lines of a device that comes and goes.
- `tests/board/`: none new; with `ODRIG_BOARD_IMAGES=trial` the board's suite runs on
  the trial build and its probe build.

## Documents

`docs/firmware.md`: `build --trial`, the folder of the newer software and what it
fetches; the log's lines; the trial and what it showed; after the move, the newer
software in "What the tool needs", the hubs that were tried and the limits found.
`docs/firmware-prerequisites.md`: lines 9, 16 and 18 and the table of seeds.
`docs/firmware-additions.md` at the move. `AGENTS.md`: the seed leaves "What is coming"
when it is done. `docs/decisions.md`: a line in its change log.

## What the trial fetches

Nothing of this is on the Mac. The sizes are those the sources state; the total is about
700 MB. A line marked *named by its manifest* is a small manifest file that names the
real download; the file given is the one its release offers for a Mac with Apple's
processor, as far as could be told without fetching the manifest.

| # | What | Version | From | Size in bytes |
|---:|---|---|---|---:|
| 1 | PlatformIO, into `newer/venv` | 6.2.0 | `https://files.pythonhosted.org/packages/bf/98/6c5cc249129c72b076ca238a435c48b48568d866c12890e01ee50fb8f322/platformio-6.2.0-py3-none-any.whl` | 418,578 |
| 2 | Its other Python packages | the versions WLED pins, and `chardet` 5.2.0 | pip's cache in `build/firmware/pip-cache`; pip still asks PyPI's index | 0 new |
| 3 | PlatformIO's own SCons | `tool-scons` 4.41101.0 | `https://dl.registry.platformio.org/download/platformio/tool/tool-scons/4.41101.0/tool-scons-4.41101.0.tar.gz` | 523,448 |
| 4 | The platform | 55.03.312-1 | `https://github.com/pioarduino/platform-espressif32/releases/download/55.03.312-1/platform-espressif32.zip` | 2,128,229 |
| 5 | Arduino-ESP32 | 3.3.12 | `https://github.com/espressif/arduino-esp32/releases/download/3.3.12/esp32-core-3.3.12.tar.xz` | 42,843,632 |
| 6 | Arduino-ESP32's compiled libraries | 3.3.12 | `https://github.com/espressif/arduino-esp32/releases/download/3.3.12/esp32-core-3.3.12-libs.tar.xz` | 347,236,084 |
| 7 | The installer of ESP-IDF's tools, `tool-esp_install` | 5.3.5 | `https://github.com/pioarduino/esp_install/releases/download/v5.3.5/esp_install-v5.3.5.zip` | 54,139 |
| 8 | The compiler, `toolchain-xtensa-esp-elf`, named by its manifest | 14.2.0+20260121 | `https://github.com/pioarduino/registry/releases/download/0.0.1/xtensa-esp-elf-14.2.0_20260121.zip`, then `https://github.com/espressif/crosstool-NG/releases/download/esp-14.2.0_20260121/xtensa-esp-elf-14.2.0_20260121-aarch64-apple-darwin.tar.xz` | 1,601 and 170,666,656 |
| 9 | The debugger, `tool-xtensa-esp-elf-gdb`, which the platform installs with the compiler; named by its manifest | 17.1_20260402 | `https://github.com/pioarduino/registry/releases/download/0.0.1/xtensa-esp-gdb-17.1_20260402.zip`, then `https://github.com/espressif/binutils-gdb/releases/download/esp-gdb-v17.1_20260402/xtensa-esp-elf-gdb-17.1_20260402-aarch64-apple-darwin24.5.tar.gz` | 1,550 and 46,924,973 |
| 10 | esptool, `tool-esptoolpy`, named by its manifest | 5.4.0 | `https://github.com/pioarduino/registry/releases/download/0.0.1/esptoolpy-v5.4.0.zip`, then `https://github.com/espressif/esptool/releases/download/v5.4.0/esptool-v5.4.0-macos-arm64.tar.gz` | 989 and 62,531,864 |
| 11 | PlatformIO's home page, which the platform installs at every build | `contrib-piohome` 3.4.4 | `https://github.com/pioarduino/registry/releases/download/0.0.1/contrib-piohome-3.4.4.tar.gz` | 922,895 |
| 12 | The platform's own Python environment, `newer/pio/penv`: `uv` 0.13.1 first, by pip | 0.13.1 | `https://files.pythonhosted.org/packages/3b/31/fad7fd2ac81954d02d33765bf8535eb320fcc2d71f2603a5c1ba0b13b8ef/uv-0.13.1-py3-none-macosx_11_0_arm64.whl` | 14,391,237 |
| 13 | Then, by `uv`, the newest from PyPI of: `pioarduino` 6.2.0 or later, `littlefs-python`, `fatfs-ng`, `pyyaml`, `rich-click`, `zopfli`, `intelhex`, `rich`, `cryptography`, `certifi`, `ecdsa`, `bitstring`, `reedsolo`, `esp-idf-size`, `esp-coredump`, `pyelftools`, `freertos-gdb`, and what they need | at the time of fetching | PyPI | about 12,000,000 |

Not fetched: WLED's libraries, which are copied from the build known good; the other
compiler, `toolchain-riscv32-esp`, which the platform takes only for a project with a
folder `ulp`; CMake, Ninja and ESP-IDF itself, which it takes only to compile ESP-IDF's
libraries again, which this design does not do.

## What needs the owner

- The approval of the list of downloads above, before anything of it is fetched.
- Any further download that the trial build turns out to need.
- The trial on the board, steps 1 to 4, and the decision when it fails.
- The owner's checks at the end: the stick's animations on the LEDs, and the bench show
  left on the board.
