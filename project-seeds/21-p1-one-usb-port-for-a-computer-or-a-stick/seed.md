# One USB port for a computer or a stick

## Summary

The chip's own USB port is a serial port to a computer when a computer is plugged into
it, and the port of a USB stick otherwise. So the board talks to a computer on either of
its two USB ports again, as it did before the firmware of seed 20, and still reads a
stick on the chip's own port.

## Priority

- `P1`

## Depends On

- Seed 04, for the commands on the chip's own USB port.
- Seed 09, task 11, for the commands on the port of the serial chip.
- Seed 20, for the firmware that reads a stick on the chip's own port.

## Product Context

The board has two USB-C ports. One is the chip's own: until 2026-10-14 the firmware made
it a serial port, and a computer sent commands and flashed the board through it. The
other reaches the chip through a serial chip, and takes commands and flashing too.

Seed 20's firmware, flashed on 2026-10-14, switches the chip's own port to host mode at
every start, so that a stick can be read there. From then on a computer plugged into that
port sees nothing: the board and the computer are both hosts. On 2026-10-15 the owner
plugged the Mac into the port that had always worked, saw the board powered and not
answering, and called it a regression. The owner wants both ports to take a computer
again, and the stick to keep working.

The chip's own port can be one thing at a time: a serial port to a computer, or a host
for a stick. A computer that is plugged in shows itself on the port's wires within a
fraction of a second, which a stick and a hub do not. So the firmware can look before it
takes the port for a stick.

The board's suite, `fw.py test-board`, talks to the board on the chip's own port; seed
14's last task waits for it. This seed lets it run again.

## Technical Constraints

- Nothing is soldered. Which port powers the board is the board's wiring and the owner's.
- No command is added and no reply gains a member unless the owner approves it.
- The serial chip's port takes commands and flashing whatever the chip's own port is.
- The probe build keeps the chip's own port a serial port, as it does today.
- The stick's animations are read as seed 20 has it; this seed changes only when the
  port becomes the stick's.
- Any refresh rate from 20 to 50 a second on the board is acceptable. On the board the
  brightness stays at 40 or less, and the firmware is built only as the tool builds it.

## Required Behavior

1. When a computer is plugged into the chip's own port as the board starts, that port is
   a serial port that takes commands as it did before seed 20's firmware, and the board
   takes no stick there until the next start.
2. When no computer is there as the board starts, the port becomes the stick's port as
   seed 20 has it.
3. The serial chip's port takes commands in both cases.
4. WLED's information says which the chip's own port is: a computer's or the stick's.
5. The board starts playing as fast as today: looking for a computer does not hold back
   the LEDs.
6. The documents say how the board decides, and what the owner does to use either way.

## Definition Of Done

1. All test suites that need no board pass.
2. On the board, started with the Mac on the chip's own port, `status` answers on that
   port and on the serial chip's port.
3. On the board, started without a computer on that port, a stick there is read as seed
   20 has it, as far as the owner's hardware lets a stick be read.
4. The board's suite, `fw.py test-board`, runs with the Mac on the chip's own port.
5. Afterwards the board is left running the two-leg bench show, autostarting, at
   brightness 40 or less.

## Open Questions

1. Is the choice made only as the board starts, or also when a cable is plugged into the
   port later?
2. How long may the board look for a computer before it takes the port for a stick? A
   stick is read that much later.
