# Design: one USB port for a computer or a stick

## Overview

`OdrigDrive::begin()` no longer switches the port to host mode at once. It starts the
task of the drive, which first looks for a computer on the port: the chip's unit for
serial and JTAG counts the start-of-frame packets a USB host sends, one each millisecond.
When the count moves during the wait, a computer is there, and the task ends without
touching the port. When it does not, the task installs the USB host and the driver of
flash drives, as seed 20's firmware does at once today.

## What this design relies on

- The chip's unit for serial and JTAG serves the port from the start, before the usermod
  runs, and a computer has enumerated it by then. The unit keeps the frame index of the
  last start-of-frame packet in `USB_SERIAL_JTAG.fram_num.sof_frame_index`, and sets the
  raw interrupt bit `USB_SERIAL_JTAG_INTR_SOF` at each one (`hal/usb_serial_jtag_ll.h`).
- A powered adapter or hub with a stick sends no start-of-frame packet: it is no host.
- WLED calls a usermod's `readFromConfig` with its object of `/cfg.json` at the start and
  after its settings page is saved, and `addToConfig` when it writes `/cfg.json`. Its
  page "Usermods" shows and edits what `addToConfig` writes.
- The drive's host functions are given to the core at its start; they answer "no drive"
  until a stick is mounted (seed 20).

## The firmware

`odrig_drive.cpp`:

- `COMPUTER_WAIT_MS = 5000`, the default of the wait, and `MOST_WAIT_MS = 60000`.
- `OdrigDrive::setWait(ms)`, called by the usermod with the setting before `begin()`.
- `begin()` makes what the drive needs, as today, and starts the drive's task; `withDrive`
  gives the core the drive's functions whatever the task finds.
- The task: it clears the raw SOF bit, then looks every 10 ms until the wait is over. A
  SOF seen ends the look with `computer`. Otherwise it installs the USB host, its task and
  the driver, and goes on as the drive's task does today. With a wait of 0 it does not
  look.
- `summary()` says `computer` in the first case.

`odrig_usermod.cpp`:

- `addToConfig`: `"odrig": {"computer_wait_s": <s>}`.
- `readFromConfig`: takes `computer_wait_s` when it is a whole number from 0 to 60, and
  leaves 5 otherwise; returns whether the member was there, as WLED asks. The value read
  at the start is the one `begin()` uses; a change on WLED's page takes effect at the next
  start, which the page says WLED does after a save.

The probe build keeps the port a serial port, as today.

## Tests

`tests/firmware/`: the constant and the range, the look before `usb_host_install`, the
SOF bit read through the unit's low-level header, the task started in `begin()` and not
the host, the settings' member and its range, `computer` in the summary, and the header
in the list of what `odrig_drive.cpp` may include.

`tests/board/`: a test that the port answers `status` when the board was started with
the Mac on it, run by the board's suite as it runs there today. The other way, without a
computer, is the owner's: it needs the Mac on the serial chip's port and a look at WLED's
information.

## Documents

`docs/firmware.md`: the port's two ways, the wait and where to change it, and what the
owner does: to use the port for commands, plug the computer in before power or press
reset; for a stick, start the board without a computer there. `docs/drifts.md` for what
comes up. `docs/decisions.md`, a line in its change log; `AGENTS.md`, the seed leaves
"What is coming"; the firmware's prerequisites, lines 12 and 15.

## What needs the owner

- The board with the Mac on the port as it starts, and once without: to see that the port
  answers, and that WLED's information says what it is.
