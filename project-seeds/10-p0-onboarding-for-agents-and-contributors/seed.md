# Onboarding for agents and contributors

## Summary

The files a new coding agent or person needs in order to start contributing from a fresh
clone on another computer: an entry file for agents, a vocabulary, the working rules, a
getting-started page, and a guide for making animations and trying them in the emulator.

## Priority

- `P0`

## Depends On

- Seeds 01 to 05, whose tools and documents these files describe.

## Product Context

The owner wants to start preparing animations on another computer with another agent, in
parallel with the work going on here.

A fresh clone of the repository builds and passes its tests, and the converter and emulator
work from it. What it lacks is a way in. The knowledge is spread over a dozen documents, nine
seeds, their specs and a log of some two hundred settled questions. Nothing tells a newcomer
what to read first, what the project's words mean, which rules bind every change, or how to
get from a video file to an animation playing in the emulator.

The rules the owner adopted were taken from another project and exist here only as
references to that project and as habits of the agents that have worked so far. A new agent
on another computer cannot read them.

Several contributors will now work at once, on separate computers. The rule that all work
goes directly on `master` was made for one contributor.

## Technical Constraints

- The files describe the repository as it is. Every command they give is one that works from
  a fresh clone, and a test runs the commands or checks that the tools and paths they name
  exist.
- Nothing is copied from the governing documents. The new files point to them.
- The files are short enough to be read in full at the start of a session. The entry file for
  agents fits in 150 lines.
- The emulator runs on macOS only. The files say so, and say what works elsewhere.
- No file names a person, a private path on someone's computer, or anything secret.
- The owner's workflow skills (seed to spec, enqueue, implement, the task runner and notify)
  live outside this repository. The files say what they are and that they are not needed to
  make animations.

## Required Behavior

1. `AGENTS.md` at the top of the repository is the entry file for any coding agent:
   what the project is in a few lines, the reading order, the rules that bind every change,
   what must never be touched, and where to find everything else. `CLAUDE.md` points to it.
2. A vocabulary page defines the project's words as they are used now, among them: canvas,
   leg, strip, snake, mapping, show, item, cycle, installed file set, JSON frames, ODRG,
   core, host, emulator, firmware, command, drift, seed, spec, bench build and target.
3. A page of working rules states, in this project's own words:
   - how work is planned and recorded: seeds, specs, tasks, one task per commit with its
     checkbox ticked, and the drift log for questions settled without the owner;
   - how commits are made: explicit paths only, a regression test shown failing before its
     fix, no history comments in code, test commands that select a suite by discovery;
   - what needs the owner: every addition to the command list, anything that changes a
     decision in `docs/decisions.md`, and anything about hardware or power;
   - the board's safety rules, for anyone who has a board;
   - the frame-rate rule: 20 to 50 refreshes a second is acceptable for any content;
   - how several contributors work at once: each contributor works on a branch of their own,
     brings it up to date with `master` before merging, and merges only with every test suite
     passing; `docs/drifts.md` and `docs/decisions.md` are only ever added to at the end, so
     that two contributors' additions can both be kept.
4. A getting-started page takes a newcomer from a fresh clone to a running emulator: what
   has to be installed, the commands to set up and to run every test suite that needs no
   board, and the commands to pack and run the demo show and send it a command.
5. An animation guide covers making an animation and trying it without the board:
   - the two ways to make one, by a generator in code and by importing a video or GIF;
   - checking it, packing it into a show with a mapping file, running it in the emulator, and
     what to look for there;
   - where sources, shows and build products go, what is committed and what is not;
   - how large sources get, with figures, and the limit a hosting service puts on one file;
   - what form of a dense animation plays best on the board.
6. The README gives the reading order for people and points agents to `AGENTS.md`.
7. `docs/decisions.md` records the rule for several contributors in place of the rule that
   all work goes directly on `master`.

## Definition Of Done

1. A test follows the getting-started page and the animation guide from a fresh clone in a
   temporary folder: setup, the test suites, packing the demo show, a short run of the
   emulator in record mode, and an import of a small GIF through to a packed show.
2. A test checks that every path and tool the new files name exists, and that `AGENTS.md` is
   within its length limit.
3. All existing test suites pass.

## Open Questions

None. Use the resolved behavior in this seed.
