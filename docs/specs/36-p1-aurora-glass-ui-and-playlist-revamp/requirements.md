# Requirements: Aurora Glass UI and playlist revamp

The seed is `project-seeds/36-p1-aurora-glass-ui-and-playlist-revamp/`, with the owner's
chosen mockup `aurora-glass-reference.png` beside it and the owner's answers of 2026-10-24
at its end. Where these requirements decide a point the seed leaves open, the decision is
recorded in `docs/drifts.md`.

## 1. The saved playlist order

1.1 The order is a file of the board's own storage, `order.txt`, that the core reads and
writes. It names internal animations by their id and animations of the external storage
(the microSD card, or a USB drive) by their file name, in one mixed order. No other
file and nothing on the external storage holds it.

1.2 The playlist plays its included animations in the saved order: automatic progression,
wrapping from the last to the first, `play all` and the start at power-on (which still
begins with the animation `start` names, when the show names one). `play <id>` goes on
with the animation after it in the saved order. Cycles, their explicit sequences and
their timing do not change.

1.3 An animation the file does not name comes after every animation it names: the
internal ones in the order of `show.json`, then the external ones in the order of their
names. A new upload is therefore last until it is moved.

1.4 An entry whose external animation is absent keeps its place in the file and is
skipped while absent; when a card with that file name is present again, the animation
takes that place again. An entry for an internal id that no longer exists is skipped,
and is dropped the next time the file is written. An upload that reuses such an id
takes that entry's place, before and after a restart alike.

1.5 `order get` and `order get <from>` report the ids of every animation that `list`
lists (internal ones, ignored ones included, and the external storage's), in the saved
order, in parts as `list` does, with a `revision` that changes whenever the order or the
listed animations change.

1.6 `order move <revision> <id> <before>` moves one listed animation, internal or
external, to stand before another listed animation, or at the end with the word `end`,
and saves the whole order durably before it answers `{"ok":true}`. A move that changes
nothing writes nothing. A revision that is not the current one is refused with the new
error `order-conflict` and changes nothing.

1.7 A move preserves the animation whose turn it is, its time in that turn, power,
brightness, every item, file and inclusion flag. Ignored animations keep their place in
the order and stay skipped by automatic playback.

1.8 A power cut at any moment of a move leaves the old order or the new one whole; the
next start removes what an interrupted move left. A failed storage call answers
`storage-error` and leaves the order as it was, in storage and in memory.

1.9 `order move` is refused with `busy` while the startup check runs and while an upload
is open; `show-invalid` while the show is invalid; `unknown-id` for an id that is no
listed animation; `in-use` for a cycle; `bad-argument` for malformed words. It works while
a test animation shows.

1.10 A restart, an app reload, a second controller and the serial port see the same
order and the same revision for the same files.

1.11 The core's memory stays bounded and is asked for only at startup. The order adds at
most two bytes for each item of the item table, and three for each place of a drive, in
one block, and nothing at runtime. A part of the order file is read at most 512 bytes
at a time while the show plays.

## 2. `external` in `list`

2.1 Every animation item of `list` has `external`: `false` for an animation of the board's
own storage, `true` for one of the external storage. Cycles have no `external`. The items,
their order, `next` and the other members are as before, and every reply still fits in
1,024 bytes.

## 3. The test animations in the core

3.1 `mapping test snake <n>`, n from 1 to 20, shows Snake n's test until it is stopped: on
the canvas of the twenty-snake installation, one white line one pixel wide from the bottom
of the snake's first column to the top of its third, 20 pixels in each of its three
columns, through the saved mapping, with every other LED dark. The diagonal stays as it
is under `mapping test on`.

3.2 `mapping get` reports `"snake":<n>` while Snake n shows, `null` otherwise; `test` stays
`true` while either kind of test shows.

3.3 Switching from one test to another keeps the playback selection saved at the first
one; `mapping test off` and an ordinary `play` resume it as for the diagonal. The rules of
entry, busy refusals, power, brightness, current limiting and restart are those of the
diagonal. A test never enters the playlist, `start`, wrapping, a cycle or the saved
order, and changes no file.

3.4 The twenty pictures are encoded by the converter from one tracked JSON source and
embedded in the core beside the diagonal, with a check that they match the converter's
output.

## 4. Routes

4.1 `order get`, `order move` and `mapping test snake <n>` work alike over HTTP, the board's
serial port, the emulator's serial port and TCP, and through `odrigctl`, by the one
command parser of the core.

## 5. The app: navigation and look

5.1 The app has four tabs, Animations, Upload, Settings and Target. Show, Storage and
Mapping do not exist as tabs any more. The look follows the owner's Aurora Glass mockup:
a midnight background with teal and violet accents, translucent rounded panels, a
restrained glow and light text, with every text at a contrast of 7:1 or more and touch
targets of at least 44 pixels.

5.2 The back gesture, the room of the phone's bars, the keyboard's room, the long-press
text rule and the readable messages work as before with the four tabs. The app begins on
Target and goes to Animations at the target's first answer.

5.3 The APK, the browser and the emulator's Controller view run the same files of
`app/www/`.

5.4 Upload holds choosing a video or a GIF, the fit, the part, making the animation with
its progress and Stop, the preview, and uploading with its progress, speed and Cancel,
as the storage screen did; nothing of it stays under the list of animations.

5.5 Target keeps the address, Use, Board, whether the target answers and how requests
travel.

## 6. The app: Animations

6.1 Animations has one compact now-playing area with power, brightness, what plays and
the refreshes, a `Playlist from the start` button, the two capacity lines of seed 28 in a
compact panel, an `Add animation` button that opens Upload, and one list of animations.
Settings has no copy of the power or brightness controls.

6.2 The list shows the animations in the saved order. Each row names its file and its id,
has a two-letter badge, `in` or `ex`, whose accessible description is Internal storage or
External storage (read-only), and a small `...` button at its right. A tap on the row
plays it; the `...` button opens the row's menu and plays nothing.

6.3 The menu of an internal row has Ignore in playlist (or Restore to playlist when
ignored), Move up, Move down, Select and Delete. The menu of an external row has Move up
and Move down and says that external storage is read-only. Ignored rows say Ignored in
words and with an icon, and are muted.

6.4 An inclusion change shows as pending until the target confirms it; a refusal or an
uncertain reply says so and reads the list again. Seed 29's semantics are kept.

6.5 Delete of one row asks first and then removes it. Select starts the selection mode,
which has a checkbox on each internal row, Select all, Clear selection, Delete selected
and Done; the bulk deletion of seed 29 is kept: the question names the count and the
files, batches of at most 32, conflicting controls disabled, partial outcomes reported,
no automatic retry of an uncertain deletion, and the selection cleared on a target
change.

6.6 Capacity is asked at the start, at a reconnection, after uploads and deletions,
also when they failed, and every ten seconds while Animations shows, as before.

## 7. The app: reordering

7.1 A long press on a row of the list lifts it; dragging it moves a placeholder where it
would land, the list scrolls when the finger nears its top or its bottom, and letting go
moves it there. A mouse does the same in a browser and in the emulator's Controller view.
Move up and Move down in the row's menu do the same without a long press.

7.2 A completed move sends one `order move` with the revision of the order the app shows,
shows the row as `Saving…` until the target confirms it, and then reads the list and the
order again. A refusal, an `order-conflict` and a lost reply each say so in words and read
the target again; the app never sends a move again by itself. A cancelled drag, or a drop
where it began, sends nothing.

7.3 Dragging is off, and the list says why, while: the target does not answer, it has no
saved order (an older target), a move, a deletion or an upload is under way, or the
selection mode is on.

7.4 A change of target ends a drag without a move and drops every reply of the old
target.

## 8. The app: Settings and the Tests group

8.1 Settings has a checkbox Show test animations, described as 20 snake tests + diagonal,
off at first and remembered on the device across a reload, and the mapping editor of seed
30 with its draft, Save, Cancel, Restore defaults, Reload, conflict recovery and messages.
The diagonal's buttons and the power and brightness controls leave Settings.

8.2 With the checkbox on, Animations has a pinned Tests group above the list, which can
be collapsed, with exactly 21 entries: Diagonal and Snake 1 to Snake 20. With it off, no
test is listed. The tests are never rows of the list: they cannot be ignored, selected,
deleted or dragged, and the list's order does not include them.

8.3 Pressing a test starts it on the target. While any test shows, on any controller,
the now-playing area says which one, with a Stop test button that resumes playback,
whether the Tests group is shown or not; pressing an animation also ends the test. A
target whose mapping is not the twenty-snake installation gets an explanation in the
Tests group in place of enabled entries.

## 9. Tests, delivery and what stays open

9.1 Core tests cover the order across restarts, absent and returning card entries, new
uploads, removals, stale revisions, interrupted writes at every storage call, playback
order, wrapping, `play all`, the start, the snake tests' pixels through a swapped mapping,
switching tests and their exclusion from every automatic path. Route tests cover HTTP,
serial, TCP and `odrigctl`.

9.2 The app's suite in Chrome against the emulator covers the four tabs, the menu actions,
ignored states, bulk selection and deletion, upload and conversion, drag and the
alternative moves, long lists, conflicts and lost replies, target changes, the Tests
group and its visibility, and phone portrait and landscape sizes, with the earlier
accessibility, long-press, bars and keyboard checks kept.

9.3 Every suite that runs without a board passes; the APK is built with
`python3 app/app.py build` and `tests/apk` passes on it; the firmware is built with
`python3 firmware/fw.py build` and with `--microsd`, so that the core's changes are known
to build for the board.

9.4 Left to the board session: the firmware of the run on the board, the 21 hand-uploaded
line-test files removed from the board, and the order and the tests seen on the LEDs.
Left to the owner: the app on a phone. Neither is claimed from emulator evidence.
