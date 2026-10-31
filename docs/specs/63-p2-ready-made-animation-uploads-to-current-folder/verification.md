# Verification

## Software and emulator proof

The core and app changes are proof-committed in 03f713e and 1e96fad. The third
task adds the emulator/browser acceptance cases and fixes same-file reselection:
the regression first failed because the file input retained its previous value;
clearing the input after capturing its File permits selecting it again.

The native emulator exercised the actual Core and FolderHost, with deterministic
20 ms ticks. It uploaded the existing `space-scan-10x.odrg` into the indexed
`space/` folder and checked all stored bytes and the complete validated timeline:

| Property | Result |
| --- | --- |
| Encoded size | 34,410,601 bytes |
| Source and stored SHA256 | `a93e82f12cbea0f5937ac74d761dcd5f2fc3c4590129496a1b8b9e126d297f19` |
| Content key | `6e46a8c2-34410601` |
| Frames / loop | 18,004 / 720,160 ms |
| Native checks | 33 passed; 23,174 commands and 19,733 polls |
| Native arena | 130,303 bytes in this fixture, unchanged by the upload |

The arena figure describes the empty-internal-show fixture, not the maximum
catalog case. The core memory and stack suites retain the existing limits.
Virtual clock execution is software correctness evidence, not measured board FPS.
The proof includes acknowledged catalog publication, folder listing, wire readback,
nonblack playback, restart, ignore/brightness persistence, removal, an unchanged
unrelated widget, and byte-identical ODRGX widget upload/playback. Missing folders,
read-only media, physical collisions, malformed payload, cancellation, oversized
Internal fallback, and removal/reinsertion refuse or stop without retargeting.
The source animation, mapping and show remain byte-identical.

The shared browser app prepared that same large file with one 36-byte prefix read
and one encoded-body read, without materializing its 18,004 frames. Its SHA256
matched the native proof, and the known catalog preview was reused. The visible
destination was `External /space/space-scan-10x.odrg`. Browser recovery cases cover
absence, gray External choice, redetection, explicit Internal for one form, fresh
preflight review, captured navigation, old-firmware refusal before data, and no
Internal replay after an External failure. The large-file browser proof checks
preparation; the native proof separately transfers and validates the whole file.

## Discovered suites and repairs

Local logs and machine-readable evidence are retained under `build/`, including
`build/seed63-proof/space-scan-native.json` and `build/seed63-proof/task2-full/`.
Suite discovery, rather than a maintained list of test files, selected the tests.

| Suite / focused recheck | Result |
| --- | --- |
| Converter npm | 1,602 passed |
| Python converter / mapping / runner | 552 / 43 / 26 passed |
| Emulator / firmware host | 656 with 19 skips / 28 passed |
| Core | 1,050 run; new creation guard initially failed, then fresh creation 3 and incremental 15 passed |
| Portable build scripts / app architecture | 53 / 7 passed after fixes |
| App | 427 run; stale contracts and assertions repaired, affected group 71 and ready uploads 8 passed |
| Firmware | 647 run; one shared-cache environment assertion, default-environment recheck 7 passed |
| Onboarding | 88 passed after removing completed work from the planned list |
| Native large upload / browser large preparation | 1 / 2 passed |
| Browser recovery / picker and conversion regressions | 7 / 30 passed |

Initial core destination failures were seen before the path/guard fixes. App
repairs include converter-boundary, ASCII-source and command-literal contracts,
catalog fixtures and field inventories. One folder-drag timing failure under
parallel load passed unchanged in the affected group. The firmware environment
failure assumed a checkout-local tool cache while the run explicitly used the
existing shared cache; its original assertions passed with the default isolated
environment. These are composite proofs with explicit rechecks, not a claim that
every initial broad run was green.

## Delivery and owner acceptance

APK and required firmware were built from the same clean software source,
`9c5b996ee8505d086bfa81b18e56f3513d873a68`. The later task-4 proof commit
changes only documentation and completion bookkeeping. See [delivery.json](delivery.json)
for hashes, lengths, source and mounted file identities.
Windows verification is authorized; macOS verification is deferred by the owner.
Physical phone installation, SD removal/reinsertion on the board, and observed LED
playback remain open owner checks. Emulator and Android AVD checks do not close them.


The APK passed all eight original packaging assertions using native Windows SDK
tool resolution, signature verification and alignment. A temporary read-only clone
of the existing Android16 AVD passed clean install, launch, same-key update and
relaunch with a live application process. Its original configuration was unchanged,
and the owned emulator was stopped. This does not claim a physical phone check.

The default microSD firmware was built through `firmware/fw.py build` on Windows,
using the pinned tools in the supported shared cache. Offline inspection passed the
ESP32-S3 application header, checksum, source/input provenance, size and linked
player entry points. It is the application image for offset `0x10000`; no board was
flashed and no flash erase was performed.

The existing `G:/My Drive/Artifacts/odrig/odrig-debug.apk` and
`odrig-firmware.bin` were overwritten in place, along with the firmware checksum,
build provenance, inspection and delivery sidecars. Readback verified every byte
hash and length, and retained the existing mounted file identities. This is mounted
Drive evidence, not an independent Drive API check. The dedicated signing key and
all four existing signing backup files remained byte-identical. The global Android
debug key was also unchanged.

## Folder-navigation follow-up

The owner authorized tasks 5 and 6 after reporting that Clocks unexpectedly
returns to Root while entries load. `askListPart` treated one `unknown-id` as proof
that the browsed folder was gone, cleared its navigation trail and immediately
selected Root. A transient lookup failure or stale folder ID therefore discarded
the operator's location without verifying the path.

Five browser assertions were observed failing against the delivered app before
the correction: the resulting path was empty and Root had been visited instead of
retaining `clocks` or `clocks/message`. The corrected client re-resolves the captured
path through fresh parent listings, recovers an updated folder ID, and restarts
pagination from zero after a bounded retry delay. Failed verification and an
incomplete/damaged catalog keep the path and previously complete rows. A confirmed
missing path still returns to Root. Every awaited reply retains target and level
identity guards, so a late recovery cannot undo the operator's Back/navigation.

The full discovered app suite passed 445 tests and onboarding passed 88 in
`build/folder-followup-suites.log` (run `20261031-120038-104212`). A subsequent focused
recovery run passed 8 tests, adding catalog-loading/damaged states; no production source
changed after the broad run. Its final result is retained in
`build/folder-recovery-final.log`. The original fail-first evidence is
`build/folder-recovery-red.log`.

The native emulator/shared-browser proof used all 120 actual Clocks files: 112
direct entries and 8 message entries. It retained 112 unique visible rows through
three complete multi-page refreshes, with no Root visit. This is the project's
native Core/host emulator, not an ESP32-S3 instruction-set/hardware simulation.
Controlled protocol refusals reproduce the faulty UI recovery; spontaneous SD I/O
failure on the physical board is not claimed reproduced or repaired by this change.
The owner's earlier storage-error report still needs its physical storage readings.

The correction changes only app code. The delivered firmware's input digest remains
`3d8b6dd472e4f9c30827a1f4c706496fd2ad7faf9afe2ce0a47677fe66f961cd`;
its image, checksum and provenance remain unchanged for this correction.
Task 6 records the new APK and retains that firmware. Phone folder-browsing
acceptance remains open until the owner tries the updated APK.
