# The microSD card

The installation's external storage of animations is a microSD card in a small reader
wired to four pins of the board. The firmware reads the `.odrg` and `.odrgx` files of the card's
folder `odrig` and plays them after the installed ones, with ids from 60001 up, as
[show.md](show.md#animations-from-a-usb-drive) describes for a drive. The board changes
files of that folder only, and only as its core asks. The core, the emulator and the app
see a drive, whether the firmware fills it from a card or from a USB stick: the
emulator's option `--drive DIR` stands in for the card.

This page covers [what the card is for](#what-the-card-is-for),
[preparing a card](#preparing-a-card), [the reader and its wiring](#the-reader-and-its-wiring),
[the build and the flash](#the-build-and-the-flash),
[plugging in and pulling out](#plugging-in-and-pulling-out),
[the log and WLED's information](#the-log-and-wleds-information), what
[the board sessions](#the-board-sessions) gave, and [what is open](#what-is-open).

## What the card is for

The board's own storage holds 13.5 MB, and the owner's animations do not fit there: the
owner's card holds 122 animations, 16,475,328 bytes. A USB stick on the chip's own socket
was the first plan and never worked: the socket gives a plugged device no power, and
through a hub with power of its own the board still saw no stick. On 2026-10-21 the owner
asked for a microSD card instead, with the same folder `odrig` and the same behaviour,
and on 2026-10-24 closed the stick's path. The firmware for the card was built by Codex
on 2026-10-21 to 2026-10-23, and seed 38 gives it its place in the project.

The board keeps one or two small animations in its own storage, as a fallback when the
card is missing, and plays the rest from the card.

## Preparing a card

- **The file system.** FAT32 or FAT16: a card of 32 GB or less as it comes from the shop,
  or any card formatted FAT32 on a computer. A card above 32 GB comes as exFAT, which the
  firmware does not promise to read: format it FAT32 on a computer first.
- **The folder.** A folder `odrig` at the top of the card holds the `.odrg` and `.odrgx`
  files, made for the board's canvas as the installed ones are, in the folder itself and
  in its sub-folders, to three levels down. Names ending in `.odrg` or `.odrgx`, in any
  case, and not beginning with a dot are taken; other files are passed over. The files
  are listed depth first: a folder's files in the order of their names, then each of its
  sub-folders in the order of their names, the same way. A card with a catalog has every
  file of its index, which the PC tool's `import` writes for a card of any size. Of a
  card without one at most 256 files and 32 sub-folders are taken, the first in that
  order; a sub-folder counts when its first file is taken, with the folders above it that
  were not counted yet, and the board's listing, which a rebuild reads too, stops at the
  same limits. What is beyond the limits is passed over, as is a sub-folder deeper than
  three levels, one whose name
  begins with a dot or is not sound, and `System Volume Information`. The log line of
  the listing counts what was passed over. Each file is known by its path from `odrig`,
  `night/comet.odrg` for one, and [catalog.md](catalog.md) has the rule of the names.
- **The clocks.** The folder `clocks` holds the clocks that play between the animations,
  and its sub-folder `message` the message after each, as [show.md](show.md#clocks-between-the-animations)
  says; `collection/card/clocks/` holds them, 113 files. A card with them and the
  installation's other files holds more than 256 files: it needs its catalog, or, without
  one, only the clocks and the files to play, at most 256 in all.
- **The names.** Keep names to the letters `a`-`z` and `A`-`Z`, digits, `-`, `_` and `.`.
  Another letter, a Hebrew one for instance, may come out as `?`; such a file cannot be
  opened by its name and is left out, with its line in the log.
- **Never formatted.** The firmware mounts the card without the option to format it,
  and makes and removes no folder. It changes only files of the folder `odrig`, by the
  names its core gives them, and only while the card has that folder and no read of the
  card has failed: a card without the folder is not written, so make the folder on a
  computer. Nothing is installed from the card into the board's storage.

### The catalog, made on a computer

`python3 -m odrig.catalog MOUNT COMMAND` keeps the catalog of the card's folder `odrig`,
the files [catalog.md](catalog.md) describes, while the card is in a computer: MOUNT is
where the card is mounted, as `/Volumes/CARD` on macOS or `E:\` on Windows, and with
`--folder` it is the folder `odrig` itself. It needs Python 3.10 or later and the
repository, and is run from the repository's top:

```
python3 -m odrig.catalog /Volumes/CARD import
refused: clip.odrg: size-mismatch
imported: 2 animations, generation 1
python3 -m odrig.catalog /Volumes/CARD status
catalog: ok, generation 1, 2 entries; 3 animation files, 1 without an entry
```

| Command | What it does |
|---|---|
| `status` | Says what the catalog is, `none`, `ok` with its generation and its entries, `damaged` or `incompatible` with what, and how many animation files the folder holds and how many of them have no entry. |
| `import` | Checks every animation file of the folder and its sub-folders, depth first as the board lists them and without a limit of files or folders, and writes the catalog and its index anew, keeping the order its files were moved into: `refused: NAME: REASON` for each file the check refuses, then `imported: N animations, generation G`. |
| `add FILE...` | Puts each file into the folder under the last part of its path, in place of a file of that name, checked and with its entry in the same change: `added: NAME, BYTES bytes`, `replaced: NAME, BYTES bytes` or `refused: NAME: REASON`. |
| `remove NAME...` | Takes each animation out of the folder with its entry: `removed: NAME` or `refused: NAME: file-missing`. |
| `check` | Compares each file's size and CRC-32 with its entry: `differs: NAME: missing`, `size` or `crc` for each file that does, then `checked: N entries, M differ`. |
| `recover` | Finishes a change that a pulled card or a cut left committed, removes what a change that was not committed left, says which, and gives the line of `status`. |

The check is the board's, through the project's reader, for the canvas of 60 x 60; its
reasons are those of [reasons.md](reasons.md). `add`, `remove` and `check` work on a card
whose catalog is `ok`: on one without a catalog they say `error: the catalog is none;
import writes it`, and on a damaged or incompatible one that `import` writes it anew, or
for an interrupted change that `recover` finishes it. The exit status is 0, 1 when a file
was refused, a file differs from its entry or the catalog cannot be used, and 2 for a
command line that is not understood or a folder that is not there.

### The card written by the board

A card with a catalog that is `ok` is written by the board while it is in the board: the
card is mounted, its folder `odrig` is there and no read has failed.
`odrigctl upload --external FILE` puts an animation on it, with its entry, and prints the
id the card gave it; `odrigctl remove <id>` of one of the card's animations takes the file
and its entry out; `odrigctl catalog` says the state of both catalogs, and
`odrigctl catalog rebuild external` reads every file of the card and writes its catalog
anew, as `import` does on a computer. The app does the same from Upload's `Store on`, Settings' `Catalogs` and the
card's rows, [android-app.md](android-app.md). A card that cannot be written, or a USB
stick, answers `read-only` to an upload and `in-use` to a removal, as before.
[commands.md](commands.md#catalogs) has the commands, and [catalog.md](catalog.md) the
files. To keep one or two small animations inside as the fallback and the rest on the
card: upload each animation to the card, remove it from the board's storage, and run
`odrigctl catalog rebuild internal` once at the end.

## The reader and its wiring

The reader is the SparkFun Shifting microSD board, a microSD socket with level shifters,
fed with 3.3 V. The owner wired it on 2026-10-22 and reported the wiring complete; no
agent has measured it. Nothing is soldered, and a change of the wiring, the power or the
reader is the owner's.

| The reader | The board | In the build |
|---|---|---|
| SCK | GPIO39 | `ODRIG_SD_SCK=39` |
| DO (MISO) | GPIO40 | `ODRIG_SD_MISO=40` |
| DI (MOSI) | GPIO41 | `ODRIG_SD_MOSI=41` |
| CS | GPIO42 | `ODRIG_SD_CS=42` |
| VCC | 3V3, never 5 V | |
| GND | GND | |
| CD | not wired | |

GPIO39 to GPIO42 are the pins left free by the twenty LED outputs on pins 1 to 18, 21 and
47, by the two USB connections, 19 and 20 for the chip's own unit and 43 and 44 for the
UART, and by the module's memory and boot pins. The firmware's suite checks that no pin
of the reader is one of the outputs of `mapping/legs-20.json` or a USB pin.

`firmware/usermod/odrig_sd_config.h` holds the defaults, every pin -1, the clock
`ODRIG_SD_FREQUENCY` of 4 MHz and the mount point `/sd`, and the checks: a pin outside 39
to 42, two pins alike, or a clock below 400 kHz or above 20 MHz start no reader and touch
no pin. A build that names no pins is such a build. The environment `odrig_microsd` of
`firmware/platformio_override.ini.in`, the firmware's, names the four pins, and its probe
build's extends it; the USB stick's environments have none of the card's code and not its
flag `ODRIG_DRIVE_SD_SPI`.

The clock stays 4 MHz. On 2026-10-22, 1 MHz and 400 kHz dropped out as 4 MHz did, and on
2026-10-23 4 MHz ran clean for fifteen minutes; a slower clock only makes the reads
slower.

## The build and the flash

```
python3 firmware/fw.py build
python3 firmware/fw.py flash --wait 60
```

The card's firmware is the firmware: `build` builds it on the newer software of
[firmware.md](firmware.md#the-newer-software), Arduino-ESP32 3.3.12 on ESP-IDF 5.5.5, in
the folder `build/firmware/newer/`, and keeps it as `build/firmware/out/odrig-firmware.bin`
with its SHA-256 beside it; `flash` and `install-firmware` write it. `build --microsd`
builds the same firmware and keeps it as `odrig-microsd.bin`, the name of the board
sessions below, which `flash --image build/firmware/out/odrig-microsd.bin` writes. The USB
stick's firmware is `build --stick`, on the software known good.

In the card's firmware the USB host is not compiled. The chip's own socket stays a serial
port for as long as the board runs, for commands and for flashing, whatever is plugged
into it, and the socket marked COM takes commands and flashing as before and writes the
log. The setting `computer_wait_s` of WLED's settings has no effect there.

The image built on 2026-10-22 from the sources of that day has 1,765,808 bytes, within
the application partition of 3,145,728 bytes, and the SHA-256
`fd089753d86c92d9cbfbb2e4823d49428e4b037213b656736636b9dd9a1950a5`. Its checks: the
image matched the build's own `firmware.bin` byte for byte; its program held Arduino's
`SD` library, the card's task, the mount path `/sd/odrig` and the text `card opened:`;
the task passed 39, 40, 41 and 42 to the SPI unit as SCK, MISO, MOSI and CS, and the
card was mounted with CS 42 at 4 MHz; both USB serial ports were linked, and nothing of
the USB host was. The firmware's suite, 545 tests then, and the core's tests of drives and
of the playlist, 82, passed. The board runs that image. The firmware with the card's free
and total space is another image: built on 2026-10-24 by `build`, 1,771,808 bytes, SHA-256
`1752f8216be641f0c60907f96a64bf2cd3669ed4e25923d34e0e795c596e19bf`, not flashed; the
image the board session flashes is built from the sources of that day, and its hash is
recorded then.

## Plugging in and pulling out

The reader's card-detect line is not wired, so the firmware finds a card by reading. A
task of the firmware, `odrig-drive`, makes one step a second:

- **No card mounted.** It tries to mount one. That fails for an empty reader and for a
  file system the chip does not read alike, which the firmware cannot tell apart. When a
  card mounts, the core gets a new drive number. A card with a catalog is read from its
  catalog, as [catalog.md](catalog.md) describes, and its folder is not listed. The folder
  `odrig` of a card without one is listed once, when the core asks: the core reads the
  card's files while the show plays and adds each sound one to the playlist as it
  finishes reading it. For 16 MB that takes minutes.
- **A card mounted.** It reads the card's first sector. When that read fails, or a read
  of a file has failed since the last step, the card's files are closed, the card is
  unmounted, and the core gets the drive number 0: the card's animations leave the
  playlist and `list`. When one of them was playing, the playlist moves on to the next
  animation it has. The next step, a second later, tries to mount again.

**Changes of the card.** The core changes a file of the card by its name in the folder
`odrig`. A file written counts as whole once its bytes and its directory entry are on the
card and it holds every byte it was given. FAT gives no file a name that another file has,
so a rename onto a file that is there removes that file first, once the file to be renamed
is known to be there: a cut between the two leaves that file under its old name, and the
catalog's change renames it again when it is finished. A file the player reads that a
change replaces or removes is closed first: its reads fail, and the card stays mounted. A
write that fails is no fault of the card, and a card whose read failed is not written
until it is mounted again. Each change is paced as the board's own storage calls are.

A card put back is taken up again with a new drive number, and its animations get their
ids afresh. A card that goes while one of its files is read can hold that read until the
chip's SD driver gives up, which may pause the LEDs for a moment. A board without a card
plays its installed show as it always did.

## The log and WLED's information

The card's lines in [the log](firmware.md#the-log) on the socket marked COM are of the
kind `sd`:

```
#log 1.204 sd: card not mounted; no card or unreadable file system
#log 9.311 sd: card mounted
#log 9.392 sd: card opened: 122 animation files in odrig
#log 12.840 player: drive file clip.odrg left out: size-mismatch
#log 74.502 sd: card unavailable; files closed, waiting for a card
```

- `card mounted`, or `the card has no folder odrig`, when a card is mounted.
- `card opened: <n> animation files in odrig`, or `card opened: <n> animation files in
  <m> folders of odrig` when sub-folders were taken, when the core has the folder of a
  card without a catalog listed; with `; <k> files and <f> folders passed over` at its
  end when the limits, the depth or a name left something out. `card folder odrig could
  not be read` when the folder could not be read.
- `card not mounted; no card or unreadable file system`, once for each spell without a
  card.
- `card unavailable; files closed, waiting for a card`, when a card went.
- `SPI did not start on the configured pins; reader disabled`, and
  `SD pins or SPI frequency not configured safely; reader disabled`, for a reader that
  is not started.

The player's lines are as for a drive: `drive file <name> left out: <reason>` for a file
of the card that is left out. Every byte outside printable ASCII is written as `?`.

WLED's information says under `odrig drive`: `SD not configured` when the build names no
pins, `no SD reader` when the reader could not be started, `looking for SD` before the
first look, `not readable` while no card is mounted, `none` for the second after a card
went, and `<n> files` for a mounted card: the files listed, or named from its catalog, so
far.

## The board sessions

### 2026-10-22: the first trial

The owner reported the wiring complete and authorised the flash. `flash --image
build/firmware/out/odrig-microsd.bin --wait 60` wrote the image through the chip's own
socket, `/dev/cu.usbmodem1101`, the only cable on the Mac. The board kept the bigger
layout, 13,500,416 bytes of storage, and its installed show, one 60 x 60 animation at
brightness 32.

- The card was mounted. `list` showed 60001, `01-062cd029337681-5_crop.odrg` of 22,103
  bytes, and 60002, `01-062cd029337681-5_cropfit.odrg` of 129,539 bytes, after the
  installed animation; the core lists a file of a drive only once it has read it whole.
- `play 60001` played it: `status` answered animation 60001 at 41 refreshes a second,
  brightness 32, no error. That is what the firmware reported; no person looked at LEDs.
- Then entries that were already listed disappeared and were found again, also within
  one open session of the command tool, without the port being opened again: the card
  dropped out. Only the clock was changed, and only for two trials, with the pins, the
  wiring, the power, the card and the show as they were:

| SPI clock | What was seen |
|---|---|
| 4 MHz, the build | Two files of the card listed; counts of 2, 0, 1, 2, 0 over repeated `list`s. |
| 1 MHz | Thirteen files listed, with the names and sizes of the source folder, then none; an entry was lost after 30.6 seconds. |
| 400 kHz | A listed file disappeared after 5.4 seconds. |

Both trial builds passed the firmware's 545 tests. The slower clocks did not help and
show no cause in the hardware either. In the code, a failed read of a file and a failed
read of the first sector each unmount the whole card, which is tried again a second
later; WLED's information does not tell the two apart. The 4 MHz image was built again
with the same SHA-256 as before, `fd089753…`, flashed back, and the board left on it,
playing, at brightness 32.

### 2026-10-23: both sockets on the Mac

The owner plugged the second cable in, so that both sockets of the board were on the
Mac: the chip's own socket as `/dev/cu.usbmodem1101` and the socket marked COM as
`/dev/cu.usbmodem5C831043631`. The commands went through the socket marked COM, one
program at a time. Nothing was flashed, and the firmware was the 4 MHz image of the day
before.

- At the start, `list` showed 43 of the card's animations read, and 60004 playing at 49
  refreshes a second. The log had no new line in that first look.
- The whole list was compared with the card's source folder again and again, for
  fifteen minutes:

| Watch | Samples | Time | The card's entries | Entries lost |
|---|---:|---:|---|---:|
| First | 108 | 598.5 s | 48 to 118 | 0 |
| Second | 53 | 303.0 s | 118 to 122 | 0 |

- All 122 of the card's files were listed, with the names and the sizes of the source,
  16,475,328 bytes, as 60001 to 60122, and with the installed `1000313581.odrg` of
  52,667 bytes, 123 items. That the core lists a file means it read it whole and found it
  sound for the canvas; it is not a comparison of the card's bytes with the source.
- `play` of four of the card's files, each watched past a loop boundary with `status`
  once a second and `list` every five seconds; each kept its id, brightness 32 and no
  error, and no entry was lost. The first two seconds after each `play` are left out of
  the rates, since `status` can still name the animation before:

| Id | File | Watched | Refreshes a second |
|---:|---|---:|---|
| 60001 | `01-062cd029337681-5_crop.odrg` | 20.6 s | 50 |
| 60061 | `21-fx-183_crop.odrg` | 24.7 s | 48 to 50 |
| 60119 | `43-yt-784dsKVrdjQ_center60of256.odrg`, the largest | 30.7 s | 26 to 48 |
| 60122 | `alphabet_hebrew.odrg`, the last | 40.4 s | 46 to 50 |

- `play all` put the playlist back, with the installed animation 1 first. With no other
  command, `status` later named 60002 with `playing` `all`, at 46 or 47 refreshes a
  second: the playlist went on to the card's animations by itself.

The board was left playing that playlist at brightness 32. Why the first day dropped out
and the second did not is not known: the second cable is the one difference that was
seen, and it is not shown to be the cause.

## What is open

These need the board and the owner, in a session under "If you have a board" of the
working rules.

- The firmware of today, with the card's free and total space, built and flashed; its
  hash recorded.
- The card's animations listed over the chip's own socket and over Wi-Fi as well as over
  the socket marked COM, and `status` while the largest file plays.
- The card pulled out while one of its animations plays and put back: the times, the
  log's lines and any pause of the LEDs.
- The dropouts, with the two cables of 2026-10-23, both sockets on the Mac: fifteen
  minutes of `status`, `list` and the log. The firmware must work with one cable or with
  two, by the owner's answer of 2026-10-24.
- The owner's look at the card's animations on the LEDs, also while the board runs with
  no computer, powered as at the event, and the app's list on a phone.
- Seed 35's catalogs on the board: the card's catalog made on the Mac with
  `python3 -m odrig.catalog /Volumes/<card> import`; the board's animations moved onto the
  card with `odrigctl upload --external FILE` and `odrigctl remove <id>`, one or two small
  fallback animations kept inside; `odrigctl catalog rebuild internal` once; the first
  reply, the first list with sizes, the first picture and the card's catalog published,
  measured against the start of 2026-10-23.
