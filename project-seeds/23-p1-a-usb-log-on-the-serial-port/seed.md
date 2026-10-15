# A USB log on the serial port

## Summary

The firmware writes a line of log on the port of the serial chip for every event of its
own USB port: a device came or went, what it is, whether a stick was opened and how many
animation files it has, and why a stick was not read. A computer on that port sees why a
stick is not read, without a special build.

## Priority

- `P1`

## Depends On

- Seed 09, task 11, for the commands on the port of the serial chip.
- Seed 20, for the firmware that reads a stick on the chip's own port.

## Product Context

On 2026-10-15 the owner tried a stick on the board in several ways: through a hub with
its own power, through a plain OTG adapter, on both of the board's ports. The board read
no stick, and the only sign was one word in WLED's information, `odrig drive: none`. It
does not say whether a device was seen at all, whether it was a hub or a stick, or why a
stick was not opened. Seed 20 planned a trial build that reports what the port sees; the
owner wants such a report to stay in the firmware itself, so that it is there whenever a
stick does not show up.

The serial chip's port carries commands. The chip's loader already writes lines there
at a start, and the command tool skips every line that is not a reply.

## Technical Constraints

- A line of log never breaks a command's line or a reply: it is written whole, between
  replies, and begins with a mark that tells it apart from a reply. The command tool
  goes on skipping it.
- No command is added and no reply gains a member unless the owner approves it.
- Writing the log never holds back the LEDs: any refresh rate from 20 to 50 a second on
  the board stays acceptable.
- The log names no secret: not the Wi-Fi password.
- The log goes to the serial chip's port only.
- On the board the brightness stays at 40 or less, and the firmware is built only as the
  tool builds it.

## Required Behavior

1. A line when the USB host of the chip's own port starts, or fails to.
2. A line when a device comes, with its maker's and its product's number and its kind:
   a hub, a stick, or another device. A line when it goes.
3. A line when a stick is opened, with the number of animation files of its folder
   `odrig`, or when it is not, with the reason: no file system that is read, no folder
   `odrig`, a fault in reading.
4. A line for every file of a stick that is left out, with its name and the reason.
5. The documents say how to read the log from a computer.

## Definition Of Done

1. All test suites that need no board pass.
2. On the board, with the Mac on the serial chip's port, plugging in and pulling out the
   owner's hub, an adapter and a stick each shows its lines, and commands on the same
   port are answered as before while the lines come.
3. Afterwards the board is left running the two-leg bench show, autostarting, at
   brightness 40 or less.

## Open Questions

1. Should the other lines the core logs, such as the reason a show becomes invalid, go
   to the same log?
2. Should the command tool print the log, or is a serial terminal enough?
