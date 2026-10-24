# Bounded decoding and responsive fault handling

## Summary

A malformed, truncated, expansion-heavy or unreadable animation must not prevent the
board from completing startup, answering commands or making progress. Bound and resume
decoding, validation, error inspection and media access rather than doing unbounded work
while the core lock is held. Keep watchdog protection enabled.

This seed supplies the execution safety needed by seed 32: a bad animation can be
reported and skipped instead of trapping the board in a freeze or reboot loop.

## Priority

- `P0`

## Depends On

- Seeds 02 and 04, for the shared core and its firmware host.
- Seeds 07, 14 and 20, for upload validation, startup checking and removable media.

## Product Context

The board investigation reproduced a task-watchdog reset loop with a 65,262-byte
malformed compressed input whose decoded tail is 64 MB. The first frame already has
an invalid palette index, but OdrgDecoder::settled continues inflating the tail to
resolve error precedence. This runs under the core mutex on CPU0. Commands wait for
that mutex, the idle task is starved, and the five-second IDF watchdog resets the board.

Matching ELF files and serial backtraces identify the path. With identical input, a
control that returns the known error without draining stays responsive. That shortcut
is not the production solution because it changes error precedence. The experiment
proves a robustness defect; it does not establish the cause of earlier transient
rejections of the owner's valid animations.

## Technical Constraints

- Playback and validation rules belong to the shared C++ core, used by the emulator
  and every firmware. Hosts provide bounded I/O, scheduling and lock ownership.
- Preserve deterministic format-error precedence across yields. Do not hide the
  defect by weakening format checks, swallowing I/O faults or disabling watchdogs.
- Specify work, expansion and supported-input limits explicitly and consistently
  across the core and format readers. A yield is pending work, never a file error.
- Keep current memory constraints and allocation rules. Do not buffer a complete
  animation or decompressed tail in RAM.
- An I/O call that can block must have a bounded timeout or an asynchronous handoff;
  bounding decoder instructions alone does not bound the entire core call.
- Firmware is built and flashed only through firmware/fw.py; board commands use
  odrigctl. One program at a time, brightness at most 40, no whole-flash erase,
  hardware/power changes or changes to the Mac's network connection.
- No new operator command is required by this seed. Any needed protocol extension
  must be proposed to the owner, not invented during implementation.
- Any refresh rate from 20 to 50 is acceptable. Do no work merely to raise a rate
  already inside that range.

## Required Behavior

1. Bound work in startup, ordinary playback, late-frame catch-up, installed/external
   validation, upload validation, decoder error settlement and file/media operations.
   No malformed input can monopolize a task or the core mutex indefinitely.
2. Preserve continuation state between work slices. Commands and other necessary
   firmware tasks get service between slices, including before the first valid frame.
3. A bad file present on every startup cannot cause an endless reboot loop. Startup
   reaches a responsive ready, degraded or recovery state even when no animation is
   usable; seed 32 defines per-file quarantine and continued healthy playback.
4. Keep watchdogs active and demonstrate that their protected tasks actually progress.
   Feeding a watchdog while commands remain blocked is not acceptance.
5. Preserve enough bounded fault context for seed 33 to report the affected file,
   operation, decoder position and final reason without needing another full decode.
6. Determine and document measurable command-latency, work-slice and media-timeout
   budgets during specification, justified against valid dense content on the board.
7. Preserve results for the existing valid assets and deterministic fault vectors.
   If a documented resource limit is reached, return a controlled reason and let
   seed 32 isolate the file instead of freezing or restarting the whole player.

## Definition Of Done

1. A deterministic regression reproduces the unbounded-error path before the fix.
   Preserve a generator/fixture for the small compressed file with a huge bad tail;
   do not depend on ignored build artifacts or install it as an ordinary animation.
2. Core tests cover truncation, excessive expansion, malformed frame records, delayed
   and failed reads, missing media, startup and repeated playback/validation. Check
   yields, eventual outcomes and unchanged error precedence, not just final rejection.
3. Host/emulator tests measure command responsiveness while faults are processed.
   All applicable suites selected by discovery pass, with sanitizers where available.
4. On the board, the reproducer no longer causes watchdog resets or command lockout.
   Exercise startup and playback faults, record firmware identity and reset reasons,
   and compare measured worst-case latency with the specified budgets.
5. Existing healthy animations still play in the accepted refresh range. Preserve the
   installed show and settings, report what is left on the board, and explicitly
   identify any unavailable hardware verification.

## The Owner's Answers

On 2026-10-24 the owner approved this fix as a new seed and made responsive boot in
the presence of corrupt animations mandatory. Per-boot skipping and grayed-out app
entries are owned by seed 32, not left as optional follow-up work.
