# Tasks: every animation tracked, the heavy ones on the share (seed 46)

The code these tasks start from is `master` at `4ad03e1`. The seed has no open question: a
question that comes up is decided and recorded at the end of `docs/drifts.md` under "Seed
46", never asked. Tasks 1 to 6 need neither the board nor a phone; task 3 and task 4 need
the share mounted. Task 7 follows the owner's merge.

Rules for every task:

- One task is one commit, which ticks its checkbox here. Stage named paths only, never
  `git add -A`, `git add .` or `git commit -a`. After committing, read `git show --stat`.
- The tests of a task are in the task's commit. Before committing, run the suites the task
  names from the repository root: `npm test --prefix converter`, `python3 -m unittest
  discover -s tests/converter -t .`, `make -C core test`, `python3 -m unittest discover -s
  tests/emulator -t .`, `python3 -m unittest discover -s tests/app -t .`, `python3 -m
  unittest discover -s tests/onboarding -t .`, `python3 -m unittest discover -s
  tests/mapping -t .`, `python3 -m unittest discover -s tests/walkthrough -t .` and
  `python3 firmware/fw.py test`. One at a time, never two at once, and with the shell's
  own background run for a long one, never `nohup ... &`.
- "Prove it fails first": run the new test against the state before the change, watch it
  fail, and put the observed failure in the commit message.
- Code and tests state what they do now: no comment about seeds, tasks, dates or earlier
  versions. No command, script or document lists test files.
- The share's path is read from `env` of the owner's checkout, `ODRIG_ANIMATIONS`. Nothing
  of the collection is deleted; the archive of task 1 is only read. The board is not
  touched, and nothing is added to the command list.
- The decisions a task takes beyond the seed go into `docs/drifts.md` under "Seed 46" in
  task 5's commit.

- [x] 1. The local collection archived and the exclude line removed
  - Set the seed's `state.json` to `in_progress`.
  - Move `/Users/koren/src/odrig/collection` whole to
    `/Users/koren/src/odrig/scratch/collection-built-2026-10-27/`; count its 1,078 files.
  - Remove the comment line and `/collection/` from the owner's `.git/info/exclude`;
    `git check-ignore -v collection/card/x.odrg` in the worktree answers nothing.
  - Check that `scratch/collection-readmes/` holds the records the seed names.
  - Suites: onboarding.
  - Requirements: 1.1, 1.2, 8.4 (the records)

- [x] 2. The converter's `--beside`
  - `converter/cli/arguments.js` and `converter/cli/thumbnail.js` as the design says;
    `docs/converter.md`: the usage line, the paragraph and an example.
  - `converter/tests/thumbnailtool.test.js`: `--beside` writes `X.gif` equal to the
    catalog's GIF, for a new key and for a key the catalog holds; it replaces an older
    `X.gif`; `X.ODRG` gets `X.gif`, and a file with neither ending its whole name and
    `.gif`; a file passed over gets none and an older GIF beside it stays; two files that
    differ only in their ending, the last one's GIF; a GIF that cannot be written ends
    with `cannot-write` and status 1, the mapping written; nothing on standard output.
    The refused command lines gain `--beside` with `--out` and `--beside` alone.
  - `converter/tests/cli.test.js` and `converter/tests/docs.test.js` follow the help and
    the usage line.
  - The check of requirement 8.3 on real files in `build/beside/`.
  - Prove it fails first: `--beside` is an unknown option before the change.
  - Suites: converter (npm), onboarding.
  - Requirements: 2.1 to 2.5, 7.6, 8.3

- [x] 3. The moves on the share
  - `scratch/collection-46/move_on_share.py` as the design says; it ends with
    `MOVED-OK`. The counts and the comparison go into the commit message.
  - Commit the ticked checkbox alone: the moves are outside git.
  - Requirements: 3.1 to 3.4

- [ ] 4. The tracked collection
  - `.gitignore`: the two lines.
  - `collection/`: the 1,001 files copied from the share by
    `scratch/collection-46/copy_to_worktree.py`, compared with the share and the archive;
    `collection/README.md` written, then copied to the share and read back.
  - `converter/tests/library.test.js`: the collection's GIFs among the tracked media.
  - `tests/onboarding/test_collection.py`, as the design says.
  - Staged from the list of 1,002 paths, with the other files of the task by name.
  - `git count-objects -vH` before the commit, in the commit message.
  - Prove it fails first: `test_collection.py` fails before the files are in place, and
    the converter's media test fails on the collection's GIFs before its change.
  - Suites: converter (npm), onboarding, emulator.
  - Requirements: 4.1 to 4.8, 5.1, 5.2 (in `collection/README.md`), 8.1

- [ ] 5. `env`, the decision and the pages
  - `tests/onboarding/support.py` and `tests/onboarding/test_pages.py`: `env` and
    `../../env` passed over by the whole word.
  - `agent/getting-started.md`, `agent/working-rules.md`, `agent/animation-guide.md`,
    `agent/vocabulary.md`, `agent/README.md`, `docs/format.md`, `docs/decisions.md` (the
    decision, "public", the change log) and `docs/drifts.md`, as the requirements say.
  - `tests/onboarding/test_guide.py`, `test_vocabulary.py` and `test_rules.py` follow.
  - Suites: onboarding, converter (npm).
  - Requirements: 5.1, 5.2, 6.1 to 6.3, 7.1 to 7.5

- [ ] 6. The measurement and every suite
  - `git count-objects -vH` after the collection's commit, and a clone of the branch into
    `build/clone/` with the sizes of its `.git` and its files.
  - `scratch/collection-46/available.py` ends with `AVAILABLE 359`.
  - Every suite of the rules above, one after another.
  - The numbers into `docs/drifts.md` under "Seed 46".
  - Requirements: 8.2, 8.4, 8.5

- [ ] 7. Completion, after the owner's merge
  - On `master`: `state.json` `completed` with `completedAt`, and the seed's line out of
    "What is coming" in `AGENTS.md`; the owner told in words what the seed's Definition
    Of Done lists.
  - Requirements: 8.6, 8.7
