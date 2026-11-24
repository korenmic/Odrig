# Requirements: brightness edits stay with their animation, and a brightness zoom

The seed is `project-seeds/89-p1-brightness-edits-stay-with-their-animation-and-a-zoom/`. It
has no open question. Where these requirements or the design decide a point the seed
leaves open, the decision is recorded at the end of `docs/drifts.md`.

Words used here:

- **The panel**: the brightness part of the panel of what plays on Animations: the line of
  `Default brightness` or `This animation's brightness` with the number field, the
  `Brightness zoom` row, the slider with `Override for this animation` beside it, and the
  lines under them.
- **A gesture**: one drag of the brightness slider, from its first movement to its
  release; one edit of the number field, from its first typed character to Enter, Done or
  leaving the field; or one press of `Override for this animation`.
- **The bound animation**: the animation the panel showed, by its id and its file, when a
  gesture began; **the bound mode**: `Default brightness` or `This animation's brightness`,
  as the panel showed it then; **the bound target**: the installation the app was aimed at
  then.

## 1. A gesture stays with its animation

1.1 When a gesture begins, it is bound to the target, the animation and the mode the panel
shows. The app learns of a change from status, up to its polling period of one second
later: a gesture that begins before the panel shows the change is bound to the animation
the panel showed, the one the operator was looking at.

1.2 While a gesture lasts, a change of the animation that status names, for whatever
reason (the end of a turn, a clock or a message break, the next member of a cycle, a `play`
from another controller, the playlist starting again), neither cancels the gesture nor
gives any of its values to another animation or to another mode.

1.3 While a gesture lasts, the panel shows the bound animation and mode, and the gesture's
value in the slider and the number field. When status names another animation, the line of
the file reads `Animation <id>: <file>, no longer playing`.

1.4 When a gesture ends, it is applied to what it is bound to:

- in `This animation's brightness`, the value is saved for the bound animation with
  `brightness <id> <value> save`, whether that animation plays or not;
- in `Default brightness`, the value is the default, with `brightness <value>`, sent while
  the slider moves as it is today;
- a press of the box that ticks it saves for the bound animation the value the panel showed
  when the press began; one that unticks it sends `brightness <id> default`.

1.5 After a gesture has ended, the panel shows the animation status names now.

1.6 A value saved for the bound animation is confirmed by a later fresh status when status
names that animation, and otherwise by `saved <id>`, whose `brightness` must equal what was
sent (null after a removal).

## 2. What the panel says

2.1 After a confirmed save for an animation the panel says `Saved <value> for <file>.`, and
after a confirmed removal `Removed the saved brightness of <file>.`, `<file>` being the
bound animation's file as the panel showed it.

2.2 After a confirmed change of the default the panel says: `The default, <value>, is for
every animation without its own brightness, until the installation starts again. Tick
Override for this animation to keep a value for the animation playing.`

2.3 A gesture whose value is not applied is said in the panel with the bound animation's
file:

- another target chosen: `Not saved for <file>: another installation was chosen.`;
- status not fresh or the app hidden when it ends: `Not saved for <file>: the
  installation did not answer.`;
- a refusal: `Not saved for <file>.` followed by the text the panel gives that refusal
  today;
- a lost or unreadable reply: `Brightness for <file> is unknown: no reply came. It is not
  sent again.`;
- a read-back that differs: `<file> keeps <value>.`, or `<file> keeps no saved
  brightness.`

2.4 Nothing of a gesture that is not applied goes to another animation or another target,
and nothing is sent again by itself.

2.5 Seed 58's other rules stay: a reply only acknowledges a command, fresh status or
`saved <id>` confirms it; a late reply never repaints another animation or target; an
uncertain save is not repeated; the box is never kept on the phone.

## 3. A hold after the panel moves on

3.1 When the panel comes to show another animation while no gesture lasts, whether
because status named another animation or because a gesture ended, the slider, the number
field and the box take no new gesture for one second.

3.2 For that second, the line of the file is in bold letters.

3.3 A gesture already in progress is not held: 1.2 applies to it.

3.4 The zoom's pins are not held.

## 4. The brightness zoom

4.1 A `Brightness zoom` row stands directly above the brightness slider's row, below the
line of the label and the number field. Its bar has two pins, `Start` and `End`, over 0
to 255, and is as wide as the brightness slider, with the words `Zoom <start> to <end>`
beside it, above `Override for this animation`.

4.2 The brightness slider's left end is `Start` and its right end `End`, in steps of 1.

4.3 The pins move by dragging and with the arrow keys, by 1, and never cross: `Start` stays
at least 1 below `End`, so the slider always has at least two values.

4.4 Moving a pin changes no brightness, sends nothing and is no gesture.

4.5 The number field still takes 0 to 255, under its rules of today.

4.6 When the value the panel shows is outside the zoom, the number field shows it
exactly, the slider stands at the zoom's nearest end, and a line says `<value> is above
the zoom <start> to <end>.` or `<value> is below the zoom <start> to <end>.` The app never
moves or widens the zoom by itself. A drag of the slider then sets a value inside the zoom,
as a gesture.

4.7 The zoom holds in both modes, for every animation, every target and board, and for a
target that saves no brightness for each animation.

4.8 Moving both pins to the ends gives 0 to 255 again. There is no other control to reset
the zoom.

## 5. The zoom kept on the phone

5.1 The app keeps `Start` and `End` in its own storage on the phone, as it keeps the
panel's collapsed state, and takes them back when it starts: after a restart of the app,
a reconnection, a change of target or of board.

5.2 The zoom is never sent to the board, needs no command and changes no saved
brightness.

5.3 The browser Controller keeps its own pair, in the storage of its page.

5.4 When that storage cannot be read or written, or holds no usable pair, the zoom is 0 to
255 for that run, and the app says nothing about it.

## 6. The layout

6.1 The panel's rows are, from the top: the line of the label and the number field, the
zoom's row, the brightness slider with the box beside it, then the lines under them.

6.2 The zoom's bar has the same left and right edges as the brightness slider; its words
stand where the box stands below them.

6.3 The pins, the slider and the box keep a touch room of 48 pixels. Nothing overlaps and
nothing scrolls sideways at 320 pixels wide and held sideways.

6.4 The panel stays at the top of the screen under its present rule, with its new height.
Collapsed, it hides the zoom with the rest.

6.5 The pins are named `Brightness zoom start` and `Brightness zoom end` for screen
readers.

## 7. What stays as it is

7.1 No command, reply, `status` member, core, firmware, emulator or tool changes. The board
saves brightness as it does today.

7.2 The default brightness stays a value of the running board, which takes `show.json`'s
`brightness` again at every start.

7.3 Without a gesture, the panel follows status as it does today: another controller's
change, a reconnection and a reload show what the target reports.

7.4 The browser Controller and the APK are one code.

## 8. Proof

8.1 Browser tests with the stand-in of the app's suite: a drag, typed digits and a press of
the box across a change of animation, at a turn's end and at a clock, in both modes; the
hold; a target chosen during a gesture; a refusal; a lost reply; a read-back that differs.

8.2 Browser tests against the real emulator, with turns of about two seconds: a drag across
the end of a turn, typed digits committed after the end of a turn, and a drag across the
start of a clock break each save their value for the animation they began on, leave the
default as it was, are said in the panel, and are kept by a restart of the emulator. A
press of the box lasts no time: its case, a press while the panel still shows the
animation that has just left, is proven with the stand-in of 8.1.

8.3 Zoom tests: the slider over a narrow zoom, pins that do not cross, values outside the
zoom from status and from the number field, both modes, the pair kept across a reload and
a restart of the emulator, storage that throws, and the layout at 320 pixels and held
sideways with the panel's rule of staying at the top.

8.4 Each fault test is seen failing before its mend. The app's suite and the onboarding
suite pass by discovery. `docs/android-app.md` describes the bound gesture, the lines, the
hold and the zoom.

8.5 A signed APK is built by the repository's tools with the persistent key.

8.6 The owner's phone check stays open until it is performed: with turns of about 30
seconds, an animation's override dragged across the end of its turn is saved for that
animation and comes back with that value, again after the board and the app restart; a
zoom of 2 to 12 lets the slider move between 4 and 5, and is kept after the app restarts.
The board's brightness stays at 40 or less during the check.
