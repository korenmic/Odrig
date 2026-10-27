# Requirements: a seek bar under the emulator's LEDs

The emulator's page gets a progress bar under the drawing of the LEDs that shows where
the animation on the LEDs is within its loop and can be dragged to move playback there.
Everything is the emulator's: nothing changes in the core, the firmware, the command list
or the operators' app. Where these requirements decide a point the seed leaves open, the
decision is recorded in `docs/drifts.md`.

## 1. The bar

1.1. Under the drawing of the LEDs and above the note, in every view that shows the
drawing, stands one row: the id of the animation on the LEDs, a progress bar, and the
numbers `m:ss / m:ss`, the time played within the loop and the loop's length. From one
hour the numbers are written `h:mm:ss`.

1.2. The bar's fill moves as the animation plays: the page updates it with every frame it
receives, from the frame's timestamp and the last `position` event.

1.3. While the length is unknown the row shows the time played alone, the fill is empty,
the bar cannot be dragged, and the row says `length unknown`.

1.4. While nothing plays, or a cycle plays, the row is hidden.

1.5. Dragging the bar, or pressing on it, moves playback to the point under the pointer:
while the pointer is held the numbers show the point, and on release the page sends the
seek. The fill and the numbers follow the frames again afterwards.

1.6. After a seek the row says, for three seconds, by how much the emulator's clock was
moved: `clock +12 s`. A seek that moved the clock by nothing says nothing.

1.7. The row keeps the dark stage's look and fits the stage's width; the drawing above it
keeps its fit in the room that is left.

## 2. The position and the length

2.1. The length of an animation is its loop: the sum of the frames' durations of an ODRG
file, the pass of a text, the `seconds` of a clock.

2.2. The start of each loop of the animation on the LEDs is the grid time at or before
the refresh in which the core opened the played file through the emulator's host: the
core opens the file anew at every loop and every turn, and begins a turn at the grid
time of the refresh that takes it. The position is the time since that start, on the
engine's clock.

2.3. The start of the turn is the first open after the animation on the LEDs changed, or
after a command was answered, or after the engine's own restart; the emulator asks
`status` once more after the refresh in which such an open happened, so that the
animation's id is known at once.

2.4. After a seek the start is the one the engine set itself: the grid time of the
refresh that took its restart, or the start of the loop it moved within.

2.5. The length is, in this order: the entry of the storage's catalog, when the storage
has one; the `duration_ms` of the converter's `check` of the file, when Node.js is on
the path, run once per file in a thread of the emulator and kept for the run; the time
between two consecutive opens of the same file with no command answered and no seek
between them. Until one of them gives it, the length is unknown.

2.6. A text or a clock animation without a catalog entry has no length: the converter's
check gives none for a container, and a pass is never seen as a loop.

2.7. Reading a catalog or running the converter never delays a refresh of the core: both
run outside the engine's lock, and their results are taken in under it.

## 3. Seeking

3.1. A seek names a point of the loop, in milliseconds from its start, from 0 to the
length less two grid steps, 40 ms.

3.2. When the point is at or after the position, the engine moves its own clock forward
by the difference, rounded down to a whole number of 20 ms grid steps, and asks the core
for a refresh: the core shows the frame of that time, as it does after a late refresh,
within a grid step below the point. Nothing is replayed.

3.3. When the point is before the position, the engine first restarts the animation with
its own `play <id>` request, moves its clock forward by one grid step so that the core
takes the next refresh, polls, and takes the grid time of that refresh as the start; then
it moves the clock to the point as in 3.2. The clock's move counts both steps.

3.4. A move of the clock is running time for the core: the animation's turn advances by
it, and so does whatever else the core counts in time, the current playlist's window
once seed 41 is built. The engine never moves the clock back.

3.5. A seek stays within the loop and so within the turn, since a turn is at least one
loop; a point above the length less two grid steps is refused with `beyond-length`.

3.6. A seek is refused with `nothing-plays` while no animation is on the LEDs, with
`cycle` while a cycle plays, with `length-unknown` while the length is unknown, and with
`bad-argument` when the point is not a whole number of milliseconds.

3.7. The `play <id>` request of a restart is entered in the log with the transport
`seek`, so that the page and any reader of the stream see it.

3.8. The answer to a seek carries the position moved to, the loop's start, the turn's
start, the length and the clock's move.

## 4. The event and the route

4.1. The event stream gains a fifth kind of event, `position`: `{"animation": <id or
null>, "start": <ms or null>, "turn": <ms or null>, "length": <ms or null>}`, the starts
on the engine's clock, the same clock as the frames' timestamps. `animation` is null
while nothing plays and while a cycle plays.

4.2. `position` is sent to a new connection after the latest status, and whenever one of
its members changes: a turn's start, a loop's start, a seek, a length learned, a cycle
begun, or nothing playing any more. It is never dropped.

4.3. `POST /seek` takes a body `{"ms": <point>}` and answers `{"ok": true, "animation":
<id>, "start": <ms>, "turn": <ms>, "length": <ms>, "position": <ms>, "moved": <ms>}`, or
`{"ok": false, "error": "<reason>"}` with the reasons of 3.5 and 3.6, with status 200 in
both cases; a body that is not such JSON is `bad-argument`; a body without a whole-number
`Content-Length` is answered 411 and any other method 405, as `/odrig` is.

4.4. The route is the page's way to the emulator and is no command of the core: the
command list, `docs/commands.md` and every route to the core are unchanged, and the
board and the emulator accept exactly the same commands.

4.5. The page sends no command; its one control, the seek bar, asks the emulator to
move playback through `POST /seek`, and nothing else of the page sends anything.

## 5. What does not change

5.1. Nothing in `core/`, `firmware/`, `app/` or `odrigctl/` changes, and no command,
reply member or error code is added.

5.2. The four events of today keep their members and their timing; `status` is asked as
today, once a second and after every command that arrived, plus once after a refresh in
which a turn's open happened. The log's transports gain `seek`.

5.3. Record mode is unchanged: it has no bar, no route and no `position` event.

5.4. The emulator needs nothing outside Python's own library and the repository's own
`odrig` package, pure Python, which reads the catalogs; Node.js is used for the length
only when it is on the path, and its absence costs the length of files without a catalog
until a loop is seen twice.

## 6. Tests and delivery

6.1. The emulator's suite checks, with an injected clock, the `position` events at a
connection, at a turn's start, at a loop's start, at a length learned, at a cycle and at
a seek; the starts against the reference player's turn and loop boundaries, within a
grid step; the lengths from a catalog, from the converter's check and from a loop seen
twice, and no seen length across a restart; a seek forward and a seek backward whose
frames afterwards equal the reference player's for their timestamps; every refusal of
`/seek`; the log line of a restart; `moved` a whole number of grid steps; and record mode
unchanged.

6.2. The page's scripts stay valid for the JavaScript shell; the page files test allows
exactly one request besides the events and the mapping file, the seek, pins the fit and
the resize observer on the drawing's host, and keeps `/odrig` forbidden; the docs tests
know five events and the reworded rule.

6.3. A Chrome test in the app's suite opens the page on the demo show with
`--headless=new --dump-dom` and a virtual time budget, twice, and sees `#seek-time`
with numbers that differ between the two; then it posts `/seek` itself and a third dump
shows the numbers at the point.

6.4. `docs/emulator.md` describes the bar, the position and the length, the seek, the
route, the event, the `seek` transport and the rule; `docs/decisions.md`'s change log
records the seed; what was decided on the way goes to the end of `docs/drifts.md`.
