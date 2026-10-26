# Design: standalone firmware as a fallback

## Overview

The standalone firmware is a small Arduino program for the ESP32-S3, built with the
PlatformIO that the firmware tool already keeps in its work folder. It does what the
usermod does inside WLED, without WLED around it:

- it mounts the board's storage and starts the shared core on the folder `/odrig`;
- it carries bytes between the USB serial port and the core, and command lines between
  a web server and the core;
- it reads the network's name and password and the limit on LED current from the stored
  settings, the two files WLED reads and the firmware tool writes;
- it drives one output per leg with the LED library WLED uses, sixteen on the chip's
  parallel driver and four on RMT;
- it applies WLED's limit on LED current, with WLED's arithmetic.

Three source files of the usermod carry no decision of WLED's and are compiled into both
firmwares: the files, the port and the HTTP transport. Everything about WLED's outputs
and WLED's live mode stays in the usermod; the standalone firmware has an output layer of
its own.

The work starts with a spike on the board, task 1, because four things this design
depends on are assumed and not known.

## What this design relies on

- Seeds 02, 04, 05 and 07 are implemented: the core with its host interface of fourteen
  functions, the firmware tool, the patch for twenty outputs, and the content commands.
- Seed 08 is implemented before task 8 of this spec: its command `set-wifi` puts the
  name and the password into the stored settings. Without it the standalone firmware
  hosts no network, by Requirement 4.3, and its HTTP transport cannot be tried.
- Seed 15 need not be implemented. Without it `/cfg.json` holds no `hw.led.maxpwr` of
  ours and the limit is 850, as with the WLED-based firmware.
- Where the code differs from what is written here, the code is followed and the
  difference is recorded in `docs/drifts.md`.

## WLED 16.0.1 and the usermod: what was read

Read in the work folder's checkout of WLED at the pinned commit, and in `firmware/`.

| | What | Where |
|---|---|---|
| R1 | The environment `esp32s3dev_16MB_opi`: board `esp32-s3-devkitc-1`, memory type `qio_opi`, flash of 16 MB at 80 MHz in mode `qio`, the flags `ARDUINO_USB_CDC_ON_BOOT=1` and `BOARD_HAS_PSRAM`, the partition table `tools/WLED_ESP32_16MB_9MB_FS.csv`. | `platformio.ini` |
| R2 | The platform is `https://github.com/tasmota/platform-espressif32/releases/download/2024.06.00/platform-espressif32.zip`. The LED library is `https://github.com/Makuna/NeoPixelBus.git#1d7ff38f14d04a976f9c6e365c83a232bcba04fc`, the web server `https://github.com/Aircoookie/ESPAsyncWebServer.git#v2.4.2` with `esp32async/AsyncTCP @ 3.4.7`. | `platformio.ini` |
| R3 | The partition table: `nvs` at 0x9000, `otadata` at 0xe000, `app0` at 0x10000 with 0x300000 bytes, `app1`, and `spiffs` at 0x610000 with 0x9E0000 bytes, which holds a LittleFS file system. | `tools/WLED_ESP32_16MB_9MB_FS.csv` |
| R4 | WLED mounts the file system with `LittleFS.begin(true)`: it formats a file system it cannot mount. | `wled00/wled.cpp` |
| R5 | The access point: `WiFi.softAPConfig(4.3.2.1, 4.3.2.1, 255.255.255.0)`, then `WiFi.softAP(name, password, channel, hidden)`. | `wled00/wled.cpp` |
| R6 | The limiter, in its global form. For each output, `used = sum * 55 / 765 + length`, where `sum` is the sum of the red, green and blue values of its LEDs and the division drops the remainder. `total` is the sum of `used` over the outputs and `leds` the number of all LEDs. `allowed` is the maximum less 120, or 1 when the maximum is 120 or less. When `allowed` is above `leds` and `total` is above `allowed`, the level is `allowed * 255 / total + 1`; when `allowed` is not above `leds`, the level is 1; otherwise nothing is dimmed. | `wled00/bus_manager.cpp`, `applyABL` and `estimateCurrent` |
| R7 | Dimming a colour to a level below 255. Black stays black. Otherwise each of red, green and blue becomes `(value * level + 127) >> 8`, and then its lowest bit is set when the value was above `(largest >> 2) + 1`, where `largest` is the largest of the three. | `wled00/colors.cpp`, `color_fade` with `video` |
| R8 | The usermod gives every output 55 mA for one LED and a share of the maximum in proportion to its LEDs. With a maximum of 0 every share is 0, no output counts for the limiter, and nothing is dimmed. | `firmware/usermod/odrig_leds.cpp`; `wled00/bus_manager.cpp` |
| R9 | `odrig_files.cpp` takes from WLED only the file system object, `WLED_FS`. `odrig_serial.cpp` takes only the Arduino `Serial`. `odrig_http.cpp` takes WLED's web server object, `server`. All three reach these through `#include "wled.h"`. | `firmware/usermod/` |
| R10 | The name of the access point is `ap.ssid` of `/cfg.json`, its channel `ap.chan`, and its password `ap.psk` of `/wsec.json`. | `docs/specs/08-p1-wifi-name-and-password/design.md`, W4 to W6 |
| R11 | `flash` writes the first application partition and clears the boot selection. It writes nothing else. | `firmware/fwtool/cli.py`, `write_application` |

## Assumed, to be verified by task 1

| | Assumption | If it does not hold |
|---|---|---|
| S1 | PlatformIO in the work folder builds a project that lies outside WLED's folder, with the platform and the libraries of R2, from what `setup` has already fetched. | `setup` fetches what is missing; the design is unchanged. |
| S2 | In a program without WLED, sixteen outputs of the library's `NeoEsp32LcdX16Ws2812xMethod` and four of its RMT methods work side by side, 180 LEDs each. | The seed's twenty outputs cannot be had this way. The finding is written down with what was tried, the firmware keeps the largest number that works, and the remaining tasks are done. |
| S3 | `LittleFS.begin(false)` mounts the file system WLED made, and the files of `/odrig` are read as WLED reads them. | The mount is given the partition's label and the base path WLED's build uses, read from the Arduino core. |
| S4 | A source file of `firmware/usermod/` is compiled into the standalone program through a file of one line in `firmware/standalone/src/` that includes it. | The three files move to `firmware/shared/`, and the usermod's `library.json` names that folder. |
| S5 | The parallel driver's buffer for sixteen lanes of 180 LEDs fits the memory that can be used for it, as it does inside WLED. | The finding is written down; the number of outputs is the largest that fits. |
| S6 | The pulse counter counts the rising edges on a pin that an output drives, as the WLED-based probe build does. | The probe report gives `pulses` as `null`, and Requirement 9.3 is recorded as not shown. |

Task 1 writes what it found into `docs/firmware.md`, "Verified on the board", and into
`docs/drifts.md` where a finding changes this design.

## Repository layout

```
firmware/
  usermod/
    odrig_files.cpp, odrig_serial.cpp, odrig_http.cpp   changed: include odrig_platform.h
    odrig_pulses.h, odrig_pulses.cpp                    new: the pulse counter, moved out of odrig_probe.cpp
    wled/odrig_platform.h                               new: the platform for the usermod
  standalone/
    platformio.ini.in        new: the build environments, with @REPO@ and @WLED@
    platform/odrig_platform.h new: the platform for the standalone program
    src/
      main.cpp               new: the start, the task, the loop, the lock
      settings.h, settings.cpp new: the stored settings; no Arduino in it
      limit.h, limit.cpp     new: the limiter; no Arduino in it
      outputs.h, outputs.cpp new: the twenty outputs
      network.h, network.cpp new: the access point and the web server
      probe.h, probe.cpp     new: the probe report, only with ODRIG_PROBE
      shared_files.cpp, shared_serial.cpp, shared_http.cpp, shared_pulses.cpp
                             new: one line each, including the usermod's file
  fwtool/
    build.py                 changed: the kinds standalone and standalone-probe
    standalone.py            new: writes platformio.ini, runs the build
    cli.py                   changed: --standalone on build, flash and test-board
  platformio_override.ini.in changed: the include path of the usermod's platform
tests/
  firmware/                  new tests, and a host program for settings.cpp and limit.cpp
  board/                     changed: the firmware under test is chosen by a variable
```

Nothing under `core/` changes.

## The tool

`build` gains `--standalone`, which combines with `--probe` and not with `--stock`.

| Command | Environment | Image in `build/firmware/out/` |
|---|---|---|
| `build --standalone` | `odrig_standalone` | `odrig-standalone.bin` |
| `build --standalone --probe` | `odrig_standalone_probe` | `odrig-standalone-probe.bin` |

`standalone.py` writes `platformio.ini` into `build/firmware/standalone/` from
`firmware/standalone/platformio.ini.in`, with the repository's path in place of `@REPO@`
and the path of WLED's checkout in place of `@WLED@`, and runs PlatformIO there with
`-d`. `src_dir` names `@REPO@/firmware/standalone/src`. The partition table is
`@WLED@/tools/WLED_ESP32_16MB_9MB_FS.csv`: the table of the WLED-based firmware by
construction. WLED's checkout is not patched and not otherwise used; `setup` has put it
there.

The environment `odrig_standalone`:

```ini
[env:odrig_standalone]
platform = <R2>
board = esp32-s3-devkitc-1
framework = arduino
board_build.arduino.memory_type = qio_opi
board_build.partitions = @WLED@/tools/WLED_ESP32_16MB_9MB_FS.csv
board_build.filesystem = littlefs
board_upload.flash_size = 16MB
board_build.f_flash = 80000000L
board_build.flash_mode = qio
lib_deps = <the three libraries of R2>
  odrig_core = symlink://@REPO@/core
build_flags = -D ARDUINO_USB_CDC_ON_BOOT=1 -D BOARD_HAS_PSRAM
  -I@REPO@/firmware/standalone/platform -I@REPO@/firmware/usermod -I@REPO@/core/include
```

`odrig_standalone_probe` extends it with `-D ODRIG_PROBE`. No other optimisation level
than the platform's is set.

`flash --standalone` takes `odrig-standalone.bin` as its image where `flash` takes
`odrig-firmware.bin`; everything else is `flash`. `--image` and `--expect` work as today,
and `--expect probe` reads the probe report of either firmware.

`test-board --standalone` and `test-air --standalone` set the variable
`ODRIG_BOARD_FIRMWARE=standalone` for the suite; see "The board suite". The suite over the
air skips its test of WLED's own pages then.

A test of `tests/firmware/` reads the pins of `platformio.ini.in` and those of WLED's
`platformio.ini` in the work folder and fails when they differ. Without a work folder it
is skipped, as the test of the patch files is.

## The platform header

`odrig_files.cpp`, `odrig_serial.cpp` and `odrig_http.cpp` include `odrig_platform.h` in
place of `wled.h`, and name the file system `ODRIG_FS` in place of `WLED_FS`. The header
is found on the include path, never beside the source files, so each build gets its own:

| Build | The header | What it gives |
|---|---|---|
| The usermod | `firmware/usermod/wled/odrig_platform.h` | `#include "wled.h"`, and `ODRIG_FS` as `WLED_FS`. The web server is WLED's `server`. |
| The standalone program | `firmware/standalone/platform/odrig_platform.h` | `Arduino.h`, `LittleFS.h`, `ESPAsyncWebServer.h`, `ODRIG_FS` as `LittleFS`, and `extern AsyncWebServer server;`. |

`platformio_override.ini.in` gains `-I@REPO@/firmware/usermod/wled`. The other files of
the usermod keep `#include "wled.h"`: they are WLED's side.

The compiled code of the WLED-based firmware does not change by this: the same
statements are compiled against the same headers. Task 2 shows it with the whole board
suite.

## The program (`main.cpp`)

`setup()`:

1. `Serial` and the port, as the usermod's `setup()` starts them (`OdrigSerial::begin`).
2. `LittleFS.begin(false)`. A failed mount is not repaired: the core is started all the
   same, finds no file, and reports the show as invalid.
3. The stored settings are read, see "The stored settings".
4. The core is started with `OdrigFiles::host()`, and the time it took is kept.
5. The legs are read from the core once, as `readLegs()` of the usermod does.
6. The outputs are made from the legs, see "The outputs".
7. The network is started, see "The network and HTTP".
8. The task that asks the core for refreshes is started on processor 0, with the stack,
   the priority and the name the usermod gives it.

`loop()` is the usermod's loop without what holds WLED back: it passes bytes of the port
to the core, and when the task has a refresh ready it copies the legs into the outputs,
applies the limiter, wakes the task, and sends as soon as every output can take data.

Every call to the core after its start is made with one lock held, as in the usermod. The
code of the lock, of `feedBytes`, `commandLine`, `readLegs` and the task is the usermod's,
written again in `main.cpp`: it is 120 lines, it names WLED nowhere, and sharing it would
put the usermod's start behind an interface for no other gain.

The program writes nothing to the port by itself: no start-up text of ours, and the
Arduino core's own log level is `none`.

## The stored settings (`settings.cpp`)

`settings.cpp` is C++11 without Arduino, so that it is tested on the computer. It gets
the bytes of `/cfg.json` and of `/wsec.json`, at most 16,384 bytes each, and gives:

```cpp
struct OdrigSettings {
  bool network;        // a usable name and password were found
  char name[33];
  char password[64];
  uint8_t channel;     // 1 to 13; 1 when the file names none or another value
  uint16_t limit_ma;   // hw.led.maxpwr of /cfg.json; 850 without it
};
```

It reads JSON with a small reader of its own that walks objects by member name and skips
every value it is not asked for; it builds no tree and takes no memory. It looks for
`ap.ssid`, `ap.chan` and `hw.led.maxpwr` in `/cfg.json` and for `ap.psk` in `/wsec.json`.

- `network` is true when the name has 1 to 32 bytes and the password 8 to 63, both
  strings without an escape other than `\"`, `\\` and `\/`. Otherwise no network is
  hosted.
- A file that is absent, longer than 16,384 bytes or not JSON gives the defaults: no
  network, a limit of 850.
- `hw.led.maxpwr` counts when it is a whole number from 0 to 65,535 written in digits.

`main.cpp` reads the two files with `LittleFS`, hands the bytes over, and frees them. It
never writes them, and nothing of the program opens a file outside `/odrig` for writing.

## The network and HTTP (`network.cpp`)

With `network` true: `WiFi.mode(WIFI_AP)`, `WiFi.softAPConfig(4.3.2.1, 4.3.2.1,
255.255.255.0)` and `WiFi.softAP(name, password, channel, 0)`, as R5. Then
`AsyncWebServer server(80)` is started and `OdrigHttp::begin(commandLine)` puts the one
route on it. The handler is the usermod's file, so the statuses and the handling of a body
are the same code.

A path other than `/odrig` is answered with 404 by the server's own handler for what was
not found. There is no page, no captive portal, no update over the network and no name
service. With `network` false the radio stays off.

## The outputs (`outputs.cpp`)

An output is an object of the LED library for one pin and one count of LEDs, behind a
small interface: `begin`, `canShow`, `pixels` and `show`.

| Legs | Method of the library | Feature |
|---|---|---|
| Sixteen | `NeoEsp32LcdX16Ws2812xMethod` | `NeoGrbFeature` |
| Four | `NeoEsp32Rmt0Ws2812xMethod` to `NeoEsp32Rmt3Ws2812xMethod` | `NeoGrbFeature` |

Which legs get RMT is what the probe report of the WLED-based firmware shows for the
target mapping, member `driver`; task 1 reads it and writes it down, and the standalone
firmware gives the legs in the same order to the same drivers. With fewer than twenty
legs the order is the same from the first leg on.

- A leg beyond the twentieth gets no output. A leg whose pin the library refuses, or the
  chip cannot use as an output, gets none either, and the others are made all the same.
  Pins 19 and 20 are refused before the library is asked: they carry USB.
- `fill` copies the three bytes of each LED from the leg's data into the output's pixel
  buffer in the order green, red, blue. The core has already applied the brightness.
- `show` sends every output. The loop calls it only when every output can take data.
- With an invalid show there are no legs and no output is made. Every pin of the target
  mapping is then left as the chip starts it.

## The limiter (`limit.cpp`)

`limit.cpp` is C++11 without Arduino. It works on the pixel buffers of the outputs after
`fill` and before `show`:

```cpp
struct OdrigLimitOutput { uint8_t *bytes; uint32_t leds; };
struct OdrigLimitResult { uint16_t limit_ma; uint16_t used_ma; bool dimmed; };
OdrigLimitResult odrig_limit(OdrigLimitOutput *outputs, uint32_t count, uint16_t maximum_ma);
```

With `maximum_ma` 0 it changes nothing and reports `limit_ma` 0, `used_ma` 0 and no
dimming. Otherwise it follows R6 and R7 exactly:

1. For each output that works, `used = sum * 55 / 765 + leds`.
2. `allowed` is `maximum_ma - 120`, or 1 when `maximum_ma` is 120 or less. `limit_ma` is
   `allowed`.
3. When `allowed` is above the number of all LEDs: when the total is above `allowed`, the
   level is `allowed * 255 / total + 1` and `used_ma` is `allowed`; otherwise nothing is
   dimmed and `used_ma` is the total.
4. When `allowed` is not above the number of all LEDs, the level is 1 and `used_ma` is
   the number of all LEDs.
5. A level below 255 dims every LED of every output as R7 says.

The order of the three bytes of an LED does not matter to any of this.

## The probe build (`probe.cpp`)

With `ODRIG_PROBE` the port holds a line `#probe` back from the core, as the usermod's
port does, and the program answers it with the report of Requirement 9. The members have
the meaning `docs/firmware.md` gives them. What only WLED has is left out: `realtime`,
`overwritten`, `wire_us`, `space_us` and `store`. The line `#store` is not answered and
reaches the core.

- `firmware` is `"standalone"`. The WLED-based probe build gains `"firmware":"wled"`, so
  that a test can tell which one answered.
- `crc` of an output is the CRC-32 of its LEDs as red, green and blue, taken from its
  pixel buffer after the limiter. While the limiter does not dim, that is the CRC-32 of
  the leg's bytes.
- `pulses` comes from `odrig_pulses`, the pulse counter that is moved out of
  `odrig_probe.cpp` unchanged: one output is counted at each send, each in its turn.
- `limited`, `limit_ma` and `used_ma` come from `odrig_limit`.
- `ap` is 1 while the access point is up.

A `#probe` that arrives between `fill` and `show` is answered after the `show`.

## Switching

Both firmwares are application images for the first application partition of the same
partition table, and `flash` writes that partition and the boot selection only (R11). The
storage partition is the same bytes before and after. So:

```
python3 firmware/fw.py build --standalone
python3 firmware/fw.py flash --standalone      # to the fallback
python3 firmware/fw.py flash                   # back to the WLED-based firmware
```

Each takes about 15 seconds on the board. Neither firmware needs the other's image to be
built on the day: both images are built ahead and kept in `build/firmware/out/`.

One difference is recorded in the documents: WLED may rewrite its own two settings files
when it saves settings, and it formats a file system it cannot mount (R4). The standalone
firmware does neither.

## The board suite

`tests/board/support.py` reads `ODRIG_BOARD_FIRMWARE`, `wled` when it is not set.

- With `standalone`, the kind `firmware` is the image `odrig-standalone.bin` and the kind
  `probe` is `odrig-standalone-probe.bin`. `running()` tells the two firmwares apart by
  the member `firmware` of the probe report, and for the plain builds by which image the
  suite last flashed, which it keeps in `build/firmware/out/on-the-board.json`.
- A test that depends on WLED carries `@support.needs_wled("<why>")`, which skips it in
  the standalone run. These are: WLED's handshake and WLED's access point in
  `test_probe.Port`; `test_an_invalid_mapping_leaves_wleds_own_outputs_and_keeps_them_dark`;
  `test_nothing_else_writes_to_the_outputs_over_30_seconds`; the store trial in
  `test_upload.Spike`; `test_measure`, whose members are WLED's; and the restore of stock
  WLED in `test_flash_restore`, which the WLED run already makes.
- Every other test runs in both.
- `leave_the_board()` flashes the WLED-based firmware whichever run it was, and installs
  the dim example show.

Three tests are new, in a file of their own, and run only in the standalone run:

- the switch: the show is read back from the board, the standalone firmware is flashed,
  then the WLED-based one, and the show and the two settings files read back are byte for
  byte what they were;
- the rates: the demo show and the dense 60 x 60 clip, compressed and uncompressed, on
  the target mapping, each for 20 seconds, written to
  `build/firmware/out/standalone-rates.json` with the start time;
- the limiter: with Hello world for the target at brightness 40, the probe report's
  `limit_ma` and `used_ma` equal those the WLED-based probe build reported for the same
  show, which the test reads from the file the WLED run's `test_measure` wrote.

## Tests without the board

In `tests/firmware/`, found by discovery:

- **The host program.** `settings.cpp` and `limit.cpp` are compiled for the computer with
  the compiler the core's suite uses, with a small `main` that reads a case from standard
  input and prints the result. The tests drive it.
- **Settings.** The files seed 08's tests make; a file without `ap`; a name of 0, 1, 32
  and 33 bytes; a password of 7, 8, 63 and 64; escapes; a file of 16,385 bytes; text that
  is not JSON; `maxpwr` absent, 0, 850, 65,535, 65,536, negative, with a fraction, a
  string.
- **The limiter.** A reference in Python written from R6 and R7, and the program compared
  with it on: no light; one LED white; 60 LEDs white at each maximum of 0, 100, 120, 121,
  850 and 65,535; 3,600 LEDs at 850, where every lit channel becomes 1 or 0 as R7 says;
  and 200 pictures from a seeded generator on one to twenty outputs.
- **The sources.** `firmware/standalone/` names `wled.h` nowhere and includes no file of
  WLED; the three shared files include `odrig_platform.h` and not `wled.h`; no file of
  the standalone program opens a file for writing; `main.cpp` holds no network name and
  no password.
- **The tool.** The kinds, the image names, the refusal of `--standalone --stock`, the
  text of `platformio.ini` for a given repository path, and the pins against WLED's.
- **The documents.** The tests of `tests/firmware/test_docs.py` for what Requirement 11
  asks.

## Documents

- `docs/firmware.md`: a section "The two firmwares" near the top, with the table of what
  each offers; the commands `build --standalone`, `flash --standalone` and
  `test-board --standalone` in "Commands"; "Switching"; the standalone probe report; the
  measurements side by side in "Measurements on the board"; the findings of task 1 in
  "Verified on the board"; an owner's check.
- `docs/decisions.md`: "Firmware" names both, and a line in the change log.
- `docs/wifi.md`: the network is the same with either firmware, and there is none
  without stored settings on the standalone one.
- `AGENTS.md`: seed 12 leaves "What is coming"; `agent/README.md` names the second
  firmware among the parts.

The table of what each offers:

| | WLED-based | Standalone |
|---|---|---|
| The show, the commands, the twenty outputs, the limit | yes | yes |
| WLED's web pages and settings | yes | no |
| A firmware update over the network | yes | no |
| A network when no settings are stored | WLED's default name and password | none |
| Writes its settings files, formats a broken file system | yes | never |
| Code we do not control | WLED and one patch | the LED library and the web server |

## Risks

- **The parallel driver outside WLED (S2, S5).** WLED sets the driver up through its own
  bus layer, and its memory estimate was patched for sixteen lanes. A bare program may
  need the same care. Task 1 is there to find this before anything else is written.
- **Two copies of the host loop.** `main.cpp` repeats the usermod's lock, task and loop.
  A change to one must be made to the other. The source test compares nothing here; the
  board suite running against both is what catches a difference.
- **The limiter is arithmetic copied from WLED.** A later WLED could change its own. The
  board test that compares `used_ma` and `limit_ma` of the two firmwares fails then.
- **The fallback goes stale.** It is used only when something is wrong. `fw.py test`
  builds nothing, so only a board run shows that it still works. The documents say to run
  `test-board --standalone` after any change to the core's host interface.

## The microSD card

The card's code is `firmware/usermod/odrig_drive.cpp` built with `ODRIG_DRIVE_SD_SPI` and
the pins of `odrig_sd_config.h`: Arduino's `SD` library over the chip's second SPI unit,
a FreeRTOS task, and the core's drive functions, with nothing of WLED but the log's
queue. The standalone firmware compiles it through a file of one line, as the files, the
port and the HTTP transport are, with the four pin flags and the flag of the card in its
`platformio.ini.in`; the log's queue, `odrig_log.cpp`, comes with it, and `main.cpp`
calls `OdrigDrive::begin()` and wraps the host with `OdrigDrive::withDrive()` as the
usermod does. Whether the `SD` library of Arduino-ESP32 2.0.18, on WLED's platform, takes
the card as the newer software's does is settled in task 6, on the board; if it does not,
the standalone firmware moves to the newer software with the WLED-based one.
