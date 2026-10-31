# Requirements: deep-space picture scan

## Resolved scope

Source: [seed62](../../../project-seeds/62-p2-deep-space-picture-zoom-and-row-scan/seed.md).
The owner approved the extra final left-to-right bottom-row pass. No owner
questions remain. Implement this animation in a new PR; seed63 is planning only.

1. **Reference and geometry.** Use the unchanged 1080x1080 WebP with SHA256
   `e24ee5296bb539f15dfb5f693b233481a6c9598967963799340dbf4621339135`.
   Render a 108x108 viewport onto 60x60 LEDs throughout. Begin already at10x
   linear zoom, upright, with no mirroring, borders or aspect distortion.
2. **Route.** Viewport origins use image coordinates, x right/y down. Start(0,0),
   traverse to(972,0), descend108 at that edge, return left, and continue over
   ten rows at y=108*r,r=0..9. Descents keep x fixed. After row10 finishes at
   (0,972), traverse that bottom row once more to(972,972). There are eleven
   horizontal passes and nine descents, without out-of-bounds or diagonal jumps.
3. **Motion and completeness.** Pan slowly and continuously through every row,
   including both edge crops and intermediate views. The last frame is the
   bottom-right crop. Treat the entire route as one loop with the existing
   final-to-first restart; add no fly-back, caption, fade or zoom transition.
4. **Determinism.** Specify exact times, cadence and pixel sampling. Preserve
   recognisable stars/galaxies and pixel-art structure with deterministic
   downsampling; no generated scene details. Keep the original file untouched.
5. **Existing pipeline.** Generate a reproducible JSON frames source and use
   the existing JavaScript converter for ODRG encoding/checking/packing and
   preview encoding. No player changes, new runtime command or firmware format.
6. **Portability and bounds.** Generation and checks run on Windows/macOS/Linux
   using pinned repository dependencies. Stream the large generated JSON rather
   than retaining it during generation. Keep oversized generated sources under
   build/. Follow the collection's >50MB/share rules for the final binary.
7. **Proof.** Automated checks cover exact vertices, directions, descent count,
   continuous interpolation, timing, bounds, final hold, sampling and LED
   orientation. The generated ODRG agrees with the intended frame pictures;
   actual shared-core/emulator evidence verifies readable content and playback.
8. **Review and collection.** Include a clearly labelled accelerated full-route
   moving review, a real-speed excerpt, a converter thumbnail, reproducible
   provenance and collection copy. The demonstration show allows a complete
   loop rather than imposing a shorter turn cap. Copy completed collection
   artifacts to the configured shared collection with byte readback when mounted.
9. **Handoff.** Run appropriate discovered suites, tick/commit one task at a
   time, open the requested new PR to master and report remote check availability.
   Keep any unperformed physical LED/phone acceptance explicit. Do not flash
   a board or replace installed app/firmware to deliver animation content.
