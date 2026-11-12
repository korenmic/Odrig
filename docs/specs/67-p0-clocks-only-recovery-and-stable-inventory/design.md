# Design

Read saved clocks policy using the existing host's open/read contract. Treat
authoritative absence separately from failed opens, incomplete reads and malformed
bytes. Keep uncertain output dark under effective Only, report `clock_error`, and
retry at most once per second. A valid read or verified explicit mode save clears
uncertainty. This uses existing command routes and unchanged hardware/output gates.

The shared app remembers only the current confirmed Only context and desired Clocks
path. Reconcile confirmed status continuously. Resolve unknown folder IDs through
their ancestry without publishing intermediate Root. Missing media becomes a virtual
`clocks` level with a null ID and an explicit unavailable flag. Retry the path on the
existing list timer. Guard Restart clocks while this level is unresolved.

This adapts the recovery behavior directly to master's existing inventory model.
No snapshots, retained keys, inventory revisions, host identity or cache machinery
are introduced. Navigation chosen explicitly by the operator retains master behavior;
the separate navigation-boundary feature is not a dependency.
