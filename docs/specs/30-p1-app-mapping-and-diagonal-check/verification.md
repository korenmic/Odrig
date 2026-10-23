# Seed 30 verification and handoff

The implementation is on `codex/app-mapping-diagonal`, in the managed worktree
`/Users/koren/.codex/worktrees/app-mapping-diagonal/odrig`. Tasks 1-4 cover the software
and artifacts; task 5 remains the owner's real-installation acceptance. No flashing,
phone installation, board command or power change was performed for this run.
The seed remains `in_progress` until that acceptance is recorded.

## Automated evidence

Run suites by discovery. The ignored `build/validation/` folder holds the command output.

| Check | Result |
|---|---|
| Core suite | 504 pass in the final fresh checkout, including existing timing, persistence and memory contracts |
| Python library | 465 pass in the final fresh checkout |
| JavaScript converter | 1,317 pass after placing the diagnostic source outside the frozen example-source folder |
| Focused mapping suite | 29 pass: durable transactions and cuts, stale revisions, real HTTP/serial/TCP commands, per-pin output bytes, app/editor/recovery and portrait/landscape |
| Firmware tool suite | 498 pass, including final documentation inventories |
| App suite | 175 pass in the final complete run after correcting two expectation failures |
| Emulator suite | 580 tests pass, with 9 platform skips, in the final fresh checkout after test-owned preview cleanup |
| Onboarding suite | 81 pass, including the final fresh checkout |
| Fresh-checkout walkthrough | All 5 pass in 1,184.818 seconds; all 23 documented setup, suite and example commands succeed |
| APK suite | 8 pass against the rebuilt APK, including byte-for-byte shared web source parity |
| Asset regeneration | `python3 core/diagonal.py --check` passes; the converter encodes the tracked JSON to the same 45-byte embedded ODRG |
| Full local show smoke | 116 animations, editable 60x60 mapping, brightness 32; diagnostic starts/stops and emulator-served Mapping source matches app/www |

The first core regressions failed on unknown commands, host regressions failed on stale
routing and missing events, and app regressions failed on the missing Mapping tab.
Those failures are recorded in their implementation commits. The fresh-checkout
walkthrough exposed the diagnostic JSON changing the tracked example animation folder's
frozen request hashes. Moving it to `core/assets/mapping-diagonal.json` preserves those
fixtures without changing converter output or stored answers.

The earlier preview failures occurred while port 8600 was occupied. Later, after the
owner's original emulator had closed, failed preview checks left their own subprocesses
running. Their PIDs were identified in the test logs and only those test-owned processes
were stopped. After cleanup completed, all seven preview checks and the full 580-test
emulator suite passed; the complete fresh-checkout walkthrough passed too. The owner's
emulator was never stopped. No board-dependent suites were run.

## Built artifacts

Built through the repository tools, without flashing:

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `build/app/odrig-debug.apk` | 4,197,581 | `bdf0e80930367b9c610efe42c7da807e36b4b6e1965bd0fa12dc3c1e56628107` |
| `build/firmware/out/odrig-firmware.bin` | 1,285,856 | `53aa13a31719ae014e88535c3fcf8ef8bb94e838f992c4c0d3cf9932c9e31129` |
| `build/firmware/out/odrig-standalone.bin` | 238,096 | `4f19e53f9cd204b58c53e596b05157d2efb7758db484074acb284ec95cfbcd97` |

The APK was rebuilt using the existing ignored local debug key. Its signer SHA-256
`93edde96f22f8a918a618bb1cd2d69e5d6246a7112c3615cb0f7c6468553a9fe` matches the
previous public APK, preserving Android update compatibility. The private key stays ignored.

The APK's build note identifies `e462494` with a clean app source tree. Its web files
are the exact shared implementation tested in Chrome. WLED includes the shared player,
atomic mapping controls and embedded diagnostic. The standalone artifact is still the
seed-12 trial; its output adapter has compiled byte-routing tests, and this build is
not evidence that the full standalone player or mapping commands exist there.

The APK delivery destination is the existing Google Drive `Artifacts/odrig/odrig-debug.apk`
file. Overwrite that existing file to retain its public-link identity; verify the public
bytes against the APK hash after synchronization. Artifacts and delivery logs stay ignored.

## Local testing

`build/local-show` is an ignored copy of the owner's full local show, made in this
worktree without modifying the original or the running emulator. Use another HTTP port:

```sh
cd /Users/koren/.codex/worktrees/app-mapping-diagonal/odrig && python3 -m emulator /Users/koren/.codex/worktrees/app-mapping-diagonal/odrig/build/local-show --port 8602
```

Open the printed page, choose Controller, then Mapping. Selecting an occupied GPIO swaps
two draft assignments; Save applies all twenty. Show diagonal uses the saved mapping.
The emulator's separate Mapping view updates live after a save. Stop diagonal restores
the prior playback selection. Normal Play also exits diagnostic mode.

## Requirement coverage and remaining acceptance

Requirements 1.1-1.4: shared editor, canonical-geometry detection, full-permutation
validation, swap/default drafts and read-only behavior for bench mappings.
Requirements 2.1-2.5: atomic persistence and restart/cut tests, fixed physical driver
routing under the whole-refresh lock, command transport parity, stale/lost reply recovery.
Requirements 3.1-3.6: exact x=y pixels through the existing decoder, packaged player
asset, playlist/cycle resume, idempotence, power/brightness/busy rules and target-owned mode.
Requirements 4.1-4.4: shared app source, live emulator view, actual per-pin bytes, both
firmware builds and APK verification. Requirement 4.5 remains task 5.

The owner must later approve a flash, connect the phone to the installation, correct an
assignment from the APK, observe one continuous bottom-left to top-right diagonal on all
twenty real snakes, restart to confirm persistence, then stop the diagnostic and observe
ordinary playback. A program cannot certify the physical wiring or the visible line.
