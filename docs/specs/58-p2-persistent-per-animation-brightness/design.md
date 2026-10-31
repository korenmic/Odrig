# Persistent per-animation brightness — design

## Durable file and cache

Use internal `brightness.txt`, published through `brightness.part`, header
`odrig-brightness 1\n`, records `VALUE f INTERNAL_NAME\n` or
`VALUE x EXTERNAL_PATH\n`. VALUE is canonical0..255; zero is present, not absent.
Reuse repeats' namespace/path rules (external path≤127 bytes). First matching line
wins, consistent with repeats. Maximum512 records, including at most32 external
records across retained cards/paths. Count retained/unlisted entries; never evict.
Updating/removing an existing entry works at capacity; adding beyond either bound
is `no-space`. Document both limits.

Stream validation/copying through bounded scratch. Write the complete part, close
durably, read back/verify, then rename atomically and publish cache changes. Failed
read/write/verification/rename preserves the prior usable cache and published file.
Boot ignores abandoned parts. Missing settings are empty. Malformed/truncated/
over-limit settings log `brightness unreadable`, discard partial startup application
and use defaults. Reject mutation of damaged published settings as `storage-error`
until deliberate repair/replacement; ordinary playback/default edits still work.
A failed runtime update must not clear a previously usable cache.

Cache internal values/presence in existing item padding/flags, applying one file's
value to every item naming it. Keep32 cached external walk positions/byte values,
rebuilt by path at drive take-up. The global32-external-record file limit ensures
every valid external preference fits; absent paths remain durable without cache
entries. Load bounded settings at startup/remount, never per-frame or per media body.
Lookups are bounded, including indexed media.

Extend the existing startup settings/order allocation. Compact private metadata
without narrowing any valid id, walk position, repeat count or cycle-entry index:
full32-bit positions/16-bit repeat counts can use compact repeat records; brightness
positions can be byte-encoded32-bit values plus a byte value. Regroup private Core
fields to remove padding as needed. Keep Core≤4096 and the existing100-item/drive
allocation<131072 tests; record actual totals without raising limits or silently
reducing support. No new per-frame allocation. Independent `read_at` sources or
existing yield boundaries must not corrupt a checker/upload/catalog decoder.

## Shared selection and protocol

One selector returns saved value or `core.brightness`. Scale the actual selected
content before its first visible frame; updating the scale table never changes
the runtime default or restarts a turn. Clock/message breaks and resume choose
their own file's value. Diagnostics/no-animation use the default. Blackout stays
unconditional. Mini uses the same selection followed by its40 cap; WLED keeps its
existing limiter without duplicating selection.

Keep `status.brightness` as default. Add `dimming` object
`{value:0..255,saved:null|0..255,error:null|string}`, or null when persistence is
unsupported. Missing/null is unsupported in the app. `value` is the selected value
before blackout/mini cap, so off controls retain their editable value; mini reports
its powered/capped value separately. Derive saved/value from the same identity as
status animation/file; no animation gives saved null and default value. Damaged
settings report `settings-unreadable`. Verify worst escaped-text/count replies;
encoded-description room may shrink if necessary while normal printable host names
and the1024-byte bound remain intact.

Retain ordinary `brightness VALUE`. For approved save/default forms, validate
shape/ranges first, then show validity and mutation busy state, resolve a listed
animation (`in-use` for cycle/folder, `unknown-id` otherwise), then storage/capacity.
Quarantine does not erase a listed file's preference identity. Storage failures use
`storage-error`, capacity uses `no-space`; unchanged saves write nothing. Reuse
mutation guards for shared write scratch. Extend CLI forms/help, not transports.

Existing host file/rename APIs supply persistence; extend firmware preservation,
explicit settings inclusion/replacement and readback. Never require SD writes.
Use pure host/tool stand-ins on Windows where full Mac firmware tests cannot run;
do not port or run the deferred firmware build.

## Shared app interaction

Extend commands/status and the existing serialized client. Capture target epoch,
animation id and file/path snapshot when editing begins. Retain ordinary controls
for old targets. Supported fresh status determines saved/null; no animation,
unknown state or settings error disables override mutation with an explanation.
Label the default explicitly and identify the current file.

Use one edit controller for slider/number/checkbox. Override dragging coalesces
into a committed save on release; default dragging retains existing throttling.
Checkbox capture uses confirmed status. Dirty valid text commits and reads back
before mode change; invalid text blocks it with the existing range message.
Identity change cancels unsent edits, releases held state and redraws from status.
Sent commands retain their captured target/id; late replies never repaint another
identity. Accepted mutations wait for fresh status. Uncertainty invalidates the
snapshot and never automatically repeats a save. Other-client changes are polled.

Place the labelled checkbox beside the slider responsively, preserving number
field, touch sizes and pinned-panel threshold. No local mode preference or APK-only
behavior. Existing mini indication remains independent of the editable value.

## Verification and delivery

Core/storage-cut tests cover all identities, precedence, playback types, failures,
retention, corruption and bounds. Transport/emulator/tool tests prove preservation
and shared behavior. Browser tests cover identity-safe edits and real-emulator
readback. Observe new fault regressions failing first, then fix and record proof.
Document limits/default-zero/recovery, run discovered supported suites and retain
human acceptance. Firmware compilation is waived; final APK/key follows seed59.

Self-review maps requirements1–5 to selection/protocol, storage, app and proof.
All technical choices are explicit; no additional owner question remains.
