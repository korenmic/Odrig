# Requirements: animations from a USB drive

Seed: [`project-seeds/20-p1-animations-from-a-usb-drive/seed.md`](../../../project-seeds/20-p1-animations-from-a-usb-drive/seed.md).

A USB flash drive with a folder `odrig` of animation files is plugged into the board, and
the installation plays them, after the animations installed in the board's storage. The
emulator does the same with a folder of the computer that stands in for the drive.

The owner answered the seed's questions on 2026-10-14:

1. The animations of the drive are **added** to the installed ones in the playlist, after
   them. They do not take their place.
2. Their ids are the spec's to choose; they are kept apart from the ids of the show.
3. Nothing on the board is soldered. The board has two USB-C sockets: one is for power
   and the computer, the other for the drive, either way round as long as one works.
4. Settled by 3: the computer reaches the board over the socket marked COM, which takes
   commands and flashing since seed 09's task 11, while the drive is in the other one.

A trial on the board the same day switched the chip's own USB socket to host mode with the
drive plugged in: the host software started, and no device appeared. That socket gives a
plugged device no power by itself. The no-solder way, which this spec takes, is a small
USB-C adapter or hub with a power input of its own between that socket and the drive; it
is the owner's to provide.

In this document "the drive" is the drive that is plugged in, "its animations" are the
files of its folder `odrig` that pass the rules below, and "the host" is whoever runs the
core: the firmware, the emulator or the test host.

## Requirement 1: what is read of a drive

1. The host SHALL read a drive with a FAT32 or FAT16 file system and SHALL look only in
   the folder `odrig` at its top.
2. Of that folder it SHALL take every file whose name ends in `.odrg`, in any case, and
   does not begin with a dot, in the order of their names, at most 256 of them.
3. The drive SHALL be read only. Nothing SHALL be written to it, and no command SHALL
   change what is on it.

## Requirement 2: the animations of the drive in the show

1. The core SHALL read every file of the drive whole, with the check it makes after its
   start, after the installed files and while the show plays.
2. A file that is sound and made for the board's canvas SHALL become an animation of the
   playlist, after the installed animations and after the drive's animations before it,
   as soon as its check has ended. It SHALL have the turn of an animation of the show
   without `repeat` and `max_seconds`.
3. A file that is not sound, or is made for another canvas, SHALL be left out and named
   in the host's log with the reason. It SHALL NOT make the show invalid.
4. Each animation of the drive SHALL have an id: the lowest id from 60001 up that the show
   does not use and no animation of the drive before it has. The same files with the
   same show SHALL get the same ids every time.
5. `list` SHALL list them after the items of the show, each with its id, the name of its
   file on the drive and its size, as for an installed animation. A name SHALL be written
   so that the reply stays valid JSON.
6. `play <id>` SHALL play one of them as it plays an installed animation, and `status`
   SHALL name it while it is on the LEDs.
7. `remove <id>` and `upload begin <id> …` of one of them SHALL be refused with `in-use`.
8. A show without an animation of its own SHALL play the drive's animations.

## Requirement 3: plugging in and pulling out

1. A drive plugged in while the core runs SHALL be taken up without a restart: its files
   are checked and its animations join the playlist.
2. A drive pulled out SHALL be dropped without a restart: its animations leave the
   playlist and `list`. When one of them was playing, the playlist SHALL go on with the
   next animation that is left, from its first frame; with none left, nothing plays.
3. A file of the drive that cannot be read, or turns out not to be sound, while it plays
   SHALL be dropped in the same way, and the show SHALL stay valid.
4. A host without a drive SHALL behave as it does today.

## Requirement 4: the commands while a drive is checked

1. `list`, `remove` and `upload begin` SHALL answer as they do once the check after the
   start is complete, while the files of a drive are checked: the drive's animations
   that are not checked yet are not listed.
2. An upload SHALL wait for the second decoders: `upload end` answers `busy` while the
   drive's check holds them, and the drive's check waits while an upload is checked.
3. No command SHALL be added and no reply SHALL gain a member or an error code.

## Requirement 5: the core's limits

1. The core SHALL take no memory after its start. Its working memory for the 60 x 60
   canvas, with 100 items and room for 256 animations of a drive, SHALL stay under
   128 KB and be reported.
2. Any refresh rate from 20 to 50 a second on the board is acceptable, also while a file
   of the drive is read.

## Requirement 6: the hosts

1. The core's host interface SHALL gain what the core needs of a drive, and a host that
   gives none of it SHALL work as today.
2. The emulator SHALL take an option `--drive DIR`: the folder `DIR` stands for the top of
   a drive, and its folder `odrig` appearing and going while the emulator runs stands for
   plugging in and pulling out.
3. The firmware SHALL host the drive on the chip's own USB socket and SHALL keep taking
   commands on the socket marked COM and over Wi-Fi.
4. The test host SHALL be able to give the core a drive, to plug it in and pull it out at
   a moment of a script, and to make a file of it fail.

## Requirement 7: the board

1. The trial of the USB host SHALL be a build the firmware tool makes, and its finding
   SHALL be recorded: whether a drive answers, with the owner's adapter.
2. With the prepared drive and the adapter, `list` SHALL show the drive's animations after
   the installed ones, and `status` SHALL report each in its turn at 20 refreshes a second
   or more.
3. Pulling the drive out and plugging it in again SHALL be followed as Requirement 3 says.
4. The owner SHALL see the drive's animations on the LEDs. Only a person can make that
   check.
5. The board SHALL be left running the two-leg bench show, autostarting, at brightness 40
   or less.

## Requirement 8: tests and documents

1. Every suite that needs no board SHALL pass, and the emulator's suite SHALL cover the
   stand-in for the drive: found, left out, plugged in, pulled out.
2. The documents SHALL say how to prepare a drive, what the board does with it, and what
   the board needs for it: the adapter and the sockets.

## Left out on purpose

- Writing to a drive, and installing from it into the board's storage.
- Folders inside `odrig`, and files of other kinds.
- A show file on the drive: the drive gives animations, not a show.
- The phone talking to the drive.
