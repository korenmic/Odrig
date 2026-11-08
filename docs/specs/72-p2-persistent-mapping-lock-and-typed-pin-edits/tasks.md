# Tasks

Each task is one proof commit with only its own checkbox ticked. A test for a fault is
seen failing first.

- [ ] 1. Make `Lock mapping edits` a checkbox of the kept value
  - `index.html`, `style.css`, `mapping.js`; the scenario `checkbox` seen failing first; the
    helpers that read `aria-pressed` changed after.
  - Requirements: 1.1–1.5.

- [ ] 2. Make each pin a typed field
  - `mapping.js`'s fields, their commit, Escape, drafts and refusals; the scenario `typed`
    seen failing first; the scenario that reads the pins' words changed after.
  - Requirements: 2.1–2.8.

- [ ] 3. The documents
  - `docs/android-app.md`, its check on a phone and `tests/app/test_docs.py`;
    `docs/drifts.md`.
  - Requirements: 3.1.

- [ ] 4. Deliver
  - Every suite that runs here; the pull request; the APK built from the branch that joins
    every unmerged seed, and its place on the Drive in `verification.md`.
  - Requirements: 1.1, 2.1.
