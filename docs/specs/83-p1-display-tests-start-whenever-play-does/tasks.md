# Tasks

Each task is one proof commit with only its own checkbox ticked. A test for a fault is
seen failing first.

- [ ] 1. Let the tests start whenever play does, and an open upload end under them
  - `mapping_control.cpp`: the test's gate on the check and the upload gone, `mapping
    set`'s gate on the check gone; `commands.cpp`: a test refuses `upload begin` alone;
    `player.cpp`: `player_item_added` waits for the test's end.
  - The core's tests of the design, seen failing first; the old `busy` expectations
    changed.
  - Requirements: 1.1–1.4, 2.1–2.2, 3.1–3.4, 4.1, 5.1–5.2, 6.2.

- [ ] 2. The emulator's lines and the documents
  - The emulator's suite over TCP; `docs/commands.md`, `docs/core.md`, the change log of
    `docs/decisions.md`, `docs/drifts.md`; the documents' tests.
  - Requirements: 6.1, 7.1–7.3.

- [ ] 3. Deliver
  - Every suite that runs here; the pull request; the firmware images of both modules,
    built from the branch that joins every unmerged seed, and their place on the Drive in
    `verification.md`.
  - Requirements: 6.1.
