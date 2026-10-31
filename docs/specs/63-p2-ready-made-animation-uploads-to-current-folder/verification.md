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

APK and firmware delivery evidence will be added by task 4. Both must use the same
clean software source; firmware changes are required for nested guarded uploads.
Windows verification is authorized; macOS verification is deferred by the owner.
Physical phone installation, SD removal/reinsertion on the board, and observed LED
playback remain open owner checks. Emulator and Android AVD checks do not close them.
