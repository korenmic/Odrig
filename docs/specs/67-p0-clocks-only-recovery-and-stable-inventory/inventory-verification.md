# Inventory verification

The shared client retains up to eight complete path snapshots, list/order objects and
preview keys. Reconnection and periodic polling validate board identity and compatible
catalog revisions before permitting actions that use cached IDs. Unchanged authoritative
inventory needs no new listing or catalog pages. Legacy and unmanaged storage receive
bounded full validation; partial or failed pagination never replaces a complete view.

Observed failures before repair:

- An unchanged poll made another full listing and replaced list/key objects; cached data
  had no stale marker (`build/seed67-task2-red.log`).
- Native catalogs lacked board/content evidence. Two different managed cards with equal
  generation and entry counts subsequently produced the same external revision
  (`seed67-task2-core-red.log`, `seed67-task2-media-red.log`). Manifest fingerprints now
  distinguish them independently from inclusion/order changes.
- A permanent failed page caused36 list requests in2.1seconds; background retries are
  now bounded. A local stale-ID rejection falsely reported that the board answered
  (`seed67-task2-backoff-red.log`, `seed67-task2-guard-red.log`).
- An injected index-read failure left metadata authoritative even though listing failed
  (`seed67-task2-index-red.log`). Broken indexes now withhold authority.
- Selection/reorder confirmations waited forever when an unchanged refresh correctly
  preserved its data version. Dedicated validation counters now complete those actions.

Verification on Windows:

- Discovered core suite:1085 tests,11 compiler-specific skips, passed with the supported
  Microsoft compiler (`build/seed67-task2-msvc-core-proof.log`). The GNU test executable
  was quarantined during the earlier run (WinError225); security settings were unchanged.
- Discovered emulator suite:682 tests,19 expected skips, passed
  (`build/seed67-task2-proof-suites.log`). Six native inventory regressions also passed
  after the index-fault repair (`seed67-task2-index-green.log`).
- Discovered app suite:502 tests;501 passed and one initial-screen stand-in timed out
  under load. Its unchanged isolated recheck passed in1.347seconds
  (`seed67-task2-refusal-recheck.log`). The preceding run's separate child-folder fixture
  failure was corrected to wait for confirmed inventory and passed its focused recheck.
- Onboarding:88 passed in the preceding discovered run
  (`build/seed67-task2-final-suites.log`).
- Regression coverage includes real content changes, board replacement at the same
  address, remount, cache identity, lost pagination, stale-action guards, retry budgets,
  preview persistence, Ignore, RepeatThis and playlist-order confirmation.
- Core3792 bytes; drive arena131045 bytes. Limits4096/131072 and512-byte frame guard
  remain unchanged. No frame-time media scan or additional frame buffer was introduced.

These are native-core and shared-browser checks. They do not establish the precise cause
of the owner's physical incident, and board/phone acceptance remains open.
