# Design: SD capacity without blocking playback

## Boundaries

The core's nullable `drive_space` contract and command schema already represent
mounted/unknown capacity. Keep both unchanged. Replace only the SPI card backend's
synchronous free-space calculation, invalidate stale shared-app reports, and
retain the USB-stick backend's separate existing implementation.

## Incremental FAT reader

Add a platform-independent fixed-memory state machine in
`firmware/usermod/odrig_sd_capacity.h`. Its caller supplies one sector per step;
it exposes the next sector address, pending/known/failed state and 64-bit totals.
It performs no IO, allocation, writes, filesystem calls or scheduling itself.

Begin at physical sector 0. Recognize a valid FAT BPB there, or a single supported
primary FAT partition in an MBR and its BPB in the next slice. Refuse unsupported
partition schemes or ambiguous multiple eligible partitions rather than silently
measuring a volume other than the mounted one. Validate signatures, sector size,
power-of-two cluster size, reserved/FAT/root regions, volume/partition bounds,
cluster count, FAT size and representable sector addresses using checked 64-bit
arithmetic. Support only FAT16/FAT32 classification by cluster count, not labels.
FAT32 active-FAT flags select the table when mirroring is disabled; otherwise use
the primary copy. Reject invalid active indices and insufficient table capacity.

Read one FAT sector at a time. Inspect only entries from cluster 2 through the
last data cluster. FAT16 entries are 16-bit; FAT32 entries mask the reserved high
four bits. A zero entry is free; every nonzero value is allocated/unavailable.
Data capacity is data-cluster count times sectors-per-cluster times 512, and free
capacity uses the same unit. FSInfo free counts are hints and are not advertised
as exact. Publish only after the complete table was consumed for a stable epoch.
Unsupported geometry leaves the card's independent mounted state untouched.

## Backend scheduling and locking

The existing card worker owns discovery. After mounting, reset the state machine;
keep publishing card generation without waiting for it. During discovery, perform
at most one `SD.readRAW` sector read per short worker pass under the existing SD
mutex, then yield before the next pass. Reuse the fixed aligned sector buffer;
do not hold the common core lock or enter `f_getfree`. Raw block reads use the
card driver's per-transfer serialization, not FatFs's whole-allocation scan lock.
Keep regular removal probes/retries and give playback opportunities between reads.
Document that physical read latency remains bounded by the existing host driver
timeout and must be measured on the card; slicing does not manufacture board proof.

`driveSpace` attempts the SD guard with a zero timeout. If busy, absent, generation
mismatched, writing, pending or failed, return -1 without touching output counters.
Otherwise copy both cached uint64 counters while held and release immediately.
No command query performs block IO. The state machine and publication share the
same mutex, preventing torn counters or mixed generations without a new public ABI.

All backend attempts that could mutate external allocation invalidate the scanner
under the guard before touching the file. While `written` exists do not scan. Close
and synchronize the writable handle through the existing close path before
restarting. Rename/remove attempts and abandoned/failed writes also invalidate;
conservative rescan is safer than inaccurate byte-delta estimates (clusters,
directory growth and replacement semantics differ). A failed mutation instead
keeps discovery unavailable until remount: a failed FatFs synchronization may
leave allocation state in RAM newer than the raw on-media table. Remount clears
that unsafe state and resets discovery. This does not revoke mounted write capability.
Unmount publishes absence and drops capacity before another card can be published.

The existing upload transaction remains responsible for out-of-space failures and
catalog/animation publication. Unknown preflight capacity is not a promise that a
file fits. Tests preserve the rollback paths and never fabricate a free-byte count.

## Shared app

The client owns whether its cached `space` reply is still current. On a connection
failure discard that report, as already done for a refused space reply or target
change. A successful future reply restores it. Capacity renderers distinguish no
current report from a confirmed present card whose numeric capacity is unknown,
and from an explicitly absent fresh report. Both Show and Storage share this rule;
existing catalog counting and writable capability remain independent of numbers.
Avoid increasing request deadlines or adding storage-specific polling.

## Verification and release ordering

Extend the compiled real-SD-backend stand-in with synthetic raw FAT volumes and
a deterministic cold-scan delay. First assert that cold `drive_space` does not enter
the monolithic calculation or consume the next refresh/status opportunity: the
old implementation must fail this regression. Then verify one-sector slices,
busy callback, exact counts, partition/active FAT boundaries, mutation invalidation,
removal/remount and IO failure. Use existing compiler discovery for host tests;
supporting a Windows stand-in is distinct from porting firmware compilation.

Run the firmware host suite where supported, discovered core/emulator/app suites,
and a deterministic emulator record/command smoke. Record host limitations honestly.
The owner explicitly deferred firmware compilation to seed 60; do not rebuild it
here. Rebuild the final cumulative APK only after seeds 56–59 software is finished.
Physical cold-card timings, power-safe removal/out-of-space trials and phone
observations are a separate unchecked owner acceptance task.
