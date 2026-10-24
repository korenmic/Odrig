# Tasks: incremental and interruption-safe content updates (seed 34)

Seeds 07, 24, 29, 31 and 32 are implemented before these tasks start. Where the real code
differs from what the design relies on, follow the code and record the difference in
`docs/drifts.md`. Tasks 1 to 6 need no board; task 7 needs the board.

Rules for every task:

- One task is one commit, which ticks its checkbox here. Stage named paths only.
- Before each commit the suites of the parts the task changed pass, with the onboarding
  suite always among them: a change of the firmware tool runs `python3 firmware/fw.py
  test`; one of the core `make -C core test` and `python3 -m unittest discover -s
  tests/emulator -t .`; one of the command tool the emulator's suite. Every suite that
  needs no board passes at the end of the seed.
- "Prove it fails first": watch the test fail on the code before, and put what was seen
  into the commit message.
- Code states what it does now; no comment about seeds, tasks or dates.
- The additions to the command list, approved in advance by the owner, are the form
  `upload begin <id> <file> <bytes> <crc32>` and the reply member `unchanged`; the firmware
  tool gains the command `recover-storage`, the options `--dry-run` and `--keep-copies` of
  `install-show`, and the reasons `cancelled`, `recovery-needed` and `storage-changed`. Each
  goes into its document and the change log of `docs/decisions.md`. Nothing else is added.
- Answers to questions that come up go into `docs/drifts.md`.

- [x] 1. The regression: one removal rewrites the whole folder
  - Set the seed's `state.json` to `in_progress`.
  - `tests/firmware/test_incremental.py`: a full storage of each layout; removing one
    animation changes at most the blocks of the files written and 4 more. Marked as an
    expected failure, which task 2 turns into a pass.
  - Prove it fails first: the removal changes megabytes at each layout.
  - Requirements: 7.1

- [x] 2. The image changes what differs
  - `firmware/fwtool/storage.py`: `change_of`, the file-by-file `with_show` with its second
    way, `blocks_in_use`, `blocks_of_files`, `plan`, `run_bytes`, `runs` with `among`.
  - `firmware/fwtool/cli.py`: `install-show` prints how the show changes and keeps the
    board's `order.txt` for a folder without one; `--dry-run`, with the plan line, and
    `--keep-copies`. `storage.folder_files` takes `order.txt`.
  - Tests: `tests/firmware/test_incremental.py` at both layouts, removal, addition,
    replacement and the same folder; the blocks in use; the replacement without room;
    `no-space`; `tests/firmware/test_storage.py` and `test_layouts.py` for the lines, the dry
    run and the copies.
  - `docs/firmware.md`, "install-show".
  - Requirements: 1.1 to 1.6, 4.1, 4.3, 4.4, 6.5, 7.2

- [ ] 3. The order of the write, the journal and recover-storage
  - `firmware/fwtool/journal.py`; `firmware/fwtool/cli.py`: `write_storage`, `apply_change`,
    `held_interrupts`, `recover-storage`, the refusal of every command that touches the
    board while a journal is there; `firmware/fwtool/flasher.py`: `compare`, esptool in a
    session of its own.
  - Tests: `tests/firmware/test_recovery.py` at both layouts, with a fault at each step;
    the calls and lines of `install-show`, `set-wifi`, `set-limit` and `install-firmware`
    as they are now.
  - `docs/firmware.md`: "install-show" as it writes now, `recover-storage`, the three
    reasons; `docs/decisions.md`: a line for the tool's additions.
  - Requirements: 2.1 to 2.6, 3.1 to 3.6, 4.1, 4.2, 6.4

- [ ] 4. The live route: an unchanged upload and the cleanup at the next change
  - `core/src/core_state.h`: `Upload.installed`; `core/src/upload.h/.cpp`:
    `upload_begin_known`, `upload end` sets `installed`; `core/src/storage.cpp`:
    `storage_cleanup`; `core/src/commands.cpp`: `upload begin` with six words;
    `core/src/content.cpp`: `ignore` calls the cleanup.
  - Tests: `tests/core/test_incremental.py`: the bytes of each live change in a show of 100
    items; `unchanged` and when it is not given; a power cut and a failure at every storage
    call of `remove many`, `ignore` and the start's cleanup; the cleanup at the next change.
    The existing tests of the cleanup that blocked later changes and of the arrays of the
    sources follow.
  - `core/src/storage.cpp`: `remove many` without a file that goes writes no `pending.txt`.
  - Prove it fails first: an upload of the bytes an item has writes the whole file again;
    a later change is refused while a cleanup is unfinished; `remove many` of an animation
    whose file another item names stops the test host with `file misuse`.
  - `docs/commands.md`, `docs/core.md`, `docs/decisions.md`.
  - Requirements: 5.1, 5.2, 5.4, 5.5, 6.1 to 6.3, 6.5, 7.2

- [ ] 5. The command tool and the emulator
  - `odrigctl/content.py`, `odrigctl/cli.py`: the CRC-32 sent, the form without it after
    `bad-argument`, the line of outcome.
  - Tests: `tests/emulator`: the same upload twice over the line port and over HTTP, the
    second `unchanged`; a target that answers `bad-argument` to the CRC-32; the lines.
  - `docs/emulator.md`, `docs/commands.md`.
  - Requirements: 5.3

- [ ] 6. The documents
  - `docs/firmware.md`: "Changing what the board holds": flashing, a change by command, a
    change by image, the quarantine, the board's check and the recovery of storage, with
    the step that cannot be cancelled, what the kept images bring back and what not, and
    the measures of a full storage.
  - Every suite that needs no board, also `tests/mapping`; the seed's state stays
    `in_progress` for task 7.
  - Requirements: 7.3, 7.4

- [ ] 7. The board
  - In the run's board session, at brightness 40 or less: one animation removed and one
    added by command (`odrigctl remove`, `odrigctl upload`, the same upload again), and by
    `install-show` with `--keep-copies`; the time and the bytes of each, the manifests
    before and after (`read-show`), the app not flashed; what remains on the board said.
    The seed's state `completed` when all is seen, otherwise what is missing said in
    `docs/firmware.md`, "Verified on the board".
  - Requirements: 7.4
