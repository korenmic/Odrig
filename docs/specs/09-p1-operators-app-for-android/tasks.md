# Tasks: Operators' app for Android (seed 09)

Seeds 06, 07 and 08 are implemented before these tasks start: the tasks use the library in
`converter/lib/`, the content commands in the core, the emulator and the firmware, and the
board's network `odrig`. Where the real code differs from what this spec's design relies
on, follow the code and record the difference in `docs/drifts.md`.

Task 2 needs the board on USB, at `/dev/cu.usbmodem*`. Task 4 needs the network, for npm,
two archives, the SDK's packages and Gradle. Tasks 5 to 10 need the Chrome that is
installed. Task 13 needs the owner and a phone. The design's three tables "Assumed, to be
verified" name what tasks 4 and 5 settle: each writes what it found into `docs/drifts.md`,
and task 12 writes it into `docs/android-app.md`.

Rules for every task:

- One task is one commit. The same commit ticks the task's checkbox in this file.
- Stage named paths only (`git add <path> ...`), never `git add -A`, `git add .` or
  `git commit -a`. After committing, read `git show --stat` and confirm it lists exactly the
  files of the task.
- The tests of a task are in the task's commit. Before committing, run the suites that
  need no board and no phone, from the repository root; all pass:
  `.venv/bin/python -m unittest discover -s tests/converter -t .`, `make -C core test`,
  `python3 -m unittest discover -s tests/emulator -t .`, `python3 firmware/fw.py test`,
  `npm test --prefix converter`, and from task 4 on
  `.venv/bin/python -m unittest discover -s tests/app -t .`.
- Where a task says "Prove it fails first", run the test against the state described, watch
  it fail in the way described, and put the observed failure in the commit message.
- Code and tests state what they do now. They carry no comment about seeds, tasks, dates or
  earlier versions.
- No command, script or document lists test files; each suite is selected by discovery.
- The web code is plain: a browser runs the files of `app/www/` as they are. Nothing
  transpiles, bundles or generates a file of it. It imports only its own files and the
  library under `lib/`.
- No file of `converter/`, `odrig/` or `odrigctl/` changes. The library is used as it is.
  Where it lacks what the app needs, record that in `docs/drifts.md`, leave that part of
  the task open and say so in the hand-over; do not change the library and do not copy
  its code.
- A command is read and answered in `core/src` only. The app sends lines of
  `docs/commands.md` to the path `/odrig` and nothing else; `fetch` is in
  `app/www/target.js` only.
- Nothing is installed outside the repository's folder: no package for the whole
  computer, no browser, no Android Studio. `npm` is run with `--prefix app` or
  `--prefix converter` only. Nothing of `app/node_modules/` and nothing of `build/` is
  staged.
- The one licence the setup accepts is `android-sdk-license`.
- The password of `odrig` is written nowhere: not into the app, a test, a document, this
  file, `docs/drifts.md`, a commit message or a hand-over.
- No agent joins this Mac to the board's network or changes the Mac's network settings.
  No agent has a phone: nothing that needs one is reported as checked.
- In task 2: only one program uses the board at a time; every show put on the board has a
  brightness of 40 or less; `esp32-backup/` is never written to, moved, deleted or
  staged; no eFuse is written and the whole flash is never erased; the task ends with the
  board running the firmware and the dim example show, and says so in its commit message.
- `animations/`, `tools/`, `firmware/wled-16.0.1/`, `esp32-backup/`, `scratch/` and the
  stock image at the repository root hold untracked files that are not part of this work.
  Do not move, edit, delete or stage them.
- Answers to questions that come up are recorded in `docs/drifts.md`, not asked.

- [ ] 1. `status` reports the canvas size
  - Set `"state": "in_progress"` in
    `project-seeds/09-p1-operators-app-for-android/state.json`.
  - If `ODRIG_REPLY_MAX` in `core/include/odrig_core.h` is still 192, or `converter/lib/`
    is not there, seed 07 or seed 06 is not implemented: stop, and record that the tasks
    are blocked.
  - `core/src/commands.cpp`: the members `width` and `height` after `error`, as the
    design's "`status` with the canvas size" gives them.
  - `tests/core/support.py`: the two members in the reference player's reply.
  - `tests/core/test_status.py`: the exact bytes for the example show, with
    `"width":60,"height":6`, and for a show on `mapping/legs-20.json`, with 60 and 60;
    the example of `docs/commands.md`. `tests/core/test_startup.py`: both `null` for a
    missing mapping file and for every mapping file of the suite that the core refuses;
    the numbers for a show that is invalid because an animation is missing. The reply
    through both entries of the core.
  - `docs/commands.md`: the section "Status reply" as the design prints it.
    `docs/core.md`, `docs/emulator.md` and `docs/firmware.md`: every `status` reply they
    print, and the members of the emulator's `status` event. The tests that read those
    pages, where they name the members.
  - Prove it fails first: the test of the exact bytes, with the new line expected, fails
    against the core as it is: the reply ends with `"error":null}`.
  - Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.9

- [ ] 2. The firmware with the canvas size, on the board
  - This task needs the board on USB. Without it, leave the task open, say so in the
    hand-over, and go on with task 3.
  - `tests/board/test_commands.py`: with the dim example show on the bench mapping,
    `status` over USB ends with `"width":60,"height":6}`.
  - Prove it fails first: against the firmware that is on the board, the new test fails:
    the reply has no `width`.
  - `python3 firmware/fw.py build`, `python3 firmware/fw.py flash`, then
    `python3 firmware/fw.py test-board`; it passes.
  - `docs/firmware.md`, "Verified on the board": the reply the board gave.
  - Requirements: 1.8

- [ ] 3. The emulator's `--lan`
  - `emulator/httpd.py` and `emulator/app.py` as the design's "The emulator on the local
    network" gives them: the flag, the address the server is bound to, `lan_address`, the
    line `lan:` and the warning.
  - `tests/emulator/test_start.py`: `--lan` is among the options; `--address` is still a
    usage error; `--lan` with `--record` is a usage error; with `--lan` the third line of
    standard output is the `lan:` line in one of its two forms and standard error has the
    warning; without it the output is the two lines of today.
    `tests/emulator/test_http.py`: without the option the emulator listens on 127.0.0.1
    only, as today; with it the listening socket is at `*:<port>`, a command is answered
    on 127.0.0.1, and on the address of the `lan:` line when there is one.
    `tests/emulator/test_scope.py`: the three addresses the design names, all in
    `emulator/httpd.py`.
  - `docs/emulator.md`: `--lan` in the usage line and the table of options; the `lan:`
    line; the warning; that the whole server is on the network then; the question macOS
    may ask. `tests/emulator/test_docs.py` for it.
  - Prove it fails first: the test that starts the emulator with `--lan`, against the
    emulator as it is, fails with the usage message.
  - Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9

- [ ] 4. The tool, the toolchain and a first APK
  - This task needs the network.
  - Before anything is installed, list the entries of the home folder and of
    `~/Library/Caches`, `~/Library/Preferences`, `~/.gradle`, `~/.android` and `~/.npm`
    with their times. List them again at the end, and name in `docs/drifts.md` what the
    task added (assumption T5).
  - Create `app/app.py` and `app/apptool/` with `cli.py`, `paths.py`, `env.py`,
    `toolchain.py`, `stage.py`, `build.py`, `webserver.py` and `device.py`, as the
    design's "The tool" gives them: the four commands, the statuses, the reasons, the
    environment of every child process, the steps of `setup` and of `build`. `device.py`
    is written and not run: it needs a phone.
  - Create `app/toolchain.json` and `app/package.json` as the design prints them, and
    `app/capacitor.config.json`. Add `/app/node_modules/` to `.gitignore`.
  - Create `app/www/index.html`, for now a page that shows the word `odrig` in light text
    on black, and `app/www/old.html`.
  - Run `npm install --prefix app` once, with the tool's environment, and track
    `app/package-lock.json`. Run `python3 app/app.py setup`. Create the Android project
    with `cap add android`, with the tool's environment, in `app/`. Add
    `distributionSha256Sum` to `app/android/gradle/wrapper/gradle-wrapper.properties`.
    Run `python3 app/app.py build`.
  - Track `app/android/` as it was created. Read `git status --short app` first and stage
    nothing that `app/android/.gitignore` leaves out.
  - Verify assumptions T1 to T7 of the design. For each, record what was found in
    `docs/drifts.md`; where one does not hold, take the way the table names. If a
    download address no longer serves the file the design names, take the newest file of
    the same line from the same source, put its size and SHA-256 into
    `app/toolchain.json`, and record the drift.
  - Record in the commit message: the first line of `java -version`; the versions of
    Gradle and of the Android Gradle plugin as the build printed them; the size of the
    work folder and of `app/node_modules/`; the time of the first build and of a second
    one; the size of the APK. After the commit, a build leaves `git status --short`
    empty.
  - `tests/app/__init__.py` and `tests/app/test_tool.py` as the design lists it.
    `tests/apk/__init__.py` and `tests/apk/test_apk.py` with what holds already: the
    identifier, the label, `minSdkVersion` 24, the files of `app/www/` and of
    `converter/lib/` with their bytes, `build.json`, and no file beyond those and
    Capacitor's own.
  - Prove it fails first: with the comparison of the SHA-256 temporarily taken out of
    `toolchain.py`, the test of an archive with one byte changed fails: the archive is
    unpacked. Undo it.
  - Requirements: 3.3, 3.5, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9, 5.1, 5.2, 5.3,
    5.4, 5.5, 5.8, 22.2, 22.5

- [ ] 5. The suite's harness, and frames from a GIF and an mp4 in Chrome
  - `npm ci --prefix converter` has run: the suite compares with
    `node converter/odrig.js import`.
  - Create `tests/app/support.py`, `tests/app/media.py`, `tests/app/page/driver.html`
    and `driver.js`, as the design's "How the suite drives the app" and "The media" give
    them: the emulator, the server with its paths for a test, Chrome, a scenario run and
    its result.
  - Create `app/www/media/sniff.js`, `gif.js`, `mp4.js`, `video.js` and `pixels.js`, and
    `app/www/convert.js` and `convert-worker.js`, as the design's "Reading media" and
    "Converting" give them. Until the add screen is there, a scenario calls them from
    the driver's own page, through the worker and directly.
  - `tests/app/test_readers.py` and `tests/app/test_convert.py` as the design lists
    them, and of `tests/app/test_scope.py` what holds already: the imports, no network
    address, no file of the library tracked outside `converter/`.
  - Verify assumptions C1 to C7 of the design. For each, record what was found in
    `docs/drifts.md`; where one does not hold, take the way the table names. Record the
    largest difference of a colour value between the app and the converter for the H.264
    video, and Chrome's version, in the commit message.
  - Prove it fails first: with the composition offsets of `ctts` temporarily left out of
    `mp4.js`, the test of the video with B-frames fails: the times differ from PyAV's.
    Undo it.
  - If Chrome on this Mac decodes no video that the fixtures can write, record what was
    tried, leave this task open and say so in the hand-over.
  - Requirements: 3.1, 3.2, 3.4, 14.2, 14.3, 14.4, 14.5, 14.6, 14.7, 14.8, 14.9, 14.10,
    14.11, 14.12, 15.1, 15.3, 15.6, 15.7, 15.8, 15.9, 15.10, 15.11, 15.12, 21.2, 21.5,
    21.6, 21.7, 21.9, 21.10

- [ ] 6. The client and the connection screen
  - `app/www/index.html` with the four screens, the four buttons, the line for a target
    that does not answer and the place for messages; `style.css`; `main.js`.
  - `app/www/target.js` with both ways of sending, `client.js` with the queue and the
    `status` that is due every second, `commands.js` with `status`, `messages.js` with
    the texts for reaching the target, and `screens/connection.js`, as the design gives
    them.
  - `tests/app/test_connection.py` as the design lists it. The way through the sender is
    tried with a stand-in for `window.Capacitor` that the scenario puts into the page.
    `tests/app/test_scope.py`: `fetch` in `target.js` only; no path but `/odrig`.
  - Prove it fails first: with the time limit temporarily taken out of `send`, the test
    with a hop that holds every reply back for ten seconds fails: the screen still says
    `Checking` after six seconds. Undo it.
  - Requirements: 6.6, 6.7, 7.8, 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 9.1, 9.2, 9.3, 9.4, 9.5,
    9.6, 9.7, 9.8, 9.9, 10.1, 10.5, 19.2, 21.3

- [ ] 7. The show screen and the items screen
  - `commands.js` with `on`, `off`, `brightness`, `play`, `space`, `list` and `remove`;
    the four classes of the queue and the times at which `list` and `space` are due;
    `screens/show.js` and `screens/items.js`; the texts of the codes these commands can
    give.
  - `tests/app/test_show.py` and `tests/app/test_items.py` as the design lists them.
  - Prove it fails first: with `list` temporarily read once, without `list <next>`, the
    test on the show of 40 items fails: the screen has fewer rows than the show has
    items. Undo it.
  - Requirements: 8.7, 10.2, 10.3, 10.4, 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 12.1, 12.2,
    12.3, 12.4, 12.5, 12.6, 12.7, 13.1, 13.2, 13.3, 13.4, 13.5, 19.5

- [ ] 8. Converting and the previews
  - `screens/add.js` from `empty` to `converted`, as the design's table of states gives
    it: the file input, what is shown of a file, the fit, the start and the length with
    their limits, the switch `Compressed`, the bar, `Cancel`. `preview.js`.
  - `tests/app/test_add.py`, the part up to `converted`: the still preview against the
    first picture of the file the converter makes; each fit; a part; the limits of the
    controls; the moving preview's pictures; the figures beside it; `Cancel`; a refusal
    with its message and the screen as before; `On`, `Off` and the slider answered while
    a conversion runs; a canvas of `null` and a reply without the members.
  - Prove it fails first: with the rows of the preview temporarily drawn top row first,
    the test with a GIF whose upper half is one colour and whose lower half another
    fails. Undo it.
  - Requirements: 11.7, 14.1, 14.13, 15.2, 15.4, 15.5, 16.1, 16.2, 16.3, 16.4, 16.5

- [ ] 9. Uploading
  - `app/www/bytes.js`, `names.js` and `upload.js`, and `screens/add.js` from
    `converted` to `installed`, as the design's "Uploading" gives them: the id and the
    name, the steps, what each reply means, `Clear it`, `Cancel`, the percentage and the
    speed. The texts of the codes an upload can give. The remove buttons out of use
    while an upload runs.
  - `tests/app/support.py`: the hop's faults. `tests/app/test_upload.py` and the rest of
    `tests/app/test_add.py`, as the design lists them. `bytes.js` against Python's
    `base64` and `zlib.crc32` for pieces of 1, 2, 3 and 1,500 bytes, and `cbf43926`.
  - Prove it fails first: with the rule for `bad-offset` temporarily taken out, so that
    it ends an upload at once, the test with the reply to one piece dropped fails: the
    screen shows the message of `bad-offset`. Undo it.
  - Requirements: 13.6, 17.1, 17.2, 17.3, 17.4, 17.5, 17.6, 17.7, 17.8, 17.9, 17.10,
    17.11, 17.12, 17.13, 18.1, 18.2, 18.3, 18.4, 18.5, 18.6, 18.7, 18.8, 18.9

- [ ] 10. Every message, the look, and back
  - `messages.js` with the whole table of the design's "Messages"; the message's place on
    every screen, with its way to dismiss it. `style.css` as the design's "The look"
    gives it. The entries of the page's history. The text of `old.html`.
  - `tests/app/test_scope.py`: a text for every error code that the table of
    `docs/commands.md` has, read from that page, and for every reason of
    `converter/lib/errors.js` the app can meet. `tests/app/test_look.py` as the design
    lists it.
  - Prove it fails first: with the text of `storage-error` temporarily taken out of
    `messages.js`, the test of the codes fails naming it. Undo it.
  - Requirements: 6.2, 19.1, 19.2, 19.3, 19.4, 19.6, 19.7, 19.8, 20.1, 20.2, 20.3, 20.4,
    20.5, 20.6, 20.7, 20.8, 21.8

- [ ] 11. The sender, the app's own Android files, and the APK
  - `app/android/app/src/main/java/app/odrig/operators/TargetPlugin.java` and the changes
    to `MainActivity.java`, `AndroidManifest.xml` and
    `res/xml/network_security_config.xml`, as the design's "The Capacitor project" and
    "The sender" give them.
  - `python3 app/app.py build`. Record in the commit message the size of the APK and
    that a build left `git status --short` empty.
  - `tests/apk/test_apk.py`, complete, as the design gives it; run
    `python3 -m unittest discover -s tests/apk -t .`; it passes.
  - `tests/app/test_scope.py`: the tracked manifest, the network security configuration
    and `capacitor.config.json`, as the design lists them; no command word in the Java
    sources.
  - Prove it fails first: `tests/apk`, with the test of the permissions, against the APK
    as task 4 left it fails: `CHANGE_NETWORK_STATE` is not declared.
  - Say in the commit message that the sender was compiled and not run: no agent has a
    phone.
  - Requirements: 3.6, 3.7, 3.8, 5.7, 6.1, 6.3, 6.4, 6.5, 6.8, 6.9, 7.1, 7.2, 7.3, 7.4,
    7.5, 7.6, 7.7, 22.1, 22.3

- [ ] 12. The documents and the last run
  - Rewrite `docs/android-app.md` as Requirement 23 and the design's table "Documents"
    give it, with "The check on a phone" as the design prints it, the sizes and times
    task 4 and task 11 measured, what tasks 4 and 5 found for the assumptions, and "What
    is verified": the versions of macOS, Node.js, npm, Python, Chrome, the JDK, the SDK's
    packages, Gradle and Capacitor that were used, and what was run on no phone.
  - `docs/wifi.md`, `docs/decisions.md` and `README.md` as that table gives them.
  - `tests/app/test_docs.py` as the design lists it.
  - Read every acceptance criterion of Requirements 1 to 23 once more and name, for each
    one a program can check, the test that checks it; add a test where one is missing.
  - Run every suite of the rules, `python3 app/app.py build`, and
    `python3 -m unittest discover -s tests/apk -t .`. All pass.
  - Prove it fails first: `tests/app/test_docs.py` against `docs/android-app.md` as it is
    before this task fails naming the first section that is missing.
  - The state in `state.json` stays `in_progress`: task 13 is the owner's.
  - Requirements: 4.10, 5.6, 21.1, 21.4, 21.11, 21.12, 22.4, 23.1, 23.2, 23.3, 23.4, 23.5,
    23.6, 23.7, 23.8

- [ ] 13. The check on a phone
  - This task needs the owner: a phone, the Mac, and the board with the firmware of task
    2. Without the owner, leave the task open, say so in the hand-over, and write under
    this task what the suites established.
  - Go through "The check on a phone" of `docs/android-app.md`, steps 1 to 15: the APK
    installed; every action against the emulator started with `--lan`; then every action
    against the board on `odrig`, with mobile data on, at a brightness of 40 or less;
    a web page loaded in the phone's browser while the app shows the board's status;
    the same with mobile data off.
  - Write into `docs/android-app.md`, "What is verified": the phone, its Android version
    and its web view's version; what the phone said about `odrig` and what was answered;
    the speed of an upload to the board; the time each conversion took; and for each of
    the assumptions P1 to P8 of the design what was found.
  - Fix what fails, each fix with a test where a program can check it, and put the result
    of every step in the commit message, without the password.
  - Set `"state": "completed"` and `completedAt` in
    `project-seeds/09-p1-operators-app-for-android/state.json`.
  - Requirements: 24.1, 24.2, 24.3, 24.4, 24.5, 24.6
