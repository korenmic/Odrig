# A microSD card as the external storage

## Summary

A microSD card is the installation's external storage of animations, in place of the USB
stick. A card reader is wired to four pins of the board, and a firmware variant,
`python3 firmware/fw.py build --microsd`, reads the animation files of the card's folder
`odrig` and plays them after the installed ones, with the same ids from 60001 up, the
same commands and the same log as the stick had. The card is never written. The board's
own USB socket stays a serial port, so a computer reaches the board on either socket.

Codex built this on 2026-10-21 to 2026-10-23 on the branch `codex/microsd-storage`,
without a seed, and the board has run it since 2026-10-22. This seed gives that work its
place in the project: what was built, what was seen on the board, and what is still open.

## Priority

- `P1`

## Depends On

- Seed 20, for the player's external animations: the folder `odrig`, the ids from 60001,
  the playlist, the log of files left out. The core and the emulator are not changed.
- Seed 21 and seed 23, for the commands and the log on the socket marked COM.
- Seed 22, for the newer software of Espressif, Arduino-ESP32 3.3.12 on ESP-IDF 5.5.5,
  that `build --trial` builds on: the microSD build is built on it. Seed 22 itself is
  superseded by this seed; its code stays.
- Seed 24, for the bigger layout of the flash, which the board has.

## Product Context

A stick on the board's own USB socket never worked: the socket gives a plugged device no
power, and through a hub with power of its own the board still saw no stick, also with
the newer software of seed 22's trial. On 2026-10-24 the owner closed that path.

On 2026-10-21 the owner asked for a microSD card instead, with the same folder `odrig`
and the same behaviour as the stick was to have. On 2026-10-22 the owner's photo showed
the reader: a SparkFun Shifting microSD board, a small adapter with level shifters that
takes 3.3 V. The owner wired it and reported the wiring complete:

| The reader | The board |
|---|---|
| SCK | GPIO39 |
| DO (MISO) | GPIO40 |
| DI (MOSI) | GPIO41 |
| CS | GPIO42 |
| VCC | 3V3 |
| GND | GND |
| CD | not wired |

What Codex built, each in its commit on `codex/microsd-storage`:

- `d5bcef6`: the card is read over SPI with Arduino's `SD` library when the firmware is
  built with the flag `ODRIG_DRIVE_SD_SPI`; the pins and the clock come from
  `firmware/usermod/odrig_sd_config.h`, whose defaults name no pin, so a build without the
  four pin flags touches none. In that build the USB host is not compiled and the board's
  own socket stays a serial port. `build --microsd` builds the variant on the newer
  software, as `odrig-microsd.bin`. Tests of the tool and of the card code, compiled on
  the Mac with a stand-in card.
- `551a52b`: the environment `odrig_microsd` names the four pins, GPIO39 to GPIO42, and
  a test checks that none of them is one of the twenty LED outputs or a USB pin.
- `5b4b4e9`, `b1fbec5`: the image built, 1,765,808 bytes, and its checks.
- `4217f91`, 2026-10-22: the first trial on the board. The owner authorised the flash;
  the card was mounted, its first two files were listed as 60001 and 60002, and
  `play 60001` played at 41 refreshes a second. Then entries that were already listed
  disappeared and were found again, in one open session: the card dropped out. Slower
  clocks, 1 MHz and 400 kHz, dropped out as well. The clock went back to 4 MHz, and the
  board was left on that image, SHA-256
  `fd089753d86c92d9cbfbb2e4823d49428e4b037213b656736636b9dd9a1950a5`.
- `d7f0120`, 2026-10-23: the second look, with both USB sockets of the board on the Mac
  and the commands sent through the socket marked COM. All 122 animations of the owner's
  card, 16,475,328 bytes, were listed as 60001 to 60122 after the installed one, 123 items
  in all; over fifteen minutes and 161 samples no entry was lost. Four of them, the
  largest and the last among them, played past a loop boundary at 26 to 50 refreshes a
  second, and the playlist went on to the card's animations by itself. Why the first day
  dropped out and the second did not is not known: the second cable is the one difference
  that was seen, and it is not shown to be the cause.
- `40cc3a9`, `533ceb8`: twenty-one small test animations of lines, `lines-test` and
  `rainbow-lines-01` to `-20`, with their generators, for the owner to see the strips.

The owner's two decisions about the card are in `docs/decisions.md`, under 2026-10-21 and
2026-10-22; `docs/microsd.md` and `docs/microsd-preflight/` are Codex's pages about it.
On 2026-10-24 the board was given back its 84 installed animations and runs this
firmware, healthy, with no card and no LEDs attached during that session.

## Technical Constraints

- The card is read and never written or formatted. Nothing is installed from it into the
  board's storage, and no command changes it.
- The core stays the one player and is not changed: the firmware tells it of the card's
  files and reads them for it, as the stick's code did, through the same host functions.
  The emulator's folder stands in for the card as it stood in for the stick.
- The same behaviour as seed 20 gives the stick: the folder `odrig` at the top of the
  card, `.odrg` files in the order of their names, at most 256, ids from 60001 up that
  are the same every time for the same files, the animations after the installed ones in
  the playlist, `list`, `play <id>`, `status` and `space` as they are. No command is
  added and no reply gains a member unless the owner approves it.
- The reader is on GPIO39 to GPIO42 only, at 3.3 V, and the twenty LED outputs stay on
  pins 1 to 18, 21 and 47. The SPI clock is 4 MHz, `ODRIG_SD_FREQUENCY` of
  `odrig_sd_config.h`; the firmware refuses a clock below 400 kHz or above 20 MHz and
  any pin outside 39 to 42. Nothing is soldered, and the wiring and the power are the
  owner's.
- The reader's card-detect line is not wired. The firmware finds a card by trying to
  mount it once a second while none is mounted, and notices that a card went by reading
  its first sector once a second and by a read of a file that fails. A card that went
  has its animations dropped and its files closed before the next try.
- The microSD build is a variant beside the firmware, built only by the tool: `build`
  goes on building the firmware with the stick's code on the software known good, and
  `build --microsd` builds the card's firmware on the newer software, in the same folder
  `build/firmware/newer/` as `build --trial`. Which one the installation runs at the
  event is the owner's, see the open questions.
- What this seed adds to the firmware gets its line in
  [firmware-additions.md](../../docs/firmware-additions.md), and by the owner's rule of
  2026-10-16 the fallback of seed 12 gets the card too.
- Any refresh rate from 20 to 50 a second on the board is acceptable, also while a file
  of the card plays. On the board the brightness stays at 40 or less, one program uses
  the board at a time, and the flash is never erased whole.
- The board is flashed and tried only in a board session with the owner. This seed's
  tasks that need no board run without one.

## Required Behavior

1. `python3 firmware/fw.py build --microsd` builds `build/firmware/out/odrig-microsd.bin`
   on the newer software, with its SHA-256 beside it, without touching `odrig-firmware.bin`
   or anything of the build known good; it goes with none of `--stock`, `--probe`,
   `--trial` and `--standalone`.
2. With a card in the reader whose file system the chip's software reads, FAT32 as a
   card comes, and a folder `odrig` at its top, the firmware lists the `.odrg` files of
   that folder for the core as seed 20 has it, and the core plays them after the installed
   ones with ids from 60001 up. `list` shows them, `play <id>` plays one, `status` names
   it, and `space` reports the card under `external`.
3. The board's own USB socket is a serial port in this build, for commands and for
   flashing, whatever is plugged into it, and the socket marked COM as well.
4. A card put in while the board runs is taken up within a few seconds without a
   restart. A card pulled out is dropped: its animations leave the playlist and `list`,
   the installed show goes on, and when one of the card's animations was playing the
   playlist moves on. The card put back is taken up again.
5. The log on the socket marked COM has a line for each event of the card: opened with
   the number of its animation files, no folder `odrig`, not mounted, gone, and the
   reader not started; and the player's line for every file left out, with the reason.
6. WLED's information says what there is of the card under `odrig drive`.
7. The four pins and the twenty LED outputs never overlap; a build that names no pins
   starts no reader and says so in the log.
8. The refresh rate stays from 20 to 50 a second while a file of the card plays.
9. The documents say how to prepare a card, how the reader is wired, how the variant is
   built and flashed, what the log says, what was seen on the board, and what is open.

## Definition Of Done

1. Every suite that needs no board passes, and the firmware tool's suite covers the
   variant, its pins and the card code compiled with a stand-in card.
2. `build` and `build --microsd` both build on the first computer, and the documents
   record the images' sizes and hashes.
3. On the board, in a session with the owner: the card's animations are listed after the
   installed ones over the socket marked COM and over Wi-Fi; the card is pulled out while
   one of its animations plays and the playlist goes on with the installed ones; the card
   is put back and its animations return; `status` reports 20 to 50 refreshes a second
   while a file of the card plays; and the board answers on both USB sockets. Whether the
   dropouts of 2026-10-22 come back with one cable is tried and recorded.
4. The owner sees the card's animations on the LEDs, and sees them while the board runs
   without a computer.
5. `docs/firmware.md`, `docs/firmware-additions.md`, `docs/firmware-prerequisites.md`,
   `docs/microsd.md` and `AGENTS.md` say what the card is and how far it has come.
6. Afterwards the board is left playing its show, at a brightness of 40 or less.

## Open Questions

The owner asked on 2026-10-24 that this seed be specified without a question pass.
Questions 1 to 6 were therefore decided by the agent, and each decision is recorded at
the end of [drifts.md](../../docs/drifts.md) under "Seed 38". Questions 7 and 8 are the
owner's, about the hardware and about what the installation runs; the work goes on
without them, and the tasks that need them come last.

1. Which file systems of a card does the firmware promise to read?
2. Does the emulator change for the card?
3. What becomes of Codex's pages, `docs/microsd.md` and `docs/microsd-preflight/`?
4. Does this seed solve the dropouts of 2026-10-22, or only find out whether they
   are still there?
5. What is the seed's state when it is added, given that its first tasks were done
   before it existed?
6. Do the stick's code and the hub's trial stay in the firmware's sources?
7. **The owner:** which socket powers the board at the event, the chip's own or the one
   marked COM, and is a computer on it? The first trial, with the Mac on the chip's own
   socket only, lost the card; the second, with both sockets on the Mac, did not. The
   check with one cable follows the answer.
8. **The owner:** once the board checks pass, does the microSD build become the firmware
   that `build` makes, with the stick's build kept behind an option, so that the
   installation runs one firmware and the fallback of seed 12 follows it? Until then
   `build --microsd` stays a variant.

## The Owner's Answers

On 2026-10-24, decided under the owner's mandate for the run of that day, which has every
open question of seeds 28 to 39 answered and recorded rather than asked:

7. The firmware must work with one cable or with two: with the board powered through
   either USB socket, with or without a computer on the other. The board session checks
   the two-cable arrangement of today, both sockets on the Mac, for the dropouts; one
   cable is not a separate condition of this seed.
8. Yes. Once the card is the external storage, `python3 firmware/fw.py build` makes the
   microSD firmware on the newer software, and `build --probe` its probe build. The USB
   stick's build stays available under an option of its own, on the software known good.
