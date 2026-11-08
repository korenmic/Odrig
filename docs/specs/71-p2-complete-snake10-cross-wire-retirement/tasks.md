# Tasks

Each task is one proof commit with only its own checkbox ticked. A test for a fault is
seen failing first.

- [x] 1. Remove the emulator's count of the retired command
  - `emulator/binding.py` and `emulator/engine.py`; the emulator's tests of the routing and
    of the refused command, seen failing first.
  - Requirements: 1.1–1.2, 3.1.

- [ ] 2. Remove the command tool's form of it
  - `odrigctl/cli.py`; `tests/mapping/test_hosts.py`, the usage error seen failing first.
  - Requirements: 2.1–2.2.

- [ ] 3. The audit and the documents
  - The search of the design, its results in `docs/drifts.md`; the user-facing documents
    checked.
  - Requirements: 4.1–4.2, 5.1–5.2.

- [ ] 4. Deliver
  - Every suite that runs here; the pull request; the APK built from the branch that joins
    every unmerged seed, and its place on the Drive in `verification.md`.
  - Requirements: 5.1.
