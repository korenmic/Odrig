# Design: animations from a USB drive

## Overview

The host knows the drive: whether one is plugged in, and the names of the animation files
of its folder `odrig`. The core asks it at its refreshes, reads each file through the host
as it reads an installed one, checks it with the check it makes after its start, and adds
each sound file to the playlist as soon as its check has ended. A drive's animation is an
item of the core's own, not of `show.json`: it has an id from 60001 up, is listed after
the show's items, and goes when the drive goes. The emulator stands a folder of the
computer in for the drive, the test host a set of files in memory, and the firmware the
drive on the chip's own USB socket.

## What this design relies on

- The core reads files only through its host, by name, with `open`/`read`/`close` for the
  player and `read_at` for the check, and both may be open at once.
- The check after the start has the second decoders, reads one file after the other in
  steps, and notes each file's size and length when it has read it whole (seed 14).
- The playlist is the animation items of the show in order; a turn without `repeat` and
  `max_seconds` lasts the fewest loops that make `min_seconds` (seed 16).
- The core's working memory for the target with 100 items is 124,549 bytes of the 131,072
  it may use (seed 14).
- The board's socket marked COM takes commands and flashing (seed 09, task 11). The
  chip's own socket can be switched to host mode by the USB host library of ESP-IDF
  4.4.8, which the firmware's framework holds; a trial on 2026-10-14 started it and saw
  no device with the drive plugged in directly.

## The host interface

Two members are added at the end of `odrig_host`. A host that leaves them NULL has no
drive, and the core behaves as today.

```c
/* A drive of animations. A host without one sets drive to NULL. */

/* The number of the drive that is plugged in now: a number other than 0 that changes
   each time a drive is plugged in, or 0 while none is. Called at refreshes. */
uint32_t (*drive)(void *ctx);

/* The name of the animation file at this place of the drive's list, as the drive has it,
   into buffer with a 0 after it, cut to capacity - 1 bytes. Returns 1, or 0 when that
   drive has no file at that place or is not plugged in any more. */
int (*drive_name)(void *ctx, uint32_t drive, uint32_t place, char *buffer, size_t capacity);
```

The host makes the list: the files of `odrig` whose names end in `.odrg`, in any case, and
do not begin with a dot, in the order of their names, the first 256. The core names the
file at place `p` as `drive/p` to `open` and `read_at`; no name of an installed file has a
slash. A host that gets such a name for a drive that is gone answers as for a file that is
not there.

## The core

**What it keeps.** When the host has a drive, the core takes at its start a table of 256
entries: for each place of the drive's list its id, its size, its length in milliseconds
and its state, which is "to check", "in the playlist" or "left out". Twelve bytes an entry,
3,072 in all, and nothing else: the name is asked of the host when `list` needs it. The
number of the drive the table holds is kept beside it.

**Plugging in and pulling out.** At each refresh, before the picture is made, the core asks
`drive`. When the number differs from the one it holds, it drops the old drive's entries
and, for a number other than 0, counts the new drive's files with `drive_name` and marks
them "to check". An animation of the old drive that was playing ends its turn: the
playlist goes on with the next animation that is left, from its first frame, or with
nothing.

**The check.** After the installed files, the check after the start goes on with the
drive's files "to check", in the order of their places, at the same pace. The installed
check is the one that makes `list`, `remove` and `upload begin` answer `busy`; the drive's
does not. A file that is sound and of the canvas gets its id and the state "in the
playlist"; one that is not is "left out", and the reason goes to the host's log as
`drive file <name> left out: <reason>`. While an upload is open, the drive's check waits:
the upload's check has the second decoders.

**Ids.** An entry that joins the playlist takes the lowest id from 60001 up that no item
of the show has and no entry before it has. Places are in the order of names, so the same
files with the same show get the same ids.

**The playlist.** A position in the playlist is an item's position as today, or, from the
number of items on, an entry of the drive. `next_animation` walks the show's animations
and then the drive's entries "in the playlist". The turn of a drive's animation is that of
an animation without `repeat` and `max_seconds`. `play <id>` finds an id among the show's
items and then among the drive's entries. `status` names the id of the entry on the LEDs.

**Faults while playing.** A drive's file that cannot be opened or read, or that turns out
not to be sound while it plays, is "left out" from then on; its turn ends there, and the
show stays valid. An installed file does what it does today.

**`list`.** The show's items, then the drive's entries "in the playlist", each as
`{"id":N,"file":"<name>","bytes":N}`. The name is asked of the host and written as a JSON
string: `"` and `\` escaped, a byte below 32 as `\u00XX`, every other byte as it is. An
entry whose name the host cannot give any more is not listed. Paging with `next` counts
both kinds of item.

**`remove` and `upload begin`** of a drive's id answer `in-use`: the drive holds that item.

**Memory.** The table is taken only from a host with a drive: 3,072 bytes more, 127,621 for
the target with 100 items. A host without a drive takes what it takes today.

## The test host and the reference player

The test host gets options for a drive: `--drive DIR` holds the files of a folder as the
drive's, and script lines `drive plug <ms>` and `drive pull <ms>` change the drive at a
moment; `--drive-read-fails NAME OFFSET` makes a file of it fail. The reference player
gets the same drive and follows this design: what it checks, which ids it gives, what it
lists and plays, and what a pull does.

## The emulator

`python -m emulator SHOW_DIR --drive DIR`: `DIR` stands for the top of the drive. The
emulator's host looks for `DIR/odrig` once a second; when the folder appears, the drive's
number goes up by one and its list is made; when it goes, the number is 0. The list is made
when the folder appears and not again while it stays, as a drive's files do not change
while it is plugged in. Files are read with `open` and `read_at` as installed ones are. The
page's header names the drive's folder when there is one.

## The firmware

**The trial.** A build the tool makes, `fw.py build --probe` with the trial in the probe's
code, switches the chip's own socket to host mode and reports over the UART, in lines
`#usb {...}`, whether a device came, its vendor and product, and the class of its first
interface: 8 is a flash drive. The trial of 2026-10-14 saw none with the drive plugged in
directly. With the owner's adapter, which gives the drive power of its own, the trial is
run again; it is what tells whether the rest of this firmware work can go on.

**The drive.** The USB host library and a driver for flash drives: the mass storage class
driver that ESP-IDF 4.4 gives as an example component, built into the usermod, and FAT on
it through the file system layer of ESP-IDF, mounted at `/usb`. A task of the usermod
waits for a drive, mounts it, makes the list of `/usb/odrig`, and raises the drive's
number; when the drive goes, it unmounts it and sets the number to 0. The host's `open`
and `read_at` read `drive/p` from the file at place `p`.

**What changes for the computer.** While the chip's own socket hosts the drive, it is no
serial port to a computer. The computer uses the socket marked COM, which the firmware
already serves. The tool's port is that one when the board has a drive.

## Tests

- `tests/core/`: a drive's files found in name order and the hidden and other files passed
  over by the host, checked after the installed ones, joined one by one, with their ids,
  listed after the show with names that need escaping, played in the playlist and by
  `play`, named by `status`; a file of another canvas and a damaged one left out and
  logged; plugged in and pulled out while one plays; a read that fails while one plays;
  `remove` and `upload begin` of a drive's id; an upload while the drive is checked; the
  memory with and without a drive; a host without the two members.
- `tests/emulator/`: the option, a folder found, left out, appearing and going.
- `tests/app/`: an emulator with a drive: its animations are rows and play.
- `tests/firmware/`: the usermod's drive code keeps to its sources' rules.
- `tests/board/`: as Requirement 7 has it, skipped without a drive.

## Documents

`docs/core.md`, `docs/commands.md`, `docs/show.md`, `docs/emulator.md`,
`docs/firmware.md` with a section on preparing a drive and on the adapter and the sockets,
`docs/android-app.md`, `docs/decisions.md`, `AGENTS.md`.

## What needs the owner

- The adapter: a USB-C adapter or hub with a power input of its own, between the chip's
  own socket and the drive.
- A yes for the download of the mass storage driver's sources from ESP-IDF, before the
  firmware task: its files, their source and their size are named when it is asked.
- The look at the LEDs with the drive plugged in.

## Risks

- **The drive is not seen with the adapter either.** Then the firmware tasks stop, and the
  owner is told what the trial showed. The core's and the emulator's work stands.
- **Memory of the firmware.** The USB host and FAT take memory outside the core's; the
  firmware's free memory is measured with a drive and recorded.
- **Rate.** A file read from a drive while the show plays may be slower than one read from
  the board's storage; the board test measures the rate.
