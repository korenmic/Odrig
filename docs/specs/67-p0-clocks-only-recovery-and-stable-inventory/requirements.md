# Clocks recovery and stable inventory

Source: project-seeds/67-p0-clocks-only-recovery-and-stable-inventory. Owner questions: none.

1. Only playback never falls back to normal root content on read/network/media errors.
   Missing Clocks remains dark with a truthful reason. An explicit confirmed mode
   change releases Only; automatic recovery does not.
2. Distinguish authoritatively missing clock settings (normal new-install default)
   from unreadable or malformed saved settings. Uncertain settings fail closed,
   report uncertainty and retry at a bounded rate until valid or explicitly replaced.
   Never report an invented confirmed Off or emit a root frame while uncertain.
3. Automatic client recovery continuously honors confirmed Only, preserves valid
   descendants, resolves changed folder IDs and uses a virtual unavailable Clocks
   location when identity cannot be recovered. Stale responses cannot reset it.
4. Keep last-good list/order/key snapshots per board, storage and path through brief
   failures and revalidation. Mark stale and gate unsafe actions until identity and
   revisions are verified. Never reuse another board's IDs or changed-media IDs.
5. Cheap identity/revision checks coalesce requests. Unchanged data preserves array,
   DOM, preview-key and pagination identity and avoids full-list/page reloads. A real
   revision change invalidates affected data only. Explicit refresh stays possible.
6. Legacy targets without sufficient evidence retain visibly stale inventory while
   bounded validation proceeds. Failed/partial pagination cannot replace a complete
   snapshot. Real firmware checking, reboot, CRC and quarantine remain truthful and
   distinct from app inventory readiness.
7. Fail-first discovered core/app/emulator tests cover the three recorded faults,
   missing/read-error/corrupt settings, reconnect request counts, reference identity,
   real changes, remounts/target switches and sustained Only playback. Controlled
   injection does not establish the physical incident's cause. Existing memory,
   stack, protocol, atomic persistence and watchdog bounds remain unchanged.
