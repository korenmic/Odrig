# Design

## The value (`app/www/screens/mapping.js`)

- `LOCK_KEY = "odrig.mappingLock"`. `keptLock()` reads it inside `try`: `"unlocked"` gives
  `false`, anything else, a refusal included, gives `true`. `keepLock(locked)` writes
  `"locked"` or `"unlocked"` inside `try`; a refusal sets `unkept`, which the status line
  shows, and a later write that succeeds clears it.
- `editLocked` starts as `keptLock()`, read once when the module loads.

## Who changes it

- `relock()` becomes `dropEdits()`: it drops the held move (`cancel()`), the unsent wanted
  assignment, and the saving state when no call is out. It no longer writes `editLocked`.
- `showing(false)`: `dropEdits()` and `closePrompt()`.
- `visibilitychange` to hidden: `dropEdits()` and `closePrompt()`; the value stays.
- `client.watch`: a new `client.targetVersion()` runs `reset()`, which calls `dropEdits()`
  and leaves the prompt; a link that is not `answers` runs `dropEdits()` while a move or an
  edit is under way.
- `confirmLock()` applies its request whatever happened meanwhile: `editLocked` takes the
  asked value, `keepLock` stores it, and a lock also runs `dropEdits()`. The request keeps no
  version. `lockEpoch` becomes `editEpoch`, which `dropEdits()` counts and a queued save
  checks before it is sent.
- `requestLock()` returns only while `live !== null` or `press !== null`, or Settings is
  not shown. The button's `disabled` follows the same two.

## What the lock allows

- `permissionLocked()` and `locked()` stay: `editLocked`, a pending prompt, Settings not
  shown, the page hidden, the link not `answers`, a read pending, a read not fresh, or a
  mapping that is not editable each block a write.
- The status line, `mapping-lock-state`:
  - locked: `Mapping edits are locked.`;
  - unlocked, the link not `answers`: `Mapping edits are unlocked. Edits wait until the
    installation answers.`;
  - unlocked, a read pending or not fresh: `Mapping edits are unlocked. Edits wait for the
    mapping to be read.`;
  - unlocked and editable: `Mapping edits are unlocked. Changes are saved immediately.`;
  - unlocked and not editable: `Mapping edits are unlocked.`, the error line saying why;
  - followed, when `unkept`, by ` This choice could not be kept on this phone; it holds
    until the app is closed.`

## Tests

`tests/mapping/test_lock.py` with new modes of `tests/app/page/scenarios/mapping-lock.js`,
in Chrome against the emulator and stand-ins:

- `kept`: unlock; hide the page and show it; leave Settings and return; `client.begin()`
  again; reload the app and open Settings: unlocked each time, and an arrow key on a handle
  saves. Lock, reload: locked.
- `disconnect`, changed: a withheld reply and the next answer keep it unlocked, and edits
  come back.
- `noboard`: a target that never answers: the control is enabled; Cancel keeps it locked;
  confirm unlocks it and the line says edits wait until the installation answers.
- `refused`: `localStorage.setItem` throws; unlock: unlocked for the run, and the line says
  it could not be kept.
- `unknown`: a stored `maybe` reads as locked.
- The default scenario's `exitRelocked` and `hiddenRelocked` become `exitKept` and
  `hiddenKept`; `target` keeps the prompt across the change of target and its answer
  unlocks for the other target; `queued` leaves the lock unlocked. They change after the new
  tests were seen failing.

## Documents

`docs/android-app.md`: "Mapping edit lock" rewritten for the kept value; a step 24 of "The
check on a phone", the note becoming 25, and `tests/app/test_docs.py`'s counts; a bullet of
"What is open". The change log of `docs/decisions.md`; `docs/drifts.md`.
