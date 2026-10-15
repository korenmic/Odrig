# A USB stick through a hub

## Summary

The firmware reads a USB stick that is plugged into a hub, with the hub on the chip's own
USB port. A hub with a power input of its own gives the stick power, which the board's
port does not. For that the firmware's USB software moves to a version of Espressif's
software that knows hubs.

## Priority

- `P2`

## Depends On

- Seed 20, for the firmware that reads a stick on the chip's own port.
- Seed 21, when it is done, for the choice of what the chip's own port is.

## Product Context

The board's own USB port gives a plugged device no power: plugged in directly or through
a plain OTG adapter, a stick is not seen. On 2026-10-15 the owner put a stick into a hub
with a power input of its own, fed by a power bank, and plugged the hub into the board.
The stick's light was on, and the board still saw no stick: WLED's information said
`odrig drive: none`. The owner has no tools for soldering, and the hub is what the owner
has at hand.

The firmware is WLED 16.0.1, built on Arduino-ESP32 2.0.18 and ESP-IDF 4.4.8. The USB
host software of ESP-IDF 4.4 talks to one device plugged into the port directly; it
knows no hub. Newer versions of ESP-IDF, as far as is known from 5.5 on, have hubs, and
mark them as experimental. Whether WLED builds and runs on a version of the framework
that has them is not known: as far as is known, WLED does not run on it officially yet.

Without this seed, an OTG adapter with a power socket and only one USB-A socket, and no
hub inside, would give a stick power; the owner has none yet.

## Technical Constraints

- WLED stays the base of the firmware, as [decisions.md](../../docs/decisions.md) has it,
  unless the owner decides otherwise.
- Nothing is soldered, and the hardware is the owner's.
- The move to the newer software is tried before the rest is built, in the steps of
  "The trial" below. When WLED does not build or run on it, the seed stops there, and the
  owner is told what the trial showed and decides what comes next.
- Hubs are served by the USB standard's own hub support, which every hub follows: no code
  names a maker or a model of hub, or treats one hub apart from another.
- Everything the firmware does today stays as it is: the twenty outputs, the rates,
  the Wi-Fi network, the commands on both routes, the storage and the show.
- No command is added and no reply gains a member unless the owner approves it.
- Any refresh rate from 20 to 50 a second on the board is acceptable. On the board the
  brightness stays at 40 or less, and the firmware is built only as the tool builds it.
- What this seed adds to the firmware gets its line in
  [firmware-additions.md](../../docs/firmware-additions.md), and the fallback of seed 12 is
  built on the same USB software.

## The Trial

No simulator runs this: as far as is known, no simulator of the ESP32-S3 imitates its
USB port, and the emulator runs the core only, not the firmware. So the trial is made on
the board, and what it shows is what the board itself reports over the cable and over
its Wi-Fi.

1. **The build, without the board.** The tool builds WLED 16.0.1 with the usermod on the
   newer software. When it does not build, the trial ends here.
2. **Before the board is touched**, the image of the firmware on the board, the last one
   known good, is kept, so that it can be flashed back at once.
3. **The board, without a hub.** The trial build is flashed over the socket marked COM.
   Read over the cable and the Wi-Fi: it starts, `status` answers with a rate from 20 to
   50, the board's suite passes, the Wi-Fi network and WLED's page answer, and the
   twenty outputs carry their signal.
4. **The board, with the hub and the stick.** The owner plugs the hub, fed by its power
   bank, into the chip's own socket, and the stick into the hub. The log on the socket
   marked COM, of seed 23, says what the port sees: a hub, a device on it, a stick, the
   stick opened with its number of files. `list` then shows the stick's animations.
5. **The rollback.** When anything the firmware did before is worse in the trial build,
   the board is flashed back to the last firmware known good at once, and only then is
   the owner told what was found.

## Required Behavior

1. With any USB hub that has power of its own between the chip's own port and a stick,
   of any maker, the stick's animations are listed and played as seed 20 has it.
2. A stick that has power from an adapter, without a hub, is read as well.
3. Plugging in and pulling out the hub or the stick is followed as seed 20 has it.
4. The log of seed 23 has a line when a hub comes and when it goes.
5. The documents name the hubs that were tried, the limits of the newer software that
   were found, and what the move to it changed.

## Definition Of Done

1. All test suites that need no board pass.
2. The trial is recorded: whether WLED builds and runs on the newer software, and
   whether a hub and a stick are seen through it.
3. On the board, with the owner's hub fed by its power bank and the owner's stick in it,
   `list` shows the stick's animations after the installed ones, and `status` reports
   each in its turn at 20 refreshes a second or more.
4. The owner sees the stick's animations on the LEDs.
5. Afterwards the board is left running the two-leg bench show, autostarting, at
   brightness 40 or less, on the trial's firmware when it passed, and on the last
   firmware known good when it did not.

## Open Questions

None. The owner answered them on 2026-10-16, below.

## The Owner's Answers

On 2026-10-16:

1. When WLED cannot move to the newer software, the seed stops, and the owner is told
   what the trial showed and decides then. Whatever the firmware gains, the fallback of
   seed 12 gains too, whichever way that goes. When the trial build makes the board
   behave worse than the firmware before it, the board is first flashed back to the last
   firmware known good.
2. Every hub must work, the owner's among them: the owner's hub may be inside something
   else than it looks. So the support is the generic one of the USB standard, with no
   code for a hub of one maker or model. A hub without power of its own cannot work on
   this board: the chip's own port gives no power, so such a hub does not even switch on,
   and only a change to the board's hardware, the owner's, would give it power.
