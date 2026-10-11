# Design: Firmware build with the player (seed 04)

## Overview

The firmware is WLED 16.0.1, built from its own source for its own environment
`esp32s3dev_16MB_opi`, with one usermod added. WLED stays the platform: it starts the chip,
mounts the file system, runs Wi-Fi and the web server, and drives the LED outputs. The
usermod, in `firmware/usermod/`, hosts the core of seed 02: it gives the core the files in
`/odrig`, sets WLED's outputs from the core's legs, holds WLED in its live mode so that
nothing else draws, and sends the core's LED data to the outputs. It carries commands
between the USB serial port and the core, and between `POST /odrig` and the core.

No file of WLED needs a change for this. WLED's serial handling is switched off by a build
flag WLED already has.

A Python tool, `firmware/fw.py`, sets up a toolchain inside `build/firmware/`, fetches
WLED, builds, flashes, restores stock WLED, and installs a show into the board's storage.

Decisions taken where the seed and the documents left a point open are listed in
`docs/drifts.md` under "Seed 04".

## What this design relies on

Seeds 01, 02 and 03 are not implemented when this is written. A task that finds one of the
following different records the difference in `docs/drifts.md` and follows the real code.

| From | Used here |
|---|---|
| Seed 01 | `python -m odrig pack`; the generators; `odrig.mapping.read`, `odrig.show.read`, `odrig.show.files`, `odrig.odrg.decode` and their reasons; `shows/example/show.json`; `/build/` in `.gitignore`. |
| Seed 02 | `core/include/odrig_core.h` exactly as its design prints it; `core/src/*.cpp` written in C++11 with no exceptions, no run-time type information, no heap use of its own and no system header beyond `stdint.h`, `stddef.h` and `string.h`; internal names in `namespace odrig`; the rules of use of the host interface. |
| Seed 03 | `python -m odrigctl`; `odrigctl.client.serial_exchange`; the emulator and its record mode; the HTTP rules of its "POST /odrig". |

## WLED 16.0.1: what was read and what is assumed

Everything in the first table was read in the source at the tag `v16.0.1`, which is commit
`29b389df1c1aaec6ff53aea742d17063b985906c`, or in the sources of the packages that tag
pins. Nothing was built or run.

### Read in the source

| # | Fact | Where |
|---|---|---|
| R1 | The environment `esp32s3dev_16MB_opi`: board `esp32-s3-devkitc-1`, memory type `qio_opi`, `custom_usermods = audioreactive`, flags `WLED_RELEASE_NAME="ESP32-S3_16MB_opi"`, `WLED_WATCHDOG_TIMEOUT=0`, `ARDUINO_USB_CDC_ON_BOOT=1`, `BOARD_HAS_PSRAM`, partition table `tools/WLED_ESP32_16MB_9MB_FS.csv`, flash 16 MB, `qio`, 80 MHz. | `platformio.ini` |
| R2 | The partition table: `nvs` 0x9000 (0x5000), `otadata` 0xE000 (0x2000), `app0` 0x10000 (0x300000), `app1` 0x310000 (0x300000), `spiffs` 0x610000 (0x9E0000 = 10,354,688 bytes), `coredump` 64 KB. | `tools/WLED_ESP32_16MB_9MB_FS.csv` |
| R3 | `platformio_override.ini` is read as an extra configuration and is ignored by WLED's git. `[platformio]` sets `build_cache_dir = ~/.buildcache`. | `platformio.ini`, `.gitignore` |
| R4 | The platform is Tasmota's `platform-espressif32` 2024.06.00: Arduino core 2.0.18, ESP-IDF 4.4.8, `toolchain-xtensa-esp32s3` 8.4.0. | `platformio.ini`; `platform.json` of that platform |
| R5 | The build runs `npm ci` and `npm run build` and stops without Node.js. Node 20 or later is asked for. PlatformIO is pinned at 6.1.17. The build scripts use Python 3.10 syntax. | `pio-scripts/build_ui.py`, `package.json`, `.nvmrc`, `requirements.txt`, `pio-scripts/validate_modules.py` |
| R6 | A usermod is a PlatformIO library with `"build": {"libArchive": false}`, named in `custom_usermods`. A bare name is looked up in WLED's `usermods/`; an entry `Name = <spec>` or a URL, `symlink://` included, is passed to `lib_deps` as it is and the library of that name is treated as a WLED module: it gets `wled00` and the include folders of the project's other libraries on its include path. After linking, each module must have a compilation unit in the program. | `pio-scripts/load_usermods.py`, `pio-scripts/validate_modules.py` |
| R7 | The usermod class and its hooks: `setup`, `loop`, `connected`, `handleOverlayDraw`, `handleButton`, `addToJsonState`, `addToJsonInfo`, `readFromJsonState`, `addToConfig`, `readFromConfig`, `appendConfigData`, `onMqttConnect`, `onMqttMessage`, `onEspNowMessage`, `onUdpPacket`, `onUpdateBegin`, `onStateChange`, `getId`. A usermod is one static object registered with `REGISTER_USERMOD`. | `wled00/fcn_declare.h`, `wled00/um_manager.cpp`, `usermods/EXAMPLE/` |
| R8 | Order of `WLED::setup()`: `Serial.begin(115200)`; `WLED_FS.begin(true)`; `deserializeConfigFromFS()`; `beginStrip()`, which calls `strip.finalizeInit()`; `UsermodManager::setup()`; later `initServer()`. | `wled00/wled.cpp` |
| R9 | `deserializeConfig()` fills the global list `busConfigs` from `hw.led.ins` of `cfg.json` and sets `doInitBusses`. It calls `UsermodManager::readFromConfig()` only when `cfg.json` has an `um` object. | `wled00/cfg.cpp` |
| R10 | `WS2812FX::finalizeInit()` removes all outputs, creates one for each entry of `busConfigs`, begins them, sets up the current limiter, empties `busConfigs`, loads the LED map and allocates the pixel buffer. | `wled00/FX_fcn.cpp` |
| R11 | `WLED::loop()` calls, in this order: `handleConnection()`; `handleSerial()` if `WLED_ENABLE_ADALIGHT` is defined; `handleNotifications()`; `handleTransitions()`; `UsermodManager::loop()`; `handleIO()`; then, only when `!realtimeMode \|\| realtimeOverride \|\| (realtimeMode && useMainSegmentOnly)`: the captive portal's DNS server, nightlight, playlists, presets and `strip.service()`; then, when `doInitBusses` is set, `strip.finalizeInit()`, `strip.makeAutoSegments()` and a write of `cfg.json`. | `wled00/wled.cpp` |
| R12 | `realtimeLock(timeoutMs, mode)` sets `realtimeMode`; with a timeout of 65000 it sets the end time to the largest value, so the mode does not time out. `exitRealtime()` ends it; `handleNotifications()` calls that when the end time has passed. The JSON interface can set `realtimeOverride` (`lor`) and end the mode (`live`). | `wled00/udp.cpp`, `wled00/json.cpp` |
| R13 | `WS2812FX::show()` copies its own pixel buffer to the outputs through the LED map and through gamma correction, then calls `BusManager::show()`. `BusManager::show()` calls `applyABL()`, the current limiter, and then every output's `show()`. | `wled00/FX_fcn.cpp`, `wled00/bus_manager.cpp` |
| R14 | `BusDigital::setPixelColor()` applies white balance when `Bus::_cct` is 1900 or more, applies the output's brightness with `color_fade(c, _bri, true)`, adds the colour to the limiter's sum, and stores it. `color_fade` returns the colour unchanged for 255. `Bus::setCCT()` and `BusManager::setBrightness()` are public. | `wled00/bus_manager.cpp`, `wled00/bus_manager.h`, `wled00/colors.cpp` |
| R15 | The limiter: with a global maximum above 0 it scales all outputs so that the estimated current stays below that maximum less 120 mA for the chip. The maximum comes from `hw.led.maxpwr` of `cfg.json`, 850 mA when absent; the current of one LED is 55 mA by default. | `wled00/bus_manager.cpp`, `wled00/cfg.cpp`, `wled00/const.h` |
| R16 | On the ESP32-S3 WLED has 4 RMT outputs and 8 more through a parallel driver, 12 in all. `PolyBus::getI()` gives an output RMT while fewer than 4 are taken and the output asks for RMT, and the parallel driver otherwise. The RMT outputs use WLED's own `NeoEsp32RmtHI` driver; the parallel ones use NeoPixelBus' eight-channel LCD method. `BusManager::add()` makes a placeholder for an output beyond 12. | `wled00/const.h`, `wled00/bus_wrapper.h`, `wled00/bus_manager.cpp` |
| R17 | Limits: 16,384 LEDs in all, 2,048 for one output, 192 KB of LED memory on the ESP32-S3. | `wled00/const.h` |
| R18 | `WLED_DISABLE_ADALIGHT` removes `WLED_ENABLE_ADALIGHT`. Without it `WLED::loop()` does not call `handleSerial()`, and `WLED::setup()` prints no `Ada` line and does not look for an Improv packet. `handleSerial()` is the only reader of the port: Adalight, TPM2, the letters `v`, `l`, `L`, `o`, `O`, the baud bytes, Improv and JSON. Improv answers are sent only after an Improv packet was received. | `wled00/wled.h`, `wled00/wled.cpp`, `wled00/wled_serial.cpp`, `wled00/improv.cpp` |
| R19 | With `ARDUINO_USB_CDC_ON_BOOT=1` and the board's `ARDUINO_USB_MODE=1`, `Serial` is the chip's USB serial and JTAG unit (`HWCDC`). It has a receive queue of 256 bytes, a send buffer of 256 bytes and a send time-out of 100 ms, and it checks whether a computer is connected before it sends. | board file of the platform; `cores/esp32/HWCDC.h`, `HWCDC.cpp` of Tasmota's Arduino core 2.0.18 |
| R20 | The web server is the global `server`, of the library `ESPAsyncWebServer` in Aircoookie's fork, version 2.4.2. `server.on(uri, method, onRequest, onUpload, onBody)` registers a handler; a handler matches its exact path and paths under it. `initServer()` adds `Access-Control-Allow-Origin: *` to every response. WLED keeps a request's body in `request->_tempObject`, which the request frees with `free()`. | `wled00/wled.h`, `wled00/wled_server.cpp`; `src/ESPAsyncWebServer.h`, `WebHandlerImpl.h`, `WebRequest.cpp` of that library |
| R21 | That library takes a body apart before any handler sees it when the content type starts with `application/x-www-form-urlencoded`, and when it is `text/plain` and the body begins with characters other than `{`, `[`, `&`, zero, followed by `=`. The body handler is then not called. A body without `=` becomes one form field named `body`, cut at `&`, with `+` and `%XX` decoded. | `src/WebRequest.cpp` (`_onData`, `_parsePlainPostChar`) of that library |
| R22 | Handlers of the web server run on the network task, not on the task of `loop()`. The loop task has a stack of 8,192 bytes, and so has the network task. | `src/WebServer.cpp` of that library; `cores/esp32/main.cpp`; `platformio.ini` (`CONFIG_ASYNC_TCP_STACK_SIZE`) |
| R23 | Wi-Fi: with no network configured, `handleConnection()` waits 2 seconds after start and `initConnection()` opens the access point at once. With a network configured and the default setting, the access point opens after 12 seconds without a connection. `initAP()` gives the board the address 4.3.2.1 and starts the web server. `GET /json/info` reports `wifi.ap`. | `wled00/wled.cpp`, `wled00/json.cpp` |
| R24 | The file system object is `WLED_FS`, which is `LittleFS` on this build, mounted on the partition named `spiffs` and formatted when it cannot be mounted. | `wled00/wled.h`, `wled00/wled.cpp`; `libraries/LittleFS` of the Arduino core |
| R25 | After several crashes in a row at start, `handleBootLoop()` restores WLED's settings from their backup, then resets them, then switches to the other application partition. | `wled00/util.cpp` |
| R26 | WLED's own notes: a usermod's `loop()` runs up to 2,000 times a second when idle, 20 to 300 times under load, and as rarely as 1 to 3 times a second while the file system is written or many requests are served. | `AGENTS.md` |
| R27 | The release asset `WLED_16.0.1_ESP32-S3_16MB_opi.bin` has 1,232,640 bytes and the SHA-256 `bd31bba8e4cb16c387bcf5dfd78be11924a3dcda54fd1207fcc648eb97306e9b`, which is the checksum of the stock file kept beside this repository. | GitHub's release data for `v16.0.1`; `firmware/wled-16.0.1/SHA256SUMS` in the main checkout |
| R28 | The C++ level: the build script of Tasmota's Arduino core, at its tag 2.0.18, compiles with `-std=gnu++11 -fexceptions -fno-rtti -Os`. WLED's own notes say GCC 8.4 with C++17 for this platform. WLED's sources keep to C++11 (for example its "C++11 compatible constexpr" hash). | `tools/platformio-build-esp32s3.py` of `tasmota/arduino-esp32`; `docs/esp-idf.instructions.md`, `wled00/wled_metadata.cpp` |

### Assumed, to be verified by an early task

| # | Assumption | Verified in |
|---|---|---|
| A1 | PlatformIO 6.1.17 installs and runs under this Mac's Python, which is 3.14. If it does not, the newest 6.1 release that does is used and recorded. | Task 1 |
| A2 | `nodeenv` puts Node 20.18 for this Mac into the work folder. If it does not, the Node.js already on the Mac is used and recorded. | Task 1 |
| A3 | `PLATFORMIO_CORE_DIR` and `PLATFORMIO_BUILD_CACHE_DIR` keep all of PlatformIO inside the work folder, the second one overriding R3's `~/.buildcache`; `npm_config_cache` and `PIP_CACHE_DIR` do the same for npm and pip. | Task 2, by comparing the home folder before and after |
| A4 | WLED's environment builds from source on this Mac, and the result starts on the board and answers `v`. | Task 2 |
| A5 | The C++ flag the build really uses, where R28's two sources disagree. The core is valid C++11, so it compiles under either. | Task 2, from the verbose build output |
| A6 | Writing only `app0` and erasing `otadata` leaves a board that starts the new image, with the bootloader and partition table already on it. | Task 2 |
| A7 | esptool 5.4.0 reads, writes, erases and verifies this board over its USB serial and JTAG unit, and resets it into and out of the bootloader. | Task 2 |
| A8 | PlatformIO accepts the usermod and the core as `symlink://` libraries outside WLED's folder, the usermod's include path reaches `odrig_core.h`, and WLED's check of linked modules passes. | Task 3 |
| A9 | `strip.finalizeInit()` and `strip.makeAutoSegments()` called from a usermod's `setup()` and `loop()` replace the outputs correctly, and ten outputs on pins 1 to 10 are all valid: four RMT and six parallel. | Task 3 |
| A10 | In live mode, with the usermod writing through `BusManager`, nothing of WLED writes to the outputs between two refreshes, and the outputs hold exactly the colours written. | Task 3, by reading the outputs back |
| A11 | With `WLED_DISABLE_ADALIGHT` the firmware writes nothing to the port after the chip's own start-up text, and the usermod can read and write the port from `loop()`. | Task 3 |
| A12 | A pass of WLED's loop, the push of 1,800 LEDs and, later, the decoding of a dense 60 x 30 frame fit well inside 20 ms. | Tasks 3 and 6 |
| A13 | littlefs-python 0.19.0 edits the board's storage image so that WLED still mounts it, and a file in the folder `/odrig` is read by `WLED_FS.open("/odrig/...")`. | Tasks 4 and 5 |
| A14 | The HTTP handler works on the board as R20 to R22 say. No agent can join the board's Wi-Fi network, so this is an owner's check. | Task 10 |

## Repository layout

```
firmware/
  fw.py                          the tool's entry; standard library only
  requirements.txt               esptool, littlefs-python and nodeenv at exact versions
  stock.sha256                   SHA-256 of the three stock WLED files
  platformio_override.ini.in     the build environments, with @REPO@ for the repository path
  patches/
    README.md                    what a patch file here is; the folder holds no patch
  fwtool/
    __init__.py
    cli.py                       subcommands, the error line, exit statuses
    paths.py                     the repository root, the work folder, the backup guard
    env.py                       the environment given to every child process
    toolchain.py                 the Python environment and Node.js in the work folder
    wled.py                      fetch, commit check, patches, the override file
    build.py                     runs PlatformIO, checks and copies the image
    partitions.py                reads a partition table
    flasher.py                   runs esptool: read, write, erase, verify
    stock.py                     the stock files and their checksums
    storage.py                   the LittleFS image: mount, replace /odrig, list, compare
    board.py                     finds the port; status and handshake through odrigctl
  usermod/
    library.json                 name "odrig", libArchive false
    odrig_usermod.cpp            the Usermod class: setup, loop, the lock, registration
    odrig_files.h, .cpp          memory, time, the files of /odrig, diagnostic text
    odrig_leds.h, .cpp           outputs from the legs, holding the LEDs, sending a refresh
    odrig_serial.h, .cpp         the port
    odrig_http.h, .cpp           POST /odrig
    odrig_probe.h, .cpp          the probe build's report; compiled only with ODRIG_PROBE
core/
  library.json                   lets PlatformIO take core/ as a library; no source changes
tests/
  firmware/                      needs no board
    __init__.py
    test_*.py
    support.py
  board/                         needs the board on USB
    __init__.py
    test_*.py
    support.py
  air/                           needs the board on USB and this Mac on the board's Wi-Fi
    __init__.py
    test_*.py
docs/
  firmware.md
```

The work folder, all of it ignored by git through `/build/`:

```
build/firmware/
  venv/            Python environment: PlatformIO, esptool, littlefs-python, nodeenv
  node/            Node.js and npm
  pio/             PLATFORMIO_CORE_DIR: platforms, toolchains, packages
  pio-cache/       PLATFORMIO_BUILD_CACHE_DIR
  npm-cache/, pip-cache/
  WLED/            WLED's source at the pinned commit, with .pio/ and node_modules/ inside
  out/             odrig-firmware.bin, odrig-probe.bin, stock-built.bin, each with .sha256
  storage/         storage images read from the board, named by time
```

`firmware/wled-16.0.1/` and `esp32-backup/` in the main checkout hold untracked files: the
three stock WLED files, and the factory backup. Nothing here tracks, moves or edits them.
`esp32-backup/` is never written to and never read by a tool.

## The tool

```
python3 firmware/fw.py setup
python3 firmware/fw.py build [--stock | --probe]
python3 firmware/fw.py flash [--port P] [--image PATH] [--expect status|wled|probe]
python3 firmware/fw.py restore-stock [--port P] [--full] [--stock-dir DIR]
python3 firmware/fw.py install-show DIR [--port P] [--no-check]
python3 firmware/fw.py read-show OUT [--port P]
python3 firmware/fw.py test
python3 firmware/fw.py test-board [--port P]
python3 firmware/fw.py test-air --http ADDRESS [--port P]
```

`fw.py` itself uses only the standard library. It makes sure the work folder's Python
environment exists and then runs `fwtool.cli` with that environment's Python, with the
repository root and `firmware/` on the module path, so that `fwtool` can import `esptool`,
`littlefs`, `odrig` and `odrigctl`.

A failure is one line `error: <reason>: <detail>` on standard error and status 1; a usage
error is status 2. Reasons: `setup-failed`, `wled-mismatch`, `patch-failed`,
`build-failed`, `image-too-large`, `image-missing`, `checksum-mismatch`, `stock-missing`,
`no-board`, `layout-mismatch`, `esptool-failed`, `no-reply`, `no-space`, `verify-failed`,
`backup-protected`, and for a show folder the reasons of seed 01.

### The environment of every child process (`env.py`)

| Variable | Value |
|---|---|
| `PLATFORMIO_CORE_DIR` | `build/firmware/pio` |
| `PLATFORMIO_BUILD_CACHE_DIR` | `build/firmware/pio-cache` |
| `PLATFORMIO_SETTING_ENABLE_TELEMETRY` | `No` |
| `npm_config_cache` | `build/firmware/npm-cache` |
| `npm_config_update_notifier` | `false` |
| `PIP_CACHE_DIR` | `build/firmware/pip-cache` |
| `PATH` | `build/firmware/node/bin`, `build/firmware/venv/bin`, then the caller's |

All paths are absolute. `HOME` is left alone.

### `setup` (`toolchain.py`, `wled.py`)

1. Fetch WLED: `git clone --depth 1 --branch v16.0.1 https://github.com/wled/WLED.git
   build/firmware/WLED`. If the folder exists, skip. Then `git rev-parse HEAD` must give
   the pinned commit, or `wled-mismatch`.
2. `python3 -m venv build/firmware/venv`, with the Python that runs `fw.py`, which must be
   3.10 or later.
3. `pip install -r build/firmware/WLED/requirements.txt`, which is WLED's own pinned
   PlatformIO 6.1.17 with its packages, then `pip install -r firmware/requirements.txt`.
4. `python -m nodeenv --prebuilt --node 20.18.0 build/firmware/node`.

Each step is skipped when its result is there. `firmware/requirements.txt` names
`esptool==5.4.0` and `littlefs-python==0.19.0`, the versions the proof-of-concept deploy
script was run with, and `nodeenv` at the version task 1 installs.

### `build` (`wled.py`, `build.py`)

1. `setup`.
2. Bring WLED's tracked files back to the pinned commit (`git checkout -- .` in
   `build/firmware/WLED`), then apply every `firmware/patches/*.patch` in name order with
   `git apply`; a failure is `patch-failed`. The folder holds no patch today.
3. Write `build/firmware/WLED/platformio_override.ini` from
   `firmware/platformio_override.ini.in`, with `@REPO@` replaced by the repository's
   absolute path. A path with a space in it is refused, because the library entries below
   cannot carry one.
4. `pio run -d build/firmware/WLED -e <environment>`: `odrig`, `odrig_probe`, or WLED's
   own `esp32s3dev_16MB_opi` for `--stock`.
5. Copy `.pio/build/<environment>/firmware.bin` to `build/firmware/out/` as
   `odrig-firmware.bin`, `odrig-probe.bin` or `stock-built.bin`, check that it is at most
   3,145,728 bytes (`image-too-large`), and write its SHA-256 beside it.

`firmware/platformio_override.ini.in`:

```ini
[env:odrig]
extends = env:esp32s3dev_16MB_opi
custom_usermods =
  odrig = symlink://@REPO@/firmware/usermod
lib_deps = ${esp32s3.lib_deps}
  odrig_core = symlink://@REPO@/core
build_unflags = ${common.build_unflags}
build_flags = ${common.build_flags} ${esp32s3.build_flags}
  -D WLED_RELEASE_NAME=\"odrig_ESP32-S3_16MB_opi\"
  -D WLED_WATCHDOG_TIMEOUT=0
  -D ARDUINO_USB_CDC_ON_BOOT=1
  -DBOARD_HAS_PSRAM
  -D WLED_DISABLE_ADALIGHT
  -I@REPO@/core/include

[env:odrig_probe]
extends = env:odrig
build_flags = ${env:odrig.build_flags}
  -D ODRIG_PROBE
```

Everything not named here, the board, the platform, the partition table and the flash
settings, is inherited from WLED's environment (R1). The audio usermod is left out because
`custom_usermods` is replaced. The release name differs from stock's, so WLED's information
shows which build runs, and WLED's own update page does not take a stock image for this
build by accident.

### How the usermod and the core enter the build

- `firmware/usermod/library.json` is `{"name": "odrig", "build": {"libArchive": false},
  "dependencies": {}}`. The entry `odrig = symlink://...` in `custom_usermods` makes WLED's
  script pass it to `lib_deps` and treat the library named `odrig` as a WLED module (R6).
- `core/library.json` is `{"name": "odrig_core", "version": "1.0.0", "frameworks": "*",
  "platforms": "*"}`. With it PlatformIO takes `core/` as a library through the second
  `symlink://` entry: it compiles `core/src/*.cpp` and offers `core/include`. A library
  named in `lib_deps` is always built. The `-I` flag gives every file the header's folder
  whatever the library finder decides.
- A `symlink://` library is used where it is: nothing is copied into WLED's folder or into
  `firmware/`, and the core's files are not touched.
- The core is compiled with the flags of the environment (R28, A5). It includes no Arduino
  header, so no macro of the framework reaches it.

## The usermod

One class, `OdrigUsermod`, derived from `Usermod`, one static object, registered with
`REGISTER_USERMOD`. It overrides `setup`, `loop`, `addToJsonInfo` and `onUpdateBegin`. It
has no settings of its own and writes nothing to `cfg.json`.

### `setup()`

1. Create the lock, a FreeRTOS mutex.
2. Start the core: `odrig_core_begin(&host)`, with the host functions of `odrig_files`.
   The time this call takes is kept for the report.
3. Take the LEDs and set the outputs: `hold()` of `odrig_leds`, which puts WLED into live
   mode and, because the outputs are not the legs' yet, calls `apply()`.
4. Register the HTTP handler (`odrig_http`).

`UsermodManager::setup()` runs after `beginStrip()` and before `initServer()` (R8), so the
outputs WLED made from `cfg.json` exist when step 3 replaces them, and the handler is in
place before the server starts.

### `loop()`

1. If an update of the firmware is in progress (`onUpdateBegin(true)` was the last call),
   return.
2. `hold()`: keep WLED in live mode and keep the outputs.
3. If WLED's access point is up, `dnsServer.processNextRequest()`, which WLED skips in live
   mode (R11).
4. The port: `odrig_serial`.
5. Playback: if `BusManager::canAllShow()`, take the lock, `odrig_core_poll(core, now())`,
   release it, and when the core produced a refresh, `send()` it.

Asking the core only when the outputs can take data means that every refresh the core
counts is sent, so `fps` in `status` is the board's real rate. When a pass of WLED's loop
or a transfer takes longer than 20 ms, the core skips grid times and `fps` falls below 50.

### Memory, time and files (`odrig_files`)

| Host function | On the board |
|---|---|
| `alloc` | `heap_caps_malloc(bytes, MALLOC_CAP_INTERNAL \| MALLOC_CAP_8BIT)`; if that gives nothing, the same with `MALLOC_CAP_SPIRAM`; NULL if both fail. Never freed. |
| `open` | The path is `/odrig/` followed by the name. `WLED_FS.exists(path)` false: 0. `WLED_FS.open(path, "r")` gives no file or a folder: -1. Otherwise keep the `File` and return 1. |
| `read` | `file.read(buffer, capacity)`: the count, 0 at the end. |
| `close` | `file.close()`. |
| `log` | Keeps the last line, at most 95 characters, for the report. Nothing is printed. |

`now()` is `esp_timer_get_time() / 1000` as an unsigned 64-bit number: milliseconds since
start, never wrapping.

The core asks for less than 60 KB for the ten-leg mapping and 100 items (seed 02). The
chip has about 330 KB of internal memory free after WLED starts.

### The outputs (`odrig_leds`: `apply()`)

For leg i of `odrig_core_leg`, with `start` the sum of the LED counts of the legs before
it, one entry is added to WLED's `busConfigs`:

```cpp
uint8_t pins[OUTPUT_MAX_PINS] = {(uint8_t)leg.pin, 255, 255, 255, 255};
busConfigs.emplace_back(TYPE_WS2812_RGB, pins, start, leg.led_count, COL_ORDER_GRB,
                        false, 0, RGBW_MODE_MANUAL_ONLY, 0,
                        LED_MILLIAMPS_DEFAULT,
                        (BusManager::ablMilliampsMax() * leg.led_count) / total,
                        0);
```

`busConfigs` is emptied first. Then `strip.finalizeInit()` and `strip.makeAutoSegments()`
are called, which is what WLED's loop does after a change of its LED settings (R10, R11),
without the write of `cfg.json` that WLED adds there.

With no legs, which is what an invalid mapping gives, `apply()` leaves WLED's outputs as
they are, `matches()` below is true, and `setup()` sends one dark picture through WLED's
own path, `strip.fill(BLACK)` and `strip.show()`. Live mode then keeps them dark.

The last argument asks for RMT; WLED gives RMT to the first four outputs and the parallel
driver to the others (R16).

**What ten legs mean on the ESP32-S3.** Legs 1 to 4 of the mapping file get the four RMT
outputs; legs 5 to 10 get six of the eight channels of the parallel driver, which sends
all its channels in one transfer from one buffer. A leg of 180 LEDs takes 5.4 ms on the
wire, so a refresh of all ten legs is out in under 6 ms, the two drivers starting within
the same call. The board can drive 12 legs. A thirteenth leg, a leg on a pin the chip
keeps for itself (19, 20, 22 to 37 on this module), or more than 16,384 LEDs gives an
output that does not work; the other outputs do. `apply()` counts the outputs that are
`isOk()` for the report.

### Holding the LEDs (`odrig_leds`: `hold()`)

Called from `setup()` and at the start of every `loop()`:

```cpp
if (realtimeOverride != REALTIME_OVERRIDE_NONE) realtimeOverride = REALTIME_OVERRIDE_NONE;
if (useMainSegmentOnly) useMainSegmentOnly = false;
if (realtimeMode != REALTIME_MODE_GENERIC) realtimeLock(65000, REALTIME_MODE_GENERIC);
if (doInitBusses) fill busConfigs from the legs;      // WLED re-creates them in this pass
else if (!matches()) apply();
```

- In live mode without override WLED's loop skips effects, presets, playlists and
  nightlight (R11), and the lock does not time out (R12). The three checks undo what
  WLED's interface or a network pixel sender can change, within one pass.
- `matches()` is true when WLED has as many outputs as the core has legs and each output
  has the type, start and length `apply()` gave it, and, when it works, the leg's pin.
  Together with the `doInitBusses` case this puts the mapping's outputs back when WLED's
  LED settings are saved.
- The runtime values the usermod changes (`realtimeOverride`, `useMainSegmentOnly`) are
  written to `cfg.json` only if somebody saves WLED's settings.

What still acts: a relay pin configured in WLED is still switched by WLED's own on and
off. WLED's switch and brightness slider no longer change the LEDs.

### Sending a refresh (`odrig_leds`: `send()`)

```cpp
BusManager::setBrightness(255);          // WLED's brightness transitions may have changed it
Bus::setCCT(-1);                         // no white balance
for each leg i:
    Bus *bus = BusManager::getBus(i);
    if (!bus || !bus->isOk()) continue;
    for n in 0 .. led_count - 1:
        bus->setPixelColor(n, RGBW32(rgb[3n], rgb[3n + 1], rgb[3n + 2], 0));
BusManager::show();
```

This writes to the outputs directly and does not pass through `strip`: so no LED map, no
matrix layout, no gamma correction and no segment touches the data (R13). At brightness
255 `setPixelColor` stores the colour unchanged (R14). `BusManager::show()` runs the
current limiter before it sends (R13, R15); its maximum is WLED's setting, changed in
WLED's LED settings page, which the usermod does not override.

Output i belongs to leg i because `apply()` made them in the legs' order.

### The port (`odrig_serial`)

Each pass reads what `Serial` has, at most 256 bytes. For each byte: take the lock,
`odrig_core_feed(core, now(), &byte, 1, on_reply, this)`, release the lock. `on_reply`
copies the reply into a buffer of `ODRIG_REPLY_MAX` bytes; after the lock is released the
buffer is written with `Serial.write`. So a reply is never written while the lock is held,
and no more than one reply is waiting at a time.

WLED opens `Serial` itself. With `-D WLED_DISABLE_ADALIGHT` nothing else of WLED reads or
writes it (R18). The usermod prints nothing but replies. The chip's own bootloader prints a
few lines at every reset; `odrigctl` skips every line that is not a reply.

### HTTP transport (`odrig_http`)

```cpp
server.on("/odrig", HTTP_ANY, onRequest, nullptr, onBody);
```

- `onBody(request, data, len, index, total)`: on the first call allocate a struct of a
  length byte and 128 bytes with `calloc` and keep it in `request->_tempObject`; copy the
  bytes whose position is below 128.
- `onRequest(request)`:
  1. `request->url()` is not `/odrig`: 404.
  2. `request->method()` is not `HTTP_POST`: 405 with the header `Allow: POST`.
  3. The line is the kept bytes; or, when the library took the body as a form (R21), the
     value of the form field `body` if there is one, cut to 128 bytes; or empty.
  4. Take the lock, `odrig_core_command(core, now(), line, length, reply, sizeof reply)`,
     release it.
  5. `request->send(200, "application/json", reply)`.

The handler runs on the network task (R22); the lock is what lets it call the core. The
timestamp is read after the lock is taken.

**The content type of the request.** The library decides from the content type whether a
handler sees the body (R21). With any type other than `application/x-www-form-urlencoded`
and `text/plain` the handler gets every byte. With those two, a body without `&`, `=`, `+`,
`%` and zero bytes arrives unchanged, by one path or the other; every valid command is such
a body. A body with one of those characters can reach the core changed, so its reply can
differ from the emulator's. `odrigctl` sends `application/octet-stream` and is exact for
every body.

### Wi-Fi

The usermod does nothing about Wi-Fi except step 3 of `loop()`. With no network to join
configured, WLED opens its access point 2 seconds after start, with the address 4.3.2.1,
and starts the web server (R23). The name and the password of the access point are WLED's
settings; `docs/wifi.md` lists choosing them as open.

### The report in WLED's information (`addToJsonInfo`)

Three entries under `u`, which WLED's information page shows:

| Entry | Value |
|---|---|
| `odrig show` | `ok`, or the text of `odrig_core_error`. |
| `odrig outputs` | `<working>/<legs>`, and for each output that does not work ` leg <n> pin <p>`. |
| `odrig start` | The milliseconds `odrig_core_begin` took. |

### The probe build (`odrig_probe`, only with `ODRIG_PROBE`)

The probe build is for the tests in `tests/board/`. It is not the build the installation
runs: once the firmware answers `status`, every board test ends by putting the firmware
back. In the probe build the port holds bytes back for as long as they are a beginning of
`#probe` followed by a newline. The complete line is answered by the usermod and does not
reach the core; anything else is passed on to the core unchanged, in order. The answer is
one JSON line, shown here on several:

```json
{"probe":1,"start_ms":412,"heap":251032,"realtime":1,"loops":1830,"sent":50,
 "gap_ms":21,"poll_us":1840,"send_us":2100,"overwritten":0,"limit_ma":730,"used_ma":96,
 "error":null,
 "outputs":[{"leg":1,"pin":1,"count":180,"ok":true,"driver":"rmt","crc":"5c2a90e1"}]}
```

`loops` and `sent` are the passes of `loop()` and the refreshes sent in the last full
second; `gap_ms`, `poll_us` and `send_us` are the longest time between two sends, the
longest `odrig_core_poll` and the longest `send()` since the last `#probe`; `overwritten`
counts the sends before which an output no longer held the colours of the send before it;
`crc` is the CRC-32 of the output's colours as read back with `getPixelColor`, three bytes
for each LED. With these a test can see, without eyes on the LEDs, that the outputs are the
mapping's, that they hold exactly the core's bytes, that nothing else wrote to them, and how
much time the board has left.

## Threads and the lock

| Task | Calls into the core |
|---|---|
| The loop task (`setup()`, `loop()`) | `odrig_core_begin`, `odrig_core_poll`, `odrig_core_feed`, `odrig_core_leg`, `odrig_core_error` |
| The network task (HTTP handlers, `addToJsonInfo`) | `odrig_core_command`, `odrig_core_error` |

Every call after `odrig_core_begin` is made with the lock held, so the calls follow one
another, which is what the core's rule of use asks for; the core keeps nothing that belongs
to a task. The lock is held for one call. The longest hold is one `odrig_core_poll`. The
LED data of the last refresh is read by `send()` on the loop task, which is also the only
task that polls, so it does not change while it is read.

## Flashing and rolling back

The flash regions the tools write, from R2:

| Region | Address | Written by |
|---|---|---|
| Bootloader | `0x0` | `restore-stock --full` only |
| Partition table | `0x8000` | `restore-stock --full` only |
| Boot selection (`otadata`) | `0xE000`, 0x2000 bytes | erased by `flash` and `restore-stock` |
| First application (`app0`) | `0x10000`, 0x300000 bytes | `flash`, `restore-stock` |
| Storage (`spiffs`) | `0x610000`, 0x9E0000 bytes | `install-show`, changed blocks only |

`nvs`, the second application partition and the core-dump partition are never written.

`flasher.py` runs esptool as `python -m esptool --chip esp32s3 --port P ...` from the work
folder's environment. It offers `read`, `write`, `erase_region` and `verify`, and refuses
every address outside the table above. It never passes `erase-flash`, and no code names
`espefuse`.

**`flash`**

1. The image and its `.sha256` exist and agree (`image-missing`, `checksum-mismatch`).
2. Find the port (`no-board`).
3. Read 0xC00 bytes at `0x8000`, parse them (`partitions.py`: entries of 32 bytes, magic
   `AA 50`, type, subtype, offset, size, name), and check the layout (`layout-mismatch`).
4. `erase-region 0xe000 0x2000`.
5. `write-flash --flash-mode keep --flash-freq keep --flash-size keep 0x10000 IMAGE`.
   esptool compares a checksum of what it wrote and resets the board.
6. Wait for the port, send `status` (`board.py`), and print the reply. No reply in 20
   seconds is `no-reply`. With `--expect wled`, used for the image of `build --stock`, the
   tool waits for WLED's handshake instead, as `restore-stock` does; with
   `--expect probe`, for a probe build, it waits for the answer to `#probe`.

**`restore-stock`** does the same with `WLED_16.0.1_ESP32-S3_16MB_opi.bin` from
`--stock-dir`, by default `firmware/wled-16.0.1/` under the repository root. Before step 4
it checks each file it will write against `firmware/stock.sha256`. With `--full` it also
writes `bootloader_s3.bin` at `0x0` and `partitions_s3_16m.bin` at `0x8000` in the same
esptool call. In step 6 it sends the byte `v` and waits for a line that starts with
`WLED ` (R18), using `odrigctl.client.serial_exchange` with its own `accept`.

`firmware/stock.sha256`:

```
bd31bba8e4cb16c387bcf5dfd78be11924a3dcda54fd1207fcc648eb97306e9b  WLED_16.0.1_ESP32-S3_16MB_opi.bin
53f1e17c81e72cdd99ce362ad9a8181a229d3879b11561b2e76052e1afa17c45  bootloader_s3.bin
9449a7020364b6a821261c8962f7683850809e13a8cd6c31dde7fe53308126b5  partitions_s3_16m.bin
```

The three files are not tracked. The application image can be fetched again from WLED's
release page and checked against the first line (R27).

Storage is not touched by either command. WLED's settings and the proof-of-concept show
stay where stock WLED finds them, and the files in `/odrig` stay where the firmware finds
them, so going back and forth loses nothing.

The last resort, written in `docs/firmware.md` and done by hand, is the factory backup:
a 16 MB image with its own checksum file in `esp32-backup/`. No tool reads or writes that
folder; `paths.py` refuses every output path under it (`backup-protected`).

**The port and resets.** `board.py` finds the port (Requirement 4 criterion 5). Opening the
port in the ordinary way resets the chip, so every exchange with the running firmware goes
through `odrigctl.client.serial_exchange`, which lowers RTS before DTR. esptool resets the
chip on purpose, into the bootloader before its work and into the firmware after it.

## Installing a show

**`install-show DIR`** (`storage.py`, `flasher.py`):

1. Unless `--no-check`: `DIR` must be a valid installed file set, checked with seed 01's
   readers as the core will check it: `odrig.mapping.read`, `odrig.show.read`, every file
   of `odrig.show.files` present, decodable with `odrig.odrg.decode` and of the mapping's
   canvas size, and no other entry in the folder. A failure is seed 01's reason.
2. Find the port; read and check the partition table; take the offset and size of `spiffs`
   from it.
3. Read the whole partition into `build/firmware/storage/<time>-before.bin`, leaving the
   chip in the bootloader.
4. Mount the image with littlefs-python. The block size, the block count and the disk
   version are read from the image's superblock (the three 32-bit numbers 12 bytes after
   the text `littlefs`) and given to the library, so the image keeps the version WLED's
   file system wrote.
5. Remove `/odrig` with everything in it, create it again, and write every file of `DIR`
   into it in name order. Running out of room is `no-space`; nothing has been written to
   the board at that point.
6. Unmount. In the new image, list `/odrig` and compare every file with `DIR`
   (`verify-failed`); compare every file outside `/odrig` with the image as read.
7. Compare the two images block by block (the block size of step 4), join neighbouring
   changed blocks into runs, and write all runs with one `write-flash` call, each run at
   its own address, keeping the chip in the bootloader.
8. `verify-flash` of the whole partition against the new image (`verify-failed`), then
   reset.
9. Wait for the port, send `status`, print the reply. Status 1 if the reply's `error` is
   not null.

This is the method of the proof-of-concept `tools/wled_deploy.py`, which is known to work
on this board: read the partition, edit it with littlefs-python at the disk version found,
write back the changed blocks.

**`read-show OUT`** does steps 2 to 4 and copies the files of `/odrig` into `OUT`, which
must be new or empty.

Reading the partition takes about a minute.

## What the firmware changes in WLED and what it leaves

| Changed | Left as it is |
|---|---|
| The LEDs show only the core's data. Effects, presets, playlists, the boot preset and nightlight do not run. | Wi-Fi, the access point and all network settings. |
| The outputs are the mapping's; WLED's LED output settings are replaced when saved. | The web interface, the JSON interface and WebSocket. |
| WLED's switch, brightness slider and live-override do not change the LEDs. | The current limiter and its maximum in WLED's LED settings. |
| The USB serial port speaks only `docs/commands.md`. | The file system and every file of WLED on it. |
| WLED's information shows `odrig` entries and the release name `odrig_ESP32-S3_16MB_opi`. | Updates through WLED's own interface. |
| The audio usermod of the stock build is not included. | Buttons, relay and infrared settings. |

## Error handling

- The usermod has no failure of its own that stops WLED. Without a core
  (`odrig_core_begin` returned NULL) it holds the LEDs dark, the port gets no reply, and
  `POST /odrig` gets status 503.
- An invalid show is the core's matter: dark LEDs, the reason in `status`.
- An output that cannot be made is reported in WLED's information; the rest runs.
- The tool checks before it writes: the image, the checksums, the partition table, the
  show folder, the room in storage. After a failure in the middle of writing, the command
  is run again; the storage image read before is in the work folder.
- A usermod that crashes at start several times in a row makes WLED restore and then reset
  its settings (R25). The files in `/odrig` are not affected, and a storage image from
  before is in the work folder.

## Testing strategy

Three suites, each `unittest`, each selected by discovery, each run by the tool with the
work folder's Python from the repository root:

```
python3 firmware/fw.py test                      python -m unittest discover -s tests/firmware -t .
python3 firmware/fw.py test-board                python -m unittest discover -s tests/board -t .
python3 firmware/fw.py test-air --http ADDRESS   python -m unittest discover -s tests/air -t .
```

`tests/board/__init__.py` and `tests/air/__init__.py` stop the whole run with `no-board`
when no board is found, and `tests/air` also when the address does not answer; their
module texts start with what they need. No command, script or document lists test files.

### `tests/firmware/`: no board

| File | What it proves |
|---|---|
| `test_paths.py` | The work folder is inside the repository; every output path under `esp32-backup/` is refused with `backup-protected`; no source of the tool or of the tests names `esp32-backup` except the guard and this test. |
| `test_env.py` | The environment of a child process has the six variables, each an absolute path inside the work folder, and the caller's `HOME`. |
| `test_wled.py` | With a small git repository made by the test: a checkout at another commit is `wled-mismatch`; patches are applied in name order and a bad patch is `patch-failed`; the override file is the template with the repository path in place of `@REPO@`, names the usermod, the core and `WLED_DISABLE_ADALIGHT`, and does not name `audioreactive`; a repository path with a space is refused. |
| `test_partitions.py` | A table built in the test from the values of R2 is parsed to the six partitions; a table without `spiffs`, with `app0` elsewhere, or with a wrong magic is `layout-mismatch`. |
| `test_flasher.py` | With a stand-in for the esptool process that records its arguments: `flash` erases `0xe000 0x2000` and writes one file at `0x10000`; `restore-stock` the same, and with `--full` also `0x0` and `0x8000`; `install-show` writes only inside the storage partition; an address outside the table of regions is refused; `erase-flash` and `espefuse` never appear. |
| `test_stock.py` | `firmware/stock.sha256` has three lines of the right form; a changed stock file is `checksum-mismatch` and a missing one `stock-missing`, both before any esptool call. |
| `test_storage.py` | On an image the test makes with littlefs-python at disk version 2.0, with files like WLED's and an old `/odrig`: after installing, `/odrig` holds exactly the new files with their bytes; every other file is unchanged; the disk version in the superblock is unchanged; the runs of changed blocks, applied to the old image, give the new one; a show larger than the free room is `no-space`; `read-show` gives the files back; an invalid show folder is refused with seed 01's reason, and accepted with `--no-check`. |
| `test_board.py` | The choice of the port: `--port`, the variable, one device, none, two. |
| `test_cli.py` | Usage errors give status 2; a failure gives the error line and status 1; `image-missing`, `checksum-mismatch` and `image-too-large`. |
| `test_usermod_files.py` | `firmware/usermod/library.json` and `core/library.json` have the content the design gives; no file under `firmware/` has the name of a file of `core/src`; the usermod's sources include only `wled.h`, `odrig_core.h` and their own headers; `Serial` is named only in `odrig_serial` and `odrig_probe`; the probe's code is inside `#ifdef ODRIG_PROBE`. |
| `test_docs.py` | `docs/firmware.md` names every command of the tool, the three test commands, the regions the tools write, and every owner's check. |

### `tests/board/`: the board on USB

`support.py` packs shows with brightness 32: it copies a show file with the `brightness`
member replaced, and refuses to install a folder whose `show.json` has a brightness above
40. It builds and flashes the probe build when a test needs it, and its last step puts the
firmware and the dim example show back.

| File | What it proves |
|---|---|
| `test_flash_restore.py` | `restore-stock` leaves a board that answers `v` with `WLED `; `flash` after it leaves a board that answers `status`; storage read before and after the pair has the same files. |
| `test_install.py` | After `install-show` of the dim example show, `read-show` gives byte-identical files and `status` reports no reason and `playing` 3; WLED's `cfg.json` in storage is unchanged; folders with a missing animation, a damaged animation, an animation of another canvas size and no `show.json`, installed with `--no-check`, each give the reason text the emulator gives for the same folder, and `play` gives `show-invalid`. |
| `test_commands.py` | One session, kept in `support.py`, with every command of `docs/commands.md`, every error code `odrigctl` can cause (`play 99`, `play abc`, `brightness 256`, `play` with 70 digits, and `play 1` on an invalid show) and no brightness above 40, sent with `odrigctl --port` to the board and to an emulator running the same folder: the replies are the same, `fps` aside. |
| `test_probe.py` | Probe build. With the example show: two outputs, pins 1 and 2, 180 LEDs, both working. With the ten-leg mapping: ten working outputs on pins 1 to 10, four `rmt` and six `parallel`. With a one-frame show in which every pixel has its own colour, at brightness 40, 32 and 1 and after `brightness` commands of 0 to 40: each output's `crc` equals the CRC-32 of that leg's bytes in the emulator's recording of the same folder and commands. After `off`: the CRC of zeros. `overwritten` stays 0 over 30 seconds. `realtime` is 1. Nothing arrives on the port in 5 seconds without a command; `v` gets no answer. |
| `test_fps.py` | `status` reports 49 or more for 10 full seconds in a row: with the dim example show; with the ten-leg mapping and the dense 60 x 30 clip of 10 seconds, compressed, and again uncompressed; and while `status` is asked five times a second. |
| `test_measure.py` | Probe build. Prints, and writes to `build/firmware/out/measurements.json`: `start_ms`, `loops`, `gap_ms`, `poll_us` and `send_us` for the example show, for the dense clip compressed and uncompressed, and for storage filled with 9 MB of dense clips. It fails only when a value is missing. |

### `tests/air/`: this Mac on the board's Wi-Fi

| File | What it proves |
|---|---|
| `test_http.py` | The session of `tests/board/support.py` over `odrigctl --http` gives the replies it gives over the port; `GET`, `PUT` and `OPTIONS` on `/odrig` give 405 with `Allow: POST`; `/odrig/x` gives 404; a body of 10,000 bytes gives `line-too-long`; `play 1` with the content types `application/octet-stream`, `text/plain` and `application/x-www-form-urlencoded` gives `{"ok":true}`; a command over HTTP changes `status` on the port. |
| `test_wled.py` | `GET /json/info` reports `wifi.ap` true, the release name `odrig_ESP32-S3_16MB_opi` and the three `odrig` entries; WLED's start page is served; after WLED's LED settings are saved through `/json/cfg` with one output on another pin, the probe-free check holds: `odrig outputs` still reports the mapping's outputs working. |

### Who checks what

| Item of the definition of done | Checked by |
|---|---|
| 1. The example show plays at power-on, by eye | The owner |
| 2. 49 or more refreshes per second, example show | `test_fps.py`; the owner repeats it with two legs wired |
| 3. Same replies as the emulator | `test_commands.py` |
| 4. The installed folder is byte-identical | `test_install.py` |
| 5. Ten-leg mapping, dense 60 x 30, compressed and uncompressed | `test_fps.py` |
| 6. Stock WLED restored and answering | `test_flash_restore.py` |
| 7. The board's Wi-Fi network and HTTP | The owner joins the network and runs `test-air` |
| 8. Documentation | `test_docs.py` |

Today one 60-LED strip is wired, on leg 1, fed from the board's 3.3 V pin. Every show a
test installs has a brightness of 40 or less for that reason, and nothing an agent runs
needs eyes on the LEDs.

## Risks

1. **Time on the board.** Decoding a dense 60 x 30 frame, sending 1,800 LEDs and one pass
   of WLED's loop have never been measured together. Task 3 measures the pass and the
   send with a test pattern, task 6 with the core. If decoding the compressed file is too
   slow, `docs/format.md` keeps uncompressed files as the fallback.
2. **Stalls of WLED's loop.** WLED's notes say the loop can slow to a few passes a second
   while its file system is written or many requests are served (R26). Playback runs in
   that loop, so it would stutter then, and `fps` would show it. If `test_fps.py` or the
   measurements show this in ordinary use, playback moves to a task of its own; that
   design is written then, with the measurements, and recorded in `docs/drifts.md`.
3. **Ten outputs.** Six of them use the parallel driver, which this project has never
   run, and legs 3 to 10 are not wired. Task 3 shows that the outputs are created; that
   LEDs light on them needs wiring.
4. **HTTP is checked by a person only.** No agent can join the board's network, and the
   web server library treats bodies by content type (R21).
5. **The toolchain.** PlatformIO 6.1.17 under Python 3.14, Node.js through `nodeenv`, and
   keeping everything out of the home folder are untried (A1 to A3).
6. **Start-up time.** The core decodes every file at start. With storage full of dense
   animation this may take many seconds, during which the LEDs are dark and the board
   answers nothing. Task 8 measures it.
7. **WLED's boot-loop handling** can reset WLED's settings if the usermod crashes at
   start (R25).
8. **Power.** The wired strip is fed from the 3.3 V pin. A test that installed a bright
   show could overload it; `tests/board/support.py` refuses such a show.
9. **PlatformIO and libraries outside WLED's folder** (A8): if `symlink://` entries do not
   work as read, the fallback is a build flag that names the folders and a source filter
   in the usermod's `library.json`; still no copy.

## Documentation

- `docs/firmware.md`: what the tool needs; the work folder; every command with an example;
  the flash regions; rolling back, the factory backup included; what the firmware changes
  in WLED and what it leaves; the access point and `POST /odrig`; the content type of
  requests; the three test commands; the owner's checks as numbered steps; the facts
  verified in tasks 1 to 3; the measurements of task 8.
- `README.md`: one sentence pointing to `docs/firmware.md`.
- `docs/decisions.md`: the two open questions about the board get what was measured.
