# Animations from a USB drive

## Summary

A USB flash drive is plugged into the board, and the installation plays the animations
that are on it: the firmware mounts the drive, looks in one folder for animation files,
and takes them into the playlist. The emulator does the same with a folder of the
computer that stands in for the drive.

## Priority

- `P1`

## Depends On

- Seed 02, for the shared core, which plays a file whatever it is read from.
- Seed 04, for the firmware on the board.
- Seed 16, for the playlist that the animations of the drive are played in.
- Seed 14, which checks installed animations while the show plays: an animation of the
  drive is checked in the same way and not before the LEDs light.

## Product Context

Today an animation gets onto the board in two ways: a show is installed over the USB
cable with the firmware tool, or one animation is uploaded with the commands, over the
cable or over Wi-Fi. Both need a computer or the app, and the storage of the board holds
about 10 MB.

On 2026-10-14 the owner asked for a third way: a USB flash drive with a folder of
animation files is plugged into the board, and the board plays what is on it. Whoever
has made animations hands over a drive; nobody needs a cable to a computer or the
network's password.

A drive was prepared for this work: a Kingston DataTraveler of 124 GB with one partition
in FAT32 under a classic partition table, as it came, and one folder `odrig` at its top
with three animations for the canvas of the bench build, 60 x 6: `hello.odrg`,
`dvd.odrg` and `dense.odrg`. It was not formatted: FAT32 is what the chip's software
mounts. A Mac leaves hidden folders at the top of such a drive, and beside a file it
writes there a second file whose name begins with `._`; those of the folder were
removed, and the firmware has to pass over such names.

What is known and what is not:

- The ESP32-S3 can be a USB host, and Espressif's software has a driver for flash drives
  and mounts FAT file systems. Nothing of it is in the firmware today, and it has not
  been tried on this board.
- The board talks to a computer over the same USB port, with the chip's unit for serial
  and JTAG. That unit and the USB host share the port's two wires: while the board hosts
  a drive, it is not a serial port to a computer on that port. Commands over Wi-Fi are
  not touched by that.
- A flash drive takes its power from the port. Whether this board's port gives 5 volts
  to what is plugged into it is a question of its wiring, and that is the owner's.
- The firmware is WLED with our addition. Whether the USB host software can be built
  into it as the tool builds it is to be found out before anything else.

## Technical Constraints

- What reads a drive is the host's: the firmware's, or the emulator's stand-in. The core
  stays the one player: it is told of the files and reads them through its host, and the
  emulator and every firmware behave alike.
- The drive is read and never written. Nothing is installed from it into the board's
  storage, and no command changes what is on it.
- No command is added and no reply gains a member unless the owner approves it. The seed
  is to be met with the commands that exist: `list` shows the animations of the drive
  with ids of their own, `play <id>` plays one, and `status` names it.
- An animation of the drive never makes the show invalid. A file that is no animation,
  that is for another canvas, or that is damaged is left out, and a drive that is pulled
  out while one of its animations plays ends that animation's turn and nothing else.
- The core takes no memory after its start and stays under its limit of working memory;
  how many animations of a drive it has room for is a fixed number that the documents
  name.
- Any refresh rate from 20 to 50 a second on the board is acceptable, also while an
  animation is read from the drive.
- Hardware and power are the owner's: the spec names what the owner has to provide or
  decide, and no agent changes the board's wiring.
- The assumptions about the chip's USB host inside the WLED-based firmware are settled
  by a trial on the board before the rest is built, as the standalone firmware's were.
- Tests that need the board, and those that need a drive, are kept apart from those that
  need neither. On the board, brightness stays at 40 or less.

## Required Behavior

1. With a drive plugged in that has a FAT32 file system and a folder `odrig` at its top,
   the firmware finds every file of that folder whose name ends in `.odrg` and does not
   begin with a dot, in the order of their names. It looks into no other folder.
2. Each such file that is a sound animation for the board's canvas is an animation of
   the playlist, after the installed ones, with an id of its own that is the same every
   time for the same set of files.
3. The animations of the drive are played in turn like installed ones, with the turn the
   playlist gives an animation that has no numbers of its own.
4. `list` shows them, `play <id>` plays one, and `status` names the one on the LEDs.
5. A file that is left out is named in the firmware's log with the reason.
6. A drive plugged in while the board runs is taken up without a restart, and a drive
   pulled out is dropped without one: its animations leave the playlist, and what is
   installed goes on playing.
7. A board without a drive behaves as it does today.
8. The emulator takes an option that names a folder to stand in for the drive, and
   behaves as the board does with a drive that has that folder's files; the folder
   appearing and going while the emulator runs stands for plugging in and pulling out.
9. The documents say how to prepare a drive, what the board does with it, and what the
   board needs for it.

## Definition Of Done

1. All test suites that need no board pass, and the emulator's suite covers the stand-in
   for the drive: found, left out, plugged in, pulled out.
2. A trial on the board has shown, and the documents record, whether the WLED-based
   firmware can host a flash drive, how the drive is powered, and what becomes of the
   serial port.
3. On the board, with the prepared drive plugged in, `list` over Wi-Fi shows the three
   animations of the drive after the installed ones, and `status` reports each of them
   in its turn, at 20 refreshes a second or more.
4. Pulling the drive out and plugging it in again, on the board, is followed as the
   required behavior says.
5. The owner sees the animations of the drive on the LEDs.
6. Afterwards the board is left running the two-leg bench show, autostarting, at
   brightness 40 or less.

## Open Questions

1. Do the animations of the drive join the installed ones in the playlist, as this seed
   says, or take their place while a drive is plugged in?
2. Which ids do they get? This seed leaves it to the spec, which keeps them apart from
   the ids of installed items.
3. The power for the drive and the port it is plugged into are the owner's to decide,
   once the trial on the board has shown what the board gives.
4. While the board hosts a drive, a computer cannot reach it over that USB port. Is
   flashing and installing over the cable, with the drive pulled out, acceptable for the
   event?
