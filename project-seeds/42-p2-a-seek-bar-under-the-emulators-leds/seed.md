# A seek bar under the emulator's LEDs

## Summary

The emulator's page gets a progress bar under the LEDs: it shows where the animation on
the LEDs is within its loop, with the time played and the loop's length, and it can be
dragged to any point of the loop, which moves playback there. The bar is the emulator's
alone: nothing changes in the core, in the firmware, in the command list or in the
operators' app. The emulator learns the position and the length by itself, and moves
playback with what it has: its own clock and the commands that exist.

## Priority

- `P2`

## Depends On

- Seed 02, for the emulator, its page and its event stream, and its 20 ms grid.
- Seed 35, for the catalogs, whose entries carry each animation's length.
- Seed 41, for the current playlist's window, which counts the board's running time and
  so moves with a seek.

## Product Context

On 2026-10-26 the owner asked for a scrollable progress bar in the emulator, in the LEDs'
display area, below them, and said it does not need to go into the board's runtime: it is
for the emulator only. The owner reviews the converted animations in the emulator, dozens
of them and some of 15 minutes, and wants to see where an animation stands and to move
along it instead of waiting.

## Technical Constraints

- **Where.** The bar stands in the stage of the emulator's page, directly under the
  drawing of the LEDs and above the note, in every view that shows the drawing. It is
  one row: the name or the id of the animation on the LEDs, the bar, and the numbers
  `m:ss / m:ss`, the time played within the loop and the loop's length.
- **What it tracks.** The animation on the LEDs is `animation` of `status`. Its position
  is the time played within the loop that is showing; the length is the loop's: the sum
  of the frames' durations of an ODRG file, the pass of a text, the `seconds` of a clock.
  While the length is not known the bar shows the time played alone and cannot be
  dragged. While nothing plays, or a cycle plays, the bar shows nothing.
- **No change in the core.** The core exposes neither the position nor the length, and
  this seed adds nothing to `core/` or to `firmware/`: the emulator infers both. The
  engine asks the core for `status` ten times a second in place of once, its own
  requests, not logged, as today; the moment `animation` changes is the start of that
  animation's turn as the engine knows it, within a tenth of a second, and the engine
  counts the position from there with its own clock, modulo the length. After a seek the
  engine knows the start exactly, since it made it. The length comes from the storage's
  catalog when the storage has one, else from the file's records read with the Python
  library `odrig` in a thread of the emulator, once per file and kept for the run; a
  file not yet read shows no length.
- **Seeking.** Dragging the bar to a point of the loop moves playback there with what
  exists. When the point is ahead of the position, the engine moves its own clock
  forward by the difference, rounded to the 20 ms grid: the core's next refresh then
  shows the frame of that time, as it does after a late refresh, and nothing is
  replayed. When the point is behind, the engine first restarts the animation with its
  own `play <id>` request, which the log shows with the transport `seek`, and then moves
  the clock forward to the point. A move of the clock is running time: the turn and the
  24-hour window of seed 41 advance by it, which the page says in a word by the bar. A
  seek stays within the loop, so it never crosses the end of the turn, which is at least
  one loop. The clock never goes back.
- **The page's one request.** The page sends the seek to the emulator on a route of its
  own, `POST /seek`, with the target in milliseconds; the emulator answers with the
  position it moved to. That route is the page's way to the emulator and no command of
  the core: the command list is unchanged, and the board and the emulator accept exactly
  the same commands. The rule that the page sends no command stays, worded so: the page
  sends no command; its one control, the seek bar, asks the emulator to move playback.
  `docs/emulator.md` and the page's tests change with it, and nothing else of the page
  sends anything.
- **A fifth event.** The event stream gains `position`, sent with each of the engine's
  own `status` requests, ten times a second: the animation's id, the time played within
  the loop and the loop's length in milliseconds, or null while unknown, and the turn's
  start on the engine's clock. The page draws the bar from it alone, so a seek made by
  another page, or a `play` sent by any tool, is seen at once. The four events of today
  are unchanged.
- **Record mode.** The bar and the route are not part of a recording; `--record` is
  unchanged.
- **Where the work goes.** `emulator/engine.py` for the faster status requests, the
  inferred position, the lengths and the seek; `emulator/httpd.py` and `emulator/hub.py`
  for the route and the event; `emulator/web/` for the bar; `docs/emulator.md` for the
  page, the route, the event and the rule; the emulator's suite for all of it, driving
  the engine with the clock the tests inject. Nothing in `core/`, `firmware/`, `app/`,
  `docs/commands.md` or `docs/core.md` changes.

## Required Behavior

1. Under the LEDs' drawing, in every view that shows it, a row holds the animation's
   name or id, a progress bar, and `m:ss / m:ss`; the bar moves as the animation plays,
   updated ten times a second.
2. While the length is unknown the row shows the time played alone and the bar is not
   draggable; while nothing plays or a cycle plays, the row is empty.
3. Dragging the bar to a point moves playback there: forward by a move of the emulator's
   clock, backward by a restart followed by a move; the LEDs show the frame of the point
   at the next refresh, and the position reported afterwards is the point, within a grid
   step.
4. The log shows a restart made for a seek with the transport `seek`; a move of the clock
   advances the turn and the window as running time, and the row says so in a word.
5. The event stream gains `position` with the animation's id, the time played, the
   length or null, and the turn's start, ten times a second; the other events are as
   they are.
6. `POST /seek` takes a target in milliseconds and answers the position moved to; a
   target beyond the length, a target while the length is unknown, and a target while
   nothing or a cycle plays are refused with a reason.
7. The lengths come from the catalog when the storage has one, else from the files,
   read once in a thread; reading them never delays a refresh.
8. `docs/emulator.md` describes the bar, the route, the event and the changed rule of
   the page; the command list, the core and the firmware are untouched.

## Definition Of Done

1. All test suites that need no board and no phone pass. The emulator's suite checks,
   with an injected clock: the `position` events and their rate, the position's error
   within a tenth of a second after a turn begins and exact after a seek, the lengths
   from a catalog and from files, a seek forward and a seek backward against a reference
   player's frames, the refusals of `/seek`, the log line of a restart, the window's
   `left` after a seek, and that record mode is unchanged; the page's JavaScript is
   checked in the shell tests and the page files test allows the one fetch; the docs
   tests know five events and the reworded rule; and a Chrome test sees the bar move and
   a drag seek.
2. The owner looks at the bar in the emulator, drags it on a long animation, and sees
   the LEDs follow.

## Open Questions

None. The owner asked for this seed to be answered without a question pass; the
decisions it needed are taken in the constraints: a bar that is dragged to seek, not a
display alone; the emulator infers the position and the length rather than the core
exposing them; the seek moves the emulator's clock forward and restarts for a move back;
the page's one request goes to a route of the emulator's and is no command; a fifth event
carries the position; and the rate is ten a second.

## The Owner's Answers

On 2026-10-26 the owner asked to modify the emulator code to add, only to the emulator,
in the LEDs' display area and below them, a scrollable progress bar, and said that this
does not need to go into the ESP32-S3 runtime, only the emulator.
