# Tasks: Shared runtime core (seed 02)

Seed 01 is implemented before these tasks start: they use its package `odrig`, its test
vectors and `docs/reasons.md`.

Rules for every task:

- One task is one commit on `master`. The same commit ticks the task's checkbox in this file.
- Stage named paths only (`git add <path> ...`), never `git add -A`, `git add .` or
  `git commit -a`. After committing, read `git show --stat` and confirm it lists exactly the
  files of the task.
- The tests of a task are in the task's commit. Before committing, run `make -C core test`;
  it passes, with no compiler warning and no sanitizer report.
- Where a task says "Prove it fails first", run the test against the state described, watch
  it fail in the way described, and put the observed failure in the commit message.
- Code and tests state what they do now. They carry no comment about seeds, tasks, dates or
  earlier versions.
- No command, script or document lists test files or source files; the suite is selected by
  discovery and the sources by `core/src/*.cpp`.
- The core's sources follow the rules of the design's "Language level and toolchain".
- `animations/`, `tools/`, `firmware/`, `esp32-backup/` and `scratch/` hold untracked files
  that are not part of this work. Do not move, edit, delete or stage them.
- Answers to questions that come up are recorded in `docs/drifts.md`, not asked.

- [ ] 1. Build, test command and reason names
  - Create `core/Makefile` for GNU Make 3.81 with the targets `all`, `test` and `clean`, the
    compiler flags of the design, sources found by `$(wildcard src/*.cpp)`, a second
    compilation of the sources with the sanitizers for the test host, and a check that
    `PYTHON` is 3.10 or later. Add `/core/build/` to `.gitignore`.
  - Create `core/src/reasons.h` and `reasons.cpp`: `Reason` and `reason_name` for every name
    of `docs/reasons.md` the core can report, plus `read-error` and `out-of-memory`.
  - Create `tests/core/__init__.py`, `tests/core/host/host.cpp` with the invocation
    `reasons`, `tests/core/support.py` (finds and runs the test host),
    `tests/core/allowed_symbols.txt` and `tests/core/test_build.py`: every name the library
    refers to and does not define is in the allowed list; the library has no symbol in a
    writable data section; no core source includes a header other than `stdint.h`,
    `stddef.h`, `string.h` and the core's own; no core source uses `float` or `double`;
    every name printed by `odrig_host reasons` is in `docs/reasons.md`.
  - Add `read-error` and `out-of-memory` to `docs/reasons.md`. Start `docs/core.md` with
    the build command and the test command and what each needs.
  - Set `"state": "in_progress"` in `project-seeds/02-p0-shared-runtime-core/state.json`.
  - Prove it fails first, twice. With a temporary `tests/core/test_probe.py` holding one
    failing test, `make -C core test` fails naming `test_probe`. With a temporary call to
    `malloc` in `reasons.cpp`, `test_build.py` fails naming `_malloc` as a name outside the
    allowed list. Remove both before committing.
  - Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 17.1, 17.7, 17.8

- [ ] 2. Host interface, file source and DEFLATE decoder
  - Create `core/include/odrig_core.h` exactly as in the design.
  - Create `core/src/file_source.h`, `.cpp` and `core/src/inflate.h`, `.cpp` as the design
    describes, with the rejection rules listed there.
  - Add to the test host: the host's file functions over a folder and over standard input,
    with the `file misuse` stop, and the invocation `inflate`.
  - Extend `test_build.py`: `odrig_core.h` compiles as C and as C++ with only `stdint.h`
    and `stddef.h`.
  - `tests/core/test_inflate.py`: seeded data of 0 bytes to 200,000 bytes compressed by
    zlib at levels 0, 1 and 9 and with the fixed strategy, data with matches at distance
    32,768 and of length 258, and streams of several blocks: output equal to zlib's; 2,000
    seeded copies with one bit or one byte changed: accepted or rejected as zlib does, with
    equal output when accepted; every prefix of a short stream is `truncated`; block type 3
    is `bad-deflate`.
  - Requirements: 2.1, 2.3, 2.8, 15.1, 15.2, 15.3

- [ ] 3. ODRG decoder, checked against the vectors and the reference decoder
  - Create `core/src/odrg_decoder.h`, `.cpp` as the design describes, and the invocation
    `decode` in the test host.
  - `tests/core/test_vectors.py`: every `.odrg` in `tests/vectors/valid` gives the frames of
    its `.json`, record by record; every file in `tests/vectors/invalid` is rejected with
    the reason before the first dot of its name. The test lists the two folders.
  - `tests/core/test_decoder.py`: files written by `odrig.odrg.encode` from seeded
    animations, with and without a palette, compressed and uncompressed, on canvases from
    1 x 1 to 60 x 30, one with N of 65,534 and one whose body is above 32,768 bytes: frames
    equal to `odrig.odrg.decode`; 2,000 seeded copies with one byte changed: accepted or
    rejected as the reference decoder does, with equal frames when accepted.
  - Requirements: 3.2, 7.5, 13.3, 17.2

- [ ] 4. JSON reader, mapping, startup memory and the allocation guard
  - Create `core/src/json_reader.h`, `.cpp`, `mapping.h`, `.cpp`, `arena.h`, `core_state.h`
    and `core.cpp` with `odrig_core_begin` up to step 3 of the design's startup, and
    `odrig_core_leg_count`, `odrig_core_leg` and `odrig_core_error`.
  - Create `tests/core/host/guard.cpp`. Add to the test host the invocation `session` with
    its start-up output, the input line `error`, the option `--alloc-fails-at` and the
    invocations `guard alloc` and `guard new`.
  - `tests/core/test_mapping.py`: for `mapping/legs-2.json`, `mapping/legs-10.json` and
    made-up mappings (a leg starting on the left, legs of two and of four rows, legs listed
    in another order), the leg list has the leg numbers, pins and LED counts of the file, in
    its order; a missing file gives `mapping-missing` and zero legs; each broken rule gives
    `mapping-malformed`.
  - `tests/core/test_json.py`: a set of at least 40 texts used as `mapping.json`, among them
    a repeated member, a byte-order mark, `60.0`, `6e1`, `-0`, `060`, `true`, an escaped
    member name, text after the closing brace and a very long number: the core accepts
    exactly those that `odrig.mapping.read` accepts.
  - `tests/core/test_memory.py`: `guard alloc` and `guard new` stop with status 70 and print
    `allocation after startup`; with `--alloc-fails-at 1` the host prints `core null`; with
    each later number the reason is `out-of-memory`.
  - Prove it fails first: with a temporary `new char[1]` in `odrig_core_leg_count`, every
    session test stops with status 70 and `allocation after startup`. Remove it.
  - Requirements: 2.2, 2.5, 2.6, 5.6, 6.1, 13.1, 13.4, 15.4, 17.6

- [ ] 5. Show reader and the check of every file at startup
  - Create `core/src/show.h`, `.cpp`, and add steps 4, 5 and 7 of the design's startup to
    `odrig_core_begin`.
  - Add the option `--read-fails` to the test host.
  - `tests/core/test_startup.py`: the example show packed by seed 01 has no reason; one
    case for each text of Requirement 3, read with the `error` line, each with the id or the
    file name in the text; when two defects are present, the earlier one in the order of
    the table is reported; a file named twice is opened for checking once; a file with a
    wrong size and a bad body is `size-mismatch`.
  - Extend `test_json.py` with at least 40 texts used as `show.json`, checked against
    `odrig.show.read`.
  - Requirements: 3.1, 3.3, 3.4, 3.6, 15.4

- [ ] 6. Clock, refreshes and playback of animation items
  - Create `core/src/player.h`, `.cpp` with the clock, the grid, the refresh of the design
    for animation items, the brightness table and the LED data, and `odrig_core_poll`. Add
    step 6 of the design's startup: an animation item named by `start` plays from power-on.
  - Add the input line `poll` to the test host.
  - Add the reference player to `tests/core/support.py` for animation items, with its own
    mapping rule.
  - `tests/core/test_playback.py`: for Hello world and DVD bounce on the two-leg mapping and
    the dense 10-second clip on the ten-leg mapping, each as the `start` item, polled every
    20 ms for one loop and 10 refreshes more: every byte of every leg equals the reference
    player; a one-frame animation in which every pixel has its own colour, on each tracked
    mapping and each made-up mapping of `test_mapping.py`: every LED shows the pixel that
    the rule of Requirement 6, computed in the test, gives it; Hello world again with
    brightness 255, 128, 1 and 0 in `show.json`; polls 1 ms apart give one refresh per grid
    time; polls 50 ms apart give one refresh per poll with the picture of the poll's
    timestamp; a poll after a gap of several loops gives the right picture; a timestamp
    below the latest is treated as the latest; a show without `start` and an invalid show
    give dark refreshes; an invalid mapping gives `idle`; a file of one frame and a file
    whose frames last 1 ms.
  - Requirements: 2.4, 4.1, 4.2, 5.1, 5.2, 5.3, 5.4, 5.5, 5.7, 6.2, 6.3, 6.4, 7.1, 7.2, 7.3,
    7.4, 9.1, 17.3

- [ ] 7. Cycles
  - Add cycles to `player.cpp` and to the reference player.
  - `tests/core/test_cycle.py`: the example show for 65 seconds, with the turn changing at
    exactly 15, 30, 45 and 60 seconds after power-on and each turn starting from the first
    frame; a cycle listing one animation twice starts it again at the turn change; a cycle
    of one entry; an animation of 3.4 seconds in a turn of 5 seconds loops and is cut at the
    turn change; a turn of 1 second and one of 65,535 seconds.
  - Requirements: 8.1, 8.2, 8.3, 8.4

- [ ] 8. Commands, replies and status
  - Create `core/src/commands.h`, `.cpp` with `odrig_core_command`, `odrig_core_feed`, the
    status reply and the refresh rate.
  - Add the input lines `line`, `linehex` and `bytes` to the test host, and commands to the
    reference player.
  - `tests/core/test_commands.py`: every command; every error code, and the first of the
    table when two apply; two spaces, a leading and a trailing space; an empty line;
    capital letters; `play 007`; `play 0`, `play 65536`, `brightness 256`, a number of 30
    digits; a final newline, with and without a carriage return; lines of exactly 64 and 65
    characters; byte input split in the middle of a line; 10,000 bytes without a newline
    followed by a newline and a valid command, giving one `line-too-long` and one
    `{"ok":true}`; each reply ends in a newline and is at most 192 bytes.
  - `tests/core/test_status.py`: the exact bytes of the status reply; `fps` is 0 in the
    first second, 50 with regular polls, the real count with late polls, and 0 after a
    second without polls; `animation` during a cycle and straight after `play`; brightness
    and state after a valid and an invalid startup; a command changes `status` at once and
    the LED data at the next refresh.
  - `tests/core/test_session.py`: one scripted session against the example show, compared
    line by line with the reference player. It contains every command, every error code,
    two turn changes of the cycle, `play` of an item that is already playing, `off` across
    a turn change followed by `on`, and brightness 0, 1, 128 and 255.
  - Extend `test_startup.py`: for each text of Requirement 3, the LEDs stay dark, `status`
    reports the text, `play` gives `show-invalid`, and `on`, `off` and `brightness` reply
    `{"ok":true}`.
  - Requirements: 2.7, 3.5, 4.3, 4.4, 9.2, 9.3, 9.4, 10.1, 10.2, 10.3, 10.4, 10.5, 10.6,
    10.7, 10.8, 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 11.7, 11.8, 12.1, 12.2, 12.3, 17.4,
    17.5

- [ ] 9. Failure while playing, fixed memory and repeatable output
  - Make a failure during playback end the show as Requirement 16 states, and add the
    options `--remove-after`, `--swap-after` and `--dirty-memory` to the test host.
  - `tests/core/test_failure.py`: a read failure in the middle of a file, a file removed
    before the next loop, and a file replaced by one of another size: the next refresh and
    all later ones are dark, `status` reports `read-error`, `file-missing` or
    `size-mismatch` with the file name, `playing` is `null`, and `play` gives
    `show-invalid`; a file replaced by a shorter one of the same size is `file-malformed`
    with `truncated`.
  - Extend `test_memory.py`: the ten-leg mapping with a show of 100 items asks for less
    than 131,072 bytes; a show with a 1-second clip and one with a 60-second clip of the
    same canvas ask for the same number of bytes; no `read` asks for more than 512 bytes;
    one session run twice prints identical output; a session run with the host handing out
    memory filled with the byte `0xA5` prints the same output as with zeroed memory.
  - Requirements: 13.2, 13.3, 14.1, 14.2, 16.1, 16.2

- [ ] 10. Benchmark
  - Create `tests/core/bench/bench.cpp` and the target `bench` in `core/Makefile` as the
    design describes. The target is separate from `test` and has no pass mark.
  - Run it once and put the printed table in the commit message.
  - Add the benchmark command to `docs/core.md`.
  - Requirements: 18.1, 18.2

- [ ] 11. Documentation and final check
  - Complete `docs/core.md`: the three commands and what each needs; every function of the
    host interface; the rules of use; the rules of time, the grid and refreshes; the LED
    data; the memory table with the figures measured in task 9; the invocations of the test
    host.
  - Add to `docs/reasons.md` what follows each name in the texts of Requirement 3, and one
    sentence to `README.md` pointing to `docs/core.md`.
  - `tests/core/test_docs.py`: every function and every member of `odrig_core.h` is named
    in `docs/core.md`.
  - Read every function of `core/src` once more against the rules of the design: no
    recursion, no clock, no file written.
  - Run `make -C core clean` and `make -C core test` from a fresh checkout state.
  - Set `"state": "completed"` and `completedAt` in
    `project-seeds/02-p0-shared-runtime-core/state.json`.
  - Requirements: 1.6, 2.4, 2.8, 19.1, 19.2, 19.3, 19.4
