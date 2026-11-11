# Tasks: the emulator's 404 and 405 reach the client (seed 88)

Requirements: [requirements.md](requirements.md). Design: [design.md](design.md).

No task needs the board or a phone. Every task is done and checked on Windows, in the
worktree of the branch `seed-88-404-and-405-reach-the-client`, made from `master` 51e1e3e4.

Rules for every task:

- One task is one commit, with the subject `Seed 88: <n>. <title>`. The same commit ticks
  the task's checkbox in this file.
- Stage named paths only, never `git add -A`, `git add .`, `git add -u` or `git commit -a`.
  After committing, read `git show --stat`.
- Prove it fails first: before the mend, run on Windows the test the task names, see it
  fail, and put the failure seen in the commit message.
- Run on Windows, one at a time, the suites the task names: `npm test --prefix converter`,
  `.venv\Scripts\python -m unittest discover -s tests/converter -t .`,
  `.venv\Scripts\python core/build.py test`,
  `.venv\Scripts\python -m unittest discover -s tests/emulator -t .`,
  `.venv\Scripts\python -m unittest discover -s tests/onboarding -t .`, and those of
  "Suites that need more" in `agent/getting-started.md`. Two suites never run at once.
  After a suite, nothing it started runs.
- Code and tests state what they do now: no comment about seeds, tasks, dates or earlier
  versions.

- [x] 1. The body is read before a 404 or a 405
  - Set `"state": "in_progress"` in
    `project-seeds/88-p1-the-emulators-404-and-405-reach-the-client/state.json`.
  - `tests/emulator/support.py`: `raw_request` with `later`, `pause` and `end`, as the
    design has it.
  - `tests/emulator/test_http.py`, in `WhatTheServerPassesOn`: the four tests of the
    design.
  - Prove it fails first, with `emulator/httpd.py` unchanged: the body that comes after
    its head fails with `ConnectionAbortedError: [WinError 10053]`; the connection that
    ends inside the body gets the 404; the long body is run and what it gave is noted; the
    test of no length to read passes.
  - `emulator/httpd.py`: `declared_length`, `read_body`, `body` and `empty`, as the design
    has them.
  - Suites: emulator, onboarding.
  - Requirements: 1.1, 1.2, 1.3, 1.4, 2.1, 2.2, 2.3, 3.1, 3.2, 3.3, 3.4, 4.1, 4.2, 4.3,
    4.4, 4.5

- [ ] 2. The pages
  - `tests/emulator/test_docs.py`: the test of the design, seen failing before the point
    is written.
  - `docs/emulator.md`: the point of the design under "Commands over HTTP".
  - Two entries at the end of `docs/drifts.md`, with the titles of the design.
  - Suites: emulator, converter, onboarding.
  - Requirements: 5.1, 5.2, 5.3, 5.4

- [ ] 3. Deliver seed 88
  - Fetch `origin`. When `master` has moved past 51e1e3e4, merge it into the branch, never
    a rebase, and make what follows on the merge.
  - Push the branch and open the pull request against `master`.
  - Every suite that works on the computer, on Windows, one at a time: the five of the
    rules, the firmware tool's suite `firmware/fw.py test`, `tests/app`, `tests/mapping`,
    `tests/firmware_host` and `tests/runner`; `tests/apk` and `tests/walkthrough` when
    they can run here. What cannot run, and each failure known on this computer that is
    not a fault of the code, is named with its reason.
  - The emulator's suite five whole times on the branch, one run at a time: no test of a
    404 or a 405 fails.
  - The proofs of "Broken on `master`, mended on the branch" in the design.
  - `verification.md` beside this file: the commits, the proofs, the suites, the pull
    request and its CI.
  - Set the seed's `state.json` to `completed`, with `completedAt`, and take its line out
    of "What is coming" in `AGENTS.md`.
  - Suites: every suite, as above, and the onboarding suite again after the seed's state.
  - Push.
  - Requirements: 3.5, 3.6, 4.6, 4.7, 4.8, 5.5, 5.6, 5.7
