# Tasks: brightness edits stay with their animation, and a brightness zoom (seed 89)

Requirements: [requirements.md](requirements.md). Design: [design.md](design.md).

No task needs the board or a phone. Every task is done and checked on Windows, in the
worktree of the branch `seed-89-brightness-edits-and-zoom`, made from `seed-87-live-mirror`
at 3ab15e17 with `master`'s seed merged in (124fc998).

Rules for every task:

- One task is one commit, with the subject `Seed 89: <n>. <title>`. The same commit ticks
  the task's checkbox in this file.
- Stage named paths only, never `git add -A`, `git add .`, `git add -u` or `git commit -a`.
  After committing, read `git show --stat`.
- Prove it fails first: before the mend, run the test the task names, see it fail, and put
  the failure seen in the commit message.
- The panel's modules of the app suite are run by discovery, one at a time:
  `.venv\Scripts\python -m unittest discover -s tests/app -t . -p "<module>.py"` for
  `test_brightness`, `test_controls`, `test_look`, `test_panel_top`, `test_now_bar`,
  `test_scope` and `test_docs`; and `.venv\Scripts\python -m unittest discover -s
  tests/onboarding -t .`. Two suites never run at once. After a suite, nothing it started
  runs.
- Code and tests state what they do now: no comment about seeds, tasks, dates or earlier
  versions.

- [ ] 1. A gesture stays with its animation
  - Set `"state": "in_progress"` in
    `project-seeds/89-p1-brightness-edits-stay-with-their-animation-and-a-zoom/state.json`.
  - `tests/app/test_brightness.py`: the stand-in answers `saved <id>`, can answer another
    value and can name a clock; the two tests that become others and the new tests of the
    design's first list, but the hold's.
  - Prove it fails first, with the app unchanged: the held drag and the typed digits are
    dropped at the change, the queued save is not sent, and the press while the panel
    lags is refused.
  - `app/www/screens/brightness.js`: the gesture, `finish`, `mutate`'s guard, confirming by
    status or by `saved <id>`, and the lines of requirements 2.1 and 2.3, as the design has
    them.
  - `app/www/client.js`: `capturedBrightness` and `brightnessSaved`.
  - Suites: the panel's modules, onboarding.
  - Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 2.1, 2.3, 2.4, 2.5, 7.1, 7.3, 7.4, 8.1

- [ ] 2. The hold and the default's line
  - `tests/app/test_brightness.py`: the tests of the hold and of the default's line.
  - Prove it fails first: the box takes a press at once after a change, and no line follows
    a confirmed default.
  - `app/www/screens/brightness.js`: `holdUntil`, its timer and the class `just-changed`;
    the default's line. `app/www/style.css`: `#level-file.just-changed`.
  - Suites: the panel's modules, onboarding.
  - Requirements: 2.2, 3.1, 3.2, 3.3, 3.4, 7.2, 8.1

- [ ] 3. The brightness zoom
  - `tests/app/page/scenarios/zoom-kept.js` and its test; the zoom acts and `look` of
    `tests/app/page/scenarios/brightness.js`; the zoom tests of the design;
    `tests/app/page/scenarios/look.js`'s `measure`; the layout tests of `test_look.py` and
    `test_brightness.py`.
  - Prove it fails first: the zoom tests and the new layout fail on the panel without the
    zoom.
  - `app/www/zoom.js`; the zoom's markup in `app/www/index.html`; its style in
    `app/www/style.css`; in `app/www/screens/brightness.js` the pins, the slider's range,
    `showValue`, the outside line and keeping the pair.
  - The tests of the panel staying at the top: run them; adjust a size whose answer the
    taller panel changes, with its reason in the commit message.
  - Suites: the panel's modules, onboarding.
  - Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 5.1, 5.2, 5.3, 5.4, 6.1, 6.2, 6.3,
    6.4, 6.5, 8.3

- [ ] 4. Against the real emulator
  - `tests/app/test_brightness.py`: the class against the real emulator of the design, with
    its show of two-second turns and its card with clocks.
  - Prove it fails first on the branch's base: in a temporary worktree at 124fc998 with the
    new class copied in, the drag across the end of a turn sets the default and saves
    nothing for its animation. Then it passes on the task's head.
  - Suites: the panel's modules, onboarding.
  - Requirements: 8.2

- [ ] 5. The pages
  - `docs/android-app.md`: "Saved animation brightness controls" and the panel's
    description at the top of the page, as the design has them.
  - Entries at the end of `docs/drifts.md` for the design's decisions.
  - Suites: `test_docs` of the app suite, onboarding.
  - Requirements: 8.4

- [ ] 6. Deliver seed 89
  - Fetch `origin`. When `seed-87-live-mirror` has moved past 3ab15e17, merge it into the
    branch, never a rebase, and make what follows on the merge.
  - Every suite that works on the computer, on Windows, one at a time, by the runner
    `tests/run.py --serial`. What cannot run, and each failure known on this computer that
    is not a fault of the code, is named with its reason and run alone or in the
    arrangement of the CI.
  - A check in a browser against the emulator, as the operator would make it: an override
    dragged across the end of a turn, its line, its value back when the animation returns
    and after a restart of the emulator; a zoom of 2 to 12, the slider between 4 and 5, and
    the zoom kept after a reload.
  - A signed APK from the branch's head with the persistent key, its certificate and
    alignment checked.
  - Push the branch and open the pull request against `seed-87-live-mirror`.
  - `verification.md` beside this file: the commits, the proofs, the suites, the browser
    check, the APK and the pull request. The seed's `state.json` stays `in_progress`, its
    summary naming the pull request, and its line in "What is coming" of `AGENTS.md` says
    it is implemented and delivered in that pull request, not merged, with the owner's
    phone check open.
  - Requirements: 8.4, 8.5, 8.6
