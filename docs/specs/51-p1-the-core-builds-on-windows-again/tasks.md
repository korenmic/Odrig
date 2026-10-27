# Tasks: the core builds on Windows again (seed 51)

Requirements: [requirements.md](requirements.md). Design: [design.md](design.md).

No task needs the board or a phone. Every task is done and checked on Windows.

Rules for every task:

- One task is one commit, with the subject `Seed 51 task <n>: <title>`. The same commit
  ticks the task's checkbox in this file.
- Stage named paths only, never `git add -A`, `git add .` or `git commit -a`. After
  committing, read `git show --stat`.
- Prove it fails first: before the mend, run what the task names on Windows, see it fail,
  and put the failure seen in the commit message.
- Run on Windows, one at a time, the suites the task names: `npm test --prefix converter`,
  `.venv\Scripts\python -m unittest discover -s tests/converter -t .`,
  `.venv\Scripts\python core/build.py test`,
  `.venv\Scripts\python -m unittest discover -s tests/emulator -t .`,
  `.venv\Scripts\python -m unittest discover -s tests/app -t .` and
  `.venv\Scripts\python -m unittest discover -s tests/onboarding -t .`. Two suites never
  run at once. After a suite, nothing it started runs.
- Code and tests state what they do now: no comment about seeds, tasks, dates or earlier
  versions.

- [x] 1. The comparison GCC refuses
  - Set `"state": "in_progress"` in
    `project-seeds/51-p1-the-core-builds-on-windows-again/state.json`.
  - `core/src/catalog.cpp`, `page_step`: `static_cast<uint32_t>(line.length) + 1 <
    kOrderLineRoom`.
  - Prove it fails first: `.venv\Scripts\python core/build.py shared` stops with
    `src/catalog.cpp:860:33: error: comparison of integer expressions of different
    signedness` and `error: build-failed: g++ ended with status 1`.
  - Suites: core, onboarding.
  - Requirements: 1.1, 1.2, 1.3, 3.1, 3.2, 3.3, 4.3

- [x] 2. The core compiles with Microsoft's compiler
  - `tests/emulator/test_build_script.py`: the class `MicrosoftsCompiler` of the design,
    skipped where the script finds no Microsoft compiler.
  - `core/src/core_state.h`: the macro `ODRIG_NOINLINE`; the nine functions of
    `catalog.cpp` and `player.cpp` use it.
  - `core/src/catalog.cpp`, `catalog_read_internal`: `Marker marker = {};`.
  - Prove it fails first: the new test fails before the macro with `error C2065:
    'noinline': undeclared identifier`, and with the macro alone with `warning C4701:
    potentially uninitialized local variable 'marker' used`.
  - Suites: core, emulator.
  - Requirements: 2.1, 2.2, 2.3, 3.1, 3.2, 3.3, 4.1, 4.2

- [x] 3. The pages, every suite, and the seed done
  - `docs/core.md`: the sentence of the design on the emulator's suite and Microsoft's
    compiler.
  - One entry at the end of `docs/drifts.md`, `## Seed 51: the core builds on Windows
    again`.
  - Every suite on Windows, one at a time; all pass, the test of task 2 run and not
    skipped.
  - In a copy under `scratch/`: `core/build.py shared --cxx cl`, and every source of the
    core and of the test host compiled with Microsoft's compiler and the script's flags.
  - The emulator from the main checkout with no `--core`, an empty show and a drive, on
    ports of its own: `status` shows a playing animation, `list` the drive.
  - Set the seed's `state.json` to `completed`, with `completedAt`, and take it out of
    "What is coming" in `AGENTS.md`.
  - Suites: every suite.
  - Requirements: 3.4, 3.5, 4.4, 5.1, 5.2, 5.3, 5.4
