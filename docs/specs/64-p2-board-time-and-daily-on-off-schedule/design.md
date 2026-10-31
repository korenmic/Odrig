# Design: board time and a daily on/off schedule

Requirements: [requirements.md](requirements.md).

## Ownership and bounds

Add civil_time.h/cpp to the discovered core sources. Keep a compact inline state in
Core: monotonic anchor, UTC seconds, zone revision/range/cursor/offset, schedule
minutes/flags/revision and error flags. No new host callback, decoder, heap allocation
or frame buffer. Remain below 131072 host bytes with a drive, 4096 Core bytes, the
1024-byte reply and existing 512-byte compiler stack-frame bound. Use independent
small readers and noinline helpers for storage operations. Compact existing bounded
state only if measurement requires it; do not reduce ID/path/count domains.

Use the core's clamped monotonic time. Advance UTC from the accepted anchor; reaching
the supported UTC limit makes time unusable, never wraps into an invented date.
Keep wall-clock correction separate from every player timestamp.

## Wire contract

The owner's autonomous request authorizes these exact in-scope additions:

| Line | Result |
|---|---|
| `time` | Confirmed clock/zone state. |
| `time zone <base64>` | Validate and atomically install a complete phone-zone snapshot. |
| `time set <utc-seconds> <zone-crc32>` | Set boot-local UTC against the expected zone revision. |
| `schedule` | Confirmed persisted schedule and current override/activity. |
| `schedule set <revision> <on-HH:MM> <off-HH:MM> <on-or-off>` | Atomically replace the pair/enabled flag; retain manual mode. |
| `schedule resume <revision>` | Atomically clear manual mode; retain times/enabled flag. |

Revisions are eight lower-case hexadecimal CRC-32 digits. `status` adds boolean
`timing:true`; old firmware without it remains usable without timing controls.
`time` returns `ok`, `valid`, nullable `utc`, `zone`, `offset`, `revision`, `from`,
`until`, and nullable `error`. `schedule` returns `ok`, `enabled`, `on`, `off`,
nullable `override` (`on`/`off`), `revision`, effective `power`, `active`, nullable
`reason` and nullable `error`. Reads are available during show recovery.

Malformed forms/ranges/base64/schema yield `bad-argument`; unexpected revisions
yield `stale`; no usable zone yields `zone-unset`; unsupported writable callbacks
yield `unsupported`; a conflicting upload/catalog mutation yields `busy`; storage
faults yield `storage-error`. Damaged stored settings/zone are explicitly reported
as `settings-unreadable`/`zone-unreadable`, leaving playback reachable.
Read-only timing commands do not reserve the content lock. Do not add APK USB
transport: existing firmware serial, HTTP and emulator transports share dispatch.

## A compact complete zone snapshot

Store `timezone.bin`; stage `timezone.part`, durably close, verify bytes/schema/CRC
and rename atomically before changing cached zone state. Ignore abandoned parts.
The decoded payload is at most the existing 1500-byte chunk, so one base64 command
fits within the existing 2048-byte line. The fixed 120-byte little-endian header is:

| Offset | Field |
|---|---|
| 0 | Eight bytes `ODTZ0001`. |
| 8, 12 | Inclusive start and exclusive end UTC seconds, uint32. |
| 16, 17, 18 | Initial offset index uint8, offset count uint8 (1..8), transition count uint16 (0..276). |
| 20 | IANA name length uint8 (1..63); bytes 21..23 reserved zero. |
| 24 | Eight signed int32 offsets in seconds (unused entries zero), bounded -86400..86400. |
| 56 | 64 bytes of zone name followed by zero padding; restrict to safe ASCII IANA characters. |
| 120 | Strictly increasing five-byte transition records: UTC uint32 and new offset index uint8. |

The range is within [946684800,4102444800), with transitions strictly inside it.
Require exact size, distinct usable offsets, legal indices and zero unused bytes.
Readback reports CRC and zone name. An identical accepted snapshot writes nothing.
Time setting is refused against the wrong CRC or outside the accepted zone range.
Reset retains zone/rules but always invalidates the epoch. On normal ticks only
crossed transition records are read; time corrections reload the cursor. Cache
the next boundary so ordinary refreshes do no storage work.

The app creates the snapshot from the phone's Intl time-zone rules for 2000..2100
in a worker. Sample at six-hour UTC intervals and binary-search offset changes to the exact
second; validate count/offset bounds and never silently truncate. Cache per current
zone in memory, not indefinitely across OS rule updates. Explicitly report an
unrepresentable zone. UTC/fixed-offset zones use zero transitions. The worker leaves
the UI responsive; browser and APK use exactly the same code and encoded bytes.

## Persistent schedule and manual precedence

Use a small versioned `schedule.txt`, staged as `schedule.part`: ASCII/LF header
`odrig-schedule 1`, then one line `ENABLED ON_MINUTE OFF_MINUTE MODE`, then EOF.
Enabled is 0/1; minutes are decimal 0..1439; mode is 0 auto,1 on,2 off. Reject extra
lines/tokens, truncated records and equal minutes. Its complete CRC is the revision;
when absent, use the canonical default file's CRC without creating the file.
Missing means enabled,18:00,06:00,auto. Validate a whole file
before applying any field; corrupt settings disable scheduling and report an error,
while clock reads and manual LED control remain reachable. Saves verify before
rename, leave the previous complete file after failure, and skip unchanged writes.
Refuse ordinary edits over unreadable settings rather than silently repairing them.

Evaluate scheduling before LED visibility is rendered and before reporting power.
When usable, enabled and not manually overridden, set core.on from the half-open
daily window. A DST jump evaluates the resulting civil minute; a repeated hour
evaluates the same window again. No replay queue or flash write at a boundary.
Otherwise retain startup/manual visibility. Existing manual on/off immediately
sets visibility and override; persist it when supported, reporting storage failure
without undoing that immediate manual control. Read-only hosts remain controllable.
Resume clears only manual mode and requires a matching settings revision. New core
instances reload that mode but never the civil epoch. Time-pair edits and clock/zone
writes do not clear manual mode. Firmware host power integration must distinguish
the schedule's own output changes from external manual requests to prevent feedback.

## App connection and Settings

Add timing command validators and a serialized target-guarded client operation.
Track a successful connection generation separately from status polling, plus the
existing target generation. A timing controller reacts once to a fresh successful
connection, verifies time and compares its per-target last-confirmed sync against
15 minutes. Invalid time bypasses cooldown. Generate/compare zone CRC; write it only
if changed. Set UTC only on a due connection, invalid clock or manual action, then
read back against the same target/zone before recording success/cooldown.

Persist enabled-by-default auto-sync and a bounded per-target confirmation map.
Treat backwards phone time as due, not an indefinite cooldown. Manual sync updates
the same confirmation record. Watch actual zone changes/foreground reconnection;
with auto-sync enabled update a changed zone without moving the UTC cooldown.
No periodic time-sync timer. A failed/uncertain operation is visible and retried only
on a later deliberate connection/action, with no tight loop or stale target replay.

Add a Time and schedule Settings card with confirmed time/zone, Refresh, Sync now,
auto-sync checkbox, enabled checkbox, two HH:MM fields, Save, manual status and
Resume schedule. Preserve typed values while pending/polling, disable conflicting
actions, and show unsupported/unset/error states in ordinary language. Target
switches immediately invalidate displayed timing state and outstanding operations.

## Verification and delivery

Use deterministic core timestamps and browser clock/connection controls; no overnight
wait. Prove new behavior missing before implementation where practical, and any bug
regression must be observed red before its fix. Run discovered suites per task and
the complete board-free runner before delivery. Include real native emulator HTTP
and TCP/byte-feed parity, Android clean/same-key update/launch, firmware build and
offline ESP32-S3 image/source inspection. Preserve existing dedicated signer and
Drive file IDs by overwriting mounted files in place and verifying bytes/inodes.
One PR targets master; retain exact build-source hashes and CI-head evidence.
Physical acceptance remains an explicit unperformed checklist, not a software task.
