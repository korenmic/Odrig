# Design: a USB log on the serial port

## Overview

A new source of the usermod, `odrig_log.cpp`, keeps a small queue of log lines. Whoever
has something to say adds a line to it, from any task, without waiting: the drive's task,
the USB host's events, and the player's log function. The serial port's code, the one
source that names the UART, writes waiting lines in its loop, whole and between replies,
as far as the UART can take them without waiting. The command tool gets `--log`, which
prints what arrives that begins with `#log `.

## What this design relies on

- `OdrigUart::poll` runs in WLED's loop, writes each reply whole, and is the one place
  that writes to the UART (seed 09, task 11; a test of the firmware tool says so).
- The command tool takes a line as a reply only when it is a JSON object with `ok`, and
  passes over every other line, as the loader's lines at a start (seed 09).
- The USB host library lets a second client open a device beside the driver of flash
  drives, and read its descriptors; the trial of seed 20 did so.
- The player logs through its host's `log`, which `OdrigFiles` keeps for WLED's
  information.

## The log

`odrig_log.h`:

```cpp
namespace OdrigLog {
// Adds a line: its kind, as `usb` or `player`, and its text. From any task; it never waits.
void add(const char *kind, const char *text);
// The next line to write, with its line feed, into room for LINE_ROOM bytes, or 0.
size_t take(char *line, size_t room);
}
```

`odrig_log.cpp`: 32 lines of up to 160 bytes, a ring under a spinlock. A line is made at
`add`: `#log <s>.<ms> <kind>: <text>\n`, every byte of the text outside printable ASCII
as `?`, cut to fit. When the ring is full, the oldest line is dropped and a count is kept;
`take` gives `#log <s>.<ms> log: <n> lines dropped` first when the count is not 0.

`odrig_uart.cpp`: at each `poll`, before it reads what arrived, as long as the UART can
take a whole waiting line now (`availableForWrite`), it takes and writes it.

## What adds lines

- `odrig_drive.cpp`: the look for a computer (`usb: a computer is on the port, which
  stays a serial port` or `usb: no computer on the port within 5 s`); the host
  (`usb: host started`, `usb: host did not start: <error>`); a second client of the USB
  host, served in the host's task, which at a new device opens it, reads its device
  descriptor and the class of its first interface, and closes it
  (`usb: a device came: maker 0781, product 5581, a stick`, kinds `a hub` for class 9,
  `a stick` for class 8, `another device (class N)`), and at a device gone
  (`usb: a device went`); a stick (`usb: stick opened: 12 animation files in odrig`,
  `usb: stick not opened: <error>`, `usb: the stick has no folder odrig`).
- `odrig_usermod.cpp`: the player's `log` function is wrapped, so that every line the
  player logs goes to `OdrigFiles`' line, as today, and to the log as `player: <text>`.

The texts are the firmware's own; the Wi-Fi settings are read by no source of the log.

## The command tool

`odrigctl/cli.py`: `--log`, which goes with `--port` or `--tcp` and no command. It opens
the target as for a command, and prints each line that begins with `#log ` as it arrives,
until it is stopped; it sends nothing. Its exit status is 0 at an interrupt, and the
target's errors are those of a command.

## Tests

- `tests/firmware/`: the ring's size and form, `add` without waiting, `take` and the line
  of dropped lines, the UART's code writing between replies only after
  `availableForWrite`, the lines of the drive's code by their texts, the wrapper of the
  player's log, and no name of the Wi-Fi settings in the log's sources.
- `tests/emulator/`: `--log` against a target of the test's own on a pseudo-terminal and
  on TCP: it prints the log lines and only them, and sends nothing; the usage errors; a
  command whose reply comes after log lines takes the reply.
- `tests/board/`: none; the owner's check is the board's.

## Documents

`docs/firmware.md`: the log, its lines, how to read it with the tool or any serial
terminal at 115,200 bits a second. `docs/emulator.md`: `--log` of the command tool.
`docs/commands.md`, "Transports": a line on the serial port that begins with `#` is no
reply. `docs/decisions.md`, a line in its change log; `AGENTS.md`, the seed leaves "What
is coming"; the firmware's prerequisites.

## What needs the owner

- The board with the Mac on the serial port, plugging in the hub, an adapter and a stick,
  and reading the lines.
