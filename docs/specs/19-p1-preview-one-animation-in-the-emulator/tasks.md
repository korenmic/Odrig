# Tasks: preview one animation in the emulator (seed 19)

Seeds 03, 06, 07, 11, 14 and 16 are implemented before these tasks start. Where the real
code differs from what this spec's design relies on, follow the code and record the
difference in `docs/drifts.md`.

No task needs the board. Task 3 needs the owner.

Rules for every task:

- One task is one commit. The same commit ticks the task's checkbox in this file.
- Stage named paths only, never `git add -A`, `git add .` or `git commit -a`. After
  committing, read `git show --stat`.
- The tests of a task are in the task's commit. Before committing, run the suites that
  need no board and no phone, from the repository root; all pass:
  `.venv/bin/python -m unittest discover -s tests/converter -t .`,
  `npm test --prefix converter`, `make -C core test`,
  `python3 -m unittest discover -s tests/emulator -t .`,
  `python3 -m unittest discover -s tests/onboarding -t .`, `python3 firmware/fw.py test`
  and `python3 -m unittest discover -s tests/app -t .`.
  Run them so that a failing suite stops the commit: no pipe hides its status.
- Where a task says "Prove it fails first", run the test against the state described,
  watch it fail, and put the observed failure in the commit message.
- Code and tests state what they do now. No comment about seeds, tasks, dates or earlier
  versions. No command, script or document lists test files.
- The command imports nothing of `odrig/` or `converter/`, and writes no show file.
- Answers to questions that come up are recorded in `docs/drifts.md`, not asked.

- [ ] 1. The command
  - Set `"state": "in_progress"` in
    `project-seeds/19-p1-preview-one-animation-in-the-emulator/state.json`.
  - `shows/preview/show.json`; `emulator/preview.py` as the design has it.
  - `tests/emulator/test_preview.py`: every test of the design's list.
  - Prove it fails first: the test that previews a file of the example's canvas, against
    the repository without the command, fails: `No module named emulator.preview`.
  - Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.2, 2.3, 2.4, 3.1, 3.2, 3.3, 3.4, 4.1,
    4.2, 4.3, 5.1

- [ ] 2. The documents
  - `docs/emulator.md`, `agent/getting-started.md`, `AGENTS.md`, `docs/decisions.md`.
  - Run every suite that needs no board and no phone, and the walkthrough of the pages
    for newcomers.
  - Requirements: 5.2

- [ ] 3. The owner looks at one animation
  - The owner runs the command with a file of their choice and says what they saw. On
    Windows too, when a computer with Windows is at hand.
  - Set the seed's `state.json` to `completed`, with `completedAt`.
  - Requirements: 5.3
