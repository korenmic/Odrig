# Brightness edits stay with their animation, and a brightness zoom

## Summary

Two changes to the brightness panel of the operators' app, the browser Controller and the
APK alike. First, a brightness edit stays with the animation it began on. Today, when the
playlist moves on while the operator drags the slider, types a value or presses
`Override for this animation`, the app drops the edit meant for the animation that left
without a word. The rest of the same gesture then becomes an edit of the default brightness
of whatever plays next, which the board does not keep after a restart. So an animation
whose brightness the operator saved comes back with its old value, and after a restart
every redirected change is gone. With this seed a gesture finishes for the animation it
began on, even when that animation no longer plays, and the panel says what was saved and
for which animation. Second, a `Brightness zoom` bar above the brightness slider, with two
pins, `Start` and `End`, that set the range the slider moves through, so that a narrow
range such as 2 to 12 spreads over the slider's whole width. The app keeps the zoom on
the phone. App only: no command, reply, core, firmware or emulator change.

## Priority

`P1`: the saved brightness of seed 58 loses the operator's edits in ordinary use.

## Depends On

- Seed 58: persistent per-animation brightness, `Override for this animation` and its edit
  flow in `app/www/screens/brightness.js`, on `master`.
- Seed 47: the brightness slider and its numeric field, which follow each other.
- Seed 84: a setting the app keeps on the phone for every link, target and board, the
  precedent for keeping the zoom.

## Product Context

- **What the owner saw, 2026-11-24.** After the owner set an animation's brightness with
  `Override for this animation` ticked, the value the app showed when the animation came
  back by itself was not the one left, and still less after a restart of the board.
- **The board keeps overrides.** Audited on 2026-11-24 at 3ab15e17, the head of pull
  request #68 on the fused branch of pull request #63, whose panel code is `master`'s
  seed 58 apart from the line that names the file. Sessions of the core's test host
  saved an override, let the playlist move on by itself and come back, and restarted on
  the same storage: the override returned every time, for an animation of the board's own
  storage, for one of the card read file by file and through its catalog, and through
  clock and message breaks. The firmware writes and reads `brightness.txt` in `/odrig` of
  the board's own storage through the same calls. An emulator restarted on the same
  folder brought the override back.
- **The app loses the edit.** The panel edits the animation that status names when each
  input event arrives. When status names another animation, `draw` cancels the edit in
  progress without a word (`cancelEdit()` at `app/www/screens/brightness.js:85` on
  `master`), and the next input event of the same drag or typing begins a new edit for
  the animation now playing (lines 248 and 265). When that animation has no override, the
  new edit is one of the default brightness, sent at once as `brightness <value>`
  (line 183). Seed 58 kept the default a value of the running board (its requirement 7):
  every start takes `show.json`'s `brightness` again.
- **Reproduced in the real app against the emulator, 2026-11-24.** `red.odrg`, its
  override 25 ticked, turns of 5 seconds. A drag from 25 down to 10 over 6 seconds, across
  the end of `red.odrg`'s turn: `red.odrg` kept 25, the default became 10, and the panel
  ended on `green.odrg` with `Default brightness 10`, the box unticked. Typing 20 just after
  the panel had moved to `green.odrg` also set the default to 20, while `red.odrg` kept its
  override. Typed promptly while `red.odrg` played, 25 was saved for it and came back after
  a restart of the emulator.
- **The zoom.** The useful range is often narrow, such as 2 to 12, and between 4 and 5 a
  finger cannot place the slider over 0 to 255. Asked for by the owner on 2026-11-24 in
  this seed, as an app feature that changes no brightness and no saved setting, kept by
  the app itself without the board.

## Required Behavior

### Edits stay with their animation

1. A brightness gesture is a drag of the brightness slider, from its first movement to its
   release; an edit of the number field, from its first typed character to Enter or Done or
   leaving the field; or a press of `Override for this animation`. When it begins, a
   gesture is bound to the target, to the animation the panel shows, by its id and its
   file, and to the mode the panel shows, `Default brightness` or `This animation's
   brightness`.
2. A change of the animation playing never cancels or redirects a gesture in progress:
   the end of a turn, a clock or message break, the next member of a cycle, another
   controller's `play`, the playlist starting again. Until the gesture ends, the panel
   keeps showing the bound animation and mode, and says when that animation no longer
   plays, for example `Animation 1: red.odrg, no longer playing`. The gesture's values go
   to nothing else.
3. When it ends, a gesture is applied to what it is bound to. A gesture on an override
   saves its value for the bound animation with `brightness <id> <value> save`, which the
   board takes for a listed animation that is not playing. A gesture on the default sets
   the default as it does now, `brightness <value>` while the slider moves, the default
   being one value for every animation without its own. A press of the box saves the
   bound animation's value as the panel showed it when the press began, or removes its
   override. Then the panel goes to the animation playing now and says in one line what was
   saved, and for which animation, for example `Saved 15 for red.odrg.`
4. A gesture whose value is not applied, because another target was chosen, the link was
   lost, the board refused or the reply is uncertain, is said in the panel with the
   animation it was for. Nothing of it goes to another animation or another target, and
   nothing is sent again by itself. Seed 58's other rules stay: late replies never repaint
   another animation or target, queued commands are checked against their capture, and
   fresh status confirms what the board kept.
5. For one second after the panel moves to another animation while no gesture is in
   progress, the slider, the number field and the box take no new gesture, and the panel
   marks the new animation's name as just changed. A touch aimed at the animation that
   just left does not land on the next one.
6. The app learns of a change from status, up to its polling period later. A gesture that
   begins before the panel shows the change is bound to the animation the panel showed:
   the one the operator was looking at.
7. A confirmed change of the default is followed by a line in the panel saying that the
   default applies to every animation without its own brightness and goes back to the
   show's value when the board starts again, and that ticking `Override for this
   animation` keeps a value for the animation playing. The default itself stays a value
   of the running board, as seed 58 has it.

### The brightness zoom

8. A `Brightness zoom` bar stands on its own row directly above the brightness slider, as
   wide as the slider's row, over 0 to 255, with two pins: `Start` and `End`. The slider's
   left end is `Start` and its right end `End`, in steps of 1, so a range of 2 to 12 puts 11
   values over the slider's whole width.
9. The pins move by dragging, in steps of 1, and do not cross: `Start` stays at least 1
   below `End`, so the slider always has at least two values. The bar shows both numbers,
   for example `2 to 12`. Moving both pins to the ends gives 0 to 255 again; there is no
   other control to reset it.
10. Moving a pin changes no brightness, sends nothing to the board and is no brightness
    gesture. The number field still takes 0 to 255 under its present rules.
11. A value outside the zoom, whether the default or an override that status reports,
    another controller's change or a value typed in the number field, stands exactly in
    the number field. The slider rests at the nearest end of the zoom, and the panel says
    that the value is outside it, for example `40 is above the zoom 2 to 12`. The app never
    widens or moves the zoom by itself. A drag of the slider then sets a value inside the
    zoom, as an ordinary gesture.
12. The zoom holds in both modes, for every animation, target and board, and for a target
    that does not save brightness for each animation.
13. The app keeps `Start` and `End` on the phone, in its own storage, as it keeps the
    panel's collapsed state and the filters, and takes them back when it starts. They stay
    through restarts of the app, reconnections and changes of target and board. They are
    never sent to the board, need no command and change no saved brightness. The browser
    Controller keeps its own pair for its page. When that storage is unavailable or holds
    no usable pair, the zoom is 0 to 255 for that run, without an error.
14. The panel keeps its line of label and number field, then the zoom's row, then the
    slider with the box beside it. The pins and the slider keep their touch room of 48
    pixels, with no overlap or sideways overflow at a width of 320 pixels and held
    sideways. The panel stays at the top of the screen under its present rule, while a
    whole row of the list of 80 pixels still fits, with the taller panel; collapsed, it
    hides the zoom with the rest. The pins are named `Brightness zoom start` and
    `Brightness zoom end` for screen readers, and the arrow keys move a pin by 1.

## Technical Constraints

- App only: `app/www/` (the panel's controller, markup and style), the app's tests and
  `docs/android-app.md`. The browser Controller and the APK are one code. No core,
  firmware, emulator, command, reply or `status` change, and no change to how the board
  saves brightness.
- One controller for the slider, the number field, the box and the zoom, built on seed
  58's edit flow. Seed 58's rule that identity changes cancel unsent edits becomes: a
  change of animation cancels no gesture in progress and redirects none, as above; the
  owner approved this on 2026-11-24.
- Built on `master`, as seed 58 is. On pull request #63's branch the panel's code differs
  only in the line that names the file, so the change reaches that branch with little to
  merge.
- Persistence of the default brightness across restarts is not part of this seed: it
  would need a new command form, which the owner has not been asked to approve.

## Open Questions

None. The owner asked on 2026-11-24 for the fix and the zoom in one seed. Decided here:
both parts in one seed, as they share one panel, one controller and its tests; the default
stays a value of the running board; a gesture is bound when it begins and finishes for its
animation; a hold of one second after the panel moves to another animation; one zoom
range for the phone, the same for every target, board, animation and mode; at least two
values in the zoom; no reset control beyond moving the pins to the ends; a value outside
the zoom is shown as it is and never moves the zoom.

## Definition Of Done

1. Browser tests against the real emulator with short turns: a drag, typed digits and a
   press of the box that span a change of animation, at a turn's end and at a clock break.
   The bound animation gets the value, the default and the next animation do not, and the
   panel says what was saved. The one-second hold, a target changed during a gesture, a
   refusal and a lost reply are covered too.
2. Zoom tests: the slider's values over a narrow zoom, pins that do not cross, values
   outside the zoom from status and from the number field, both modes, the pair kept
   across reloads of the app and restarts of the emulator, storage unavailable, and the
   layout at 320 pixels and held sideways with the panel's pinned rule.
3. Each fault test is seen failing first. The app's and the onboarding suites pass by
   discovery, and `docs/android-app.md` describes the bound gesture, the hold, the line
   about the default and the zoom kept on the phone.
4. A signed APK is built by the repository's tools with the persistent key.
5. The owner's phone check stays open until it is performed. With turns of about 30
   seconds: drag an animation's override across the end of its turn and see it saved for
   that animation; see it come back with that value, and again after the board and the app
   restart; set the zoom to 2 to 12, move between 4 and 5, restart the app and find the
   zoom kept. The board's brightness stays at 40 or less during the check.
