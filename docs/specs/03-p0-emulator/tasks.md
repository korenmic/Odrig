# Tasks: Emulator (seed 03)

Seeds 01 and 02 are implemented before these tasks start: they use the package `odrig`,
the example show, the core in `core/`, its `Makefile` and the reference player of
`tests/core/support.py`. Where the real code differs from what this spec's design relies
on, follow the code and record the difference in `docs/drifts.md`.

Rules for every task:

- One task is one commit on `master`. The same commit ticks the task's checkbox in this file.
- Stage named paths only (`git add <path> ...`), never `git add -A`, `git add .` or
  `git commit -a`. After committing, read `git show --stat` and confirm it lists exactly the
  files of the task.
- The tests of a task are in the task's commit. Before committing, run
  `python3 -m unittest discover -s tests/emulator -t .` from the repository root; it passes.
- Where a task says "Prove it fails first", run the test against the state described, watch
  it fail in the way described, and put the observed failure in the commit message.
- Code and tests state what they do now. They carry no comment about seeds, tasks, dates or
  earlier versions.
- No command, script or document lists test files; the suite is selected by discovery.
- `emulator/` and `odrigctl/` import only the Python standard library. No file of
  `core/src` or `core/include` is changed.
- `animations/`, `tools/`, `firmware/`, `esp32-backup/` and `scratch/` hold untracked files
  that are not part of this work. Do not move, edit, delete or stage them.
- Answers to questions that come up are recorded in `docs/drifts.md`, not asked.

- [ ] 1. Shared library, binding to the core, and the test command
  - Add the target `shared` to `core/Makefile`: `core/build/libodrig_core.dylib` from
    `src/*.cpp` with the flags of the static library, linked with `-dynamiclib`.
  - Create `emulator/__init__.py`, `emulator/failure.py` (`Failure` and the reason names of
    Requirement 12), `emulator/binding.py` and `emulator/host.py` as the design describes.
  - Create `tests/emulator/__init__.py`, which runs `make -C core shared` once and fails
    with make's output when that fails, and `tests/emulator/support.py` with the helper
    that packs the example show into a temporary folder.
  - `tests/emulator/test_binding.py`: the library loads; the names `binding.py` declares
    are exactly the functions declared in `core/include/odrig_core.h`, read from that file;
    on the example show the legs are leg 1 on pin 1 and leg 2 on pin 2 with 180 LEDs each,
    `error` is `None`, `poll` gives a refresh and `frame` has 1,080 bytes; `command` and
    `feed` answer `status`; on an empty folder `error` is `mapping-missing` and there are
    no legs; a host name with a path separator is refused.
  - `tests/emulator/test_scope.py`: every module of `emulator/` imports only modules of the
    standard library and of its own package, so none imports `odrig`; only `binding.py`
    imports `ctypes`.
  - Start `docs/emulator.md` with the command that builds the shared library and the test
    command and what each needs.
  - Set `"state": "in_progress"` in `project-seeds/03-p0-emulator/state.json`.
  - Prove it fails first, twice. With a temporary `tests/emulator/test_probe.py` holding
    one failing test, the test command fails naming `test_probe`. With the `shared` target
    temporarily renamed in `core/Makefile`, the test command stops with make's error before
    any test runs. Undo both before committing.
  - Requirements: 2.1, 2.2, 2.3, 2.5, 16.1, 16.2, 16.3

- [ ] 2. Record mode on a virtual clock
  - Create `emulator/recfile.py`, `emulator/record.py`, `emulator/app.py` and
    `emulator/__main__.py` with the record options, the checks of the folder, the length
    and the script, and the error line and exit statuses of the design.
  - Add to `support.py` the wrapper around seed 02's reference player that gives every
    leg's LED data and every reply for a list of tick times and timed commands.
  - `tests/emulator/test_record.py`: 60 seconds of the example show equal the reference at
    each of the 3,000 ticks, and the picture changes animation at 15, 30 and 45 seconds; a
    script with every command of `docs/commands.md`, every error code that a line of 64
    characters or fewer can give, and a time that is not a multiple of 20 gives the
    reference's replies on standard output and its LED data in the file; with the
    `first_led` of leg 2 flipped in the packed folder's `mapping.json`, leg 1 equals the
    reference of the unchanged mapping at every tick and every row of leg 2 is the
    reference row reversed, with at least one tick at which the two differ; an invalid
    mapping gives a header with no legs and ticks without a refresh; two runs give
    identical bytes; 600 seconds of a one-frame show are recorded in under 60 seconds; the
    header fields and the file size for a known length; `--seconds 0`, a script line
    without a time, a time that goes backwards, a time at the length of the recording and a
    script that does not exist each give their reason, status 1 and no file; a folder that
    does not exist is `not-a-folder`; a wrong `--core` is `core-not-built`; a usage error
    is status 2; no `.part` file is left in any case.
  - Prove it fails first: with a temporary change that sends a script command after the
    tick of its time instead of before it, `test_record.py` fails at the tick of the first
    command. Undo it.
  - Add the record mode, the script format and the record file format to
    `docs/emulator.md`.
  - Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 11.7, 11.8, 12.1, 12.2, 12.3

- [ ] 3. Real-time engine, start and stop, and commands over HTTP
  - Create `emulator/engine.py` (`Engine`, `RealTime`), `emulator/hub.py` with the log
    entries and the latest status, and `emulator/httpd.py` with `POST /odrig`, status 405
    for other methods, 411 and 404.
  - Extend `app.py` with the real-time start order without the port: the `page:` line,
    `--port`, and the stop on `SIGINT` and `SIGTERM`.
  - Add to `support.py` the helper that starts the emulator as a child process on port 0,
    reads what it prints and ends it with `SIGTERM`.
  - `tests/emulator/test_http.py`: every case the design lists for it except the ones
    that need the port.
  - `tests/emulator/test_start.py`: the `page:` line names 127.0.0.1 and the port in use;
    `SIGTERM` and `SIGINT` give status 0; `address-in-use` when the test holds the port; a
    folder without a show starts, `status` over HTTP reports `mapping-missing`, and `play 1`
    gives `show-invalid`; a show with a missing animation reports `file-missing` with the
    file's name.
  - `tests/emulator/test_realtime.py`: with the example show, `status` reports 49 or more
    for five full seconds in a row; with the emulator's process stopped for 300 ms and
    continued, the refreshes that follow carry current timestamps and `fps` of that second
    is below 50.
  - Requirements: 1.2, 1.4, 1.5, 2.4, 3.1, 3.2, 3.3, 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7,
    10.4, 12.1, 12.2, 15.1

- [ ] 4. The virtual serial port
  - Create `emulator/serialport.py` and complete the start order of `app.py`: the port and
    its link, the `serial:` line, `--serial-link`, and the removal of the link at exit and
    when a later step fails.
  - `tests/emulator/test_serial.py`: every case the design lists for it.
  - Extend `test_start.py`: exactly the two lines are printed, in order; the link is a
    symbolic link to a terminal device and is gone after `SIGTERM`; a link left by an
    earlier run is replaced; a regular file at the link path is `serial-unavailable` and
    stays untouched; `address-in-use` leaves no link behind; without `--serial-link` the
    path is `build/emulator/serial` under the repository root whatever the working folder.
  - Extend `test_http.py`: `brightness 7` over HTTP is reported by `status` through the
    port, and `off` through the port by `status` over HTTP.
  - Prove it fails first: with the call that makes the port raw temporarily removed,
    `test_serial.py` fails because the port returns the sent line before the reply. Put it
    back.
  - Add the port to `docs/emulator.md`.
  - Requirements: 1.1, 1.3, 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 7.8, 10.4, 12.1, 12.2

- [ ] 5. The event stream to the page
  - Add `GET /events` and `GET /show/mapping.json` to `httpd.py`, the connections with
    their queue and their slot for the newest refresh to `hub.py`, and to the engine the
    status request after every command and once a second.
  - `tests/emulator/test_events.py`: every case the design lists for it.
  - Prove it fails first: with the emulator's own status requests temporarily passed to the
    log, the test that expects one `log` event for each command fails by counting more.
    Undo it.
  - Requirements: 4.5, 5.1, 5.2, 8.1, 8.2, 8.3, 8.5, 8.6

- [ ] 6. The command tool
  - Create `odrigctl/__init__.py`, `__main__.py`, `cli.py` and `client.py` as the design
    describes.
  - `tests/emulator/test_tool.py`: every case the design lists for it. The session of
    Requirement 13 criterion 9 holds every command, `play` of an id that does not exist,
    `play abc`, `brightness 256`, and `play` followed by 70 digits; it is run once with
    `--port` and once with `--http` against fresh emulators, and both lists of replies
    equal the reference player's, `fps` aside; the events of the page hold one `log` entry
    for each command with its transport.
  - Extend `test_scope.py` to the modules of `odrigctl/`, and add: `git ls-files tools`
    lists none of `wled.py`, `wled_send.py` and `wled_deploy.py`.
  - Prove it fails first: with the order of the two modem-line requests temporarily
    swapped in `client.py`, the test that sees the requests through a stand-in for
    `fcntl.ioctl` fails naming DTR before RTS. Undo it.
  - Add the command tool to `docs/emulator.md`, with one example for each command and each
    transport.
  - Requirements: 13.1, 13.2, 13.3, 13.4, 13.5, 13.6, 13.7, 13.8, 13.9, 13.10

- [ ] 7. The page: LEDs view, status and command log
  - Create `emulator/web/index.html`, `style.css`, `layout.js` (`read`, `position`,
    `find`, `rows`, `path`, `colour`, `shown`, and `fit` without the board), `view.js` (the
    canvas of LEDs, the brackets, the `y=` labels and the end numbers) and `app.js` (the
    event stream, the header, the reason band, the log, the readout, the count of refreshes
    drawn). Serve the files of `emulator/web/` from `httpd.py`.
  - Create `tests/emulator/js/dump_layout.js` and `tests/emulator/test_layout.py`: the
    cases the design lists for `position`, `find`, `rows`, `path`, `colour`, `shown` and
    `fit` of the LEDs view.
  - `tests/emulator/test_page_files.py`: every case the design lists for it.
  - Prove it fails first: with `position` temporarily starting every row on the
    `first_led` side, `test_layout.py` fails naming LED 61 of leg 1. Undo it.
  - Open the page on the example show in one browser and look at it once: the words are
    upright and the log and the status follow a command. The full check list is task 11.
  - Add the page, the LEDs view, the status and the log to `docs/emulator.md`.
  - Requirements: 4.1, 4.2, 4.3, 4.4, 4.6, 4.7, 5.3, 5.4, 5.5, 8.1, 8.4, 8.7, 10.1, 10.2,
    10.3, 15.2, 15.3

- [ ] 8. The page: mapping view
  - Create `emulator/web/board.js`. Add `side`, `place`, `tracks` and `fit` with the board
    to `layout.js`, and the board, the pads, the lines, the paths, the outlines, the view
    switch and the pointing to `view.js` and `app.js`.
  - `tests/emulator/test_board.py`: the two lists of `board.js` equal the pin labels of the
    board drawing in `docs/mapping.md`, read from that file, in order.
  - Extend `test_layout.py`, loading `board.js` before `layout.js` in the shell: `side` for mappings that start on the right, on the left and
    half each; `place` for pins 1 to 10 and for a pin the board does not have; `tracks`
    gives every leg its own track, ordered by the first row; `fit` for the ten-leg mapping
    at 1280 x 800 gives a cell of 12 pixels with the canvas, the gutters, the channel and
    the board inside the area and apart from each other; `path` for a leg whose rows are
    not neighbours.
  - Prove it fails first: with two entries of `OdrigBoard.left` temporarily swapped,
    `test_board.py` fails naming the first label that differs. Undo it.
  - Open the page on the example show and look at the mapping view once. The full check
    list is task 11.
  - Add the mapping view to `docs/emulator.md`.
  - Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8

- [ ] 9. The ten-leg demo show and the ten-leg measurements
  - Create and track `shows/demo-10/show.json` as in the design.
  - `tests/emulator/test_demo.py`: every case the design lists for it. The sources are
    generated into a temporary folder; nothing generated is tracked.
  - Extend `test_realtime.py`: a show with `mapping/legs-10.json` and the dense clip of 10
    seconds from seed 01's generator, compressed and again uncompressed, reports 49 or more
    in `fps` for five full seconds in a row, and the event stream delivers at least 147
    refreshes of 5,400 bytes in 3 seconds.
  - Add to `docs/emulator.md` the commands that generate, pack and start the demo show.
  - Requirements: 3.4, 14.1, 14.2, 14.3, 14.4

- [ ] 10. Documentation and final check by program
  - Complete `docs/emulator.md` as Requirement 17 lists, with the check list of
    Requirement 16 criterion 5 written as numbered steps that name what to start, what to
    send and what must be seen. Add one sentence to `README.md` pointing to
    `docs/emulator.md`.
  - `tests/emulator/test_docs.py`: every case the design lists for it.
  - Read the acceptance criteria of Requirements 1 to 15 once more and name, for each one a
    program can check, the test that checks it; add a test where one is missing.
  - Run `make -C core clean` and then the test command.
  - Requirements: 16.4, 16.5, 17.1, 17.2

- [ ] 11. The check list by eye, in Safari and in Chrome
  - This task needs a person, or an agent with a tool that drives a real browser. Without
    one, leave the task open and say so in the hand-over.
  - Go through the check list of `docs/emulator.md` in current Safari and in current
    Chrome, with the example show, the dense 60 x 30 show and the demo show: the drawing
    fits a window of 1280 x 800 and follows its size; dark LEDs are visible; HELLO WORLD is
    upright and readable and alternates with the square every 15 seconds; the page's own
    count is 49 or more for the example show and for the dense clip; a command sent with
    `odrigctl` by each transport appears in the log at once and the status follows; the
    mapping view of the demo show has the board, ten legs on pins 1 to 10, the lines, the
    paths, both end numbers of all 30 rows and no label over another; pointing at a label,
    a pin, a line and a row highlights one leg everywhere; a show with a missing animation
    shows its reason.
  - Fix what fails, each fix with a test where a program can check it, and put the result
    of every step for each browser in the commit message.
  - Set `"state": "completed"` and `completedAt` in `project-seeds/03-p0-emulator/state.json`.
  - Requirements: 4.2, 4.6, 4.8, 4.9, 8.1, 8.4, 9.1, 9.5, 9.8, 10.1, 14.5, 15.2
