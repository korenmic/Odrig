# Tasks

Each task is one proof commit with only its own checkbox ticked. A test for a fault is
seen failing first.

- [ ] 1. Keep the lock's value on the phone, changed only by a confirmed press
  - `mapping.js`: the stored value, `dropEdits()` in place of `relock()`, the dialog that
    survives, the control without a board, the status line's reasons and the refused
    store.
  - The scenarios `kept`, `noboard`, `refused` and `unknown` seen failing first; the old
    relocking expectations changed after.
  - Requirements: 1.1–1.2, 2.1–2.2, 3.1–3.2, 4.1–4.2, 5.1–5.2, 6.1–6.2, 7.1, 8.1.

- [ ] 2. The documents
  - `docs/android-app.md`, its check on a phone and `tests/app/test_docs.py`; the change
    log of `docs/decisions.md`; `docs/drifts.md`.
  - Requirements: 9.1–9.2.

- [ ] 3. Deliver
  - Every suite that runs here; the pull request; the APK built from the branch that joins
    every unmerged seed, and its place on the Drive in `verification.md`.
  - Requirements: 8.1.
