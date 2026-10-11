# Tasks: Onboarding for agents and contributors (seed 10)

Seeds 01 to 05 are implemented, up to what needs a person, before these tasks start. These
tasks describe their tools and documents and change none of them. Where the repository
differs from what this spec's design relies on, follow the repository and record the
difference in `docs/drifts.md`.

No task needs the board. Tasks 3, 4 and 6 need a network connection, for the three
libraries the walk-through installs in its temporary folder.

Rules for every task:

- One task is one commit, on the contributor's own branch and not on `master`. The same
  commit ticks the task's checkbox in this file.
- Stage named paths only (`git add <path> ...`), never `git add -A`, `git add .`,
  `git add -u` or `git commit -a`. After committing, read `git show --stat` and confirm it
  lists exactly the files of the task.
- The tests of a task are in the task's commit. Before committing, run the quick suite,
  `python3 -m unittest discover -s tests/onboarding -t .`, and the converter's suite,
  `.venv/bin/python -m unittest discover -s tests/converter -t .`, which reads every
  tracked document; both pass. Tasks 5 and 6, which change or check `README.md`, also run
  `make -C core test`, `python3 -m unittest discover -s tests/emulator -t .` and
  `python3 firmware/fw.py test`; all pass. Tasks 3, 4 and 6 also run the walk-through,
  `python3 -m unittest discover -s tests/walkthrough -t .`, with the new files of the task
  staged; it passes.
- Where a task says "Prove it fails first", run the test against the state described, watch
  it fail in the way described, and put the observed failure in the commit message.
- Code and tests state what they do now. They carry no comment about seeds, tasks, dates or
  earlier versions.
- No command, script or document lists test files; each suite is selected by discovery.
- A page states what is so now. It tells no story of how the project got here, names no
  person and no path of somebody's computer, and describes nothing that is not in the
  repository. After a page is written, read it once from top to bottom as somebody who
  knows nothing of the project, and run every command it gives.
- Nothing is copied from a governing document or from another project. A page points to
  the document that specifies a thing.
- No tool is changed. Of the documents that exist, only `README.md`, `docs/decisions.md`
  and `docs/drifts.md` are changed. No seed is edited other than this seed's `state.json`,
  and no other seed's spec.
- No serial port is opened and the board is not touched. No firmware is built or flashed.
- Nothing is installed outside the walk-through's temporary folder. Nothing fetched or
  built is staged.
- A file that is untracked and was not made by the task is not moved, edited, deleted or
  staged.
- Answers to questions that come up are recorded in `docs/drifts.md`, at its end, not
  asked.

- [x] 1. The vocabulary, and the quick suite
  - Write `docs/vocabulary.md` as the design lists it: four groups, an entry for each word
    of Requirement 2 criteria 1 and 3, each definition one to four sentences that use only
    words defined above it, with a link to the governing document that specifies the thing.
  - Create `tests/onboarding/` with `support.py` and `test_pages.py` as the design
    describes them, with the vocabulary as the only page so far, and `test_vocabulary.py`.
    Each later task adds its pages to the list in `support.py`.
  - Set `"state": "in_progress"` in
    `project-seeds/10-p0-onboarding-for-agents-and-contributors/state.json`.
  - Prove it fails first: with a path that does not exist, a link to a heading the target
    lacks and a command with an option its tool does not have, each written into the page
    for the moment, the three tests of `test_pages.py` fail naming each. Undo it.
  - Requirements: 2.1, 2.2, 2.3, 2.4, 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 8.1, 8.7

- [x] 2. The working rules, and the rule for several contributors in the decisions
  - Write `docs/working-rules.md` with the seven headings of the design. Check every rule
    about the board against `docs/firmware.md` and every figure against its source in the
    design's table of facts.
  - In `docs/decisions.md`, "Scope and process": put the rule for several contributors in
    place of the entry that all work is committed directly on `master`, and say that the
    repository carries the vocabulary and the working rules. Add one entry at the end of
    the change log.
  - `tests/onboarding/test_rules.py`, and the page in the list of `support.py`.
  - Prove it fails first: `test_rules.py`, run against `docs/decisions.md` as it is before
    this task, fails naming the rule that all work goes directly on `master`.
  - Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 6.3, 6.4

- [x] 3. Getting started, and the walk-through
  - Write `docs/getting-started.md` with the headings of the design's table. Run every
    command of the page as it is written, in a clone that has nothing set up, and paste
    what the emulator and the record run print as they print it.
  - `tests/onboarding/test_start.py`, and the page in the list of `support.py`.
  - Create `tests/walkthrough/` with `support.py` and `test_fresh_copy.py`: the fresh copy,
    the followed and the not followed headings of the getting-started page, and the checks
    on the packed demo show and on the reply of its record run.
  - Prove it fails first: with the name of the requirements file misspelt in the page's
    command for the moment, the walk-through fails naming the page, the heading `Set up`
    and that command, and shows pip's message. Undo it.
  - Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 8.2, 8.3, 8.4, 8.5

- [ ] 4. The animation guide
  - Write `docs/animation-guide.md` with the headings of the design's table. Measure every
    size the page gives again with the tools as they are, and take the rates from
    `docs/firmware.md`.
  - `tests/onboarding/test_guide.py`, and the page in the list of `support.py`.
  - Add `tests/walkthrough/make_gif.py`, and the guide to `test_fresh_copy.py`: its
    followed and not followed headings, the GIF written before the import, and the checks
    on the imported source and on the show packed from it.
  - Prove it fails first: with the example generator's row changed for the moment to row 0,
    which no canvas has, `test_guide.py` fails where it runs the generator. Undo it.
  - Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7

- [ ] 5. The entry file, `CLAUDE.md` and the README
  - Write `AGENTS.md` with the headings of the design, at most 150 lines, and `CLAUDE.md`.
  - Add the section `Start here` to `README.md`. The phrases and the links that the suites
    of seeds 01 to 05 check in it stay.
  - `tests/onboarding/test_entry.py`, and the two files in the list of `support.py`.
  - Prove it fails first: with a line added to `AGENTS.md` for the moment until it has 151,
    the test of its length fails; and with one link to a file of `docs/` taken out, the
    test of the reading order fails naming that file. Undo both.
  - Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 6.1, 6.2, 7.7

- [ ] 6. The final check, and the seed's state
  - Read the acceptance criteria of Requirements 1 to 8 once more and name, for each one a
    program can check, the test that checks it; add a test where one is missing.
  - Read the six pages once more, in the order a newcomer reads them: `AGENTS.md`, the
    vocabulary, the working rules, getting started, the animation guide. Mend what is
    unclear, out of order or no longer true.
  - Run the quick suite, the four suites and the walk-through from a clean working tree.
    Put the count of tests of each and the time of the walk-through in the commit message.
  - Set `"state": "completed"` and `completedAt` in
    `project-seeds/10-p0-onboarding-for-agents-and-contributors/state.json`.
  - Requirements: 8.1, 8.2, 8.6, 8.7
