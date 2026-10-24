# Requirements: standalone firmware as a fallback

Seed: [`project-seeds/12-p2-standalone-firmware-as-a-fallback/seed.md`](../../../project-seeds/12-p2-standalone-firmware-as-a-fallback/seed.md).

The firmware in use is WLED 16.0.1 with one patch and our usermod, which hosts the shared
core. This spec adds a second firmware for the same board that holds nothing of WLED: a
small program that hosts the same core, drives the same twenty outputs, and accepts the
same commands over USB and over the board's own Wi-Fi network. It is a fallback for the
event. The WLED-based firmware stays the one in use.

In this document:

- "the WLED-based firmware" is what `python3 firmware/fw.py build` builds today;
- "the standalone firmware" is the second one;
- "the stored settings" are the two files `/cfg.json` and `/wsec.json` in the top folder
  of the board's storage, which WLED reads and which the firmware tool writes (seed 08);
- "the probe report" is the JSON line a probe build answers `#probe` with.

## Requirement 1: built and flashed by the firmware tool

**User story.** As the person who prepares the board, I want one command to build the
standalone firmware and one to flash it, so that switching to it at the event is a matter
of a minute.

1. WHEN `python3 firmware/fw.py build --standalone` is run THEN the tool SHALL build the
   standalone firmware in the work folder and keep the image with its SHA-256 beside it.
2. WHEN `python3 firmware/fw.py build --standalone --probe` is run THEN the tool SHALL
   build the probe build of the standalone firmware.
3. WHEN `python3 firmware/fw.py flash --standalone` is run THEN the tool SHALL write the
   standalone image to the board the way `flash` writes the WLED-based one, and wait for
   the reply to `status`.
4. WHEN the standalone firmware is built THEN no file of WLED SHALL be compiled into it.
5. WHEN the standalone firmware is built THEN the platform, the LED library and the web
   server library SHALL be the versions that WLED 16.0.1 pins for this board.
6. WHEN any command of the tool that exists today is run THEN it SHALL do what it does
   today.
7. WHEN the standalone firmware is built THEN the source files of the shared core SHALL
   be the files in `core/`, unchanged.

## Requirement 2: the start

**User story.** As an operator, I want a board with the standalone firmware to start its
show by itself, as it does with the WLED-based firmware.

1. WHEN the board starts THEN the firmware SHALL start the core on the files of the folder
   `/odrig` of the board's storage.
2. WHEN the show is valid THEN the firmware SHALL make one output for each leg of
   `mapping.json` and the start item SHALL play.
3. WHEN the storage cannot be mounted THEN the firmware SHALL NOT format it.
4. WHEN the show is invalid THEN no LED SHALL be lit, and `status` SHALL give the reason
   the WLED-based firmware gives for the same files.

## Requirement 3: commands over USB

**User story.** As someone who controls the board from a computer, I want the same
commands and the same replies whichever firmware is on the board.

1. WHEN a command line of `docs/commands.md` arrives on the USB serial port THEN the
   reply SHALL be the bytes the WLED-based firmware replies with, for every member but
   the measured rate.
2. WHEN no command is sent THEN the firmware SHALL write nothing to the port.
3. WHEN the session of commands that the board suite sends is run THEN its replies SHALL
   equal those of the emulator for the same files.

## Requirement 4: the network and commands over HTTP

**User story.** As an operator with a phone, I want to join the same network with the same
password and send the same requests, whichever firmware is on the board.

1. WHEN the stored settings hold a network name of 1 to 32 characters and a password of 8
   to 63 characters THEN the firmware SHALL host a Wi-Fi network with that name,
   protected by that password.
2. WHEN the network is up THEN the board's address SHALL be `4.3.2.1`, as with the
   WLED-based firmware.
3. WHEN the stored settings hold no such name and password THEN the firmware SHALL host
   no network, and SHALL play and answer over USB as ever.
4. The firmware SHALL never host a network with a name or a password that is compiled
   into it.
5. WHEN `POST /odrig` arrives with a command line as its body THEN the response SHALL be
   what the WLED-based firmware gives: status 200 with the reply as its body, 405 for
   another method, 404 for another path, 503 when no reply can be given.
6. The firmware SHALL serve no page and offer no way to change a setting.

## Requirement 5: the outputs

**User story.** As the builder of the installation, I want all twenty legs driven by the
standalone firmware, on the pins the mapping names.

1. WHEN the target mapping is installed THEN the firmware SHALL drive twenty outputs:
   sixteen through the chip's parallel driver and four through its RMT driver, each leg
   on the driver the WLED-based firmware gives it.
2. WHEN a refresh is sent THEN each output SHALL carry the bytes the core gives its leg,
   as WS2812B data in the order green, red, blue.
3. WHEN a leg names a pin the board cannot use THEN that output SHALL not work and every
   other output SHALL work.
4. WHEN a mapping has more legs than the board has outputs THEN the first twenty SHALL
   work.

## Requirement 6: the limit on LED current

**User story.** As the builder of the installation, I want the same limit on LED current
with either firmware, set in one place.

1. WHEN `/cfg.json` holds `hw.led.maxpwr` THEN the firmware SHALL take it as the limit in
   milliamps. Without it the limit SHALL be 850.
2. WHEN the limit is 0 THEN no refresh SHALL be dimmed.
3. WHEN the limit is above 0 THEN the firmware SHALL estimate the current of each refresh
   and dim it as `design.md`, "The limiter", defines, which is WLED's arithmetic.
4. WHEN the same picture is played with the same limit on both firmwares THEN the two
   probe reports SHALL give the same `limit_ma` and the same `used_ma`.

## Requirement 7: the rate

**User story.** As the owner, I want to know how fast the standalone firmware refreshes,
beside the figures of the WLED-based firmware.

1. WHEN the bench show plays THEN `status` SHALL report a rate from 20 to 50.
2. WHEN the demo show and a dense 60 x 60 animation play on the target mapping THEN their
   rates SHALL be measured and written into `docs/firmware.md` beside those of the
   WLED-based firmware.
3. No work SHALL be done to raise a rate that is from 20 to 50.

## Requirement 8: switching between the two firmwares

**User story.** As the person at the event, I want to switch a board from one firmware to
the other and back without installing its show again.

1. WHEN either firmware is flashed THEN only the first application partition SHALL be
   written and the boot selection cleared; the storage SHALL not be written.
2. WHEN the board is switched to the standalone firmware and back THEN the installed show
   SHALL be byte for byte what it was, and so SHALL the stored settings.
3. The standalone firmware SHALL write no file outside the folder `/odrig`.
4. The standalone firmware SHALL be built for the partition table of the WLED-based
   firmware.

## Requirement 9: the probe build

**User story.** As a program that tests the board, I want to check what the standalone
firmware gives the LEDs without eyes on them.

1. WHEN the probe build receives the line `#probe` THEN it SHALL answer with one JSON
   line that has `"probe":1` and `"firmware":"standalone"`.
2. The report SHALL have, with the meaning they have in `docs/firmware.md`: `start_ms`,
   `heap`, `loops`, `sent`, `gap_ms`, `poll_us`, `send_us`, `limited`, `limit_ma`,
   `used_ma`, `ap`, `error`, and `outputs` with `leg`, `pin`, `count`, `ok`, `driver`,
   `crc` and `pulses` for each.
3. WHEN an output of 180 LEDs has sent a refresh THEN its `pulses` SHALL be 4,320.
4. WHEN the limiter does not dim THEN the `crc` of an output SHALL be the CRC-32 of the
   bytes the core gives its leg.

## Requirement 10: the board suite

**User story.** As a contributor, I want the tests that the WLED-based firmware passes on
the board to judge the standalone firmware too.

1. WHEN `python3 firmware/fw.py test-board --standalone` is run THEN the board suite SHALL
   run against the standalone firmware and its probe build.
2. WHEN a test depends on WLED itself THEN that run SHALL skip it, with the reason.
3. WHEN a test does not depend on WLED THEN that run SHALL pass it.
4. WHEN either run of the board suite ends THEN the board SHALL be left on the WLED-based
   firmware with the bench show, autostarting, at a brightness of 40 or less.
5. WHEN `python3 firmware/fw.py test-board` is run THEN it SHALL pass as it does today.

## Requirement 11: the documents

**User story.** As someone who has to choose a firmware at the event, I want one page that
says what each one is, how to switch, and what each offers that the other does not.

1. `docs/firmware.md` SHALL describe both firmwares, the commands that build and flash
   each, how to switch from one to the other, and a table of what each offers that the
   other does not.
2. `docs/firmware.md` SHALL give the measured rates and start times of both, side by side.
3. `docs/decisions.md` SHALL say that the fallback exists and which firmware is in use.
4. `AGENTS.md` SHALL no longer list seed 12 as coming.

## Requirement 12: what is left behind

1. WHEN the work of this seed ends THEN the board SHALL run the WLED-based firmware and
   the bench show, autostarting, at a brightness of 40 or less.
2. Every suite that needs no board SHALL pass.

## Requirement 13: the microSD card

**User story.** As the person who prepares the board, I want the fallback to play the
animations of the microSD card as the firmware does, so that switching to it at the event
keeps the card's animations.

This is line 26 of [firmware-additions.md](../../firmware-additions.md), which the
WLED-based firmware has had since 2026-10-24, when the owner made the card's firmware the
one `python3 firmware/fw.py build` makes; the fallback follows that firmware, and the USB
stick's lines 17 and 18 hold for the stick's build only.

1. The standalone firmware SHALL read the `.odrg` files of the folder `odrig` of a
   microSD card in the reader on GPIO39 to GPIO42, at 4 MHz, and give them to the core
   as a drive, as the WLED-based firmware does: FAT32 or FAT16, at most 256 files, never
   written, taken up and dropped while the board runs, its free and total space for
   `space`, and the log's `sd` lines on the socket marked COM.
2. The standalone firmware SHALL keep the chip's own USB socket a serial port.
3. The board suite against the standalone firmware SHALL list a card's animations after
   the installed ones when a card is in the reader.
