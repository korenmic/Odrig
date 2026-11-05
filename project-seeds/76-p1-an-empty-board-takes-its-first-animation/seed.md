# An empty board takes its first animation

## Summary

A board whose storage holds no `mapping.json` and no `show.json`, as a spare board flashed
with the firmware alone, refuses everything: the core reads the mapping file first, finds
none, and the show is invalid with `mapping-missing`. `status` then reports no canvas, the
app refuses every ready-made file with `The target has not reported its canvas yet.`, and
the board itself would refuse `upload begin` with `show-invalid`. So a board that has
nothing cannot be given its first animation from the phone. The canvas of the
installation is 60 x 60 on twenty legs, the one file `mapping/legs-20.json` describes,
and nothing else was ever installed. This seed makes the core play without the two files:
a board without a mapping file has the installation's mapping, built into the core, and a
board without a show file has an empty show. `status` reports the canvas, the first
upload is accepted, and the first change that writes the show file writes the mapping
file beside it, so that the folder is a whole installed file set from then on. The fix is
the core's; the firmware is rebuilt from it and no command is added. The app is not
changed.

## Priority

- `P1`

## Depends On

- Seed 02, the core: `core/src/core.cpp`, whose `start()` reads the mapping file and then
  the show file and fails the show on the first fault; `core/src/mapping.cpp`, the reader
  of the mapping file; `core/src/show.cpp`, the reader of the show file.
- Seed 05, the canvas of 60 x 60: `mapping/legs-20.json`, the target's mapping file, and
  the rule in [decisions.md](../../docs/decisions.md) that the target is twenty upright
  legs of three columns each.
- Seed 30, the mapping controls: `core/src/mapping_control.cpp`, whose `persist()` writes
  `mapping.json` from the legs in memory, and `core/src/diagonal_data.h`, the diagonal
  built into the core by `core/diagonal.py`, read through an in-memory host.
- Seed 34, the content changes: `content_write_show()` of `core/src/content.cpp`, through
  which every change of the show writes `show.json`.
- Seed 03, the emulator: `emulator/httpd.py`, which serves the folder's mapping file at
  `/show/mapping.json` for the page's mapping view.
- The reference model of the core's tests, `tests/core/support.py`, whose `_check()`
  refuses a file set without the two files as the core does today.

## Product Context

On 2026-11-05 at 06:41 the owner, at the installation with the spare board, whose own
storage is empty (`Internal storage: Free 5.1 MB of 5.1 MB`) and without a card, chose
`time-standalone-5-time-bands.odrg` with `Choose a ready-made animation` and got the
dialog `Cannot use this animation: The target has not reported its canvas yet.` The
owner ruled: "the canvas is always 1:1 60x60 no matter what. Whether a first animation
already pre exists or not should not be a legit valid deal breaker for uploading the
first animation!"

What the code does, read on 2026-11-05:

- `prepareReady()` of `app/www/convert.js` throws that sentence when `status` gives no
  `width` and `height`; `make()` of `app/www/screens/storage.js` refuses a video the same
  way with the words of `no-canvas`. [commands.md](../../docs/commands.md) says the two
  are `null` "while there is no mapping the player can use".
- `start()` of `core/src/core.cpp` calls `read_mapping()`, whose `read_once()` answers
  `kMappingMissing` when the host has no `mapping.json`, and `core_fail()` makes the show
  invalid: `width` and `height` stay 0 and are reported `null`, `readiness` is
  `recovery`, `error` is `mapping-missing`, and every content command, `upload begin`
  among them, is refused with `show-invalid`. A folder with a mapping file and no show
  file is invalid the same way with `show-missing`. So the app's refusal is only the
  first wall: without the app's check the board would refuse the upload itself.
- The board's folder is written by `fw.py install-show` from a computer over the USB
  cable, which puts `mapping.json`, `show.json` and the animations there. The spare board
  was flashed with the firmware alone; the field notes of pull request #47 record its
  `status` as `mapping-missing` on 2026-11-03. The owner has a phone at the installation
  and no computer.
- Seed 65, pull request #44, which is not merged, meets the same fault from the
  firmware's side: `firmware/usermod/odrig_bootstrap.h` writes the twenty-leg mapping and
  an empty show into a fresh store before the core starts. The core itself and the
  emulator keep refusing a folder without the files, and the owner's spare board still
  reported no canvas on 2026-11-05; which firmware it runs is not recorded.

So the fault is the core's: it treats the absence of a file that has only one sensible
content as a fault of the show.

## Technical Constraints

- **The built-in mapping.** The core holds the installation's mapping, the bytes of
  `mapping/legs-20.json`, in `core/src/mapping_data.h`, made by `core/mapping_data.py`
  from that file as `core/diagonal.py` makes `diagonal_data.h`, with the same `--check`
  that refuses a header that differs from the file. When the host has no `mapping.json`,
  `read_mapping()` reads the built-in bytes through an in-memory host, in the same two
  readings and with the same tables, and `core.mapping_builtin` says so. Twenty legs of
  180 LEDs on the pins 1 to 18, 21 and 47, a canvas of 60 x 60. `mapping get` reports it
  editable with the default pins and the revision of those pins; `mapping set` persists
  as it does today, after which the mapping is the file's. A `mapping.json` that is there
  and malformed, or that cannot be read, is a fault as today: `mapping-malformed` and
  `read-error mapping.json` stay.
- **The empty show.** When the host has no `show.json`, the show is empty: brightness
  128, the value of `shows/example/show.json`, no `min_seconds`, no `start`, no item, with
  the room of `kFewestItems` in the tables, as a show file with `"items": []` gets.
  `status` reports `error` null, `width` 60, `height` 60, `readiness` `ready`, `playing`
  null and `animation` null; `list` lists nothing; nothing plays and the LEDs are dark.
  A `show.json` that is there and malformed, or whose ids are wrong, or that cannot be
  read, is a fault as today.
- **What is written, and when.** Nothing at the start, so that a host whose storage
  cannot be changed, and a board whose storage cannot be written, still report the canvas
  and refuse a change in words. The first change that writes `show.json`, every one of
  which goes through `content_write_show()`, writes `mapping.json` first when the
  mapping is the built-in one, as `mapping set` writes it, and the change goes on only
  when that write succeeded; from then on the folder is a whole installed file set, which
  `fw.py read-show` copies and `install-show` accepts. A write that fails is the change's
  `storage-error`, as today.
- **The reasons.** `mapping-missing` and `show-missing` are the reasons of the tools, the
  converter, the Python library and `fw.py install-show`, which refuse a folder without
  the files, and they stay. The core reports neither: the table of
  [reasons.md](../../docs/reasons.md), "The core", begins at `mapping-malformed`, and
  the reference model of `tests/core/support.py` follows the core.
- **The emulator.** An empty folder starts valid: twenty legs in the mapping view, every
  LED dark, no reason band. `/show/mapping.json` answers the repository's
  `mapping/legs-20.json` when the folder has no mapping file, the bytes the core holds,
  and the folder's own file, as it is, when it has one. The step of the emulator's check
  list that removes `show.json` to see a reason breaks the show file instead.
- **The firmware.** No change of its own: it is rebuilt from the core, and makes WLED's
  outputs from the twenty legs as it does with an installed target file. Seed 65's
  bootstrap in pull request #44 writes the same two files from the firmware's side; the
  two agree, and what becomes of the bootstrap is decided when that pull request is
  brought up to date with `master`, not here.
- **The app.** Not changed. Its sentence `The target has not reported its canvas yet.`
  now means a mapping file that cannot be used, or a target older than this seed, and
  the row of `no-canvas` in [android-app.md](../../docs/android-app.md) says so.
- **Where the work goes.** `core/src/mapping.cpp`, `core/src/mapping_control.cpp`,
  `core/src/content.cpp`, `core/src/show.cpp`, `core/src/core.cpp`,
  `core/src/core_state.h`, `core/src/mapping_data.h` and `core/mapping_data.py`;
  `tests/core/`, its reference model first; `emulator/httpd.py` and `tests/emulator/`;
  `tests/app/` for a first upload against the emulator with an empty folder; the pages
  `docs/core.md`, `docs/reasons.md`, `docs/commands.md`, `docs/mapping.md`,
  `docs/emulator.md`, `docs/android-app.md` and `agent/getting-started.md`; the change
  log of `docs/decisions.md` with the owner's ruling, and `docs/drifts.md`.
- **Where it lands.** On a branch from `master`, as a pull request. The firmware is
  built from the pull request's head with `python firmware/fw.py build` on Windows,
  verified with `firmware/verify_build.py`, and placed on the Drive under
  `odrig archive/seed-76/` with its `.sha256`, its `.build.json` and a README that says
  how it is flashed from the phone: the application image at offset 0x10000, the flash
  settings kept, no erase, as the earlier deliveries say. No APK: the app is unchanged,
  and the APK of seed 75 works with the new firmware.

## Required Behavior

1. A host without `mapping.json` plays on the installation's mapping: `status` reports
   `width` 60, `height` 60 and `error` null, and `mapping get` reports the twenty default
   pins, editable.
2. A host without `show.json` has an empty show: `readiness` `ready`, nothing playing,
   `list` empty, the LEDs dark; `upload begin` and `upload end` of an animation of 60 x
   60 are accepted, the animation plays, and the folder then holds `mapping.json`,
   `show.json` and the file.
3. A mapping file or a show file that is there and cannot be used refuses the show as
   today, with the reason as today.
4. The emulator started on an empty folder shows the twenty legs, serves the built-in
   mapping at `/show/mapping.json`, and shows no reason.
5. The tools are unchanged: `odrig pack`, the Python library and `fw.py install-show`
   refuse a folder without the files as today.
6. The app is unchanged, and with the new firmware `Choose a ready-made animation`
   accepts a 60 x 60 file on a board that has nothing, and the upload proceeds.

## Definition Of Done

1. The core's suite with its reference model, each test of a fault seen failing before
   the change: an empty file set gives the twenty legs, a 60 x 60 canvas and no error; a
   file set with the mapping file alone is `ready` and dark; one with the show file alone
   plays its show on the built-in mapping; the first upload into an empty file set is
   accepted, plays, and leaves the three files; `mapping set` on the built-in mapping
   persists and the next start reads the file; a malformed mapping file and a malformed
   show file are refused as today; the check of `mapping_data.h` against
   `mapping/legs-20.json`.
2. The emulator's suite: an empty folder gives the legs, no reason and the served
   mapping; a mapping the core refuses is still served as it is. The app's suite: a
   ready-made upload into the emulator started on an empty folder, acknowledged and
   listed.
3. The firmware built on Windows from the pull request's head and verified; the
   firmware's host suites, the onboarding suite and the converter's docs test.
4. The owner, with the spare board flashed with the firmware and the phone: `Choose a
   ready-made animation`, `Internal storage`, `Upload to the installation`, and `Uploaded
   as animation 1 <file>. It plays in the playlist.`; the animation on the LEDs.

## Open Questions

None. The owner asked for a fix seed with no open questions; what is decided here is
that the core holds the installation's mapping and uses it when the mapping file is not
there; that a missing show file is an empty show of brightness 128; that nothing is
written at the start and the first change of the show writes the mapping file beside the
show file; that `mapping-missing` and `show-missing` stay the tools' reasons and leave the
core's; that the emulator serves the built-in mapping for its page; that the firmware is
rebuilt without a change of its own and the app is not changed; and that seed 65's
bootstrap is left to that seed's pull request.
