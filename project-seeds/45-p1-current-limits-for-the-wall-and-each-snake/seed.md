# Current limits for the wall and each snake

## Summary

The installation's LED current gets two kinds of budget that the operator sets in the
app: one for the whole wall, and one for each of the twenty snakes, each a ceiling in mA
on WLED's estimate of the LEDs' draw, with nothing counted for the chip. Today the only limit is WLED's
own limiter, at the 850 mA that `firmware/limit.json` gives the bench, less 120 mA WLED
keeps for the chip: on the installation's 3,600 LEDs it holds every LED at its lowest
level, so that brightness 2 to 255 look the same and 1 is dark. The limiting moves into
the core, with WLED's estimate and fade and a level that keeps the estimate within the
budget, so that the board and the emulator dim alike and both kinds of budget act at once; the firmware switches WLED's own limiter off in memory; the
budgets are kept in a file on the installation and read and set with new commands; and
Settings gets a new panel, `Current limits`, under the Mapping panel, with a field for
the wall's budget, one for each snake's, and the estimated current beside each.

## Priority

- `P1`

## Depends On

- Seed 12, the standalone firmware, a trial program that is to host the core: its own
  copy of WLED's limiter, not yet called, gives way to the core's limiting.
- Seed 15, the current limit in `firmware/limit.json`, whose value, less 120 mA, becomes
  the board's wall budget while no budgets are saved.
- Seed 30, for the twenty snakes of the installation's mapping, `mapping get` and the
  mapping file's atomic save, which the budgets' file follows.
- Seed 36, for Settings and its look.
- Seed 43, for the snake as a physical place: snake n is leg n, columns 3n-2 to 3n,
  whatever pin drives it and however it is wired.

## Product Context

On 2026-10-27 the owner found that on the installation only brightness 0 and the others
looked different. WLED's limiter estimates 1 mA for each LED at rest, 3,600 mA for the
installation, more than the 730 mA its 850 mA maximum leaves the LEDs; it then fades
every frame to its lowest level, at which a channel above a quarter of its LED's
brightest one is sent as 1 and the others as 0, whatever plays. `docs/firmware.md` said
the limit must be raised or switched off before twenty legs are lit; it was not.

The owner asked for the limit to be set from the app, and for a limit of its own for
every snake, in a new interface below the mapping's. The installation's LEDs are fed by
several power supplies, each feeding a group of six or seven snakes; a budget per snake
keeps each supply's group within what the supply gives, and a budget for the wall keeps
the sum within what all of them give together.

WLED cannot do both: it applies its limit for each output only while its limit for the
whole is 0. Its limiter also runs only on the board, so the emulator showed every
brightness while the board showed none, which is how the fault went unseen. A limiter in
the core, the code the board, the standalone firmware and the emulator share, does both
and shows the same everywhere.

## Technical Constraints

- **What a budget is.** A ceiling in whole mA on the LEDs' estimated draw: it dims a
  snake, or the wall, only at a refresh whose picture would draw more, as WLED's
  brightness limiter does, and then to within the budget. It is not a cap on brightness. The brightness
  control stays 0 to 255 and is applied first; the limiting only lowers what passes a
  budget. 0 is no limit.
- **The estimate**, WLED's: for a snake, E = floor(S × 55 / 765) + N, where S is the sum
  of all the bytes its LEDs are sent and N its number of LEDs: 55 mA for an LED at full
  white, 1 mA for each LED at rest. No current is counted for the board: the
  installation's LEDs have supplies of their own. The wall's estimate is the sum of its
  snakes'. Estimates are whole mA, up to 201,600 for the installation, and are carried as
  32-bit numbers. The core keeps in memory only the budgets of the mapping's legs, the
  wall's budget and default, and a `limited` bit for each leg and for the wall; the
  estimates are made again from the LED data, the bytes sent, when `limits` is answered;
  and budgets of legs the mapping lacks stay in the file alone, copied from the old file
  into the part file at each save. The target mapping with a drive leaves the core about
  560 bytes of its 131,072.
- **The level**: with a budget B above 0 and an estimate E above B, the level is 1 when
  B is N or less, as in WLED, and otherwise the largest from 1 to 254 at which the fade
  below gives bytes whose estimate is B or less, and 1 when none does; it is found by
  halving, always with all eight fades, which holds because the faded estimate never
  falls as the level rises. Otherwise, and at a level of 255, nothing changes. The wall uses the same rule with its budget, its estimate and all its
  LEDs. Only at level 1 can the estimate of the bytes sent stay above the budget, which
  every budget at or below the LEDs at rest, N, gives on a picture that is not dark. A
  snake, or the wall, is `limited` at a refresh exactly when a level below 255 was used
  for it, which a budget below N gives even on a dark picture. WLED's level, floor(B × 255 / E) + 1,
  leaves the estimate of the bytes sent above the budget by about the LEDs at rest: a
  full-white snake with a budget of 500 mA is held at level 7 and estimated at 451 mA,
  where WLED's level would leave 684.
- **The fade**, WLED's video fade, `color_fade(c, level, true)` in WLED's `colors.cpp`:
  an LED that is black stays black; each byte b of another LED becomes
  (b × level + 127) >> 8, with its lowest bit set when b is above (the LED's largest byte
  >> 2) + 1. A channel at or below that quarter may go dark at low levels.
- **The order.** At a refresh that writes the LEDs, the core first applies each snake's
  budget to that snake and estimates every snake again from the bytes it will send; then
  it applies the wall's budget, by one level for every snake, to the bytes the snakes'
  own budgets left, and estimates every snake again; last, since the fade can raise a
  low even byte by 1, a snake with a budget whose estimate is now above it is faded again
  by its own rule from the bytes the wall left and estimated again, which only lowers the
  wall's estimate. A snake is `limited` when either of its passes used a level below 255. The estimates reported are those of
  the bytes sent, after every limiting, with for each snake and for the wall whether its
  budget dimmed that refresh, `limited` as above. A refresh that keeps the picture before keeps its bytes and
  its estimates and is not limited again. A budget set by command takes effect from the
  next refresh, as a brightness set does. The diagonal and the snake tests are limited
  like any other picture.
- **The budgets.** The wall's budget is 0 to 250,000 mA; a snake's, or a leg's of
  another mapping, 0 to 65,535 mA, by its leg number, 1 to 255. For the installation, snake n is
  leg n, a physical place, unchanged by `mapping set` or `mapping cross`.
- **The file.** The budgets are a file of the board's own storage beside `mapping.json`,
  written atomically, by a part file and a rename, as the mapping is, and read as
  strictly as the mapping: an unknown or repeated member, or a value out of range, makes
  it unreadable. It holds the wall's budget and the budget of every leg number that was
  set; a budget of a leg the mapping lacks is kept and unused; a leg the file does not
  name has 0. The spec chooses its name and its JSON form. The first save while the
  defaults are in force writes a whole file: the wall's budget then in force, every leg
  at 0, and the one value set; until a file is saved, every set writes, even of the value
  in force. Once one is saved, the same value again writes nothing.
- **The defaults.** While no budgets are saved, or the file is unreadable, which is said
  once in the log and replaced whole at the next save, every leg's budget is 0 and the
  wall's comes from the host. On the board it is what WLED's limiter gave the LEDs:
  WLED's maximum as WLED loaded it, `BusManager::ablMilliampsMax()`, the value of
  `firmware/limit.json` that `install-firmware` and `set-limit` write, or WLED's 850 when
  none is stored, less 120 mA; 730 mA for 850; 1 mA for a maximum of 120 or less; no
  limit for a maximum of 0. Every board keeps today's limit across the update, the bench
  and the installation alike: the installation, whose 3,600 LEDs pass 730 mA at rest, is
  held at level 1 as today, and the bench's strip is held within the same 730 mA, which
  WLED's level let it pass by about its LEDs at rest. The emulator and the core's test
  host have no WLED settings and no pin to protect: their default is no limit, so that the
  demo show, the previews and every test that saves no budgets show what they show today.
- **The commands**, which the owner approves by name through this seed:
  - `limits` and `limits <from>` report the budgets and the latest written refresh's
    estimates in one reply of at most 1,024 bytes, as every reply is:
    `{"ok":true,"saved":<bool>,"wall":[N,B,E,<0|1>],"legs":[[leg,N,B,E,<0|1>],...],"next":<k|null>}`,
    each array the leg's number for a leg, then the LED count, the budget, the estimate
    and whether it was `limited`, 1 or 0; the legs in the mapping file's order from position `<from>`,
    0 when it is left out, as many as fit, and `next` the position of the first leg left
    out, or null; the app and the command tool follow `next`, as they follow `order get`'s.
    `saved` is false while the budgets are the defaults. Without a usable mapping it gives
    the wall alone and no legs. It is never refused but for a `<from>` that is not a
    whole number from 0 to 65,535, `bad-argument`.
  - `limits wall <mA>` saves the wall's budget, and `limits snake <n> <mA>` the budget of
    leg n, at once; `limits default` removes the budgets' file, so that the defaults are in
    force again and `saved` is false, and writes nothing when there is none. They are
    refused in this order: `bad-argument` for words that are not the form, a leg number
    outside 1 to 255 or a value out of range; `busy` while a catalog rebuild runs; `show-invalid`
    while the show is invalid; `bad-argument` for a leg number the mapping lacks; `busy`
    while the start-up check runs or an upload is open; `storage-error`. They are accepted
    while a mapping test shows. There is no revision: the last save wins.
  - The command tool sends the five forms.
- **WLED's own limiter.** The odrig firmware switches it off in memory by setting
  `BusManager::_useABL` false before every send, again after any re-making of its
  outputs, and never changes WLED's maximum or an output's: nothing WLED stores changes,
  so that `read-limit` reads what `set-limit` wrote and stock WLED after `restore-stock`
  keeps the bench's limit. `install-firmware` keeps writing
  `firmware/limit.json` into WLED's settings. The firmware page says that WLED's stored
  maximum is the odrig firmware's default wall budget and the stock firmware's limit.
- **The standalone firmware**, a trial program that does not yet host the core, loses its
  own copy of WLED's limiter, which nothing calls: `firmware/standalone/src/limit.h` and
  `limit.cpp`, the `limit` mode of `tests/firmware/host/host.cpp`, `limit.cpp` in
  `tests/firmware/hostprogram.py`'s parts and `tests/firmware/test_standalone_limit.py`
  go together; its settings and `ODRIG_LIMIT_DEFAULT_MA` stay. The core's suite takes its
  estimate and fade from that test's `reference` and `faded`, without the chip's 120 mA,
  with the level of these constraints found by halving, a level of 255 changing nothing, the estimate made
  again from the bytes sent and `limited` as above. `docs/drifts.md` records for seed 12 that its requirement 6, the
  limit members of its probe report and its tasks 6 and 10 give way: the program, once it
  hosts the core, gives the core its stored limit less 120 mA as the default wall budget,
  and the core limits.
- **The probe build's** `limited`, `limit_ma` and `used_ma` keep reporting WLED's own
  limiter, and the probe's code stays as it is: under the odrig firmware, with a stored
  maximum of 0 or above 120 mA, `limited` and `used_ma` read 0, which is the check that
  WLED dims nothing, and `limit_ma` keeps reading WLED's maximum less 120, 730 with 850
  stored; with a maximum of 1 to 120 mA, `limit_ma` is 0 and the unchanged probe counts
  every send as `limited`, a reading of the probe and not WLED dimming, which the probe's
  table in `docs/firmware.md` says. `tests/board/test_probe.py`'s target test expects, at
  the default 730 mA, `limited` and `used_ma` at 0 and the bytes the core's fade at level
  1 gives, a lit channel reading 1 and no longer WLED's 128, and the read-back paragraph
  and the example probe line of `docs/firmware.md` follow. The board suite's limiter tests assert exactly that
  and check the core's limiting through `limits`. A board test checks the board's default
  only when `limits` reports `saved` false at its start, and says so when it skips it;
  every board test that saves budgets ends with `limits default`. The rule that turns
  WLED's maximum into the default sits in a header the firmware tool's suite compiles and
  tests on the computer, which is where the default for a stored maximum of 0, no limit,
  is checked. The run with a maximum of 0 stored saves `limits wall 730` before
  `set-limit` stores 0, so that the bench never plays without a wall budget across the
  restart, and ends with `limits default` after 850 is stored again.
- **The firmware tool.** `read-show` saves the budgets' file with the show, and the
  show folder's check accepts its name. `install-show` writes a folder's budgets file
  only when asked, with `--limits`, after checking it as the core reads it; without
  `--limits` the folder's copy is ignored and the board's file, or its absence, is kept,
  unlike `order.txt`, whose folder copy is installed, so that a budget never moves from
  the installation to the bench by accident. `--limits` with a folder that holds no budgets file is refused,
  `limits-missing`, and with one the core would find unreadable, `limits-malformed`, both
  before the board is touched and both in the error table of `docs/firmware.md`.
- **The bench.** The working rules' board rules gain one: on a board whose strip is fed
  from its 3.3 V pin, the wall's budget is never 0 or above 730 mA, and `install-show
  --limits` is not run there with a folder of the installation.
- **The refresh rate.** On the board the rate stays within 20 to 50 a second with every
  snake and the wall limiting, measured with the dense 60 x 60 clip as `docs/firmware.md`
  measures it; no work is done to raise a rate inside that range. The core's memory with
  the target mapping, a show of 100 items and a drive stays under its 131,072 bytes.
- **The panel.** Settings gets a panel `Current limits` under the Mapping panel. A short
  explanation says what a budget is, that the values beside the fields are WLED's
  estimate and not a measurement, and that a low wall budget also dims the diagonal that
  the mapping from a photo reads. A field for the wall's budget, in mA, with the wall's
  estimate beside it; under it a row for each snake, `Snake n · columns a–b`, with its
  field and its estimate, shown while `mapping get` reports the installation's twenty
  snakes as editable; for another mapping, or none, the panel has the wall's field alone.
  A field takes digits only; a stored 0 shows as an empty field with the placeholder `No
  limit`. A value is saved when it is entered or the field is left; a value out of range
  is not sent, and the app says the range and shows the saved value again; a save is said
  as the mapping's saves are, and each refusal code gets its own sentence, with the saved
  value shown again; an emptied field saves 0. A field whose text is the value last read
  sends nothing when entered or left: only changed text is saved, and an emptied field is
  changed only when the saved value is not 0. A budget from 1 to the LEDs' count, 3,600 mA for the wall and 180 mA
  for a snake, is saved, and the app says beside it that every LED is then held at its
  lowest level; 0 never gets that warning. While no budgets are saved the panel says
  that the wall's budget is the installation's default. A dimmed snake or wall is marked beside its
  estimate. The panel reads `limits` every two seconds while Settings shows, updating
  every estimate but never the value of a field that has the focus or unsaved text, and
  nothing while a save is out. An installation whose software does not know `limits`
  gets the explanation and nothing to set.
- **One app.** The panel is the same in the APK, the browser and the emulator's
  Controller view, and once budgets are saved the emulator's LEDs show the limiting as
  the board's do.
- **The records.** `docs/firmware-additions.md`, row 14: the LED current of the wall and
  of each snake is limited by the budgets kept on the board, 0 being no limit, done in
  `core/`, seeds 15 and 45, and seed 12 by the core. `docs/decisions.md` records that the
  limiting moved into the core, that the limit became budgets kept on the board with WLED's
  stored maximum as the board's default, the commands by name, and the bench rule.

## Required Behavior

1. With the wall's budget at 0 or above what a picture draws, brightness 1 to 255 shows
   1 to 255 on the LEDs, on the board as in the emulator.
2. A snake whose level is below 255 is dimmed at that refresh by it, to within its
   budget unless the level is 1, and the others are not; a wall whose level is
   below 255 is dimmed as a whole, after the snakes' own budgets.
3. The budgets are set in Settings' new panel and with the command tool, saved on the
   installation at once, kept across a restart, and shown as the installation has them.
4. The estimates of the wall and of each snake, and whether each was dimmed, are shown
   beside their fields.
5. WLED's own limiter never dims the odrig firmware's outputs, and what WLED stores is
   unchanged by it.
6. A board without saved budgets keeps the limit it has today; the emulator without them
   shows what it shows today.
7. The pages of the commands, the core, the firmware, the firmware additions, the
   emulator, the app and the working rules describe the estimate, the limiting, the
   budgets, the file, the defaults, the panel and the bench rule; the decisions record
   the changes.

## Definition Of Done

1. All test suites that need no board and no phone pass. The core's suite estimates,
   levels and fades snakes and the wall exactly by the rule, in its order, against its
   own reference: the estimate and the fade of `tests/firmware/test_standalone_limit.py`
   without the chip's 120 mA, and the level of the constraints;
   checks the defaults, the file's strict reading, its atomic save and a power loss at
   every step, the commands and their refusals, and that snake n's budget still dims
   columns 3n-2 to 3n after `mapping set` moved its pin and after `mapping cross on`; the
   reference player of `tests/core/support.py` states the limiting a second time. The
   emulator's suite shows the limited LEDs once budgets are saved and sends the commands
   through the command tool. The firmware tool's suite keeps the file through
   `read-show`, and writes it with `install-show --limits` only. The app's suite checks
   the panel in Chrome against the emulator. The docs suites pass.
2. With a board, the board suite passes on the probe build.
3. A new firmware and a new APK are built and put with the artifacts. The owner checks on
   the installation: with the wall's budget at 0, brightness changes what the LEDs show;
   with a bright full-wall animation at brightness 255 and snake 1's budget at 500 mA,
   snake 1 is visibly dimmer than the others and the panel shows it dimmed, with its
   estimate at 500 mA or a little under, 451 for full white.

## Open Questions

None. By approving this seed the owner rules on what the working rules reserve for the
owner, as the constraints take it:

- the limiting moves from WLED's own limiter into the core, because WLED applies its
  limits for each output only while its limit for the whole is 0, and does not run in
  the emulator;
- the limit stops being the single value of `firmware/limit.json`: it becomes a budget
  for the wall and one for each snake, kept on the installation, with WLED's stored
  maximum, less 120 mA, as the board's default while none are saved;
- a budget is a ceiling on the estimate: the level is the largest whose faded picture
  stays within the budget, which is stricter than WLED's level for budgets above the LEDs
  at rest and the same, level 1, below them;
- the commands `limits`, `limits <from>`, `limits wall <mA>`, `limits snake <n> <mA>` and
  `limits default`, and the reply of `limits`;
- the power: no limit by default in the emulator, today's limit on every board, budgets
  that move to a board only with `--limits`, and the bench rule.

## The Owner's Answers

On 2026-10-27, after the finding that every brightness from 2 to 255 looked the same,
the owner asked for a seed that allows changing WLED's limits on brightness, with the
budget configurable in the app, and that also allows, in Settings, a limit for every
specific snake, not in the mapping's interface but in a new one below it. The same day
the owner said that the installation's LEDs are fed by several supplies, each feeding a
group of six or seven snakes, and on 2026-10-25 that the installation has no brightness
limit. Showing the brightness as 0 to 100 % instead of 0 to 255 was the owner's
brainstorm of 2026-10-27, not to be built, and is not part of this seed.
