# Requirements: playing at once at power-on

Seed: [`project-seeds/14-p1-playing-at-once-at-power-on/seed.md`](../../../project-seeds/14-p1-playing-at-once-at-power-on/seed.md).

Today the core decodes every installed animation from its first frame to its last before
anything plays: for that time the LEDs are dark and no command is answered, 39 seconds on
the board with its storage full. This spec makes the core look at the header of each
animation only, play at once, and check the bodies while the show plays.

The seed was written before the playlist existed, and speaks of "the start item". A show
now plays its playlist by itself, or the cycle its `start` names. Where the seed says the
start item plays, this spec says: the show plays what it plays by itself.

In this document:

- "the header" is the first 16 bytes of an animation file;
- "the body" is everything after the header;
- "the check after the start" is the check of the bodies while the show plays;
- "a step" is one piece of that check: reading the header of a file again, decoding one
  frame record, or reading the end of a file;
- "the length of an animation" is the sum of the durations of its frames, which is how
  long one loop lasts. It is not in the header: it is known when the body was read once;
- "the reference player" is the player written in Python in `tests/core/support.py`.

## Requirement 1: the start looks at headers only

**User story.** As an operator, I want the LEDs to light right after power comes back,
however much is installed.

1. At its start the core SHALL read `mapping.json` and `show.json` as today, and of every
   animation file the show names, in the order in which the show first names them, the
   header only.
2. A file that is missing, a header that is not sound, and a canvas that is not the
   mapping's SHALL make the show invalid at the start, each with the reason it has today,
   and of two faults the one that is reported today SHALL be reported.
3. The work of the start SHALL NOT grow with the size of the bodies of the files.
4. WHEN the start has ended and the show is valid THEN the show SHALL play what it plays
   by itself, from the first refresh on.

## Requirement 2: the bodies are checked while the show plays

1. After the start the core SHALL check the body of every animation file, one file after
   the other, in the order in which the show first names them.
2. The check SHALL take its steps at refreshes that follow the refresh before them
   without a grid time left out, and none at any other refresh.
3. At such a refresh the check SHALL take as many steps as refreshes of that kind have
   followed one another, and at most 16.
4. WHEN the check has read a file to its end THEN the core SHALL know the file's size in
   bytes and its length.
5. WHEN the check finds a fault THEN the show SHALL be invalid from that refresh on, with
   the reason the same show is refused with today: the LEDs go dark and `status` gives
   the reason.
6. WHEN the last file has been checked THEN the check after the start SHALL be complete.
   It SHALL NOT start again until the next start.
7. A show without an animation SHALL have its check complete at the start.

## Requirement 3: an animation plays before its length is known

1. An animation SHALL be played from its first frame whether or not its file was checked.
2. WHILE the length of the animation that plays is not known, its first loop SHALL be
   played to its last frame, and the core SHALL then know the length.
3. The turn of an animation in the playlist, and the turn of an animation in a cycle,
   SHALL be what [show.md](../../show.md) says, whether its length was known when the
   turn began or became known during it.
4. A refresh that comes late, or after a long time without one, SHALL show the picture of
   its moment, as today. Where that needs the length of an animation that is not known,
   the core SHALL read that animation through, once.
5. A fault that the player meets in a file SHALL make the show invalid from that refresh
   on, as today.
6. For a show whose files are sound, every refresh and every reply to `status` SHALL be
   what they are today.

## Requirement 4: commands while the check after the start runs

1. `play`, `play all`, `on`, `off`, `brightness`, `status` and `space` SHALL work as they
   do when the check is complete.
2. `list`, `remove` and `upload begin` SHALL be answered with `busy`.
3. `upload data`, `upload end` and `upload cancel` SHALL be answered as they are when no
   upload is open.
4. WHEN the check is complete THEN every command SHALL work as it does today, and `list`
   SHALL report the size of every file.
5. No command SHALL be added, and no reply SHALL gain a member or an error code.

## Requirement 5: a host whose storage cannot be changed

1. With a host that offers no storage that can be changed, the core has no second reader
   of a file. It SHALL check every file before it plays, as today, and its check after
   the start SHALL be complete at the start.

## Requirement 6: memory and time

1. The core SHALL take no memory after its start.
2. Its working memory for the 60 x 60 canvas with 100 items SHALL stay under 128 KB and
   be reported.
3. The check after the start SHALL use the memory the check of an upload has.
4. Any refresh rate from 20 to 50 a second on the board is acceptable.

## Requirement 7: the hosts, the tools and the app

1. The emulator and the firmware SHALL behave as the core does, with no code of their own
   for the check.
2. The firmware tool SHALL wait until the check after the start is complete before it
   reports that a show was installed, and SHALL report a show that turned invalid as a
   failure.
3. The command tool SHALL print `busy` as it prints any refusal.
4. The operators' app SHALL ask for the list again, after a second, while it is answered
   with `busy`, and SHALL NOT take `busy` for an invalid show.

## Requirement 8: shown on the board

1. With the storage filled with 9 MB of dense clips and a small animation first, the time
   from a restart to the first reply of `status` SHALL be within one second of that time
   with the demo show alone, and that reply SHALL report the playlist playing. Both times
   SHALL be reported.
2. WHILE the check after the start runs, `status` SHALL report 20 refreshes a second or
   more, with the demo show and with a dense 60 x 60 clip playing. The time the check
   takes SHALL be reported for both.
3. The board SHALL be left running the bench show, autostarting, at brightness 40 or
   less.

## Requirement 9: the documents

1. `docs/core.md`, `docs/show.md`, `docs/commands.md`, `docs/emulator.md`,
   `docs/firmware.md` and `docs/android-app.md` SHALL describe the start, the check after
   the start and `busy` as they are.
2. `AGENTS.md` SHALL no longer list this seed as coming.
