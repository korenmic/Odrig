# What the firmware adds to WLED

The firmware on the board is WLED 16.0.1 with what this project adds to it. This page lists
every addition, one line each, so that every firmware of the project gets all of them.

**The owner's rule, 2026-10-16.** Every firmware of the project gets everything on this
list: the WLED-based one, the one without WLED of seed 12, which is the fallback for the
event, and any other made later. The fallback is not a firmware that only starts and plays:
whatever is added to the WLED-based firmware is added to it too.

- A seed that adds to what the firmware does adds its line here in the same commit, and
  fills in the column "Seed 12".
- A firmware other than the WLED-based one is done only when it has every line, or when
  the owner has said which line it may go without.

How a line reaches another firmware, the column "Reaches another firmware":

- **The core**: the line is done by the shared core, `core/`, which every firmware compiles
  unchanged. It comes with the core.
- **Shared file**: the line is done by a file of `firmware/usermod/` that names nothing of
  WLED, which the standalone firmware compiles as well (seed 12, task 2): `odrig_files.cpp`,
  `odrig_serial.cpp` and `odrig_http.cpp`.
- **Written again**: the line is done by a file of the usermod that uses WLED, or by WLED
  for us. Another firmware does it with code of its own.

The column "Seed 12" says how far the fallback has it: *Built* when a task of seed 12 built
it, *In its spec* when seed 12's spec has it and its task is still open, and *No* when the
line came after seed 12's spec was written. Before seed 12's open tasks go on, its spec
takes every line marked *No*.

## The list

| # | What the firmware does | Seeds | Where it is done today | Reaches another firmware | Seed 12 |
|---:|---|---|---|---|---|
| 1 | Plays the `.odrg` files of the installed show: decoding, the mapping onto the legs, the timing, the brightness, the show's cycles. | 02, 04 | `core/` | The core | In its spec |
| 2 | Plays a playlist of every installed animation when the show names nothing else, each for a turn of at least 30 seconds; `play all`. | 16 | `core/` | The core | In its spec |
| 3 | Plays at once at power-on: the start checks the headers only, and the bodies are checked while the show plays. | 14 | `core/` | The core | In its spec |
| 4 | Answers the commands of [commands.md](commands.md), with the same replies on every route: `space`, `list`, `remove` and `upload` among them. | 02, 07 | `core/` | The core | In its spec |
| 5 | A broken file never stops the show, and a power cut never leaves a half-changed show. | 02, 07, 14, 20 | `core/` | The core | In its spec |
| 6 | Starts the core on the files of `/odrig`, gives it a file in pieces of at most 512 bytes, its memory from the internal memory first, and a 64-bit clock of milliseconds. | 04 | `odrig_usermod.cpp` | Written again | In its spec |
| 7 | Storage: the seven storage functions of [core.md](core.md) on the file system, every name checked, a file written only in `/odrig`, the free space counted rather than asked of the file system. | 04, 07 | `odrig_files.cpp` | Shared file | Built |
| 8 | Paces storage: after storage calls, no command line for the longer of 20 ms and twice the time they took. | 07 | `odrig_files.cpp`, `odrig_serial.cpp` | Shared file | Built |
| 9 | Takes commands on the chip's own USB port, with a queue of 4,096 bytes, and writes nothing else there. | 04 | `odrig_serial.cpp` | Shared file | In its spec |
| 10 | Takes commands over HTTP on the board's Wi-Fi, `POST /odrig`, with 405, 404 and 503 as [firmware.md](firmware.md) has them. | 04, 07 | `odrig_http.cpp` | Shared file | In its spec |
| 11 | Takes commands on the socket marked COM as well, the serial chip's port, at 115,200 bits a second, and keeps the line of each socket apart. | 09, 21 | `odrig_uart.cpp` | Written again | No |
| 12 | Drives twenty outputs, one for each leg of `mapping.json`, WS2812B in the order green, red, blue: four on RMT and sixteen on the parallel driver. | 04, 05 | `odrig_leds.cpp`; WLED with `firmware/patches/010-sixteen-parallel-outputs.patch` | Written again | Built |
| 13 | Works out a refresh on the chip's other processor core while the one before it is sent, with one lock for every call to the core. | 04, 05 | `odrig_usermod.cpp`, `odrig_leds.cpp` | Written again | In its spec |
| 14 | Limits the LED current, counted as WLED counts it, to the value of `firmware/limit.json`; 0 is no limit. | 15 | WLED's limiter; `set-limit` | Written again | Built |
| 15 | Opens the board's own Wi-Fi network at 4.3.2.1, with the name and the password of `firmware/wifi.json`. | 08 | WLED's Wi-Fi; `set-wifi` | Written again | In its spec |
| 16 | Answers a phone that joins the network as a captive portal does, also while the show plays. | 04 | `odrig_usermod.cpp`, which keeps WLED's portal answering | Written again | No: its design has no captive portal |
| 17 | Gives the chip's own USB port to a computer when one is plugged in as the board starts, and to a USB stick otherwise; the wait, 5 seconds, is a setting. | 21 | `odrig_drive.cpp` | Written again | No |
| 18 | Plays the animations of a USB stick after the installed ones: FAT32 or FAT16, the folder `odrig`, at most 256 files, never written, taken up and dropped while the board runs. | 20 | `odrig_drive.cpp`, `firmware/usb_host_msc/` | Written again | No |
| 19 | Writes a log on the socket marked COM: a `#log` line for every event of the chip's own USB port and for every line the player logs. | 23 | `odrig_log.cpp`, `odrig_uart.cpp`, `odrig_drive.cpp` | Written again | No |
| 20 | Runs on the bigger layout of the flash, one firmware slot and 13,500,416 bytes of storage, and refuses an update over Wi-Fi there with the reason. | 24 | `firmware/fwtool/partitions.py`, `odrig_update.cpp` | Written again, built for both layouts | No: its spec knows WLED's layout only |
| 21 | Tells a person what it is doing without a command: the show's state, the outputs, the start's time, the stick, and whether an update over Wi-Fi is taken. | 04, 20, 23, 24 | WLED's information page, filled by `odrig_usermod.cpp` | Written again | No: it has no page; how it tells these is settled with the owner when seed 12 goes on |
| 22 | Has a probe build, which measures the outputs and the rate on the board. | 04 | `odrig_probe.cpp`, `build --probe` | Written again | In its spec |
| 23 | Is built, flashed, rolled back and set up by one tool: `build`, `flash`, `restore-stock`, `big-storage`, `install-show`, `set-wifi`, `set-limit`, `read-limit`, `install-firmware`, `read-show` and the board's suites. | 04, 08, 15, 24 | `firmware/fw.py`, `firmware/fwtool/` | Written again: each command takes the other firmware too | In part: `build`, `flash` and the board's suite are in its spec |
| 24 | Saves a complete twenty-pin permutation atomically and displays a packaged white diagonal through the shared core; the same commands reach it over HTTP and serial. | 30 | `core/src/mapping_control.cpp`, `odrig_routing.h`, `odrig_usermod.cpp` | Written again: fixed physical outputs resolve the currently assigned logical snake | Output adapter supports pin lookup; full standalone player remains pending seed 12 |
| 25 | Persists playlist inclusion, removes installed animations atomically in batches, and reports internal plus nullable external capacity through every command route. | 29 | `core/`; read-only FAT capacity in `odrig_drive.cpp` and `firmware/usb_host_msc/` | The core for semantics; a host callback supplies external capacity | No: the full player and external drive adapter remain pending |
| 26 | Has an experimental SPI microSD build in place of the USB-storage transport, preserving the external-animation interface and native USB serial; its profile uses SCK39, MISO40, MOSI41 and CS42. All 122 card files and representative playback are verified in the two-USB bench setup; autonomous-power operation remains open. | Owner | `odrig_drive.cpp`, `odrig_sd_config.h`, `build --microsd`; see [microSD preparation](microsd.md) | Written again | No |

## Coming

- **Seed 22, a USB stick through a hub.** When it is done, the firmware reads a stick
  through any USB hub, on newer USB software of Espressif. Its line comes here then, and
  the fallback is built on the same USB software.

## Not carried

These exist only because WLED is there, and another firmware has nothing to do for them:

- WLED is held in its live mode, so that its effects, presets and playlists never reach the
  LEDs.
- WLED's own serial protocols are switched off.
- The mapping's outputs are put back when WLED's LED settings are saved.
- WLED's audio usermod is left out of the build.
- WLED's pages, its JSON interface and its own update over Wi-Fi.

## Live mapping controls

The shared core supplies mapping reads, atomic twenty-pin assignment saves and the
packaged diagonal diagnostic. WLED's adapter refreshes cached RGB pointers by fixed
physical pin under its core lock; the standalone output adapter uses the same pin
lookup contract. The complete standalone player is still pending seed 12. No new
firmware has been flashed or checked on real LEDs for these controls yet.

## Shared playlist and capacity support

The shared core owns persisted inclusion and batch deletion on every route. The drive
adapter adds only a read-only FAT capacity query, using 64-bit byte arithmetic; all
space JSON is produced by the core. The tracked MSC VFS copy exposes this capacity
helper; its mount/unmount and licence remain unchanged. The standalone trial still
has no external drive adapter and does not claim complete player functionality.
