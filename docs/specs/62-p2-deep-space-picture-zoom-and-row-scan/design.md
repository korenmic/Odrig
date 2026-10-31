# Design: deep-space picture scan

## Source and ownership

The source generator lives beside the seed under `source/generate.mjs` and
imports the existing converter's media-decoder and preview APIs. Its only
animation input is the checked-in reference. Verify SHA256 before decoding;
verify the decoder returns exactly one1080x1080 image. Reuse pinned
ffmpeg-static from converter/node_modules, with no global image library or
platform-specific path. Existing converter/library/core behavior is unchanged.

The generator writes a new output directory, refusing to replace an existing
directory. It emits `space-scan.json`, a manifest, review GIFs and a review page.
Only reproducible code, tests, original reference and small review artifacts
are tracked as sources. The large JSON is an ignored build product.

## Route and time

Build an ordered list of segments: for r=0..9, one horizontal pass at y=108*r,
right on even r and left on odd r; add a108-pixel downward segment after all
but the last row. Append a final rightward segment from(0,972) to(972,972).
Camera interpolation is linear inside a segment and continuous at shared
vertices. Clamp queried time to the beginning/end; reject non-finite times.

Each horizontal segment lasts60,000ms. A descent lasts6,680ms, approximately
the same source-pixel speed. Frames last40ms(25content frames/second), a
multiple of20ms. The twenty segments take720,120ms; include the exact final
camera position for another40ms. This yields18,004frames and720,160ms per
loop. All segment boundaries lie on the40ms grid. A show with repeat1 and no
max_seconds demonstrates one whole loop. Existing clock interruptions, if
enabled by an operator, retain their existing behavior.

## Pixels and memory

Read source pixels in ordinary top-row-first image order. Sample the centre
of each output pixel within the108x108 window: source coordinate
`origin + (output + 0.5)*108/60 - 0.5`. Bilinearly interpolate adjacent source
pixels in encoded RGB, round half up and clamp to0..255. Coordinates remain
inside the image; this small reconstruction filter provides fractional camera
motion while retaining the source's block structure. Do not quantize or replace
colours in the ODRG source. Store output in bottom-row-first RGB order required
by ODRG, reversing the image row only once. Small asymmetric fixtures verify
sampling and orientation independently of the reference picture.

Keep the decoded image and one output frame in the generator's main loop.
Write JSON frames incrementally with Node's filesystem API, preserving UTF8/LF.
The converter remains the single encoder and may read that source through its
existing API. Rendering and encoding are separate bounded build stages, not a
new runtime path. Progress messages identify emitted-frame counts. On a failed
run leave its owned build directory for diagnosis; never clean another path.

## Review and generated content

Use the converter's `thumbnail.encode` for two additional GIFs from the same
rendered pictures: a full-route overview sampled every2,000ms with all segment
vertices/final endpoint included, and a first-five-second excerpt at real40ms
cadence. Label the overview accelerated/sampled, rather than representing its
speed as the installation's speed. A small static review page shows both with
the original reference and route/timing details. Converter `thumbnail` creates
the ordinary app/catalog preview from the final ODRG.

Encode with `node converter/odrig.js encode`; inspect with `check` and verify
the binary through both the existing reader and the actual emulator. Store
`space-scan.odrg`, its normal GIF and provenance in collection/card/space/ if
the binary is <=50,000,000bytes, otherwise follow collection/long/ and the
configured share rules. The provenance includes image/binary checksums,
source revision, route, sampling, full loop length and reproduction commands.
Do not truncate the scan to reduce size. Keep a repeat1 demonstration show
separate from the owner's installed show; mapping remains legs-20.

## Verification and failure handling

Discovered converter tests import the generator module. Establish the missing
feature with the new tests failing before implementation; record the observed
failure in the proof commit. Test the expected segment coordinates with an
independent vertex list, all temporal boundaries, many in-bounds intermediate
samples, end clamping/hold and synthetic pixel grids. Validate reference hash
and refuse an existing output destination or a changed input.

Artifact checks validate the encoded file's full loop, first/last images and
representative corner/descent views against independently specified geometry.
Record emulator output from the actual ODRG and compare decoded LED RGB to the
file reader/reference at selected times, with brightness accounted for. Complete
at least one virtual loop, including restart, in the proof run; do not infer it
from a preview. Reuse existing core build/record APIs and end every owned process.

Run converter-npm and onboarding for task1, converter-npm/converter/onboarding
for task2, and discovered emulator plus relevant artifact tests for task3.
New regression tests must fail first when correcting a fault. Do not claim
that native Windows evidence is a Mac or physical-board test.

## Spec self-review

Requirements cover all seed behaviors and the approved endpoint. The route
has ten distinct row positions, nine descents and eleven passes; no parity
ambiguity remains. Times are40ms-aligned, image bounds are finite, and the last
frame includes the exact endpoint. Generator and converter responsibilities
are separate; no new protocol/hardware decision is needed. Owner LED/phone
checks, seed61 command approval and seed63 root selection are separate matters.
