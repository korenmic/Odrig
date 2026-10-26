# Design: a microSD card as the external storage

## Overview

The firmware's code for external animations, `firmware/usermod/odrig_drive.cpp`, has two
backends behind one build flag. Without the flag it is the stick's: the USB host on the
chip's own socket, Espressif's driver of flash drives, the watcher that logs what comes
and goes. With `ODRIG_DRIVE_SD_SPI` it is the card's: Arduino's `SD` library over the
chip's SPI unit, on four pins the build names, with a small task that mounts a card when
one is there and notices when it goes. Both backends give the core the same two things,
a drive number and a list of names, and read the files through the same host functions,
so the core, the emulator and the app see no difference. The tool builds the card's
backend as a variant, `build --microsd`, on the newer software, in the folder of
`build --trial`.

Most of this design is built, in Codex's commits `d5bcef6`, `551a52b`, `5b4b4e9`,
`b1fbec5`, `4217f91` and `d7f0120` on the branch `codex/microsd-storage`. The design
describes the code as it is, and marks what is still to do: the card's free and total
space after the merge with `master`, the documents in the house style, the board session,
and the two questions of the owner.

## What this design relies on

From the sources at `533ceb8`, and `master` at `547c01b`, on 2026-10-24:

- The core's host interface, `core/include/odrig_core.h`: `drive` returns the number of
  the drive that is plugged in now, other than 0 and new at every plugging in, or 0 while
  none is, and is called at refreshes; `drive_name` gives the name at a place of the
  drive's list; `open`, `read`, `close` and `read_at` take a name `drive/<place>` to the
  file at that place; and, since seed 29 on `master`, `drive_space` optionally gives the
  drive's free and total bytes, 1 or -1, writing nothing.
- `odrig_drive.cpp` as seed 20, 21 and 23 built it: the list of names in 64 KB of the
  external memory, `MOST_FILES` 256 and `NAME_ROOM` 256; two files open at most, the one
  that plays and the one that is checked, each with a buffer of `READ_BUFFER` 4,096
  bytes of the internal memory; one mutex, `guard`, held by the core's calls and by the
  task that publishes a list or drops a drive; the number `plugged` that grows at each
  plugging in and is never 0; `listFolder()`, which reads the folder `odrig` of the
  mount, filters and sorts the names, and answers `NO_FOLDER` or `NOT_LISTED` when it
  cannot; and `setSummary()`, the text for WLED's information.
- Arduino-ESP32 3.3.12's `SD` library: `SD.begin(cs, bus, hz, mountpoint, maxFiles,
  formatIfEmpty)` mounts a card over a `SPIClass` with the chip's FatFs at a mount point;
  `SD.readRAW(buffer, sector)` reads one 512-byte sector of the card itself; `SD.end()`
  unmounts; `SD.totalBytes()` and `SD.usedBytes()` read the volume's size and its free
  clusters, writing nothing. `SPIClass bus(FSPI)` is the chip's second SPI unit, and
  `bus.begin(sck, miso, mosi, cs)` puts it on four pins of one's choosing; `SD.begin`
  calls `SPI.begin()` without pins when it is given no bus.
- The tool: `fwtool/build.py` builds a kind, `KINDS`, with the Python and the PlatformIO
  folders of the newer software when the kind is in `ON_NEWER`; `fwtool/env.py` gives
  the newer software its folders with `child(newer=True)`; `fwtool/toolchain.py` makes
  its Python environment, `newer_environment()`. The environments are in
  `firmware/platformio_override.ini.in`; `odrig_trial` is `odrig` on the newer platform
  with the trial's flags and `firmware/newer/odrig_newer.h`, and the trial's patch,
  `firmware/patches/020-newer-software.patch`, holds every change by
  `ESP_IDF_VERSION_MAJOR >= 5`.
- On `master`, seed 29 added `driveSpace()` to the stick's backend, from
  `msc_host_vfs_space()` of the USB driver, and set `made.drive_space` in `withDrive()`.

## The reader and the pins

The reader is the SparkFun Shifting microSD board: a microSD socket with level shifters,
fed with 3.3 V. The owner wired it on 2026-10-22 and reported the wiring complete; no
agent has measured it.

| The reader | The board | In the build |
|---|---|---|
| SCK | GPIO39 | `ODRIG_SD_SCK=39` |
| DO (MISO) | GPIO40 | `ODRIG_SD_MISO=40` |
| DI (MOSI) | GPIO41 | `ODRIG_SD_MOSI=41` |
| CS | GPIO42 | `ODRIG_SD_CS=42` |
| VCC | 3V3 | |
| GND | GND | |
| CD | not wired | |

GPIO39 to GPIO42 are the exposed pins left after the twenty LED outputs, pins 1 to 18, 21
and 47, the two USB connections, 19 and 20 for the chip's own unit and 43 and 44 for the
UART, the module's memory pins and the boot pins. `firmware/usermod/odrig_sd_config.h`
holds the defaults, every pin -1, the clock `ODRIG_SD_FREQUENCY` 4,000,000 and the mount
point `ODRIG_SD_MOUNT_PATH` `/sd`, and three checks: `available(pin)` is true for 39 to
42 only; `pinsValid()` wants four available pins, all different; `valid()` wants that and
a clock from 400,000 to 20,000,000. The environment `odrig_microsd` of
`platformio_override.ini.in` extends `odrig_trial` and adds `-D ODRIG_DRIVE_SD_SPI` and the
four pins; no other environment has the flag, so the stick's build has none of the card's
code, and a build with the flag but without the pins starts no reader.

The clock stays 4 MHz. On 2026-10-22, 1 MHz and 400 kHz dropped out as 4 MHz did, and on
2026-10-23 4 MHz ran clean for fifteen minutes; a slower clock only makes the reads
slower.

## The card

A microSD card of 32 GB or less as it comes, FAT32 or FAT16, or any card formatted FAT32
on a computer. The firmware mounts it at `/sd` with `SD.begin(ODRIG_SD_CS, cardBus,
ODRIG_SD_FREQUENCY, "/sd", 3, false)`: three files at most, and never formatted. The
folder is `/sd/odrig`; its files are listed by `listFolder()` as for the stick: names
ending in `.odrg` in any case, not beginning with a dot, sorted, the first 256, folders
and other files passed over. Names are kept to `a`-`z`, `A`-`Z`, digits, `-`, `_` and
`.`; a name with other letters may come out as `?` and such a file is left out.

A card holds what the board's storage cannot: the owner's card has 122 animations,
16,475,328 bytes, where the storage holds 13.5 MB.

## The task: mounting, watching, dropping

`OdrigDrive::begin()` in the card's build first checks `OdrigSdConfig::valid()`; when it
is false it logs `SD pins or SPI frequency not configured safely; reader disabled` and
returns, and WLED's information says `SD not configured`. Otherwise it makes the guard and
the buffers, as the stick's backend does, and starts the task `odrig-drive` on processor
1, the one of WLED's loop, at priority 1 with a stack of 6,144 bytes.

The task's first act is `cardBus.begin(ODRIG_SD_SCK, ODRIG_SD_MISO, ODRIG_SD_MOSI,
ODRIG_SD_CS)`. When that fails it logs `SPI did not start on the configured pins; reader
disabled`, says `no SD reader` and ends; it never lets `SD.begin` fall back to the chip's
default SPI pins. Then it loops, one step a second, `CARD_POLL_MS`:

- **No card mounted**: `mountCard()`. `SD.begin` fails for no card or for a file system
  FatFs does not read, which the firmware cannot tell apart without the card-detect line:
  the state becomes `NOT_READ`, `not readable`, and the line `card not mounted; no card or
  unreadable file system` is written once for the spell, at the first failure. When it mounts, `listFolder()` reads `/sd/odrig` and logs `card opened: <n>
  animation files in odrig`, `the card has no folder odrig` or `card folder odrig could
  not be read`; then, with the guard held, the count becomes the list's length, `plugged`
  grows past 0, the number becomes `plugged`, the state `MOUNTED`, and the summary the
  count. The core sees the new number at its next refresh, reads the names, and adds
  each sound file to the playlist as it finishes reading it.
- **A card mounted**: `sdStep()` takes the guard and reads sector 0 with `SD.readRAW`.
  When that fails, or a read of a file failed since the last step, it drops the card
  under the guard: the number becomes 0, the count 0, the two files are closed,
  `SD.end()` unmounts, the state becomes `NO_DRIVE`, `none`; then, with the guard given
  back, it logs `card unavailable; files closed, waiting for a card`. The next step, a
  second later, tries to mount again, and with no card the state is `NOT_READ` from then
  on; so `none` shows for a second only.

A read of a file that fails is remembered by `readFailed()`, which sets `cardFailed`
under the guard: `openFile` and `readPart` call it when opening fails for any reason but
`ENOENT`, `readSome` and `readPart` when `fread` reports an error, and `readPart` when
`fseek` fails. The core's calls themselves answer -1 as before; the unmounting is the
task's alone, so no file is closed under a call that reads it. The card's files are
opened with the same two handles as the stick's, `played` and `second`, with their
buffers.

Timing: a card put in is mounted within a second plus the time `SD.begin` takes; a card
pulled out is noticed within a second by the sector read, or at once by a read of a file
that fails, and the core drops its animations at its next refresh. A card that goes
while a file is read can hold that read until the chip's SD driver gives up, which may
pause the LEDs for a moment; the board session measures it.

## Free and total space

Not built yet; it is done in the commit that merges `master` into the seed's branch,
since seed 29's `drive_space` comes with `master`. In the card's build `driveSpace()`
takes the guard, answers -1 unless the drive asked for is the card's current number and
the card is mounted, else reads `SD.totalBytes()` and `SD.usedBytes()`; a total of 0 is
-1, and otherwise free is total minus used and the answer is 1. The stick's `driveSpace()`
stays as `master` has it, behind `#ifndef ODRIG_DRIVE_SD_SPI`. `withDrive()` sets
`made.drive_space` in both builds. The stand-in card of the test gets `totalBytes()` and
`usedBytes()`, and the test checks the numbers while mounted, -1 for another number, for
an unmounted card and for a total of 0.

## The sockets

In the card's build nothing of the USB host is compiled: no look for a computer, no
`COMPUTER_WAIT_MS`, no watcher. The chip's own socket is the serial port that
`odrig_serial.cpp` has always made of it, and a computer plugged into it at any time gets
commands and flashing; `computer_wait_s` in WLED's settings is kept for the stick's build
and has no effect here. The socket marked COM is as before: commands, flashing and the
log.

## The log and WLED's information

The card's lines are of the kind `sd`, by `say()`, which gives `OdrigLog::add` the kind
`sd` in the card's build and `usb` in the stick's. They are the seven lines named above.
The player's lines are unchanged: `drive file <name> left out: <reason>` for a file of the
card, and the reason the show became invalid, which the card never causes.

WLED's information keeps the entry `odrig drive`, filled by `OdrigDrive::summary()`:
`SD not configured`, `no SD reader`, `looking for SD`, `not readable` while no card is
mounted, `none` for the second after a card went, or `<n> files` for a mounted card. The
text `computer` of the stick's build does not occur.

## The tool

```
python3 firmware/fw.py build --microsd
python3 firmware/fw.py flash --image build/firmware/out/odrig-microsd.bin --wait 60
```

`build --microsd` is the kind `microsd` of `fwtool/build.py`, environment `odrig_microsd`,
image `odrig-microsd.bin`, in `ON_NEWER`: `toolchain.newer_environment()` first, then
`wled.restore_and_patch()` with every patch and `wled.write_override()`, then the newer
software's Python running PlatformIO in WLED's folder with `env.child(newer=True)`, and
`keep()` copies the image to `build/firmware/out/` with its SHA-256 beside it when it
fits the application partition. `cli.py` makes `--microsd` the kind before `--standalone`
and `--trial`, and `parsed()` refuses it with `--stock`, `--probe`, `--trial` or
`--standalone`. The images built: 1,765,808 bytes on 2026-10-22, SHA-256
`fd089753d86c92d9cbfbb2e4823d49428e4b037213b656736636b9dd9a1950a5`, which the board runs.
The merged firmware, with seeds 29 and 30, is another image; its hash is recorded when it
is built and when it is flashed.

`flash --image` writes the card's build through either socket; the board session uses the
socket marked COM, so that the chip's own socket's enumeration does not get in the way.
`flash` without `--image` writes the stick's build, `odrig-firmware.bin`: the card's
build is chosen on purpose, every time, until the owner answers question 8.

## Tests

In `tests/firmware/`, all built:

- `test_microsd_build.py`: `build --microsd` runs the newer software's PlatformIO on
  `odrig_microsd` with the newer folders first in `PATH` and `PLATFORMIO_CORE_DIR`, keeps
  `odrig-microsd.bin`, and reports a failed build with its environment; the refused
  combinations; the kind beside the firmware's, which it never replaces; the environment
  extends `odrig_trial` and alone has the flag and the pins; the pins are 39 to 42 and
  none of them is a pin of `mapping/legs-20.json` or of USB, 19, 20, 43 and 44.
- `test_usermod_sd.py`: `odrig_drive.cpp` compiled on the Mac with `ODRIG_DRIVE_SD_SPI`
  against a stand-in `SD.h`, `SPI.h` and task scheduler, with the sanitizers on: pins and
  clocks that are refused start no task and touch no pin; a failed `cardBus.begin` never
  lets `SD.begin` run on default pins; an absent or unmountable card keeps the installed
  files and is retried; names are filtered, sorted and cannot leave the folder; the first
  256 only; a missing or empty folder; the playing and the checking file read apart and
  the installed files beside them; a sector read that fails drops the card and a card put
  back gets a new number; a read error unmounts only after both files are closed, and
  recovers.

To add, in the merge: in `test_usermod_sd.py`, the free and total space of the stand-in
card, as "Free and total space" says.

The suites that run before every commit are those of `tasks.md`. The firmware's suite is
run with the work folder's Python, `build/firmware/venv/bin/python`, which has
littlefs-python; `python3 firmware/fw.py test` does that.

## The documents

- `docs/microsd.md`: the card's page, rewritten in the house style from Codex's page and
  the two records of `docs/microsd-preflight/`: what the card is for; preparing a card;
  the reader and its wiring, as the owner reported it; the build and the flash; plugging
  in and pulling out; the log's lines and WLED's information; what the board sessions of
  2026-10-22 and 2026-10-23 gave, in full; what is open. Then `docs/microsd-preflight/`
  goes, and every link to it.
- `docs/firmware.md`: "A USB drive" becomes the external storage, the stick in the
  stick's build and the card in the card's, with a link to `docs/microsd.md`; the sections
  on the newer software and the trial get one sentence that the card's build uses the
  same software; "The log" gets the lines of the kind `sd`; "Verified on the board" gets
  the two sessions in short, with the hashes; the paragraph on `build --microsd` is kept
  current.
- `docs/firmware-additions.md`: the card's line, in the house style: what the firmware
  does, seeds 20 and 38, `odrig_drive.cpp`, `odrig_sd_config.h`, `build --microsd`,
  "Written again", and for seed 12 "No: the fallback gets the card too, by the owner's
  rule". "Coming" loses seed 22.
- `docs/firmware-prerequisites.md`: line 9, the external storage is the card, with what
  was seen and what is open; line 16, read without soldering: the reader is wired without
  soldering and reads the card; "Seeds not finished" gets seed 38 and loses seed 22's
  mention.
- `docs/show.md`, "Animations from a USB drive": one sentence that on the board the drive
  is a USB stick or a microSD card, as `docs/firmware.md` says.
- `AGENTS.md`: the seed's line in "What is coming" while it is open, and
  `docs/microsd.md` in the firmware row; both are there.
- `docs/decisions.md`: a line in the change log when the seed is completed, saying what
  the board runs.

## The board session

In a session with the owner, under "If you have a board": one program at a time, a
brightness of 40 or less, nothing erased, the firmware built only by the tool.

1. `build --microsd` on the merged branch; the hash recorded. `flash --image
   build/firmware/out/odrig-microsd.bin --wait 60` through the socket marked COM; the
   installed show and the settings kept; `status` answers.
2. With the owner's card in the reader: `status` and `list` over the socket marked COM
   every few seconds until the core has read the card, which takes minutes for 16 MB and
   is not a fault: `list` answers `busy` meanwhile. Then the card's animations, 60001 up,
   after the installed ones, over the socket marked COM, over the chip's own socket, and
   over Wi-Fi with `python -m odrigctl --http 4.3.2.1 list` from a device on the board's
   network. `play` of the largest file, `status` sampled for half a minute: 20 to 50.
3. The card pulled out while one of its animations plays: `status` and the log sampled
   every second; the time until `status` names another animation and `list` has no card
   entry recorded, and any pause of the LEDs. The card put back: the time until the
   card's animations return, and their ids.
4. The dropouts: with the cable arrangement the owner names for question 7, `status` and
   `list` sampled for fifteen minutes with the log kept, as on 2026-10-23. A list that
   shrinks is recorded with its lines before anything is changed.
5. The owner looks at the LEDs: the card's animations, and the board running with no
   computer, powered as at the event; the app's list on a phone.
6. The board left playing its show at a brightness of 40 or less; what is on it recorded.

What was seen goes into `docs/microsd.md` and `docs/firmware.md`, "Verified on the board".

## What does not change

- The core, the emulator, `odrigctl` and the app: the card is a drive to them. The
  emulator's `--drive DIR` stands in for the card as for the stick.
- The commands and the replies: nothing added, no member gained.
- The stick's build, `build`, and the hub's trial, `build --trial`, with
  `firmware/newer/`, the patch `020-newer-software.patch` and `firmware/usb_host_msc/`:
  the card's build is built on them. Their removal or move is question 8 of the owner.
- The twenty LED outputs, the Wi-Fi, the storage, the bigger layout and `big-storage`.

## What needs the owner

- Question 7: which socket powers the board at the event, and whether a computer is on
  it; the one-cable check of the dropouts follows the answer.
- Question 8: whether the card's build becomes the firmware that `build` makes.
- The session: the flash, the card put in and pulled out, the look at the LEDs, the board
  without a computer, and the phone's list over Wi-Fi.
- Any change of the wiring, the power or the reader.
