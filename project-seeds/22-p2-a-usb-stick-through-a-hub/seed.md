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
- The move to the newer software is tried on the board before the rest is built: a
  build the tool makes, which reports what the port sees with a hub and a stick. When
  WLED does not build or run on it, the seed stops there, and the owner is told what
  the trial showed.
- Everything the firmware does today stays as it is: the twenty outputs, the rates,
  the Wi-Fi network, the commands on both routes, the storage and the show.
- No command is added and no reply gains a member unless the owner approves it.
- Any refresh rate from 20 to 50 a second on the board is acceptable. On the board the
  brightness stays at 40 or less, and the firmware is built only as the tool builds it.

## Required Behavior

1. With a hub that has its own power between the chip's own port and a stick, the
   stick's animations are listed and played as seed 20 has it.
2. A stick that has power from an adapter, without a hub, is read as well.
3. Plugging in and pulling out the hub or the stick is followed as seed 20 has it.
4. The documents name the hubs that were tried, and what the move to the newer software
   changed.

## Definition Of Done

1. All test suites that need no board pass.
2. The trial is recorded: whether WLED builds and runs on the newer software, and
   whether a hub and a stick are seen through it.
3. On the board, with the owner's hub fed by its power bank and the owner's stick in it,
   `list` shows the stick's animations after the installed ones, and `status` reports
   each in its turn at 20 refreshes a second or more.
4. The owner sees the stick's animations on the LEDs.
5. Afterwards the board is left running the two-leg bench show, autostarting, at
   brightness 40 or less.

## Open Questions

1. When WLED cannot move to the newer software, does the owner want the firmware without
   WLED of seed 12 to be moved instead, or an adapter with a power socket bought?
2. Must every hub work, or the one the owner has?
