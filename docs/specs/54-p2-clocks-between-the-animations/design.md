# Design: clocks between the animations

Requirements: [requirements.md](requirements.md). Seed:
`project-seeds/54-p2-clocks-between-the-animations/seed.md`. The code is `master` with seeds
50 and 52 merged: the drive's files are positions of its walk, the root's files first and
then each folder's in the tree's order, read through `drive_row`; a folder of the tree
(`IndexFolder`) has `first`, `last` and `files`, its own files being the positions from
`first` on, `files` of them, and its subtree the positions from `first` to `last`. Where the
code differs from this design, the code is followed and the difference recorded in
`docs/drifts.md`.

## The core

### The module `breaks.cpp` and `breaks.h`

- **The settings.** `Core` gains `uint8_t clocks_on`, `uint8_t clock_message_on`.
  `breaks_start(core)` at the start, after the show is read and before the player starts:
  removes `clocks.part` when there is one (as `storage.cpp` removes `repeats.part`), reads
  `clocks.txt` whole through the host's `read_at` into a small stack buffer of 64 bytes:
  exactly `odrig-clocks 1\n`, `clocks on\n` or `clocks off\n`, `message on\n` or `message
  off\n`, and nothing more; a missing file is both off; anything else both off and the log
  `clocks unreadable`.
- **The commands.** `breaks_command(core, words, reply)` for `clocks on|off` and `clocks
  message on|off`: `bad-argument` for other words; `show-invalid`; `busy` while
  `catalog_rebuilding`, `!check_complete` or an upload is open; a setting already in force
  succeeds and writes nothing; `storage-error` when the host cannot write (`write_open`
  null or failing) or a call fails, nothing changing; else `write_open("clocks.part")`,
  the three lines, `write_close`, `rename("clocks.part", "clocks.txt")`, then the setting
  takes effect. `clocks on` from off starts the counts (`player_counts_start`).
- **The clocks' folders.** `Core` caches `clocks_first`, `clocks_last`, `clocks_files`
  (the folder `clocks`: its subtree's positions and its own files'), and `message_first`,
  `message_files` (the folder `clocks/message`), all 0 when there is no such folder.
  `breaks_tree(core)` recomputes them with `drive_folder_with_path(core, "clocks")` and
  `"clocks/message"` and `drive_folder`. It is called wherever the tree is built or found
  again and wherever the walk's positions move or a drive is taken up or dropped: after
  `tree_build`, `tree_find_current`, `tree_clear`, `player_drive_moved`,
  `player_drive_shifted` and `player_drive_changed`. It also starts a new order of the
  clocks.
- **The order of the clocks.** `Core` gains `uint32_t order_key`, `uint32_t order_next`
  and `uint32_t order_count`. `clock_shuffle(key, count, index)` in `clock.cpp`: the
  index's place in a permutation of `0 .. count - 1`, a balanced Feistel network of four
  rounds over the smallest even number of bits `b >= 2` with `2^b >= count`, each round
  `R' = L ^ (mix(key ^ (round * 0x9E3779B9u) ^ R) & mask)`, `L' = R`, repeated on its own
  output while the value is `>= count` (cycle walking). `breaks_pick(core, at)`: while
  `order_next >= order_count` or the count changed, a new order: `order_key =
  clock_seed(core.noise, clocks_files, at)`, `order_count = clocks_files`, `order_next =
  0`; then the positions `clocks_first + clock_shuffle(order_key, order_count,
  order_next++)` in turn until one `drive_plays`; at most two whole orders are tried;
  `kNothing` when none plays or there is no folder.
- **The message.** `breaks_message(core)`: the first position from `message_first`, of
  `message_files`, that `drive_plays`, else `kNothing`.
- **The test host** gets `odrig_host shuffle KEY COUNT`, printing the permutation, and
  `tests/core/support.py` a twin `clock_shuffle(key, count, index)`.

### The player (`player.cpp`, `player.h`, `core_state.h`)

`Core` gains: `uint8_t break_phase` (0 none, 1 the clock's turn, 2 the message's),
`uint8_t break_paused`, `uint8_t break_held`, `uint8_t break_turns`; `uint32_t break_back`
(the position the playlist goes back to), `uint32_t break_repeat` (the paused turn's
`turn_repeat`), `uint32_t break_seed` (its clock's seed, 0 for none), `uint32_t
resume_seed`; `uint64_t break_offset` (the paused turn's time), `uint64_t break_due` (the
timestamp at which 5 minutes of the playlist are counted), `uint64_t break_rest` (the time
left while the count is held). About 60 bytes; the object stays within its 4,096.

- **Passing over.** `drive_playing_from` skips `[clocks_first, clocks_last)` while
  `clocks_on` and the range is not empty, so `first_in`, `next_in`, `judge_in_place` and
  the rest follow; the rounds' sum is not taken while `clocks_on`.
- **The time count.** `break_held` with `break_rest` while the playlist does not play:
  `player_play_cycle` and `player_halt` hold (`break_rest = break_due > latest ? break_due
  - latest : 0`); where `player_poll` sets `zero` for a pending turn of the playlist, a
  held count is let go: `break_due = zero + break_rest`. At the start the count is held
  with `break_rest = 300,000`. `player_counts_start(core)`: `break_turns = 0`, and
  `break_due = latest + 300,000` while the playlist plays, else held with 300,000.
- **A turn cut.** `player_play_all` while the playlist plays: with `break_phase != 0` the
  break is cut (`break_phase = 0`, `break_paused = 0`, `resume_seed = 0`, the counts held
  anew with 300,000); else with `clocks_on` `++break_turns` (at most 255). A test of the
  mapping during a break: `mapping_test` calls `player_break_leave` before it saves what
  plays, which sets `turn_item` and `shown` to `break_back` (or the playlist's first when
  none) and cuts the break as above; the test then halts, and its end plays it from its
  first frame.
- **`playlist_turn`.** The loop's step for a turn that has not ended gains, while
  `clocks_on` and `break_phase == 0` and `!break_held` and `now >= break_due`: the pause
  at `D = max(break_due, zero)`: `break_back = turn_item`, `break_paused = 1`,
  `break_offset = D - zero`, `break_repeat = turn_repeat`, `break_seed` = `core.seed` when
  the stream open is that turn's widget, else 0; then a clock from `breaks_pick(core, D)`:
  none, and the counts start at `D` with nothing paused; one, and `zero = D`,
  `turn_item` the clock, `turn_repeat = 0`, `++turn_number`, `break_phase = 1`. Where a
  turn ends, by the phase:
  - 0, a playlist turn: `++break_turns` while `clocks_on`; the next position as today
    (the window, `resume_item`, `next_animation`); then, while `clocks_on`, when
    `break_turns >= 5` or `zero >= break_due` (not held): `breaks_pick(core, zero)`; a
    clock begins a break with `break_back` that next position and nothing paused; none
    starts the counts at `zero`.
  - 1, the clock's turn: while `clock_message_on` and `breaks_message` gives one, its
    turn with `turn_repeat = 1` and phase 2; else the break ends.
  - 2: the break ends.
  The break's end at `zero`: `break_phase = 0`; the counts start at `zero`; when the
  window has passed, `rotate` and the new playlist's first, nothing resumed; else, paused:
  `turn_item = break_back`, `zero -= break_offset`, `turn_repeat = break_repeat`,
  `resume_seed = break_seed`; not paused: `break_back` when it plays, else
  `next_animation(break_back)`, else the playlist's first. The window is not rotated at the
  end of a break's turn, only at the break's end.
- **The seed kept.** `show_at`, opening a widget's stream: `core.seed = resume_seed != 0 ?
  resume_seed : clock_seed(...)`, and `resume_seed = 0`. `player_play_all`,
  `player_play_cycle` and `player_halt` clear it.
- **Positions that move.** `player_item_leaves` adjusts `break_back` as it adjusts
  `resume_item`, and when `break_back` is the item that leaves, sets it to the animation
  after it; `player_drive_moved` and `player_drive_shifted` move a drive position in
  `break_back` as they move `turn_item`.
- **`status`** (`commands.cpp`): `"clocks":true|false,"clock_message":true|false` before
  `left`. The turn members need nothing: a break's turn is the playlist's turn.

### Memory

`docs/core.md`'s figure of the core object and the total grow by the new fields; the
suite's memory test with a drive stays within 131,072.

## The firmware tool and the command tool

`firmware/fwtool/storage.py`: `clocks.txt` among the kept and allowed names, as
`repeats.txt`; `install-show` keeps the board's, `read-show` copies it. `odrigctl/cli.py`:
the four lines among its forms.

## The emulator

`emulator/app.py`: `--drive-folder DIR`, refused with `--drive` by the parser; it sets the
drive read-only. `emulator/host.py`: a drive whose folder `odrig` is DIR itself; the
listing, the reads and the limits are the same code. `docs/emulator.md`: the option, the
demo show and its commands, the seek bar after a resumed turn.

`shows/clock-breaks/show.json`: `{"version":1,"brightness":128,"min_seconds":6,"items":[
{"id":1,"file":"hello.odrg"},{"id":2,"file":"dvd.odrg"}]}`, packed as getting-started packs
`shows/demo-20`.

## The app

`app/www/index.html`: `#clocks-panel` after the first panel of `#settings`, hidden, with
`#clocks`, `#clock-message` (in the `label.check` form of `#mapping-cross`) and
`#clocks-said` (`role="status"`). `app/www/screens/clocks.js`: draws from each `status`
(hidden without `clocks`; boxes checked from the members unless a line is out; disabled
while a line is out or the installation does not answer); on `change` sends through
`client.js` `clocks <on|off>` or `clocks message <on|off>`, says the result in
`#clocks-said`, then asks for `status`. `commands.js` and `client.js`: the lines;
`main.js`: the screen's wiring; `style.css` only if needed. Tests in
`tests/app/test_clocks.py`.

## The message

`project-seeds/54-p2-clocks-between-the-animations/source/render-message.mjs`: loads the
page in headless Chrome with a temporary profile (as seed 52's renderer), replaces
`requestAnimationFrame`, `performance.now` and `matchMedia` before the script runs, and
takes the canvas at 0, 50, ... 5,950 ms into a frames JSON of 120 frames of 50 ms; the
converter encodes it, `check` accepts it, `thumbnail --catalog thumbnails --card
collection/card --beside` writes its preview, and its readme is written by hand.

## Tests

- `tests/core/test_clocks.py`: the settings, the file, `status`; on a card with a folder
  `clocks` of three short files and `clocks/message`: the passing over, a break after 5
  turns, the pause at 5 minutes and the resume (a frames file at its frame, a widget with
  its seed, a `repeat` kept), the message once, no clock, each command during a break, the
  window, a restart; the order (each clock once per order) and `shuffle` against the twin;
  a card with and without a catalog; the memory test.
- `tests/emulator/`: `--drive-folder`; a break in a recording of the demo show.
- `tests/app/test_clocks.py`; `tests/firmware/` and `tests/emulator/test_tool.py` for the
  tools.
