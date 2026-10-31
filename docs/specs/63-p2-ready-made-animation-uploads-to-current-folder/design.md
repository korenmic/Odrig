# Design

## Boundaries

The shared core owns safe path resolution, writes, authoritative validation and
publication. The shared app owns selection, visible destination and preflight.
The emulator supplies the same core with a writable card. No internal-folder
redesign, new format, hardware change or new command tokens are needed.

## Core destination lifetime

Extend the existing external begin's `<file>` argument to a valid catalog path.
Split it into a basename and an existing indexed folder's stable id (zero means
root). Reconstruct its canonical path on the stack when committing. Keep only
the basename and compact folder id in Upload; pack boolean/state fields to avoid
growing the fixed arena. Do not borrow the live playback/index row's name buffer.
Resolve the folder by id and confirm the path before opening a part. Existing
drive-number change handling must discard the transaction before a different
medium can be written. Recheck the folder at commit.

Generalize `catalog_install_external` from root to the resolved IndexFolder. Use
its global first position plus own-file offset for replacement/addition, its
ordinal for `files_of`, `firsts_after`, map folder and ancestor folder rows. Reuse
the existing index transaction/recovery engine and player position adjustments.
Do not increase shared per-file names, lower capacity or relax memory warnings.

## Creation guard without new command spelling

Keep existing explicit external replacement clients compatible. Extend the
existing `upload expect <crc32>` to external storage: `00000000` requires the
destination to be absent, both before accepting data and immediately before
publication. An occupied path returns `stale`; it never replaces a file. Nonzero
values retain bounded expected-content checking for explicit replacements where
supported. The app sends the absence guard for every new external upload.
Internal new uploads use a fresh id and name checked against the current root
and retain the existing in-use protections. Existing text/clock edits are untouched.
This extends argument handling of existing command forms on all core transports;
there is no new command-list spelling. Document the semantics and rationale in
commands.md and an appended drift entry.

## App modules

Add a small read-only ready-file helper using converter ODRG/ODRGX headers and
bounded drawn-container validation. Read headers before loading encoded bytes;
reject sizes outside uint32. Never invoke the frames reader/inflater for a
compressed ready-made file. A prepared result keeps the original encoded bytes,
format facts and preview eligibility; it does not materialize all frame pictures.
Known preview URLs come from the existing content-key catalog/cache. Unknown or
unsafe previews show a clear fallback. Only bounded uncompressed frames or
bounded drawn containers may call the existing preview maker.

Add a destination helper that captures target identity, browsed folder and
catalog generations at selection/preparation; models automatic External versus
explicit Internal; validates basenames; computes a visible physical destination;
and checks a fresh catalog and folder list before begin. External unknown is
disabled, detected read-only is not absence. Selection captures browsing context;
later navigation cannot retarget it. Storage change/absence recomputes the
visible destination using that captured context. A target or generation change
requires re-preparing/reselecting rather than guessing that old ids remain valid.
Fetch the full root for internal ids and exact destination-folder list for
collisions, independent of current navigation/filter. Verify folder path and id
through its parent listing; catalog generation anchors the snapshot.

Update storage.js and index.html: separate ready-made picker, shared named
storage dropdown, editable basename, destination/reason and preview fallback.
Retain video/GIF conversion controls for media only. Each new file resets storage
default. Freeze controls during transmission, capture job arguments by value,
and send the external absence guard before data. After success let the existing
client refresh list/catalog/keys. Generate safe previews only; never call the
unbounded frame inflater after a large ready-made success.

## Validation and delivery

Task1 proves nested indexed ODRG/ODRGX writes, untouched bytes, id-map/count
updates, creation collisions, removed/read-only media, cancellation and restart
recovery through the real core host and checks fixed memory limits. Task2 tests
pure preparation/destination functions and the shared browser UI, including
conversion and edit regressions. Task3 runs actual emulator/app integration and
the34.4MB space-scan upload with bounded phone preparation, readback hashes,
catalog/playback/namespace checks and portable suites. Preserve test failures
seen before fixes in the respective commit messages.

Task4 builds via firmware/fw.py and app/app.py's existing Windows recipes with
the persistent key from the private signing directory. Verify artifacts and
Android clean install, same-key update and launch on the existing disposable AVD.
Overwrite Drive odrig-debug.apk and odrig-firmware.bin with r+b/truncate, flush,
readback SHA256 and stable mounted file identity, preserving signing backups.
Record source commit, hashes, test proof and physical acceptance limits in a
verification document. The final implementation push updates PR37; it includes
PR35's still-unmerged delivered baseline, which must be disclosed as a dependency.
