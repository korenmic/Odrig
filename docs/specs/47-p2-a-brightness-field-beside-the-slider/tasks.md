# Tasks: a brightness field beside the slider

Requirements: [requirements.md](requirements.md). Design: [design.md](design.md).

- [x] 1. The field, its sync with the slider and its sends
  - `app/www/index.html`: `#level-line` with the label and the field, the slider's
    accessible name `Brightness`, the line `#level-range` under the slider.
  - `app/www/screens/show.js`: `inForce`, `writeLevel`, `unsent`, `typingIn`,
    `showInForce`, `commitLevel`; the field's `input`, `keydown` and `change`; the slider's
    `input` dropping text not sent; `draw` following `status` only without text not sent
    and outside the typing state.
  - `app/www/style.css`: `#level-line` and the field.
  - Tests: `tests/app/page/reading.js` reads the field's value; `tests/app/test_long_press.py`
    names `#level-number` first among the fields; `tests/app/page/scenarios/typed.js` and
    the class `TheField` of `tests/app/test_controls.py` with the cases of the design.
  - `docs/drifts.md`: the decisions of the spec beyond the seed.
  - `project-seeds/47-p2-a-brightness-field-beside-the-slider/state.json`: `in_progress`.
  - Suites: the app's.

- [x] 2. The field's look on a phone
  - `tests/app/page/scenarios/look.js` measures the line of the label and the field and the
    slider; `tests/app/test_look.py` checks them at 320, 360 and 740 px: one line, the
    field 44 px wide or more and 48 px high or more, about 5.5 em, tabular digits, the
    slider 8 px under it and as wide as the panel's inside. `app/www/style.css` mended if
    a measure fails.
  - Suites: the app's.

- [x] 3. The documents and every suite
  - `docs/android-app.md`: the Animations bullet of "What it is", the first column of the
    slider's row in the table of lines, the slider's sentence in "Using it" step 3, the
    paragraph on the fields where a long press marks text, step 4 of "The check on a
    phone" and the brightness in "What is verified"; the owner's check of the field is
    added to "What is open".
  - Every suite that works on this computer. The APK is built once seed 48 is built on the
    same branch, from its tip, and put with the artifacts on the share and on Drive. The
    seed stays `in_progress`: the owner's check on a phone, requirement 6.4, is left open
    in words.
  - Suites: every suite.
