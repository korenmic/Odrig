# The microSD card

The installation's external storage of animations is a microSD card in a small reader
wired to four pins of the board. The firmware reads the `.odrg` and `.odrgx` files of the card's
folder `odrig` and plays them after the installed ones, with ids from 60001 up, as
[show.md](show.md#animations-from-a-usb-drive) describes for a drive. The card is never
written. The core, the emulator and the app see a drive, whether the firmware fills it
from a card or from a USB stick: the emulator's option `--drive DIR` stands in for the
card.

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
  files, made for the board's canvas as the installed ones are. Names ending in `.odrg` or
  `.odrgx`, in any case,
  and not beginning with a dot are taken, in the order of their names, at most 256.
  Folders inside `odrig` and other files are passed over.
- **The names.** Keep names to the letters `a`-`z` and `A`-`Z`, digits, `-`, `_` and `.`.
  Another letter, a Hebrew one for instance, may come out as `?`; such a file cannot be
  opened by its name and is left out, with its line in the log.
- **Never written.** The firmware mounts the card without the option to format it,
  opens its files for reading only, and no command changes it. Nothing is installed
  from it into the board's storage.

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
  card mounts, its folder `odrig` is listed once, and the core gets a new drive number:
  it reads the card's files while the show plays and adds each sound one to the playlist
  as it finishes reading it. For 16 MB that takes minutes, and `list` answers `busy`
  meanwhile; that is no fault.
- **A card mounted.** It reads the card's first sector. When that read fails, or a read
  of a file has failed since the last step, the card's files are closed, the card is
  unmounted, and the core gets the drive number 0: the card's animations leave the
  playlist and `list`. When one of them was playing, the playlist moves on to the next
  animation it has. The next step, a second later, tries to mount again.

A card put back is taken up again with a new drive number, and its animations get their
ids afresh. A card that goes while one of its files is read can hold that read until the
chip's SD driver gives up, which may pause the LEDs for a moment. A board without a card
plays its installed show as it always did.

## The log and WLED's information

The card's lines in [the log](firmware.md#the-log) on the socket marked COM are of the
kind `sd`:

```
#log 1.204 sd: card not mounted; no card or unreadable file system
#log 9.311 sd: card opened: 122 animation files in odrig
#log 12.840 player: drive file clip.odrg left out: size-mismatch
#log 74.502 sd: card unavailable; files closed, waiting for a card
```

- `card opened: <n> animation files in odrig`, `the card has no folder odrig`, or
  `card folder odrig could not be read`, when a card is mounted.
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
went, and `<n> files` for a mounted card.

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
