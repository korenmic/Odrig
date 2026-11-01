# Design

## Saved policy

The host's sequential `open` distinguishes missing (0) from error(-1), unlike
`read_at`. Probe once at startup before playback, close promptly, then parse through
the existing bounded64-byte reader. Only authoritative absence selects default Off.
Read errors and invalid schemas set a small uncertainty flag and effective fail-closed
Only policy. Block clock selection/manual playback while uncertain so output is dark.
An additive nullable `clock_error` status field reports the uncertainty without
changing existing `clock_mode` or `clock_only.state` enums. A bounded retry uses
independent reads and cannot disturb the player's open file. A successful explicit
clock-mode write clears uncertainty even if its mode equals the conservative effective
mode. A message-only write cannot guess the missing saved policy. Atomic verification
and no-op behavior remain intact for confirmed settings.

## Automatic recovery

Replace one-shot `onlyOpened` with continuously reconciled confirmed policy. The
client represents unresolved Clocks as a virtual location with reason/staleness rather
than a null-ID ordinary root. Resolve actual Clocks and nested IDs under target and
navigation guards; only publish a complete verified path. Recovery cannot clear a
confirmed Only trail. Seed66 subsequently constrains deliberate navigation.

## Inventory

Separate connection/status freshness, inventory freshness and firmware readiness.
Retain last-good snapshots and key maps through transient errors. Use target/board,
storage, path and authoritative content evidence as cache keys; bound the cache.
Prefer existing catalog generations and validated identities. Where needed, compatible
additive status metadata may expose identity/revision evidence without a new command;
only report an authoritative token if all list-affecting mutations invalidate it.
Insufficient legacy/unmanaged evidence uses bounded full validation with stale data
still visible. Unknown identity gates mutations; actual identity changes discard all
old-board IDs. Real media/generation changes invalidate affected snapshots and keys.

Unchanged complete lists and orders preserve object/array identities and versions.
Incomplete/failed pagination never replaces the committed snapshot. Cheap periodic
validation coalesces reconnect/poll/explicit work; explicit refresh can force listing
without first clearing it. Genuine core readiness remains the actual status progress,
including reboots and CRC checking. Previews continue using unchanged key objects.

## Proof and constraints

Tests use the actual native core with injected host read errors and separate missing,
malformed, transient and permanent cases. Browser scenarios retain references and count
wire requests across reconnect and real changes. Existing automatic-recovery traces
become regressions. Run discovered core/emulator/app suites for touched layers. Keep
arena131072, Core4096, command/reply/frame/stack bounds and scheduler fairness; use
small state flags, not a new canvas or unbounded core storage. Document controlled
faults separately from the unobserved physical incident.
