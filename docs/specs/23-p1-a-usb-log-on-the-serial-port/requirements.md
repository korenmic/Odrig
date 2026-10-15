# Requirements: a USB log on the serial port

Seed: [`project-seeds/23-p1-a-usb-log-on-the-serial-port/seed.md`](../../../project-seeds/23-p1-a-usb-log-on-the-serial-port/seed.md).

On 2026-10-15 a stick was not read on the board, through a hub and through a plain
adapter, and the only sign was one word in WLED's information. This spec gives the
firmware a log on the port of the serial chip: a line for every event of the chip's own
USB port, and the lines the player logs. The command tool shows it.

The owner answered the seed's questions on 2026-10-15:

1. The other lines the player logs, such as the reason a show becomes invalid, go to the
   same log.
2. The command tool can show the log: it prints the log's lines as they arrive, and no
   command is added to the board for it.

In this document "the log" is the lines the firmware writes, "the port" is the chip's own
USB port, and "the serial port" is the port of the serial chip, which takes commands.

## Requirement 1: what the log says

1. The firmware SHALL write a line when the drive's task has looked for a computer on the
   port, saying whether one was there.
2. It SHALL write a line when the USB host starts or fails to start, with the reason.
3. It SHALL write a line when a device comes, with its maker's and its product's number
   and its kind: a hub, a stick, or another device; and a line when it goes.
4. It SHALL write a line when a stick is opened, with the number of animation files of
   its folder `odrig`, and when it is not, with the reason: no file system it reads, no
   folder `odrig`, or a fault in reading.
5. Every line the player logs SHALL be a line of the log: a file of a stick that is left
   out with its name and reason, the reason a show becomes invalid.
6. The log SHALL name no secret: not the Wi-Fi password.

## Requirement 2: the log on the serial port

1. Each line SHALL begin with `#log `, then the seconds since the start with three
   decimals, the kind of the line and its text: `#log 12.345 usb: ...`. A line is one
   line of printable ASCII.
2. A line SHALL never break into a command's reply: it is written whole, between replies.
3. Writing the log SHALL never hold back the LEDs or the commands. When the serial port
   cannot take a line now, the line waits; when lines come faster than they can be
   written, the oldest waiting ones are dropped and a line says how many.
4. The log SHALL go to the serial port only.

## Requirement 3: the command tool

1. `python -m odrigctl --port NAME --log` SHALL print every line of the log as it arrives,
   until it is stopped, and send nothing to the target.
2. The tool's commands SHALL go on taking only replies as replies, whatever log lines come
   between them.
3. `--log` SHALL go with `--port` and `--tcp` only, and with no command.

## Requirement 4: tests and documents

1. The suite of the firmware tool SHALL check the sources: the lines of Requirement 1, the
   form of a line, that the log is written by the serial port's code between replies and
   never waits, and that nothing of the Wi-Fi settings is named in it.
2. The emulator's suite SHALL test the command tool's `--log`, with a target of its own.
3. On the board, with the Mac on the serial port, plugging in and pulling out the owner's
   hub, an adapter and a stick SHALL show their lines, while commands on the same port
   are answered. Only the board can show it.
4. Every suite that needs no board and no phone SHALL pass, and the firmware's page and
   the emulator's page SHALL say how to read the log.

## Left out on purpose

- A log over Wi-Fi.
- Keeping the log in the board's storage.
- The emulator's serial port: the emulator prints the player's lines with `--verbose`.
