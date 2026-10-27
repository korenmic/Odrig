# A bar for the animation playing now, and a frozen top

## Summary

The top panel of the operators' app's Animations screen gets a bar of its own for the
animation playing now, between its name and the line that says what plays (`Playlist`):
the actions of that animation's row menu, without Move up and Move down, and `Repeat
this` with a number field that sets how many loops the turn now in progress plays, ad
hoc, for that turn alone. The field shows the turn's own loop count, from the show's
`repeat` or the show's minimum time, and can be changed. The panel, from `Now playing`
down to the brightness slider, stays at the top of the screen while the list below it
scrolls. The core gets one command, `repeat <id> <n>`, and `status` two members,
`repeat` and `loop`, which the owner approves by name with this seed.

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
- Seed 44, for the thumbnail of the animation playing now.
- Seed 45, in pull request #15 and not yet on master, for `limits`, and for its changes to
  the same core files and the core's memory figures. This seed is built from master and
  needs none of seed 45's code; whichever of the two is merged second is brought up to
  date with the other, and the core stays within its memory with both.
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
scroll.

During a show the operator watches the wall, not the list: to keep a good animation on
longer, to drop a bad one, or to fix a text, they had to find its row first, often in
another folder or below the fold. The panel stays in reach and acts on what is on the
LEDs.

## Technical Constraints

- **What a turn's repeat is today.** An animation item of `show.json` may have `repeat`,
  how many times the animation is played through when its turn comes, 1 to 65,535
  (`docs/show.md`); without it the turn is the fewest whole loops lasting the show's
  `min_seconds`, 30 when absent; `max_seconds` cuts a turn, mid-loop if need be. A
  text's loop is its pass, never cut; a clock's loop is its `seconds`, and its seed is
  kept for the whole turn. A cycle has no turn in the playlist. Card and drive
  animations have no `repeat` of their own. No reply reports a turn's loop count today,
  and no command changes it; the app cannot read `show.json`.
- **The command**, which the owner approves by name through this seed: `repeat <id>
  <n>`, `<id>` the animation `status` names as `animation` and `<n>` a whole number
  from 1 to 65,535, the range of `repeat` in `show.json`. It makes the playlist turn now
  in progress, the turn of `<id>`, `n` loops long, counted from the turn's first frame,
  the meaning `repeat` has in `show.json`. Nothing restarts: the frame on the LEDs, the
  turn's time and a clock's seed go on. When `n` is at or below the loop now playing,
  the turn ends at the end of the loop in progress, never mid-loop, and no later turn is
  skipped: the core keeps the larger of `n` and the loop now playing. The item's
  `max_seconds` does not cut a turn so set. A text counts passes; a clock counts loops
  of its `seconds`; a card or drive animation is accepted like an item; after a `play
  <id>` jump it acts on the jumped turn. The reply is `{"ok":true}`. It is refused in
  this order: `bad-argument` for words that are not this form or a number out of range;
  `show-invalid` while the show is invalid; `stale`, the code that already means the
  operator's view is out of date, when no playlist turn of `<id>` is in progress: a
  cycle plays, nothing plays, a mapping test shows, or the turn has moved on. No new
  error code is added.
- **Its lifetime.** The value holds for the turn in progress only, in memory only: it is
  cleared at that turn's end and by every new turn, whether by `play`, `play all`, a
  folder's `play`, an upload or the quarantine of its file, its removal or `ignore`, a
  card pulled out, a mapping test or a restart. It is kept through `order move`, `on`,
  `off` and `brightness`, and through seed 45's `limits` once both are merged; while the
  LEDs are off or at brightness 0 the loops
  run in the dark, as playback's time does. Nothing is written to `show.json`,
  `playlist.txt` or `order.txt`. A folder playlist whose 24-hour window ends during
  such a turn waits for the turn to end, as it already does, with `left` at 0.
- **`status`.** Two members before `left`, which stays last: `repeat`, the loops of the
  playlist turn in progress, the value set by `repeat` or else the turn's own count,
  the item's `repeat` or the fewest whole loops lasting `min_seconds`, a loop cut by
  `max_seconds` counting as one, at most 65,535,000, since `min_seconds` is at most
  65,535 and a loop at least 1 ms; and `loop`, the loop in progress, from 1, at most the
  same. Both are null unless a playlist turn plays; `repeat` is also null
  while the loop's length is not yet known and nothing was set, and `loop` is then 1.
- **The core.** One 32-bit value in `Core`, 0 while nothing is set, which holds the larger
  of `n` and the loop in progress and so may exceed 65,535; on the host build it fits in
  padding after `turn_item`, leaving the core object's size unchanged. It is set where a
  turn's length is made and cleared
  where a turn ends and wherever a new one begins; the turn's length is `n` loops while
  it is set, and the division that takes off whole rounds after a long gap is skipped
  while it is set. The core's memory stays within its limits with the target mapping, a
  show of 100 items and a drive; `docs/core.md`'s figures follow when a size changes.
  The reference player of `tests/core/support.py` states the rule a second time.
- **The bar.** A block `#now-bar` inside the panel's words, after `#now`, the thumbnail
  and the name, and before `#playing`, never inside `#now`. It shows while a playlist
  turn plays, `playing` being `all` or a folder's id, and the list holds the animation
  `status` names, also while the LEDs are off; it is hidden before the first `status`,
  while nothing plays, while a test or the diagonal shows, while the show is invalid,
  while a cycle plays and while the list does not hold the id. While the installation
  does not answer it dims with the panel and its buttons are disabled, as the rows' `...`
  is. It looks the animation up in the whole list, not in the folder shown or the
  filters, and each of its buttons acts on the id it showed when it was drawn, never on
  one read again at the press; it is drawn again only when what it shows changes.
- **Its actions.** The actions of that animation's row menu, built from the same code
  with the same rules of when each is offered and disabled, without Move up and Move
  down: for an internal animation `Ignore` or `Restore`, `Select` and `Delete`, and
  `Edit` for a text or a clock without a fault; for a file on a card the installation
  can write, `Delete`; for read-only external storage, or software that cannot change
  the animation, one short line instead, `External storage is read-only.` or `This
  installation's software allows no change here.` The words are short so that the bar
  keeps to two lines; each button's accessible name says it in full with the animation,
  for example `Ignore 1 hello.odrg in playlist`. Each sends what the menu sends:
  `ignore <id> 1` ends the turn at once and the playlist goes on with the next animation,
  or halts when none is left, and the bar follows; `ignore <id> 0` changes nothing that
  plays; `Delete` asks the menu's question and sends `remove <id>`, the playlist going on
  with the next animation, or dark when it was the only one, and a refusal said as
  today; `Edit` opens the editor on Upload as the menu does. `Select` turns the
  selection mode on with that animation ticked, as the menu's Select does: the list goes
  to the root, where every internal animation stands, a filter that hides it is set back
  to all, and the list scrolls so that the row, ticked, stands just below the frozen top;
  the selection bar, with `Delete selected` and `Done`, stands above the list as today and
  is reached by scrolling up.
- **Repeat this.** On the bar's second line, for every kind of animation, while the
  installation reports `repeat` in `status`: a button `Repeat this` and a field,
  `<input id="repeat-count" type="text" inputmode="numeric" enterkeyhint="done"
  autocomplete="off">`, which takes digits only as they are typed and shows the turn's
  `repeat`, empty with the placeholder `-` while it is null. The button, or Enter or the
  keyboard's Done key in the field, sends `repeat <id> <n>` for the id the bar shows,
  with the text the field holds, although a press of the button has taken the focus
  from the field. Leaving the field sends nothing, so that a stray tap never changes what
  plays. While the field has the focus, no `status` rewrites it and the bar stays on the
  animation it named, as the slider is left alone while it is held; once the field has
  been without the focus for a second, its text not sent is dropped, and the field and
  the bar follow `status` again. The moment the field lost the focus is taken from the
  document's `focusout` that `main.js` already listens to. A value from 1 to 65,535 is
  sent; another is not, and the app says `A repeat is 1 to 65,535.` in its place for
  messages. After a send the app asks for `status` and says in its place for messages
  `Animation 1 hello.odrg plays 8 loops this turn; loop 3 is playing.` from that
  `status`'s `repeat` and `loop`; a `stale`
  refusal is said `That animation's turn had already ended.` An installation whose
  `status` has no `repeat` gets no `Repeat this` and no field, and is never sent the
  line.
- **The bar's size.** While it shows, the bar is two lines of 48 px, 8 px apart, at
  every width from 320 px: the first holds the actions that apply or the one short line;
  the second holds `Edit` when it applies, `Repeat this` and the field. A playlist that
  mixes internal, card and text files does not move the list under the finger at a turn's
  change.
- **The frozen top.** On the Animations screen the panel, `#now-panel`, from `Now
  playing` down to the brightness slider, with the bar and the lines the panel holds
  (`#readiness`, `#test-now` and its `Stop test`, `#silent`), sticks to the top of the
  screen while everything below it, from the storage panel to the end of the list,
  scrolls. The row above it, the app's name with the connection pill, scrolls away, and
  the panel docks right under the band that keeps the room of the phone's status bar,
  at `top: var(--bar-top)`, so that nothing of it goes under the band: the room is the
  list's, and the panel already dims and says so when the installation does not answer.
  The lines the panel holds under the slider, the test's line with `Stop test` and the
  lines of an installation that does not answer, stay in the panel and so stick with it. The page keeps scrolling as a
  whole, by CSS `position: sticky`, so that moving rows, the menus and the bars work as
  they do. The panel is opaque while it sticks, so rows that pass under it are not seen
  through it, and it stays below the top band, the tabs, the menus, a lifted row and the
  app's messages. A field brought into view, and the top edge of a row being moved,
  stop below the frozen panel. The panel sticks only while at least two rows of the list,
  150 px, stay visible between it and the tabs; otherwise, held sideways, on a short
  phone, or while the phone's keyboard is open, the whole screen scrolls as today.
- **Events.** The bar's controls listen to `click`, `input` and `keydown` only, and the
  field's leaving is read from `main.js`'s `focusout`: the set of events the app listens
  to, which a test pins, is unchanged.
- **One app.** The emulator's Controller view and the APK show the same bar and the same
  frozen top from the same `app/www`. The emulator runs the same core and needs no code;
  `docs/emulator.md` says that a seek backward in its page, which sends its own `play
  <id>`, starts a new turn and so drops a repeat set by command.
- **Where the work goes.** `core/src/commands.cpp`, `player.cpp`, `player.h`,
  `core_state.h` and the core's tests; `tests/core/support.py`'s reference player and
  `status`; `odrigctl/cli.py`'s forms; `app/www/index.html`, `screens/show.js`,
  `commands.js`, `client.js`, `messages.js`, `main.js`, `style.css` and their tests,
  among them `tests/app/test_long_press.py`'s fields, the scenarios that press `Select`
  by its words, which name the list's own, and the lists of the panel's buttons. The
  documents: `docs/commands.md`, `docs/core.md`, `docs/show.md`, `docs/emulator.md`,
  `docs/android-app.md`, `agent/vocabulary.md`, and `docs/decisions.md` with the
  owner's approval of the command and the members; the app's table of the lines it
  sends gains `repeat <id> <n>`. Rulings beyond this seed go to the end of
  `docs/drifts.md`.

## Required Behavior

1. While a playlist turn plays an animation the list holds, the Animations panel shows
   a bar between its name and the line that says what plays, with that animation's row
   actions except the moves, and `Repeat this` with a field showing the turn's loop
   count; the bar is hidden while nothing, a cycle, a test or an invalid show plays.
2. Each action acts on the animation the bar showed, as its row menu's does, with the
   same question before `Delete`; `Select` shows the selection mode with that animation
   ticked in the list.
3. `Repeat this` with a value from 1 to 65,535 makes the turn in progress that many
   loops long, counted from its first frame, or ends it at the end of the loop in
   progress when that loop is already the n-th or later, without a restart, for that
   turn alone, and the panel then says how many
   loops it plays and which is playing; a turn that has ended is refused with `stale`
   and said so; nothing is saved.
4. `status` reports `repeat` and `loop` of the playlist turn in progress, and null
   otherwise.
5. On the Animations screen the panel down to the brightness slider stays at the top
   while the rest scrolls, whenever two rows of the list still fit below it; held
   sideways, on a short phone or with the keyboard open the screen scrolls as today.
6. The bar keeps one height while it shows; the emulator's Controller view and the APK
   show the same; an installation without `repeat` shows the bar without `Repeat this`.

## Definition Of Done

1. All test suites that need no board and no phone pass. The core's suite checks the
   command and its refusals in order, a turn made `n` loops long from its first frame,
   `n` at or below the loop in progress ending the turn at that loop's end, `max_seconds`
   not cutting it, a text's passes, a clock's seed kept, a card animation, a jump, every
   way the value is cleared and the ways it is kept, a folder's window waiting, `status`'s
   `repeat` and `loop` against the reference player, a loop count above 65,535, and the
   memory limits. The command tool sends the form. The app's suite checks in Chrome
   against the emulator and stand-ins: the bar's place and its states, its actions per
   kind of animation, `Select` from another folder and through a filter with the row
   below the frozen top, `Repeat this` sent by its button with the typed text and by Done,
   refused with `stale`, the field kept while it has the focus and its unsent text
   dropped a second after it is left, the bar's one height, the frozen top at 360 x 740
   with the list
   scrolling under it, no freeze at 740 x 360, at 320 x 568 and with the keyboard open, a
   row moved under the frozen top, and the look rules at 320, 360 and 740 px.
2. A new firmware and a new APK are built and put with the artifacts on the share and on
   Drive.
3. The owner checks on a phone against the installation: the bar shows for the
   animation on the LEDs; `Repeat this` with 3 plays it three loops and then the next;
   `Ignore` moves on at once; the panel stays at the top while the list scrolls.

## Open Questions

None. By approving this seed the owner rules on what the working rules reserve for the
owner, as the constraints take it: the command `repeat <id> <n>`, its reply and its
refusals, and the `status` members `repeat` and `loop`. The rest follows the app's
existing patterns and is decided above: the bar's place, its actions and short words,
`Repeat this` sending on the button or Done and never on leaving the field, and the
frozen panel docking at the very top with the app's name scrolling away, sticking only
while two rows of the list fit under it.

## The Owner's Answers

On 2026-10-27 the owner asked for a buttons bar below `Now playing` with the thumbnail
and the name, and above the `Playlist` line, to manage the animation playing now: every
button of its row's `...` menu except Move up and Move down, and `Repeat this` with a
number field for how many times to repeat that playlist item right now, showing its own
repeat value as the default, changed ad hoc for the current instance only; and for
everything down to `Set the brightness` and its slider to stay frozen at the top while
the list below scrolls.
