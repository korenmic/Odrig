# Requirements: one USB port for a computer or a stick

Seed: [`project-seeds/21-p1-one-usb-port-for-a-computer-or-a-stick/seed.md`](../../../project-seeds/21-p1-one-usb-port-for-a-computer-or-a-stick/seed.md).

The board has two USB-C ports: the chip's own, and the one of the serial chip. Since the
firmware of seed 20, the chip's own port is the port of a USB stick from every start, and
a computer plugged into it sees nothing. This spec makes that port a computer's again when
a computer is there as the board starts, and the stick's otherwise.

The owner answered the seed's questions on 2026-10-15:

1. The choice is made as the board starts. When no computer shows itself, the port is the
   stick's until the next start, and a stick may be pulled out and plugged in again at any
   time, as seed 20 has it.
2. The board looks for a computer for 5 seconds. The time is a setting: a named constant of
   the firmware's source as its default, and a value in a settings file in the board's own
   storage, where the owner can see it and change it.

In this document "the port" is the chip's own USB port, "a computer" is anything that is a
USB host on the other end of the port's cable, and "the wait" is the time the board looks
for a computer.

## Requirement 1: the choice at the start

1. As the board starts, it SHALL look for a computer on the port for the time of the wait.
   A computer shows itself by the frames that a USB host sends to a device it serves,
   one every millisecond.
2. When it finds one, the port SHALL stay a serial port: it takes commands, as it did
   before seed 20's firmware, and the board takes no stick there until the next start.
3. When it finds none, the port SHALL become the stick's port, as seed 20 has it.
4. Looking for a computer SHALL NOT hold back the LEDs: the show plays from the start as
   it does today.
5. The port of the serial chip SHALL take commands in both cases.

## Requirement 2: the wait

1. The wait SHALL be 5 seconds unless the settings say otherwise, a constant of the
   firmware's source.
2. The board SHALL read the wait from WLED's settings file in its storage, where WLED's
   page shows the settings of the usermod and lets the owner change them, from 0 to 60
   seconds. A value that is missing or outside that range SHALL leave the default.
3. A wait of 0 SHALL make the port the stick's at once.

## Requirement 3: what the board tells

1. WLED's information SHALL say what the port is: `computer`, or what there is of a
   stick, as it says today.
2. The firmware's page SHALL say how the board decides, how long it waits, how to change
   the wait, and what the owner does to use the port either way.

## Requirement 4: the board's suite

1. The board's suite, `fw.py test-board`, SHALL run with a computer on the port as the
   board starts, as it did before seed 20's firmware.

## Requirement 5: tests

1. The suite of the firmware tool SHALL check the sources: the wait's constant and its
   setting, the look for a computer before the stick's host is started, and the
   information's line.
2. On the board, started with the Mac on the port, `status` SHALL answer on the port and
   on the serial chip's port. Started without a computer on the port, the port SHALL
   become the stick's after the wait, which WLED's information shows. Only the board can
   show both.
3. Every suite that needs no board and no phone SHALL pass.

## Left out on purpose

- Switching the port from a stick to a computer after the start.
- A command that tells what the port is: WLED's information tells it.
