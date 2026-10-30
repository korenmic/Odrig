# Message clock widgets and clocks-only mode — design

## Ownership and compatibility

Use the existing type3 ODRGX container, shared converter renderer and C++ drawn
player. Add widget subtype6, `message-clock`, beside existing subtypes1–5 without
changing their formats or validation order. Python independently reads/validates
the new payload. Browser preview imports the same converter implementation; the
emulator/firmware use the same core. Ordinary authoring controls do not gain the
source simulator's tabs/sliders; these generated widgets may be previewed/uploaded,
but unsupported editing must be explicit rather than corrupt their payload.

The player already holds a drawn payload in its32768-byte inflate window and
draws into existing RGB pixels. Reuse both; do not allocate message state per frame
or introduce a decoder/browser dependency on the board. Keep Core≤4096 and the
existing100-item drive allocation≤131072, with no supported domain narrowed.

## Message payload and source

Subtype6 is fixed60x60 and payload version1, at most32768 bytes. All multibyte
fields are little-endian. Pixel order is row-major from the top; two4-bit alpha
samples share a byte, earlier sample in its high nibble. These are static font/mask
assets, not an animation frame stream: time, fades, digits, stops, sweep and square
are evaluated at runtime.

The24-byte head is: widget byte6 at0, payload version1 at1, source tab1..7 at2,
caption count1..24 at3, loop milliseconds u32 at4, total UTF-8 text bytes u16 at8,
zero u16 at10, caption-mask offset u32 at12, glyph offset u32 at16, and complete
payload length u32 at20. Require exact derived offsets and lengths, no overlaps,
gaps, trailing bytes or arithmetic wrap. Outer loop/payload lengths must agree.

Next are count12-byte records: duration u32, flags u8, zero u8, text offset u16,
text length u16, zero u16. Text offsets are contiguous from zero; lengths1..256,
combined text≤4096. UTF-8 is strict, without NUL/control characters. Flags are
countdown1, zero-subtitle2, motion-stop4, square-freeze8, boosted-roll16; other bits
are invalid. Countdown duration is2000ms, other records6100ms; derive loop from
their sum. Stop is allowed once in tab1; freeze/boost only in tab6; countdown and
zero-subtitle only in tab5, without combining those two. Record flags and masks
are emitted from the exact retained source; generated-artifact tests additionally
compare every original caption/role/order, rather than making arbitrary valid
payloads depend on one set of hardcoded strings.

After text come count fixed900-byte caption masks (60x30 alpha4), then62 fixed
64-byte glyph masks (8x16 alpha4): ten digits for each of six positions, then two
colons. Crop x origins are2,9,23,30,43,50 for numeric positions and16,36 for colons;
clock crop top is34. Compile each slot's clipped glyph separately to preserve the
source's6.9px spacing. The worst permitted layout is29976 bytes. Validation can
stream head/records/text/assets with bounded scratch; playback keeps the whole
payload in the existing window. Truncated/unknown/bad settings/loop/size/trailing
data retain existing rejection categories and never reach unchecked drawing.

Reproducible Node generation extracts the seven source sequences and flags from
the retained HTML, verifies its tracked SHA, and compiles font masks offline.
Use the repository's authored Hebrew small font and scaled large-digit font,
with existing bidi/wrap logic, as the explicit portable adaptation of Arial and
monospace. No system font is redistributed or required. Area sampling/alpha4
quantization and9px line spacing are specified by the generator; record the font
source/hash and visually compare source/portable output at fixed times. Source
decorative unlit dots/background are deliberately excluded from physical pixels.

## Deterministic runtime

Use elapsed time modulo declared loop and an explicit nonzero turn seed. Start
digits from xorshift32(seed) modulo86400 seconds (24-hour initial HHMMSS). Replay
at most floor(loop/2000) clock ticks, fewer than74, from the seed to the requested
motion time. The source rolls seconds modulo digit10 with its own carry behavior;
do not silently normalize subsequent random wheel values to conventional time.
Per tick draw minute/hour chance first, then their directions only when selected,
using exact integer probability comparisons to14/100,45/1000, or48/100 and25/100
during the boosted caption. This replaces Date/Math.random without state leakage.

Normal motion time is elapsed. At the motion-stop caption boundary S, for
u=clamp(t-S,0,3500), use the fixed integer integral
`S + u - floor(u^3/3500^2) + floor(u^4/(2*3500^3))`, held after3500ms; before S use t.
Renderers use identical floor rules and existing sine interpolation. This is the
deterministic continuous version of the source's frame-integrated smooth stop;
record its bounded boundary difference during visual comparison. Clock ticks
occur every2000ms of motion, digit rolls last500ms of motion using smoothstep;
stopped digits stay lit. Boost only occurs in nonslowing tab6, so its event-caption
lookup uses the event's real time. Square position is29.5+26.5*cos(motion*2pi/4000),
rounded as the source and covering its centre±1 in rows57..59. Freeze it at the
specified caption boundary without stopping that tab's clock.

Each caption fades linearly for600ms, holds5000ms, fades500ms; countdown is steady
for2000ms. Zero-subtitle masks retain zero and the two wrapped subtitle rows.
Sweep repeats every9000ms for1500ms, centre=`progress*1.35-0.15`, half-width0.07,
RGB90/205/255 where text strength exceeds0.03; otherwise white. Physical background
is zero, source strength≤0.015 is black, and clock/square never blink or fade
during stops. Use fixed-point arithmetic and exact JS/C++ vectors for masks,
rolls, fades, wave, stop boundaries, loop end and arbitrary seek order.

## External inclusion settings

Internal Ignore stays in show.json. Extend the same command/UI/eligibility model
to general external files/folders through internal `ignored.txt`/`ignored.part`:
header `odrig-ignored 1\n`, then `f FULL_PATH\n` or `d FULL_PATH\n` for own ignored
choices. Absence means included. Namespace/kind/full path distinguish identity;
retain absent paths. At most128 records including retained paths, no eviction;
adding at capacity is `no-space`, removing/updating existing records still works.
Path rules match existing external preference identities. First duplicate wins.
Malformed files report/log settings trouble and safely apply no partial exclusion;
reject mutation until deliberate repair. Use bounded read, durable part close,
readback verification and atomic rename; failure preserves published bytes/cache.
No SD write or animation/catalog modification is involved. Firmware tool inclusion,
preservation/replacement/readback adds this operator settings file.

Cache128 compact5-byte kind/full32-bit-position records in the existing order
allocation. Resolve paths on tree publication/remount/index mutation. A file record
stores walk position, a folder record ordinal; folder subtree ranges come through
existing bounded index lookups. Reduce FileSource and DriveIndex read caches from
512 to256 bytes, using actual capacity at every refill; retain the full512-byte
quarantine fingerprint independently of one refill. Preserve full line, path, ID,
count and decoding-work domains. Three cache blocks recover768 bytes for the
640-byte preference cache and mode/message-bag state. Prove exact allocations,
stack limits, unchanged quarantine behavior and index lines spanning refills.

Separate physical/manual availability from automatic eligibility. One helper adds
own/ancestor exclusions to availability for every automatic traversal/bag/prepared
candidate. List rows add `ignored` and `inherited_ignored`, including folders;
inherited state is derived, never stored as the child's own preference. Snapshot
borrowed index rows/paths before a settings read can replace the host read cache.
Ignore changes revalidate current automatic turns and prepared candidates at the
next safe refresh; they do not ban explicit manual play inside the mode boundary.

## Modes, bags and playback enforcement

Store0/1/2 in the existing clocks_on byte for Off/Between/Only. Keep public boolean
`clocks` true for either enabled mode and independent `clock_message`. Add
`clock_mode:"off"|"between"|"only"` and nullable `clock_only` status with resolved
Clocks folder ID and state `playing`, `no-card`, `missing-folder`, or `no-clocks`.
No new refusal category: outside play/display diagnostics in Only are `in-use`.
Preserve the1024-byte status bound, reserving metadata space and testing longest
escaped host/file values rather than increasing the bound.

Write `odrig-clocks 2\nmode off|between|only\nmessage on|off\n` atomically;
strictly accept old v1 off/on files and retain message flag. Missing/invalid
settings recover Off with a diagnostic. No-op writes nothing; failed writes never
publish a changed mode. Approved CLI forms are the existing off/on/message forms
and additional `clocks only` only.

Use resolved `clocks`/`clocks/message` direct-file ranges and separate shuffled
bags (existing clock key/next/count plus a message key/next/count). Test eligibility
again when selecting a candidate; ignore changes need not prematurely reshuffle
the remaining permutation. Media/index generations invalidate raw ranges/bags.
Message turns play one whole declared loop, including the existing message; no
30-second cutoff. Clock-face turn duration otherwise retains existing behavior.

Only is a distinct automatic scheduler branch, with no ordinary break recursion.
Use the existing break phase for clock/message turns and existing normal playlist
path/window as the saved normal selection, not as the exclusive-mode selection.
Do not persist Clocks over the normal path. Re-resolve normal path on exit; never
restore a transient ID or paused break. Central helpers enforce subtree membership
before every explicit and automatic playback/diagnostic entry, including cleanup,
resume and folder-window rotation. When no clock qualifies, hold Only dark and
responsive and retry on relevant media/settings changes, without outside fallback.

## Shared app and delivery

Status normalization supports additive mode/inclusion metadata; older booleans
map to Off/Between with Only unavailable. The dropdown and message checkbox follow
confirmed status and target epochs, handling pending/refusal/timeout honestly.
Entering Only opens the resolved folder once per target/mode transition; ordinary
browsing then stays where the operator chooses. Disable outside Play with an
explanation; global restart sends `play <resolved-clocks-folder-id>`, while raw
`play all` is refused as the seed requires. Core enforcement remains
authoritative even for stale lists or another client. Folder and external row
menus expose own Ignore/Include and distinguish inherited exclusions.

Track seven generated files, source metadata, GIFs and standard.md provenance,
preserving the old message. Rebuild thumbnail metadata by discovery, copy to the
configured share and verify bytes. Update public format/command/show/core/app/
emulator/firmware-additions docs and append technical resolutions. Run discovered
supported suites plus deterministic renderer and emulator integration smokes.
Final APK/key and firmware builds/uploads follow seed60. Physical SD, board and
phone acceptance remain a separate unchecked task.

Self-review: ownership, encoding, deterministic source adaptation, fixed-memory
settings, all playback boundaries, migration, app compatibility and deployment
map to requirements1–6. No new command or owner choice beyond approved forms.
