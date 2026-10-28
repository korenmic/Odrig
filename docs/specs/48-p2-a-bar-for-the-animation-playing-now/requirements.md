# Requirements: a bar for the animation playing now, and a frozen top

The seed is `project-seeds/48-p2-a-bar-for-the-animation-playing-now/`. It has no open
question: by approving it the owner ruled on the forms `repeat <id> <n>` (approved on
2026-10-27), `repeat <id> <n> save` and `repeat <id> default`, their replies and refusals,
the `status` members `repeat`, `loop` and `saved`, and the file `repeats.txt`, and the
owner ordered it specified and built without a question pass. It is built after seed 47,
on the same branch, and so includes seed 47's field in the panel. Where these requirements
decide a point the seed leaves open, the decision is recorded at the end of
`docs/drifts.md`.

Words used here: a **turn** is a playlist turn of one animation; its **loop** is the
animation's loop: a frames file's length, a text's pass, a clock's `seconds`; the **loop in
progress** is the loop the turn's time lies in, counted from 1; the **default** of an
animation is the count the show gives its turns: the item's `repeat`, else the fewest whole
loops that last `min_seconds`, `max_seconds` cutting. A turn is **reported** while the show
is valid, no test of the mapping shows, the playlist plays, the animation whose turn it is
is the one `status` names as `animation`, and the turn's first refresh has been made.

## 1. The command `repeat`

1.1 `repeat <id> <n>`, `<id>` 1 to 65,535 and `<n>` 1 to 65,535 in decimal, makes the turn
in progress of the animation `<id>`, while it is reported, `n` loops long counted from the
turn's first frame. Nothing restarts: the frame on the LEDs, the turn's time and a clock's
seed go on. The core keeps the larger of `n` and the loop in progress, so that a turn whose
loop in progress is already the `n`-th or later ends at the end of that loop, never in the
middle of one, and no later turn is skipped. `max_seconds` does not cut a turn so set. A
text counts passes, a clock loops of its `seconds`; a card's or a drive's animation is
accepted as an item is; after `play <id>` it acts on the jumped turn. While the loop's
length is not known yet, the loop in progress is the first. The reply is `{"ok":true}`.

1.2 Its refusals, in this order: `bad-argument` for words that are not one of the three
forms or a number out of range; `show-invalid` while the show is invalid; `stale` while no
turn of `<id>` is reported: a cycle plays, nothing plays, a test of the mapping shows, the
show's id is of no animation, or the turn has moved on.

1.3 The value it sets, the **ad hoc value**, holds for that turn only and in memory only.
It is cleared at the turn's end and by every new turn: `play`, `play all`, a folder's
`play`, an upload that replaces or adds the animation whose turn it is, the quarantine of
its file, its removal, `ignore`, a card or drive pulled out, a test of the mapping and a
restart. It is kept through `order move`, `on`, `off` and `brightness`; while the LEDs are
off or dark the loops run on. It writes nothing to storage. A folder's window that ends
during such a turn waits for the turn's end, with `left` at 0.

1.4 `repeat <id> <n> save` keeps `n` as the **saved repeat** of the animation `<id>` for
every later turn, across a restart, and acts on its reported turn, when there is one, as
`repeat <id> <n>` does. It is about the animation, not the turn: it is never refused with
`stale`, it is accepted for every animation `list` lists, an unavailable one included, and
while a test of the mapping shows. Saving the value already saved writes nothing and still
acts on the turn.

1.5 `repeat <id> default` removes the animation's saved repeat. When its turn is reported,
the ad hoc value is dropped and the turn plays its default again: the larger of the
default count and the loop in progress; when the default turn would end at or before the
moment, the turn ends at the end of the loop in progress. While the loop's length is not
known the ad hoc value is merely cleared. With nothing saved it writes nothing.

1.6 The two saving forms are refused, in this order: `bad-argument`; `show-invalid`;
`busy` while a rebuild of a catalog runs, until the check after the start has ended, or
while an upload is open; `unknown-id` for an id `list` does not list; `in-use` for a cycle
or a folder of the card; `no-space`, for `save` only, as 2.5 says; `storage-error` when the
storage fails to read or write the file, nothing changing then. A file out of form is no
failure: the save writes it anew. Both reply `{"ok":true}`. No error code is added.

## 2. The file of saved repeats

2.1 `repeats.txt` in the board's own storage, beside `order.txt`, in lines ended by LF: the
header `odrig-repeats 1`, then one line for each animation with a saved repeat: `<n> f
<name>` for a file of the board's own storage by its file name in `show.json`, or `<n> x
<name>` for a card's or a drive's file by the name the drive gives it, as `order.txt` names
it, 1 to 127 bytes without NUL; `<n>` 1 to 65,535 in decimal without a leading zero; at
most 512 lines. It is not JSON.

2.2 It is read strictly as a whole: a wrong header or any line out of form makes it
unreadable, which the log says once for that reading, `repeats unreadable`; no saved
repeat is in force then, and the next save writes the file anew. Of two lines for one file
the first counts; the core never writes two. A missing file holds no saved repeat.

2.3 It is written whole as `repeats.part` and renamed, as `order.txt` is: the old file is
read and every line copied but those of this animation, whose new line takes the place of
the first of them or comes at the end; a restore copies every line but this animation's. A
power cut at any step leaves the old file or the new one whole. A `repeats.part` left by a
cut is removed at the start.

2.4 It is read at the start after `order.txt`; for a drive, in steps after the drive's part
of `order.txt` and before any of its files joins the playlist; and again wherever
`order.txt` is read again: after an upload adds an item or a card file, after a rebuild of
the drive's catalog, and also after an upload gives an item another file name.

2.5 A save is refused with `no-space` when it would add a card's or a drive's file while the
saved repeats of the drive's files in memory fill their 32 places with other files, or when
the file already holds 512 lines of other animations once the save has dropped the lines of
the board's own files that `show.json` no longer names, which it does whenever it finds the
file full.

2.6 A saved repeat belongs to the file name, not the id. A removal and an upload write
nothing to the file: a removed animation's line stays and comes back with its name;
re-uploading under the same name, or editing a text or a clock, keeps it; a new name starts
from the default; a card pulled out leaves its lines, and a card put back, or a rebuild of
the drive's catalog, matches them again by name before any of its files plays; two items
that name one file share the value. `ignore`, `order move` and the brightness leave saved
repeats alone; cycles have none.

2.7 A take-up of a drive that matches more than 32 lines uses the first 32 and the log says
`repeats over`.

## 3. Which count a turn plays

3.1 The first that applies: the ad hoc value, for the rest of its turn; the saved repeat;
the item's `repeat`; the fewest whole loops that last `min_seconds`, `max_seconds` cutting.
A saved repeat, like an ad hoc one, is `n` loops from the turn's first frame and is not cut
by `max_seconds`.

3.2 The division that takes off whole rounds of the playlist after a long gap counts saved
repeats, takes the turn with an ad hoc value off before it, and stays exact.

## 4. `status`

4.1 Three members after `seed` and before `left`, which stays last:

- `repeat`: the loops of the reported turn by the order of 3.1, a loop cut by
  `max_seconds` counting as one, at most 65,535,000; `null` while the loop's length is not
  known and nothing was set or saved;
- `loop`: the loop in progress, from 1, at most `repeat`; 1 while the length is not known;
- `saved`: the saved repeat of the animation whose turn is reported, 1 to 65,535, or `null`
  when none is saved.

4.2 All three are `null` while no turn is reported: at a turn's change until the new
animation's first refresh, so that they never pair one animation with another's counts.

## 5. The core's memory

5.1 The ad hoc value is one 32-bit value in `Core`, 0 while nothing is set, which may
exceed 65,535; the core object stays within its 4,096 bytes. A saved repeat of an internal
animation is the upper 16 bits of its item's `count`, which every reader of `count` masks.
The saved repeats of the drive's files are a table of 32 places of 4 bytes in the block of
the saved order, only on a host with a drive.

5.2 No memory is asked for after the start. With the target mapping, a show of 100 items
and a drive the core asks for less than 131,072 bytes; `docs/core.md`'s figures are what
the suite measures.

5.3 The reference player of `tests/core/support.py` states the rules a second time for the
board's own files: the three forms, the file, the counts and the three members.

## 6. The tools

6.1 The command tool sends the three forms: `repeat ID N`, `repeat ID N save` and `repeat
ID default`.

6.2 `install-show` keeps the board's `repeats.txt` when the folder has none, as it keeps
`order.txt` and `playlist.txt`, a folder's check accepts the name, and `read-show` copies
it with every file of the show.

6.3 The emulator writes the file in its show folder through its host and needs no code.
`docs/emulator.md` says so, and that a seek backward in its page, which sends its own
`play <id>`, starts a new turn and so drops an ad hoc repeat, not a saved one.

## 7. The bar

7.1 A block `#now-bar` in the panel's words, after `#now` and before `#playing`, never
inside `#now`; the panel's words take the panel's whole width. It shows while a playlist
turn plays, `playing` being `"all"` or a folder's id of the list, and the whole list holds
the animation `status` names, also while the LEDs are off. It is hidden before the first
`status`, while nothing plays, while a test or the diagonal shows, while the show is
invalid, while a cycle plays and while the list does not hold the id.

7.2 While the installation does not answer it dims with the panel and its buttons are
disabled, as the rows' `...` is; they are disabled while the selection is locked, as the
row menu's are.

7.3 It looks the animation up in the whole list, not in the folder shown or the filters.
Each of its buttons acts on the id it showed when it was drawn; it is drawn again only when
what it shows changes.

7.4 Its first line holds the actions of the animation's row menu, made by the same code
with the same rules of when each is offered and disabled, without `Move up` and `Move
down`, in short words: for an internal animation `Ignore` or `Restore`, `Select` and
`Delete`, with `Edit` for a text or a clock without a fault on the second line; for a file
of a card the installation can write, `Delete`; for read-only external storage, or
software that cannot change the animation, one line of 48 px instead: `External storage is
read-only.` or `This software allows no change.` Each button's accessible name says it in
full with the animation: `Ignore 1 hello.odrg in playlist`, `Restore 1 hello.odrg to
playlist`, `Select 1 hello.odrg`, `Delete 1 hello.odrg`, `Edit 1 hello.odrg`.

7.5 Each sends what the menu sends: `ignore <id> 1`, which ends the turn at once, the bar
following; `ignore <id> 0`; `Delete` asks the menu's question and sends `remove <id>`, a
refusal said as today; `Edit` opens the editor on Upload as the menu does. `Select` turns
the selection mode on with that animation ticked: the list goes to the root, a filter that
hides the animation is set back to All, and the list scrolls so that the ticked row stands
just below the frozen top; the selection bar stands above the list as today.

## 8. Repeat this, Save and Restore default

8.1 On the second line, for every kind of animation, while the installation reports
`repeat` in `status`: a button `Repeat this` and the field `<input id="repeat-count"
type="text" inputmode="numeric" enterkeyhint="done" autocomplete="off">`, which takes
digits only as they are typed and shows the reported `repeat`, empty with the placeholder
`-` while it is `null`. An installation whose `status` has no `repeat` gets neither and is
never sent the line.

8.2 The button, or Enter or Done in the field, sends `repeat <id> <n>` for the id the bar
shows with the text the field holds, although a press of the button took the focus from
the field. Enter and Done never save. Leaving the field sends nothing.

8.3 While the field has the focus, no `status` rewrites it and the bar stays on the
animation it named, `Restore default` keeping its state; once the field has been without
the focus for a second, its text not sent is dropped and the field and the bar follow
`status` again. The moment the field lost the focus is taken from the `focusout` that
`main.js` already listens to.

8.4 A value from 1 to 65,535 is sent; another, or an empty field, is not: the app says `A
repeat is 1 to 65,535.` in its place for messages and shows the value in force again.

8.5 After a reply the app asks for `status` and says, from that `status`, while it still
names the animation and its `repeat` is not `null`: `Animation 1 hello.odrg plays 8 loops
this turn; loop 3 is playing.`, a count of one said `1 loop`; otherwise `Animation 1
hello.odrg's turn has ended.` A `stale` refusal is said `That animation's turn had already
ended.`

8.6 On the third line, for every kind of animation, read-only card files included, while
the installation reports `saved`: `Save`, `#repeat-save`, and `Restore default`,
`#repeat-default`, side by side. `Save` sends `repeat <id> <n> save` with the field's text,
the value in force when it was not touched, under the check of 8.4. `Restore default` is
always drawn and enabled only while `saved` is a number; it ignores the field, drops any
text not sent, and sends `repeat <id> default`. No question is asked before either. An
installation whose `status` has no `saved` gets no third line.

8.7 While a line of the bar is out, `Repeat this`, `Save` and `Restore default` are
disabled, the field is not rewritten and the bar stays on its animation. After a reply the
field follows `status`, and the app asks for `status` and says, the second sentence only
while that `status` still names the animation and its `repeat` is not `null`: `Saved:
animation 1 hello.odrg plays 5 loops every turn. It plays 5 loops this turn; loop 3 is
playing.` or `Default restored: animation 1 hello.odrg plays its own count again. It plays
8 loops this turn; loop 3 is playing.` Without a reply: `No confirmed reply. The saved
repeat is read again before another change.` Refusals are said by the app's sentences,
with two of their own for `repeat`: `no-space`, `The installation has no room for another
saved repeat: it keeps them for at most 32 files of a card or drive and 512 files in
all.`, and `in-use`, `That is a cycle or a folder, which keeps no repeat.`

8.8 Accessible names: `Repeat this` is `Repeat 1 hello.odrg this turn`, the field `Loops of
1 hello.odrg this turn`, `Save the repeat of 1 hello.odrg for every turn` and `Restore the
default repeat of 1 hello.odrg`.

## 9. The bar's size

9.1 While it shows, the bar is three lines of 48 px, 8 px apart, with 4 px above and below
it, at every width from 320 px, while the installation reports `repeat` and `saved`;
otherwise two, the second holding `Edit` when it applies and, while `repeat` is reported,
`Repeat this` and the field, and kept empty otherwise. It is never one line: its height
depends on the installation, never on the animation.

9.2 Its buttons are as wide as their words with 8 px and 10 px of padding at the panel's 17
px letters; the field is 5 em wide with the fields' padding of 14 px and tabular digits,
which holds `65535`; a longer count scrolls within it.

## 10. The frozen top

10.1 On the Animations screen the panel `#now-panel`, from `Now playing` down to the
brightness slider, with the bar and the lines the panel holds, sticks to the top while
everything below it scrolls, by CSS `position: sticky` at `top: var(--bar-top)`; the row
with the app's name scrolls away. The page keeps scrolling as a whole.

10.2 While it sticks it is opaque, and it stays below the top band, the tabs, the menus, a
lifted row and the app's messages. A field brought into view, and the top edge of a row
being moved, stop below it.

10.3 It sticks only while at least 80 px, one whole row of the list, stay between it and
the tabs; otherwise, held sideways, on a short phone or while the keyboard is open, the
whole screen scrolls as today.

10.4 The bar's controls listen to `click`, `input` and `keydown` only: the set of events the
app listens to, which a test pins, is unchanged.

## 11. One app, the documents and the tests

11.1 The emulator's Controller view and the APK show the same bar and frozen top from the
same `app/www`. The table of the lines the app sends gains the three forms.

11.2 The documents: `docs/commands.md`, `docs/core.md`, `docs/show.md`, `docs/emulator.md`,
`docs/firmware.md`, `docs/android-app.md`, `agent/vocabulary.md`, and `docs/decisions.md`
with the owner's approval of the forms, the members and the file.

11.3 The core's suite checks every point of sections 1 to 5, the command tool its three
forms, the firmware tool's suite that `install-show` keeps the board's `repeats.txt` and
that `read-show` copies it, and the app's suite in Chrome against the emulator and
stand-ins every point of sections 7 to 10, as the seed's definition of done lists them.

11.4 Every suite that works on this computer passes. A new firmware is built to prove it
compiles and is neither flashed nor uploaded; a new APK is built and put with the artifacts
on the share and on Drive. The owner's checks on a phone against the installation are left
open, and need a firmware with this seed on the board; the seed stays `in_progress` until
they are made.
