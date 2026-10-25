# Tasks: the mapping from a photo of the diagonal (seed 40)

Seeds 30, 36 and 37 are in the code these tasks start from, the unified branch of the
run of 2026-10-24. Task 4 needs the owner's phone and the installation.

Rules for every task:

- One task is one commit, which ticks its checkbox here. Stage named paths only.
- Before each commit run the app's suite and the onboarding suite; task 3 runs every
  suite.
- "Prove it fails first": watch the new test fail on the code before, and put what was
  seen into the commit message.
- Code states what it does now; no comment about seeds, tasks or dates.
- No command, reply member or error code is added, and nothing outside `app/www/`, the
  tests and the documents changes.

- [x] 1. The analysis
  - Set the seed's `state.json` to `in_progress`.
  - `app/www/photo.js`: `readPhoto`, `analyse`, `assignment`.
  - Tests, `tests/app/test_photo.py` and `tests/app/page/scenarios/photo-analysis.js`,
    `tests/app/media.py` (the turned JPEG), `tests/app/support.py` (`.jpg` under `/m/`):
    every photo of the design's "Tests" read as required, the four photos of the seed
    refused with the count found, the turned JPEG read upright.
  - Prove it fails first: the module does not exist; the scenario's import fails.
  - Requirements: 1.3, 2.1 to 2.6, 4.1, 4.2, 5.1

- [x] 2. The screen
  - `app/www/screens/photomap.js`; `index.html`, `style.css`, `main.js`;
    `screens/mapping.js` exports `latest()` and `saveFromPhoto(pins)`.
  - Tests, `tests/app/test_photo.py` and `tests/app/page/scenarios/photomap.js`: the
    button and the words, the diagonal offered and started, the preview and its numbers,
    the words, the choices with a dead line at an end, Apply saving the permutation on the
    emulator, Discard, Other reading, a conflict said, the photo dropped on leaving.
  - docs/android-app.md describes the feature.
  - Prove it fails first: Settings has no button From a photo.
  - Requirements: 1.1, 1.2, 3.1 to 3.4, 5.2, 5.3

- [ ] 3. The APK and every suite
  - Every suite that runs without a board; `python3 app/app.py build`; `tests/apk`.
  - docs/decisions.md: a dated line. The seed stays `in_progress` for task 4.
  - Requirements: 5.3, 5.4

- [ ] 4. The owner's check on a phone
  - The owner, with the APK, at the installation with the diagonal showing: a photo from
    the front, the reading, Apply, and the diagonal straight afterwards; a dead line if
    one can be made. The photo joins `photos/` beside the seed with the owner's leave, and
    the suite reads it. Only then is the seed `completed`.
  - Requirements: 5.4
