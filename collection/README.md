# The collection

Every animation file the installation has been given, kept as the file itself, with its
preview and a readme of where it came from beside it. Nothing of the installation reads
this folder. Git tracks it, all but its heavy animation files; the share keeps every file
of it, in the share's folder artifacts/odrig/collection.

## The four folders

- `card/`: the animation files of the card's folder `odrig` that are not heavy, at their
  paths on the card. The two files at its root have the same bytes as two files of
  `youtube/`. A file stays at the path it was given when it was added. A card takes at
  most 256 files and 32 sub-folders.
- `earlier/`: the owner's earlier set, the files found at the root of the share's folder
  artifacts/odrig: 119 files of 43 originals numbered 01 to 43, in the variants fit,
  crop, cropfit and zoom70, `43-yt-784dsKVrdjQ_center60of256.odrg` and the two
  alphabets.
- `others/`: the files with no place on the card, at first two files found on the
  board's own storage, read on 2026-10-25.
- `long/`: the heavy files. A group of a long video, cut into groups of 15 minutes, is
  in `long/yt-<id>/`, its path on the card; any other file over 50,000,000 bytes is at
  the root of `long/` by its own name, its path on the card in its readme's Notes.

## What git tracks, and where the rest is kept

- In `card/`, `earlier/` and `others/`: each animation file with its `X.gif` and `X.md`.
- In `long/`: each heavy file's `X.gif` and `X.md`, and not the file. `.gitignore` keeps
  the animation files of `long/` out, `/collection/long/**/*.odrg` and
  `/collection/long/**/*.odrgx`. They are kept on the share, in its `long/`.
- The key of every file, with its GIF and its names, its path on the card among them, is
  in the repository's `thumbnails/catalog.js`, the one file the app reads.

The share holds every file of this folder, heavy ones included, at the same paths. Its
full path on a computer that has it is `ODRIG_ANIMATIONS` in the file `env` at the root of
the checkout, a copy of `env.template` that git ignores. The paths where these files were
on the share before are kept in the share's folder artifacts/odrig/archived. Google Drive
is not used for the collection for now: it has no room.

## Beside each file

For an animation file `X.odrg` or `X.odrgx`:

- `X.gif`: its preview, byte for byte the `thumbnails/<key>.gif` of its key;
- `X.md`: its readme.

The key of a file is its CRC-32 of zlib as eight lowercase hexadecimal digits, a dash and
its size in bytes.

## The readme

UTF-8 with LF line ends, plain ASCII where the source allows. A title line, an empty line
and then these 16 lines, always all of them, in this order, each `- Label: value` with a
value that is never empty. `unknown` stands for what is not known.

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

- TITLE: the title, else the uploader and the media id, else the file's name.
- File and Key: those of its file. A readme names its file, not its path.
- Animation: read from the file; KIND is frames, text or widget.
- Source: the link, or `unknown`. Platform: YouTube, Instagram, Giphy, Tenor, itch.io,
  Internet Archive, or `unknown`.
- Uploader: the name the platform shows, or `unknown`; an uploader recorded as an e-mail
  address is written as `unknown`.
- Title and Media id: as recorded, or `unknown`.
- Part: `whole`, `from S s for D s`, `group N of M, from S s for D s`, or `unknown`.
- Crop: `none`, the crop `W:H:X:Y` of the cut, or `unknown`.
- Fit: the converter's `--fit` (fill, fit or stretch) and the mapping, or `unknown`.
- Made with: the converter's commands, their files as words in capitals such as
  `MEDIA`, `FRAMES.json` and `X.odrg`, and any other step in words: the download, the
  crop, the cut or the join of pieces. Else `unknown`.
- Converted and Added: `YYYY-MM-DD`; Converted may be `unknown`.
- Found: where the file was when it was added, in words.
- Notes: what the lines above cannot say, in words, or `none`. A heavy file that is not of
  a long video ends its Notes with its path on the card.

A readme names no folder of a computer, no mount point and no account of the owner, and
holds no carriage return. The share is "the share's folder artifacts/odrig" and Google
Drive "the owner's Google Drive folder artifacts/odrig/animations". A link is taken from
the records, never made from a name, and no reading of a name's words is written as a
fact. The first readmes were written on 2026-10-27 from the records of the conversions
kept on the first computer. A source the owner gives later goes into the readme.

## Adding a later conversion

The seven `card/clocks/message/v7-*.odrgx` files are complete procedural message
widgets, one retained source tab each, with loops of 24.4 to 76.9 seconds.
Their reproducible generator, source/font hashes, caption manifest and visual
comparison are in
`project-seeds/59-p2-message-clock-widgets-and-clocks-only-mode/source/`.
Their GIFs use the same accelerated sampling as every other preview. Runtime
playback preserves each whole sequence. The earlier `its-not-the-time` file and
its companions remain unchanged. Share delivery is a collection copy, not an SD
installation; a physical card update still uses managed catalog tools.

A conversion is added when it is handed to the owner. A conversion that is only tried is
not added. It goes into `long/` when it is heavy, a group of a long video or a file over
50,000,000 bytes; else into `card/` at the path it is to have on the card, or into
`others/` when it has none.

The checkout of the first computer stays on the commit the owner runs. So the steps run
in a worktree of `origin/master`, after `git fetch origin`, which holds this folder too.

1. Import and encode in the worktree's `build/`, as for any animation. Its JSON stays
   there.
2. Copy `X.odrg` to its place in `collection/`. A path the collection already holds with
   other bytes, in git or on the share, is not reused: give the conversion a name of its
   own first.
3. Run
   `node converter/odrig.js thumbnail collection/card/<folder>/X.odrg --catalog thumbnails --card collection/card --beside`.
   For a group of a long video, `--card collection`, since its path from `collection/` is
   its path on the card; for a file of `others/` or another file of `long/`, no `--card`.
   It adds the preview to `thumbnails/` and writes `X.gif` beside the file.
4. Write `X.md` in the shape above.
5. Commit by named paths, on the worktree's branch: `thumbnails/catalog.js`,
   `thumbnails/<key>.gif` for a new key, `X.gif`, `X.md`, and `X.odrg` when it is not
   heavy. The animation files of `long/` are never staged; git ignores them.
6. Copy `X.odrg`, `X.gif` and `X.md` to the same place in the share's collection, at the
   path `ODRIG_ANIMATIONS` of `env` gives: from a worktree two folders down, `../../env`
   of the first computer's checkout, else `env.template`.
