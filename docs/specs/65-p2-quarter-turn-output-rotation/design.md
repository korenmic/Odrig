# Design

## Core state and saved bytes

Use two quarter-turn bits and one saved-read-error bit in Core's existing byte of
bitfields. Measure Core size and drive arena; limits do not change. No heap/frame buffer
is added. Read `rotation.txt` at startup before playback, even if content validation failed.
Its bounded ASCII form is `1 DEGREES\n`, where DEGREES is exactly0,90,180 or270.
Missing means0. Invalid version/length/trailing bytes or a read error means0 with
`error:"unreadable"`. This metadata does not make a show invalid.

`rotation` returns `{ok:true,supported:BOOL,degrees:N,revision:CRC,error:null|"unreadable"}`.
The CRC32 of the single quarter-turn byte is the revision. A valid rectangular legacy
fixture reports unsupported. Missing/invalid content cannot change the installation's
permanent square capability. `rotation set REVISION DEGREES` validates exact
degrees/revision, square support, diagnostics and upload/rebuild contention.
Reject with existing bad-argument/unsupported/busy/in-use/storage-error
codes plus `rotation-conflict` for a stale revision. A same valid value is a no-op;
an errored setting is rewritten even for0. Write the complete bounded text to
`rotation.part`, close, atomically rename to `rotation.txt`, then publish live bits.
Clean failed temporary writes. Read/set returns the complete confirmed rotation object.
Add metadata names to show-install preservation, never reset orientation during installs.

The production firmware initializes an absent/empty `/odrig` store before creating
the core host or caching capacity. A small platform-independent transaction owns an
empty `fresh-init` directory, installs canonical mapping data and an empty show via
verified `fresh.part` writes and destination-absent renames, then removes its marker.
The embedded mapping must equal `mapping/legs-20.json` in host regression tests.
Interrupted attempts can resume only while every existing transaction destination
still equals its default and no unknown file/folder is present. Existing installations
are never repaired by guessing or overwritten. WLED configuration is outside this
transaction and keeps its bytes.

## Rendering

For a square side N, let output coordinates be zero-based with x right and y up.
Inverse source coordinates for clockwise0/90/180/270 are respectively:
`(x,y)`, `(N-1-y,x)`, `(N-1-x,N-1-y)`, `(y,N-1-x)`.
One shared inline index helper takes a canonical output index and returns the source
index. Bypass for diagnostic output,0 or a non-square canvas. `fill_leds` uses this
index before every RGB/palette/layer lookup. Miniature averaging uses the same helper
on each logical60x60 sample; physical `((x+2)*6+y)` placement stays unchanged. Overlay
composition samples background and overlay at the same rotated index exactly once.
Brightness/current scaling remain downstream; decoder/source/clock state is unchanged.

## App and command tool

Add strict rotation reply parsing plus commands.rotation()/rotationSet(). Add serialized
client operations using the existing target/visibility guard and a dedicated Settings
controller. On entry/target/reconnect, read actual rotation and capture target version.
Render the last confirmed value. A user selection queues a revision-bearing write only
while the captured target remains current, visible and connected. After any uncertain
result reread; never replay the write. Disable during loading/saving/disconnection or
unsupported firmware, and show an actionable error/status. Do not modify catalog previews.
Old firmware unknown-command is an unsupported control, not a broken whole app.
odrigctl passes the same read/set grammar. Keep documented command inventories consistent.

## Verification and limits

Add native-core tests before runtime implementation, observe missing-command/unchanged
output failures, then verify all angles against independent coordinate expectations.
Exercise RGB/indexed/layered content and miniature diagnostics, successful reboot/no-op,
bad data and atomic storage failures. Browser checks cover confirmed selection, target
change, queued cancellation, refusal/loss and legacy firmware. Native emulator output
must match the same expectations. Discovered core/emulator/mapping/app suites gate tasks;
standalone APK/FW builds and Windows/Ubuntu CI gate delivery.
Real phone/LED observation remains an owner's check, never inferred from a model.
