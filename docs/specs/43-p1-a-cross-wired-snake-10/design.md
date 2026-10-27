# Design: a cross-wired snake 10

Requirements: [requirements.md](requirements.md). Seed:
`project-seeds/43-p1-a-cross-wired-snake-10/seed.md`.

## The format: `starts`

A leg may carry `starts`, an array of end words, one per strip in chain order:

```json
{"leg": 10, "pin": 10, "first_led": "bottom", "columns": [28, 30, 29], "starts": ["bottom", "bottom", "top"]}
```

The words are those of `first_led` for the file's kind. The first word repeats
`first_led`, so that a reader that knows only `first_led` still finds the first strip
right; a difference is malformed. The length must be the number of strips. "Where each
LED is" becomes: the strip `s` starts at `starts[s]` when the leg has `starts`, else at
the `first_led` end when `s` is even and at the opposite end when `s` is odd.

The vocabulary is the ends, `bottom`/`top` and `left`/`right`, not `up`/`down`: it is
the format's own, and a column that starts at the bottom runs up.

## The core

`core/src/mapping.cpp`, `read_leg`: a fifth member bit, 16, for `starts`. The array is
read as words; each word is checked against the kind of the words seen so far and held
as a bit, far end or not, in `starts_far`, a bitmask allocated beside `strip_check` in
`read_mapping` with one bit per strip of the file, at bit `seen.strips + index`; in the
first reading, which counts without filling, the words are only checked. The first word's
far-ness is held in `starts_first` and the count in `starts_count`. At the leg's end:
`members` is 15 or 31; with `starts`, `starts_count == strips`, the words' kind is the
leg's kind, and `starts_first == starts_far_of_first_led`. The placement loop takes
`from_far = has_starts ? bit(starts_far, seen.strips + s) : starts_far != ((s & 1) != 0)`.
`starts` may come before `columns`, as `first_led` may; the bits are addressed by the
leg's first strip, which is known at the leg's start.

`core/src/mapping_control.cpp`:

- `canonical_leg(core, number)` is today's loop of `mapping_editable` for one leg;
  `crossed_leg(core, 10)` expects strip 0 on column 28 from the bottom, strip 1 on
  column 30 from the bottom, strip 2 on column 29 from the top.
  `mapping_editable` = 60 x 60, twenty legs of 180, every leg canonical but leg 10,
  which is canonical or crossed. `mapping_cross(core)` = editable and leg 10 crossed.
- `mapping_get` writes `,"cross":true|false` after `revision`.
- `persist(core, pins, cross)` writes leg 10 as `"columns":[28,30,29],"starts":
  ["bottom","bottom","top"]` when `cross`, else canonical; every caller passes the
  present bit but `mapping cross`, which passes the new one.
- `mapping_cross(core, on, reply)`: `show-invalid`, `bad-argument` when not editable,
  `busy` as `mapping_set`, `{ok:true}` when the bit is already `on`, else `persist` with
  the present pins and the new bit, then `place_leg_10(core, on)`: the three strips'
  `led_pixel` entries rewritten in place by the form, 180 entries.
- The command parser (`core/src/commands.cpp` or where `mapping test` is parsed) takes
  `mapping cross on|off`; any other word is `bad-argument`. `docs/commands.md` lists it
  in the command table and in "Mapping controls", and names the new reply member.

The revision stays `revision_of`, the CRC-32 of the pins: the app computes the same
from the pins it shows, and the bit is idempotent, so a stale app can only set what it
means to set. Recorded in `docs/drifts.md`.

## The Python library and the emulator

`odrig/mapping.py`: `Leg` gets `starts`, a tuple of words or `None`; `_mapping` allows
the member, checks it as 1.2, and `position` uses it. `docs/python-library.md` names it.

`emulator/web/layout.js`: `read` keeps `starts` on the leg; `startsLow(leg, s)` returns
whether `starts[s]` is the low end when the leg has `starts`, else today's alternation.
`position`, `find`, `strips` and `path` follow from it. The emulator's page needs nothing
else: the LEDs view and the mapping view draw from these.

## The app

`app/www/commands.js`: `mappingCross(on)` sends `mapping cross on|off`; `client.js`
wraps it as `mappingSet` is wrapped, under the `mapping` operation. `mappingGet` keeps
`cross` in the reply it returns.

`app/www/index.html`, in `#mapping` after the buttons:

```html
<label class="check" for="mapping-cross"><input id="mapping-cross" type="checkbox"><span><span class="title">Snake 10 is cross-wired</span><span class="small">Its chain runs up line 28, up line 30 and down line 29, around a dead output.</span></span></label>
```

`app/www/screens/mapping.js`: `latest` keeps `cross`; `poll` counts a changed `cross`
as a change; `draw` sets the box's `checked` from `latest.cross` and disables it under
`locked() || live !== null || !editable() || crossing`; on `change`, `crossing = true`,
`client.mappingCross(checked)`, on success `latest.cross = checked` and the summary
`Saved: snake 10 is cross-wired.` or `Saved: snake 10 is wired as the others.`, on a
refusal `explanation(error)` as a save's and the box redrawn from `latest`; then a
`read()`. The listener is `change`, which the look test allows.

`docs/android-app.md`: a paragraph after the editor's, and a sentence in the photo's
paragraph on reading with the bit off.

## The photo reading with the bit off

Nothing changes in `app/www/photo.js`. With the bit off on the installation as wired,
canvas pixel (29, 3s - 1) is sent to LED 122 - 3s of the leg, which sits on column 30 at
row 62 - 3s, and pixel (30, 3s) to LED 120 + 3s, on column 29 at row 61 - 3s: two LEDs
in the rows of snake 21 - s. That position's votes go 2 to 1 to snake 21 - s, which the
position that truly shows it holds with 3, so position 10 gets null and the fill rule
gives it the snake no position shows. The test's wall generator takes `crossed`, a list
of positions drawn this way.

## Tests

- `tests/core/test_mapping.py`: a column-leg file with `starts` on one leg read and its
  LEDs placed; the rejections of 1.2; a row-leg file with column words.
- `tests/converter/test_mapping.py`: the same through the library, and `position`.
- `tests/emulator/test_layout.py`: a made-up column-leg file with `starts`: positions,
  strips' ends and path.
- `tests/mapping/test_core.py`: `cross` false; `mapping cross on` and the file's bytes;
  the diagonal's and the snake test's pixels on leg 10 by the crossed placement; `off`;
  idempotence; `mapping set` keeping the bit; refusals; power loss at every step;
  restart.
- `tests/mapping/test_app.py` and `tests/app/page/scenarios/mapping.js`: the checkbox.
- `tests/app/test_photo.py` and `tests/app/page/scenarios/photo-analysis.js`: the
  `crossed` wall.
- `tests/firmware`: nothing new; the usermod does not change.
