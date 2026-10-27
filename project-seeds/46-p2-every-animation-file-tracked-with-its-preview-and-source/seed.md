# Every animation file tracked with its preview and its source

## Summary

Every animation file the installation has been given is tracked in the repository as the
ODRG or ODRGX file itself, never as its JSON, in a new folder at the top, `collection/`.
Beside each file sit its preview, a copy of its GIF in `thumbnails/`, and a short readme
that says where it came from: the link, the uploader, the title, the part of the video and
how it was converted. Where nothing was recorded, the readme says the source is unknown
and gives what is known. The folder starts with 359 files, 357 different ones: 4.69 GB
stored once, 4.72 GB of animation files in a checkout that holds them. `collection/card/`
holds the animation files of the card's folder `odrig` at their paths, without its
catalog. `collection/earlier/` holds the owner's earlier set, and `collection/others/` two
files found on the board. That is 357 of the 424 animations known: the 57 test files stay
where git tracks them today, and the 10 files that the generators write are left out.
Nothing of the installation reads the folder. The converter's `thumbnail` subcommand gains
an option that writes the preview beside a file, and a new test keeps the folder in its
shape. For these files, the decision that every animation's JSON source is committed gives
way. Whether the files go into plain git or into Git LFS is the owner's answer to the
first open question. Until then the spec is written for Git LFS, the recommended answer.

## Priority

- `P2`

## Depends On

- Seed 44, for the key of an animation, the CRC-32 and the size of its file, for
  `thumbnails/` with the preview of each of the 424 animations known, and for the
  converter's `thumbnail` subcommand with `--catalog` and `--card`.
- Seeds 35, 38 and 41, for the card: its folder `odrig` with sub-folders, the rule of its
  names and its limits.
- Seeds 35, 38, 41 and 44 are merged on `master`. Only their checks on the board, and on a
  phone, keep them in progress, and this seed needs neither.
- The converter, `converter/`, whose `decode` gives a JSON source back from an ODRG file.

## Product Context

On 2026-10-27 the owner asked, in their words: "I want all the animation tracked, would it
be possible? and per animation file a readme where it was taken from if possible to back
track". After an assessment, the owner asked whether ODRG is lossless like JSON, and how
much tracking ODRG only saves. Then: "add a seed to save only the odrg + preview thumbnail
per each next to it".

The answers given were these. ODRG is lossless in what it shows: `decode` gives back the
same picture at every millisecond (`docs/converter.md`, "decode"; `docs/format.md`). The
JSON text comes back byte for byte only when no two frames in a row are equal, since the
encoder merges such frames. Tracking ODRG only saves about 41 GB: 4.7 GB of ODRG against
an estimated 46 GB of JSON.

The assessment gave the owner these figures. There are 424 different animation files by
CRC-32 and size, 4.69 GB in all. The largest is 83.7 MiB. 47 are above 50 MiB, where
GitHub warns, and none is above 100 MiB, where GitHub blocks a file. GitHub asks that a
repository stay ideally under 1 GB, and strongly recommends under 5 GB. Git LFS on a free
personal account has 10 GiB of storage and 10 GiB of downloads a month.

Today the installation's animations live only in places git does not track: the card, a
copy of it in `scratch/`, show folders in `build/`, the owner's network share and a folder
of the owner's Google Drive. The records of where they came from are in
`scratch/new-animations/` on the first computer, which git ignores. A lost disk would lose
that trail. The rule says the JSON source of every animation is committed, but these were
never committed: one of their JSON sources is kept, 11.4 times the size of its ODRG
(`scratch/new-animations/sources/sci8bit-defdjatcvsr_fit.json`, 29,194,970 bytes, against
2,562,157).

## Technical Constraints

- **What the collection holds.** The animation files the installation has been given, at
  the start 357 keys in 359 files, all of them 60 x 60:
  - `collection/card/`: the 235 animation files of the card's folder `odrig`, at their
    paths, without its catalog, as `scratch/all-card-local/odrig` holds them today: 2 at
    its root, `archive/` 5, `gifs/` 11, `long/yt-<id>/` 8 folders with 74, `reels/` 15,
    `science-in-8bit/` 108 and `youtube/` 20. The 2 at the root have the same bytes as two
    files of `youtube/`. They are kept, so that `card/` holds the card's paths; git keeps
    identical bytes once.
  - `collection/earlier/`: the 122 files at the root of the share's folder
    `artifacts/odrig`. They are the owner's earlier set, 119 files of 43 originals
    numbered 01 to 43 in the variants `fit`, `crop`, `cropfit` and `zoom70`, together
    with `alphabet_english.odrg`, `alphabet_hebrew.odrg` and
    `43-yt-784dsKVrdjQ_center60of256.odrg`.
  - `collection/others/`: `1000313299.odrg` and `1000313581.odrg`. They were on the
    board's own storage before the session of 2026-10-25 and are found only in
    `scratch/board-2026-10-25/`.
  The task that asked for this seed says that the installation's card holds the 235 in
  `odrig/` and the 122 in `odrig-earlier-2026-10-27/`. The card was not at hand to check.
- **What it does not hold.**
  - No JSON. No JSON source of a collection file is committed, now or for a later one.
  - The 57 tracked test files, of `test-animations/` and the valid vectors of
    `tests/vectors/`, stay where they are, with their JSON or `build.mjs` beside them.
    Their tests read them there, and 26 of them are not 60 x 60.
  - The 10 files that the generators write: `hello.odrg` 4 times, `dvd.odrg` 3 times and
    `dense.odrg` 3 times, each with other bytes, 2,207,850 bytes in all. Six are made
    again byte for byte by today's generators and mappings. The three of 60 x 30 are made
    again from `mapping/legs-10.json` as it was before commit `70c9a69`, which removed
    it. The `hello.odrg` of 60 x 20 needs `build/lane/show/mapping.json`, which git does
    not track, so it cannot be made again from the repository. They are left out because
    what a generator writes is not committed: the guide's table says
    "No. The generator is." of the sources a generator writes, and puts ODRG files in
    `build/`. 7 of them are not 60 x 60. Their previews stay in `thumbnails/`.
  - The 2 broken test files of the board's session of 2026-10-25, `huge-tail-test.odrg`
    and `broken-test.odrg`, which the reader refuses and which have no preview.
  - The 34 trial files of agents, found only in worktrees and in `core/build/`.
  So the 357 keys of the collection, the 57 test files and the 10 files of the generators
  are the 424 keys of `thumbnails/catalog.js`. The report tells the owner in words which
  files are not in the collection, and why.
- **Lossless.** A collection file keeps the same picture at every millisecond as the JSON
  it was made from. `decode` writes a JSON source from it into `build/` whenever one is
  needed, frames in a row with the same picture merged into one. Three files decoded and
  encoded again came back byte for byte; the others were not tried.
- **The folder.** `collection/`, at the top of the repository.
  - Not `animations/`. The converter's stored answers hash the tracked files of every
    folder a stored command names, and the tests of `pack` name `--sources animations`.
    One tracked ODRG there made 11 of the 167 tests of `pack.test.js` fail in a trial in
    a scratch clone. The folder also holds the bench's two JSON sources.
  - Not `test-animations/`, whose every file the preview test makes again, and not
    `thumbnails/`, which holds the mapping and the GIFs only and goes into the APK.
  - Not a name with the words "library" or "catalog", which the project already uses for
    other things.
  - No tool of the installation reads the folder. The emulator, `app.py serve` and the
    APK's build take only `thumbnails/`. `pack` reads only the JSON sources a show names
    and refuses an ODRG. `fw.py install-show` takes a show folder made by `pack`. The
    board reads only the card's folder `odrig`.
- **Names.** Every file keeps the name it has on the card or the share. The longest name
  is 48 bytes, and the deepest is two folders down in `card/`. The largest folder is
  `earlier/`, with 122 files; the largest of `card/`, `science-in-8bit/`, has 108.
  - A file of `card/` keeps the card's rule of names, `name_allowed` of
    `odrig/catalog.py` as `docs/catalog.md` gives it, for its path from `collection/card`.
    A file of `earlier/` or `others/` lies directly in its folder, and its name keeps the
    same rule.
  - No two animation files in one folder have names that are equal once their endings
    are taken off and their letters are made lower case, and none is named `README`.
  - No two paths of `collection/` differ only in case. No part of a path, with everything
    from its first dot taken off and in any case, is a device name of Windows: CON, PRN,
    AUX, NUL, COM1 to COM9 or LPT1 to LPT9. Every animation file ends in `.odrg` or
    `.odrgx` in lower case.
  - `40-64ub7Rv_fit.odrg` is in `earlier/` as the share names it.
    `40-64ub7rv_fit.odrg` of `build/owner-show-full`, the show the board was given on
    2026-10-16, has the same bytes and differs only in case, so it is not added: macOS
    and Windows would see one file.
  Every file is a real copy. No symbolic link is tracked, so that Windows checks out
  files.
- **Beside each file.** For `X.odrg` or `X.odrgx`:
  - `X.gif`, byte for byte the `thumbnails/<key>.gif` of its key, copied and never made
    again. Git keeps one object for identical bytes (seen in the trial clone: one blob for
    both paths), so the GIFs add nothing to the history and 12.2 MB to a checkout.
  - `X.md`, its readme.
  The folder holds nothing else but `collection/README.md`. A card takes only `.odrg` and
  `.odrgx` files and passes over the rest.
- **The readme.** Markdown in UTF-8, with LF line ends: one title and one uploader are not
  ASCII. It has a title line, an empty line and then 16 lines in a fixed order:
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
  Every line is always there, and `unknown` stands for what is not known:
  - TITLE: the title, else the uploader and the media id, else the file's name.
  - Animation: read from the file; KIND is frames, text or widget, as `check` names it.
  - Source: the link, or `unknown`. Platform: YouTube, Instagram, Giphy, Tenor, itch.io,
    Internet Archive, or `unknown`.
  - Uploader: the name the platform shows, or `unknown`. An uploader recorded as an
    e-mail address is written as `unknown`, and the link stays.
  - Title and Media id: as recorded, or `unknown`.
  - Part: `whole`, `from S s for D s`, `group N of M, from S s for D s`, or `unknown`.
  - Crop: `none`, the crop `W:H:X:Y` of the cut, or `unknown`.
  - Fit: the converter's `--fit`, which is fill, fit or stretch, and the mapping; or
    `unknown`.
  - Made with: the converter's subcommands that the job's script runs, its files given as
    words in capitals, such as `node converter/odrig.js import MEDIA FRAMES.json
    --mapping mapping/legs-20.json --fit fit`, then `node converter/odrig.js encode
    FRAMES.json X.odrg`. Any other step is said in words: the download, the crop, the cut
    or the join of pieces. Else `unknown`.
  - Converted and Added: `YYYY-MM-DD`; Converted may be `unknown`. Found: where the file
    was when it was added, in words.
  - Notes: what the lines above cannot say, in words, or `none`.
  The collection's test checks the shape: line 1 is `# ` and a title that is not empty;
  line 2 is empty; then exactly these 16 lines in this order, each `- Label: value` with a
  value that is not empty; then the end of the file. The lines File and Key are those of
  its file.
  - A readme names its file, not its path, so the two copies at the root of `card/` get
    the same readme as their twins in `youtube/`.
  - It names no folder of a computer, no mount point and no account of the owner. The
    share is "the share's folder artifacts/odrig", and Google Drive is "the owner's Google
    Drive folder artifacts/odrig/animations". The path of the Drive's mirror holds the
    owner's e-mail.
  - It holds no carriage return, which `tests/emulator/test_build_script.py` checks of
    every tracked Markdown file. It is a record: it copies a title as its source gives it.
    So `collection/` joins the records that the tests of three classes of
    `tests/converter/test_docs.py` pass over. The 868 texts of the records, every name,
    kind, id, link, title, uploader and note, were checked against those tests: none
    breaks them.
- **Where the first readmes come from.** The records of the first computer in
  `scratch/new-animations/`:
  - `inventory-sources.json`: its map `src` gives 159 files with kind, id, link and
    uploader (123 from Instagram, 20 from YouTube, 11 GIFs, 5 from the Internet Archive),
    and its map `folders` gives the 8 long videos with link, title and uploader;
  - the job lists `*.txt`, the logs `*.log` with the name, size, cut and crop of 158 of
    the 159 single files, and `picks-2026-10-26.json`, with titles. The 159th,
    `sci8bit-defdjatcvsr_fit.odrg`, has its job line and its kept JSON.
  Every one of the 233 keys of `card/` has its link there. The file `yt-<id>_NN.odrg` of a
  long video is its group NN of 15 minutes, from (NN - 1) x 900 s (`long/run_long.sh`,
  and `yt/run_groups.sh` for `yt-t6jlhqnxryk`).
  - A link is taken from the records and never made from a name: the names of the
    conversions are lower case, and `yt-t6jlhqnxryk` stands for the video `t6jlhqNxRYk`.
  - The one exception is the two files `43-yt-784dsKVrdjQ_fit.odrg` and
    `43-yt-784dsKVrdjQ_center60of256.odrg`. They have in their names `784dsKVrdjQ`, which
    is a YouTube video (oEmbed, 2026-10-27: "Interstellar Gargantua Black Hole | 1 Hour
    Full HD Live Wallpaper", Kalakaar FX). Their readmes give its link. Their Notes say
    that it was read from the name, and that no record says the file was made from it.
    Their Platform is YouTube and their Media id `784dsKVrdjQ`. Their Title and Uploader
    are those oEmbed gave on 2026-10-27.
  - A log line belongs to a file when its name and its size in bytes both match. The block
    of the log that ends in that line, from its `==` line on, gives Crop and Part. Crop is
    `W:H:X:Y` from a line "cutting to crop=W:H:X:Y", and otherwise `none`:
    `convert_links.py` and `convert_reels.py` crop only when the job asks, and say "no
    bars found to cut; the whole picture is used" when they find nothing to cut. Part is
    `whole`, since no job of these logs gives `start=` or `duration=`. Converted is then
    2026-10-26, the day all the logs `*.log` ran. Where no line matches, Crop, Part and
    Converted are `unknown`.
  - That rule is for the 159 single files. The five Phosphor files have one line each in
    `phosphor-2026-10-26.log`, with no block above it, so their Crop and Part are
    `unknown`.
  - A group of a long video is logged by its tag, such as `ujejhzrmhcc-g01`, or by its
    number in `yt/log/run.log`, not by its file's name, so no line matches it. Its Part is
    the group as above; the last group runs to the end of the video, or of its loop. D is
    900 s, except for the last group, whose D is the length that its "cutting" line in
    `long/log/run.log` gives, such as 209.870 s. The lines of `yt/log/run.log` give none,
    so D of group 41 of `yt-t6jlhqnxryk` is the length of its file, 10.64 s. Its Crop is
    `none`: neither `long/run_long.sh` nor `yt/run_groups.sh` crops. Its Converted is the
    date of the line that cuts the group, in `long/log/run.log`, or in `yt/log/run.log`
    for `yt-t6jlhqnxryk`.
  - Made with is written from the job's script, since the commands were not logged, and
    Notes say so. `convert_reels.py` was changed at 01:53 on 2026-10-26, after the job of
    `reels-2026-10-26.log` ran, so the Notes of its 14 files also say that their Made with
    is read from the script as it is now.
- **What is known of the rest.** No source was recorded for 122 keys: 118 of the earlier
  set, the two alphabets and the two numbered files. What is known:
  - where each file was found: the earlier set on the share's root, and 115 of its 122
    files also in the owner's Google Drive folder, which the owner pointed to on
    2026-10-15;
  - the date of each file on the share: 2026-10-12 for 115, 2026-10-15 for 5 and
    2026-10-16 for 2. These are dates on the share, not dates of a conversion;
  - its number in the earlier set, and its variant as the name says.
  Each of their readmes says `Source: unknown`. In every readme of `earlier/`, the two
  `43-yt-784dsKVrdjQ` files included, Fit and Converted say `unknown`. Its Found is "the
  share's folder artifacts/odrig", followed for the 115 also in the Drive by "and the
  owner's Google Drive folder artifacts/odrig/animations". Its Notes give the number and
  the variant word of the name where it has them, the variant being fit, crop, cropfit,
  zoom70 or center60of256 "as the name says", and "the file's date on the share:
  YYYY-MM-DD". In `others/`, Found is "the board's own storage, read on 2026-10-25". No
  reading of a name's words, such as `tenor`, `whatsapp`, `slowtv` or a date, is written
  as a fact. A source the owner gives later goes into the readmes in a commit of its own.
- **Who writes the readmes.** The tool cannot know a source, so it writes no readme. The
  first 359, 357 different, are written once from the records above, by a script that
  stays in `scratch/` with the records it reads. A later readme is written by whoever
  adds the file, in the shape that `collection/README.md` gives, and the collection's test
  checks the shape.
- **The converter.** `thumbnail` gains the option `--beside`, so that adding a preview
  beside a file is one command on every computer. It goes with `--catalog` only; without
  it, it is a mistake of the command line, status 2. After a file's key is in the
  catalog, the subcommand writes `X.gif` beside the file, a copy of the catalog's
  `<key>.gif`, in place of a file of that name. `X` is the file's name without its ending
  when that ending is `.odrg` or `.odrgx` in any case. A file with neither ending gets
  its whole name followed by `.gif`. A file it passes over gets none. A GIF that cannot be
  written ends the run with `cannot-write` and status 1, as a GIF of the catalog does. It
  still writes nothing on standard output. No subcommand is added, and nothing is added to
  the board's command list.
- **Plain git or Git LFS.** The owner's answer to the first open question decides. The
  layout, the files beside each one and the readmes are the same either way. The
  collection's test finds out which answer holds, as its paragraph below says.
  - With Git LFS: only the animation files of `collection/` go to LFS.
    - `.gitattributes` gains `*.odrgx binary` beside `*.odrg binary`, then the lines
      `collection/**/*.odrg filter=lfs diff=lfs merge=lfs -text` and the same for
      `*.odrgx` after them, so that they win. Its first line stays `* -text`. The GIFs,
      the readmes and the 139 tracked test files, 78 ODRG and 61 ODRGX, stay in plain
      git, since the tests read the test files' bytes.
    - A committed `.lfsconfig` sets `lfs.fetchexclude` to `collection/**`. A clone, the
      Windows computer's included, then downloads none of the collection's files unless
      asked. `collection/README.md` clears that exclusion for one run of the command that
      fetches: `git lfs pull -I "collection/card/reels/**" -X ""` for one folder, and
      `git lfs pull -I "collection/**" -X ""` for all.
    - Whether git-lfs reads the committed `.lfsconfig` during a clone's first checkout is
      not verified. It is checked after the first part of the fill, 16,530,716 bytes, is
      pushed, and before the second is: a fresh clone from GitHub, made with git-lfs,
      holds pointers in `collection/`, and then
      `git lfs pull -I "collection/others/**" -X ""` fetches the two files of `others/`
      byte for byte in it. A clone that cannot fetch at all does not pass. If the clone
      downloads the collection's files despite `.lfsconfig`, `collection/README.md` tells
      a reader to clone with `GIT_LFS_SKIP_SMUDGE=1`, the definition of done checks that
      form instead, and a drift entry records it. No owner question is needed for that.
    - git-lfs is not installed on the first computer: `git lfs version` answers "git:
      'lfs' is not a git command". Nothing is installed in the system. One pinned release
      for macOS on arm64, its SHA-256 checked against the release's `sha256sums.asc`, is
      unpacked into the `tools/` of the owner's checkout. The repository's own git
      configuration sets `filter.lfs.clean`, `filter.lfs.smudge` and `filter.lfs.process`
      to its full path. Nothing global changes.
    - git-lfs writes four hooks: pre-push, post-checkout, post-commit and post-merge. As
      git-lfs writes them, they look for git-lfs on the PATH and stop with status 2 when
      it is not there (git-lfs's `lfs/hook.go`). A push, a checkout and
      `git worktree add` would then fail. The hooks are in the common `.git/hooks`, which
      every worktree shares. So the hooks call git-lfs by the same full path, and a push
      from any shell finds it.
    - The global configuration of the first computer already defines the `lfs` filter as
      required (`~/.gitconfig`). So a git that cannot run git-lfs refuses a collection
      file instead of adding it whole. On a computer without that configuration, git adds
      the file whole without a word, and pushed history is never rewritten. The
      collection's test therefore refuses an animation file of `collection/` that git
      holds as anything but an LFS pointer, so the suites, run after the files are staged
      and before the commit, catch it before anything is pushed.
    - A test that makes a clone, the walk-through's fresh copy among them, runs git with
      `GIT_CONFIG_GLOBAL` and `GIT_CONFIG_SYSTEM` set to the null device: for the clone,
      and for every git command it runs in the clone. Its clone then holds the
      collection's pointers whatever the computer has, which is what
      `tests/walkthrough/support.py:13` already promises.
    - Git for Windows includes Git LFS; whether it is turned on in the owner's Windows
      git is not verified.
    - A worktree of the first computer may also check out the whole files, from the store
      it shares; not tried.
    - A file of up to 2 GB is taken on the free plan.
  - With plain git: the files are plain git objects.
    - Every full clone downloads all of them and every later one, for good.
    - Each push stays under GitHub's limit of 2 GB, which the fill's parts below keep.
    - The 47 files above 50 MiB each give GitHub's warning at the push.
    - GitHub blocks a file larger than 100 MiB, and its page of limits says 100 MB. The
      collection keeps to the stricter reading: a file of 100,000,000 bytes or more is
      not added. A conversion that would make one is told to the owner in words, since
      the groups of 15 minutes are the owner's rule.
  - Until the owner answers, the spec is written for the recommended answer, Git LFS.
    The tasks that do not depend on the answer come first: `--beside`, the collection's
    test, the other tests and the pages. One task is the owner's answer to the first two
    open questions, asked in words. Its commit ticks its checkbox and records the answers
    in a dated entry at the end of the change log of `docs/decisions.md`. The tasks that
    set up Git LFS, fill the collection and push it come after that task. The script that
    writes the readmes is made in the first task of the fill, and each task of the fill
    commits the readmes of its part. If the owner answers plain git, the tasks that set up
    Git LFS are marked in `tasks.md` as not needed by the owner's answer, a drift entry
    records it, and the rest stands as written. The commands that fetch, and the advice to
    fetch `collection/card` before a card is filled from it, go into
    `collection/README.md` in a task that sets up Git LFS. So under plain git the README
    has none.
- **A file is added once.** A collection file is the file the installation was given,
  and it is never changed once pushed. A new conversion of the same media is a new file
  with a name of its own.
  - `collection/card/` holds each file at the path it had on the card when it was added,
    and does not follow later changes to the card. A file taken off the card, or moved on
    it, stays where it is in `card/`.
  - A new file whose path on the card is already taken in `card/` by other bytes is not
    added: the conversion is given a name of its own before it goes onto the card.
  - So a card made from `card/` holds every file the card has held, not the card of
    today. The collection's test counts no files or folders of `card/` against a card's
    limits.
  Under LFS every pushed version counts whole in the storage, for good; under plain git it
  stays in every full clone.
- **Size.** The collection's test refuses a file larger than the host takes: under Git
  LFS one above 2,000,000,000 bytes, otherwise one of 100,000,000 bytes or more. A group
  of 15 minutes of a busy video can pass 100 MiB: a dense 60 x 60 clip takes 138,377
  bytes a second compressed (`docs/decisions.md`), so 124,539,300 bytes for 900 s. That
  is a worst case: the largest group so far is 70.6 MB, and the largest file 87.7 MB.
  GitHub enforces 2 GB for one push. Whether that counts LFS uploads is not verified, so
  the collection is pushed in the same parts either way.
- **Filling it.** The files are read where they live and never changed there:
  - `scratch/all-card-local/odrig` for `card/`;
  - the root of the share's `artifacts/odrig` for `earlier/`, the share mounted, its
    AppleDouble files `._*` left out. Four of its files were found nowhere else on this
    computer or the Drive's mirror: `41-whatsapp-sticker-2026-10-12_fit.odrg`,
    `42-kaleidoscope-slowtv_fit.odrg` and the two `43-yt-784dsKVrdjQ` files;
  - `scratch/board-2026-10-25/` for `others/`.
  These `scratch/` folders, like `scratch/new-animations/`, are those of the owner's
  checkout, not of the agent's worktree. If the share is not mounted when the fill starts,
  the agent does not mount it: it asks the owner in words, and the first part of the fill
  waits. The key of each copy is checked against `thumbnails/catalog.js` before it is
  staged. The GIFs are written by `thumbnail` with `--beside`. Every name
  `thumbnail --catalog thumbnails --card collection/card` gives the 359 files is already
  in the mapping (checked), so filling the collection changes no byte of `thumbnails/`.
  Files are staged by name. The fill is five tasks, one commit each. Each commit holds the
  animation files of its part with their `X.gif` and `X.md`, and is pushed on the seed's
  branch before the next is made:
  1. `collection/earlier/` and `collection/others/`;
  2. `collection/card/` outside `long/`;
  3. the seven folders of `card/long/` other than `yt-t6jlhqnxryk/`;
  4. groups 01 to 20 of `card/long/yt-t6jlhqnxryk/`;
  5. groups 21 to 41 of it.
  Each holds less than 2,000,000,000 bytes of new files: the largest part, the third,
  holds 1,358,244,469. The branch reaches `master` as the working rules say.
- **A later conversion.** It is added when it is put onto the card or onto the board's
  own storage, not before. A conversion that is only on the share, or only tried, is not
  added. The steps, which `collection/README.md` gives:
  1. Import and encode in `build/`, as today.
  2. Copy `X.odrg` into `collection/card/` at its path on the card, or into
     `collection/others/` when it goes onto the board's own storage.
  3. Run `node converter/odrig.js thumbnail collection/card/<folder>/X.odrg --catalog
     thumbnails --card collection/card --beside`, without `--card` outside `card/`.
  4. Write `X.md`.
  5. Make one commit of `X.odrg`, `X.gif`, `X.md`, `thumbnails/catalog.js` and, for a new
     key, `thumbnails/<key>.gif`.
  The JSON stays in `build/`.
- **The collection's test.** A new test file of the converter's suite,
  `converter/tests/collection.test.js`:
  - takes the files of `collection/` that git tracks or would track:
    `git ls-files --cached --others --exclude-standard -z -- collection`. Where git
    cannot list them, the test is skipped, as `library.test.js` does;
  - checks that every animation file has `X.gif` and `X.md` beside it, and that the
    folder holds nothing else but `collection/README.md`;
  - checks that `X.gif` equals `thumbnails/<key>.gif`, and that the key is in
    `thumbnails/catalog.js` with the file's name: its path from `collection/card` in
    `card/`, else its own name;
  - checks the readme's shape, and the names as "Names" says;
  - checks that every file is 60 x 60 by its header, and keeps the size rule.
  The answer is Git LFS when `git check-attr filter` gives `lfs` for the collection's
  animation files. Then the blob in git's index for each animation file git tracks must
  be a pointer, and the size rule is that of Git LFS; otherwise it is that of plain git.
  When the file in the working tree is a pointer, its key is the `Key` line of its
  readme. The pointer's size must equal the key's size, and `X.gif` must equal
  `thumbnails/<key>.gif`. The CRC-32 and the header's 60 x 60 are not checked then.
  Keying 4.7 GB takes about 10 s with a warm disk cache, an estimate from 506 MB a second
  measured on 210 MB; a check in Python keyed them in 5.2 s. The report gives the test's
  time.
- **Other tests that change.**
  - `converter/tests/library.test.js` allows tracked GIFs at `thumbnails/<key>.gif` and as
    `collection/**/X.gif` beside its `X.odrg` or `X.odrgx`. MP4 and MOV stay none.
  - `tests/onboarding/test_guide.py` expects 8 rows in the guide's table of where things
    go. The row of `animations/NAME.json` stays Yes. The words of the ruling on JSON
    sources that it pins change with the guide and the decision.
  - `tests/onboarding/test_vocabulary.py`: `WORDS` gains "collection" right after
    "preview", in the group "The programs". Its definition uses no word explained after
    it. The entries before it, source, JSON frames, ODRG and preview, use the word
    collection only as `collection/` in backticks.
  - `tests/converter/test_docs.py`: `collection/` joins `RECORDS` of `TheTenLegFile`,
    `OneConverter` and `TheTarget`, since its readmes record titles and names as their
    sources give them.
  - The scan of every tracked file for the Wi-Fi password, in
    `tests/firmware/test_wifi_settings.py`, three passes, reads the collection's readmes
    and passes over its animation files and GIFs, which the converter writes. Each pass
    would otherwise read 4.7 GB more.
  - The walk-through: its fresh copy, `tests/walkthrough/support.py`, and its check that
    the copy holds what git tracks, `tests/walkthrough/test_fresh_copy.py`.
    - Every git command they run, the clone among them, runs with `GIT_CONFIG_GLOBAL` and
      `GIT_CONFIG_SYSTEM` set to the null device. The commands of the pages that the
      walk-through runs in the copy keep the caller's environment.
    - For an animation file of `collection/`, both compare the blobs of the two indexes,
      not the bytes of the files. A file whose blob differs, such as one staged and not
      committed, is written into the copy from its blob. Under Git LFS that blob is its
      pointer.
    - Under plain git each run copies about 4.7 GB of objects and checks out 4.7 GB of
      files beside them, about 9.4 GB in a temporary folder, an estimate. The converter's
      suite that it runs in the copy keys those files again. This cost is accepted.
  - `tests/onboarding/support.py` does not change. The guide gives no `cp` and no
    `git lfs` command, which it does not know. It points to `collection/README.md`, which
    is no page of the onboarding suite.
  - A page for newcomers may name in backticks only what the repository holds
    (`tests/onboarding/test_pages.py:77-81`). So `collection/README.md` is committed
    before a page names `collection/`.
- **The decision and the records.**
  - In `docs/decisions.md` the sentence "The JSON source is committed for every animation,
    including those imported from video, and nothing else is committed in its place"
    changes. The JSON source stays what is committed for an animation of the bench or of a
    test, and the typed JSON for a text or a clock of the bench or of a test. An animation
    the installation is given is committed as its ODRG or ODRGX file in `collection/`,
    with its preview and its readme beside it, and its JSON is not committed. A text or a
    clock the installation is given is in `collection/` the same way, as its ODRGX file
    with its preview and its readme, and its typed JSON is not committed. The table of
    formats says so for JSON frames, the custom binary format and the GIF's second role.
    Its paragraph on ODRGX, and `docs/format.md` on the JSON source of a text, say the
    same: typed JSON is the tracked source of a text or a clock of the bench or of a test.
  - A dated entry goes at the end of the change log. The entries of 2026-10-12, in which
    the owner ruled that the JSON source stays the one thing committed, and asked whether
    ODRG could replace it, an idea noted as not planned, stay as they are.
  - `docs/drifts.md` gains an entry at its end that gives way to two earlier answers:
    that the previews of `thumbnails/` are the only GIFs tracked (seed 44, which had
    already replaced "no media file is tracked"), and that an imported source is
    committed in `animations/` when it is at most 50 MB (seed 10). Seed 44's sentence
    that the JSON decision stays is a record and does not change.
- **The pages.**
  - `docs/format.md`: JSON frames is the tracked source of the animations of the bench and
    of the tests; a collection file is tracked as itself.
  - `agent/vocabulary.md`: source, JSON frames, ODRG and preview, and a new word,
    collection, after preview.
  - `agent/README.md`: the converter turns a video or a GIF into a source, which git
    tracks for the bench and the tests.
  - `agent/working-rules.md`: nothing fetched or built is committed, apart from the files
    of `collection/`.
  - `agent/animation-guide.md`, its table of where things go:
    - a new row, "An animation the installation is given | `collection/`, at its path on
      the card or among the others, with its preview and its readme beside it | Yes: its
      ODRG or ODRGX file, never its JSON; see `collection/README.md`.";
    - the import row becomes "A source made by an import for the bench or a test |
      `animations/NAME.json` | Yes. Keep it to 50 MB or less; see the next section.";
    - the `build/` row says "ODRG files other than the collection's".
    The steps of a later conversion are in `collection/README.md` only, and the guide
    points there. Its ruling on sources changes with the decision. It stays within its
    200 lines; it has 199 today.
  - `docs/converter.md`: `--beside`.
  - `collection/README.md`: what the folder is, its three folders, the readme's lines,
    and the steps to add a file. One sentence says that a card takes at most 256 files
    and 32 sub-folders, and that a card made from `card/` holds every file the card has
    held. Under Git LFS it gives the commands that fetch, and says to fetch
    `collection/card` with them before copying it onto a card.
  - `AGENTS.md` changes only in its line for seed 46 under "What is coming": the task that
    sets the seed's state to `completed` takes it out, as
    `tests/onboarding/test_entry.py:140-150` requires. What it says of `build/` still
    holds, since a file of `collection/` is a copy and not a file made under `build/`.
- **What stays.** The board, the firmware, the core, the emulator, the app, the APK, every
  command and every reply. `thumbnails/` and its 424 previews. The card's catalog. `pack`,
  which takes JSON sources: a show of collection files is made with `decode` into
  `build/`, then `pack` from there. The guide's advice, "Keep every source at 50 MB or
  less", now for the JSON sources still committed.

## Required Behavior

1. `collection/` holds the 359 files of `card/`, `earlier/` and `others/`, 357 keys, each
   with `X.gif` and `X.md` beside it, and nothing else but `collection/README.md`.
2. Each `X.gif` is byte for byte the preview of its key in `thumbnails/`. Each `X.md` has
   the readme's shape: its source from the records for the 233 keys of `card/`, the link
   read from the name for the two `43-yt-784dsKVrdjQ` files, and `unknown` with what is
   known for the 122 keys without a record.
3. `node converter/odrig.js thumbnail FILE... --catalog DIR --beside` writes `X.gif`
   beside each file it does not pass over, a copy of the catalog's GIF; `--beside`
   without `--catalog` is refused with status 2.
4. A later conversion is added in one commit, as `collection/README.md` says. The
   collection's test refuses a file without its GIF or its readme, a GIF that is not the
   preview, a readme of another shape or another key, a name or a depth the card refuses,
   two names or paths that differ only in case, a device name of Windows, an ending not
   in lower case, a canvas other than 60 x 60, a file above the size rule, and under Git
   LFS a file git holds whole.
5. No JSON of a collection file is committed. `docs/decisions.md`, its change log and
   `docs/drifts.md` say what is committed now.
6. Nothing of the installation reads the folder, and filling it changes no byte of
   `thumbnails/`.
7. Under Git LFS, a clone downloads none of the collection's files unless asked, and the
   suites pass in it with pointers in their place. On the first computer, git refuses to
   add a collection file whole, and every git command works whether `tools/` is on the
   PATH or not. Under plain git, every full clone holds the files.
8. The pages of the project describe the collection, as the constraints list them.

## Definition Of Done

1. All test suites that need no board and no phone pass: on the first computer, and under
   Git LFS also in a fresh clone that holds the collection's animation files as pointers.
   The converter's suite checks `--beside`, its refusal without `--catalog`, a file passed
   over, a file without either ending and a GIF that cannot be written, the collection's
   test, and the rule of tracked media. The onboarding suite passes with the guide's new
   row and the word collection.
2. `collection/` is filled in its five parts, each pushed on the seed's branch. The
   report gives the number of files and keys, their bytes, how many have a full source, a
   partial one and none, the collection test's time, the size a new worktree takes, and,
   under Git LFS, the storage GitHub shows as used where the agent can read it. A full
   source is a link from the records, 233 keys. A partial one is a link read from a name,
   2 keys. None is `Source: unknown`, 122 keys.
3. Under Git LFS: before the second part of the fill is pushed, it is known whether a
   clone reads the committed `.lfsconfig` at its first checkout, and the fallback is taken
   if it does not. A fresh clone of the pushed repository downloads none of the
   collection's files. The command of `collection/README.md` fetches
   `collection/card/gifs/`, 11 files of 3,338,428 bytes, byte for byte, and nothing else.
   On the first computer, from a shell without `tools/` on its PATH, `git worktree add`, a
   checkout, a commit, a merge and a push work.
4. The owner is told in words what is not in the collection and why, which files have no
   known source, that the records and scripts the readmes were written from stay untracked
   on the first computer, that the card itself and the board's own storage since
   2026-10-25 were not read for this seed, that a file a phone uploads to the board does
   not reach git, and what the push used.

## Open Questions

1. **Plain git or Git LFS for the collection's animation files?** This must be answered
   before the first collection file is committed. Converting the files already pushed
   from one to the other rewrites history, which the rules forbid. A later switch would
   apply only to new files and leave the collection split between the two.
   - The figures: the collection is 4.69 GB, 4.37 GiB. GitHub blocks a file larger than
     100 MiB, and its page of limits says 100 MB. It limits one push to 2 GB, and
     strongly recommends a repository under 5 GB. Git LFS on the free plan takes a file
     up to 2 GB and gives 10 GiB of storage and 10 GiB of downloads a month.
   - Every pushed version counts whole in the storage, for good. GitHub frees it only
     when the repository is deleted and made again, or when GitHub's support purges an
     object. A download by anyone counts against the owner, and the repository is public
     today (question 2).
   - Without a payment method on file, use beyond the quota is blocked, not charged.
     Past the downloads, GitHub says that "Git LFS support is disabled on your account
     until the next month", read here as stopping pushes too. Past the storage, new files
     cannot be pushed. Whether the account has a payment method, and its plan, is not
     known here (`gh api user` gives no plan). Prices were not found in GitHub's pages.
   - Plain git needs nothing fetched or set up and no quota. But every full clone holds
     the 4.7 GB and every later file, for good, and each new worktree of the first
     computer checks out 4.7 GB more; each run of the walk-through's suite writes about
     9.4 GB into a temporary folder; there are 36 working trees today, 35 of them
     worktrees. One more long video the size of the largest, 2.57 GB, would take the
     repository past the 5 GB that GitHub strongly recommends. On the Windows computer the
     collection's test then reads the 4.7 GB at every run of the converter's suite; under
     Git LFS it reads pointers there.
   - Git LFS keeps the repository near its size today, with a pointer of less than 1,024
     bytes for each file, and takes a long group above 100 MB. It needs git-lfs fetched
     into `tools/` on the first computer, its filters and hooks set up there, and a check
     against a file committed whole. About 5.6 GiB stay free for later conversions, if no
     other repository of the account uses Git LFS (not checked). Beyond them the owner
     pays or stops adding. A worktree of the first computer may also check out the whole
     files, from the store it shares; not tried.
   - **Recommended answer:** Git LFS, for the animation files of `collection/` only, not
     fetched by a clone unless asked, without any change to the account's billing.
2. **The repository is public, but the project's pages record it as private. Which is
   meant?** GitHub shows `korenmic/Odrig` public (`gh api repos/korenmic/Odrig`).
   `docs/decisions.md`, in "Scope and process" and in its change log of 2026-10-12, and
   `agent/working-rules.md` call it private, and an onboarding test pins those words.
   With the collection it would hold whole conversions of other people's videos and
   reels, with their links and uploaders, and a push cannot be taken back. Under Git LFS,
   a private repository also keeps strangers' downloads off the owner's quota. The
   previews of seed 44 are already in its public history.
   - The visibility is the owner's to change on GitHub; the agent never changes it. The
     collection's first push waits until the owner has said in words that the
     repository is private now or that it stays public. If it stays public, a drift entry
     records that the pages are wrong there.
   - **Recommended answer:** private, as decided.
3. **Where did the earlier set, the two alphabets and the two numbered files come from?**
   No record of their sources was found on this computer, the share or the Drive's
   mirror; only their names are recorded.
   - **Recommended answer:** nothing now. Their readmes say `Source: unknown` and where
     each file was found. A source the owner gives later goes in, in a commit of its own.

## The Owner's Answers

On 2026-10-27 the owner asked for every animation to be tracked, with a readme for each
animation file of where it was taken from, so that it can be traced back. The owner's
words that followed, "add a seed to save only the odrg + preview thumbnail per each next
to it", came after the answers that ODRG keeps every picture and timing and that tracking
ODRG instead of JSON saves about 41 GB. They are the owner's ruling that an animation the
installation is given is committed as its ODRG or ODRGX file, not as its JSON. "Only" is
read against the JSON. The readme of where each file came from, which the owner asked for
earlier that day ("per animation file a readme where it was taken from"), stays beside
each file. The owner's rulings of 2026-10-12 stay in the change log as records. The
answers of `docs/drifts.md` that the previews are the only GIFs tracked and that an
imported source is committed in `animations/` give way in a new entry at its end. No
command is added. The three open questions above remain for the owner: the first before
any collection file is committed, the second before any is pushed.
