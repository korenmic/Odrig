# Seeds 29 and 30: software verification and delivery

The combined implementation is on `codex/seeds-29-30-playlist-storage-mapping` in
`/Users/koren/.codex/worktrees/app-mapping-diagonal/odrig`. Seed 29 tasks 1–5 and
seed 30 tasks 1–4 cover the software and delivery. Seed 29 task 6 and seed 30 task 5
remain the owner's phone and physical-installation acceptance. Both seeds stay
`in_progress`. No board was flashed, queried, installed on, or changed in this run.

## Behavior

The shared core owns persisted inclusion, playlist scheduling, atomic metadata for
bulk deletion, recovery cleanup, and capacity JSON. The WLED and emulator hosts supply
capacity facts; serial, HTTP and TCP carry the same commands. Android and the emulator
controller serve the same `app/www` implementation.

Show has confirmed Include in playlist checkboxes, independent explicit Play buttons,
and internal/external capacity. Storage has labelled selection, Select all, Clear
selection, confirmation with count and filenames, and sequential batches of at most 32.
A refusal preserves the remaining selection; an uncertain reply reports only acknowledged
progress and refreshes the authoritative list without retrying. Target changes discard
old replies and clear confirmations. External animations have no mutation controls.
Capacity refreshes on boot/reconnect/return, mutations and active-view polling.

Mapping still saves the complete twenty-pin assignment atomically and runs the embedded
diagonal. The diagram's physical appearance remains an owner check.

## Automated evidence

The ignored `build/` logs retain the detailed output. Suites use discovery.

| Check | Result |
|---|---|
| JavaScript converter | 1,319 pass in the fresh copy |
| Python library | 467 pass in the fresh copy |
| Core | 523 pass in the fresh copy with address and undefined-behavior sanitizers |
| Emulator and CLI | 583 tests succeed, with 9 platform skips |
| Shared app | 184 pass in the final complete run |
| Mapping | 29 pass, including saved assignment, diagonal, conflicts and phone-size layouts |
| Firmware tool and adapters | 499 pass through `python3 firmware/fw.py test` |
| Onboarding | 81 pass after updating the command vocabulary and inventory |
| APK | 8 pass against the exact delivery binary; shared source matches byte for byte |
| Embedded diagonal | `python3 core/diagonal.py --check` succeeds |
| Fresh-copy walkthrough | All 5 pass in 810.283s; all 23 documented commands succeed, including core 523, emulator 583 (9 skips), converter 1319, Python 467 and onboarding 81 |
| Full-show smoke | 116 animations selected in Chrome; mapping edit/restore, diagonal, inclusion, explicit play, bulk deletion, upload and capacity verified |

Before implementation, the management browser regressions failed on the missing
show-space element and inclusion checkbox. The onboarding regression later exposed
its old command inventory omitting `ignore`; the vocabulary and inventory now match.
The first final firmware suite invocation used system Python without LittleFS; rerunning
through the documented tool uses its prepared environment and all 499 tests pass.

The full-show smoke used a disposable copy, not the owner's show. Its cycle references
all 116 animations, and deletion was correctly refused while those references existed.
After removing the cycle in that copy, two files were deleted and one uploaded again;
internal free space rose from 307200 to 315392 bytes after deletion. The emulator-served
Show, Storage, Mapping and protocol sources matched `app/www` byte for byte. Brightness
was 32. The owner's existing emulator on port 8602 remained running and unchanged.

## Delivery artifacts

Built through `app/app.py` and `firmware/fw.py`, without flashing:

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `build/app/odrig-debug.apk` | 4,200,944 | `c4dc8564ad9a4fb11e805fbb16e1e6c04d471ab1759b5a5f2873890fc01c3251` |
| `build/firmware/out/odrig-firmware.bin` | 1,289,152 | `edf09f82d1185aeb85ef3ec71360bc8f724088710fdc196d756c5b87994dfbbb` |
| `build/firmware/out/odrig-standalone.bin` | 238,096 | `3bc87872a51acf342eee08d91a6a5ef85980d632e06a0f8d13b7c94e12547c79` |

The APK build note names `db3235b8c55183e3da68a43e3cff9766e2e71b11` with clean app
sources. Its signer SHA-256 is
`93edde96f22f8a918a618bb1cd2d69e5d6246a7112c3615cb0f7c6468553a9fe`, matching the
previous APK. Its private signing key stays ignored. Later verification changes are
documentation and test inventories, with no change to delivered runtime sources.

The standalone image remains the existing seed 12 trial. Building it does not establish
that its full player, external drive adapter or these new commands are implemented.
The WLED image is the primary delivery firmware and contains the shared player.

Both primary files were copied to the usual Drive folder:
`/Users/koren/Library/CloudStorage/GoogleDrive-miki801@gmail.com/My Drive/artifacts/odrig/`.
Their copied bytes match their local SHA-256 values. The existing APK was overwritten
in place, preserving its file id; an anonymous public download matched the new APK hash.
The firmware's Drive file id was assigned, and its Drive-mounted copy was verified;
no anonymous firmware-download claim is made.

- [APK](https://drive.google.com/file/d/1a8vUVJZcHBQcCNzDFgcCmeo6GepUA75-/view)
- [WLED firmware](https://drive.google.com/file/d/1pUYItwF6shn3uiegpw3bfj6tqR1Y33ht/view)
- [Drive folder](https://drive.google.com/drive/folders/15JM7uTBAGcUtKWbW3NDUp9o-hxsdDG8j)

## Branch and local testing

[Combined PR #8](https://github.com/korenmic/Odrig/pull/8) targets `master` from
`codex/seeds-29-30-playlist-storage-mapping`. The branch was fetched against
`origin/master` with no incoming commits. No merge was performed.

GitHub reports no check runs or status checks for this PR, and the pre-push master
baseline also had none. The remote CI classification is unknown/no observed checks,
not a claim that CI passed; the local verification above is the available evidence.

Run a new emulator on the available port 8603 with a dedicated local 116-animation copy:

```sh
cd /Users/koren/.codex/worktrees/app-mapping-diagonal/odrig && python3 -m emulator /Users/koren/.codex/worktrees/app-mapping-diagonal/odrig/build/local-show-seeds-29-30 --port 8603
```

The app is in the emulator's Controller view. This dedicated ignored copy starts the
ordinary playlist and omits the source show's explicit cycle, so inclusion and deletion
can be tested directly. The original local show and the owner's running emulator remain
unchanged. The software suites use disposable copies for deletion.

## Deferred acceptance

No phone install, flash or merge was requested. The owner still needs to verify Android
network delivery and controls, persisted inclusion and deletion on the board, actual
external-media capacity, and all twenty physical snakes forming one continuous diagonal
through a restart. These are physical acceptance checks, not open product questions.
