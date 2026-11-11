# Requirements

Seed 72, `project-seeds/72-p2-persistent-mapping-lock-and-typed-pin-edits/seed.md`, built
on seed 84, which keeps the lock's value on the phone. The app's web code, its tests and
documents. No firmware, core, command, reply, wiring or power change.

## 1. The checkbox

1.1 `Lock mapping edits` is a labelled checkbox on the Settings page, in the Mapping panel,
in no menu or folded section. Checked is locked; unchecked is unlocked.
1.2 It shows seed 84's kept value, `odrig.mappingLock`; there is no second value.
1.3 A press opens the "Are you sure?" dialog and leaves the checkbox as it was; only a
confirmation changes it and the kept value. Cancel, Escape and a dismissed dialog change
neither.
1.4 It can be changed with or without a board that answers; that alone sends nothing.
1.5 While locked the pin fields, the handles, held and keyboard moves, `Restore defaults`
and the photo's Apply and Other reading are disabled, and their handlers refuse too.
Reads, `Reload` and the diagnostics stay.

## 2. The typed pins

2.1 Each of the twenty pins beside its snake is a labelled text field holding the pin's
number, with a numeric keyboard, beside the handle that still drags it.
2.2 Typing is a draft. Enter, or leaving the field, commits it once; Escape puts the field
back to the confirmed pin and commits nothing.
2.3 A committed whole number that names one of the twenty pins of the confirmed assignment
moves that pin into the edited snake's row, the pins between moving one place, as a drag
to that row does: one complete unique assignment of the same twenty pins. The snakes, the
canvas, the chain directions and every strip's start stay.
2.4 The pin that row already has commits nothing.
2.5 Empty, malformed, fractional or negative text, or a number that is not one of the
twenty pins, writes nothing; the field goes back to the confirmed pin and the error line
says why.
2.6 A commit saves through the same serialized, revision-checked save and readback as a
drag, with its conflict, storage-error and no-reply handling; nothing is retried by itself
and nothing goes to another target.
2.7 A poll that leaves the assignment as it was keeps a draft and its focus. An assignment
that changed, a new target, leaving Settings or hiding the app drops the draft.
2.8 A field cannot be edited while the lock is on, the board does not answer, the mapping
is not read fresh or is not editable.

## 3. The documents

3.1 `docs/android-app.md`: the checkbox, the typed pins, a step of "The check on a phone"
and a bullet of "What is open"; `docs/drifts.md`.
