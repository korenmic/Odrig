# Requirements: clocks between the animations

The seed is `project-seeds/54-p2-clocks-between-the-animations/`. It has no open question:
the owner asked for it on 2026-10-28 with every question answered by the agent, and so
ruled on the commands `clocks on`, `clocks off`, `clocks message on` and `clocks message
off`, their replies and refusals, the `status` members `clocks` and `clock_message`, the
file `clocks.txt` and the addition to the decision on what plays. The owner also allowed
the work to run beside seed 52's. Where these requirements decide a point the seed leaves
open, or state one more exactly than it does, the decision is recorded at the end of
`docs/drifts.md`.

Words used here: a **clock** is an animation file directly in the folder `clocks` of a
card's folder `odrig` that can play; the **message** is the first animation file directly
in `odrig/clocks/message` that can play; a **break** is a turn of a clock, followed, while
the message is on and there is one, by a turn of the message; a **playlist turn** is any
turn of the playlist that is not a break's; the **clocks' folders** are `clocks` and every
folder below it; the **counts** are the playlist turns ended and the playlist's time since
the counts last started.

## 1. The files

1.1 The 112 files of seed 52 are tracked in `collection/card/clocks/`, each with `X.gif` and
`X.md` beside it, by the collection's standard of `collection/README.md`, and the share's
collection holds the same bytes at the same paths. Seed 52's task 14 places them; this seed
checks them there.

1.2 `collection/card/clocks/message/its-not-the-time.odrg` is a frames animation of 60 x 60,
120 frames of 50 ms, made from the page `horror-text-60x60.html` by its own script in a
headless Chrome with a temporary profile, the page's clock stepped by the tool, reduced
motion off, its colours as the page draws them. `check` accepts it. Its preview is in
`thumbnails/` with its card path, `its-not-the-time.gif` and `its-not-the-time.md`, the
readme of the 16 lines, are beside it, and the share's collection holds the three files at
the same path.

1.3 The page is beside the seed in `references/`, and the tool that renders it in the seed's
`source/`, tracked.

## 2. The settings

2.1 `clocks on` and `clocks off` switch the clocks between the animations on and off;
`clocks message on` and `clocks message off` switch the message after each clock on and
off. Each replies `{"ok":true}` once its setting is saved. A setting already in force writes
nothing and replies the same.

2.2 Their refusals, in this order: `bad-argument` for words that are not one of the four
lines; `show-invalid` while the show is invalid; `busy` while a rebuild of a catalog runs,
until the check after the start has ended, or while an upload is open; `storage-error`
when the storage fails to write the file or cannot be changed, nothing changing then.

2.3 The settings are kept in `clocks.txt` in the board's own storage: the line
`odrig-clocks 1`, then `clocks on` or `clocks off`, then `message on` or `message off`, each
ended by LF, nothing more. It is written whole as `clocks.part` and renamed; a
`clocks.part` is removed at the start. It is read once at the start: a missing file is both
off; a file out of that form is both off and the log says `clocks unreadable` once; the next
change writes it anew. A power cut at any moment leaves the old settings or the new ones.

2.4 `status` has `clocks` and `clock_message`, `true` or `false`, the settings in force,
before `left`, which stays last.

2.5 While both are off, the player plays as it did before this seed.

## 3. The folders of the clocks

3.1 The clocks' folders are found by their paths in the card's tree, with a catalog or
without one: `clocks` at the first level and `clocks/message` at the second, by those
bytes. The show's own animations are never clocks, nor is a file of another sub-folder of
`clocks`.

3.2 While the clocks are on, every playlist passes over the files of the clocks' folders,
as it passes over an ignored animation: the walk of the root and of a folder, the first
animation of a playlist, and a folder whose files are all in them, which has nothing to
play, so that the root plays in its place. A `play <id>` of one of their files plays its
turn as a jump; a `play <id>` of one of the folders makes it current, and the root plays
in its place.

3.3 While the clocks are off, the clocks' folders are folders of the card like any other.

## 4. When a break comes

4.1 The counts start from zero when the core starts with the clocks on, when `clocks on`
switches them on, at the end of every break, when a break is cut, and when a break is due
and no clock can play.

4.2 A playlist turn counts one when it ends, at its end or cut by a command or an event:
`play`, `play all`, `ignore`, `remove`, an upload, the quarantine of its file or its card
pulled out. A turn a break paused counts once, when it ends.

4.3 The playlist's time is the board's running time while the playlist plays, the time the
LEDs are off included; the time a cycle plays, a test of the mapping shows or nothing plays
is not counted.

4.4 While the clocks are on, a break begins at the end of a playlist turn when 5 turns are
counted, or when 5 minutes, 300,000 ms of the playlist's time, are counted at that end or
before it.

4.5 When the 5 minutes are counted in the middle of a playlist turn, that turn is paused at
that moment and a break begins. When the break is over the turn goes on from the same
point of its time, with the frame, the loop, the clock's seed and the count of loops a
`repeat` gave it that it had, and lasts the rest of its turn. While a frames file comes
back to that point, the player decodes as it does when it is behind.

4.6 When a break is due and no clock can play, nothing plays in its place.

## 5. A break

5.1 The clock's turn is as long as its turn in the playlist would be: its saved repeat, else
the fewest whole loops that last `min_seconds`. The clock's seed is drawn when its turn
begins.

5.2 While the message is on and there is one, the message plays once after the clock: one
loop, a text's pass, never cut.

5.3 After the break the playlist goes on with the paused turn, or with the animation whose
turn was to begin when the break began; when that animation can no longer play, with the
animation after it in the playlist.

5.4 `status` reports a break's turns as turns: `animation` names the clock or the message,
`repeat`, `loop` and `saved` are theirs, and `playing` stays `all` or the folder's id.
`repeat <id> <n>` and its saving forms act on them as on any turn.

5.5 A break is cut, its paused turn not resumed and the counts started anew, by whatever
cuts a playlist turn: a `play` of any kind, `play all`, `ignore`, `remove`, an upload, the
quarantine of its file, its card pulled out; and by a test of the mapping, after which the
playlist plays, from its first frame, the animation the break was to give way to.

5.6 `clocks off` and `clocks message off` let a break in progress play to its end, the
message as it was set then; no break begins after it. `clocks message on` during a clock's
turn gives that clock its message. `on`, `off`, `brightness`, `order move` and `list`
change nothing of a break.

5.7 A playlist's window that passes during a break is taken at the break's end: the paused
turn is not resumed and the next playlist plays from its first animation. A restart forgets
a break.

## 6. The order of the clocks

6.1 The clocks of a break are taken in an order drawn at random among all the orders of the
files directly in `clocks` when it is drawn, each file once. A file that cannot play when
its place comes is passed over. When the order is used up a new one is drawn; the last
clock of one order may be the first of the next.

6.2 A new order is drawn at the start, when a card is taken up or dropped, and when its tree
changes. The randomness is the core's noise.

6.3 The order is a permutation computed from a 32-bit key and the number of files: the core
keeps no table of the clocks.

## 7. The core's memory and time

7.1 The core stays within its 131,072 bytes with the target mapping, a show of 100 items
and a drive; the new state is fields of `Core`, and `docs/core.md`'s figures follow.

7.2 While the clocks are on, the whole rounds taken off after a long gap are not taken; the
turns are walked one by one.

## 8. The emulator and the tools

8.1 `--drive-folder DIR` takes DIR as the card's folder `odrig` itself, read-only always,
with the limits of a card; it cannot be given with `--drive`.

8.2 `shows/clock-breaks/show.json` holds `hello.odrg` and `dvd.odrg` with `min_seconds` 6.
`docs/emulator.md` gives the commands that make it and run it with `--drive-folder
collection/card`; the one line works on Windows.

8.3 The emulator plays the breaks through the core. Its seek bar counts a resumed turn's
loop from the moment of the resume until the next loop begins; `docs/emulator.md` says so.

8.4 `odrigctl` sends the four lines. The firmware tool's `install-show` keeps the board's
`clocks.txt` when the folder has none and a folder's check accepts the name; `read-show`
copies it.

## 9. The app

9.1 Settings has a panel `#clocks-panel`, `Clocks`, after the first panel, with the
checkboxes `#clocks`, `Clocks between animations`, and `#clock-message`, `The message after
each clock`, each with the small line the seed gives it.

9.2 Each box shows its `status` member and sends its line when it is changed, at once; it
is disabled while a line of the panel is out and while the installation does not answer.

9.3 `#clocks-said` says what was saved, in the seed's four sentences, or why it was refused,
with sentences of its own for `busy`, `show-invalid` and `storage-error`; the box then shows
the setting in force again. After a reply both boxes follow `status`.

9.4 The panel is hidden while `status` has no `clocks`. The boxes listen to `change`, so
the events the app listens to are unchanged. The emulator's Controller view and the APK
show the same panel.

## 10. The pages and the checks

10.1 `docs/commands.md`, `docs/show.md`, `docs/core.md`, `docs/emulator.md`,
`docs/firmware.md`, `docs/microsd.md`, `docs/android-app.md` and `agent/vocabulary.md`
(`clock break`) state what this seed adds; `docs/decisions.md` gets the owner's ruling in
its commands bullet and a line in its change log; `AGENTS.md` keeps the seed's line until
it is completed.

10.2 Every suite that runs on Windows passes.

10.3 The owner checks on the installation, with the clocks on its card: the two boxes, a
clock after 5 animations, a long animation cut at 5 minutes and resumed, the message after
a clock, both kept after a restart.
