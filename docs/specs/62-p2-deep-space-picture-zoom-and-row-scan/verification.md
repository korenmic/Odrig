# Verification: complete deep-space scan

The approved animation is implemented. It starts already at10x linear zoom,
covers ten alternating rows and nine descents, then makes the approved final
rightward pass across the bottom row. The first and last crops were inspected
upright against the original. The reference WebP is unchanged.

## Delivered content

| Property | Observed value |
|---|---|
| File | `collection/card/space/space-scan-10x.odrg` |
| Canvas / source window | 60x60 / 108x108 from1080x1080 |
| Frames / loop | 18,004 / 720,160ms |
| Bytes / app preview key | 34,410,601 / `6e46a8c2-34410601` |
| SHA256 | `a93e82f12cbea0f5937ac74d761dcd5f2fc3c4590129496a1b8b9e126d297f19` |
| Generator / content proof | `5b5a094` / `c495bbb` |

The [manifest](../../../project-seeds/62-p2-deep-space-picture-zoom-and-row-scan/source/artifact.json)
also records the original, generated JSON, mapping and show checksums. The
461,201,924byte generated JSON remains under build/. The compressed binary is
below the collection50MB limit and is tracked with its normal GIF/provenance.
It is too large for the board's usual internal store: physical use is from SD.

## Actual playback evidence

The normal Windows shared-core build passed with warnings as errors and the
existing512byte checked frame limit. The [portable verifier](../../../project-seeds/62-p2-deep-space-picture-zoom-and-row-scan/source/verify.py)
uses the actual emulator FolderHost, native shared core and recording writer.
It observes readiness before starting a fresh turn; play origin was23,020ms
on the virtual clock. The fixture uses64MiB simulated storage, brightness40,
the target mapping and repeat1. It is a content proof, not a board-capacity test.

The entire720,160ms loop and restart produced36,012refreshes. All57selected
LED pictures matched the converter's independent file decoder byte-for-byte,
with target wiring and brightness scaling applied. They include each edge,
descent samples, the final hold and the first two pictures after restart.
The player stayed ready with no error or unavailable file.

The recording is389,253,884bytes, SHA256
`d4cbf0edeb5a26cf0a281a7ab54fa0bdce6231aec3afd926c74891c2fc5f2a3e`.
Both original and portable-hash proof runs produced that same recording.
Its local proof is `build/space-scan/emulator-proof-portable/proof.json`;
the large recording stays under build/. The review ZIP includes the small proof.

## Discovered suites and fault-first evidence

- Converter-npm:1,588tests, OK, one Windows filename skip.
- Python converter/library:552tests, OK.
- Emulator:630tests, OK,19platform skips.
- Onboarding:88tests, OK.

Task logs are `build/seed62-task1-npm.log`, `build/seed62-task2-suites.log` and
`build/seed62-task3-suites.log`. The runner retains the newest detailed report
and previous suite summaries in `build/tests/report.json`; older per-run log
directories are removed by its normal retention policy.

Before implementation, the generator tests failed with ERR_MODULE_NOT_FOUND;
after task1 the six new route/pixel/reference/output-protection cases passed.
Before content generation, the artifact test failed with “complete space-scan
artifact manifest missing”. It then passed through the actual full binary,
including independently named camera positions and exact preview comparison.
The draft verifier's newer Python checksum helper failed an API-absence probe;
portable chunk hashing then passed the same full-loop proof. This was a simulated
Python3.10 API absence, not native execution on that interpreter.

## Review, copies and open acceptance

The [review page](../../../project-seeds/62-p2-deep-space-picture-zoom-and-row-scan/source/review/review.html)
has an accelerated sampled full-route GIF and a real-speed five-second excerpt.
Neither is presented as a physical LED observation. Reproduction commands are
in the [source readme](../../../project-seeds/62-p2-deep-space-picture-zoom-and-row-scan/source/README.md).

The collection triplet was copied to the configured shared collection at
`card/space/`. The usual Drive `Artifacts/odrig/` now holds the ODRG, GIF,
provenance readme, `space-scan-review.zip` and `space-scan-delivery.json`.
All eight destination files, including the receipt, passed size/SHA256 readback.
This verifies the mounted filesystems, not an independent Drive API response.
Existing APK, firmware, signing backups and their receipts were untouched.

Physical SD installation/catalog refresh and LED/phone acceptance remain
unperformed. Seed63's ready-made upload feature is planned separately and is
not implemented here; its mixed-root destination question remains open.
The new PR's remote-check availability is reported in the handoff; the base
has no workflow files and reported zero check runs and zero statuses.
