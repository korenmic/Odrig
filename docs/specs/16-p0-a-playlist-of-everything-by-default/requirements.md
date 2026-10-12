# Requirements: a playlist of everything by default

Seed: [`project-seeds/16-p0-a-playlist-of-everything-by-default/seed.md`](../../../project-seeds/16-p0-a-playlist-of-everything-by-default/seed.md).

Today a show plays what its `show.json` names as `start` and stays dark without one,
`play <id>` of an animation loops it for ever, and only a cycle shows several animations
in turn. This spec makes the player play every installed animation in turn by default,
gives each animation a turn of its own length, and adds the command `play all`. The
owner ruled on each point on 2026-10-12; the seed lists the rulings.

In this document:

- "a loop" is one play of an animation from its first frame to its last;
- "a turn" is the time one animation has before the next one starts;
- "the playlist" is every animation item of the show, in the order of `show.json`;
- "the reference player" is the player written in Python in `tests/core/support.py`,
  which the core is compared with.

## Requirement 1: the show file says how long an animation plays

**User story.** As the person who prepares a show, I want to give an animation a repeat
count and a longest duration, so that a short one is seen long enough and a long one does
not hold the installation.

1. An animation item of `show.json` MAY have the members `repeat` and `max_seconds`, each
   a whole number from 1 to 65,535. A cycle item SHALL NOT have them.
2. `show.json` MAY have the member `min_seconds` at its top, a whole number from 1 to
   65,535. Without it the value is 30.
3. A value outside these limits, or one that is not a whole number, SHALL make the show
   file malformed, with the reason it has today for a malformed show file.
4. A show file that is valid today SHALL stay valid.
5. The Python reference, the JavaScript converter and the core SHALL accept and refuse
   the same show files, with the same reasons.
6. `pack` SHALL carry the members into the installed show as the show file has them.

## Requirement 2: the turn of an animation

1. WHEN an animation item has `repeat` THEN its turn SHALL be that many loops.
2. WHEN it has no `repeat` THEN its turn SHALL be the fewest loops that last at least
   `min_seconds`, and one loop at least.
3. WHEN it has `max_seconds` and the turn of criterion 1 or 2 is longer THEN the turn
   SHALL end at `max_seconds`, in the middle of a loop if need be.
4. A turn SHALL begin with the first frame of its animation.

## Requirement 3: the playlist plays by default

1. The playlist SHALL play every animation item of the show in the order of `show.json`,
   each for its turn, and then from the first again, without end.
2. WHEN a show has one animation THEN its turns SHALL follow one another.
3. WHEN a valid show without `start` starts THEN the playlist SHALL play from its first
   animation.
4. WHEN `start` names an animation THEN the playlist SHALL play from that animation.
5. WHEN `start` names a cycle THEN the cycle SHALL play, as today.
6. WHEN a show has no animation THEN nothing SHALL play.
7. A turn SHALL begin at the moment the turn before it ends, also when the host asks for
   refreshes late.
8. WHILE the LEDs are switched off the time of the playlist SHALL go on.

## Requirement 4: `play <id>` and `play all`

1. WHEN `play <id>` names an animation THEN the playlist SHALL play from that animation:
   its turn begins, and afterwards the playlist goes on with the animation after it.
2. WHEN `play <id>` names a cycle THEN the cycle SHALL play, as today.
3. WHEN `play all` is sent THEN the playlist SHALL play from its first animation.
4. WHEN `play all` is sent to a show without an animation THEN it SHALL be refused with
   `unknown-id`.
5. `play all` SHALL be refused as `play <id>` is: `show-invalid` while the show is
   invalid, `bad-argument` with a word too many.
6. No other command SHALL be added, and `on`, `off` and `brightness` SHALL do what they
   do today.

## Requirement 5: `status` says what plays

1. WHILE the playlist plays, `playing` in the reply to `status` SHALL be `"all"`.
2. WHILE a cycle plays it SHALL be the id of the cycle, and `null` when nothing plays.
3. `animation` SHALL be the id of the animation on the LEDs, as today.
4. No member SHALL be added to or taken from the reply.

## Requirement 6: the show changes while it plays

1. WHEN an animation is uploaded as a new item THEN it SHALL be part of the playlist from
   then on, at its place in the show.
2. WHEN an animation is uploaded while nothing plays THEN the playlist SHALL play from
   its first animation.
3. WHEN the animation whose turn it is gets another animation by an upload THEN its turn
   SHALL begin again.
4. WHEN the animation whose turn it is is removed THEN the playlist SHALL go on with the
   animation after it.
5. WHEN the last animation of the show is removed THEN nothing SHALL play.
6. WHEN the cycle that plays is removed THEN the playlist SHALL play from its first
   animation.
7. An animation that a cycle lists SHALL still be refused with `in-use`.
8. WHEN the core writes `show.json` THEN it SHALL keep `repeat`, `max_seconds` and
   `min_seconds` as the show has them.

## Requirement 7: memory and time

1. The core SHALL take no memory after its start.
2. Its working memory for the 60 x 60 canvas with 100 items SHALL stay under 128 KB and
   be reported.
3. Any refresh rate from 20 to 50 a second on the board is acceptable.

## Requirement 8: the hosts and the shows

1. The emulator and the firmware SHALL behave as the core does, with no code of their own
   for the playlist.
2. The emulator's page SHALL show that the playlist plays, and which animation.
3. The command tool SHALL send `play all`.
4. The demo show for the target SHALL have no cycle and no `start`. The example show for
   the bench SHALL keep its cycle.

## Requirement 9: shown on the board

1. WHEN a show of two animations without `start` is installed at a brightness of 40 or
   less THEN `status` over USB SHALL report `"playing":"all"` from power-on.
2. The session of commands of the board tests, with `play all` in it, SHALL give the
   replies the emulator gives.
3. The board SHALL be left running the bench show, autostarting, at brightness 40 or
   less.

## Requirement 10: the documents

1. `docs/show.md` SHALL describe the new members, the turn and the playlist.
2. `docs/commands.md` SHALL describe `play all`, what `play <id>` does now, and the
   values of `playing`.
3. `docs/core.md`, `docs/emulator.md`, `docs/firmware.md`, the converter's pages and the
   pages for newcomers SHALL describe the player as it is.
4. `AGENTS.md` SHALL no longer list seed 16 as coming.
