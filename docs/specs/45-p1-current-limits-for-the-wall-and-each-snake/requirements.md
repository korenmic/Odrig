# Requirements: current limits for the wall and each snake

The seed is `project-seeds/45-p1-current-limits-for-the-wall-and-each-snake/`. The owner
approved it with its rulings and asked for it to be specified and built without a
question pass; a point these requirements decide that the seed leaves open is recorded at
the end of `docs/drifts.md`.

## 1. The limiting

1.1 At every refresh that writes the LEDs, a new picture, a test picture or a dark one,
the core limits the bytes it sends, after the brightness, by the budgets in force. A
refresh that keeps the picture before keeps its bytes, its estimates and its `limited`
bits.

1.2 The estimate of a leg of N LEDs whose bytes sum to S is floor(S × 55 / 765) + N mA.
The wall's estimate is the sum of its legs'.

1.3 With a budget B above 0 and an estimate E above B, the level is 1 when B is N or
less, and otherwise the largest level from 1 to 254 at which the fade of 1.4 gives bytes
whose estimate is B or less, 1 when none does, found by halving with all eight fades.
Otherwise the level is 255, which changes nothing. The wall uses the same rule with its
budget, its estimate and the LEDs of all legs.

1.4 The fade at a level below 255: an LED whose three bytes are 0 stays so; for another
LED with largest byte m, each byte b becomes ((b × level + 127) >> 8), with its lowest bit
set when b is above (m >> 2) + 1.

1.5 The order: each leg is faded by its own budget, and every leg's estimate is made again;
then every leg is faded by the wall's level, and every leg's estimate is made again; then
each leg with a budget whose estimate is now above it is faded again by its own rule from
the bytes the wall left, and its estimate made again. A leg is `limited` when a level
below 255 was used for it in either of its passes; the wall when its level was below 255.

1.6 A budget of 0 is no limit. Brightness is applied first and is not changed. The
diagonal and the snake tests are limited like any other picture.

## 2. The budgets and their file

2.1 The wall's budget is 0 to 250,000 mA. A leg's budget is 0 to 65,535 mA, kept by its
leg number, 1 to 255. For the installation, snake n is leg n, a physical place unchanged
by `mapping set` and `mapping cross`.

2.2 The budgets are kept in `limits.json`, in the board's own storage beside
`mapping.json`. Its form is `{"version":1,"wall":<mA>,"legs":[[<leg>,<mA>],...]}`, read as
strictly as the mapping file: exactly these three members, `version` 1, `wall` 0 to
250,000, each entry of `legs` an array of a leg number 1 to 255 and a budget 0 to 65,535,
no leg number twice. Anything else makes the file unreadable.

2.3 A save writes `limits.part` whole and renames it to `limits.json`, as the mapping is
saved; a `limits.part` left by a cut is removed at the start. The file holds the wall's
budget and every leg whose budget is above 0: the mapping's legs from memory, in the
mapping's order, then the legs of the old file that the mapping lacks, copied from it.

2.4 While no `limits.json` is present, or it is unreadable, the budgets are the defaults:
every leg's 0, and the wall's the host's default. An unreadable file is said once in the
log at the start, `limits unreadable`, and is replaced whole at the next save.

2.5 The host gives the wall's default through an optional member of the host's record,
`limit_default`. Absent, the default is no limit: the emulator and the core's test host,
unless the test host is given `--limit-default MA`. The board's firmware gives WLED's
maximum as WLED loaded it less 120 mA: 730 for 850, 1 for a maximum from 1 to 120, no
limit for 0.

2.6 The first save while the defaults are in force writes the whole file: the wall's
budget then in force, every leg at 0, and the one value set; until a file is saved,
every set writes, even of the value in force. Once one is saved, the same value again
writes nothing.

## 3. The commands

3.1 `limits` and `limits <from>`, `<from>` a whole number from 0 to 65,535, reply in one
line of at most 1,024 bytes:
`{"ok":true,"saved":<bool>,"wall":[N,B,E,L],"legs":[[leg,N,B,E,L],...],"next":<k|null>}`,
the wall's and each leg's LED count, budget, estimate and `limited` as 1 or 0. The legs are
those of the mapping, in its file order, from position `<from>`, as many as fit, and
`next` is the position of the first left out, or null. The estimates are those of the
bytes of the latest refresh that wrote the LEDs. Without a usable mapping there are no
legs and the wall's LED count is 0. `limits` is never refused but with `bad-argument` for
a `<from>` that is not such a number.

3.2 `limits wall <mA>` saves the wall's budget; `limits snake <n> <mA>` saves leg n's;
`limits default` removes `limits.json` and puts the defaults in force, `saved` false, and
writes nothing when no file is present. They are refused in this order: `bad-argument`
for words that are not one of these forms, a leg number outside 1 to 255 or a budget out
of its range; `busy` while a catalog rebuild runs; `show-invalid` while the show is
invalid; `bad-argument` for a leg number the mapping lacks; `busy` while the start-up
check runs or an upload is open; `storage-error` when the file cannot be written or
removed. They are accepted while a mapping test shows. There is no revision: the last
save wins. A budget set takes effect from the next refresh that writes the LEDs.

3.3 The command tool sends the five forms, and `limits` without a position follows
`next` as `list` does.

## 4. The firmware

4.1 The odrig firmware switches WLED's limiter off in memory, setting
`BusManager::_useABL` false before every fill and send and after any making of its
outputs, and resets an output that WLED's limiter left dimmed; it never changes WLED's
maximum or an output's, and nothing WLED stores changes. `install-firmware`, `set-limit`
and `read-limit` keep working on WLED's stored maximum.

4.2 The rule that turns WLED's maximum into the default is in a header the firmware tool's
suite compiles and tests on the computer.

4.3 The probe build's code stays; its `limited` and `used_ma` read 0 for a stored maximum
of 0 or above 120, and `limit_ma` keeps reading the maximum less 120. The board suite's
tests of the limiter, and the target test of the probe suite, expect that and the bytes of
the core's fade, and check the core's limiting through `limits`; a board test checks the
board's default only when `limits` reports `saved` false at its start, and says so when it
skips it; every board test that saves budgets ends with `limits default`; no board test
sets a wall budget of 0 or above 730 mA on the bench. The run with a stored maximum of 0
first saves `limits wall 730`, then `set-limit` stores 0, so that the bench never plays
without a wall budget across the restart, and after 850 is stored again it ends with
`limits default`.

4.4 The standalone firmware's own limiter goes: `firmware/standalone/src/limit.h` and
`limit.cpp`, the `limit` mode of the firmware suite's host program, and its test.

## 5. The firmware tool

5.1 `read-show` saves `limits.json` with the show, and a show folder's check accepts the
name. `install-show` writes the folder's `limits.json` only with `--limits`, after reading
it as the core does; without `--limits` the folder's copy is left out and the board's
file, or its absence, is kept. `--limits` with a folder that holds no `limits.json` is
refused with `limits-missing`, and with one the core would not read with
`limits-malformed`, before the board is touched.

## 6. The app

6.1 Settings gets a panel `Current limits` under the Mapping panel, the same in the APK,
the browser and the emulator's Controller view: an explanation that a budget is a ceiling
on WLED's estimate of the LEDs' draw, not a measurement, and that a low wall budget also
dims the diagonal the mapping from a photo reads; a field for the wall's budget in mA
with the wall's estimate beside it; and a row for each snake, `Snake n · columns a–b`,
with its field and its estimate, shown while `mapping get` reports the twenty snakes as
editable, the wall's field alone otherwise.

6.2 A field takes digits only; a stored 0 shows as an empty field with the placeholder
`No limit`. Changed text is saved when the field is entered or left; text equal to the
value last read sends nothing; an emptied field saves 0 when the saved value is not 0. A
value out of range is not sent: the app says the range and shows the saved value. A save
is said, `Saved: the wall's budget is 2,000 mA.` or `Saved: snake 3 has no limit.`; a
refusal is said with its own sentence and the saved value shown again.

6.3 Beside a budget from 1 to the LEDs' count the app says that every LED is then held at
its lowest level; never beside 0. While `saved` is false the panel says that no budgets
are saved and the wall's budget is the installation's default. A dimmed wall or snake is
marked beside its estimate, and the estimates are labelled as estimates.

6.4 The panel reads `limits`, following `next`, when Settings opens and every two
seconds while it shows; a read updates every estimate but never the text of a field that
has the focus or unsaved text, and nothing is read while a save is out. An installation
whose software answers `limits` with `unknown-command` gets the explanation, the sentence
`This installation's software has no current limits.` and nothing to set, and is not
asked again until the target changes.

## 7. Documents, tests and builds

7.1 docs/commands.md, docs/core.md, docs/firmware.md, docs/firmware-additions.md row 14,
docs/emulator.md, docs/android-app.md, docs/python-library.md, docs/reasons.md,
agent/working-rules.md and agent/vocabulary.md describe the estimate, the limiting, the budgets, the file, the
defaults, the commands, the panel, the firmware tool's option and the bench rule: on a
board whose strip is fed from its 3.3 V pin the wall's budget is never 0 or above 730 mA
and `install-show --limits` is not run there with a folder of the installation.
docs/decisions.md records the rulings; docs/drifts.md records seed 12's requirement 6, its
probe members and its tasks 6 and 10 giving way, and what this spec decided beyond the
seed.

7.2 Every suite that needs no board passes. The core's suite checks the limiting exactly
against the Python library's reference, `odrig.limits`, which the reference player of
`tests/core/support.py` uses too; the defaults with and without a host default; the file's
strict reading, its save, a power loss at every step; the commands, their refusals and
paging; a leg's budget staying with its snake after `mapping set` and `mapping cross on`;
the memory with the target mapping, a show of 100 items and a drive under 131,072 bytes.
The emulator's suite shows the limited LEDs once budgets are saved and sends the commands
through the command tool. The firmware tool's suite checks the header, `read-show` and
`install-show --limits`. The app's suite checks the panel in Chrome against the emulator.

7.3 A firmware and an APK are built; the APK is put with the artifacts. By the owner's
order of 2026-10-27 the firmware is not flashed until the owner has merged seed 43 and
this branch is brought onto master: it is kept in `build/firmware/out/` and put with the
artifacts when it is flashed, so that the share's firmware stays the board's. The board
suite on the probe build and the owner's checks on the installation are left open in
words.

7.4 On the board, with a budget on every snake and on the wall that limits the dense
60 x 60 clip at every refresh, the rate stays within 20 to 50 a second, measured as
docs/firmware.md measures it with the board suite's `test_fps.py`; no work is done to
raise a rate inside that range. It is measured with the board session that 7.3 leaves
open.
