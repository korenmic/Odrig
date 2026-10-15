# Requirements: a USB stick through a hub

Seed: [`project-seeds/22-p2-a-usb-stick-through-a-hub/seed.md`](../../../project-seeds/22-p2-a-usb-stick-through-a-hub/seed.md).

The chip's own USB port gives a plugged device no power, so a stick needs a hub or an
adapter with a power input of its own between the port and the stick. On 2026-10-15 the
owner's stick, in such a hub, was not seen by the board: the firmware's USB software,
that of ESP-IDF 4.4, talks to one device plugged into the port directly and knows no hub.
This spec moves the firmware to a newer version of Espressif's software, whose USB host
has hubs, after a trial that shows whether WLED builds and runs on it.

The owner answered the seed's questions on 2026-10-16:

1. When WLED cannot move to the newer software, the seed stops, and the owner is told
   what the trial showed and decides then. Whatever the firmware gains, the fallback of
   seed 12 gains too. When the trial build makes the board behave worse than the
   firmware before it, the board is first flashed back to the last firmware known good.
2. Every hub must work, the owner's among them. The support is the generic one of the
   USB standard, with no code for a hub of one maker or model. A hub without power of its
   own cannot work on this board: the port gives it none.

In this document "the port" is the chip's own USB port; "the software known good" is
Arduino-ESP32 2.0.18 on ESP-IDF 4.4.8, on which the firmware is built today; "the newer
software" is Arduino-ESP32 3.3.12 on ESP-IDF 5.5.5, with the PlatformIO platform that
carries them; "the trial build" is the firmware built on the newer software for the
trial; and "the last firmware known good" is the image of the firmware that the board
runs before the trial.

## Requirement 1: the trial build, without the board

1. `python3 firmware/fw.py build --trial` SHALL build WLED 16.0.1 with the patches of
   `firmware/patches/`, the usermod and the core on the newer software, and keep the
   image as `build/firmware/out/odrig-trial.bin` with its SHA-256 beside it;
   `build --trial --probe` SHALL build its probe build, `odrig-trial-probe.bin`.
2. The newer software and the tools that build with it SHALL be kept in a folder of the
   work folder of their own, `build/firmware/newer/`; only pip's and npm's caches, which
   keep what was fetched, are shared. The trial build SHALL change nothing of the tools,
   the packages and the images of the software known good: `build`, `build --probe`,
   `build --stock` and `build --standalone` build as before.
3. Every package of the newer software that the tool names SHALL be pinned at an exact
   version, and `docs/firmware.md` SHALL list what the trial build fetches, with where
   it comes from, as it lists what the build known good fetches.
4. Nothing SHALL be fetched for the newer software before the owner has approved the
   list of what it fetches.
5. A change that WLED's source needs for the newer software SHALL be a patch file of
   `firmware/patches/` whose every change is held to the newer software by its version,
   so that the build on the software known good compiles as before. When WLED needs
   more, a change of its drivers of the LEDs, the Wi-Fi or the storage, or a library
   that has no version for the newer software, the trial SHALL stop there.
6. The image SHALL fit the application partition, 3,145,728 bytes.
7. Whether the trial build builds SHALL be recorded in `docs/firmware.md`, and when it
   does not, what stopped it.

## Requirement 2: hubs

1. On the newer software the firmware's USB host SHALL serve hubs by the hub class of
   the USB standard, as the host library of ESP-IDF does with its hub support switched
   on. No code SHALL name a maker or a model of hub, or treat one hub apart from another.
2. With any USB hub that has power of its own between the port and a stick, the stick's
   animations SHALL be listed and played as seed 20 has it.
3. A stick that has power from an adapter, without a hub, SHALL be read as well.
4. Plugging in and pulling out the hub or the stick SHALL be followed as seed 20 has it:
   when a hub goes, a stick behind it goes with it.
5. One stick is read at a time, as today: while one is read, another that comes is
   passed over until the first goes.

## Requirement 3: the log

1. The log of seed 23 SHALL have a line when a hub comes, as it has today:
   `a device came: maker <four hex digits>, product <four hex digits>, a hub`.
2. It SHALL have a line when a device goes that names it as its line of coming did:
   `a device went: maker <four hex digits>, product <four hex digits>, <kind>`, for a
   hub `a hub`. This holds for every device that came while the host ran, not only for
   the first.
3. On the newer software, the line of a device behind a hub SHALL say so, with the
   hub's port: `a device came: maker 0781, product 5581, a stick, on port 2 of a hub`.

## Requirement 4: everything else stays

1. On the newer software the firmware SHALL do everything it does today, as
   [firmware-additions.md](../../firmware-additions.md) lists it: the twenty outputs,
   a rate from 20 to 50 refreshes a second, the Wi-Fi network and WLED's page, the
   commands on both routes, the storage and the show, the look for a computer on the
   port, the log, the bigger layout and the refused update over Wi-Fi.
2. No command SHALL be added, and no reply SHALL gain a member.

## Requirement 5: the trial on the board

1. Before the board is touched, the image of the last firmware known good SHALL be kept
   with its SHA-256, so that it can be flashed back at once.
2. Without a hub, the trial build SHALL be flashed over the socket marked COM, and the
   board SHALL start; `status` SHALL answer with a rate from 20 to 50; the board's suite
   SHALL pass on the trial build and its probe build; the Wi-Fi network and WLED's page
   SHALL answer; and the twenty outputs SHALL carry their signal.
3. With the owner's hub, fed by its power bank, in the port and the owner's stick in the
   hub, the log on the socket marked COM SHALL show the hub, the stick on it, and the
   stick opened with its number of files, and `list` SHALL show the stick's animations.
4. When anything the firmware did before is worse with the trial build, the board SHALL
   be flashed back to the last firmware known good at once, and only then is the owner
   told what was found. The seed then stops until the owner decides.
5. What the trial showed on the board SHALL be recorded in `docs/firmware.md`: whether
   the trial build runs, and whether a hub and a stick are seen through it.

## Requirement 6: the move

1. Only after the trial passed on the board: `build` and `build --probe` SHALL build on
   the newer software, and `build --trial` and the board suite's run on the trial build
   SHALL go. `build --stock` SHALL stay on the
   software known good, on which stock WLED 16.0.1 is built.
2. The standalone firmware of seed 12 SHALL be built on the same newer software, with
   the same USB host library.
3. [firmware-additions.md](../../firmware-additions.md) SHALL have this seed's line: the
   firmware reads a stick through any USB hub that has power of its own, on the newer
   USB software, with its column "Seed 12" filled in.

## Requirement 7: tests and documents

1. The suite of the firmware tool SHALL check: the trial's environment and its pinned
   platform; the folder of the newer software, and that the trial changes nothing of the
   software known good; the USB host library with its hub support on; that no code of
   the firmware or of the library compares a maker's or a product's number; and the log's
   lines of a device that comes and goes.
2. Every suite that needs no board and no phone SHALL pass.
3. The documents SHALL name the hubs that were tried, the limits of the newer software
   that were found, and what the move to it changed: `docs/firmware.md`,
   `docs/firmware-prerequisites.md`, `docs/firmware-additions.md`, `AGENTS.md`, and a
   line in the change log of `docs/decisions.md`.
4. On the board, with the owner's hub fed by its power bank and the owner's stick in it,
   `list` SHALL show the stick's animations after the installed ones, and `status` SHALL
   report each in its turn at 20 refreshes a second or more; the owner sees them on the
   LEDs. Afterwards the board is left running the two-leg bench show, autostarting, at
   brightness 40 or less, on the newer firmware when the trial passed and on the last
   firmware known good when it did not.

## Left out on purpose

- A hub without power of its own: the port gives none, and only a change to the board's
  hardware, the owner's, would.
- More than one stick read at a time.
- Anything for a hub of one maker or model.
- A rebuild of the libraries of Arduino-ESP32 with ESP-IDF: the hub support comes with a
  USB host library of the firmware's own, as the design says.
