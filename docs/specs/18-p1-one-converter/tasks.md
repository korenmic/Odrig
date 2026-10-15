# Tasks: one converter (seed 18)

Seeds 01 to 13, 16 and 19 are implemented before these tasks start. Where the real code
differs from what this spec's design relies on, follow the code and record the difference
in `docs/drifts.md`.

No task needs the board, a phone or the owner.

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
- The bytes the converter writes do not change. A stored file changes only in the task
  that makes it.
- Answers to questions that come up are recorded in `docs/drifts.md`, not asked.

- [x] 1. The stored files
  - Set `"state": "in_progress"` in `project-seeds/18-p1-one-converter/state.json`.
  - `tests/converter/make_expected.py`; run it; `converter/tests/expected/` and
    `converter/tests/media/`. The two tests that forbid tracked media allow the folder.
  - `converter/tests/expected.test.js`: every stored file is valid, their size is 8 MB
    at most, and each one equals what `reference.py` answers today.
  - Prove it fails first: the test of the stored files, against an empty folder, fails:
    the files are missing.
  - Requirements: 2.1, 2.2

- [ ] 2. The codec on stored files
  - `decode`, `encode`, `deflate`, `inflate` and the vector checks read the stored
    files; `support.js` gets `expected`.
  - Prove it fails first: `decode.test.js`, with Python taken off its path, fails
    before this task and passes after it.
  - Requirements: 2.1, 3.3

- [ ] 3. The import on stored files
  - `fit`, `timeline`, `import` and `whole` read the stored files and the stored media.
  - Prove it fails first: as task 2, for `import.test.js`.
  - Requirements: 2.1

- [ ] 4. The readers and the command line on stored files; no Python
  - `jsonframes`, `strictjson`, `mapping`, `pack` and `cli` read the stored files.
    `reference.py` and every helper of `support.js` that starts Python go. A test runs
    the suite's helpers with no Python on the path.
  - Prove it fails first: the test with no Python on the path, before the last helper
    goes, fails: the helper starts Python.
  - Requirements: 2.3, 2.4

- [ ] 5. The library
  - `odrig/cli.py`, `__main__.py`, `media.py` and `pack.py` go, with their tests and
    `tests/converter/make_expected.py`; the helper of the generators moves to `errors`.
    The suites of the core, the emulator, the firmware tool and the board pack with the
    converter; the core's benchmark encodes with it; the walkthrough's GIF is stored.
    `requirements.txt` goes. The scope test of who runs converter logic.
  - Prove it fails first: the scope test, against the repository before the task, fails:
    `odrig/cli.py` exists.
  - Requirements: 1.1, 1.2, 1.3, 3.1, 3.4, 4.1, 4.2, 4.3, 5.1

- [ ] 6. The documents and the seed's state
  - `docs/python-library.md` in place of `docs/reference-converter.md`, and every page
    that names the reference converter or its setup; `docs/decisions.md` with a line in
    its change log; `AGENTS.md`: the seed leaves "What is coming".
  - Run every suite that needs no board and no phone, and the walkthrough.
  - Tell the owner that the suites of Windows are to be run there.
  - Set the seed's `state.json` to `completed`, with `completedAt`.
  - Requirements: 3.2, 5.2, 5.3, 5.4
