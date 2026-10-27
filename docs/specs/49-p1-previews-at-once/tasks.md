# Tasks: previews at once, each as soon as it is known (seed 49)

The code these tasks start from is `master` at `3709ce0`. The seed has no open question: a
question that comes up is decided and recorded at the end of `docs/drifts.md` under "Seed
49", never asked. Tasks 1 to 5 need neither the board nor a phone. Task 6 is the owner's.

Rules for every task:

- One task is one commit, which ticks its checkbox here. Stage named paths only, never
  `git add -A`, `git add .` or `git commit -a`. After committing, read `git show --stat`.
- The tests of a task are in the task's commit. Before committing, run the suites the task
  names from the repository root: `python3 -m unittest discover -s tests/app -t .` and
  `python3 -m unittest discover -s tests/onboarding -t .`; task 5 runs every suite that
  works on this computer. Long suites run with the shell's own background run, never
  `nohup ... &`, which makes the tests' Ctrl-C ignored.
- "Prove it fails first": run the new test against the state before the change, watch it
  fail, and put the observed failure in the commit message.
- Code and tests state what they do now: no comment about seeds, tasks, dates or earlier
  versions. No command, script or document lists test files.
- No command, reply, member or error code is added; the board, the firmware, the core and
  the emulator do not change. The APK is not built: another piece of work is changing it.
- The decisions a task takes beyond the seed go into `docs/drifts.md` under "Seed 49" in
  the task's commit or in task 4's.

- [x] 1. A preview by name and size
  - Set the seed's `state.json` to `in_progress`.
  - `app/www/previews.js`: `named` and `keyByName(file, bytes)`.
  - `app/www/screens/show.js`: `previewOf(animation)`, used by `rowsState()` and
    `drawNow()`.
  - `tests/app/support.py`: `run(..., thumbnails=None)`, a folder served under
    `/thumbnails/` in place of `thumbnails/`.
  - `tests/app/page/scenarios/keys.js`: the squares in its snapshot (file, source,
    background colour) and the plan's `{"untilRows": n}` and `{"enter": folder}`.
  - `tests/app/test_keys.py`: `Paged.busy_always`, every `catalog page` refused with
    `busy`.
  - `tests/app/test_previews.py`: the rows by name and size while every page is `busy`;
    the made-up catalog's two keys of one size, another size, a card row by the last part
    of its path, a black square without a preview, and a key from the pages that replaces
    the one by name; the show without a catalog with its two previews before Settings'
    rebuild and after it.
  - Prove it fails first: the rows by name and size have no source before the change.
  - Suites: app, onboarding.
  - Requirements: 1.1 to 1.5, 4.2, 6.4

- [ ] 2. The keys of each reply used at once
  - `app/www/client.js`: `askPage()` makes `keysVersion` grow when a reply adds a name;
    `keyOf()` looks in the read under way of the row's storage first.
  - `tests/app/page/scenarios/keys.js`: the plan's `{"until": "some-keys"}`.
  - `tests/app/test_keys.py`: with slow pages, rows have keys while the storage has none,
    the names of the first page before the last page is asked, and each such key is the
    one the board gives; with `thumbnails=` a made-up catalog holding some of the target's
    keys under other names, at `some-keys` those rows' squares have their image and the
    others none, on a black background.
  - Prove it fails first: no row has a key before the storage's keys are set.
  - Suites: app.
  - Requirements: 2.1 to 2.4, 4.1

- [ ] 3. The keys kept on the phone
  - `app/www/previews.js`: `VERSION = 2`, both stores created when missing, `kept` taken
    at `start()` without replacing a key kept in this run, `blocked` and `versionchange`,
    and `keeper` with `kept`, `keep` and `forget`.
    - `app/www/client.js`: `keeper`, `keepKeysIn()`, `keptUnder` set by `begin()`,
      `keptTaken`, and `due()` giving no page before it;
    `noteCatalog()` takes the kept keys of an `ok` storage and forgets them for `damaged`,
    `incompatible` and `none`; `askPage()` keeps the keys of a read that ends whole;
    `keptKeysReady()`.
  - `app/www/main.js`: `client.keepKeysIn(previews.keeper)` and `client.keptKeysReady()`
    after `previews.start()`.
  - `tests/app/page/scenarios/keys.js`: the plan's `{"reload": true}`.
  - `tests/app/test_keys.py`: after a reload, `catalog` and no `catalog page`; a new
    generation read and kept, then none read at the next reload; `loading` and `absent`
    keep the kept keys and `damaged` forgets them; another address has keys of its own;
    the silence test finds the keys back with no page read after the silence.
  - `tests/app/page/scenarios/ownpreviews.js`: its helpers open the database without a
    version.
  - Prove it fails first: after the reload the pages are read again.
  - Suites: app.
  - Requirements: 3.1 to 3.8

- [ ] 4. The pages
  - `docs/android-app.md`: the square's sentence; "The keys of the animations", with how a
    row's preview is found, the keys kept by address and storage and the states that drop
    them; and its sentence on a show that `pack` makes.
  - `docs/drifts.md`, at its end, under "Seed 49": the lines of each reply used at once;
    the shape and the key of a kept record; kept keys that come after a read has started;
    the test's own default catalog; the owner's words of 2026-10-28 that the APK waits for
    another piece of work.
  - Suites: app, onboarding.
  - Requirements: 6.1 to 6.3

- [ ] 5. The measurement and every suite
  - In the emulator of the branch, with the show `scratch/seed-44-show` and the card copy
    `scratch/all-card-local`, `--drive-read-only`, the app at `/app/` in a browser: the
    rows of files the default catalog names show their previews with no `catalog page`
    before them, and at a second start no `catalog page` is sent; the requests to the
    target before the first preview, and at a second start the `catalog page` requests;
    beside the numbers of `master` (86 before the first preview, and the same again at
    every start).
  - The round trip to the board over Wi-Fi, the median of 20 `status` and the delay it
    gives for 86 requests, only when the board answers from this computer without changing
    its network; otherwise the report says it waits.
  - The numbers into `docs/drifts.md` under "Seed 49".
  - Every suite that works on this computer: the converter's, the Python library's, the
    core's, the emulator's, the app's, the onboarding suite and the firmware tool's.
  - Suites: all of them.
  - Requirements: 5.1 to 5.4, 7.1 to 7.3

- [ ] 6. The owner's check
  - Once the APK may be built, an APK of the branch on the phone against the board and its
    card: the previews show with the rows or one by one soon after; a square stays black
    only for an animation whose preview is not known; at the second opening of the app the
    previews show at once. Then `state.json` becomes `completed` with `completedAt`, and
    the seed's line leaves "What is coming" in `AGENTS.md`.
  - Requirements: 7.4
