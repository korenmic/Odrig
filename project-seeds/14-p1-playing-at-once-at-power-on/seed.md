# Playing at once at power-on

## Summary

At power-on the installation shows its start item at once and checks the installed
animations while it plays. Today the LEDs stay dark, and the board answers nothing, until
every installed animation has been decoded once.

## Priority

- `P1`

## Depends On

- Seed 02, for the shared core, which does the check at start.
- Seed 04, for the firmware that hosts the core on the board.
- Seed 07, for the check of a file that runs beside playback, built for uploads.

## Product Context

When the core starts it checks every animation of the show by decoding it from its first
frame to its last. Nothing plays and no command is answered until that is done.

Measured on the board: 215 ms for the demo show, 6.1 seconds for one dense 60 x 60 clip
of 10 seconds, and 39 seconds for a storage filled with 9 MB of such clips. For that time
the LEDs are dark, the board answers nothing on USB or on the network, and its Wi-Fi
network is not up yet.

At the event the power can drop, and a board can be restarted on purpose. The more
animations are installed, the longer the installation then stays dark. The owner wants the
start item to play at once and the other files to be checked in the background.

Seed 07 gave the core a way to check one file while another plays: one frame of the
checked file after each refresh, giving way when playback is late. It is used for an
uploaded file. The same means can check the installed files after the start.

A file that turns out to be damaged while it plays already makes the show invalid from
that moment on. So a fault that is found after the start has a defined result.

## Technical Constraints

- The change is in the shared core, so the emulator and every firmware behave alike.
- The core takes no memory after its start, and its working memory for the 60 x 60 canvas
  with 100 items stays under 128 KB. It is at 124,501 bytes today, so the check after the
  start uses the memory that the check of an upload already has.
- No command is added, and no reply gains a member or a new error code. `busy` is an
  error code that `remove` and `upload begin` already give.
- A show that is valid today stays valid, and a show that is refused today is still
  refused, with the same reason. Only the moment at which a damaged animation is found
  changes.
- Playback comes first: the check gives way whenever a refresh is late.
- Any refresh rate from 20 to 50 a second on the board is acceptable.
- Tests that need the board are kept apart from those that do not. On the board,
  brightness stays at 40 or less.

## Required Behavior

1. At its start the core reads `mapping.json` and `show.json` and, of every animation the
   show names, the header only: that the file is there, that it is an ODRG file, and that
   its canvas is the mapping's. A fault found there makes the show invalid at once, with
   the reason it has today.
2. Then the LEDs are switched on and the start item plays, if the show has one. The time
   from power-on to the first frame does not grow with the size of the installed files.
3. While the show plays, the core checks the body of every installed animation, one after
   the other, in the order in which the show first names them. This is the check after
   the start.
4. A fault that the check after the start finds makes the show invalid from that moment
   on, as a file that fails while it plays does today: the LEDs go dark, and `status`
   gives the reason.
5. While the check after the start runs:
   - `play`, `on`, `off`, `brightness`, `status` and `space` work as ever. An item can be
     played before its file has been checked.
   - `list`, `remove` and `upload begin` are answered with `busy`: the size of a file is
     known only when it has been read to its end, and the check of an upload uses the
     same memory.
6. When the check after the start is complete, every command works as it does today, and
   `list` reports the size of every file.
7. A host whose storage cannot be changed has no second reader for a file. With such a
   host the core checks every file before it plays, as today.
8. The firmware tool waits for the check after the start to be complete before it reports
   that a show was installed, and reports a show that turned invalid as a failure.
9. `docs/core.md`, `docs/show.md`, `docs/commands.md`, `docs/emulator.md` and
   `docs/firmware.md` describe the start as it is.

## Definition Of Done

1. All test suites that need no board pass.
2. In the emulator, with a show of one small start item and dense animations of 60
   seconds in all, `status` reports the start item playing in the first second after the
   start, `list` is answered with `busy` then, and later with the size of every file.
3. A show with a damaged animation that is not the start item plays its start item, and
   then becomes invalid with the reason that the same show is refused with today.
4. The core's measured working memory for 60 x 60 with 100 items is under 128 KB and is
   reported.
5. On the board, with the storage filled with 9 MB of dense clips and a small start item,
   the time from a restart to the first reply of `status` is within one second of that
   time with the demo show alone, and that reply reports the start item playing. Both
   times are reported.
6. On the board, `status` reports 20 or more refreshes a second while the check after the
   start runs, with the demo show's cycle as the start item and with a dense 60 x 60 clip
   as the start item. The time the check takes is reported for both.
7. Afterwards the board is left running the two-leg bench show, autostarting, at
   brightness 40 or less.

## Open Questions

None. Use the resolved behavior in this seed.
