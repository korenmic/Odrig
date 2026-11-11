# Design

## The checkbox

- `index.html`: `<label class="check"><input id="mapping-lock" type="checkbox" checked
  aria-describedby="mapping-lock-state"> Lock mapping edits</label>` in place of the
  toggle button, at the same place in the Mapping panel. The dialog stays.
- `mapping.js`: a `click` on it is prevented, so that the box keeps its state, and asks
  `requestLock()`; `draw()` sets `checked` to `editLocked` and `disabled` as the button's
  was. Seed 84's value, its keeping and its dialog are unchanged.
- The page helpers read `checked` where they read `aria-pressed`.

## The typed pins

- `card(pin, snake)`: after the handle, `<label class="words">GPIO <input class="pin-field"
  type="text" inputmode="numeric" autocomplete="off" aria-label="GPIO of snake n"></label>`,
  its value the pin, `dataset.pin` the confirmed pin.
- A press on a field does not start a hold or a drag: `pointerdown` returns for a target
  inside `.pin-field`.
- `commitTyped(field)`: the text, trimmed, must match `^[0-9]{1,3}$`; its number must be one
  of `shownPins()`. Else the field takes its pin again and `problem` says `Type the number
  of a GPIO.` or `GPIO n is not one of the installation's twenty pins.` The same pin
  commits nothing. Else `moveTo(pin, snake - 1)`, the drag's insert and shift, and its save.
  `locked()` and a save under way refuse, the field taking its pin again.
- Enter commits, `change` (leaving the field) commits, and Escape restores the field and
  leaves the focus where it is.
- `rows()` draws the column again only when the pins change, so a draft and its focus
  stay through a poll that changes nothing; a field with the focus that is drawn again
  gets the focus back with the confirmed pin.
- `dropEdits()` also puts every field back to its pin; the fields are disabled as the
  handles are.

## Tests

`tests/mapping/test_lock.py` and `tests/mapping/test_app.py`, with the scenarios in Chrome
against the emulator:

- `checkbox`: a checkbox `Lock mapping edits`, checked; a press opens the dialog and keeps it
  checked; Cancel keeps it; confirm unchecks it and stores `unlocked`; without a board too.
- `typed`: locked, the fields are disabled; unlocked, typing a pin of snake 5 into snake 1's
  field and Enter saves the drag's assignment; leaving a field commits; Escape restores;
  `abc`, `2.5`, `-3`, empty and `99` write nothing and say why; the same pin writes nothing;
  a draft survives a poll; hiding the app drops it.
- The scenarios that read `aria-pressed` and the words of the pins change after.

## Documents

`docs/android-app.md`: "Mapping edit lock" names the checkbox; "Mapping" names the typed
pins; a step of "The check on a phone" and `tests/app/test_docs.py`'s counts; a bullet of
"What is open". `docs/drifts.md`.
