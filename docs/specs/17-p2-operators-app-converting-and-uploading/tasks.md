# Tasks: the operators' app, converting and uploading (seed 17)

Seeds 06, 07, 09 and 16 are implemented before these tasks start: the converter's library,
the commands `space`, `remove` and `upload`, the app's first part, and the playlist. Where
the real code differs from what this spec's design relies on, follow the code and record
the difference in `docs/drifts.md`.

Tasks 1 to 6 need Chrome and the Python of `.venv`, and nothing that is not in the
repository. Task 6 builds the APK with the toolchain of `build/app/`, which seed 09 set
up. Task 7 needs the owner and a phone. No task needs the board.

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
- The web code is plain: a browser runs the files of `app/www/` as they are. It imports
  its own files and the converter's library under `converter/`, and nothing else.
- No command is added. The one change of a reply is the canvas in `status`, task 1.
- No file of `converter/lib/` changes.
- A page changes in the commit that changes the code it describes.
- Before a push, fetch: another contributor pushes to this repository.
- Answers to questions that come up are recorded in `docs/drifts.md`, not asked.

- [x] 1. The canvas in `status`
  - Set `"state": "in_progress"` in
    `project-seeds/17-p2-operators-app-converting-and-uploading/state.json`.
  - `core/src/commands.cpp`: `width` and `height` after `error`, `null` without legs.
    `tests/core/support.py`: the reference player reports them. `tests/core/`: a show
    with a canvas, no mapping, a refused mapping, a show invalid for another reason.
  - The tests of other suites that name the members of `status`, and `app/www/commands.js`,
    which keeps the two in its state.
  - `docs/commands.md`, `docs/core.md` where it names the reply, `docs/emulator.md`.
  - Prove it fails first: the test that reads the canvas from `status`, against the core
    as it is, fails: the reply has no `width`.
  - Requirements: 1.1 to 1.3, 6.4

- [x] 2. The converter's library beside the web code
  - `app/apptool/webserver.py`, `app/apptool/stage.py`, `emulator/httpd.py`: the library
    under `converter/`, from `converter/lib/`.
  - `tests/app/`: `serve` and the suite's server give each file of the library; the staged
    folder holds them. `tests/emulator/`: `/app/converter/` gives them. `tests/apk/`: the
    package holds them, byte for byte.
  - `docs/android-app.md`, `docs/emulator.md`.
  - Prove it fails first: the test that asks the tool's server for
    `/converter/index.js` gets 404 from the server as it is.
  - Requirements: 6.1, 6.2, 6.3

- [x] 3. The storage screen
  - `app/www/index.html`, `app/www/main.js`, `app/www/client.js`,
    `app/www/screens/storage.js`, `app/www/messages.js`, `app/www/style.css`: the third
    screen and button, the back gesture, `space`, the rows with their sizes, `remove`
    with its confirmation, and their messages.
  - `tests/app/`: scenarios for the screen, a removal confirmed and one kept, the
    refusals, the look at 360 and 320 pixels.
  - `docs/android-app.md`: the screen, removing, the lines the app sends, the messages.
  - Requirements: 2.1 to 2.5, 5.1, 5.2

- [x] 4. Converting
  - `app/www/convert.js`, the part of the storage screen that adds an animation, the
    preview, and the messages of converting.
  - `tests/app/support.py`: the media made with `.venv` and
    `tests/converter/media_fixtures.py`, a GIF and an mp4 in H.264, and served to the
    driver. Scenarios: each fit and a part for the GIF, compared byte for byte with
    `import` and `encode`; the mp4's durations and colours; `Stop`; `no-canvas` with a
    stand-in target.
  - `docs/android-app.md`: converting.
  - Requirements: 3.1 to 3.7, 5.1

- [x] 5. Uploading
  - `app/www/upload.js`, `app/www/crc32.js`, the client's job, the upload's part of the
    storage screen, and its messages.
  - `tests/app/`: uploading the GIF and the mp4 to the emulator and playing each from the
    show screen; `Cancel`; the space check before the upload; `busy` to `upload end`;
    `no-upload` after the app was hidden; the refusals with stand-in targets.
  - `docs/android-app.md`: uploading, the lines, the messages.
  - Requirements: 4.1 to 4.6, 5.1, 5.2

- [ ] 6. The APK and the documents
  - `python3 app/app.py build`; `tests/apk/` passes against the new APK.
  - `docs/android-app.md`: what is verified, what is open, and the steps of the check on
    a phone for converting, uploading and removing. `docs/decisions.md`: a line in the
    change log. `AGENTS.md`: the seed leaves "What is coming".
  - Requirements: 6.3, 7.1 to 7.3

- [ ] 7. The owner's check on a phone
  - The owner, with the APK on a phone, converts and uploads a video to the emulator on
    the local network and to the board on its own network, and sees it play.
  - Set the seed's `state.json` to `completed`, with `completedAt`.
  - Requirements: 7.4
