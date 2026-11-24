# Design: brightness edits stay with their animation, and a brightness zoom

Requirements: [requirements.md](requirements.md). The seed is
`project-seeds/89-p1-brightness-edits-stay-with-their-animation-and-a-zoom/`.

## Where it is built

On the branch `seed-89-brightness-edits-and-zoom`, made from `seed-87-live-mirror` at
3ab15e17, the newest tip of the stack on `master` (pull request #68 on pull request #63's
branch), with `master`'s commit of the seed merged in (124fc998). The owner asked on
2026-11-24 for the pull request on top of that tip; the seed's "Built on `master`" gives way
to it. The panel's code on this branch is `master`'s seed 58 with the line of the file
written by `playingFile`.

## The fault, in the code of today

`app/www/screens/brightness.js` keeps `edit`, the snapshot taken at the first input event,
and `binding`, the key of the identity the panel shows. `draw` calls `cancelEdit()` when
the key changes, which drops the edit without a word and sets `edit` to null. The next
input event of the same drag or typing takes a new snapshot of the animation now playing;
when it has no override, `sendLevel` sends the value as the default. `client.js`'s
`capturedBrightness` refuses as `stale` any command whose snapshot's animation, file or
override no longer match status, so a save released just after a change is dropped too.

## The gesture

`brightness.js` replaces `edit` with `gesture`, null or:

```js
{kind: "slide" | "type" | "box",
 bound: {version, animation, file, fileText, override},
 value}
```

`bound` is taken from status when the gesture begins: `version` is
`client.targetVersion()`, `animation` and `file` are status's, `fileText` is the text of the
line of the file as the panel shows it, `playingFile(status, client.clockStorageOf(status))`,
and `override` is `status.dimming?.saved != null`.

- A slide begins at the slider's first `input` event and ends at its `change` event.
- A typed edit begins at the field's first `input` event and ends at Enter or the field's
  `change` event, through `commitLevel`.
- A press is a gesture that begins and ends with the box's `change` event, through
  `switchOverride`; its `value` is `status.dimming.value` at that moment.

`draw` while a gesture lasts:

- When `client.targetVersion()` differs from `bound.version`, or status is no longer fresh,
  the gesture ends at once without being applied, its line kept over the panel's next move
  (requirement 2.3); a held draft so never outlives uncertainty, as seed 58 has it.
- Otherwise nothing of the gesture changes: the label follows `bound.override`, the line of
  the file is `Animation <bound.animation>: <bound.fileText>`, followed by `, no longer
  playing` when status names another animation or file, and the slider and the field keep
  the gesture's value. `binding` keeps the bound key until the gesture ends.

The value of a slide is the slider's value at each `input` event, kept in `gesture.value`;
the value of a typed edit is the field's number. `sendLevel(value)` takes it as its argument
and never reads the slider again, since the zoom of this seed clamps the slider's own value.

## Applying a gesture

`finish(gesture)` runs when the gesture ends:

1. The app is hidden, the link does not answer or status is not fresh: not applied, the
   line `Not saved for <fileText>: the installation did not answer.`
2. In the bound mode `This animation's brightness` a slide or a typed edit calls
   `mutate(value, bound, value)`; a press calls `mutate(value, bound, enable ? value : null)`;
   in `Default brightness` a slide or a typed edit sends the default as today, through
   `client.setBrightness(value, bound)`, throttled every 200 ms while the slider moves.
3. `gesture` becomes null, and the next `draw` shows the animation status names.

`mutate` keeps its single `pending` request. Its guard no longer compares the captured key
with the current one: it refuses only while another request is pending, the app is hidden
or status is not fresh.

`client.js`:

- `capturedBrightness(snapshot, carry)` refuses as `stale` when the target changed, the link
  does not answer or status is not fresh; and, when status still names the snapshot's
  animation and file, when its override no longer matches the snapshot's. When status names
  another animation the command goes: a save or a removal names its animation by id, and the
  default is one value for every animation.
- `brightnessSaved(id, snapshot)` is new: `saved <id>` through
  `requestOperation("brightness-edit", ...)` under the same check, giving
  `{brightness, repeat, start}`.

## Confirming

A request keeps `count`, the status count when its reply came. At the first later fresh
status:

- a default request is confirmed when `status.brightness` equals its value, as today;
- a save or a removal is confirmed by status when status names the bound animation and
  file: `status.dimming.saved` equals what was sent;
- otherwise the app reads `saved <bound.animation>` and compares its `brightness`.

A pending request is no longer finished when the identity changes; it is finished when the
target changes. While it is pending the panel shows the animation status names, with the
controls disabled and `Saving brightness; waiting for confirmed status.` as today.

## The lines

`note` holds the panel's line, under the same precedence as today: no fresh status,
no support, damaged settings and no file outrank it. The texts are those of requirement 2:

| Case | Line |
|---|---|
| Save confirmed | `Saved <value> for <fileText>.` |
| Removal confirmed | `Removed the saved brightness of <fileText>.` |
| Default confirmed | `The default, <value>, is for every animation without its own brightness, until the installation starts again. Tick Override for this animation to keep a value for the animation playing.` |
| Another target | `Not saved for <fileText>: another installation was chosen.` |
| No fresh status or hidden | `Not saved for <fileText>: the installation did not answer.` |
| Refusal | `Not saved for <fileText>. ` and the refusal's text of `REFUSALS` |
| No reply | `Brightness for <fileText> is unknown: no reply came. It is not sent again.` |
| Read-back differs | `<fileText> keeps <value>.` or `<fileText> keeps no saved brightness.` |

`note` is set after the panel has moved to the animation status names, so the move does not
clear it; a new gesture or the next move clears it.

## The hold

`holdUntil` is a time. When `draw` finds that the panel comes to show another animation,
no gesture lasting, it sets `holdUntil` to now and 1,000 ms, and a timer draws again when
it ends. "Another animation" means that the panel showed an animation with an id and a file
on the same target and now shows a different id or file: the first status after a start, a
reload or a change of target sets no hold.

While `performance.now() < holdUntil`, the slider, the field and the box are disabled and
the line of the file has the class `just-changed`, bold. The zoom's pins are never held.

## The zoom

`app/www/zoom.js`, without any element:

```js
export const KEY = "odrig.brightness-zoom";
export const FULL = {start: 0, end: 255};
export function load(storage)          // the kept pair, or FULL
export function save(storage, range)   // writes "<start> <end>"; a failure is ignored
export function moved(range, which, to) // the pair with one pin moved, never crossing
export function place(value, range)    // "below", "above" or null
export function words(range)           // "Zoom <start> to <end>"
export function outside(value, range)  // the line of requirement 4.6, or null
```

`load` takes a pair `"<start> <end>"` of whole numbers with `0 <= start < end <= 255`, and
anything else, or a storage that throws, as `FULL`. `brightness.js` reaches the storage
through a function that gives `window.localStorage` or null when reaching it throws.

Markup, in `#now-panel` between `#level-line` and `#level-controls`:

```html
<div id="level-zoom" role="group" aria-label="Brightness zoom">
<div id="level-zoom-bar">
<input id="level-zoom-start" type="range" min="0" max="255" step="1" value="0" aria-label="Brightness zoom start">
<input id="level-zoom-end" type="range" min="0" max="255" step="1" value="255" aria-label="Brightness zoom end">
</div>
<p id="level-zoom-said" class="small">Zoom 0 to 255</p>
</div>
```

and `<p id="level-zoom-outside" class="small" role="status" aria-live="polite" hidden>`
after `#level-range`.

The two inputs lie over each other in `#level-zoom-bar`, 48 pixels high, the bar's width.
They take no pointer themselves (`pointer-events: none`); their thumbs do. A thumb is a
touch area of 48 by 48 pixels whose visible pin is a disc in its middle. When the pins
touch, the one that can move away is on top: `Start` when both are in the upper half of 0
to 255, `End` otherwise. The bar draws a thin track and the part between the pins in the
accent colour, from two custom properties the controller sets in percent.

An `input` event of a pin calls `moved`, sets both pins, the slider's `min` and `max`, the
words and the outside line, and saves the pair; `change` saves it again. Nothing is sent to
the board.

`showValue(value)` writes the value to the field and sets the slider to the value clamped to
the zoom; `outside(value, range)` fills or hides `#level-zoom-outside`.

Style:

- `#level-zoom` is a flex row like `#level-controls`, `margin-top: 8px`; `#level-zoom-bar`
  has the slider's flex, `1 1 100px` and a minimum of 80 pixels; `#level-zoom-said` has the
  box's flex, `0 1 180px`, so the bar's edges are the slider's and the words stand above the
  box.
- `#level-controls` gets `margin-top: 8px`, so the rows stand 8 pixels apart.
- `#level-file.just-changed` is bold.

## Tests

`tests/app/test_brightness.py`, with the stand-in of the suite. The stand-in `Target` also
answers `saved <id>` from what it keeps, can give it another value, and can name a clock as
the animation.

- `test_animation_identity_change_cancels_held_and_dirty_edits` becomes
  `test_a_held_drag_or_typed_value_stays_with_its_animation_across_a_change`: for a slide
  and typed digits in the override, after the change the panel shows `Animation 1:
  hello.odrg, no longer playing` with 70; the release or Enter sends `brightness 1 70 save`,
  `saved 1` reads 70 back, the line is `Saved 70 for hello.odrg.`, the panel then shows
  animation 2 with 128, and the default stays 128.
- The same in the default: `brightness 70` is sent, animation 1 keeps no override, and the
  line is the default's.
- The same when the animation that comes is a clock, `60003`, `clocks/c1.odrg`.
- `test_save_queued_behind_new_identity_status_is_cancelled_before_sending` becomes
  `test_a_save_queued_behind_a_change_still_goes_to_its_animation`: `brightness 1 70 save` is
  sent after the change and confirmed by `saved 1`.
- A press of the box while the panel still shows animation 1 and the stand-in already plays
  animation 2 saves for animation 1.
- The hold: after a change with no gesture, the box, the slider and the field are disabled
  and the line of the file bold for about a second; a press within it sends nothing; one
  after it is taken. No hold after a reload or at the first status.
- A target chosen during a slide: nothing sent to either target, and the line says so.
- A refusal of the save of an animation no longer playing, a lost reply and a read-back
  that differs each give their line, and nothing is sent again.

`tests/app/page/scenarios/brightness.js` takes the acts `zoom: [start, end]` and
`zoomKey: [which, key]` and its `look` gives the pins, the slider's `min`, `max` and value,
the words, the outside line and whether the line of the file is bold.

Zoom tests:

- The slider over 2 to 12: its `min`, `max` and that a slide to its right end sends 12.
- Pins that would cross stay 1 apart, with the pointer and with the arrow keys.
- A value from status and a typed value outside the zoom: the field shows it, the slider
  stands at the end, the line says above or below, and the zoom is as it was.
- Both modes keep the zoom; a reload and a restart of the emulator find it kept.
- `tests/app/page/scenarios/zoom-kept.js`, without the app, as `move-jobs.js`: `load` and
  `save` with a storage that throws, an empty one, malformed pairs and a good pair.

The layout:

- `tests/app/test_look.py`'s
  `test_the_brightness_field_stands_on_one_line_with_its_label_and_the_slider_under_it`
  becomes the field's line, the zoom's row 8 pixels under it with the bar's edges at the
  slider's and its words at the box's, and the slider 8 pixels under the zoom's row.
- `look.js`'s `measure` gives the zoom's bar and words.
- `test_small_and_landscape_layouts_fit_and_keep_touch_room` checks the pins too.
- The tests of the panel staying at the top run with the taller panel; a size whose answer
  changes is adjusted with its reason.

Against the real emulator, a test class beside the others of the module: a show of two
animations whose turns last about two seconds, and a card with three clocks and a message
for the break. A slide held across the end of a turn, typed digits committed after the end
of a turn, and a slide held across the start of a clock break each save their value for
the animation they began on (`brightness.txt` and `saved <id>`), leave `status.brightness`
as it was, give their line, and are read back after a restart of the emulator on the same
folder.

## Pages

`docs/android-app.md`, "Saved animation brightness controls": the gesture bound to its
animation, the lines, the hold, the default's line and the zoom kept on the phone; and the
panel's description at the top of the page gains the zoom's row. Entries at the end of
`docs/drifts.md` for the decisions below.

## Decisions recorded in `docs/drifts.md`

- Built on `seed-87-live-mirror`, as the owner asked on 2026-11-24, not on `master`.
- The zoom's bar has the slider's edges and its words stand above the box, which reads
  "as wide as the slider's row" as the column of the slider.
- A save for an animation that no longer plays is confirmed by `saved <id>`.
- A change of target ends a gesture at once, unapplied.
- The hold begins only when the panel moves from one known animation to another on the same
  target.
- The zoom is kept under `odrig.brightness-zoom` as `"<start> <end>"`.
- The pins are two range inputs over each other with thumbs of 48 by 48 pixels, the one
  that can move away on top.
- A press of the box across a change is proven with the stand-in only, since a press lasts
  no time.
- The texts of the lines.

## Self-review

Requirements 1 and 2 are the gesture, applying and confirming it, and the lines; 3 the
hold; 4 to 6 the zoom, its keeping and the layout; 7 what stays; 8 the tests and the
delivery's tasks. Nothing needs the owner: no command, decision of `docs/decisions.md`,
hardware or person-only check changes, and the phone check stays open as requirement 8.6
says.
