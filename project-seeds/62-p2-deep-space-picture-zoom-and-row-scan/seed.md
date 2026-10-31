# Deep-space picture at 10x zoom, scanning alternate rows

## Summary

Make one animation from the owner's supplied deep-space pixel-art picture. Keep
the view at 10x zoom and slowly scan it in alternating horizontal rows: begin
at the top-left corner, move to the top-right, descend by one tenth of the
picture's height, move back to the left, descend again, and continue to the bottom.
The owner requests a final view of the bottom-right corner.

The original picture is tracked unchanged in this seed's `references/` folder.
This seed plans animation content; it does not implement a new renderer, change
the firmware or install anything on the board.

## Priority

`P2`.

## Product Context

On 2026-10-31 the owner supplied the picture and requested:

> Create a seed that has a 10 times zoom on this picture into 1/10 of it,
> starting from the top left most corner, slowly moves to the top right most
> corner, then goes down 1/10 row and moves back left, then at the left most
> side goes down another 1/10 row and repeats everything till we reach the
> bottom right. Push that seed with the picture as reference.

The reference is a square, static 1080 x 1080 WebP. Preserve its stars, galaxies,
dark background, colours and pixel-art appearance. Use this exact picture as
the source rather than generating another space scene or reconstructing it.

Interpret 10x zoom as a fixed viewport one tenth of the source width and one
tenth of its height, enlarged to fill the target's 60 x 60 canvas. This is
linear magnification: a 108 x 108 source window, or one hundredth of the image
area. Begin already zoomed in; no opening zoom transition was requested.

Ten non-overlapping rows with alternating directions end at the bottom-left,
not the bottom-right. The owner's endpoint is retained as a requirement, with
the smallest proposed reconciliation and its approval question below. Do not
silently implement a different endpoint or claim that the parity issue is settled.

## Reference

- [Original picture](references/deep-space-james-webb-telescope-v0-jtypls13gcb91.webp).
- [Reference provenance and checksum](references/README.md).
- Original bytes: 88,838.
- SHA-256: `e24ee5296bb539f15dfb5f693b233481a6c9598967963799340dbf4621339135`.

## Required Behavior

1. The first frame shows the top-left 108 x 108 window of the original picture,
   scaled to the complete 60 x 60 target canvas, upright and without mirroring,
   stretching or letterboxing. Keep the same zoom throughout the scan.

2. Describe camera positions in source-image coordinates: the origin is the
   picture's top-left, x grows right and y grows down. If `(x, y)` is the
   viewport's top-left, it always remains within `0 <= x <= 972` and
   `0 <= y <= 972`. Pixel sampling never reads beyond the source or pads an edge
   with an invented border.

3. The first horizontal leg goes continuously from `(0, 0)` to `(972, 0)`.
   At that right edge, descend to `(972, 108)` before moving left to `(0, 108)`.
   At the left edge, descend to `(0, 216)`, then move right. Repeat the pattern
   at row origins `y = 108 * r`, for `r = 0..9`, reaching `y = 972` exactly.
   Horizontal direction alternates right, left, right, left. A descent keeps
   x fixed at the current edge; there is no diagonal shortcut or jump between
   disconnected crops.

4. Traverse the complete width of every row, including both edge crops and the
   last row's bottom pixels. Do not scan only ten stationary tiles or skip the
   details between them. This path covers the whole reference picture.

5. Motion is slow and continuous, with gentle, consistent panning. Exact leg
   durations, pixel sampling and frame cadence are specification work: choose
   and document a deterministic timing and show a faithful preview. Keep the
   source's pixel-art character and legibility at 60 x 60; avoid conspicuous
   shimmer, flicker, smeared stars or newly invented details.

6. The requested final viewport is the bottom-right crop at `(972, 972)`.
   Resolve Q1 before S2S finalizes the route. The recommended reconciliation
   is to finish the ordinary tenth row at `(0, 972)`, then make one additional
   slow left-to-right pass along that same bottom row, ending at `(972, 972)`.
   This repeats the bottom row once without changing the ten row positions,
   the 10x zoom, the first direction or the requested descent size. It is a
   proposal, not an approved extra movement.

7. Treat the complete agreed scan as one animation loop. Use the existing
   playback behavior when the file repeats from its final frame to its initial
   top-left frame. Do not add a fly-back, fade, zoom-out, caption, clock overlay
   or random movement. A demonstration show must allow a whole scan to finish
   rather than cutting it short with a cycle or `max_seconds` limit.

8. Keep a reproducible source or generator with the original image as its
   input. Record dimensions, crop geometry, route, timing, sampling method and
   source checksum so another supported computer can reproduce the animation.
   Pack/check and generate the app preview with the existing JavaScript
   converter; do not introduce a second converter or a new runtime command.

9. Verify the generated content through the existing shared core and emulator.
   Check the first and last view, each edge turn, all descents, source bounds,
   orientation, full route and loop duration. Show representative images and
   a useful moving preview for visual review; a short app thumbnail alone
   does not demonstrate coverage of the entire long scan.

10. Follow the collection's existing animation/preview/provenance and shared-copy
    rules at implementation time, including its policy for files above 50 MB.
    Preserve the original reference bytes. Do not replace an existing animation
    or show, or deploy content merely because this seed was created.

## Technical Constraints

- Target `mapping/legs-20.json`, a 60 x 60 canvas. Source-image top-left coordinates
  must be translated correctly to the project's bottom-left LED coordinates.
- Existing ordinary ODRG frames and the current player are the expected route;
  no new ODRGX type, independent firmware renderer or runtime zoom feature is
  requested. Respect the current format, memory and bounded-work protections.
- Frame times are multiples of 20 ms. Select an appropriate content cadence
  without changing the board's accepted 20–50 refreshes per second rule.
- A long, slow scan can have a large generated JSON source. Use reproducible
  generation and the existing collection/share policy rather than committing
  oversized generated sources or silently shortening/skipping the requested path.
- Generation and verification must work on Windows, macOS and Linux; do not
  require access to a Mac or alter unrelated app/firmware build work.
- Seed61's internal clock/message feature is independent of this animation.
  Do not fold it into this seed or resume it through an unrelated answer here.
- The current request is seed creation and push with the reference only.
  S2S, enqueue, implementation, artifact builds and board/phone checks follow
  a later instruction. Any actual LED/phone acceptance remains the owner's check.

## Open Questions Requiring The Owner

### Q1. Which final path should reconcile the tenth row with the requested corner?

Ten rows beginning left-to-right alternate to a last right-to-left row and end
at bottom-left. The requested bottom-right endpoint needs an additional movement
or a change to one of the stated path rules.

- **A. Recommended:** approve one extra left-to-right pass along the bottom row,
  ending at bottom-right. Preserve all ten row positions and 10% descents.
- **B. Alternative:** finish at bottom-left after the ten alternating rows,
  explicitly changing the requested final corner.

Await the owner's answer before generating the final requirements/design/tasks.
The linear meaning of 10x zoom is stated above; exact slow timing and sampling
are technical specification choices, not additional owner questions.

## Definition Of Done

1. Q1 is answered and the seed/spec route agrees with that answer; no contradictory
   row count, direction or endpoint remains.
2. The unchanged reference, checksum, reproducible source/generator and chosen
   crop/timing/sampling parameters are available to a fresh supported checkout.
3. An animation of the whole agreed scan plays upright at fixed 10x zoom on the
   60 x 60 emulator, with all rows, edge turns and descents visible and in bounds.
4. Automated path/content checks and the relevant discovered suites pass; emulator
   evidence and a moving preview demonstrate the whole route and correct endpoint.
5. The completed animation, preview and source provenance follow the collection's
   storage and sharing rules. Unperformed owner LED/phone checks are stated openly.
6. Creating this seed leaves it planned and does not claim an animation build,
   firmware/APK update, content deployment or physical acceptance.
