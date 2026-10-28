# Design: a brightness field beside the slider

Requirements: [requirements.md](requirements.md). Seed:
`project-seeds/47-p2-a-brightness-field-beside-the-slider/seed.md`.

Only the app changes: `app/www/index.html`, `app/www/screens/show.js` and
`app/www/style.css`, with their tests and `docs/android-app.md`. The line the app sends,
`brightness <n>`, and the way it goes, `client.setBrightness` through the one queue of
requests, are today's.

## The markup

In `#now-panel`, the label with its span becomes:

```html
<div id="level-line">
<label for="level-number" class="slider-label">Set the brightness to</label>
<input id="level-number" type="text" inputmode="numeric" enterkeyhint="done" autocomplete="off" placeholder="-">
</div>
<input id="level" type="range" min="0" max="255" step="1" value="0" aria-label="Brightness">
<p id="level-range" class="small" role="status" aria-live="polite" hidden></p>
```

The line `#level-range` stands right under the slider and above `#test-now`, `#silent` and
`#silent-why`, so that the slider never moves while it shows.

## The look

`#level-line` is a flex row, its items centred, 8 px apart, with the panel's 8 px above
it: the label takes the room left (`flex: 1 1 auto`, margin 0, today's 15 px lettering in
the lesser colour), the field is `flex: 0 0 auto`, `width: 5.5em` at the field's 17 px
letters, which is 93.5 px, margin 0, with `font-variant-numeric: tabular-nums`; it keeps
the fields' 48 px of height, their 14 px of padding and their border. The slider keeps its
margin of 8 px, so that it stands 8 px under the field. At 320 px the panel's inside is 266
px wide and the label's 21 characters at 15 px take about 150 px: the line fits.

## The value in force and the text not sent

`show.js` keeps `inForce`, a number or null, beside `held`, `sentValue` and `sentAt`.

- `writeLevel(value)` sets the field's text to the value (empty for null) and `inForce` to
  it; every writer of the field goes through it: the slider's `input` and `change`, a value
  sent from the field, and `draw` following `status`.
- `unsent()` is `field.value !== (inForce === null ? "" : String(inForce))`.
- `typingIn()` is the field having the focus while `document.body` has the class `typing`,
  which `main.js` sets while the keyboard is open.
- `showInForce()` writes the value in force into the field and stands the slider at it, at
  0 while there is none.

## The handlers

The field's three listeners, added in `start`:

- `input`: the text without its non-digits, written back only when it differs; the line
  `#level-range` hidden; when the text is not empty and its number is 255 or less, the
  slider is set to that number. Nothing is sent.
- `keydown` with the key `Enter`: `commitLevel()` when `unsent()`. The focus stays; the app
  calls no `blur` there.
- `change`: `commitLevel()` when `unsent()`.

`commitLevel()`:

1. The digits of the text, read as a number (`Number("080")` is 80).
2. While the app is hidden (`document.hidden`), or the text is empty, or the number is
   above 255: `showInForce()`, and for a number above 255 while the app is shown the line
   `The brightness is 0 to 255.`; nothing is sent.
3. A number equal to `inForce`: `showInForce()`, so `080` is rewritten `80`; nothing is
   sent.
4. Otherwise the slider is set to it, `writeLevel(it)`, the line hidden, and the slider's
   own `change` path runs: `sentValue = null` when a second or more has passed since
   `sentAt`, then `sendLevel()`. `sendLevel` keeps its 200 ms spacing and its skip of the
   value sent last, and `client.setBrightness` replaces a brightness that waits in the
   queue.

An Enter commits and leaves the field's text equal to the value in force, so the `change`
that follows when the field is left finds no text not sent and sends nothing: one send.

The slider's `input` handler becomes: `held = true`; when `unsent()`, the field's text is
first written with the slider's value through `writeLevel` and only then the field loses
the focus, so that the `change` the browser fires on leaving it finds nothing to send; else
`writeLevel(slider)`; the line hidden; `sendLevel()`. Its `change` handler: `held =
false`, `writeLevel(slider)`, the line hidden, then as today. When the browser itself moves
the focus to the slider before the slider's first `input`, the field's `change` comes
first and commits the typed text; the slider's value then follows by `sendLevel`'s spacing
and is what stands. That is recorded in `docs/drifts.md`.

## Status

In `draw`, the slider and the field follow `status` only when
`!held && performance.now() - sentAt >= SLIDER_RESTS_MS && !unsent() && !typingIn()`:
then the slider is set to `status.brightness` and `writeLevel(status.brightness)`. The fact
`#brightness` follows every `status` as today. A brightness that waits out `sendLevel`'s
200 ms when the app is hidden goes out when it comes back, for the field as for the slider:
`sendLevel`'s timer is today's; what waits in the client's queue is dropped by its rule.

## The events

No new kind of event: `input`, `change` and `keydown` are already in the set that
`tests/app/test_look.py` pins.

## The tests

- `tests/app/page/reading.js`: `controls(app).number` reads the field's value, `null` while
  the field is not on the screen.
- `tests/app/test_long_press.py`: `#level-number` first in `FIELDS`.
- `tests/app/page/scenarios/typed.js`: a scenario of its own, which works the field as an
  operator does: `fill` for typing, a `keydown` of Enter, a `change` for leaving it, the
  slider by `slide` and `release`, the page made hidden by `document.hidden` and a
  `visibilitychange`, and the test's steps for another client's brightness; it reports the
  field, the slider, the fact and the line `#level-range` after each act.
- `tests/app/test_controls.py`, a class `TheField`, against the emulator (the lines it
  logged over HTTP, with their times) and against a stand-in that obeys nothing: Enter
  sends `brightness 8` and the slider stands at 8; leaving the field sends; Enter and then
  `change` send once; typing `1`, `12`, `120` moves the slider to each and sends nothing
  until Enter; a slider move with text not sent sends the slider's value only, writes it
  into the field and leaves the field without the focus; `080` is written `80` and
  sends `brightness 80` once; a value equal to the value in force, an empty field and 256
  send nothing, 256 with `The brightness is 0 to 255.` under the slider and gone at the
  next keystroke; a commit while hidden sends nothing and shows the value in force; a
  `status` of another client leaves the field and the slider alone while the field holds
  text not sent and is followed once the field is left; several commits in a row keep at
  most five sends a second.
- `tests/app/page/scenarios/look.js` and `tests/app/test_look.py`: the line of the label
  and the field measured at 320, 360 and 740 px: on one line, the field 44 px wide or more
  and 48 px high or more, about 5.5 em, tabular digits, the slider 8 px under it and as
  wide as the panel's inside.

## The documents

`docs/android-app.md` as requirement 6.1 lists. The command list and its count stay.
