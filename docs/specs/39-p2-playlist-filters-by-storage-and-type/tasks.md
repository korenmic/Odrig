# Tasks: playlist filters by storage and type (seed 39)

Seed 36 is in the code these tasks start from (its branch). `type` of `list` comes with seed
37; until that is merged, the core reports none and every row is Normal. Task 3 needs the
owner's phone.

Rules for every task:

- One task is one commit, which ticks its checkbox here. Stage named paths only.
- Before each commit run the app's suite and the onboarding suite; task 2 runs every
  suite.
- "Prove it fails first": watch the new test fail on the code before, and put what was
  seen into the commit message.
- Code states what it does now; no comment about seeds, tasks or dates.
- No command, reply member or error code is added, and nothing outside `app/www/`, the
  tests and the documents changes.

- [ ] 1. The two filters
  - Set the seed's `state.json` to `in_progress`.
  - `app/www/screens/filters.js`; `index.html`, `style.css`; `screens/show.js` (rows that
    match, the empty list); `screens/reorder.js` (off while filtered);
    `screens/selection.js` (shown rows only).
  - Tests, `tests/app/test_filters.py` and `tests/app/page/scenarios/filters.js`: every
    combination and its counts, the empty list and `Show all`, the choices kept across a
    reload, reordering off and why, Select all and a filter change, the Tests group, a
    card absent, plugged in and pulled out, rows without `type`, no request more.
  - docs/android-app.md describes the filters.
  - Prove it fails first: Animations has no filter Storage.
  - Requirements: 1.1 to 1.9, 2.1 to 2.3, 3.1, 3.2

- [ ] 2. The APK and every suite
  - Every suite that runs without a board; `python3 app/app.py build`; `tests/apk`.
  - docs/decisions.md: a dated line. The seed stays `in_progress` for task 3.
  - Requirements: 3.3

- [ ] 3. The owner's check on a phone
  - The owner, with the APK of the run, against the board with the card in: each filter,
    the counts, the empty list, a reload, reordering off while filtered. Only then is the
    seed `completed`.
  - Requirements: 3.4
