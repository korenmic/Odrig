# Design: a seek bar under the emulator's LEDs

## What this design relies on

- The core opens the file it plays through the host's `open` at the start of every turn
  and of every loop (`open_stream` in `core/src/player.cpp`, called from `show_at` when
  the animation, the turn or the loop changes), and reads the checked files through
  `read_at`, never `open`; at power-on, inside `odrig_core_begin`, it opens the show's
  files once to check them, before the engine exists. So at run time an `open` of an
  animation file is the start of a loop of the animation on the LEDs. A text or a clock
  is opened once per turn and closed at once. The emulator's host is `FolderHost` in
  `emulator/host.py`; its `open(name)` is called by the binding inside `core.poll`, which
  the engine calls under its lock in `Engine.tick`.
- A refresh is taken only at a grid time: `odrig_core_poll` returns nothing before
  `next_due`, the grid step after the last refresh, and a turn that a `play` began
  starts at the grid time at or before the refresh that takes it (`core.zero = grid`).
  Measured on the example show: opens at 0, 5100 and 10200 ms for the 5.1 s loop, and a
  `play 1` sent at 40007 ms, refused a poll at 40010, taken at 40027 with the loop
  starting at 40020.
- The engine's clock is `now_ms()`, `(clock() - start_ns) // 1_000_000`
  (`emulator/engine.py`). Every refresh and every frame event carries that clock. Moving
  `start_ns` earlier by a whole number of grid steps raises every later `now_ms` by that
  much, and `RealTime.step`, which computes the next grid time from `t0` and `now`, stays
  on the grid. The core takes any forward time: a late refresh shows the frame of its own
  timestamp and replays nothing (`docs/core.md`, the timestamp and the refresh).
- `status` names the animation on the LEDs in `animation` and what plays in `playing`,
  `"all"`, a cycle's id or null; `list` tells which ids are cycles.
- A storage's catalog gives `total_ms` for every entry (`odrig/catalog.py`, `Entry`;
  `read(Storage(folder))` gives a `Catalog` whose `state` is `ok` when it can be used).
  The converter's `check` prints `duration_ms:` for an ODRG file
  (`node converter/odrig.js check FILE`) and nothing of the kind for a container.
- The hub (`emulator/hub.py`) keeps the log entries and the latest status for new
  connections and sends `status` and `log` events to every connection without dropping
  them; the page (`emulator/web/app.js`) draws from the events alone and, today, sends
  nothing but `GET events` and `GET show/mapping.json`.
- Seed 41 is not in master yet: nothing here relies on its `left` or its folders.

## The played file's opens

`FolderHost` gets an attribute `on_open`, `None` by default. After a successful `open`
of an animation file, a name that ends in `.odrg` or `.odrgx` or a drive place
`drive/<number>`, the host calls `on_open(name, path)` with the name the core used and
the file's path on disk (`self.drive.path(name)` for a place, the show folder's file
otherwise). Nothing else of the host changes; a host without the attribute set behaves
as today.

The engine sets `host.on_open` to its own `_opened`, which only notes the name and the
path of the open in the tick that is running: it never calls the core, since it runs
inside `core.poll`. After `core.poll` returns, still under the lock, `tick` takes the
note up: the start of the loop is the grid time at or before the tick's timestamp,
`t0 + ((now - t0) // 20) * 20`.

## The playback state

`Engine` keeps a `Playback` record: `animation` (the id from `status`, or null),
`playing` (the `playing` member), `stream` (the name opened last), `path`, `start` (the
loop's start), `turn` (the turn's start), `length` (ms or null) and `source`
(`catalog`, `check`, `seen`, or null); and beside it `cycles`, the set of cycle ids from
`list`, `answered`, a count of the commands answered, and `marked`, the count at the
previous open together with whether a seek came since.

- An open is a turn's start when its name differs from `stream`, when a command was
  answered since the previous open, or when it follows the engine's own restart. Then
  `stream`, `path` and `start` are set, `turn = start`, the length is looked up for the
  path (see below), and `tick` asks the core for `status` at once, after the poll, so
  that `animation` and `playing` are the new ones; the hub gets that status as it gets
  every status.
- Any other open of the same stream is a new loop. When the length is unknown and no
  seek came since the previous open, the length becomes `now - start` with the source
  `seen`. Then `start = now`. On a playlist of one animation a turn's open comes exactly
  a loop after the previous one and is counted as a loop, which is also right.
- Whenever `status` is taken in (`refresh_status`, the tick's own request, after
  commands): `animation` and `playing` are updated; when `animation` is null, or
  `playing` is one of `cycles`, the record's event shows `animation` null while the
  record keeps the id for the refusal `cycle`.
- After every command that arrived (`line`, `feed`), the engine asks `list` and its
  pages, its own requests, not logged, and keeps the ids of cycle items in `cycles`;
  `answered` goes up by one.
- Every change of what the event shows, `animation`, `start`, `turn` or `length`, sends
  a `position` event.

## The lengths

`Lengths` in a new module `emulator/lengths.py`:

- `catalog(folder)`: reads the catalog of a folder with `odrig.catalog.read(Storage(
  folder))` and returns `{name: total_ms}` for an `ok` catalog, `{}` otherwise. The engine
  reads the show folder's catalog at start and the drive's folder `odrig` at every
  plug-in, outside the lock, and keeps the two tables; a lookup goes by the file's name
  in its storage.
- `check(path, done)`: when `shutil.which("node")` finds Node.js, runs
  `node converter/odrig.js check <path>` in a worker thread, one file at a time, and
  calls `done(path, duration_ms)` with the number after `duration_ms:` in the output,
  or `None` when the check fails or prints no duration. Results are cached by path for
  the run. The engine's `done` takes the lock, sets the length when the path is still
  the played one, and sends `position`.
- Without Node.js the second source is skipped and the third stands alone.

## The event `position`

`Hub.position(data)` keeps the latest and sends `event: position` with
`{"animation", "start", "turn", "length"}` to every connection, as `status` is sent;
`connect` sends it after the latest status. `docs/emulator.md` gets the fifth kind.

## The seek

`Engine.seek(target_ms)` returns a dictionary for the route:

1. Under the lock: `bad-argument` when the target is not a whole number; `nothing-plays`
   when `animation` is null; `cycle` when `playing` is in `cycles`; `length-unknown`
   when `length` is null; `beyond-length` when the target is below 0 or above the length
   less 40.
2. `position = (now - start) % length`, with `moved = 0`.
3. When `target < position`: the engine sends `play <animation>` to the core as its own
   request and logs it with the transport `seek`; it moves the clock forward by one grid
   step (`start_ns -= 20_000_000`, `moved = 20`), polls the core at the new time so that
   the turn begins and the file is opened, which sets `start` to that refresh's grid time
   and `turn` with it; and takes `position = now - start`.
4. `move = ((target - position) // 20) * 20`; when it is above 0: `start_ns -= move *
   1_000_000`, `moved += move`, and the core is polled at the new time; a frame it
   produces goes to the hub. The seek is marked so that the next open is not taken as a
   seen loop.
5. The reply holds the new position, `start`, `turn`, `length` and `moved`.

The lock is held throughout, so the real-time thread's next step sees the moved clock
and stays on the grid, as every move is a whole number of grid steps.

## The route

`httpd.py` gets `SEEK_PATH = "/seek"`: `POST` with a JSON body `{"ms": N}` answers 200
with the dictionary of `Engine.seek` as JSON, `{"ok": false, "error": ...}` included;
a body that is not that JSON answers `bad-argument` the same way; a missing or
malformed `Content-Length` answers 411 and another method 405 with `Allow: POST`, as
`/odrig` does. The route is dispatched beside `/odrig`, before the page files.

## The page

- `index.html`: inside `main.stage`, between `div#drawing` and `p#note`, `div#seek` with
  `span#seek-name`, `div#seek-bar` (`role="slider"`, `aria-valuemin`, `aria-valuemax`,
  `aria-valuenow`) holding `div#seek-fill` and `div#seek-knob`, `span#seek-time` and
  `span#seek-note`. No `<input>` and no `<form>`.
- `style.css`: `.stage` becomes a flex column; `#drawing` takes the room that is left
  (`flex: 1; min-height: 0`); `#seek` is one row of 28 px at the bottom with the bar
  filling the middle; the fill and the knob in the accent colour; the bar gets a
  `draggable` class only while a length is known; `.chip[data-via="seek"]` in the accent
  colour for the log.
- `app.js`: `fit` uses the drawing host's size in place of the stage's, and the resize
  observer watches the host. A `position` listener keeps the last event. `onFrame` calls
  `seekDraw(ms)`: elapsed is `ms - start`, the shown time is elapsed modulo the length
  when known, the fill is its share of the length, the numbers are `m:ss / m:ss`
  (`h:mm:ss` from one hour), `length unknown` without a length, and the row is hidden
  while `animation` is null. Pointer events on the bar: down takes the pointer, move
  shows the point's time, up sends `fetch("seek", {method: "POST", body: JSON.stringify({
  ms: point})})` and, with an `ok` answer, shows `clock +N s` in the note for three
  seconds when `moved` is above 0. A point from a press without a move is sent on the
  up as well. No keyboard seeking.
- The page's comment and `docs/emulator.md`'s rule read: the page sends no command; its
  one control, the seek bar, asks the emulator to move playback.

## The documents

- `docs/emulator.md`: in "The page", a bullet for the seek bar and the reworded rule; a
  subsection "Seeking" with the position, the lengths and the move of the clock; in the
  routes table, `POST /seek`; in "The event stream", five kinds with the `position`
  example and its table row, and `seek` among the `log` transports; the sentence on the
  standard library names the `odrig` package.
- `docs/decisions.md`: a change-log line at the end, with task 4.
- `docs/drifts.md`: the decisions taken on the way, at the end.

## Decisions taken beyond the seed

Recorded in `docs/drifts.md` with task 4: the numbers from one hour as `h:mm:ss`; the
words `length unknown` and `clock +N s` for three seconds; the start as the grid time of
the refresh; the move rounded down and the last two grid steps of a loop out of reach;
`status` asked once more after a turn's open; no keyboard seeking; cycles shown as
nothing playing; the `odrig` package used by the emulator for the catalogs.

## Verification

- `tests/emulator/test_playback.py` (new): `Engine` with the real core, an injected clock
  and a `FolderHost` on the example show, ticked grid by grid: the `position` events of
  the hub at the first open, at every loop of `hello.odrg` (its length is the reference
  player's), at the turn's change to `dvd.odrg`; `source` `seen` after two opens
  without Node.js (`shutil.which` patched to `None`); no `seen` length across a `play`
  of the same animation; the length from a catalog written with `odrig.catalog` into a
  show folder; the length from the converter's check when Node.js is at hand (skipped
  without it); `animation` null in the event while the cycle plays; clearing when
  nothing plays.
- `tests/emulator/test_seek.py` (new): `Engine.seek` with the injected clock: forward,
  the frames afterwards equal the reference player's for their timestamps; backward,
  the log entry with the transport `seek`, the reference player sent `play` at the same
  timestamp and polled on, the start at the grid; every refusal; `moved` a whole number
  of grid steps; and the route through the running emulator (`support.Emulator`) with
  `POST /seek`, 411 and 405.
- `tests/emulator/test_events.py`: `position` after the latest status on a new
  connection; `test_docs.py`: five events and the `seek` transport; `test_page_files.py`:
  the one fetch `seek`, no request to `/odrig`, the fit and the observer on the host;
  `test_record.py`: nothing new in a recording.
- `tests/app/test_emulator_seek.py` (new): Chrome with `--headless=new --dump-dom` and a
  virtual time budget on the demo show, twice, `#seek-time` differing; a `POST /seek`
  from the test and a third dump with the numbers at the point.

## What does not change

`core/`, `firmware/`, `app/`, `odrigctl/`, `docs/commands.md`, `docs/core.md`, the four
events of today, record mode, and the commands the board and the emulator accept.
