# Requirements

Seed 76, `project-seeds/76-p1-an-empty-board-takes-its-first-animation/seed.md`. The
core, the emulator's page server, the reference model of the core's tests and the
pages; the firmware is rebuilt from the core without a change of its own; no command
is added; the converter, the Python library, the firmware tool and the app are not
changed.

## 1. The built-in mapping

1.1 The core holds the installation's mapping, the bytes of `mapping/legs-20.json`,
in `core/src/mapping_data.h`, which `core/mapping_data.py` writes from that file and
checks with `--check`, as `core/diagonal.py` does for `diagonal_data.h`.
1.2 When the host has no `mapping.json`, the core reads the built-in bytes in place of
the file, in the same two readings and into the same tables, so that it has twenty
legs of 180 LEDs on the pins 1 to 18, 21 and 47 and a canvas of 60 x 60. The host is
asked to open `mapping.json` once.
1.3 `status` then reports `width` 60 and `height` 60, and `odrig_core_leg_count` gives
20. `mapping get` reports `editable` true, the twenty pins in snake order and the
revision of those pins. `mapping set` works as it does today, and after it the
mapping is the file's. `mapping test on` and `mapping test snake <n>` work as they do
with the installed target file.
1.4 A `mapping.json` that is there and breaks a rule, or that cannot be read, refuses
the show as today: `mapping-malformed`, `read-error mapping.json`.

## 2. The empty show

2.1 When the host has no `show.json`, the show is empty: brightness 128, no
`min_seconds`, no `start` and no item, with the room of `kFewestItems` in the tables,
as a show file with `"items": []` gets.
2.2 `status` then reports `error` null, `readiness` `ready` once the start's checks are
done, `playing` null and `animation` null, and `brightness` 128; `list` lists nothing;
nothing plays and every LED is dark. `space`, `mapping get`, `clocks` and the other
commands answer as they do for a show with no item.
2.3 `upload begin` and `upload end` of an animation of 60 x 60 are accepted, the
animation gets the id 1, the playlist plays it, and `list` lists it.
2.4 A `show.json` that is there and breaks its format, or whose ids are wrong, or that
cannot be read, refuses the show as today, with the reason as today.
2.5 `pending.txt`, `order.txt`, `repeats.txt` and the other files of the show are
read, and the leftovers of an interrupted change are cleared away, as for a show with
no item.

## 3. What is written, and when

3.1 Nothing is written at the start: a host whose storage cannot be changed, and a
board whose storage cannot be written, report the canvas and the empty show, and
refuse a change in words.
3.2 The first change that writes `show.json` writes `mapping.json` first when the
mapping is the built-in one: the bytes of `mapping/legs-20.json`, written as
`mapping.part` and renamed over `mapping.json`, as `mapping set` writes. The change
goes on only when that write succeeded; a write that fails is the change's
`storage-error`, and `mapping.part` is removed. From then on the mapping is the
file's.
3.3 After the first upload into an empty folder the folder holds `mapping.json`, byte
for byte `mapping/legs-20.json`, `show.json` with the one item, and the animation's
file, a whole installed file set that `fw.py install-show` accepts.
3.4 `mapping set` on the built-in mapping writes `mapping.json` as it does today, with
the new pins; the next start reads that file.

## 4. The reasons

4.1 `mapping-missing` and `show-missing` stay the reasons of the tools: the converter's
`pack`, the Python library's readers and `fw.py install-show` refuse a folder without
the files as today.
4.2 The core reports neither. The table of `docs/reasons.md`, "The core", begins at
`mapping-malformed`, and its text says that a missing mapping file is the built-in
mapping and a missing show file is the empty show.
4.3 The reference model of the core's tests, `tests/core/support.py`, follows the
core: a file set without `mapping.json` has the legs of `mapping/legs-20.json`, one
without `show.json` has the empty show, and a change that writes the show file of such
a set writes the mapping file beside it.

## 5. The emulator

5.1 The emulator started on an empty folder starts valid: its `hello` event names the
twenty legs and no error, its status events report no error, the page draws the legs
with every LED dark, and the reason band is hidden.
5.2 `GET /show/mapping.json` answers the folder's mapping file byte for byte when the
folder has one, whatever the core made of it, and the repository's
`mapping/legs-20.json` when the folder has none.
5.3 The step of the emulator's check list that showed a reason by removing
`show.json` shows it by breaking the show file instead, and the page's reason band is
described for a file that cannot be used.

## 6. The tools and the app

6.1 The converter, the Python library and the firmware tool are not changed.
6.2 The app is not changed. Its sentence `The target has not reported its canvas yet.`
and the reason `no-canvas` now mean a mapping file the installation cannot use, or an
installation older than this seed, and the row of `no-canvas` in `docs/android-app.md`
says so.
6.3 The firmware is not changed: it is rebuilt from the core and makes WLED's outputs
from the twenty legs as it does with the installed target file.

## 7. Proof and delivery

7.1 The core's suite, each new test of a fault seen failing before the change: an
empty file set gives the twenty legs, the canvas of 60 x 60, no error and dark
refreshes; a file set with the mapping file alone is `ready` and dark; one with the
show file alone plays its show on the built-in mapping; the first upload into an empty
file set is accepted, plays, and leaves `mapping.json` byte for byte the target file,
`show.json` and the animation; a change that cannot write `mapping.json` is refused
with `storage-error` and leaves no part; `mapping set` on the built-in mapping writes
the file and the next start reads it; a malformed mapping file and a malformed show
file are refused as today; `core/mapping_data.py --check` passes and a changed header
fails it.
7.2 The emulator's suite: an empty folder gives the legs, no reason and the served
mapping; a mapping the core refuses is still served as it is; the documentation test
with the changed check list. The app's suite: an upload into the emulator started on
an empty folder, acknowledged as `Uploaded as animation 1 <file>. It plays in the
playlist.` and listed.
7.3 The firmware's host suites, the onboarding suite, the converter's documentation
test and the app's documentation test pass; the firmware is built on Windows from the
pull request's head with `python firmware/fw.py build`, verified with
`firmware/verify_build.py`, and placed on the Drive under `odrig archive/seed-76/`
with its `.sha256`, its `.build.json`, the verification files and a README that says
how it is flashed from the phone: the application image at offset 0x10000, the flash
settings kept, no erase. No APK is built: the app is unchanged, and the APK of seed 75
works with the new firmware.
7.4 The owner, with the spare board flashed with the firmware and the phone: `Choose
a ready-made animation`, `Internal storage`, `Upload to the installation`, `Uploaded
as animation 1 <file>. It plays in the playlist.`, and the animation on the LEDs. This
check is the owner's and stays open until the owner reports it.
