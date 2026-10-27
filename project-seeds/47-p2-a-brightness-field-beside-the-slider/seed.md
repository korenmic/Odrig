# A brightness field beside the slider

## Summary

The brightness on the top panel of the operators' app's Animations screen becomes
editable as a number too: the number in `Set the brightness to N` turns into a text
field, and the big slider under it stays. The two are synced both ways: moving the slider
writes its value into the field, and typing a value into the field moves the slider; a
typed value is sent when the field is entered or left, by the same path the slider sends
by. Nothing changes in the core, the firmware, the emulator or the command list: the app
sends the same line, `brightness <n>`, as today.

## Priority

- `P2`

## Depends On

- Seed 09, the operators' app, for the brightness slider and its rules of sending (its
  spec's design, "The show screen", and the drift "Seed 09: The controls of the show
  screen"): at most one `brightness` every 200 ms, the value at which the slider is let
  go always sent, a waiting brightness replaced by a newer one, and the slider following
  `status` only when it is not held and a second has passed since this phone's last send.
- Seed 36, for the Animations tab, its top panel, `#now-panel`, and the look of its fields.
- Seed 45, on the branch `seed-45-current-limits` and not yet on master, cited only as the
  pattern of a numeric field this seed follows: its `Current limits` panel,
  `app/www/screens/limits.js`, takes digits only, saves when a field is entered or left,
  says a range under the field and never rewrites a field that has the focus or unsent
  text. This seed is built from master and needs none of seed 45's code; whichever of the
  two is merged second is brought up to date with the other.

## Product Context

On 2026-10-27 the owner asked for the brightness to be editable in a text field where its
number is shown, keeping the big brightness slider, with the two synced so that one
changes the other and the other way round. A slider is quick for a rough setting but hard
to put on an exact value such as 8 or 40 on a phone; a number typed is exact.

## Technical Constraints

- **Where.** In `app/www/index.html` the line `Set the brightness to <span
  id="level-number">` becomes a label and a text field on one line, the field taking the
  span's place and its id, `level-number`; the slider, `#level`, stays full width under
  it and gets the accessible name `Brightness`. The fact `Brightness N` in the panel's
  facts, `#brightness`, which says what the installation reports, is unchanged, so that
  what the installation has stays visible while the operator types.
- **The field.** `<input id="level-number" type="text" inputmode="numeric"
  enterkeyhint="done" autocomplete="off">`, made as the app's whole-number fields are
  (Speed, Pause, the clock's seconds and speeds), with `enterkeyhint` so that the phone's
  keyboard shows Done; its label is `Set the brightness to`. Anything typed or pasted
  that is not a digit is removed as it is typed. Until the first `status` the field is
  empty with the placeholder `-` and the slider stands at 0, as the number and the slider
  are today. The field is never disabled, as the slider is never disabled; it dims with
  the panel while the installation does not answer.
- **The value in force.** The field and the slider compare against one value: the value
  this phone last wrote into the field, by the slider, by a value sent from the field, or
  by following `status`. Before the first `status` there is none, and any value from 0 to
  255 that is committed is sent.
- **When a typed value is sent.** When the field is entered, by Enter or the keyboard's
  Done key, only when its text differs from what the panel last wrote into it, the focus
  staying in the field; and when the field is left with changed text, its `change`. An
  Enter followed by the field's `change` sends once. Never at each keystroke, which would
  light the wall at 2 and 20 on the way to 200. Leading zeros are read away, `080` being
  80 and the field rewritten `80`; a committed value equal to the value in force sends
  nothing.
- **How it is sent.** A typed value is sent as letting go of the slider is: the slider
  is set to the value, and the same `sendLevel` sends it, with its 200 ms spacing, a
  waiting brightness replaced by the newer one, and the value sent again when a second
  or more has passed since this phone's last send. The line is `brightness <n>`, which
  the app sends today; the command list, and the table of the lines the app sends in
  `docs/android-app.md` with its count, are unchanged.
- **Out of range, empty.** A value above 255 is not sent: a line says
  `The brightness is 0 to 255.`, and the field and the slider show the value in force;
  the line goes at the next keystroke or the next value sent. The line stands under the
  slider, so that the slider never moves while it shows; it is a `p` with
  `role="status"` and `aria-live="polite"`. An emptied field sends nothing and shows the
  value in force, without a sentence: an empty field is not 0, because brightness 0
  darkens the wall while it stays on. 0 is shown as `0`.
- **The sync.** The slider writes its value into the field at every move and when it is
  let go, as it writes the number today. While the field holds text not sent, the slider
  follows each whole value from 0 to 255 as it is typed, so the two are seen to move
  together; while the text is empty or above 255 the slider stays where it stands.
  Nothing is sent until the field is entered or left; when that sends nothing, both show
  the value in force. When the slider is moved while the field holds text not sent, the
  slider's move wins, whatever the browser does with the focus: the app's own `input`
  handler of the slider drops the unsent text, takes the focus from the field, which
  closes the keyboard, and writes the slider's value into the field; the slider then
  sends as it does today.
- **Status.** While the field holds text not sent, or has the focus while the phone's
  keyboard is open (the app's typing state), a `status` reply changes neither the field
  nor the slider, as while the slider is held; otherwise both follow `status` by today's
  rule, not held and a second after this phone's last send, so that once the keyboard is
  closed or the field is left they follow the installation again. Enter and Done keep the
  focus, and the app does not close the keyboard itself. The fact `Brightness N` keeps following
  every `status`, so a value set on another phone shows there within two seconds, as
  today.
- **Feedback.** As for the slider: no `Saving` and no `Saved` line; the fact confirms
  within about two seconds; a refusal shows in the app's place for messages; a send
  without a reply is not repeated. Leaving the app with text not sent counts as leaving
  the field when the browser reports it so; a commit made while the app is hidden sends
  nothing, and when the app comes back the field and the slider show the value in force.
  What waits in the app's queue when the app leaves the screen is dropped by the app's
  rule, unchanged; a brightness still waiting out `sendLevel`'s 200 ms at that moment
  goes out when the app comes back, for the field as for the slider today.
- **On a phone.** One line: the label in its lettering of today, `.slider-label`, and the
  field about 5.5 em wide, at least 44 px wide and 48 px high, its digits tabular; the
  slider under it, 8 px apart; every look test passes at 320, 360 and 740 px wide. While
  the keyboard is open the tabs hide and the field is scrolled into view, as for every
  field.
- **Events.** The field listens to `input`, `change` and `keydown` only: the set of
  events the app listens to, which a test pins, is unchanged.
- **One app.** The emulator's Controller view and the APK show the same field from the
  same `app/www`; nothing in `emulator/` changes.
- **Where the work goes.** `app/www/index.html`, `app/www/screens/show.js` and
  `app/www/style.css`; `tests/app/page/reading.js` reads the number from the field's
  value; `tests/app/test_long_press.py` lists the new field first among the page's
  fields; new tests in `tests/app/test_controls.py` with a scenario of their own; the
  slider's tests stay as they are. In `docs/android-app.md`: the Animations bullet of
  "What it is", the table row of the slider (its first column), the sentence on the
  slider in "Using it" step 3, the paragraph that names the fields where a long press
  marks text, step 4 of "The check on a phone" and the brightness in "What is verified". Rulings beyond this seed
  go to the end of `docs/drifts.md`. Nothing in `core/`, `firmware/`, `emulator/`,
  `docs/commands.md` or `docs/core.md` changes.

## Required Behavior

1. The top panel of the Animations screen shows `Set the brightness to` with a text field
   holding the brightness, and the big slider under it; `Brightness N`, what the
   installation reports, stays.
2. Moving the slider writes its value into the field at every move, and wins over text
   typed and not sent; typing a value from 0 to 255 moves the slider to it as it is
   typed.
3. A typed value is sent with `brightness <n>` when the field is entered or left with
   changed text, by the slider's path and its spacing; nothing is sent at a keystroke,
   for a value equal to the value in force, for an empty field, for a value above 255,
   which is said under the slider, or while the app is hidden; in each of these the field
   and the slider show the value in force.
4. A `status` reply rewrites neither the field nor the slider while the field holds text
   not sent or has the focus with the keyboard open; otherwise both follow it as the
   slider does today.
5. The field takes digits only, shows Done on the phone's keyboard, is never disabled,
   and fits the panel on a phone at 320 to 740 px wide with the look rules of the app.
6. The Controller view of the emulator and the APK show the same field; the command list
   is unchanged.

## Definition Of Done

1. All test suites that need no board and no phone pass. The app's suite checks in
   Chrome against a stand-in and the emulator: the field sent by Enter and by leaving it,
   Enter and `change` sending once, the slider following typed values and the field
   following the slider, a slider move dropping unsent text, `080` written `80`, a value
   equal to the value in force sending nothing, an empty field and 256 sending nothing
   with the range said for 256 under the slider, a commit while the page is hidden
   sending nothing, a `status` leaving the field alone while it holds unsent text, the
   spacing of the sends kept, and the field's size and look at 320, 360 and 740 px; the
   slider's tests pass unchanged.
2. A new APK is built and put with the artifacts on the share and on Drive.
3. The owner checks on a phone: typing 8 and pressing Done on the keyboard sets the
   installation to 8, and the slider stands at 8; moving the slider shows its number in
   the field.

## Open Questions

None. Nothing here needs the owner by the working rules: no command is added, no
decision of `docs/decisions.md` changes, and nothing touches hardware or power. The
choices above follow the app's existing slider rules and the pattern of seed 45's
numeric fields.

## The Owner's Answers

On 2026-10-27 the owner asked for the brightness to be editable in a text field where the
number is presented, keeping the big brightness slider too, with the two synced, one
changing the other and the other way round, and for a seed of it.
