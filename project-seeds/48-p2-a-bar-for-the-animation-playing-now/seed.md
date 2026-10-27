# A bar for the animation playing now, and a frozen top

## Summary

The top panel of the operators' app's Animations screen gets a bar of its own for the
animation playing now, between its name and the line that says what plays (`Playlist`):
the actions of that animation's row menu, without Move up and Move down; `Repeat this`
with a number field that sets how many loops the turn now in progress plays, ad hoc, for
that turn alone; and `Save` and `Restore default`, which keep a repeat for every later
turn of that animation, or remove it, on the installation's own storage. The field shows
the turn's own loop count: a saved repeat, or else the show's default, from the item's
`repeat` or the show's minimum and maximum times. The panel, from `Now playing` down to
the brightness slider, stays at the top of the screen while the list below it scrolls.
The core gets the command `repeat` in three forms, a file of saved repeats, and `status`
three members, `repeat`, `loop` and `saved`, which the owner approves by name with this
seed.

## Priority

- `P2`

## Depends On

- Seed 09, the operators' app, for `status` read every second, the request queue and
  the rule that a refusal is said in the app's place for messages.
- Seed 29, for `ignore <id> <0|1>`, and seed 32's quarantine, for the grayed rows.
- Seed 35, for external storage that is read-only and for the card the installation can
  write, whose files `Delete` removes; seed 37, for texts and clocks and their editor; and
  seed 39, for the filters that `Select` sets back to all.
- Seed 36, for the Animations tab, its top panel, `#now-panel`, the rows' `...` menus,
  the selection mode and the look of the app.
- Seed 41, for folder playlists, whose turns this seed's `repeat` acts on like the
  root's.
- Seed 36 also for `order.txt`, the saved order, whose names of card and drive files,
  whose reading at the start and at a drive's take-up, and whose atomic save the file of
  saved repeats follows; and seed 41 for the files `install-show` keeps on the board.
- Seed 44, for the thumbnail of the animation playing now.
- Seed 45, in pull request #15 and not yet on master, for `limits`, for its atomic save
  of a settings file with a `default`, and for its changes to the same core files and
  the core's memory figures. This seed is built from master and needs none of seed 45's
  code; whichever of the two is merged second is brought up to date with the other, and
  the core stays within its memory with both.
- Seed 47, on master as a seed and not built: it turns the number in `Set the brightness
  to N`, above the slider, into a field in the same panel. Whichever of the two is built
  second is brought up to date with the other.

## Product Context

On 2026-10-27 the owner asked for a bar of buttons below `Now playing` with the
thumbnail and the name, and above the `Playlist` line: a bar to manage the animation
playing now, with every button of its row's `...` menu except Move up and Move down, and
with `Repeat this` and a number field that says how many times to repeat that playlist
item right now. The item may already have a repeat value of its own; it shows in the
field as the default, can be changed on the spot, and the change holds only for the
animation's current instance. The owner also asked for everything from the top down to
`Set the brightness` and its slider to stay frozen at the top while the animations below
scroll. The same day the owner approved the command and refined it: every animation
already has a default repeat of its own from the show's minimum and maximum logic; an ad
hoc change holds for the current instance; a `Save` button keeps the value for every
later turn of that animation, and a `Restore default` button brings its default back,
both kept on the installation's storage.

During a show the operator watches the wall, not the list: to keep a good animation on
longer, to drop a bad one, or to fix a text, they had to find its row first, often in
another folder or below the fold. The panel stays in reach and acts on what is on the
LEDs.

## Technical Constraints

- **What a turn's repeat is today: the default.** An animation item of `show.json` may
  have `repeat`, how many times the animation is played through when its turn comes, 1 to
  65,535 (`docs/show.md`); without it the turn is the fewest whole loops lasting the
  show's `min_seconds`, 30 when absent; `max_seconds` cuts a turn, mid-loop if need be. A
  text's loop is its pass, never cut; a clock's loop is its `seconds`, and its seed is
  kept for the whole turn. A cycle has no turn in the playlist. Card and drive
  animations have no `repeat` of their own and follow the `min_seconds` rule. This is
  each animation's default; this seed never writes `show.json` for a repeat, so the
  default stays what the show says. No reply reports a turn's loop count today, no
  command changes it, and the app cannot read `show.json`.
- **The ad hoc repeat**, `repeat <id> <n>`, approved by the owner on 2026-10-27: `<id>`
  the animation `status` names as `animation` and `<n>` a whole number from 1 to 65,535,
  the range of `repeat` in `show.json`. It makes the playlist turn now in progress, the
  turn of `<id>`, `n` loops long, counted from the turn's first frame, the meaning
  `repeat` has in `show.json`. Nothing restarts: the frame on the LEDs, the turn's time
  and a clock's seed go on. When `n` is at or below the loop now playing, the turn ends
  at the end of the loop in progress, never mid-loop, and no later turn is skipped: the
  core keeps the larger of `n` and the loop now playing. The item's `max_seconds` does
  not cut a turn so set. A text counts passes; a clock counts loops of its `seconds`; a
  card or drive animation is accepted like an item; after a `play <id>` jump it acts on
  the jumped turn. The reply is `{"ok":true}`. It is refused in this order:
  `bad-argument` for words that are not one of the three forms or a number out of range;
  `show-invalid` while the show is invalid; `stale`, the code that already means the
  operator's view is out of date, when no playlist turn of `<id>` is in progress: a
  cycle plays, nothing plays, a mapping test shows, or the turn has moved on.
- **Its lifetime.** An ad hoc value holds for the turn in progress only, in memory only:
  it is cleared at that turn's end and by every new turn, whether by `play`, `play all`,
  a folder's `play`, an upload or the quarantine of its file, its removal or `ignore`, a
  card pulled out, a mapping test or a restart. It is kept through `order move`, `on`,
  `off` and `brightness`, and through seed 45's `limits` once both are merged; while the
  LEDs are off or at brightness 0 the loops run in the dark, as playback's time does. It
  writes nothing to storage. A folder playlist whose 24-hour window ends during such a
  turn waits for the turn to end, as it already does, with `left` at 0.
- **Saving a repeat**, `repeat <id> <n> save`: the same `<id>` and `<n>`. It keeps `n` as
  that animation's repeat for every later turn, and acts on its playlist turn in
  progress, when there is one, as `repeat <id> <n>` does. It is about the animation, not
  the turn: it is never refused with `stale`, and is accepted for any animation `list`
  lists, an unavailable one included, and while a mapping test shows. Saving the value
  already saved writes nothing but still acts on the turn in progress.
- **Restoring the default**, `repeat <id> default`: it removes that animation's saved
  repeat; when a playlist turn of `<id>` is in progress, its ad hoc value is dropped and
  the turn goes back to the default count, the larger of that count and the loop now
  playing, or is merely cleared while the loop's length is not yet known. With nothing
  saved it writes nothing.
- **The refusals of the two saving forms**, in this order, as `order move` orders its: `bad-argument`; `show-invalid`; `busy` while a catalog rebuild runs, the
  check after the start has not finished, or an upload is open; `unknown-id` for an id
  `list` does not list; `in-use` for a cycle or a card's folder; `no-space`, for a save
  only, when the saved repeats of card and drive files already fill their 32 places with
  other files, or the file already holds 512 lines once a save has dropped the lines of
  the board's own files that `show.json` no longer names, which it does whenever it finds
  the file full; `storage-error` when the storage fails to read or write the
  file, nothing changing then; a file out of form is no failure, and the save writes it
  anew. Both reply `{"ok":true}`. No new error code
  is added.
- **The file of saved repeats.** `repeats.txt` in the board's own storage, beside
  `order.txt`, written whole as `repeats.part` and renamed, as `order.txt` is written as `order.part`: the old
  file is read and every line copied but this animation's, whose new line takes its
  place or comes at the end. Its form, in lines ended by LF: the header `odrig-repeats 1`,
  then one line for each animation with a saved repeat, `<n> f <name>` for a file of the
  board's own storage by its file name in `show.json`, or `<n> x <name>` for a card or
  drive file by the name the drive gives it, as `order.txt` names it, 1 to 127 bytes
  without NUL, the rest of the line; `<n>` from 1 to 65,535 in decimal without a leading
  zero; at most 512 lines. It is not JSON, because a drive's names may hold bytes the
  core's JSON reader refuses. It is read strictly as a whole: a wrong header or any line
  out of form makes it unreadable, which the log says once, `repeats unreadable`; no
  saved repeat is then in force, and the next save writes the file anew. Of two lines
  for one file the first counts; the core never writes two. A `repeats.part` left by a
  cut is removed at the start. It is read at the start after `order.txt`, in steps when
  a drive is taken up before any of its files joins the playlist, and again wherever
  `order.txt` is read again, after an upload adds an item or a card file, and after an
  upload gives an item another file name.
- **Which animation a saved repeat belongs to: its file name.** Ids are not used,
  because the app gives a new upload the lowest free id, often a deleted animation's.
  So a removal and an upload write nothing more: a removed animation's line stays and
  comes back with its name; re-uploading the same media, or editing a text or a clock,
  keeps it; a new name starts from the default; a card pulled out leaves its lines, and
  a card put back, or `catalog rebuild external`, matches them again by name before any
  file plays; two items naming one file share the value. `ignore`, `order move` and the
  brightness leave saved repeats alone, and cycles have none.
- **Which count a turn plays**, the first that applies: the ad hoc value for the rest of
  its turn; the saved repeat; the item's `repeat` in `show.json`; the fewest whole loops
  lasting `min_seconds`, `max_seconds` cutting. A saved repeat, like an ad hoc one, is
  `n` loops from the turn's first frame and is not cut by `max_seconds`. The division
  that takes off whole rounds after a long gap counts saved repeats, takes the turn with an ad hoc value off before it, and stays
  exact.
- **`status`.** Three members before `left`, which stays last: `repeat`, the loops of the
  playlist turn in progress by that order, a loop cut by `max_seconds` counting as one,
  at most 65,535,000, since `min_seconds` is at most 65,535 and a loop at least 1 ms;
  `loop`, the loop in progress, from 1, at most the same; and `saved`, the saved repeat
  of the animation whose playlist turn is in progress, from 1 to 65,535, or null when
  none is saved. All three are null unless a playlist turn plays and `animation` names
  that turn's animation: at a turn's change, until the new animation's first picture is
  on the LEDs, they are null, so that they never pair one animation with another's
  counts, as `seed` already never does. `repeat` is also null while the loop's length is
  not yet known and nothing was set or saved, and `loop` is then 1. `repeat <id> <n>` is
  refused with `stale` while they are null.
- **The core's memory.** The ad hoc value: one 32-bit value in `Core`, 0 while nothing is
  set, which holds the larger of `n` and the loop in progress and so may exceed 65,535;
  it fits in padding after `turn_item`, leaving the core object's size unchanged. A
  saved repeat of an internal animation: the upper 16 bits of its item's `count`, which
  a `repeat` of at most 65,535 leaves free, every reader of `count` masking them: no
  bytes. Saved repeats of card and drive files: a table of 32 places of 4 bytes in the
  block of the saved order, only on a host with a drive, 128 bytes and a pointer; a
  take-up that matches more than 32 lines uses the first 32 and the log says
  `repeats over`. The ad hoc value is set where a turn's length is made and cleared where
  a turn ends and wherever a new one begins. The core's memory stays within its limits
  with the target mapping, a show of 100 items and a drive: about 130,749 of its 131,072
  bytes with seed 45; `docs/core.md`'s figures follow. The reference player of
  `tests/core/support.py` states the rules a second time, the file included.
- **The firmware tool and the emulator.** `install-show` keeps the board's `repeats.txt`
  when the folder has none, as it keeps `order.txt` and `playlist.txt`, and a folder's
  check accepts the name; `read-show` copies it with every file of the show. The
  emulator writes it in its show folder through its host and needs no code;
  `docs/emulator.md` says so, and that a seek backward in its page, which sends its own
  `play <id>`, starts a new turn and so drops an ad hoc repeat, not a saved one.
- **The bar.** A block `#now-bar` inside the panel's words, after `#now`, the thumbnail
  and the name, and before `#playing`, never inside `#now`; the panel's words take the
  panel's whole width, so that the bar spans it. It shows while a playlist turn plays,
  `playing` being `all` or a folder's id, and the list holds the animation `status`
  names, also while the LEDs are off; it is hidden before the first `status`, while
  nothing plays, while a test or the diagonal shows, while the show is invalid, while a
  cycle plays and while the list does not hold the id. While the installation does not
  answer it dims with the panel and its buttons are disabled, as the rows' `...` is, and
  they are disabled while the selection is locked, as the row menu is. It looks the
  animation up in the whole list, not in the folder shown or the filters, and each of
  its buttons acts on the id it showed when it was drawn, never on one read again at the
  press; it is drawn again only when what it shows changes.
- **Its actions**, on its first line: the actions of that animation's row menu, built
  from the same code with the same rules of when each is offered and disabled, without
  Move up and Move down: for an internal animation `Ignore` or `Restore`, `Select` and
  `Delete`, and `Edit` for a text or a clock without a fault, which stands on the second
  line; for a file on a card the installation can write, `Delete`; for read-only
  external storage, or software that cannot change the animation, one short line of 48
  px instead, `External storage is read-only.` or `This software allows no change.` The
  words are short so that each line fits at 320 px; each button's
  accessible name says it in full with the animation, for example `Ignore 1 hello.odrg in
  playlist`. Each sends what the menu sends: `ignore <id> 1` ends the turn at once and
  the playlist goes on with the next animation, or halts when none is left, and the bar
  follows; `ignore <id> 0` changes nothing that plays; `Delete` asks the menu's question
  and sends `remove <id>`, the playlist going on with the next animation, or dark when it
  was the only one, and a refusal said as today; `Edit` opens the editor on Upload as the
  menu does. `Select` turns the selection mode on with that animation ticked, as the
  menu's Select does: the list goes to the root, where every internal animation stands,
  a filter that hides it is set back to all, and the list scrolls so that the row,
  ticked, stands just below the frozen top; the selection bar, with `Delete selected`
  and `Done`, stands above the list as today and is reached by scrolling up.
- **Repeat this**, on the second line, for every kind of animation, while the
  installation reports `repeat` in `status`: a button `Repeat this` and a field,
  `<input id="repeat-count" type="text" inputmode="numeric" enterkeyhint="done"
  autocomplete="off">`, which takes digits only as they are typed and shows the turn's
  `repeat`, empty with the placeholder `-` while it is null. The button, or Enter or the
  keyboard's Done key in the field, sends `repeat <id> <n>` for the id the bar shows,
  with the text the field holds, although a press of the button has taken the focus
  from the field. Enter and Done never save. Leaving the field sends nothing, so that a
  stray tap never changes what plays. While the field has the focus, no `status`
  rewrites it and the bar stays on the animation it named, as the slider is left alone
  while it is held, `Restore default` keeping the state it had; once the field has been without the focus for a second, its text
  not sent is dropped, and the field and the bar follow `status` again. The moment the
  field lost the focus is taken from the document's `focusout` that `main.js` already
  listens to. A value from 1 to 65,535 is sent; another, or an empty field, is not, and
  the app says `A repeat is 1 to 65,535.` in its place for messages and shows the value
  in force again. After a send the app asks for `status` and says in its place for
  messages `Animation 1 hello.odrg plays 8 loops this turn; loop 3 is playing.` from that
  `status`'s `repeat` and `loop` while it still names the animation and its `repeat` is
  not null, and otherwise `Animation 1 hello.odrg's turn has ended.`; a count of one is
  said in the singular, `1 loop`; a `stale` refusal is said `That animation's turn had
  already ended.` An installation whose `status` has no `repeat` gets no `Repeat this`
  and no field, and is never sent the line.
- **Save and Restore default**, on the third line, for every kind of animation, read-only
  card files included, since their saved repeats are kept in the board's own storage,
  while the installation reports `saved` in `status`: `Save`, `#repeat-save`, and
  `Restore default`, `#repeat-default`, side by side. `Save` sends `repeat <id> <n> save`
  with the field's text, which is the value in force when it was not touched, under the
  same check of 1 to 65,535 and the same sentence for another value. `Restore default` is
  always drawn and is enabled only while `status`'s `saved` is a number; it ignores the
  field, drops any text not sent, and sends `repeat <id> default`. No question is asked
  before either: a saved repeat is small and set again by typing a number, and the
  message names the result. While a line of the bar is out, `Repeat this`, `Save` and
  `Restore default` are disabled, the field is not rewritten and the bar stays on its
  animation. After a reply the field follows `status`, and the app asks for `status` and
  says, its second sentence only while that `status` still names the animation and its
  `repeat` is not null: `Saved: animation 1 hello.odrg plays 5 loops every turn. It
  plays 5 loops this turn; loop 3 is playing.` or `Default restored: animation 1
  hello.odrg plays its own count again. It plays 8 loops this turn; loop 3 is playing.`
  A save after the turn has moved on says only the first sentence. With no reply:
  `No confirmed reply. The saved repeat is read again before another change.` Refusals
  are said by the app's sentences for refusals, with sentences of their own for
  `repeat`'s `no-space`, `The installation has no room for another saved repeat: it
  keeps them for at most 32 files of a card or drive and 512 files in all.`, and
  `in-use`, `That is a cycle or a folder, which keeps no repeat.` Accessible
  names: `Save the repeat of 1 hello.odrg for every turn` and `Restore the default repeat
  of 1 hello.odrg`. An installation whose `status` has no `saved` gets no third line.
- **The bar's size.** While it shows, the bar is three lines of 48 px, 8 px apart, with
  4 px above and below it, at every width from 320 px, while the installation reports
  `repeat` and `saved`; otherwise it is two, its second line holding `Edit` when it
  applies and, while `repeat` is reported, `Repeat this` and the field, and kept empty
  otherwise. It is never one line. Its height thus depends on
  the installation, never on the animation: a playlist that mixes internal, card and text
  files does not move the list under the finger at a turn's change. Its buttons are as
  wide as their words with 8 px and 10 px of padding, at the panel's 17 px letters, and
  the field is 5 em wide with the fields' padding of 14 px and tabular digits, which
  holds `65535`; a count of six or more digits, which a long `min_seconds` can give,
  scrolls within it.
- **The frozen top.** On the Animations screen the panel, `#now-panel`, from `Now
  playing` down to the brightness slider, with the bar and the lines the panel holds
  (`#readiness`, `#test-now` and its `Stop test`, `#silent`), sticks to the top of the
  screen while everything below it, from the storage panel to the end of the list,
  scrolls. The row above it, the app's name with the connection pill, scrolls away, and
  the panel docks right under the band that keeps the room of the phone's status bar,
  at `top: var(--bar-top)`, so that nothing of it goes under the band: the room is the
  list's, and the panel already dims and says so when the installation does not answer.
  The lines the panel holds under the slider, the test's line with `Stop test` and the
  lines of an installation that does not answer, stay in the panel and so stick with it.
  The page keeps scrolling as a whole, by CSS `position: sticky`, so that moving rows,
  the menus and the bars work as they do. The panel is opaque while it sticks, so rows
  that pass under it are not seen through it, and it stays below the top band, the tabs,
  the menus, a lifted row and the app's messages. A field brought into view, and the top
  edge of a row being moved, stop below the frozen panel. The panel sticks only while at
  least one whole row of the list, 80 px, stays visible between it and the tabs, so that
  the list can always be reached; otherwise, held sideways, on a short phone, or while
  the phone's keyboard is open, the whole screen scrolls as today. With the bar's three
  lines, measured in Chrome with the app's style and estimated for the phone's bars, a
  412 x 915 screen keeps four rows or more under the panel; a 360 x 740 screen keeps
  about 155 px in Chrome and about 115 px in the APK with a 24 px status bar and a 16 px
  gesture bar, so that it sticks, and about 27 px less once seed 47's field is built,
  still sticking except with the three-button navigation bar.
- **Events.** The bar's controls listen to `click`, `input` and `keydown` only, and the
  field's leaving is read from `main.js`'s `focusout`: the set of events the app listens
  to, which a test pins, is unchanged.
- **One app.** The emulator's Controller view and the APK show the same bar and the same
  frozen top from the same `app/www`.
- **Where the work goes.** `core/src/commands.cpp`, `player.cpp`, `player.h`,
  `core_state.h`, `order.cpp` and `order.h` or a module of their own for the saved
  repeats, `storage.cpp`, `core.cpp`, `content.cpp` and `catalog.cpp` where `order.txt`
  is read, and the core's tests; `tests/core/host/host.cpp`'s file names;
  `tests/core/support.py`'s reference player, its file and `status`; `odrigctl/cli.py`'s
  forms; `firmware/fwtool/storage.py`'s kept and allowed names and the firmware tool's
  tests; `app/www/index.html`, `screens/show.js`, `commands.js`, `client.js`,
  `messages.js`, `main.js`, `style.css` and their tests, among them
  `tests/app/test_long_press.py`'s fields, the scenarios that press `Select` by its
  words, which name the list's own, and the lists of the panel's buttons. The documents:
  `docs/commands.md`, `docs/core.md`, `docs/show.md`, `docs/emulator.md`,
  `docs/firmware.md`, `docs/android-app.md`, `agent/vocabulary.md`, and
  `docs/decisions.md` with the owner's approval of the forms and the members; the app's
  table of the lines it sends gains the three forms. Rulings beyond this seed go to the
  end of `docs/drifts.md`.

## Required Behavior

1. While a playlist turn plays an animation the list holds, the Animations panel shows
   a bar between its name and the line that says what plays, with that animation's row
   actions except the moves, `Repeat this` with a field showing the turn's loop count,
   and `Save` and `Restore default`; the bar is hidden while nothing, a cycle, a test or
   an invalid show plays.
2. Each action acts on the animation the bar showed, as its row menu's does, with the
   same question before `Delete`; `Select` shows the selection mode with that animation
   ticked in the list.
3. `Repeat this` with a value from 1 to 65,535 makes the turn in progress that many
   loops long, counted from its first frame, or ends it at the end of the loop in
   progress when that loop is already the n-th or later, without a restart, for that
   turn alone, and the app then says how many loops it plays and which is playing; a
   turn that has ended is refused with `stale` and said so; it writes nothing to
   storage.
4. `Save` keeps the field's value as the animation's repeat on the installation's own
   storage, for every later turn and across a restart, and acts on its turn in progress
   as `Repeat this` does; `Restore default` removes it, and the animation's turns, the
   one in progress included, play the show's own count again. Both work for every kind
   of animation the bar shows, by its file name, and never write `show.json`.
5. `status` reports `repeat`, `loop` and `saved` of the playlist turn in progress, and
   null otherwise.
6. On the Animations screen the panel down to the brightness slider stays at the top
   while the rest scrolls, whenever a whole row of the list still fits below it; held
   sideways, on a short phone or with the keyboard open the screen scrolls as today.
7. The bar keeps one height while it shows; the emulator's Controller view and the APK
   show the same; an installation without `repeat` shows the bar without `Repeat this`
   and its field, and one without `saved` without `Save` and `Restore default`; the bar
   is never less than two lines.

## Definition Of Done

1. All test suites that need no board and no phone pass.
   - The core's suite checks: the three forms and their refusals in order; a turn made
     `n` loops long from its first frame; `n` at or below the loop in progress ending the
     turn at that loop's end; `max_seconds` not cutting an ad hoc or a saved repeat; a
     text's passes; a clock's seed kept; a card animation; a jump; every way an ad hoc
     value is cleared and the ways it is kept; a folder's window waiting; saved repeats
     across a restart, by file name, after a removal and an upload, a card pulled out and
     put back and `catalog rebuild external`; the order of the counts; the file's strict
     reading and its log line; a failure and a power cut at every step of a save and of a
     restore; `repeats.part` removed at the start; the 32 places of card and drive files
     and `no-space`; `status`'s `repeat`, `loop` and `saved` against the reference
     player; a loop count above 65,535; the rounds after a long gap; and the memory
     limits.
   - The command tool sends the three forms. The firmware tool's suite checks that
     `install-show` keeps the board's `repeats.txt` and that `read-show` copies it.
   - The app's suite checks in Chrome against the emulator and stand-ins: the bar's place
     and its states; its actions per kind of animation; `Select` from another folder and
     through a filter with the row below the frozen top; `Repeat this` sent by its button
     with the typed text and by Done, and refused with `stale`; the field kept while it
     has the focus and its unsent text dropped a second after it is left; `Save` with
     typed text and with the untouched value; 0, 65,536 and an empty field sending
     nothing; Done never saving; `Restore default` disabled with nothing saved, enabled
     with a saved value, sent, and the field following `status`; their sentences and
     refusals; the buttons disabled while the installation does not answer and while a
     line is out; no question asked; the bar's one height for every kind of animation at
     320, 360 and 740 px; the frozen top at 412 x 915 with the list scrolling under it,
     and at 360 x 740, with no insets and with a 24 px top and 16 px bottom inset,
     sticking exactly when 80 px stay below it; no freeze at 740 x
     360, at 320 x 568 and with the keyboard open; a row moved under the frozen top; and
     the look rules at 320, 360 and 740 px.
2. A new firmware and a new APK are built and put with the artifacts on the share and on
   Drive.
3. The owner checks on a phone against the installation: the bar shows for the
   animation on the LEDs; `Repeat this` with 3 plays it three loops and then the next;
   `Save` with 3 makes its next turn three loops too, also after a restart; `Restore
   default` brings its own count back; `Ignore` moves on at once; the panel stays at the
   top while the list scrolls.

## Open Questions

None. By approving this seed the owner rules on what the working rules reserve for the
owner, as the constraints take it: the forms `repeat <id> <n>`, which the owner approved
on 2026-10-27, `repeat <id> <n> save` and `repeat <id> default`, their replies and
refusals, the `status` members `repeat`, `loop` and `saved`, and the file
`repeats.txt`. The rest follows the app's and the core's existing patterns and is
decided above: the bar's place, its actions and short words on three lines, `Repeat this`
sending on the button or Done and never on leaving the field, `Save` and `Restore
default` without a question, a saved repeat kept by file name for every kind of
animation, at most 32 of them for the files of a card or drive because of the board's
memory, and the frozen panel docking at the top with the app's name scrolling away,
sticking only while a whole row of the list fits under it.

## The Owner's Answers

On 2026-10-27 the owner asked for a buttons bar below `Now playing` with the thumbnail
and the name, and above the `Playlist` line, to manage the animation playing now: every
button of its row's `...` menu except Move up and Move down, and `Repeat this` with a
number field for how many times to repeat that playlist item right now, showing its own
repeat value as the default, changed ad hoc for the current instance only; and for
everything down to `Set the brightness` and its slider to stay frozen at the top while
the list below scrolls.

The same day the owner approved the new command and refined it: each animation already
has a default value for its repeats, from the minimum and maximum logic in place;
editing the value ad hoc changes the current instance of the animation; a `Save` button
makes it permanent for future turns, and a `Restore default` button brings the default
back, both keeping the setting on the installation's storage.
