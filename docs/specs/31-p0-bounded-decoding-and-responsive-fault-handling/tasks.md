# Tasks: bounded decoding and responsive fault handling (seed 31)

Seeds 02, 04, 07, 14, 20, 28 and 38 are implemented before these tasks start. Where the
real code differs from what the design relies on, follow the code and record the
difference in `docs/drifts.md`. Tasks 1 to 4 need no board; task 5 needs the board.

Rules for every task:

- One task is one commit, which ticks its checkbox here. Stage named paths only.
- The suites that need no board pass before each commit: `npm test --prefix converter`,
  `python3 -m unittest discover -s tests/converter -t .`, `make -C core test`,
  `python3 -m unittest discover -s tests/emulator -t .`,
  `python3 -m unittest discover -s tests/onboarding -t .`, `python3 firmware/fw.py test`,
  `python3 -m unittest discover -s tests/app -t .` and the mapping suite.
- "Prove it fails first": watch the test fail on the code before, and put what was seen
  into the commit message.
- Code states what it does now; no comment about seeds, tasks or dates.
- No command is added and no reply changes. The format does not change.
- Answers to questions that come up go into `docs/drifts.md`.

- [x] 1. The reproducer and the unbounded call
  - Set the seed's `state.json` to `in_progress`.
  - `tests/core/huge_tail.py`; the test host's `--trace-calls`; `tests/core/test_bounded.py`
    with the test of the most a call reads, which fails before task 2.
  - Prove it fails first: one `poll` with the reproducer reads the whole file.
  - This task's commit holds the failing test marked as an expected failure, and task 2
    removes the mark.
  - Requirements: 7.1, 7.2

- [x] 2. Settling in slices
  - `core/src/odrg_decoder.h/.cpp`: the settling fields, `settle_more`, `kPending`,
    `body_read`. `core/src/reasons.h`: `kPending` without a name. `core/src/core.cpp`,
    `core/src/upload.cpp`, the drive's check: `kPending` is "going on". `core/Makefile`
    and `tests/core/support.py`: the host built with slices of 7 bytes.
  - Tests: every vector's reason unchanged with slices of 7 bytes; the reproducer's reason;
    failed reads and a drive pulled out while settling; no reply or log line says
    `pending`.
  - Requirements: 1.1 to 1.5, 3.1 to 3.3, 4.3

- [ ] 3. Playback in slices
  - `core/src/player.cpp`: `kCatchUpBytes` in the catch-up loops; a refresh without a new
    picture keeps the one before.
  - Tests: frames of 1 ms after a pause catch up over several refreshes and reach the
    picture of their time; the demo show's pictures and times unchanged.
  - Requirements: 2.1 to 2.3

- [ ] 4. The fault's context, the emulator's measure and the documents
  - `core/src/core_state.h`, `core/src/core.cpp`, `core/src/upload.cpp`, the drive's
    check: `FaultContext`.
  - `tests/emulator/test_bounded.py`: every `status` within 50 ms with the reproducer
    installed, through the start, the playback and the check.
  - `docs/core.md`, `docs/reasons.md`, `docs/firmware.md`; `docs/decisions.md`: a line.
  - Requirements: 4.1, 5.1, 5.2, 6.1, 6.2, 7.3 to 7.5

- [ ] 5. The board
  - In the run's board session: the reproducer on the microSD card, the firmware of the
    run, no watchdog reset and no `status` waiting longer than 50 ms through the start, the
    playback and the check; the firmware's identity and reset reasons recorded in
    `docs/firmware.md`, "Verified on the board"; the seed's state `completed` when all is
    seen, otherwise what is missing said there.
  - Requirements: 4.2, 7.6
