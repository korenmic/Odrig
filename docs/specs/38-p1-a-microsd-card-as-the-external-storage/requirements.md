# Requirements: a microSD card as the external storage

Seed: [`project-seeds/38-p1-a-microsd-card-as-the-external-storage/seed.md`](../../../project-seeds/38-p1-a-microsd-card-as-the-external-storage/seed.md).

A USB stick on the board's own USB socket never worked, directly or through a hub, and
on 2026-10-24 the owner closed that path. A microSD card in a small reader wired to four
pins of the board is the external storage instead. Codex built the firmware for it on
2026-10-21 to 2026-10-23 without a seed, as `python3 firmware/fw.py build --microsd`, on
the newer software of seed 22's trial, and the board has run it since 2026-10-22. This
spec gives that work its requirements, its design as built, and the tasks that are done
and those that are open.

The owner asked that this spec be written without a question pass. The seed's questions
1 to 6 were decided by the agent on 2026-10-24 and are recorded in
[drifts.md](../../drifts.md) under "Seed 38". Two questions are the owner's and stay open;
the tasks that need them come last:

7. Which socket powers the board at the event, the chip's own or the one marked COM, and
   is a computer on it? The first board session, with the Mac on the chip's own socket
   only, lost the card; the second, with both sockets on the Mac, did not.
8. Once the board checks pass, does the microSD build become the firmware that `build`
   makes, with the stick's build kept behind an option?

In this document "the card" is a microSD card in the reader; "the reader" is the
SparkFun Shifting microSD board the owner wired, a level-shifting adapter that takes
3.3 V; "the stick's build" is what `build` makes, the firmware with the USB host for a
stick, on the software known good, Arduino-ESP32 2.0.18 on ESP-IDF 4.4.8; "the newer
software" is Arduino-ESP32 3.3.12 on ESP-IDF 5.5.5 with pioarduino's platform
55.03.312-1, in `build/firmware/newer/`; "the card's build" is what `build --microsd`
makes, `odrig-microsd.bin`, on the newer software; "the chip's own socket" is the USB-C
socket behind the chip's own USB unit, and "the socket marked COM" the one that reaches
the chip's UART through a bridge chip; and "a session" is a board session with the owner,
under "If you have a board" in the working rules.

## Requirement 1: the card's build

1. `python3 firmware/fw.py build --microsd` SHALL build WLED 16.0.1 with the patches of
   `firmware/patches/`, the usermod and the core on the newer software, with the card's
   code in place of the USB host, and keep the image as
   `build/firmware/out/odrig-microsd.bin` with its SHA-256 beside it.
2. The card's build SHALL use the newer software's folder, `build/firmware/newer/`, its
   Python environment and its PlatformIO folders, as `build --trial` does, and SHALL
   change nothing of the stick's build: `build`, `build --probe`, `build --stock` and
   `build --standalone` build as before, and `odrig-firmware.bin` is never replaced by it.
3. `--microsd` SHALL go with none of `--stock`, `--probe`, `--trial` and `--standalone`;
   the tool refuses the combination before it builds.
4. The image SHALL fit the application partition, 3,145,728 bytes.
5. `docs/firmware.md` SHALL name the card's build among the builds, and the documents
   SHALL record the image's size and SHA-256 that were built and what the board runs.

## Requirement 2: the card's animations

1. With a card in the reader whose file system is FAT32 or FAT16, a card of 32 GB or
   less as it comes or any card formatted FAT32 on a computer, the firmware SHALL mount
   it at `/sd`, without formatting, only to read it, and look in its folder `odrig` at
   the top, and in no other.
2. The firmware SHALL list for the core the files of that folder whose names end in
   `.odrg`, in any case, and do not begin with a dot, in the order of their names, at
   most 256; folders inside `odrig` and other files are passed over. Names are kept to
   the letters `a`-`z` and `A`-`Z`, digits, `-`, `_` and `.`; a file whose name has other
   letters may come out as `?` and is left out.
3. The core SHALL treat the card as it treats a drive of seed 20: each sound file for the
   board's canvas is an animation of the playlist after the installed ones, with the
   lowest id from 60001 up that is free, the same every time for the same files and the
   same show; a file that is no animation, is for another canvas or is damaged is left
   out, named in the log with its reason, and never makes the show invalid.
4. `list` SHALL show the card's animations after the show's items, `play <id>` SHALL
   play one, `status` SHALL name the one on the LEDs, and `remove` and `upload begin` of
   a card id SHALL be refused with `in-use`, as for a drive.
5. The card SHALL never be written or formatted: the firmware mounts it without the
   option to format, opens its files for reading only, and no command changes it.
6. `space` SHALL report the card under `external` with `present` true, `read_only` true
   and its free and total bytes, read from the card's file system without writing; when
   the numbers cannot be read the capacities are null, and with no card `present` is
   false, as seed 29 has it.
7. The firmware SHALL take no more memory for the card than the stick's code took: the
   list's names in 64 KB of the external memory, and two read buffers of 4 KB each in the
   internal memory.

## Requirement 3: the sockets and WLED's information

1. In the card's build the chip's own socket SHALL stay a serial port for as long as the
   board runs, for commands and for flashing, whatever is plugged into it: the USB host is
   not compiled in, the firmware never waits for a computer there, and `computer_wait_s`
   has no effect.
2. The socket marked COM SHALL take commands and flashing as before, and write the log.
3. WLED's information SHALL say what there is of the card under `odrig drive`:
   `SD not configured` when the build names no pins, `no SD reader` when the reader could
   not be started, `looking for SD` before the first look, `not readable` while no card is
   mounted, since without the card-detect line the firmware cannot tell an empty reader
   from a card whose file system it does not read, `none` for the second after a card
   went, and `<n> files` for a mounted card.

## Requirement 4: plugging in and pulling out

1. A card put into the reader while the board runs SHALL be taken up without a restart:
   the firmware tries to mount once a second while no card is mounted, lists the folder
   once, and gives the core a new drive number, so the core reads the files and adds them
   to the playlist one by one while the show plays.
2. A card pulled out SHALL be dropped without a restart: the firmware reads the card's
   first sector once a second while a card is mounted, and a read of a file that fails is
   remembered; on either sign it closes the card's files, unmounts the card and gives the
   core the drive number 0, so the card's animations leave the playlist and `list`.
3. The installed show SHALL go on through both; when one of the card's animations was
   playing, the playlist moves on to the next animation it has.
4. A card put back SHALL be taken up again, with a new drive number, so that its
   animations return with ids given afresh under 2.3.
5. A card that fails while a file is read MAY hold that read until the chip's SD driver
   gives up; the refresh rate is measured in the session with the card pulled out, and a
   pause of the LEDs longer than a second is recorded.
6. A board without a card SHALL play its installed show as it does today.

## Requirement 5: the log

1. The log on the socket marked COM SHALL have a line of the kind `sd` for each event of
   the card: `card opened: <n> animation files in odrig`, `the card has no folder odrig`,
   `card folder odrig could not be read`, `card not mounted; no card or unreadable file
   system`, once for each spell without a card, `card unavailable; files closed, waiting
   for a card`, `SPI did not start on the configured pins; reader disabled`, and `SD pins
   or SPI frequency not configured safely; reader disabled`.
2. The player's line for every file of the card that is left out, `drive file <name>
   left out: <reason>`, SHALL be written as for a drive.
3. No line of the log SHALL name a secret.

## Requirement 6: the pins and the clock

1. The card's build SHALL drive the reader on GPIO39 for SCK, GPIO40 for MISO, GPIO41 for
   MOSI and GPIO42 for CS, at 3.3 V, and on no other pin.
2. The twenty LED outputs SHALL stay on pins 1 to 18, 21 and 47, and the firmware's test
   SHALL check that no pin of the reader is one of them, nor a USB pin, 19, 20, 43 or 44.
3. The firmware SHALL refuse any pin outside 39 to 42, two pins alike, and a clock below
   400 kHz or above 20 MHz: it starts no reader, touches no pin, and says so in the log.
   A build that names no pins, the defaults of `odrig_sd_config.h`, is such a build.
4. The SPI clock SHALL be 4 MHz, `ODRIG_SD_FREQUENCY`; no other clock is tried in this
   seed, since 1 MHz and 400 kHz dropped out alike on 2026-10-22.
5. No pin, voltage or wiring SHALL change without the owner.

## Requirement 7: the rate

1. The refresh rate SHALL stay from 20 to 50 a second while a file of the card plays, as
   it did on 2026-10-23: 26 to 48 for the largest file of the owner's card and 46 to 50
   for the others.

## Requirement 8: tests and documents

1. The suite of the firmware tool SHALL cover the card's build: the kind `microsd` on the
   newer software, its image and checksum paths, the refused combinations, the environment
   `odrig_microsd` and its flags, and the pins against the twenty outputs; and the card's
   code compiled on the Mac with a stand-in card and task scheduler: the refused pins and
   clocks, a reader that does not start, a card that is absent, unreadable, plugged in,
   pulled out and put back, the names filtered and sorted, the first 256, the installed
   files read beside the card's, the files closed before the card is unmounted, and the
   free and total space.
2. Every suite that needs no board SHALL pass.
3. `docs/microsd.md` SHALL be the card's page: how to prepare a card, the reader's wiring,
   the build and the flash, the log's lines, WLED's information, what the board sessions
   gave, and what is open. `docs/firmware.md` SHALL name the card beside the stick, the
   card's build among the builds, the `sd` lines in the log, and the sessions under
   "Verified on the board", and SHALL say where it calls the newer software "the trial"
   that the card's build uses the same software. `docs/firmware-additions.md` SHALL have
   the card's line, and `docs/firmware-prerequisites.md` SHALL say in lines 9 and 16 that
   the external storage is the card, how far it has come, and what is open. `AGENTS.md`
   SHALL name the seed in "What is coming" until it is completed, and link
   `docs/microsd.md`.
4. By the owner's rule of 2026-10-16, the card's line in `docs/firmware-additions.md`
   SHALL say that the fallback of seed 12 gets the card too.

## Requirement 9: the board

Only the board can show these; each is done in a session with the owner.

1. The merged firmware SHALL be built with `build --microsd` and flashed through the
   socket marked COM with `flash --image`, the image's hash recorded, the installed show
   and the settings kept.
2. With the owner's card in the reader, `list` over the socket marked COM and over Wi-Fi
   SHALL show the card's animations after the installed ones, once the core has read
   them; `status` SHALL report 20 to 50 refreshes a second while a file of the card
   plays; and both USB sockets SHALL answer commands.
3. The card pulled out while one of its animations plays SHALL be followed as Requirement
   4 says, and the card put back as well; the log's lines and the time each took are
   recorded.
4. Whether the dropouts of 2026-10-22 come back SHALL be tried with the cable arrangement
   the owner names in answer to question 7, for at least fifteen minutes, with `status`
   and `list` sampled and the log kept; what is seen is recorded before anything is
   changed. A cause in the card's code or its clock is mended in this seed; a cause in the
   hardware is the owner's and becomes a new seed.
5. The owner SHALL see the card's animations on the LEDs, and SHALL see them while the
   board runs with no computer attached, powered as it will be at the event.
6. Afterwards the board SHALL be left playing its show at a brightness of 40 or less, and
   what is left on it recorded.

## Requirement 10: what the installation runs

1. Until the owner answers question 8, the card's build SHALL stay a variant: `build`
   makes the stick's build, and the board is flashed with the card's build by
   `flash --image build/firmware/out/odrig-microsd.bin`.
2. When the owner says yes, `build` and `build --probe` SHALL make the card's firmware
   and its probe build on the newer software, the stick's build SHALL stay available
   behind an option, the trial's environments and `ODRIG_BOARD_IMAGES=trial` SHALL go,
   the board's suite SHALL run on the card's firmware, and the fallback of seed 12 SHALL
   take the card's line into its spec. When the owner says no, nothing changes and the
   answer is recorded.

## Left out on purpose

- Writing or formatting the card, and installing anything from it.
- A change to the core, the emulator, the app or the commands: the card is a drive to
  all of them.
- The reader's card-detect line: it is not wired, and presence is found by reading.
- exFAT, and cards above 32 GB as they come.
- Any clock other than 4 MHz, and any change of the wiring or the power.
- Removing the stick's code or the hub's trial from the sources.
