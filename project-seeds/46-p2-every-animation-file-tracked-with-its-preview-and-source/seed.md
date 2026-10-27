# Every animation kept with its preview and its source, outside git

## Summary

Every animation file the installation has been given is kept as the file itself, ODRG or
ODRGX, never as its JSON, in a collection outside git: the folder `collection/` of the
owner's checkout on the first computer, and its copy on the share. Beside each file sit
its preview, a copy of its GIF in `thumbnails/`, and a short readme of where it came from.
Only the previews are tracked, in `thumbnails/`, as seed 44 made them. The collection's
files are never committed and never pushed. The collection was built by hand on
2026-10-27, after the owner's answers: 359 files, 357 keys, 4.72 GB of animation files.
This seed asks for the rest. Git ignores `collection/` in every clone. The converter's
`thumbnail` subcommand gains `--beside`, which writes the preview beside each file. The
pages say where an animation the installation is given is kept, and that the repository
is public. Google Drive waits until it has room.

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
three (see "The Owner's Answers"). The animations are not tracked after all, only their
catalog of previews. The repository stays public, and the collection is not pushed to it.
The earlier set's sources stay unknown for now.

Before that day the installation's animations lived only in places git does not track:
the card, a copy of it in `scratch/`, show folders in `build/`, the share, and a folder of
the owner's Google Drive. The records of where they came from are in
`scratch/new-animations/` of the owner's checkout, which git ignores. The collection puts
the files in one place, each with its readme, on two disks: the first computer and the
share.

## Technical Constraints

- **Where it stands.** This was done by hand on 2026-10-27, after the owner's answers. It
  is the seed's starting state.
  - `collection/` was built in the owner's checkout, `/Users/koren/src/odrig`. Git
    ignores it there, and in the worktrees of that checkout, through
    `.git/info/exclude`, a local file that is not tracked. A clone elsewhere, the Windows
    computer's among them, has no such line. A worktree holds no `collection/` of its own.
  - It holds 359 animation files of 357 keys, 4,718,456,538 bytes (4.72 GB), each with
    `X.gif` and `X.md` beside it, and `collection/README.md`: 4,730,999,232 bytes in all.
    Every animation file is an ODRG file of 60 x 60. None is ODRGX.
  - Each `X.gif` is byte for byte the `thumbnails/<key>.gif` of its key.
  - The 359 readmes were written by one script, `write_readmes.py`, from the records
    below. 233 keys have a full source, a link from the records. 2 have a partial one, a
    link read from a name. 122 have none: `Source: unknown`. Four scripts written apart
    from it checked them, with 0 errors.
  - The folder was copied to the share, as the share's folder artifacts/odrig/collection,
    and every copy was read back. Then the share's old animation paths were moved, not
    deleted, into the share's folder artifacts/odrig/archived, with their relative paths:
    the 122 files of its root, and its folder `animations/` with `new animations` in it.
    The APK, the firmware and `photos/` stay where they are.
  - Google Drive was not touched.
- **What the collection holds.**
  - `collection/card/`: the 235 animation files of the card's folder `odrig`, at their
    paths, without its catalog, as `scratch/all-card-local/odrig` holds them: 2 at its
    root, `archive/` 5, `gifs/` 11, `long/yt-<id>/` 8 folders with 74, `reels/` 15,
    `science-in-8bit/` 108 and `youtube/` 20. The 2 at the root have the same bytes as two
    files of `youtube/`. They are kept, so that `card/` holds the card's paths.
  - `collection/earlier/`: the 122 files of the share's root, the owner's earlier set.
    They are 119 files of 43 originals numbered 01 to 43, in the variants `fit`, `crop`,
    `cropfit` and `zoom70`, with `alphabet_english.odrg`, `alphabet_hebrew.odrg` and
    `43-yt-784dsKVrdjQ_center60of256.odrg`.
  - `collection/others/`: the files with no place on the card, at first
    `1000313299.odrg` and `1000313581.odrg`. They were on the board's own storage before
    the session of 2026-10-25, and are found only in `scratch/board-2026-10-25/`.
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
    words. The move of the share's old paths into archived does not change it.
  - Notes: what the lines above cannot say, in words, or `none`.
  A readme names no folder of a computer, no mount point and no account of the owner. The
  share is "the share's folder artifacts/odrig", and Google Drive "the owner's Google
  Drive folder artifacts/odrig/animations". It holds no carriage return.
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
  reports, were made in a session's scratch
  folder, which the system may clear. They were copied on 2026-10-27 into
  `scratch/collection-readmes/` of the owner's checkout, with `build_collection.py`, which
  built the folder, and `mirror_g.py`, which made the share's copy and the archive. Git
  ignores `scratch/`. None of them is committed.
- **Git ignores the folder.** `.gitignore` gains the line `/collection/`, after `/tools/`.
  Every checkout then ignores the folder, a fresh clone and the Windows computer's clone
  among them, and a broad `git add` never stages a file of it. The line of the owner's
  `.git/info/exclude` may stay; it is local.
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
- **A later conversion.** It is added when it is handed to the owner: into
  `collection/card/` at the path it is to have on the card, or into `collection/others/`
  when it has none. A conversion that is only tried is not added.
  - The collection of the first computer is that of the owner's checkout. That checkout
    stays on the commit the owner runs, which may lack `thumbnail` and `thumbnails/`;
    today it lacks both. So the steps run in a worktree of `origin/master`, after `git
    fetch origin`, which names the collection by its path from the worktree:
    `../../collection` from a worktree two folders down, such as `scratch/<name>/`. On a
    computer without the collection, the folder is made in its checkout for the new file
    alone, and the path is `collection`.
  Its steps:
  1. Import and encode in the worktree's `build/`, as today. The JSON stays there.
  2. Copy `X.odrg` into `../../collection/card/` at its path on the card, or into
     `../../collection/others/`. A path the share's collection already holds with other
     bytes is not reused: the conversion gets a name of its own first.
  3. Run `node converter/odrig.js thumbnail ../../collection/card/<folder>/X.odrg
     --catalog thumbnails --card ../../collection/card --beside`, without `--card
     ../../collection/card` for a file of `others/`.
  4. Write `X.md` in the readme's shape.
  5. Commit `thumbnails/` only, by name, in the worktree on its branch:
     `thumbnails/catalog.js` and, for a new key, `thumbnails/<key>.gif`.
  6. Copy `X.odrg`, `X.gif` and `X.md` to the same place in the share's folder
     artifacts/odrig/collection.
  A file of the collection is never changed once added. A new conversion of the same
  media is a new file with a name of its own. `card/` keeps each file at the path it was
  given when it was added, and does not follow later changes to the card.
- **`collection/README.md`.** It is not a file of the repository. It is in the owner's
  checkout and on the share. It tells what the folder is, its three folders, the readme's
  shape and the steps above. Today its steps 3 and 4 run `thumbnail` and then copy the
  GIF by hand. Once `--beside` is on `master`, they become the one step above, and its
  sentence on `.git/info/exclude` says that every checkout ignores the folder, through
  `.gitignore`. Its copy on the share is replaced with it. It gives the steps in the form
  from a worktree, as above.
  - It is the one untracked file of the owner's that the seed's agent edits, as the seed
    asks. No other file of the collection is changed, and on the share only `README.md`
    of the share's folder artifacts/odrig/collection is replaced.
- **The decision and the records.**
  - In `docs/decisions.md`, "Animation formats", the sentence "The JSON source is
    committed for every animation, including those imported from video, and nothing else
    is committed in its place" changes. The JSON source stays what is committed for an
    animation of the bench or of a test. An animation the installation is given is kept
    outside git, in the collection, `collection/` of the first computer and its copy on
    the share, as its ODRG or ODRGX file with its preview and its readme beside it. Only
    its preview is tracked, in `thumbnails/`, and its JSON is not committed. The table's
    row for JSON frames, "The tracked, lossless source of each animation", and the
    paragraph on ODRGX, "The tracked source of a text or a clock is typed JSON", say "of
    the bench or of a test" the same way.
  - In "Scope and process", `docs/decisions.md:37-38`, "a private repository" becomes "a
    public repository", by the owner's answer of 2026-10-27. The same goes for
    `agent/working-rules.md:127`, "which is private", and `agent/getting-started.md:54`,
    "Clone the repository, which is private".
  - A dated entry goes at the end of the change log: the collection kept outside git, with
    its preview tracked and its JSON not committed; the remote public; the earlier set's
    sources unknown. It does not begin with "The repository has a remote": one entry
    only begins so (`tests/onboarding/test_rules.py:147-151`). The entries of 2026-10-12,
    on the JSON source and on the remote as private, stay as they are: the change log is
    only added to at the end.
  - `docs/drifts.md` gains an entry at its end, "Seed 46: the installation's animations,
    kept outside git". Its question: the decision committed every animation's JSON
    source, seed 10's answer committed an imported source in `animations/` up to 50 MB,
    and the pages called the remote private. Its answer: the owner's answers of
    2026-10-27, the collection outside git, and the remote public. Seed 44's answer that
    the previews of `thumbnails/` are the only GIFs tracked still holds.
- **The pages.**
  - `agent/animation-guide.md`, its table of where things go:
    - a new row, "An animation the installation is given", in `collection/`, at its path
      on the card or in `collection/others/`, with its preview and its readme beside it,
      and a copy on the share. Committed: "No." Git ignores the folder; only its preview
      is tracked, in `thumbnails/`. The row gives the steps above in short, the command of
      step 3 in full in its form from a worktree, and points to `collection/README.md`;
    - the import row becomes "A source made by an import for the bench or a test", still
      `animations/NAME.json` and "Yes";
    - its ruling in "How large sources get", that the JSON source is what is committed for
      every animation, says of the bench and of the tests.
    The guide names the files `NAME.odrg`, `NAME.gif` and `NAME.md`, as it names a source
    `animations/NAME.json`: the onboarding test reads `NAME` as any name, but `X.md` as a
    file that a clone must hold. It names `collection/README.md` in backticks and never
    links to it, since no clone holds it. It stays within its 200 lines; it has 199
    today, so the row takes the last one and the changed sentences keep their lines.
  - `agent/README.md:14`, the vocabulary's source, `docs/format.md:7` and
    `docs/format.md:342` say of the bench or of a test, as the decision does. The source
    of an animation of the bench or of a test is tracked; that of an animation the
    installation is given is not kept. The source's entry uses no word explained after
    it, such as collection. The guide's preview row says, on its line, that for an
    animation the installation is given the commit holds `thumbnails/` alone.
  - `agent/vocabulary.md`: a new word, collection, right after preview, in "The
    programs": every animation file the installation has been given, kept as the file
    that is played, with its preview and its readme beside it, in `collection/` and on
    the share; git ignores the folder, only the previews are tracked; nothing of the
    installation reads it. It uses no word explained after it, such as owner, seed or
    task. No entry before it uses the word.
  - `docs/converter.md`: `--beside` in the section "thumbnail", its usage line and an
    example.
  - `AGENTS.md`, under "What is coming": the commit of this rewrite changed its line for
    seed 46, which said the installation's ODRG files in git, to "**Every animation kept
    with its preview and its source, outside git**, seed 46: the installation's animation
    files with their GIFs and readmes, on the first computer and the share; only the
    previews tracked." The spec's only task on it is the one that sets the seed's state
    to `completed` and takes the line out, as `tests/onboarding/test_entry.py:140-152`
    requires.
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
  - `tests/onboarding/test_guide.py`: 8 rows in the table of where things go; the row of
    `collection/` answers No; `.gitignore` holds the line `/collection/`, and `git
    check-ignore -q collection/x` answers 0; the phrases it pins of the ruling, in the
    guide and in `docs/decisions.md`, follow the new words.
  - `tests/onboarding/test_vocabulary.py`: `WORDS` gains "collection" right after
    "preview".
  - `tests/onboarding/test_rules.py:124` pins "a private repository"; it pins "a public
    repository".
  - `tests/onboarding/support.py`: `collection/` and `../../collection/` join the paths a
    page may name although no clone holds it, beside `tools/` and `scratch/`
    (`looked_for`). The check of links does not use that list, so no page links into
    `collection/`.
  - The tests of the whole tree, the scan for the Wi-Fi password and the walk-through
    among them, list what git tracks or would track, so an ignored folder is not read.
    They do not change.
- **Google Drive.** Not now. The owner's Google Drive has no free space. When it has room,
  the owner's first words apply to it: the collection copied there in its final shape,
  and the Drive's old folder artifacts/odrig/animations deleted and replaced by it. That
  waits for the owner's word then, and is not part of this seed.
- **What stays.** The board, the firmware, the core, the emulator, the app, the APK, every
  command and every reply. `thumbnails/` and its 424 previews, byte for byte. The card's
  catalog. `pack`, which takes JSON sources: a show of collection files is made with
  `decode` into `build/`, then `pack` from there. The collection's animation files, GIFs
  and readmes as they were built; of the collection, only `collection/README.md` changes.

## Required Behavior

1. Git ignores `collection/` in every clone, through `.gitignore`. No file of it is
   tracked, and none is pushed.
2. `node converter/odrig.js thumbnail FILE... --catalog DIR --beside` writes `X.gif`
   beside each file it does not pass over, a copy of the catalog's GIF of its key, once
   the mapping is written. `--beside` without `--catalog` is refused with status 2, and
   nothing is written.
3. A later conversion is added as the steps say: one command makes its preview in
   `thumbnails/` and beside it, only `thumbnails/` is committed, and the three files go to
   the share's collection.
4. `docs/decisions.md`, its change log and `docs/drifts.md` say what is committed now and
   that the remote is public. `agent/working-rules.md` and `agent/getting-started.md` say
   public too.
5. The guide's table has the row of the collection with its steps, the vocabulary has the
   word collection, and `docs/converter.md` has `--beside`.
6. `collection/README.md`, in the owner's checkout and on the share, gives the steps with
   `--beside`.
7. No byte of `thumbnails/` changes, and nothing of the installation reads the collection.

## Definition Of Done

1. All test suites that need no board and no phone pass. The converter's suite checks
   `--beside` as "Tests that change" says. The onboarding suite passes with the guide's
   eighth row, `git check-ignore` on `collection/`, the word collection, and the public
   remote.
2. A check on real files, in the agent's worktree: the 11 files of `collection/card/gifs/`
   of the owner's checkout, 3,338,428 bytes, are copied into `build/beside/card/gifs/`,
   and a copy of `thumbnails/` into `build/beside/thumbnails/`. `thumbnail` is run on them
   with `--catalog build/beside/thumbnails --card build/beside/card --beside`. Each GIF it
   writes equals the collection's `X.gif`, and the copy of the catalog keeps the bytes of
   `thumbnails/`.
3. `collection/README.md` of the owner's checkout gives the steps with `--beside`, and its
   copy on the share has the same bytes.
4. A read of the share, which changes nothing there, finds its folder
   artifacts/odrig/collection with the 359 animation files, their 359 GIFs and 359
   readmes, and `README.md`, of the same bytes as the owner's checkout; and its folder
   artifacts/odrig/archived with the 122 files and `animations/`. AppleDouble files `._*`
   are not counted. If the copy or the move had not ended, the report says so, and the
   agent moves nothing itself. If the share is not mounted, the agent does not mount it;
   the report says so, and the copy of `README.md` and the read wait.
5. `scratch/collection-readmes/` of the owner's checkout holds the script, its
   `inventory.json`, the four checks with their outputs, `build_collection.py` and
   `mirror_g.py`, untracked; the agent checks that they are there and changes none.
6. The owner is told in words: what is not in the collection and why; that 122 keys have
   no known source; that the collection is in no clone, only on the first computer and
   on the share; that the records and the script that wrote the readmes stay untracked on
   the first computer; that the card itself and the board's own storage since 2026-10-25
   were not read for the collection; that a file a phone uploads to the board does not
   reach the collection; and that Google Drive waits until it has room. No board is
   needed.

## Open Questions

None. The owner answered the three questions of the seed as first written, on 2026-10-27;
see "The Owner's Answers". Google Drive is no question: the owner said to leave it for
now, since it has no free space. When it has room, the copy there and the replacement of
its old folder wait for the owner's word.

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
