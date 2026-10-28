# Every animation tracked with its preview and its source, the heavy ones on the share

## Summary

Every animation file the installation has been given is kept as the file itself, ODRG or
ODRGX, never as its JSON, in the folder `collection/`, with its preview, a copy of its GIF
in `thumbnails/`, and a short readme of where it came from beside it. The collection was
built by hand on 2026-10-27, outside git, on the first computer and on the share: 359
files, 357 keys, 4.72 GB of animation files. By the owner's correction of 2026-10-28, git
tracks it, all but its heavy files: the groups of the 8 long videos and every other file
over 50,000,000 bytes, 76 files of 4.09 GB. They move to `collection/long/`, where only
their GIFs and readmes are tracked; `.gitignore` ignores the files themselves, which are
kept on the share, whose collection holds every file. The folder built on the first
computer is archived in `scratch/`. The other 283 files, 630 MB, are tracked with their
GIFs and readmes, and so is `collection/README.md`. The untracked `env`, a copy of the
tracked `env.template`, names the share's collection for agents, for the emulator's
one-line commands too. The converter's `thumbnail` subcommand gains `--beside`, which
writes the preview beside each file. The pages say where an animation the installation is
given is kept, and that the repository is public, so the tracked collection is published
with it. Google Drive waits until it has room.

## Priority

- `P2`

## Depends On

- Seed 44, for the key of an animation, the CRC-32 and the size of its file, for
  `thumbnails/` with the preview of each of the 424 animations known, and for the
  converter's `thumbnail` subcommand with `--catalog` and `--card`. It is merged on
  `master`. Only its checks on the board and on a phone keep it in progress, and this
  seed needs neither.
- Seeds 35, 38 and 41, for the card: its folder `odrig` with sub-folders, the rule of its
  names and its limits.

## Product Context

On 2026-10-27 the owner asked, in their words: "I want all the animation tracked, would it
be possible? and per animation file a readme where it was taken from if possible to back
track". After an assessment, the owner asked whether ODRG is lossless like JSON, and how
much keeping ODRG only saves. Then: "add a seed to save only the odrg + preview thumbnail
per each next to it". The answers given were these. ODRG keeps the same picture at every
millisecond as the JSON it was made from (`docs/converter.md`, "decode"). Keeping ODRG
instead of JSON saves about 41 GB: 4.7 GB of ODRG against an estimated 46 GB of JSON.

Seed 46 was first written to track those files in git. It had three open questions: plain
git or Git LFS; whether the repository is private, as the pages say, or public, as GitHub
shows it; and where the earlier set came from. Later on 2026-10-27 the owner answered all
three: only the catalog of previews tracked, and the collection kept outside git; the
repository public; the earlier set's sources unknown for now. The seed was rewritten so,
and the collection was built by hand.

On 2026-10-28 the owner corrected the first answer: git ignores only the heavy, very long
animations that weigh a lot, and the small ones are tracked. Every file above 50 MB goes
into a folder `long`, ignored by git and kept on the share, with its preview and its
readme tracked. An untracked file `env` and a tracked `env.template` hold one constant,
the full path of the folder that keeps every animation, the share's collection, for
agents and for the emulator's one-line commands. And GIFs are acceptable beside a seed.
See "The Owner's Answers". This is the seed rewritten for those words.

Before 2026-10-27 the installation's animations lived only in places git does not track:
the card, a copy of it in `scratch/`, show folders in `build/`, the share, and a folder of
the owner's Google Drive. The records of where they came from are in
`scratch/new-animations/` of the owner's checkout, which git ignores. The collection puts
the files in one place, each with its readme: on the first computer and on the share, and
now in the repository, all but the heavy files.

## Technical Constraints

- **Where it stands.** This was done by hand on 2026-10-27, after the owner's first
  answers, and on `master` on 2026-10-28. It is the seed's starting state.
  - `collection/` was built in the owner's checkout, `/Users/koren/src/odrig`. Git ignores
    it there, and in every worktree of that checkout, through the line `/collection/` of
    `.git/info/exclude`, a local file that is not tracked. A clone elsewhere, the Windows
    computer's among them, has no such line. A worktree holds no `collection/` of its own.
  - It holds 359 animation files of 357 keys, 4,718,456,538 bytes (4.72 GB), each with
    `X.gif` and `X.md` beside it, and `collection/README.md`, 5,571 bytes: 1,078 files,
    4,730,999,732 bytes in all. Every animation file is an ODRG file of 60 x 60. None is
    ODRGX.
  - Each `X.gif` is byte for byte the `thumbnails/<key>.gif` of its key, every key is in
    `thumbnails/catalog.js`, and each readme has the 16 lines below with the name and the
    key of its own file. A script checked all 359 on 2026-10-28.
  - The 359 readmes were written by one script, `write_readmes.py`, from the records
    below. 233 keys have a full source, a link from the records. 2 have a partial one, a
    link read from a name. 122 have none: `Source: unknown`. Four scripts written apart
    from it checked them, with 0 errors.
  - The folder was copied to the share, as the share's folder artifacts/odrig/collection,
    and every copy was read back. Then the share's old animation paths were moved, not
    deleted, into the share's folder artifacts/odrig/archived, with their relative paths:
    the 122 files of its root, and its folder `animations/` with `new animations` in it.
    The APK, the firmware and `photos/` stay where they are. On 2026-10-28 the share's
    collection held the same 1,078 files as the owner's checkout, by path and size, and
    no AppleDouble file `._*`.
  - Google Drive was not touched.
  - On `master`, 629bf57 added `env.template`, one line,
    `ODRIG_ANIMATIONS=/Volumes/192.168.0.1/artifacts/odrig/collection`, the share's
    collection as the first computer mounts it, and the line `/env` at the end of
    `.gitignore`. The owner's checkout holds the untracked `env`, of the same bytes.
  - On `master`, 941a464 let a tracked GIF lie inside a seed's folder, by the owner's
    ruling of 2026-10-28: the converter's test, in `converter/tests/library.test.js`, is
    now "the only media files are the default catalog's previews and GIFs beside a seed".
- **What the collection holds.** After this seed, four folders:
  - `collection/card/`: the 159 animation files of the card's folder `odrig` that are not
    heavy, at their paths, without its catalog, as `scratch/all-card-local/odrig` holds
    them: 2 at its root, `archive/` 4, `gifs/` 11, `reels/` 15, `science-in-8bit/` 108 and
    `youtube/` 19. The 2 at the root have the same bytes as two files of `youtube/`. They
    are kept, so that `card/` holds the card's paths.
  - `collection/earlier/`: the 122 files of the share's root, the owner's earlier set.
    They are 119 files of 43 originals numbered 01 to 43, in the variants `fit`, `crop`,
    `cropfit` and `zoom70`, with `alphabet_english.odrg`, `alphabet_hebrew.odrg` and
    `43-yt-784dsKVrdjQ_center60of256.odrg`.
  - `collection/others/`: the files with no place on the card, at first
    `1000313299.odrg` and `1000313581.odrg`. They were on the board's own storage before
    the session of 2026-10-25, and are found only in `scratch/board-2026-10-25/`.
  - `collection/long/`: the 76 heavy files. The card's `long/yt-<id>/`, 8 folders with
    74 files, keep their paths, so that `long/yt-<id>/` of the collection is
    `long/yt-<id>/` of the card. At its root, by their own names, are the two other heavy
    files, `arps-mostly-mwc5p1aaigy_fit.odrg` of the card's `youtube/` and
    `jls-liquid-loops-1969_fit.odrg` of its `archive/`.
  Today, as built, `card/` holds all 235 files of the card, `long/yt-<id>/` and the two
  other heavy files among them, and there is no `long/`; "The moves" makes the four
  folders.
- **Heavy and small.** A file is heavy when it is a group of a long video, a file of the
  card's `long/yt-<id>/`, or when it is over 50,000,000 bytes. A long video is kept whole,
  its small last groups with it, so that its groups stay together: the smallest such
  group is `yt-rf6c0a518ue_05.odrg`, 6,071 bytes. Every other file is small. Today:
  - heavy: 76 files, 4,088,620,595 bytes. They are the 74 groups of the 8 long videos, 41,
    9, 8, 5, 4, 3, 2 and 2 of them, and two other files over 50,000,000 bytes,
    `card/youtube/arps-mostly-mwc5p1aaigy_fit.odrg`, 87,743,717 bytes, and
    `card/archive/jls-liquid-loops-1969_fit.odrg`, 71,498,473 bytes. Their 76 GIFs and 76
    readmes are 2,320,807 bytes.
  - small: 283 files, 629,835,943 bytes, the largest
    `card/youtube/spacedoutth-tw733ut5ze0_fit.odrg`, 44,240,343 bytes. Their 283 GIFs and
    283 readmes are 10,216,816 bytes.
  The owner's "above 50 MB" is read as over 50,000,000 bytes. That is below 50 MiB,
  52,428,800 bytes, above which GitHub warns of a file.
- **What it does not hold.** 67 of the 424 keys of `thumbnails/catalog.js` are not in it:
  - the 57 test files of `test-animations/` and of the valid vectors of `tests/vectors/`,
    which git tracks where they are, with their JSON or `build.mjs` beside them;
  - the 10 files the generators write: `hello.odrg` 4 times, `dvd.odrg` and `dense.odrg`
    3 times each, each with other bytes. What a generator writes is not kept; the
    generator is.
  Also left out: the 2 broken test files of the board's session of 2026-10-25, which the
  reader refuses and which have no preview; the 34 trial files of agents, found only in
  worktrees and in `core/build/`; and `40-64ub7rv_fit.odrg` of `build/owner-show-full`,
  which has the bytes of `earlier/40-64ub7Rv_fit.odrg` and a name that differs only in
  case. No JSON is kept. When one is needed, `decode` writes it from the file into
  `build/`, with frames in a row of the same picture merged into one.
- **The readme.** Markdown in UTF-8 with LF line ends. One title and one uploader are not
  ASCII. A title line, an empty line, then these 16 lines, always all of them, in this
  order, each `- Label: value` with a value that is never empty:
  ```
  # TITLE

  - File: `X.odrg`
  - Key: `CRC32-BYTES`
  - Animation: W x H, KIND, LENGTH s, N frames
  - Source: LINK
  - Platform: PLATFORM
  - Uploader: UPLOADER
  - Title: TITLE
  - Media id: ID
  - Part: PART
  - Crop: CROP
  - Fit: FIT
  - Made with: COMMANDS
  - Converted: DATE
  - Found: WHERE
  - Added: DATE
  - Notes: NOTES
  ```
  `unknown` stands for what is not known.
  - TITLE: the title, else the uploader and the media id, else the file's name.
  - File and Key: those of its file. A readme names its file, not its path, so the two
    files at the root of `card/` have the same readme as their twins in `youtube/`.
  - Animation: read from the file. KIND is frames, text or widget, as `check` names it.
  - Source: the link. Platform: YouTube, Instagram, Giphy, Tenor, itch.io or Internet
    Archive. Uploader: the name the platform shows; one recorded as an e-mail address is
    written as `unknown`, and the link stays. Title and Media id: as recorded.
  - Part: `whole`, `from S s for D s`, or `group N of M, from S s for D s`. Crop: `none`
    or the crop `W:H:X:Y` of the cut. Fit: the converter's `--fit` and the mapping.
  - Made with: the converter's subcommands, their files as words in capitals such as
    `MEDIA`, `FRAMES.json` and `X.odrg`. Any other step is said in words: the download,
    the crop, the cut or the join of pieces.
  - Converted and Added: `YYYY-MM-DD`. Found: where the file was when it was added, in
    words. The move of the share's old paths into archived does not change it, nor the
    move into `long/`.
  - Notes: what the lines above cannot say, in words, or `none`.
  A readme names no folder of a computer, no mount point and no account of the owner. The
  share is "the share's folder artifacts/odrig", and Google Drive "the owner's Google
  Drive folder artifacts/odrig/animations". It holds no carriage return.
  - The two heavy files that are not of a long video keep their readmes, with one
    sentence added at the end of their Notes, since `long/` is not their path on the
    card: "Kept in long/ of the collection as a file over 50,000,000 bytes; its path on
    the card is youtube/arps-mostly-mwc5p1aaigy_fit.odrg.", and the same with
    `archive/jls-liquid-loops-1969_fit.odrg`. Their Found already names the card's
    folder. No other readme changes.
- **Where the first readmes came from.** The records of `scratch/new-animations/`:
  `inventory-sources.json`, whose map `src` gives 159 files with kind, id, link and
  uploader, and whose map `folders` gives the 8 long videos with link, title and
  uploader; the job lists `*.txt`; the logs `*.log`; and `picks-2026-10-26.json`,
  `search-2026-10-26.json` and `search2-2026-10-26.json`, with titles, which
  `inventory.json` gathers.
  - A link is taken from the records and never made from a name. The names of the
    conversions are lower case: `yt-t6jlhqnxryk` stands for the video `t6jlhqNxRYk`.
  - The one exception is the two `43-yt-784dsKVrdjQ` files. Their names hold a YouTube
    video id, and their readmes give its link, title and uploader, as oEmbed gave them on
    2026-10-27. Their Notes say it was read from the name, and that no record says the
    file was made from it.
  - Crop, Part and Converted come from the block of a log that ends in the line of the
    file's name and size. A group `yt-<id>_NN.odrg` of a long video is its group NN of
    15 minutes, from (NN - 1) x 900 s. Made with is written from the job's script, since
    the commands were not logged, and Notes say so.
  - The 122 readmes of `earlier/` give where the file was found, its date on the share,
    and its number and variant "as the name says" where the name has them. The dates are
    2026-10-12 for 115, 2026-10-15 for 5, and 2026-10-16 for the two `43-yt-784dsKVrdjQ`
    files; they are dates on the share, not of a conversion. 115 of them were also in the
    owner's Google Drive folder. The two readmes of `others/` say the files were on the
    board's own storage, read on 2026-10-25. No reading of a name's words, such as
    `tenor`, `whatsapp`, `slowtv` or a date, is written as a fact.
  - The script read those dates at the share's root, before the files were moved. It is a
    record, and it is not run again.
- **Keeping the records.** The script, the `inventory.json` it reads beside it, and the
  four scripts that checked the readmes, `check_readmes.py`, `check_singles.py`,
  `check_long.py` and `check_rest.py` with its `facts.json`, with their outputs and
  reports, were made in a session's scratch folder, which the system may clear. They were
  copied on 2026-10-27 into `scratch/collection-readmes/` of the owner's checkout, with
  `build_collection.py`, which built the folder, and `mirror_g.py`, which made the share's
  copy and the archive. Git ignores `scratch/`. None of them is committed.
- **What git tracks.** `collection/` becomes a folder of the repository:
  - in `card/`, `earlier/` and `others/`, each small file `X.odrg` with `X.gif` and `X.md`
    beside it, 849 files;
  - in `long/`, the `X.gif` and `X.md` of each heavy file, 152 files, and not the file;
  - `collection/README.md`.
  That is 1,002 files, 642,379,137 bytes with today's `README.md`. They are committed in
  the agent's worktree, copied there from the share's collection after the moves, each
  compared by its bytes with the built folder archived in `scratch/` (see "The owner's
  local collection").
  - No tracked file is over 50,000,000 bytes. The largest becomes 44,240,343 bytes; it is
    1,628,668 today.
  - Each tracked `X.gif` is the blob of its `thumbnails/<key>.gif`, so git keeps it once,
    and the two files at the root of `card/` are the blobs of their twins in `youtube/`.
    Of the 996 distinct blobs, the 357 GIFs are in git already. The other 639, 281
    animation files and 358 readmes, hold 602,179,037 bytes. zlib does not make an ODRG
    file smaller, so they take about 602 MB in git.
  - The repository is public, so every tracked file of the collection is published with
    it: anyone can clone it. Most of the files are conversions of videos and GIFs of
    other uploaders, whom their readmes name.
- **The two mirrors.** The share's collection, at the path of `ODRIG_ANIMATIONS`, holds
  every file of the collection, the heavy ones included. The tracked collection holds
  every small animation file with its metadata, and of a heavy one its metadata alone:
  its preview `X.gif`, its readme `X.md` with its key and source, and its key in
  `thumbnails/catalog.js` with its GIF and its names, its path on the card among them.
  `thumbnails/catalog.js` is the one tracked file that the app reads at runtime: by a
  row's key, and by its name and size while the key is not known. On 2026-10-28 the key
  of each of the 76 heavy files was in it, with the file's path on the card among its
  names. The readmes and the GIFs beside the files have no runtime consumer; they are for
  people and for the checks.
- **What git ignores.** `.gitignore` gains two lines at its end, after `/env`:
  ```
  /collection/long/**/*.odrg
  /collection/long/**/*.odrgx
  ```
  They ignore every animation file of `collection/long/`, at its root and in its folders,
  and nothing else: no GIF, no readme, and no file of `card/`, `earlier/` or `others/`. A
  broad `git add` never stages a heavy file. The heavy files are kept on the share, in its
  `collection/long/`, which holds every file of the collection; no clone holds them, and
  the first computer has them only in the built folder archived in `scratch/`.
  - Checked on 2026-10-28 with git 2.55.0, in the owner's checkout, with lines of the same
    shape: `git ls-files --others --ignored --exclude='/collection/card/long/**/*.odrg'`
    listed the 74 groups of the long videos and no GIF or readme, and
    `--exclude='/collection/card/**/*.odrg'` listed the two files at the root of `card/`
    too, so `**/` also stands for no folder. With `--cached`, the two lines match no file
    git tracks today.
  - git reads the endings in any case where it ignores case, as on macOS and Windows,
    and only as written elsewhere. The collection holds no ending in capitals.
- **The owner's local collection.** The folder `/Users/koren/src/odrig/collection` of the
  owner's checkout, built by hand on 2026-10-27, and the line `/collection/` of
  `.git/info/exclude` that hides it, hold for every worktree of that checkout: on
  2026-10-28, in such a worktree, `git check-ignore --no-index -v` answered
  `.git/info/exclude:9:/collection/` for `collection/long/x.odrg` and
  `collection/card/x.odrg` alike, so no path of `collection/` could be staged but with
  `git add -f`. The seed's first task therefore:
  - moves that folder whole to
    `/Users/koren/src/odrig/scratch/collection-built-2026-10-27/`, a rename within one
    disk, nothing deleted; git ignores `scratch/`. It stays there as built, a second copy
    of every file, and is not changed afterwards;
  - removes the line `/collection/` of `.git/info/exclude` and the comment line above it.
    The line `/env` and every other line stay.
  From then on every worktree tracks `collection/` through `.gitignore` alone, and nothing
  is staged with `-f`. The owner's checkout, on the commit the owner runs, holds no
  `collection/` until it moves onto a commit that tracks it, so no untracked file is in
  the way of that move. The heavy files are on the share, which holds every file of the
  collection.
- **The moves.** On the share, in its folder artifacts/odrig/collection:
  - the folder `card/long/` is moved whole to `long/`: its 8 folders, with their 74 files
    and the GIFs and readmes beside them;
  - `card/youtube/arps-mostly-mwc5p1aaigy_fit.odrg` and
    `card/archive/jls-liquid-loops-1969_fit.odrg`, each with its `X.gif` and `X.md`, are
    moved to `long/`. `card/youtube/` keeps 19 animation files and `card/archive/` 4.
  A move is a rename within one disk. Nothing is deleted, and no animation file or GIF
  changes. Every moved file is read back: the share's collection then holds the same 1,078
  files as the built folder archived in `scratch/`, by bytes, at their new paths,
  AppleDouble files `._*` not counted. The share's folder artifacts/odrig/archived does
  not change. The share's path is read from `env`. If the share is not mounted, the agent
  does not mount it: the report says so, and the moves, the copies and the commit of the
  collection wait for it.
- **`env` and `env.template`.** `env.template` is tracked, so every clone holds it: one
  line, `ODRIG_ANIMATIONS=` and the full path of the folder that keeps every animation,
  the share's collection as the first computer mounts it. `env` is untracked, ignored
  through `.gitignore`, one for each computer that has the collection: a copy of
  `env.template` with that computer's path. Today only the owner's checkout has one.
  - A worktree has no `env` of its own. From a worktree two folders down, such as
    `scratch/<name>/`, an agent reads `../../env` of the owner's checkout, and without it
    `env.template`.
  - An agent takes the collection's path from there whenever it names the share's
    collection: to move or copy files there, to read them back, and in a one-line command
    for the emulator that it gives the owner. It types no such path from memory.
  - A computer without `env` has no share to copy to: the copies wait, and the owner is
    told in words which files wait.
  - Nothing of the installation, and no test, reads `env`.
- **The converter.** `thumbnail` gains the option `--beside`, so that a preview beside a
  file is one command on every computer. Only the command line changes,
  `converter/cli/arguments.js` and `converter/cli/thumbnail.js`. The library does not.
  - The usage line becomes `node converter/odrig.js thumbnail FILE... (--catalog DIR
    [--card ODRIG] [--beside] | --out OUT.gif)`, and the usage text gains a line for
    `--beside`.
  - `--beside` goes with `--catalog` only. Given with `--out`, or alone, it is a mistake
    of the command line: status 2, the usage text, and nothing written. It is refused as
    `--card` is: "--beside goes with --catalog".
  - Once the mapping is written, the subcommand writes `X.gif` beside each file it did not
    pass over, in the order the files are given: in the file's folder, the bytes of the
    catalog's `<key>.gif`, in place of a file of that name. `X` is the file's name
    without its ending when that ending is `.odrg` or `.odrgx`, in any case. A file with
    neither ending gets its whole name followed by `.gif`.
  - A file passed over gets no GIF, and a GIF already beside it stays as it is.
  - Two files of one folder that differ only in their ending, such as `a.odrg` and
    `a.odrgx`, share `a.gif`: the last one given writes it. The collection holds no such
    pair.
  - A GIF that cannot be written ends the run with `cannot-write` and status 1, as a GIF
    of the catalog does. The mapping is then written, and so are the GIFs before it;
    `docs/converter.md` says so.
  - It still writes nothing on standard output. No subcommand and no reason are added,
    and nothing is added to the board's command list.
- **A later conversion.** It is added when it is handed to the owner. A conversion that
  is only tried is not added. It goes:
  - into `collection/long/` when it is heavy: a group of a long video in
    `long/yt-<id>/`, its path on the card, and any other file over 50,000,000 bytes in
    `long/` by its own name, with its path on the card, if it has one, in its Notes;
  - else into `collection/card/` at the path it is to have on the card, or into
    `collection/others/` when it has none.
  The owner's checkout stays on the commit the owner runs, which may lack `thumbnail`,
  `--beside` and the tracked `collection/`. So the steps run in a worktree of
  `origin/master`, after `git fetch origin`, two folders down, such as `scratch/<name>/`.
  The share's collection is the path of `ODRIG_ANIMATIONS`, read from `env` as above.
  Its steps:
  1. Import and encode in the worktree's `build/`, as today. The JSON stays there.
  2. Copy `X.odrg` to its place in the worktree's `collection/`. A path the collection
     already holds with other bytes, in git or on the share, is not reused: the
     conversion gets a name of its own first.
  3. Run `node converter/odrig.js thumbnail collection/card/<folder>/X.odrg --catalog
     thumbnails --card collection/card --beside`. For a group of a long video, `--card
     collection`, since its path from `collection/` is its path on the card. For a file
     of `others/` or any other file of `long/`, no `--card`.
  4. Write `X.md` in the readme's shape.
  5. Commit by named paths, in the worktree on its branch: `thumbnails/catalog.js`,
     `thumbnails/<key>.gif` for a new key, `X.gif` and `X.md`, and `X.odrg` when it is
     small. The `X.odrg` of `long/` is never staged; git ignores it.
  6. Copy `X.odrg`, `X.gif` and `X.md` to the same place in the share's collection, which
     holds every file, heavy ones included. The tracked files reach the owner's checkout
     when it moves to a commit that holds them; they are not copied there by hand.
  A file of the collection is never changed once added, but by this seed: the moves, and
  the Notes of the two readmes. A new conversion of the same media is a new file with a
  name of its own. `card/` keeps each file at the path it was given when it was added,
  and does not follow later changes to the card.
- **`collection/README.md`.** A file of the repository now, written in the agent's
  worktree and then copied to the share's collection, in place of its copy. It tells what
  the folder is, its four folders, which files git tracks and which it ignores and where
  those are kept, the readme's shape, `env`, and the steps above in the form from a
  worktree, with `--beside`. Its sentence on `.git/info/exclude` gives way to the two
  lines of `.gitignore`. It names the share as "the share's folder
  artifacts/odrig/collection" and no folder of a computer, as a readme does: the path is
  that of `ODRIG_ANIMATIONS`. It names neither the ten-leg files nor a reference
  converter, as no tracked document outside the records does.
- **The size of the repository.** Measured on 2026-10-28 in the worktree
  `scratch/seed-44` of the owner's checkout, at 629bf57:
  - `git count-objects -vH`: 32.56 MiB of packs and 1.37 MiB of loose objects. This is
    the object store the owner's checkout shares with its worktrees, every branch in it.
  - `git rev-list --objects --disk-usage origin/master`: 29,128,236 bytes, 27.78 MiB, for
    what `master` reaches, about the objects a fresh clone gets.
  - GitHub's size of the repository: 29,640 KB.
  No fresh clone was made for this rewrite. With the collection, a clone's objects grow
  by about 602 MB, to about 631 MB, and its files by 642 MB. GitHub asks for a repository
  under 1 GB, warns of a file over 50 MiB and refuses one over 100 MiB; no tracked file
  comes near.
  - Every clone and every checkout of `master`, each worktree included, then holds about
    642 MB more. The walk-through suite clones the repository with `--no-hardlinks` at
    each run, so it copies those objects and those files each time.
- **The decision and the records.**
  - In `docs/decisions.md`, "Animation formats", the sentence "The JSON source is
    committed for every animation, including those imported from video, and nothing else
    is committed in its place" changes. The JSON source stays what is committed for an
    animation of the bench or of a test. An animation the installation is given is
    tracked in `collection/` as its ODRG or ODRGX file, with its preview and its readme
    beside it, except a heavy one, a group of a long video or a file over 50,000,000
    bytes, which is kept on the share with only its preview and its readme tracked. Its
    JSON is not committed. The repository is public, so the tracked collection is
    published with it. The table's row for JSON frames, "The tracked, lossless source of
    each animation", and the paragraph on ODRGX, "The tracked source of a text or a clock
    is typed JSON", say "of the bench or of a test" the same way. The table's row for GIF
    adds that a copy of each preview lies beside its animation file in `collection/`.
  - In "Scope and process", `docs/decisions.md:37-38`, "a private repository" becomes "a
    public repository", by the owner's answer of 2026-10-27. The same goes for
    `agent/working-rules.md:127`, "which is private", and `agent/getting-started.md:54`,
    "Clone the repository, which is private".
  - A dated entry goes at the end of the change log: the collection tracked in git with
    each file's preview and readme, the heavy files kept on the share with only their
    previews and readmes tracked, and no JSON of them committed; `env` and
    `env.template`; the remote public, and the tracked collection published with it; the
    earlier set's sources unknown. It does not begin with "The repository has a remote":
    one entry only begins so (`tests/onboarding/test_rules.py:147-151`). The entries of
    2026-10-12, on the JSON source and on the remote as private, stay as they are: the
    change log is only added to at the end.
  - `docs/drifts.md` gains an entry at its end, "Seed 46: the installation's animations in
    git, the heavy ones on the share". Its question: the decision committed every
    animation's JSON source, seed 10's answer committed an imported source in
    `animations/` up to 50 MB, the pages called the remote private, and the entry "Seed
    44: the tracked previews are the media the repository holds" let no GIF be tracked
    but the previews, and since 2026-10-28 GIFs beside a seed. Its answer: the owner's
    answers of 2026-10-27 and 2026-10-28; the collection in git, the heavy files on the
    share; the remote public; GIFs tracked in `collection/` too, each a copy of a preview.
- **The pages.**
  - `agent/animation-guide.md`, its table of where things go:
    - a new row, "An animation the installation is given": in `collection/card/` at its
      path on the card, or in `collection/others/`, or, a group of a long video or a file
      over 50,000,000 bytes, in `collection/long/`; with its preview and its readme beside
      it, and a copy on the share. Committed: "Yes", the three files, but the animation
      file of `collection/long/`, which git ignores and the share keeps. The row gives
      the steps above in short, the command of step 3 in full in its form for a file of
      `card/`, and links to `collection/README.md`;
    - the import row becomes "A source made by an import for the bench or a test", still
      `animations/NAME.json` and "Yes";
    - the preview row says, on its line, that for an animation the installation is given
      the commit holds its files of `collection/` with `thumbnails/`;
    - its ruling in "How large sources get", that the JSON source is what is committed
      for every animation, says of the bench and of the tests.
    The guide names the files `NAME.odrg`, `NAME.gif` and `NAME.md`, as it names a source
    `animations/NAME.json`: the onboarding test reads `NAME` as any name, but `X.md` as a
    file that a clone must hold. It names no animation file of `collection/long/` by its
    path, since no clone holds one. It stays within its 200 lines; it has 199 today, so
    the row takes the last one and the changed sentences keep their lines.
  - `agent/README.md:14`, the vocabulary's source, `docs/format.md:7` and
    `docs/format.md:342` say of the bench or of a test, as the decision does. The source
    of an animation of the bench or of a test is tracked; that of an animation the
    installation is given is not kept, its animation file is. The source's entry uses no
    word explained after it, such as collection.
  - `agent/vocabulary.md`: a new word, collection, right after preview, in "The
    programs": every animation file the installation has been given, kept as the file
    that is played, with its preview and its readme beside it, in `collection/`; the
    heavy ones are kept on the share, and only their previews and readmes are tracked;
    nothing of the installation reads it. It uses no word explained after it, such as
    owner, seed or task. No entry before it uses the word.
  - `agent/getting-started.md`, in "Set up": on a computer that has the collection, the
    share's or a copy of it, copy `env.template` to `env` and set in it the collection's
    full path on that computer; git ignores `env`. It is prose, in no block of commands:
    the walk-through runs those, and the onboarding test knows no program that copies.
    The page has 200 lines, its limit: the paragraph under the commands of "Set up" is
    shortened to make room, and the page stays at 200 lines or fewer. The row of
    `tests/onboarding` in its table of suites names the collection in git, and its time
    is measured again.
  - `agent/working-rules.md`, in "Several contributors at once", after "One app, in the
    emulator and on the phone": a paragraph on `env`: an agent takes the path of the
    collection from `ODRIG_ANIMATIONS` in `env`, from a worktree `../../env` of the
    owner's checkout, else `env.template`, to copy there, to read back, and in a one-line
    command for the emulator that it gives the owner; never a path typed from memory. The
    page has 181 lines today.
  - `docs/converter.md`: `--beside` in the section "thumbnail", its usage line and an
    example.
  - `AGENTS.md`, under "What is coming": the commit of this rewrite changes its line for
    seed 46, which said the animations were kept outside git, to "**Every animation
    tracked with its preview and its source, the heavy ones on the share**, seed 46:
    small animation files tracked with their GIFs and readmes; long videos and files
    over 50 MB kept on the share, only their GIFs and readmes tracked." It names no path,
    since every path a page names must be in the clone, and `collection/` is not yet. The
    spec's only task on it is the one that sets the seed's state to `completed` and takes
    the line out, as `tests/onboarding/test_entry.py:140-152` requires.
- **Tests that change.**
  - `converter/tests/thumbnailtool.test.js`: `--beside` writes `X.gif` equal to the
    catalog's GIF, for a new key and for a key the catalog holds; it replaces an older
    `X.gif`; `X.ODRG` gets `X.gif`, and a file with neither ending its whole name and
    `.gif`; a file passed over gets none, and an older GIF beside it stays; a GIF that
    cannot be written ends with `cannot-write` and status 1, the mapping written; nothing
    is written on standard output. The list of refused command lines gains `--beside`
    with `--out`, and `--beside` without `--catalog`.
  - `converter/tests/cli.test.js`: the words the help of `thumbnail` gives gain
    `--beside`. `converter/tests/docs.test.js` checks the new usage line in
    `docs/converter.md` as it is.
  - `converter/tests/library.test.js`: a tracked GIF may also lie in `collection/card/`,
    `collection/earlier/`, `collection/others/` or `collection/long/`, at any depth, and
    the test's name says so: "the only media files are the default catalog's previews,
    GIFs beside a seed and the collection's previews". MP4 and MOV files are still
    tracked nowhere.
  - `tests/onboarding/test_collection.py`, new. A suite is one folder of `tests/`, and
    `agent/getting-started.md` lists the suites, so the test goes into the onboarding
    suite, which checks what a clone holds. It checks:
    - every tracked file of `collection/` is `README.md` at its root, or an animation
      file, a GIF or a readme in `card/`, `earlier/`, `others/` or `long/`;
    - every tracked animation file has `X.gif` and `X.md` tracked beside it; `X.gif` is
      byte for byte `thumbnails/<key>.gif` of the file's key, its CRC-32 of zlib and its
      size; `X.md` has the readme's shape, in UTF-8 with LF line ends, its File the
      file's name and its Key the file's key;
    - the `X.gif` and `X.md` of `long/` come in pairs; the readme has the shape, its File
      is `X.odrg` or `X.odrgx`, its Key is a key of `thumbnails/catalog.js`, and `X.gif`
      is byte for byte `thumbnails/<key>.gif`; the path on the card of a heavy file, its
      path in `long/` for a group of a long video and the one its Notes give for another,
      is among the names `thumbnails/catalog.js` gives its key;
    - no tracked file of the repository is over 50,000,000 bytes;
    - no tracked file of `collection/long/` ends in `.odrg` or `.odrgx`, in any case;
    - `.gitignore` holds the two lines, and `git check-ignore --no-index`, asked with the
      `--git-dir` of an empty repository that `git init` makes in a temporary folder, the
      repository's root as `--work-tree` and an empty file there as `core.excludesFile`,
      so that no exclude of one computer counts, ignores `collection/long/a.odrg`,
      `collection/long/yt-a/a_01.odrg` and `collection/long/a.odrgx`, and not
      `collection/long/a.gif`, `collection/long/a.md`, `collection/card/a.odrg` or
      `collection/README.md`.
    It reads the tracked collection, about 642 MB, at each run.
  - `tests/onboarding/test_guide.py`: 8 rows in the table of where things go; the row of
    `collection/` answers Yes; the phrases it pins of the ruling, in the guide and in
    `docs/decisions.md`, follow the new words.
  - `tests/onboarding/test_vocabulary.py`: `WORDS` gains "collection" right after
    "preview".
  - `tests/onboarding/test_rules.py:124` pins "a private repository"; it pins "a public
    repository".
  - `tests/onboarding/support.py`: `env` joins what a page may name although no clone
    holds it, beside `tools/` and `scratch/`: a new tuple, `("env", "../../env")`, which
    `looked_for` passes over by the whole word and not by its start, since every clone
    holds `env.template`. `TheChecks` in `tests/onboarding/test_pages.py` gains
    `../../env` among the words not looked for. `collection/` needs no such place: every
    clone holds it.
  - The tests of the whole tree list what git tracks, so they read the tracked
    collection: the scan for the Wi-Fi password in the firmware tool's suite, the search
    of `tests/converter` for the names of the ten-leg files and for a reference
    converter, the check of the emulator's suite for carriage returns, and the
    walk-through's clone. They do not change. On 2026-10-28 no file of the collection
    held the names of the ten-leg files, and no readme named a reference converter or
    the canvas given up, or held a carriage return.
- **Google Drive.** Not now. The owner's Google Drive has no free space. When it has room,
  the owner's first words apply to it: the collection copied there in its final shape,
  and the Drive's old folder artifacts/odrig/animations deleted and replaced by it. That
  waits for the owner's word then, and is not part of this seed.
- **What stays.** The board, the firmware, the core, the emulator, the app, the APK, every
  command and every reply. `thumbnails/` and its 424 previews, byte for byte. The card's
  catalog. `pack`, which takes JSON sources: a show of collection files is made with
  `decode` into `build/`, then `pack` from there. The collection's animation files and
  GIFs as they were built, and its readmes but the Notes of two. Nothing of the
  installation reads `collection/` or `env`.

## Required Behavior

1. Git tracks `collection/`: the 283 small animation files of `card/`, `earlier/` and
   `others/`, each with its `X.gif` and `X.md`, the `X.gif` and `X.md` of the 76 heavy
   files in `long/`, and `collection/README.md`. No tracked file is over 50,000,000
   bytes.
2. `.gitignore` ignores the animation files of `collection/long/`, and nothing else of
   `collection/`, in every clone. No heavy file is tracked or pushed.
3. The heavy files are in `long/` of the share's collection and of the owner's local
   collection. Those two hold the same files by path and bytes, and the tracked ones have
   the bytes of the repository's.
4. `node converter/odrig.js thumbnail FILE... --catalog DIR --beside` writes `X.gif`
   beside each file it does not pass over, a copy of the catalog's GIF of its key, once
   the mapping is written. `--beside` without `--catalog` is refused with status 2, and
   nothing is written.
5. A later conversion is added as the steps say: one command makes its preview in
   `thumbnails/` and beside it; `thumbnails/` and its files of `collection/` are
   committed, but a heavy animation file; and the three files go to the share's
   collection.
6. `env.template` and `env` are described in `agent/getting-started.md` and
   `agent/working-rules.md`, and an agent takes the share's path from `env`, for the
   emulator's one-line commands too.
7. `docs/decisions.md`, its change log and `docs/drifts.md` say what is tracked now, that
   the remote is public and that the tracked collection is published with it.
   `agent/working-rules.md` and `agent/getting-started.md` say public too.
8. The guide's table has the row of the collection with its steps, the vocabulary has the
   word collection, and `docs/converter.md` has `--beside`.
9. `collection/README.md` is tracked, and its copy on the share has its bytes.
10. The owner's local collection is archived whole in
    `scratch/collection-built-2026-10-27/`, and the line `/collection/` of
    `.git/info/exclude` is removed, by the first task.
11. No byte of `thumbnails/` changes, and nothing of the installation reads the
    collection.

## Definition Of Done

1. All test suites that need no board and no phone pass, the walk-through among them.
   The converter's suite checks `--beside` as "Tests that change" says, and GIFs in
   `collection/`. The onboarding suite passes with the test of the collection, the
   guide's eighth row, the word collection, `env` and the public remote.
2. A check on real files, in the agent's worktree: the 11 files of
   `collection/card/gifs/`, 3,338,428 bytes, are copied into `build/beside/card/gifs/`,
   and a copy of `thumbnails/` into `build/beside/thumbnails/`. `thumbnail` is run on
   them with `--catalog build/beside/thumbnails --card build/beside/card --beside`. Each
   GIF it writes equals the collection's `X.gif`, and the copy of the catalog keeps the
   bytes of `thumbnails/`.
3. The moves are made and read back. The share's collection holds 1,078 files: 359
   animation files, `card/` 159, `earlier/` 122, `others/` 2 and `long/` 76, with their
   359 GIFs and 359 readmes, and `README.md`; each has the bytes of its copy in the
   archive of `scratch/` (but `README.md` and the two readmes whose Notes change). The
   1,002 tracked files of the branch have the bytes of their copies there. The share's
   folder artifacts/odrig/archived still holds the 122 files and `animations/`.
   AppleDouble files `._*` are not counted. If the share is not mounted, the agent does
   not mount it: the report says so, and the moves on the share, the copies to it and its
   read wait.
4. `scratch/collection-readmes/` of the owner's checkout holds the script, its
   `inventory.json`, the four checks with their outputs, `build_collection.py` and
   `mirror_g.py`, untracked; the agent checks that they are there and changes none.
5. The size is measured on the branch: `git count-objects -vH` in the worktree before and
   after the commit of the collection, and a clone of the branch, made by `git clone
   --no-local --single-branch --branch <branch>` of the worktree into `build/clone/`,
   with the size of its `.git` and of its files. The report gives them, and after the
   push the size GitHub gives.
6. Every animation is available: each of the 359 files, by its key, is on the share's
   collection, and each of the 283 small ones is tracked on the branch too; each of the 76
   heavy ones has its `X.gif`, its `X.md` and its key in `thumbnails/catalog.js` tracked,
   with its path on the card among that key's names. The archive in `scratch/` holds the
   1,078 files as built, and the line `/collection/` is gone from `.git/info/exclude`.
7. The owner is told in words: that git now tracks the 283 small files of the collection
   with every GIF and readme, about 642 MB, published with the public repository, and that
   every clone and checkout holds them; that the 76 heavy files are only on the share,
   besides the archive of the built folder in `scratch/`; what is not in the collection
   and why; that 122 keys have no known source; that the records and the script that wrote
   the readmes stay untracked on the first computer; that the card itself and the board's
   own storage since 2026-10-25 were not read for the collection; that a file a phone
   uploads to the board does not reach the collection; that the built folder was archived
   in `scratch/` and the exclude line removed; and that Google Drive waits until it has
   room. No board is needed.

## Open Questions

None. The owner answered the three questions of the seed as first written on 2026-10-27,
and corrected the first answer on 2026-10-28; see "The Owner's Answers". The decisions
those words needed are taken in the constraints: "above 50 MB" as over 50,000,000 bytes; a
long video kept whole in `long/`, its small last groups with it; a heavy file that is not
of a long video in `long/` by its own name, its path on the card in its readme; the two
lines of `.gitignore`; `collection/README.md` tracked; the new test in the onboarding
suite; and the owner's local collection archived in `scratch/` and the line of
`.git/info/exclude` removed by the first task, so that no path is staged with `-f`. Google
Drive is no question: the owner said to leave it for now, since it has no free space. When
it has room, the copy there and the replacement of its old folder wait for the owner's
word.

## The Owner's Answers

On 2026-10-27 the owner asked for every animation to be tracked, with a readme for each
animation file of where it was taken from, so that it can be traced back. Then, after the
answers that ODRG keeps every picture and timing and that keeping ODRG saves about 41 GB:
"add a seed to save only the odrg + preview thumbnail per each next to it". The seed as
first written tracked the files in git, and asked three questions. Later that day the
owner answered them, in their words:

1. Storage: "the animations should not be tracked after all, only their catalog of
   hash-to-thumbnail-gif-preview. for now copy 100% of the animations to where they would
   have been saved had they been tracked, but lets keep that git ignored at the moment.
   the final format/folder structure should be mirrored to google drive and G, and
   previous paths should be archived in G (renamed to archived path) and in google drive
   deleted and replaced by the final folder structure) actually no need to touch the
   google drive for now only manage the files on G because I do not have free space
   anymore on google drive". G is the share.
2. Visibility: "Public, no collection". The repository stays public, the pages are
   corrected to say so, and the collection is not pushed to it.
3. The earlier set: "Unknown for now". The other 120 readmes of `earlier/`, the two
   alphabets among them, and the two of `others/` say `Source: unknown` with what is
   known. The two `43-yt-784dsKVrdjQ` files give the link read from their names, and
   their Notes say that no record says the file was made from it. A source the owner
   gives later goes into a readme, on the first computer and on the share.

The copy, the readmes, the share's copy and the archive of its old paths were done by hand
the same day, as "Where it stands" says. The owner's rulings of 2026-10-12 stay in the
change log as records.

On 2026-10-28 the owner corrected the first answer, in their words:

1. "lets make a correction for 46, we should git ignore only the heavy super long
   animations that weigh a lot, the small ones are ok to get tracked"
2. "include in big all files above 50 MB and git ignore them and move them in G to a
   folder called long, they keep their preview and hash catalog tracked data but the
   heavy animations themselves are in G, we also keep an untracked file called env and a
   tracked file called env.template, they contain a single const pointing to the
   fullpath where we keep all the animations (G's fullpath) used for emu one liner
   generations as well."
3. "gifs are acceptable alongside seeds."

These words stand where they differ from the answers of 2026-10-27. The small files are
tracked, and only the heavy ones are kept outside git, on the share and on the first
computer, with their previews and readmes tracked. "no collection" of the answer on
visibility gives way: the tracked collection is pushed with the repository, which stays
public. The answer on the earlier set stands. G is the share, and its collection the
share's folder artifacts/odrig/collection. `env.template`, `env` and the GIFs beside a
seed were done on `master` the same day, in 629bf57 and 941a464.

Later on 2026-10-28, in their words: "the G mirror should have 100% of files including
heavy files / the tracked mirror should have all the non-heavy files animations and
metadata, and for the heavy files just their metadata (preview, hash, expected path on the
sd card, what ever is necessary and has a runtime consumer, etc...)". "The two mirrors"
says what each holds, and the Definition Of Done checks that every animation is on the
share and every small one tracked.
