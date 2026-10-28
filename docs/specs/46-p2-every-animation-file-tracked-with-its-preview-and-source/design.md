# Design: every animation tracked, the heavy ones on the share

## What this design relies on

- The collection built on 2026-10-27, `/Users/koren/src/odrig/collection`, with 1,078
  files: `card/` (235 animation files at their card paths, `long/yt-<id>/` among them),
  `earlier/` 122, `others/` 2, a GIF and a readme beside each, and `README.md`; hidden by
  the line `/collection/` of `.git/info/exclude`, which every worktree shares.
- The share's collection, the same 1,078 files, at the path of `ODRIG_ANIMATIONS` in
  `env` of the owner's checkout (`env.template` holds the same path).
- `thumbnails/catalog.js` with every key of the collection and its names, the card paths
  among them (checked for the 76 heavy files on 2026-10-28).
- `converter/cli/arguments.js`: each subcommand's `usage`, `options`, `flags` and `check`;
  a flag is a word mapped to a value name, false unless given.
- `converter/cli/thumbnail.js`: `intoCatalog(values, streams)` reads the mapping, writes
  each new GIF, passes over a refused file with a line on standard error, and writes the
  mapping last; `files.write` throws `cannot-write` for a file it cannot write.
- `tests/onboarding/support.py`: `looked_for(word)`, which passes over prefixes of folders
  made on a computer and a few whole names.
- `converter/tests/library.test.js`: the test of what is tracked, whose media rule lets
  `thumbnails/<key>.gif` and a GIF inside a seed's folder be tracked.

## The local collection and the exclude line (task 1)

- `mv /Users/koren/src/odrig/collection
  /Users/koren/src/odrig/scratch/collection-built-2026-10-27` after a check that the
  target does not exist; then a count of its files, 1,078.
- `.git/info/exclude`: the two lines `# The collection of every animation, kept outside
  git (seed 46).` and `/collection/` are removed byte-safe; the rest stays. A worktree's
  `git check-ignore -v collection/card/x.odrg` then answers nothing.
- The archive is never written to again; every later step only reads it.

## `--beside` (task 2)

- `arguments.js`, `thumbnail`: `flags: {"--beside": "beside"}`; the usage line
  `thumbnail FILE... (--catalog DIR [--card ODRIG] [--beside] | --out OUT.gif)` and the
  line `  --beside       writes each file's preview beside it as X.gif, with --catalog`;
  `check`: after the existing checks, `if (values.beside && values.catalog === null)
  throw refuse("--beside goes with --catalog")`. Alone, `--beside` still meets "give one
  of --catalog and --out" first.
- `thumbnail.js`: `besideOf(file)`, the path `X.gif` in the file's folder, `X` the name
  without `/\.odrgx?$/i`, else the whole name and `.gif`. `intoCatalog` keeps, for each
  file not passed over, `[file, key]`; after the mapping is written, when `values.beside`,
  it writes for each in order `files.write(besideOf(file), fs.readFileSync(path.join(
  folder, `${key}.gif`)))`. A failed write throws `cannot-write` there, after the mapping
  and the GIFs before it.
- `docs/converter.md`: the usage line, the paragraph of `--beside` and an example with
  `--card`.

## The moves on the share (task 3)

- A script of the agent's, `scratch/collection-46/move_on_share.py` of the owner's
  checkout, untracked: it reads the share's path from `env`, stops when that folder is
  missing, renames `card/long` to `long` and the six files of the two big ones into
  `long/`, appends the sentence of requirement 3.2 to the Notes line of their readmes,
  removes AppleDouble files `._*` it made, and then compares every file of the share's
  collection with the archive: the archive path of a file of `long/yt-<id>/` is
  `card/long/yt-<id>/`, of the two big ones `card/youtube/` and `card/archive/`; every
  other path is the same. All bytes equal but the two readmes and `README.md`; each of
  those two equals its archive copy with the sentence added. It prints the counts by
  folder and ends with `MOVED-OK` or with the first difference.

## The tracked collection (task 4)

- `scratch/collection-46/copy_to_worktree.py`: from the share's collection into
  `collection/` of the worktree, the small animation files with their GIFs and readmes
  and, of `long/`, only the GIFs and readmes; each copy compared by bytes with the share
  and with the archive (through the mapping above); 1,001 files; no animation file of
  `long/` copied.
- `collection/README.md`: written in the worktree from the archive's README, changed as
  requirement 4.6 says; then copied to the share's collection and read back.
- `.gitignore`: the two lines at its end.
- Staging by named paths, from a list of the 1,002 paths given to `git add
  --pathspec-from-file`; `git status --short` then shows no other path.
- `converter/tests/library.test.js`: the media rule also lets
  `/^collection\/(card|earlier|others|long)\/.+\.gif$/` be tracked; the test's name says
  "the only media files are the default catalog's previews, GIFs beside a seed and the
  collection's previews".
- `tests/onboarding/test_collection.py`, in the onboarding suite:
  - the tracked files of `collection/` from `git ls-files collection`;
  - the readme read line by line against the 16 labels of the seed, in order, each value
    not empty, UTF-8, no carriage return, its File the name and its Key `crc32-size`;
  - `zlib.crc32` and the size give the key of each tracked animation file;
  - `thumbnails/catalog.js` parsed by its line shape into keys with their names;
  - the card path of a heavy file: `long/yt-<id>/` and the readme's File for a group of a
    long video; the path after "its path on the card is " in the Notes for another;
  - the size of every tracked file from `git ls-files -z` and the file system;
  - the ignore lines asked of a git of its own: `git init` in a temporary folder, then
    `git --git-dir=<it>/.git --work-tree=<root> -c core.excludesFile=<an empty file>
    check-ignore --no-index -q <path>` for the six paths of the seed.

## `env` and the pages (task 5)

- `tests/onboarding/support.py`: `UNTRACKED_FILES = ("env", "../../env")`, passed over by
  `looked_for` by the whole word; `test_pages.py`'s check of `looked_for` names both.
- `agent/getting-started.md`, "Set up": the sentence on `env`, its paragraph under the
  commands shortened so that the page keeps 200 lines; "private" becomes "public"; the
  onboarding suite's row names the collection, with its time measured again.
- `agent/working-rules.md`: "public"; the paragraph on `env` in "Several contributors at
  once", after "One app, in the emulator and on the phone".
- `agent/animation-guide.md`, `agent/vocabulary.md`, `agent/README.md`, `docs/format.md`,
  `docs/decisions.md` (the decision, "public", the change log) and `docs/drifts.md`, as
  the requirements say; `tests/onboarding/test_guide.py`, `test_vocabulary.py` and
  `test_rules.py` follow.

## The measurement and every suite (task 6)

- `git count-objects -vH` in the worktree before task 4's commit is recorded in task 4's
  commit message, and after it in task 6.
- `git clone --no-local --single-branch --branch seed-46-collection <worktree>
  build/clone`, then `du -sk` of its `.git` and of its files.
- The check of requirement 8.3 in `build/beside/`.
- The check of availability, `scratch/collection-46/available.py`: for each of the 359
  animation files of the archive, its key, its place in the share's collection with equal
  bytes, and, for a small one, the tracked file of the branch with equal bytes; for a
  heavy one, its tracked `X.gif`, `X.md` and catalog key with the card path. It ends with
  `AVAILABLE 359` or the first gap.
- Every suite: the converter's (npm), the Python library's, the core's, the emulator's,
  the app's, the onboarding suite, the firmware tool's and the walk-through, one after
  another.

## Completion (task 7)

- After the owner has merged: `state.json` `completed` with `completedAt`, and the seed's
  line out of `AGENTS.md`, in one commit on `master`.
