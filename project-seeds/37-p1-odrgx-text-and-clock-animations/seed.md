# ODRGX text and clock animations

## Summary

Add a header-selected ODRGX container for three animation types: existing frame-based
ODRG, procedural text and built-in procedural widgets. Text and widget files contain
descriptions and parameters, not a stored frame timeline. The runtime produces their
pictures while they play, with the same behavior on the ESP and emulator.

The shared app creates, edits and previews text and clock animations. Text supports
mixed Hebrew/English, multiline layout and moving oversized messages. The first widgets
are analog, digital and Dalí-inspired melting art clocks, with randomized imaginary
time. Existing .odrg files keep working unchanged.

## Priority

- `P1`

## Depends On

- Seeds 02-04, for the shared player, emulator and firmware.
- Seeds 05-07, for the 60 x 60 canvas, JavaScript converter and content commands.
- Seeds 09, 16 and 17, for the shared app, playlist timing and app authoring/upload.
- Seeds 31-35, for bounded processing, boot-local quarantine, diagnostics, safe content
  updates and managed internal/external catalogs.
- Coordinate inclusion/order and mapping with seeds 29-30. Integrate authoring into
  seed 36's Upload workflow and management into Animations, not a second controller.
  Do not resolve seed 36's external-reordering owner question in this seed.

## Product Context

Current ODRG is a timeline of encoded pictures. The existing HELLO WORLD generator
prepares pictures on a computer and supports only its small hard-coded letter set.
There is no general text editor, runtime text renderer or clock widget.

The owner wants compact animations that retain their meaning: a text message plus
motion, or a clock behavior plus parameters. Moving text should not require uploading
all of its pictures, and changing the motion should not require another recorded video.
The new content remains ordinary named animation items in the same library and playlist.

This deliberately extends the frame-only format/source and runtime decisions. Rendering
known procedural types is not media conversion or execution of arbitrary code supplied
by a file. The existing frame format and converter stay supported.

## Chosen Visual Reference

![60 x 60 melting-clock concept](melting-clock-reference-60x60.png)

The accompanying PNG is the exact 60 x 60 concept discussed with the owner: a soft,
folded watch face with a gold rim, pale face, dark hands and black background. It was
generated with the built-in image tool and reduced to the actual canvas size. It is
a visual reference, not a playable widget, final glyph artwork or proof of ESP speed.

The shape was informed by the draped watches in Dalí's
[The Persistence of Memory, at MoMA](https://www.moma.org/collection/works/79018).
The widget is an original stylized interpretation, not a reproduction of the painting.
The reference's approximate markings and static hand positions are not requirements.
Runtime hands and numerals must be clean and independently renderable.

## Technical Constraints

- Keep container format version, content type and type-specific schema version
  separate. The owner's odrg1/odrg2/odrg3 names identify frames/text/widgets; they
  must not force unrelated types to share one evolving version number.
- Specify magic, lengths, canvas, type/version and required metadata in the header.
  Dispatch by validated headers, not the filename alone. Preserve existing .odrg
  reading and support .odrgx throughout naming, validation, packing and storage paths.
- Procedural descriptors contain validated data, bounded assets/references and named
  built-in effects/widgets. No JavaScript, bytecode interpreter, arbitrary scripts,
  external network dependency or unbounded physics simulation runs from a file.
- The portable C++ core owns playback/rendering semantics. Firmware and emulator
  compile the same implementation. Make the same rendering logic available to app
  preview, rather than relying on a browser's unrelated text drawing or clock model.
- Keep human-readable typed JSON descriptors as the tracked source for text/widgets;
  keep existing JSON-frames sources unchanged. The JavaScript converter remains the
  single compiler/packer for runtime files. Do not expand procedural sources into
  full-frame JSON merely to satisfy the previous source convention.
- Bundle initial font bitmaps/metrics in firmware and the corresponding preview/
  emulator assets, identified and versioned consistently. Do not initially embed
  each message's glyph bitmaps in its file. Measure font flash/RAM costs; if excessive,
  propose the embedded-glyph alternative to the owner before changing this decision.
- Use appropriately licensed font assets. Shared glyphs, metrics and layout rules
  must produce matching pixels on the app preview, emulator and board. Preserve UTF-8
  source text and editable parameters; compact precomputed layout may be stored with
  font/version references, but not a baked frame timeline.
- Correct mixed Hebrew/English ordering includes digits and punctuation. Follow the
  [Unicode bidirectional algorithm](https://www.unicode.org/reports/tr9/), not simple
  string reversal. Initial support excludes niqqud, emoji and additional scripts;
  unsupported input gets a readable error, never silent character loss.
- Use bounded integer/fixed-point rendering consistent with core constraints. Work
  per refresh depends on the bounded canvas/visible glyphs, not walking an arbitrarily
  long message or generating its entire future timeline. Respect existing memory and
  allocation rules; measure buffers, font storage and runtime limits during design.
- Register every type through seed 35's managed catalog pipeline, on supported internal
  and external storage. Save type, compatibility and duration metadata at registration.
  Do not add boot-time timeline generation, payload expansion or full-library scans.
- Keep seed 32's per-boot quarantine, failed gray list entries and safe repair for
  every type. An unsupported widget/font/version is an isolated content fault.
- Keep one command list across all transports. Existing upload/replacement routes
  carry the files; obtain owner approval for any additional command during specification.
  No app-only mutation endpoint or unrelated external-write capability is implied.
- Preserve mapping, output drivers, off state, global brightness and current limiting.
  Any board work uses firmware/fw.py and odrigctl, brightness at most 40, one program
  at a time, no whole-flash erase and no wiring, power or Mac Wi-Fi changes.

## Required Behavior

### Container and ordinary animation integration

1. Read legacy .odrg files unchanged and new .odrgx files containing a frames, text or
   widget payload. Define the frames payload by reusing the existing ODRG semantics,
   not a competing codec. Unknown/malformed headers or versions fail safely.
2. Every type supports the same library identity, compatible canvas checks, upload,
   internal/external registration, listing, ordering, inclusion, deletion and playback
   rules where the storage capability permits. These are ordinary animations, not
   manual-only diagnostic Tests entries. Preserve existing items and their settings.
3. Store enough bounded metadata to list and schedule procedural content without
   enumerating future pictures. A missing font/widget or bad descriptor cannot hold
   up boot, hide healthy animations or require reflashing to recover.

### Text authoring and playback

4. The app has an explicit text-creation workflow with input, font/size, foreground/
   background colors, alignment, motion settings and live canvas preview. Support
   English uppercase/lowercase, Hebrew including final forms, spaces, digits and
   supported punctuation in mixed-direction messages, without niqqud.
5. Support both single-line and multiline text with wrapping. Show the actual target
   canvas in preview. Distinguish reading order from motion direction; moving the
   message must not mirror glyphs or reverse the order inside a mixed-language run.
6. Initial effects are static appearance, continuous marquee, slide-in/out and slow
   back-and-forth panning. Provide applicable direction, speed and pause controls.
   Oversized content must have a complete readable traversal, including vertical
   overflow for multiline text; do not silently leave part of the message clipped.
   Explain in preview when static content needs the slow-pan behavior to be fully seen.
7. Automatic advancement waits until the current complete text pass finishes, even
   if the nominal playlist/cycle switch time arrives earlier. Derive the pass duration
   from layout/effect settings, expose the resulting timing, and preserve legacy
   frame-animation timing. Explicit operator play/stop/removal actions can interrupt;
   the rule must not make controls wait for a long message.
8. Preview, save/export and upload the descriptor as a normal named animation. The
   app can reopen an existing text descriptor, edit it and transactionally replace
   it while preserving its identity, position and inclusion settings. Respect read-only
   media and detect stale edits rather than overwriting another controller's change.

### Clock widgets

9. Provide analog, digital and melting clock modes, with app creation/editing and
   previews. These are art clocks: their displayed hours need not match real time.
   Internet time, time zones, an RTC and accurate wall-clock operation are not required.
10. Generate a fresh random variation when a clock starts a new playback turn,
    including explicit play. Keep a stable seed for that turn and retain it in bounded
    diagnostics so the same run can be replayed. Do not choose unrelated random values
    on every LED refresh or reset the seed on a mere list query or frame delay.
11. Start at a randomized imaginary hour and vary virtual-time speed/acceleration
    smoothly within specified bounds. Use elapsed time and the chosen seed, not the
    number of refreshes, so skipped refreshes do not change the intended trajectory.
    Hands/digits derive from the same virtual-time model. Reversal is not required.
12. Clocks play for 30 seconds by default, editable in the authoring workflow. Store
    the scheduling metadata without rendering the future sequence. Document interaction
    with existing explicit cycle/playlist timing and preserve their operator controls.
13. The melting mode targets a recognizable folded/sagging watch on 60 x 60, with
    moving hour and minute hands attached at one pivot. Render a normal dial and
    hands in clock coordinates, then deform them together onto the soft surface.
    Do not rotate the entire reference image, leave baked-in stationary hands underneath,
    or draw detached straight hands over an unrelated distorted face.
14. Treat the PNG as a design target, not as mandatory pixel-perfect shading or a
    substitute for runtime geometry. Keep contrast and readable moving hands at actual
    LED resolution. Validate the deformation visually in the emulator and on the LEDs;
    record performance before claiming the result works on the ESP.
15. Editing a widget changes its validated settings through the normal replacement
    transaction. Preserve unrelated content, mapping, order and persistent exclusions.

## Definition Of Done

1. One requirements/design/tasks set covers the container, both procedural types,
   shared runtime rendering, app editor/preview, three clock modes and integrations.
   Record the deliberate format/source/runtime extensions in the relevant decisions
   and append-only change log during implementation, not in this planning commit.
2. Format/compiler/core tests cover all types, legacy byte/pixel/timing compatibility,
   unknown types/versions, malformed lengths, bad UTF-8, missing fonts, resource limits,
   wrong canvas, truncated assets and interrupted registration. Observe regressions
   before fixing them and run applicable suites by discovery.
3. Golden text cases cover English, Hebrew/final forms, mixed numbers/punctuation,
   multiline wrapping, every motion, oversized horizontal/vertical traversal and
   rejection of unsupported characters. Exact preview/emulator/runtime pixels agree.
4. Tests prove text is not cut off by automatic advancement, while manual controls
   stay responsive. Check ordinary playlist and cycles, inclusion, replacement and
   existing legacy timing. Cataloged duration agrees with actual completed passes.
5. Clock tests replay captured seeds, verify fresh variations per new turn, equal
   virtual time for hands/digits and smooth bounded motion at irregular refresh times.
   Analog, digital and melting modes render on the target canvas without whole-timeline
   allocation. Inspect changing hand positions, not only a static concept image.
6. Browser tests cover create/edit/preview/save/upload, compatibility feedback,
   read-only destinations, stale edits, failure/cancellation and preserved identity/
   order/inclusion in the shared app. Integrate with seed 36's navigation and style.
7. Verify new types through managed internal and PC-prepared external catalogs,
   changed external metadata reload and per-boot quarantine without routine rescans.
   Bad procedural content does not block boot, the list or healthy playback.
8. Measure actual font footprint, renderer memory, worst work slices, command latency
   and ESP refresh rate. Existing 20-50 refreshes per second is the accepted range;
   do not claim performance from desktop rendering alone. Build the APK and applicable
   firmware variants through repository tools and run locally supported suites.
9. An owner checks Hebrew readability, movement and the melting clock's attached
   moving hands on the real 60 x 60 LEDs and the app on a phone. Report unavailable
   checks explicitly and exactly what firmware/show/settings remain on the board.

## The Owner's Answers

On 2026-10-24:

1. Keep initial fonts in firmware. Consider embedding per-file glyphs only if measured
   font size becomes excessive; that fallback is not the selected initial design.
2. Support mixed Hebrew/English with numbers and punctuation, without niqqud initially.
3. Include analog and digital art clocks and a Dalí-style melting clock with moving
   hands, subject to the actual 60 x 60 visual and runtime checks.
4. Support single-line and multiline text, not just one-line marquee.
5. Generate a fresh random clock variation per playback and retain the seed for
   debugging, rather than storing one permanently repeating random sequence.
6. Finish the complete text pass before automatically switching to the next animation.
   Clocks default to 30 seconds, editable.
7. The approved consolidated scope includes the header-selected container, backward
   compatibility, text effects, app creation/editing/preview, catalogs and bounded
   runtime rendering. Seed creation does not implement or flash these features.

## Open Questions

None about the approved product scope. Header layout, concrete font choice, supported
limits, implementation structure and measured execution budgets belong to specification.
Any newly required command or departure from the approved font policy still needs the
owner's approval before implementation.
