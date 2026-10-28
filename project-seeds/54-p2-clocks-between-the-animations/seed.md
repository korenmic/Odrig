# Clocks between the animations

## Summary

The 112 clocks of seed 52 are tracked in a folder of their own, the collection's
`card/clocks/`, their path on the card, each with its preview and its readme as the
collection keeps every animation; `collection/card/clocks/message/` holds one more
animation, the installation's name, "זה לא הזמן", that flashes once, made from the
owner's page `horror-text-60x60.html`. The share's collection holds the same files at the
same paths. The emulator gets `--drive-folder`, which takes a folder as the card's
folder `odrig` itself, so that one line shows `collection/card` as a card. The operators' app's
Settings gets a panel `Clocks` with two checkboxes, kept on the installation. With
`Clocks between animations`, a clock of the card's folder `clocks` plays between the
playlist's animations: after every 5 of them, and whenever 5 minutes have passed since
the last clock, when it cuts the animation that plays, which goes on from where it was
cut once the clock is over. The clocks come in a random order that plays each of them
once before a new order is drawn. With `The message after each clock`, the message
flashes once after every such clock. The core gets the commands `clocks on`, `clocks
off`, `clocks message on` and `clocks message off`, the file `clocks.txt` and the
`status` members `clocks` and `clock_message`, which the owner's request of 2026-10-28
approves.

## Priority

- `P2`

## Depends On

- Seed 52, for the 112 files, the picture widgets that play 100 of them, and, by its task
  14, which the owner added on 2026-10-28, the files placed in `collection/card/clocks/`
  with their GIFs, readmes and card paths in `thumbnails/catalog.js`. It is in progress on the branch `seed-52-a-hundred-picture-clocks`, with no pull request yet, as this seed is written. If it
  is not on `master` when this seed's tasks begin, its branch is merged into this seed's
  branch first, and the pull request says so.
- Seed 46, merged in pull request #21: the collection, the standard of its places, its
  readme of 16 lines, `thumbnail --beside`, `env` and `env.template`.
- Seed 41, for the folders of a card as playlists: the tree, the exhausting order, the
  24-hour window and `playlist.txt`.
- Seed 48, for `repeat` and the count of a turn, for `repeats.txt`, whose strict form and
  whose save as a `.part` renamed `clocks.txt` follows, and for `status`'s members of the
  turn in progress.
- Seed 43, for a checkbox of Settings whose value the installation keeps, `Snake 10 is
  cross-wired`, which the two checkboxes follow.
- Seed 37, for the clocks' seed of a turn and the core's noise; seed 44, for the previews
  and `thumbnail --catalog`.
- Seed 50, in progress, changes how the core keeps a drive's files. Nothing of this seed
  keeps a table of a drive's files, and whichever of the two is merged second is brought
  up to date with the other. Seed 45, not built, adds a saved setting and `status`
  members too; whichever of the two is built second follows the other.

## Product Context

The installation is called "זה לא הזמן", "it's not the time". Seed 52 made 112 clocks for
it: 100 from the owner's picture of timekeepers and twelve from the owner's ideas of time
that is not the time. On 2026-10-28 the owner asked, in their words:

> all the clocks animations you've made, they must be tracked and be put in a special
> folder just for them
>
> in settings a new checkbox would be made, when selected/checked, between every
> playlist animation currently playing or at the bare minimum once every 5 minutes
> (even if something is being played and not finished yet) one random animation from
> the clocks playlist/folder/directory must be played. the randomness works like this -
> the entire clocks playlist is taken randomized and each item there is picked by this
> feature till the list is exhausted once, then the playlist is randomized once again
> and items are picked for the checkbox feature once again, this repeats forever. if an
> item is being played while the 5 minutes timer is done, then the playlist item would
> be paused, its offset saved, the single randomized clock item is played and then the
> previously played item is resumed. there is also a bare minimum of 5 non-clock items
> being played before a clock item would be played, but if 5 minutes passed then it
> beats this bare minimum rule.
>
> also add another checkbox for this: make a tracked animation out of this:
> [the page `horror-text-60x60.html` on the Windows computer]
> if the secondary checkbox is checked, then after every clock that msg appears
> flashing once.
>
> this entire thing would be the seed single. when the seed would be s2s'ed, that is
> when your 112 clocks generations are copied into the mirror and the repository and
> starting to get tracked

The owner asked for the seed with no open question: every question is answered here.

Later the same day the owner merged seed 46, pull request #21, the standard of where an
animation is kept, and asked that seed 52 follow it by a task 14 of its own: seed 52
places the 112 files in `collection/card/clocks/`, tracked, and on the share. This seed
checks them there and places the message beside them by the same standard. The owner
also allowed this seed's work to run beside seed 52's, before seed 52 is done.

The page `horror-text-60x60.html` was made by another tool from the owner's conversation
of 2026-10-28. It draws the installation's name in two lines, `זה לא` above `הזמן`, in
bold 15 px Arial on a 60 x 60 canvas, for 6 seconds: the letters come out of the dark,
dip twice in brightness, a scan line passes, a dark red edge sits one pixel behind them,
specks of noise flicker, and the letters fade to a sixth of their light. Its script uses
no random number: the same time gives the same picture. A copy is beside this seed in
`references/`.

## Technical Constraints

- **Where it stands.** On `master` at 6ce30cd, with seed 46's collection and no clock of seed 52 in it. Seed 52's agent makes the 112 files and places them by its task 14. The installation's card
  holds no folder `clocks`; no setting of the core decides anything between two turns.
- **The clocks' folder.** `collection/card/clocks/`, tracked, the folder the owner asked
  for, by the collection's standard of `collection/README.md`: an animation the
  installation is given goes into `card/` at the path it is to have on the card, and the
  clocks' path on the card is `clocks/`.
  - `collection/card/clocks/`: the 112 files of seed 52, by the names seed 52 gave them,
    each with `X.gif` and `X.md`, as seed 52's task 14 places them. No sub-folder but
    `message/`.
  - `collection/card/clocks/message/its-not-the-time.odrg`, the message, with
    `its-not-the-time.gif` and `its-not-the-time.md`, placed as "Adding a later
    conversion" says: `thumbnail ... --catalog thumbnails --card collection/card
    --beside`, its readme of the 16 lines.
  No file is over 50,000,000 bytes, so none is heavy. The first task of this seed's spec
  checks that the 112 are tracked there with the bytes the share holds, and places the
  message.
- **The share.** The share's collection, `E:\artifacts\odrig\collection` on the Windows
  computer and `/Volumes/192.168.0.1/artifacts/odrig/collection` on the first, as `env`
  or `env.template` names it, holds every file of the repository's collection at the
  same paths. This seed adds `card/clocks/message/` with the message, its GIF and its
  readme, and reads it back. Nothing else of the share changes.
- **A card with the clocks.** The installation's card holds 235 animation files today; with
  the 113 of `clocks/` it holds more than the 256 a card without an index takes, and the
  files after the 256th in the listing's order are passed over. Seed 50 lifts the limit
  with an index on the card; until it is on the board, the owner puts on the card the
  clocks and the files to play, at most 256. `docs/microsd.md` says so.
- **The message.** `its-not-the-time.odrg`, a frames animation of 60 x 60, made from the
  page's own script: the page is loaded in a headless Chrome with a temporary profile, its
  `performance.now` and `requestAnimationFrame` replaced by a clock the tool steps, its
  reduced motion off, and the canvas taken at 0, 50, ... 5,950 ms: 120 frames of 50 ms,
  6 seconds, one loop. Its colours are kept as the page draws them: the 8 colours are the
  owner's rule for clocks, and the message, which is not a clock, needs its shades for
  the fades. The converter makes the file from the frames and `check` accepts it; its
  readme names the page as its source. Beside this seed, tracked:
  `references/horror-text-60x60.html`, the page, and `source/render-message.mjs`, the tool
  that renders it, run from `scratch/`.
- **Clocks and the message on a card.** A clock is an animation file directly in the
  sub-folder `clocks` of the card's folder `odrig`, by that name in lower case, on a card
  or a drive with a catalog or without one, that can play: read, available, made for the
  canvas. The message is the first, in the order of their names, of the animation files
  directly in `odrig/clocks/message` that can play. Files in other sub-folders of
  `clocks` are neither. The show's own animations are never clocks. The card's limits
  stay: 256 files, 32 sub-folders, three levels; `clocks` and `clocks/message` are two of
  the sub-folders, at the first and second level.
- **The two settings.** Both are off until they are switched on, and both are kept on the
  installation's own storage across a restart, as the saved order is:
  - `clocks on` switches the clocks between the animations on, `clocks off` off;
    `clocks message on` switches the message after each clock on, `clocks message off`
    off. Each replies `{"ok":true}` once the file is written. The setting that is already
    in force writes nothing and replies the same.
  - Refusals, in this order, as `repeat`'s saving forms order theirs: `bad-argument` for
    words that are not one of the four lines; `show-invalid` while the show is invalid;
    `busy` while a catalog rebuild runs, the check after the start has not finished, or
    an upload is open; `storage-error` when the storage fails to read or write the file,
    nothing changing then, and on a host whose storage cannot be changed. No new error
    code is added.
  - The file `clocks.txt`, in the board's own storage beside `order.txt` and
    `repeats.txt`, in lines ended by LF: `odrig-clocks 1`, then `clocks on` or `clocks
    off`, then `message on` or `message off`; nothing more. It is written whole as
    `clocks.part` and renamed; a `clocks.part` left by a cut is removed at the start. It
    is read at the start, strictly: a missing file is both off; a file out of that form
    is both off, and the log says once `clocks unreadable`; the next change writes it
    anew. A show never names it.
  - `status` gets two members before `left`, which stays last: `clocks` and
    `clock_message`, `true` or `false`, the settings in force. A reply without them
    comes from a player before them.
- **While the clocks are on, the folder is theirs.** Every playlist passes over the folder
  `clocks` and every folder below it, as it passes over an ignored animation: the root's
  walk, a folder's walk, the first animation of a playlist and the whole rounds after a
  long gap. A `play <id>` of a clock or of the message plays its turn as a jump, and the
  playlist goes on after it; a `play <id>` of the folder `clocks` or `clocks/message`
  makes it current, and since it has nothing to play, the root plays in its place, as
  for any folder with nothing to play. While the clocks are off, the folder is a folder of
  the card like any other.
- **A break.** What plays between two turns, or within one, while the clocks are on: one
  turn of a clock, and, while the message is on and there is one, one loop of the
  message after it. The clock's turn is as long as the playlist would make it: its saved
  repeat, else the fewest whole loops that last the show's `min_seconds`, as a card's
  file has no `repeat` and no `max_seconds`; a clock's seed is drawn when its turn
  begins, as always. The message plays once: one loop, a pass for a text, never cut.
- **When a break comes.** The core counts, from the start of the core while the clocks
  are on, from `clocks on`, and from the end of every break:
  - the turns of the playlist that ended, those of a break not counted: a turn that ends
    at its end and a turn a command cuts, by `play`, `ignore`, `remove`, an upload or a
    card pulled out, count one each; a turn a break paused counts once, when it ends;
  - the time of the playlist, in milliseconds of the board's running time, the time the
    LEDs are off included, the time a cycle or a mapping test plays not included.
  A break begins at the end of a turn once 5 turns are counted. It begins in the middle
  of a turn when 5 minutes, 300,000 ms, are counted before 5 turns are: that turn is
  paused at that moment; when the break is over it goes on from the same point of its
  time, with the loop, the frame, the clock's seed and the count of loops a `repeat`
  gave it that it had, and it then lasts the rest of its turn. When the 5 minutes end
  exactly at the end of a turn, the break begins there and pauses nothing. When a break
  is due and no clock can play, no card, no folder `clocks` or none of its files read,
  nothing plays in its place and both counts start again from zero, as after a break.
- **The order of the clocks.** The clocks play in an order drawn at random among all the
  orders of the clocks there are when it is drawn: each break takes the next clock of the
  order; a clock that cannot play when its place comes is passed over, and so is a place
  whose file is no longer there; when the order is used up, a new one is drawn, and the
  last clock of one order may be the first of the next. A new order is drawn at the start,
  when a drive is taken up or dropped, and when the folder's files change. The randomness
  is the core's noise, which the timestamps of the polls stir, as a clock's seed is. The
  core keeps no table of the clocks for it: the order is a permutation drawn from a
  32-bit key, computed for each break, so that the core's memory grows by a few fields
  only, whatever the card holds; the design states the permutation, and the reference
  player of `tests/core/support.py` computes the same.
- **Commands during a break.** A `play` of any kind ends the break at once: the turn it
  paused is not resumed, and what the `play` names plays as it always does. `clocks off`
  and `clocks message off` let the break in progress play to its end, the message as it
  was then, and no break begins after it; `clocks message on` during a clock's turn gives
  that clock its message. `repeat <id> <n>` and its saving forms act on a clock's or the
  message's turn in a break as on any turn of the playlist; `status` reports a break's
  turn as a turn: `animation` names the clock or the message, `repeat`, `loop` and
  `saved` are theirs, and `playing` stays the playlist's, `all` or a folder's id. `on`,
  `off`, `brightness`, `order move`, `ignore` of another animation and the list change
  nothing of a break. When the paused turn's animation is removed, ignored, quarantined
  or leaves with its card during the break, the playlist goes on after the break with
  the animation after it, as when its turn ends. A mapping test during a break ends the
  break; the playlist then plays as after any test, and the paused turn is not resumed.
- **A break and the window of a playlist.** A window that passes during a break is taken
  when the break is over: the paused turn is not resumed, and the next playlist plays
  from its first animation. A restart forgets a break: the playlist begins as at any
  start, and both counts from zero.
- **The core's memory.** The settings, the two counts, the paused turn and the key and
  place of the order are fields of `Core`, a few dozen bytes in all, no block of their
  own. The core stays within its 131,072 bytes with the target mapping, a show of 100
  items and a drive; `docs/core.md`'s figures follow. The whole rounds taken off after a
  long gap are not taken while the clocks are on, since breaks make the rounds unequal;
  the turns are walked one by one then.
- **The emulator.** It plays the breaks through the core and needs no code for them. Its
  seek bar takes the first open of a file after a change as the start of a turn, so after
  a break resumes a turn the bar counts that turn's loop from the moment of the resume
  until the next loop begins; `docs/emulator.md` says so. Its page shows the two
  checkboxes in the Controller view, which is the app.
- **`--drive-folder DIR`.** A new option of the emulator, the other form of `--drive`: DIR
  stands for the card's folder `odrig` itself, not for the top of the card, so that
  `collection/card`, or the share's `card/`, is a card as it is, with nothing copied.
  It cannot be given with `--drive`. A drive given so is always read-only, as
  `--drive-read-only` makes one, so that the emulator never writes into the collection.
  The host serves the folder's files as those of `odrig/`, and the same limits hold: 256
  files, 32 sub-folders, three levels.
- **The demo show.** `shows/clock-breaks/show.json`: `hello.odrg` and `dvd.odrg`, as
  `shows/demo-20` has them, and `min_seconds` 6, which the card's files follow too, so
  that the first break comes after about half a minute. `docs/emulator.md` gives the
  commands that make it and run it with `--drive-folder collection/card`.
- **The firmware tool and the command tool.** `install-show` keeps the board's
  `clocks.txt` when the folder has none, as it keeps `order.txt`, `repeats.txt` and
  `playlist.txt`, and a folder's check accepts the name; `read-show` copies it.
  `odrigctl` sends the four lines.
- **The app.** In Settings, after the first panel, a panel `#clocks-panel` with the title
  `Clocks` and two checkboxes in the form of `Snake 10 is cross-wired`:
  - `#clocks`, `Clocks between animations`, its small line: `After every 5 animations,
    and at least every 5 minutes, a clock of the card's folder clocks plays; an animation
    cut for it goes on where it was.`
  - `#clock-message`, `The message after each clock`, its small line: `The animation of
    clocks/message flashes once after every clock, while clocks between animations is
    on.`
  Each shows the `status` member, sends `clocks on` or `clocks off`, `clocks message on`
  or `clocks message off` when it is changed, at once, as the cross-wired box saves, and
  is disabled while its line is out and while the installation does not answer. A line
  of the panel, `#clocks-said`, says what was saved, `Saved: a clock plays between the
  animations.`, `Saved: no clock plays between the animations.`, `Saved: the message
  flashes after each clock.` or `Saved: no message after the clocks.`, or why it was
  refused, with sentences of its own for `busy`, `show-invalid` and `storage-error` in the
  manner of the mapping panel's; the box then shows the setting in force again. After a
  reply both boxes follow `status`. The panel is hidden while `status` has no `clocks`.
  The boxes listen to `change`, as the cross-wired box does, so the events the app
  listens to stay those a test pins. The emulator's Controller view and the APK show the
  same panel from the same `app/www`.
- **Where the work goes.** `collection/card/clocks/message/`, `thumbnails/`; the emulator's
  `app.py` and `host.py` for `--drive-folder`, and its tests; `core/src/commands.cpp`, `player.cpp`,
  `player.h`, `core_state.h`, `core.cpp`, `storage.cpp` and a module of their own for the
  settings and the order of the clocks, and the core's tests; `tests/core/host/host.cpp`'s
  file names; `tests/core/support.py`'s reference player; `odrigctl/cli.py`;
  `firmware/fwtool/storage.py` and the firmware tool's tests; `app/www/index.html`,
  `screens/`, `commands.js`, `client.js`, `messages.js`, `style.css` and the app's tests;
  `shows/clock-breaks/show.json`. The documents: `docs/commands.md`,
  `docs/show.md`, `docs/core.md`, `docs/emulator.md`, `docs/firmware.md`,
  `docs/microsd.md`, `docs/android-app.md`, `agent/vocabulary.md` with `clock break`,
  `AGENTS.md`'s line, and `docs/decisions.md` with the owner's ruling and a line in its
  change log. Rulings beyond this seed go to the end of `docs/drifts.md`.

## Required Behavior

1. The 112 clocks of seed 52 and the message are tracked in `collection/card/clocks/`,
   each with its GIF and readme, and the share's collection holds the same files.
2. The message is a frames animation of 60 x 60, 6 seconds in 120 frames, made from the
   owner's page and its own script.
3. Settings has the panel `Clocks` with `Clocks between animations` and `The message after
   each clock`; each is kept on the installation across a restart and shows the setting
   in force.
4. While `Clocks between animations` is on, a clock of the card's folder `clocks` plays
   after every 5 turns of the playlist, and when 5 minutes of the playlist have passed
   since the last clock first, in the middle of a turn, which goes on from the same point
   once the clock is over; the folder `clocks` plays only so.
5. The clocks come in a random order in which each plays once before a new order is
   drawn.
6. While `The message after each clock` is on too, the message plays once after every
   such clock.
7. While both are off, nothing plays differently from today.

## Definition Of Done

1. All test suites that need no board and no phone pass.
   - The core's suite checks: the four lines and their refusals in order; `clocks.txt`
     written, read strictly, its log line, `clocks.part` removed, a failure and a power
     cut at each step of a save; the members of `status`; the folder passed over while
     on and played while off; a break after 5 turns, with turns cut by each command
     counted; a break at 5 minutes pausing a frames animation, a text and a clock and
     each resumed at its point with its loop, its seed and its `repeat` count; the 5
     minutes at a turn's end; no clock and both counts from zero; the message once, and
     none without a file; each command during a break; the window passing in a break; a
     restart; the order of the clocks using each once per order against the reference
     player, a clock passed over, a new order at a drive's change; a drive with a catalog
     and one without; the whole rounds while off and none while on; the memory limits.
   - The firmware tool's suite checks that `install-show` keeps `clocks.txt` and that
     `read-show` copies it; the command tool sends the four lines.
   - The app's suite checks in Chrome against the emulator and stand-ins: the panel and
     its two boxes, each sending its line and following `status`, disabled while a line
     is out and while the installation does not answer, a refusal said and undone, and
     the panel hidden for a player without `clocks`; the look rules at 320, 360 and 740
     px.
   - The emulator's suite: `--drive-folder` serving a folder as `odrig/`, read-only,
     refused with `--drive`; the demo show with `collection/card` as its card: a break
     after 5 turns, a clock that is one of the folder's, the message after it, a turn
     cut at 5 minutes and resumed.
   - The converter's suite and the onboarding suite: the message's file accepted by
     `check`, and the collection in git as its standard says.
2. The owner can run the emulator with one line from the documents and see the breaks.
3. A new firmware and a new APK are built and put with the artifacts on the share and on
   Drive by the owner, on the first computer.
4. The owner checks on the installation, with the clocks copied onto its card: the two
   boxes in the app, a clock after 5 animations, a long animation cut at 5 minutes and
   resumed, the message after a clock, and both kept after a restart.

## Open Questions

None. The owner asked for this seed on 2026-10-28 with every question answered by the
agent that writes it, and what the working rules reserve for the owner is ruled by that
request as the constraints state it: the commands `clocks on`, `clocks off`, `clocks
message on` and `clocks message off`, their replies and refusals, the `status` members
`clocks` and `clock_message`, the file `clocks.txt`, and the addition to the decision on
what plays. The rest is decided above: the clocks' folder `collection/card/clocks/` by the
collection's standard, and `--drive-folder` to show it with nothing copied; the clocks
and the message by their folders on the card; the message made
from the page with its own colours; both settings off at first and kept on the board;
the folder passed over while the clocks are on; 5 turns or 5 minutes, counted from the
end of the last break, with the playlist's own time; the turn cut at 5 minutes resumed
at its point; the clock's turn as the playlist would make it and the message once; a
random order drawn with no table; a `play` ending a break; the window taken at a break's
end; and the demo show with a short `min_seconds`.

## The Owner's Answers

On 2026-10-28 the owner asked for the clocks to be tracked in a folder of their own, for
a checkbox in Settings that plays a random clock between the playlist's animations,
after at least 5 of them and at least every 5 minutes, cutting and then resuming an
animation that plays when the 5 minutes end, from an order that uses every clock once
before it is drawn again; and for a second checkbox that makes the message of the page
`horror-text-60x60.html`, made a tracked animation, flash once after every clock. The
owner asked for the seed with zero open questions, answered by the agent, and for the
files to be copied into the share's collection and the repository when the seed is made
into a spec.
