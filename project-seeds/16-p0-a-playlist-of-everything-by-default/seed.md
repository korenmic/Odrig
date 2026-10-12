# A playlist of everything by default

## Summary

The player plays all installed animations one after the other, as a playlist, unless the
show says otherwise. Each animation has a turn: by default it repeats until at least 30
seconds have passed and then finishes the loop it is in; a show can give an animation a
repeat count and a maximum duration of its own. `play <id>` jumps to an animation and the
playlist goes on after it. One new command, `play all`, starts the playlist from its
first animation.

## Priority

- `P0`

## Depends On

- Seed 02, for the shared core, which holds the player and the commands.
- Seed 03 and seed 04, for the emulator and the firmware that host the core.
- Seed 06, for the JavaScript converter, which reads and packs show files.
- Seed 07, for the commands that add and remove animations while the show runs.

## Product Context

Today a show plays what its `show.json` names as `start`, and stays dark when it names
nothing. `play <id>` of an animation loops that animation for ever. The only way to show
several animations in turn is a cycle, which lists animations and gives all of them the
same number of seconds. A cycle cannot be made or changed by a command, so an animation
that is uploaded to a running installation never plays until somebody sends `play` for
it.

The owner wants the installation to play everything that is installed, by itself, and
ruled on 2026-10-12:

- By default all installed animations start as a playlist.
- Each animation has a repeat count and a maximum duration for its playback.
- An animation without these repeats again and again until at least 30 seconds have
  passed. The loop it is in then is its last, and after it the next animation starts.
- `on` stays a plain switch: it lights the LEDs again and what was playing goes on. A new
  command, `play all`, goes back to the playlist.
- After `play <id>` the animation plays its turn, and then the playlist goes on with the
  animation after it.
- An animation is called by its file name. No other name is added.

The operators' app is built on this: its main screen is the playlist, with what is
playing now.

## Technical Constraints

- The change is in the shared core, so the emulator and every firmware behave alike.
- The core takes no memory after its start, and its working memory for the 60 x 60 canvas
  with 100 items stays under 128 KB. It is at 124,501 bytes today.
- One command is added, `play all`, which the owner approved. No other command is added.
  No reply gains or loses a member; `playing` in the reply to `status` gains one value.
- A show file that is valid today stays valid and means what it means today wherever it
  names a `start`: a cycle plays as it does today.
- The Python reference, the JavaScript converter and the core read a show file alike and
  refuse the same files with the same reasons.
- The core writes `show.json` when the show is changed by a command. It keeps every
  member that this seed adds.
- Any refresh rate from 20 to 50 a second on the board is acceptable.
- Tests that need the board are kept apart from those that do not. On the board,
  brightness stays at 40 or less.

## Required Behavior

1. In `show.json` an animation item may have two more members, both optional:
   - `repeat`, a whole number from 1 to 65,535: how many times the animation is played
     through in one turn.
   - `max_seconds`, a whole number from 1 to 65,535: the longest a turn lasts. A turn
     that reaches it ends there, in the middle of a loop if need be.
2. `show.json` may have one more member at the top, optional: `min_seconds`, a whole
   number from 1 to 65,535, and 30 when it is absent.
3. The turn of an animation:
   - with `repeat`, it is played through that many times;
   - without `repeat`, it is played through again and again until at least `min_seconds`
     have passed, and the loop it is in then is played to its end;
   - in both cases the turn ends at `max_seconds` at the latest, when the item has it.
4. The playlist is every animation item of the show, in the order of `show.json`, each
   for its turn, and then from the first again, for ever. A show with one animation plays
   it again and again. A show without an animation plays nothing.
5. At power-on:
   - a show without `start` plays the playlist from its first animation, where today it
     stays dark;
   - a show whose `start` names an animation plays the playlist from that animation;
   - a show whose `start` names a cycle plays the cycle, as today.
6. `play <id>` of an animation makes the playlist jump to it: its turn begins with its
   first frame, and afterwards the playlist goes on with the animation after it.
   `play <id>` of a cycle plays the cycle, as today.
7. `play all` plays the playlist from its first animation. In a show without an
   animation it is answered as `play` of an id that does not exist is.
8. In the reply to `status`, `playing` is `"all"` while the playlist plays, the id of the
   cycle while a cycle plays, and `null` when nothing plays. `animation` is the id of the
   animation on the LEDs, as today.
9. `on`, `off` and `brightness` do what they do today. While the LEDs are off the time
   of the playlist goes on.
10. While the show is changed by a command:
    - an uploaded animation is part of the playlist from then on, at its place in the
      show;
    - when the animation on the LEDs is removed, the playlist goes on with the one after
      it; when it was the last animation of the show, nothing plays;
    - an animation that a cycle lists is still refused with `in-use`.
11. The converter and the Python reference accept the new members, refuse values
    outside their limits with the reason of a malformed show, and `pack` carries them
    into the installed show. The command tool sends `play all`.
12. The demo show for the target plays as the playlist: its cycle and its `start` are
    taken out. The example show for the bench keeps its cycle.
13. `docs/show.md`, `docs/commands.md`, `docs/core.md`, `docs/emulator.md`,
    `docs/firmware.md`, the converter's pages and the pages for newcomers describe the
    playlist, the turn and the new command.

## Definition Of Done

1. All test suites that need no board pass.
2. The core gives the LED data and the replies of the reference player of the tests for:
   the default turn of 30 seconds with a loop played to its end, a `repeat`, a
   `max_seconds` that cuts a loop, a `min_seconds` of the show, a jump with `play <id>`,
   `play all`, a show that names a cycle as `start`, and an upload and a removal while
   the playlist plays.
3. In the emulator, with the demo show, `status` reports `"playing":"all"` from the
   start, and the animation on the LEDs changes at the end of a loop once 30 seconds
   have passed.
4. The core's measured working memory for 60 x 60 with 100 items is under 128 KB and is
   reported.
5. On the board, with a show of two animations and no `start` at a brightness of 40 or
   less, `status` over USB reports the playlist from power-on, and the session of
   commands of the board tests gives the replies the emulator gives.
6. Afterwards the board is left running the two-leg bench show, autostarting, at
   brightness 40 or less.

## Open Questions

None. Use the resolved behavior in this seed.
