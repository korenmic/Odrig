# Tasks: Canvas 60 by 60 (seed 05)

Seeds 01 to 04 are implemented before these tasks start, and these tasks change their
code. Where the real code differs from what this spec's design relies on, follow the code
and record the difference in `docs/drifts.md`.

Tasks 1, 2, 8 and 11 need the board on USB. Task 10 needs a tool that drives a browser.
The design's table "Assumed, to be verified by the spike" and its section "The time of one
refresh" name what tasks 1 and 2 settle: each writes what it found into `docs/firmware.md`
under "Verified on the board", and into `docs/drifts.md` when the finding changes the
design.

Rules for every task:

- One task is one commit on `master`. The same commit ticks the task's checkbox in this file.
- Stage named paths only (`git add <path> ...`), never `git add -A`, `git add .` or
  `git commit -a`. After committing, read `git show --stat` and confirm it lists exactly the
  files of the task.
- The tests of a task are in the task's commit. Before committing, run the four suites that
  need no board, from the repository root; all four pass:
  `.venv/bin/python -m unittest discover -s tests/converter -t .`, `make -C core test`,
  `python3 -m unittest discover -s tests/emulator -t .` and `python3 firmware/fw.py test`.
- In tasks 1, 2, 8 and 11 also run `python3 firmware/fw.py test-board`; it passes. It takes
  about half an hour, so it is run once the task's own board tests pass.
- Where a task says "Prove it fails first", run the test against the state described, watch
  it fail in the way described, and put the observed failure in the commit message.
- Code and tests state what they do now. They carry no comment about seeds, tasks, dates or
  earlier versions.
- No command, script or document lists test files; each suite is selected by discovery.
- A test that concerns a row-leg file passes unchanged, except where it names the ten-leg
  file. `mapping/legs-2.json`, `shows/example/show.json`, `animations/hello.json` and
  `animations/dvd.json` keep their bytes.
- In `core/src` and `core/include` only `core/src/mapping.cpp` changes, and comments in
  `core/src/core_state.h` and `core/include/odrig_core.h`. No file of `emulator/*.py` and
  none of `odrigctl/` changes.
- A change to a file of WLED exists only as a patch file in `firmware/patches/`. Nothing is
  installed outside `build/firmware/`. Nothing fetched or built is staged.
- `esp32-backup/` is never written to, moved, deleted or staged. No eFuse is written. The
  whole flash is never erased.
- Every show put on the board has a brightness of 40 or less: one 60-LED strip is wired, on
  pin 1, fed from the board's 3.3 V pin. Nothing is judged by looking at the LEDs.
- A task that touches the board ends with the board running what the task says it leaves,
  and says so in its commit message.
- `animations/`, `tools/`, `firmware/wled-16.0.1/`, `esp32-backup/`, `scratch/` and the
  stock image at the repository root hold untracked files that are not part of this work.
  Do not move, edit, delete or stage them.
- Answers to questions that come up are recorded in `docs/drifts.md`, not asked.

- [x] 1. Spike: twenty outputs of 180 LEDs on the board
  - Set `"state": "in_progress"` in `project-seeds/05-p0-canvas-60-by-60/state.json`.
  - Create `firmware/patches/010-sixteen-parallel-outputs.patch` as the design's table "The
    patch" lists it, written against WLED's files at the pinned commit, with its first lines
    saying what it changes and why the usermod cannot. Rewrite the last paragraph of
    `firmware/patches/README.md`.
  - Add `wire_us` and `pulses` to the probe build, in `firmware/usermod/odrig_probe.h`,
    `.cpp` and the calls of `odrig_usermod.cpp`, as the design's "What a program can prove
    without LEDs" describes. Give `summary()` of `odrig_leds.cpp` room for twenty legs.
  - `tests/firmware/test_patches.py`: every tracked patch file applies to WLED's files at
    the pinned commit; the README names every patch file. Extend
    `tests/firmware/test_usermod_files.py`: the pulse counter and the wire time are named
    only in `odrig_probe` and inside `#ifdef ODRIG_PROBE`.
  - `tests/board/support.py`: the pins of the target, `1` to `18`, `21` and `47`; a dense
    clip of any canvas size. `tests/board/test_twenty.py` as the design's "The spike",
    step 2, lists it, on row-leg mappings of twenty legs made by `legs_mapping`.
  - On the board: `build --probe` and `build`; flash the probe build; run
    `tests/board/test_twenty.py`, then the whole board suite.
  - Write into `docs/firmware.md`, "Verified on the board": what was found for A1 to A5,
    with `pulses`, `wire_us`, `sent`, `heap`, and for the two dense 60 x 60 clips the
    refreshes sent in a second and the mean and longest request and send.
  - If twenty outputs do not work: follow the design's "The fallback", keep the largest
    number that works, name it once in `tests/board/support.py`, make `test_twenty.py`
    expect it, and add the entry to `docs/drifts.md` and the finding to the open questions
    of `docs/decisions.md`. If a pin fails: Requirement 12 criterion 10.
  - Prove it fails first: with the patch file moved out of `firmware/patches/` and the probe
    build built and flashed again, `test_twenty.py` fails with outputs 13 to 20 reported as
    not working. Put the patch back, build and flash again.
  - The board is left with the firmware of this task and the dim example show.
  - Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6, 12.7, 12.8, 12.9, 12.10, 12.11, 17.1,
    17.3

- [ ] 2. Fifty refreshes a second with a dense 60 x 60 clip on twenty outputs
  - Add to `tests/board/test_fps.py`: on the twenty row legs of task 1, with the dense
    60 x 60 clip of 10 seconds, compressed and then uncompressed, the firmware's `status`
    reports 49 or more in every one of ten full seconds in a row.
  - Run it with the firmware of task 1. If it passes, the loop stays as it is: say so in
    `docs/firmware.md` and in the commit message, with the figures.
  - If it fails: move the request for a refresh to a task of its own, as step 2 of the
    design's "The time of one refresh" describes, in `firmware/usermod/odrig_usermod.cpp`,
    with the port feeding one line under one hold of the lock in `odrig_serial.cpp` and the
    probe timing the request in the task. Extend `tests/firmware/test_usermod_files.py`:
    the usermod starts one task, in `odrig_usermod.cpp` only. Record the three assumptions
    of that section as found.
  - Measure with the probe build, over 25 seconds each: the bench show, and the two dense
    clips on twenty legs. Write the figures into `docs/firmware.md`, and the change of the
    loop, if there is one, into `docs/drifts.md`.
  - If `fps` is still below 49: step 3 of that section. Requirement 13 criterion 5 then
    holds for the rest of the seed.
  - Prove it fails first: the new test against the firmware of task 1, when that is what
    made the change necessary. When the firmware of task 1 passes it, show instead that the
    test sees a lower rate: with a temporary wait of 10 ms in the usermod's loop it fails
    with the rates it read. Undo it.
  - The board is left with the firmware of this task and the dim example show.
  - Requirements: 13.1, 13.2, 13.3, 13.5, 12.11
  - Left open. Done: the two tests of the rate, which fail with the firmware of task 1
    (22 to 24 and 32 to 34 refreshes a second); the request in a task of its own with the
    line-at-a-time port and the probe's timing in the task; the tests of the usermod's
    files; the figures as far as measured, in `docs/firmware.md`, `docs/decisions.md` and
    `docs/drifts.md`. Found: 27 to 34 and 44 or 45 with the probe build, below 49, so
    Requirement 13 criterion 5 holds. Not done, because the board stopped answering on USB
    after a trial build (see `docs/drifts.md`, "Seed 05: A trial build at another
    optimisation level, and a board that no longer answers"): the rate read from the
    firmware build, the 25-second measurements, the whole board suite with this firmware,
    and leaving the board with this firmware and the dim example show.

- [x] 3. The mapping format with column legs: the document and the converter's reader
  - `docs/mapping.md`: rewrite "Mapping file", "Rules" and "Where each LED is" for both
    kinds, as the design's "The mapping file format" has them. The drawings and tables stay
    as they are until task 7. `docs/reasons.md`, "Mapping files": the two reasons hold for
    both kinds. `docs/converter.md`: the canvas of `import` for both kinds.
  - `odrig/mapping.py` as the design's "The reader" gives it: the kind, `Leg.strips`,
    `strip_length`, `led_count`, `position`, the order of the checks and the details.
    Follow every user of `Leg.rows` in the tracked files.
  - `tests/converter/test_mapping.py`: every rule broken once for a column-leg file; both
    `width` and `height`, and neither; `rows` in a column-leg file and `columns` in a
    row-leg file; `"left"` in a column-leg file and `"bottom"` in a row-leg file; the
    detail of each of these; the edges; W and H of a column-leg file; `position` of every
    LED of a row-leg and a column-leg file against the rule written out in the test; every
    row-leg file of today's tests accepted as before.
  - `tests/converter/test_show_pack.py` and `test_generators.py`: with a made-up column-leg
    mapping, the generators write for its canvas, and `pack` copies the mapping file byte
    for byte and refuses a source of another canvas size with `size-mismatch`.
  - Prove it fails first: the new tests against the reader as it is fail with a valid
    column-leg file refused for its member `height`.
  - Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 2.1, 2.2, 2.3, 2.4, 4.1, 4.2, 4.3,
    4.4, 4.5

- [x] 4. The core reads column legs
  - `core/src/mapping.cpp` as the design's "The core" describes: the two kinds in the
    first reading, whatever the order of the members; the strip check; the table of a
    column leg in the second reading. Reword the comments on rows in
    `core/src/core_state.h` and `core/include/odrig_core.h`.
  - `tests/core/support.py`: the four made-up column-leg mappings of the design, given by
    a function of their own for now; the column rule in `led_pixels` and in
    `ReferencePlayer`, written out there.
  - `tests/core/test_mapping.py`: the broken and the edge files of task 3, each judged by
    the core as by the converter; the leg list of every column-leg mapping.
    `tests/core/test_json.py`: a column-leg file with `legs` before `height` and with
    `first_led` before `columns`. `tests/core/test_playback.py`: on every column-leg
    mapping each LED shows the pixel the rule gives it; a clip plays against the reference.
  - `docs/core.md`: `led_count` is the strip length times the number of strips.
  - Prove it fails first: the new tests against the core as it is fail with
    `mapping-malformed` for a valid column-leg file.
  - Requirements: 5.1, 5.2, 5.3, 5.5, 5.7, 15.2, 15.3

- [x] 5. The page reads both kinds, the LEDs view for upright legs, and the target file
  - Add `mapping/legs-20.json` with the bytes the design prints.
  - `emulator/web/layout.js`: `read`, `position` and `find` for both kinds; the strips,
    the path and the runs of a leg; `side`; twenty colours; the LEDs view for column legs
    as the design's "The LEDs view for column legs" describes. `emulator/web/view.js`: the
    leg band, the marks of the rows and the upright numbers. Row-leg files are drawn by the
    code they are drawn by today.
  - `tests/core/support.py`: the column-leg mappings join `mapping_texts()`, so that every
    suite runs on them and on the target file. `tests/core/test_mapping.py` and
    `tests/converter/test_mapping.py`: the target file has twenty legs of 180 LEDs on pins
    1 to 18, 21 and 47, a canvas of 60 x 60, and the corners of Requirement 3 criterion 2.
  - `tests/emulator/js/dump_layout.js` and `tests/emulator/test_layout.py`: position and
    `find` of every LED of every mapping against the reference; the strips, paths and runs
    of column legs; the parts of the LEDs view for the target file and the made-up column
    files inside the drawing and apart from each other; cells of 7 or more with the whole
    drawing inside areas of 1280 x 546 and 500 x 546; twenty different colours, the first
    twelve unchanged. `tests/emulator/test_record.py`: Requirement 7 criterion 4.
  - Prove it fails first: the position test for the target file against `layout.js` as it
    is fails, and so does the test of the area of 1280 x 546 against a fit that takes the
    canvas for 60 rows of a row-leg file. Put the observed failures in the commit message.
  - Requirements: 3.1, 3.2, 3.4, 7.1, 7.2, 7.3, 7.4, 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7,
    8.8, 10.1, 10.2, 10.3, 15.2

- [x] 6. The mapping view for upright legs and twenty lines
  - `emulator/web/layout.js`: the wide and the narrow arrangement for column legs, the
    level and the upright channel, the track rules, the short and the long way round the
    board, the line to a first LED at the far edge, the mirrored arrangements for a feed
    edge at the top, and the chain with its turns outside the top and the bottom edge, as
    the design's "The mapping view for column legs" describes. `emulator/web/view.js` and
    `emulator/web/style.css`: the outline, the path, the arrows, the number bands, the tag
    and the lines for column legs.
  - `tests/emulator/test_layout.py`, for the target file and the made-up column files, in
    areas of 1280 x 546, 1920 x 1000, 1100 x 600, 756 x 546 and 600 x 546: the wide
    arrangement in the first three and the narrow one in the last two; cells of 9 or more
    at 1280 and at 756 wide, and no drawing wider than its area there; every part inside
    the drawing, the board apart from the canvas and from both channels; every line from
    the pad of its pin to the first LED of its chain, in level and upright pieces; no two
    lines on each other; no line through the board or over an LED; no two lines crossing
    twice; 88 crossings for the target file in both arrangements; the chain of a
    leg through the corners of its path with its turns outside the canvas; a leg that
    starts at the top reached through the gap beside its first column; a file whose legs
    all start at the top drawn mirrored. Every test of today for the row-leg files passes
    as it is.
  - Prove it fails first: with every leg of the far row of pads taking the short way, the
    test of the crossings fails with more than 88. Undo it.
  - Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8, 9.9, 9.10, 9.11, 10.1, 10.2

- [x] 7. The tool that writes docs/mapping.md
  - Create `odrig/mapdoc.py` as the design's "The tool that writes docs/mapping.md"
    describes: the markers, the board, the drawing and the table of a file of either kind,
    `--check`, `--page` and `--mapping-dir`.
  - `docs/mapping.md`: put the markers in; "Legs and pins" and the target section for
    twenty upright legs, with the sentence on columns drawn lying down and the command
    that writes the page; then run `python -m odrig.mapdoc`. The part for `legs-2.json`
    comes out with the bytes it has.
  - `tests/converter/test_mapping_page.py` as the design lists it.
    `tests/emulator/test_layout.py`: the two tests that read the drawings and the tables of
    the page read the bench section and the twenty-leg section.
    `tests/emulator/test_board.py`: the legs of the board drawing are on the pins of the
    target file.
  - Prove it fails first, twice: before the page is written again, `--check` fails naming
    `board legs-20`; and on a copy, with the pin of leg 19 changed in `legs-20.json`, the
    test fails naming a part of that file.
  - Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 11.7, 11.8, 11.9, 16.1

- [ ] 8. The board with the target file
  - `tests/board/support.py`: the target file in place of the ten-leg file; the dense clip
    at 60 x 60; `legs_mapping` can make column legs.
  - `tests/board/test_probe.py` with the tests of `test_twenty.py` moved into it, and that
    file removed: with the target file, twenty working outputs of 180 LEDs on pins 1 to
    18, 21 and 47, four `rmt` and sixteen `parallel`, each holding what the limiter's
    lowest level makes of its leg's bytes, 4,320 pulses on every pin, `wire_us` between
    4,500 and 7,500; with a column-leg file of twenty legs of three columns of 6, every
    output holding exactly its leg's bytes as the emulator records them. With fewer than
    twenty outputs after task 1: that number working, and the rest reported as not working.
  - `tests/board/test_fps.py`: the target file with the dense 60 x 60 clip, compressed and
    uncompressed, in place of the ten-leg tests and of the test of task 2.
  - `tests/board/test_measure.py`: the bench show; the demo show's two animations made for
    the target file, dimmed; the dense 60 x 60 clip, compressed and uncompressed; and
    storage filled with 9 MB of dense 60 x 60 clips. Each row has the figures of
    Requirement 13 criterion 4.
  - On the board: the whole board suite. Write the measurements into `docs/firmware.md`,
    "Measurements on the board", with the number of outputs the firmware drives.
  - Prove it fails first: with the `first_led` of one leg changed to `"top"` in the copy of
    the mapping the emulator records, and not in the one installed, the test of the exact
    bytes fails for that leg's output and for no other. Undo it.
  - The board is left with the firmware and the dim example show.
  - Requirements: 12.1, 12.3, 12.4, 12.5, 12.6, 12.7, 13.1, 13.2, 13.4, 15.5, 17.1, 17.2
  - Left open. Done, without the board: `tests/board/support.py` has the target file, the
    dense clip at 60 x 60, column legs in `legs_mapping` and the dimmed demo show for a
    mapping; `tests/board/test_probe.py` has the two tests of the twenty outputs, on the
    target file and on twenty column legs of three columns of 6, and `test_twenty.py` is
    removed; `tests/board/test_fps.py` and `tests/board/test_measure.py` use the target
    file. What these tests do before they talk to the board was run: the mappings are
    valid, the emulator records twenty legs for each show, and the 9 MB show fits the
    storage image. Not done, because the board does not answer on USB (see
    `docs/drifts.md`, "Seed 05: A trial build at another optimisation level, and a board
    that no longer answers"): none of these tests has run on the board, the measurements
    are not taken and `docs/firmware.md`, "Measurements on the board", still has the
    figures of seed 04, and the test of the exact bytes was not shown to fail.

- [ ] 9. The target takes the place of the ten-leg file
  - Add `shows/demo-20/show.json`. Remove `shows/demo-10/` and `mapping/legs-10.json` with
    `git rm`.
  - `core/Makefile`: the benchmark clip from `mapping/legs-20.json`.
  - `tests/converter/`: `test_generators.py`, `test_import_timeline.py` and
    `test_show_pack.py` with the target file and 60 x 60. `tests/core/`:
    `test_playback.py` with Hello world, DVD bounce and the dense clip on the target file
    against the reference for one loop; `test_memory.py` with the target file and 100
    items, tables of 67,656 bytes and a total below 131,072; `test_startup.py`,
    `test_cycle.py`, `test_decoder.py`. `tests/emulator/`: `support.py`, `test_demo.py`
    with the demo show, Hello world in the rows 28 to 33 and the square over all twenty
    legs, `test_realtime.py` with the demo show and the dense 60 x 60 clip,
    `test_tool.py`, `test_docs.py`. `tests/firmware/test_storage.py`: the target file as
    the canvas of another size. `tests/board/`: no line names the ten-leg file after task
    8; check it.
  - The documents that give commands or figures the tests read: `docs/emulator.md`, "Two
    shows to run" and the commands of its check list; `docs/core.md`, the benchmark's row
    of the commands table, "Memory" with the measured figures and "Benchmark" with the
    figures of this Mac; `docs/converter.md`, the dense clip; `docs/firmware.md`, where it
    names the ten-leg file.
  - `tests/converter/test_docs.py`: no tracked file names `legs-10` or `demo-10`, apart
    from the seeds, the specs, `docs/drifts.md` and the change log of `docs/decisions.md`.
  - Prove it fails first: that test, before the two are removed, fails listing the files
    that name them.
  - Requirements: 3.3, 3.4, 5.4, 5.6, 6.1, 6.2, 6.3, 6.4, 6.5, 14.1, 14.2, 14.3, 14.4,
    14.5, 15.1, 15.3, 15.4

- [ ] 10. The documents, the measured sizes, and the check list by eye
  - `docs/format.md`: the row of the dense clip at 60 x 60, measured with the converter,
    and the statement of what fits, computed as the design's "Measured sizes and what
    fits" says. `docs/decisions.md`: the section on the canvas, what fits, the emulator's
    snake, the open questions, and a line in the change log. `docs/mapping.md`: "What is
    confirmed". `docs/emulator.md`: the two views for both kinds of leg, with the
    arrangements, the tracks and the count of crossings. `docs/firmware.md`: the outputs,
    the patch under "What the firmware changes in WLED", the limiter with 3,600 LEDs, the
    two new members of the probe's report, and the two new owner's checks. `README.md`:
    the line on the mapping.
  - `tests/converter/test_docs.py`: the row of `docs/format.md` holds the sizes the
    converter gives; no document outside the change log, `docs/drifts.md`, the seeds and
    the specs says that the target is 60 x 30 or has ten legs.
    `tests/emulator/test_docs.py`: the check list has a numbered step for every criterion
    Requirement 18 names, beside those of seed 03. `tests/firmware/test_docs.py`: the
    owner's checks.
  - The check list by eye of `docs/emulator.md`: rewrite its steps for the demo show of
    twenty legs and the dense 60 x 60 clip, and add the steps of Requirement 18. Go through
    it in current Chrome with a tool that drives the browser, in windows of 1280 x 800 and
    of 756 x 900, take a screenshot at every step into `build/`, and look at each one. Fix
    what is not as described, each fix with a test where a program can check it. Write
    under "What has been checked" what was checked, how, and what is left.
  - Without a tool that drives a browser: leave this task open and say so in the hand-over.
  - Requirements: 8.9, 9.8, 9.9, 16.1, 16.2, 16.3, 16.4, 16.5, 16.6, 16.7, 18.1, 18.2, 18.3

- [ ] 11. The last check, and the board left as it was found
  - Read every acceptance criterion of Requirements 1 to 18 once more and name, for each
    one a program can check, the test that checks it; add a test where one is missing.
  - Run the four suites that need no board, `make -C core bench`, and
    `python3 firmware/fw.py test-board`. The last step of the board suite leaves the
    firmware and the bench show at brightness 32, playing from its start: confirm it with
    `python -m odrigctl --port PORT status`, which reports `"playing":3`, `"brightness":32`
    and `"error":null`.
  - Set `"state": "completed"` and `completedAt` in
    `project-seeds/05-p0-canvas-60-by-60/state.json`. If Requirement 13 criterion 5 holds,
    or task 10 is open, leave the state `in_progress`, leave this task open, and say in
    the hand-over what is left.
  - Requirements: 13.5, 15.4, 15.5, 17.1, 17.2, 17.3, 18.4
