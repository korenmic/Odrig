# Requirements: SD capacity without blocking playback

Source: [seed](../../../project-seeds/56-p1-sd-capacity-without-blocking-playback/seed.md).
No unanswered owner choices remain. Firmware compilation is explicitly deferred
by the owner's 2026-10-29 instruction to future seed 60; this does not waive host
tests, emulator verification or later board/phone acceptance.

## 1. Responsive mounted storage

1.1. A mounted card SHALL be published immediately with its own nonzero generation,
independently of capacity. Catalog/list/read access SHALL remain available while
capacity is unknown or failed, without rescanning animation bodies or catalogs.
1.2. Every `drive_space` query SHALL read only cached state and SHALL neither start
nor wait for a FAT scan. A busy storage lock SHALL yield unavailable capacity
immediately; the existing 50 ms callback budget SHALL hold for cold and warm queries.
1.3. `space` SHALL preserve the existing schema: unknown capacity is `free:null`
and `total:null`, while a mounted card remains `present:true`. Unknown capacity
SHALL NOT mean absent, corrupt, full or read-only. No command or ABI is added.

## 2. Bounded trustworthy capacity

2.1. Capacity discovery SHALL use bounded, interleavable work on supported FAT16
and FAT32 volumes, including partitioned and unpartitioned cards. It SHALL never
call the monolithic `f_getfree` path through `SD.totalBytes()` or `SD.usedBytes()`.
2.2. One worker slice SHALL read at most one 512-byte sector, do bounded fixed-memory
work and release the storage lock before yielding. No FatFs allocation-table scan
or filesystem-wide lock SHALL be held across slices. Playback reads and commands
SHALL be able to interleave while scanning.
2.3. Valid results SHALL count the actual allocation units with 64-bit arithmetic,
excluding reserved entries and honoring the active FAT. Unsupported, ambiguous,
malformed or failed capacity discovery SHALL remain explicitly unknown and SHALL
not invalidate an otherwise mounted/cataloged card merely for unavailable capacity.
2.4. Publication SHALL be atomic for the card generation and mutation epoch that
were scanned. A partial scan, previous card, or pre-mutation result SHALL never
be returned as the current exact available capacity.

## 3. Mutations and recovery

3.1. Removal, remount, attempted writes, replacements, removals and their error
paths SHALL invalidate capacity before they could change allocation. Discovery
SHALL pause while a writable handle is open and restart from synchronized media
after it closes. A failed/partial mutation SHALL never retain an optimistic cache.
3.2. Capacity SHALL converge again after a quiescent successful mutation or remount,
or report unavailable if discovery fails. Existing generation/writable checks,
safe upload publication and out-of-space refusal SHALL remain intact. No guessed
capacity, new catalog format, partition, dependency or storage rewrite is allowed.

## 4. Honest shared app

4.1. Unknown capacity on a present card SHALL leave its presence, catalog count
and supported write capability distinguishable from a genuine current absence.
4.2. A disconnected/timed-out/refused request SHALL invalidate the old capacity
report as current information. The app SHALL show an unknown/stale state, never
present an earlier absence or byte count as a fresh observation of the target.
4.3. Target changes SHALL discard the former target's storage report; fresh replies
SHALL recover normal rendering. Browser Controller and APK SHALL use the same code.

## 5. Evidence

5.1. A regression SHALL first demonstrate the old cold-query stall, including its
delay to a following refresh/status opportunity, before the fix. Tests SHALL cover
warm/cold/busy queries, sliced FAT geometry/counting, >4 GiB values, failures,
mutations, generation changes and malformed input. Suites SHALL use discovery.
5.2. Emulator checks SHALL verify transport-compatible present/unknown/absent
capacity behavior and continued status/playback. App tests SHALL cover loss and
recovery with both an earlier absence and an earlier mounted report.
5.3. A later approved real-board session SHALL repeat two cold starts, require first
and warm `space` and concurrent `status` within 500 ms on local USB, and observe
20–50 FPS without multi-second gaps. Removal/remount and controlled out-of-space
mutation SHALL retain catalogs and safe publication. The owner SHALL inspect phone
states; unperformed physical observations SHALL remain open and reported in words.
