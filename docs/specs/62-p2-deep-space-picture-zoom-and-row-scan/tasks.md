# Tasks: deep-space picture scan

Run through TACTIC in order, one task/test/checkbox/proof commit at a time.
This seed's owner questions are resolved. Seed63 remains planning only.

- [x] 1. Implement the deterministic camera route and source generator
  - First add discovered converter tests demonstrating the missing generator;
    observe and record the failing import/feature assertion before implementing.
  - Implement source validation, the twenty timed segments, bilinear60x60
    rendering with correct LED orientation, streamed JSON and both review GIFs.
    Protect existing output directories and make decoding portable.
  - Set the seed state to in_progress. Run discovered converter-npm and
    onboarding suites; tick only this item and commit with the observed failure.

- [ ] 2. Generate and publish the complete animation with previews and provenance
  - Generate all18,004frames, encode/check with the existing converter, create
    the normal thumbnail and reproducible repeat1 demonstration show.
  - Publish collection binary/GIF/readme under the existing size policy; include
    full-route and real-speed reviews with route/checksum/timing evidence.
  - Add artifact regressions; observe the missing artifact assertion fail before
    generating it. Run discovered converter-npm, converter and onboarding suites.
    Tick only this item and commit the content/proof together.

- [ ] 3. Verify a complete emulator loop and deliver the new PR
  - Exercise the actual packed content through the shared core/emulator, including
    a complete virtual loop, final crop and restart. Compare representative LED
    pictures against the file/source at first/last and edge/descent positions.
  - Record checksums, actual commands, discovered emulator results, review and
    shared-collection byte readback; leave physical LED/phone checks explicit.
    Document the portable reproduction/check procedure and any non-owner detail
    resolved during specification at the end of docs/drifts.md.
  - Set software completion state, run relevant discovered artifact/emulator and
    onboarding checks, tick only this item and commit; self-audit task boundaries.
    Push to the new branch, create/attach the requested PR to master, inspect its
    remote checks and fix attributable regressions, then send final notifications.

The seed63 planning commit is separate from these implementation tasks. No board
flash, phone acceptance or upload-feature implementation is included in this run.
