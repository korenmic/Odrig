# Browsing boundary verification

Observed before repair:

- Direct Back, outside navigation and a prefix collision published respectively
  `''`, `other` and `clocks-other` instead of staying in Clocks
  (`build/seed66-task1-red.log`). The visible Back affordance also allowed the escape
  (`seed66-task1-ui-red.log`).
- A reused folder ID returned another folder's files, which were briefly published
  under Clocks (`seed66-task1-reused-id-red.log`).
- A restart rejected for stale Only status briefly published a board reply despite
  sending no wire command. A watcher trace observed this before repair; sampling after
  the immediate retry had hidden it (`seed66-task1-stale-restart-trace-red.log`).

Shared navigation now validates the Clocks boundary and known folder identity before
changing the trail or notifying watchers. Back stops at Clocks. Returned folder data
must belong to the requested Clocks level before it can replace a snapshot; reused IDs
trigger ancestry resolution. Stale folder controls are disabled. Unknown/disconnected
status retains the last confirmed Only boundary; confirmed Off/Between releases it.
Local stale restart rejection happens before the transport-success path.

Verification on Windows, supported Microsoft compiler:

- Focused boundary, recovery and clock-mode modules:39 passed, including8 new boundary
  cases (`build/seed66-task1-final-targeted.log`).
- Discovered app suite:520 passed. Discovered emulator suite:682 tests passed with20
  expected Windows/compiler skips (`build/seed66-task1-suites.log`, run
  `20261101-025109-147320`,496seconds). No runtime source changed during this run.
- Coverage includes exact/prefix paths, unresolved and reused IDs, valid descendants,
  child reconnect, missing storage, delayed target replies, reload, mode uncertainty,
  disconnection, normal-mode restoration and the actual native player with read-only SD
  media. Existing deliberate-outside-browsing expectations were revised to the owner's
  requested boundary.

Settings/Target and mode exit remain available. Standard button activation shares the
same guarded navigation path. Upload and authoring destination enforcement is the next
task. Physical phone and LED acceptance remain open.
