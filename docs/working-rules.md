# Working rules

The rules that bind every change to this repository, whoever makes it. The words used here
are explained in [vocabulary.md](vocabulary.md).

## How work is planned and recorded

- **A seed holds one piece of planned work.** It is a folder in `project-seeds/`, named by
  number, priority and subject, with two files. `seed.md` says what is wanted and why, and
  ends with a definition of done. `state.json` holds the seed's state, which is one of
  `remaining`, `in_progress`, `completed`, `suspended`, `cancelled` and `superseded`. The
  state is written nowhere else.
- **One seed, one commit.** A commit that adds a seed or changes its text holds that
  seed's folder and nothing more.
- **A seed becomes a spec before it is built.** The spec is three files in a folder of
  `docs/specs/` with the seed's name: `requirements.md` says what must hold, as numbered
  criteria that can be checked; `design.md` says how; `tasks.md` lists the steps in order,
  each with a checkbox. The spec is one commit and leaves the seed's state as it is.
- **One task, one commit.** The commit that does a task holds its code, its tests and the
  tick in its checkbox in `tasks.md`, and nothing of another task. Its subject is
  `Seed <number> task <number>: <the task's title>`. The first task of a spec sets the
  seed's state to `in_progress` and the last sets it to `completed`.
- **A question met on the way is answered, not asked.** When a seed, a spec or a document
  leaves a point open, or two of them disagree, decide it yourself and add an entry at the
  end of [drifts.md](drifts.md): the heading `## Seed <number>: <subject>`, then
  **Question.**, **Answer.** and **Resolution.**, which names the file that now carries
  the answer. If the question shows a gap in a document that defines the project, say so in
  the entry; your answer then holds until the owner rules. What the section
  [What needs the owner](#what-needs-the-owner) lists is never decided this way.
- **The scope of a seed is fixed once its tasks are being done.** Nothing is added to the
  seed or to its requirements then. A gap you find becomes a new seed, proposed to the
  owner and built after the work in hand.
- **A commitment for later reaches the owner in words.** Something left open, put off or
  found broken in passing counts for nothing while it stands only in a file, a commit
  message or a comment. Say it in the hand-over at the end of your work, and keep saying
  it until the owner turns it down or it has become a seed.

What has been decided is in [decisions.md](decisions.md), each decision as it stands now.

## How commits are made

- **Stage named paths only**: `git add <path> ...`. Never `git add -A`, `git add .`,
  `git add -u` or `git commit -a`. A working folder holds build products, trials and
  files that belong to somebody else, and a broad add commits them.
- **Read the list of files after every commit**, with `git show --stat`, and see that it
  is exactly what the task changed.
- **A test for a fault is seen failing first.** Write the test, run it against the code
  that still has the fault, and watch it fail in the way you expected. Put the failure you
  saw into the commit message. Only then mend the fault. A test that passes before the
  mend tests something else. A task that adds such a test says so in `tasks.md`.
- **Code carries no history.** Code and tests say what they do now. They have no comment
  about a seed, a task, a date, a ruling or an earlier version. That belongs in the commit
  message, the seed and the spec.
- **A suite is selected by discovery.** Each folder of `tests/` that holds tests is one
  suite, run by one command such as
  `python -m unittest discover -s tests/converter -t .`. No command, script or document
  lists test files, so a new test file needs no change anywhere else.
- **The suites pass before a commit.** The `tasks.md` of a spec says which suites a task
  runs, and [getting-started.md](getting-started.md#run-the-tests) has the command of each.
- **Leave alone what is not yours.** Nothing under `build/` or `.venv/` is committed, and
  nothing that was fetched or built. An untracked file that you did not make is not moved,
  edited, deleted or staged.

## What needs the owner

Do not decide these yourself, and do not work on a guess. Put the question to the owner in
words and wait for the answer.

- **Every addition to the command list.** There is one list of commands for every way a
  command can travel, and a command is added to all of them or to none.
- **Anything that changes a decision** in [decisions.md](decisions.md).
- **Anything about hardware or power**: wiring, the power supply, the limit that WLED puts
  on the current, which LEDs are connected. Wiring and power are handled on site by the
  operators and are not this project's work.

Some checks need a person, because only a person sees what the LEDs do or holds a phone
that has joined the board's network. The documents list them as the owner's checks, in
[firmware.md](firmware.md#the-owners-checks), and as the check list by eye, in
[emulator.md](emulator.md#the-check-list-by-eye). An agent leaves such a check open and
says so.

## If you have a board

Most contributors have none, and nothing in getting started or in the animation guide needs
one. For anyone who has:

1. **Two folders are never changed, moved, deleted or committed**: `esp32-backup/`, an
   image of the board's whole flash as it came, and `firmware/wled-16.0.1/`, the stock
   files of WLED. They are what brings a board back. They are untracked and exist on the
   first computer only.
2. **Only the tools of this repository talk to the board**: `firmware/fw.py` and
   `odrigctl`. A program that opens the board's serial port in the usual way restarts the
   board. The tools lower the line RTS before the line DTR when they send a command, which
   does not.
3. **One program uses the board at a time.**
4. **Brightness 40 or less.** One strip of 60 LEDs is wired at present, on pin 1, and it is
   fed from the board's 3.3 V pin. A show installed on the board in that state has a
   `brightness` of 40 or less in its `show.json`. The tracked shows have 128: pack a copy
   with a lower value. The tool does not check this.
5. **The flash is written only by `firmware/fw.py`**, which touches only the regions that
   [firmware.md](firmware.md#the-regions-of-the-flash) lists. The whole flash is never
   erased, and no fuse of the chip is ever written.
6. **The firmware is built only as `python3 firmware/fw.py build` builds it.** A build of
   the whole firmware with other compiler settings once left the board silent on USB.
7. **A board that stops answering needs a person**: the cable is pulled and put back by
   hand, and no program can do that. [firmware.md](firmware.md#verified-on-the-board) has
   the steps that follow.
8. **A person joins a computer to the board's Wi-Fi network**, not an agent, and an agent
   does not change WLED's settings.
9. **Say what you left on the board** in the commit message of a task that used it.

## The frame rate

Any refresh rate from 20 to 50 a second is acceptable on the board, for any content. Only a
rate above 50 or below 20 is a fault. Do not propose work to raise a rate that is inside
the range, and do not do any.

What was measured on the board, with the firmware making twenty outputs: the demo show is
refreshed 50 times a second, and a clip of 60 x 60 in which every LED changes at every
frame 36 to 42 times when its file is compressed and 45 to 47 times when it is not. The
emulator refreshes 50 times a second whatever plays, so it says nothing about the rate on
the board. The figures are in [firmware.md](firmware.md#verified-on-the-board).

## Several contributors at once

- **Each contributor has a checkout and a branch of their own.** Two contributors never
  work in one checkout: it has one checked-out branch, and when one of them switches it,
  the other's next commit lands on the wrong branch. Before you commit, see that
  `git branch --show-current` names your branch.
- **Nothing is committed directly on `master`.** It only receives merges.
- **A branch is brought up to date with `master` before it is merged**, by merging
  `master` into it or by rebasing it.
- **A branch is merged only with every suite that needs no board passing** on the
  up-to-date branch.
- **Two files are added to at the end only**: [drifts.md](drifts.md), and the change log
  that ends [decisions.md](decisions.md). An entry that is there is not edited or moved; a
  later finding is a new entry that names the earlier one. When your branch and `master`
  have both added at the end, keep both additions, those of `master` first.

## The owner's workflow skills

The owner runs this process with a set of workflow skills for coding agents: one turns a
seed into a spec, one puts the tasks of a spec into a queue, one has the queued tasks
implemented, one is the task runner that does them one commit at a time, and one sends a
notification after each task. They live on the owner's computer and are not part of this
repository, so a clone does not have them.

You do not need them, neither to make animations nor to contribute. What they produce is
what the rules above describe: the three files of a spec, and one commit for each task with
its checkbox ticked. Their own files, a queue and the notes of a session, are kept in
`.codex/`, which git ignores.
