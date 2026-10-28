# Requirements: every animation tracked, the heavy ones on the share

Seed 46, `project-seeds/46-p2-every-animation-file-tracked-with-its-preview-and-source/`.
Every animation file the installation has been given is kept with its preview and a
readme of its source. Git tracks the small ones with both; a heavy one, a group of a long
video or a file over 50,000,000 bytes, is kept on the share, with only its preview, its
readme and its key with its path on the card tracked. The share's collection holds every
file. The owner's answers of 2026-10-27 and 2026-10-28 are in the seed; it has no open
question. Its figures, measured on 2026-10-28, hold as the seed gives them.

## 1. The local collection and the exclude line

1.1. The folder `collection/` of the owner's checkout, `/Users/koren/src/odrig`, built by
hand on 2026-10-27, moves whole to
`/Users/koren/src/odrig/scratch/collection-built-2026-10-27/`, a rename within one disk.
Nothing of it is deleted or changed, then or after.

1.2. The line `/collection/` of the checkout's `.git/info/exclude`, and the comment line
above it, are removed; every other line, `/env` among them, stays. From then on no path
of `collection/` of any worktree is ignored but by `.gitignore`.

## 2. The converter's `--beside`

2.1. `node converter/odrig.js thumbnail FILE... --catalog DIR [--card ODRIG] --beside`
writes, once the mapping is written, `X.gif` beside each file it did not pass over, in the
order the files are given: in the file's folder, the bytes of `DIR/<key>.gif`, in place of
a file of that name.

2.2. `X` is the file's name without its ending when that ending is `.odrg` or `.odrgx`, in
any case; a file with neither ending gets its whole name followed by `.gif`.

2.3. A file passed over gets no GIF, and a GIF already beside it stays as it is. Of two
files of one folder that differ only in their ending, the last one given writes the GIF.

2.4. A GIF that cannot be written ends the run with `cannot-write` and status 1; the
mapping is then written, and so are the GIFs before it.

2.5. `--beside` with `--out`, or without `--catalog`, is a mistake of the command line:
status 2, the usage text, nothing written; with `--out`, the line "--beside goes with
--catalog". The usage line becomes `node converter/odrig.js thumbnail FILE... (--catalog
DIR [--card ODRIG] [--beside] | --out OUT.gif)`, and the usage text gains a line for
`--beside`. Nothing is written on standard output; no subcommand and no reason is added.

## 3. The moves on the share

3.1. In the share's collection, at the path `ODRIG_ANIMATIONS` of `env` gives: the folder
`card/long/` moves whole to `long/`; `card/youtube/arps-mostly-mwc5p1aaigy_fit.odrg` and
`card/archive/jls-liquid-loops-1969_fit.odrg`, each with its `X.gif` and `X.md`, move to
`long/`. Nothing is deleted.

3.2. The Notes of those two readmes gain, at their end, "Kept in long/ of the collection
as a file over 50,000,000 bytes; its path on the card is
youtube/arps-mostly-mwc5p1aaigy_fit.odrg." and the same with
`archive/jls-liquid-loops-1969_fit.odrg`. No other file of the collection changes.

3.3. Afterwards the share's collection holds 1,078 files, `card/` 159 animation files,
`earlier/` 122, `others/` 2 and `long/` 76, each with its GIF and readme, and `README.md`;
each has the bytes of its copy in the archive of 1.1, but `README.md` and the two readmes
of 3.2. AppleDouble files `._*` are not counted, and the share's folder
artifacts/odrig/archived does not change.

3.4. When the share is not mounted, the agent does not mount it; the moves, the copies and
the commit of the collection wait, and the report says so.

## 4. The tracked collection

4.1. Git tracks `collection/`: in `card/`, `earlier/` and `others/` each small animation
file with its `X.gif` and `X.md`, 849 files; in `long/` the `X.gif` and `X.md` of each
heavy file, 152 files; and `collection/README.md`: 1,002 files, copied from the share's
collection after 3 and compared by bytes with the archive of 1.1.

4.2. `.gitignore` gains, at its end, `/collection/long/**/*.odrg` and
`/collection/long/**/*.odrgx`. They ignore every animation file of `collection/long/`, at
its root and in its folders, and no other file of `collection/`.

4.3. No tracked file of the repository is over 50,000,000 bytes, and no animation file of
`collection/long/` is tracked.

4.4. Each tracked `X.gif` has the bytes of `thumbnails/<key>.gif` of its file's key; each
`X.md` has the readme's shape of the seed, its File and Key those of its file.

4.5. The key of each heavy file is in `thumbnails/catalog.js`, with the file's path on
the card among its names: for a group of a long video its path in `long/`, for another
the path its Notes give. `thumbnails/` does not change.

4.6. `collection/README.md` is tracked and tells what the folder is, its four folders,
which files git tracks and which it ignores and where those are kept, the readme's shape,
`env`, and the steps of a later conversion from a worktree, with `--beside`. It names the
share as "the share's folder artifacts/odrig/collection" and no folder of a computer. Its
copy on the share has its bytes.

4.7. The converter's test of what is tracked lets a GIF lie in `collection/card/`,
`collection/earlier/`, `collection/others/` or `collection/long/`, at any depth, besides
`thumbnails/` and a seed's folder; MP4 and MOV files stay tracked nowhere.

4.8. Nothing of the installation reads `collection/` or `env`.

## 5. A later conversion

5.1. A later conversion goes into `collection/long/` when it is heavy, a group of a long
video in `long/yt-<id>/` and another heavy file by its own name with its path on the card
in its Notes; else into `collection/card/` at its path on the card, or
`collection/others/`.

5.2. Its steps run in a worktree of `origin/master`: import and encode in `build/`; copy
`X.odrg` into `collection/`; `thumbnail` with `--catalog thumbnails`, the `--card` of its
place and `--beside`; write `X.md`; commit by named paths `thumbnails/` and its files of
`collection/`, never a heavy animation file; copy the three files to the share's
collection.

## 6. `env`

6.1. `agent/getting-started.md` says, in prose, that a computer that has the collection
copies `env.template` to `env` and sets the collection's full path in it, and that git
ignores `env`. The page stays within its 200 lines, and its table of suites names the
collection in the onboarding suite's row, with that suite's time measured again.

6.2. `agent/working-rules.md` says that an agent takes the collection's path from
`ODRIG_ANIMATIONS` in `env`, from a worktree `../../env` of the owner's checkout, else
`env.template`, to copy there, to read back and in a one-line command for the emulator;
never a path typed from memory.

6.3. The onboarding test of the pages passes over `env` and `../../env` as names no clone
holds, by the whole word, so that `env.template` is still looked for.

## 7. The decision and the pages

7.1. `docs/decisions.md`, "Animation formats": the JSON source is what is committed for
an animation of the bench or of a test; an animation the installation is given is tracked
in `collection/` as its file with its preview and readme, but a heavy one, kept on the
share with only its preview and readme tracked; its JSON is not committed; the repository
is public, so the tracked collection is published with it. The rows for JSON frames and
GIF and the paragraph on ODRGX follow.

7.2. "a private repository" becomes "a public repository" in `docs/decisions.md`,
`agent/working-rules.md` and `agent/getting-started.md`, and
`tests/onboarding/test_rules.py` pins the new words.

7.3. A dated entry ends the change log of `docs/decisions.md`, and an entry "Seed 46: the
installation's animations in git, the heavy ones on the share" ends `docs/drifts.md`, with
the decisions this spec takes beyond the seed.

7.4. `agent/animation-guide.md`: a row "An animation the installation is given" in its
table of where things go, the import row "for the bench or a test", the preview row and
the ruling of "How large sources get" as the seed says; within 200 lines.
`tests/onboarding/test_guide.py` follows.

7.5. `agent/vocabulary.md`: the word collection right after preview;
`tests/onboarding/test_vocabulary.py` follows. `agent/README.md` and `docs/format.md` say
"of the bench or of a test" where they speak of the tracked source.

7.6. `docs/converter.md`: `--beside` in "thumbnail", its usage line and an example.

## 8. The checks

8.1. The onboarding suite gains `tests/onboarding/test_collection.py`, which checks 4.3 to
4.5, the folders of 4.1 and the two lines of 4.2 with a git of its own that no exclude of
one computer reaches.

8.2. Every suite that works on the first computer passes, the walk-through among them.

8.3. A check on real files: the 11 files of `collection/card/gifs/` and a copy of
`thumbnails/` in `build/beside/`, `thumbnail --beside` on them, each GIF equal to the
collection's `X.gif`, the copy of the catalog unchanged.

8.4. Every animation is available: each of the 359 files, by its key, is on the share's
collection; each of the 283 small ones is tracked on the branch; each of the 76 heavy ones
has its `X.gif`, `X.md` and catalog key tracked as in 4.5. `scratch/collection-readmes/`
of the owner's checkout still holds the records the seed names, unchanged.

8.5. The size is measured: `git count-objects -vH` before and after the commit of the
collection, and a clone of the branch into `build/clone/`; after the push, GitHub's size.

8.6. The owner is told in words what the seed's Definition Of Done lists.

8.7. When the work is merged, the seed's state is `completed` and its line leaves "What is
coming" in `AGENTS.md`.
