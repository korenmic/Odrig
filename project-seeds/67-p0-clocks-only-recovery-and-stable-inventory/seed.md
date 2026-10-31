# Preserve Clocks Only and known inventory during recovery

## Summary

Repair automatic escapes from Clocks Only and unnecessary destruction/reloading of
known app inventory after transient failures. Keep playback inside Clocks, preserve
last-good listings/catalog keys as explicitly stale during revalidation, and refresh
only when authoritative evidence makes that necessary. Never fake firmware readiness.

## Priority

`P0`.

## Product Context

On2026-11-01 the owner reported intermittent return to root playback and a full app
playlist repopulation despite unchanged content. Inspection and controlled local
reproductions used source d39bb3576c17c92a17043852d0e8357e4e9eb2b4. See
[evidence.json](references/evidence.json), with source hashes and explicit conditions.

1. Executing the unchanged client functions: an Only status entered `clocks`; a
   folder recovery with an empty root lookup and an absent managed catalog cleared
   the trail. The next identical Only status left the browser at root because
   `onlyOpened` was still true. `toLevel` cleared the displayed inventory/order.
2. Executing unchanged `heard` after one no-answer: both known catalog key sets were
   discarded and full-list/catalog work scheduled without comparing board identity
   or a content revision. A separate10-second timer also requests full listings,
   and every completed list replaces arrays/increments listVersion even if identical.
3. The actual native core, given valid saved Only settings, played `clocks/face.odrgx`.
   Injecting a startup `read_at` error for that settings file, with its bytes unchanged,
   produced mode Off and root `picture.odrg`. `breaks_start` initializes mode Off and
   returns without retaining an unavailable/unknown mode when that read fails.

These reproduce failure paths, not the exact spontaneous physical incident. Existing
core guards refuse normal root playback while the in-memory mode remains Only; do not
claim those guards were bypassed by the browser test. Investigate mode loss/reset/read
failure and distinguish a UI root view from actual firmware root playback in regressions.

## Required Behavior

1. Only is released by an explicit confirmed mode change, never by a brief network
   failure, folder re-resolution, media change or failed settings read. While active,
   all playback entry/recovery paths remain inside the resolved Clocks subtree; if
   unavailable, stay dark with a reason. Never start a normal root animation as fallback.
2. Treat a failed read of committed clock settings distinctly from an authoritative
   genuinely missing default on a new installation. Retry/resolve uncertain reads
   without emitting normal root frames. A corrupt/unreadable saved mode fails closed
   with an explicit diagnostic until a valid mode is obtained or the operator changes
   it. Do not publish an invented confirmed Off state. Preserve normal default startup
   when settings are authoritatively absent. Establish this distinction through the
   existing host IO contracts or a compatible host-level improvement, not a new wire command.
3. Make automatic client recovery continuously respect confirmed Only, including
   changed folder IDs, remounts, stale replies, temporarily empty listings, absent or
   busy catalogs, reload/reconnect and explicit clock-folder restart. Preserve a valid
   Clocks descendant; use an unavailable Clocks view when recovery cannot establish one.
4. Keep per-board, per-storage, per-path last-good list/order/catalog-key snapshots
   through transient disconnection and revalidation. Mark them stale and gate unsafe
   actions until current target identity/revisions are confirmed. Never reuse another
   board's cache or assume IDs remain valid after a real media/content generation change.
5. Prefer cheap authoritative identity/revision validation; unchanged content must
   not discard keys, previews or completed pagination, reset readiness presentation,
   replace identical arrays/DOM or perform a full rebuild. Coalesce overlapping work
   and use bounded retry/backoff. Refetch only affected paths/storage on actual change.
6. Where old firmware supplies insufficient identity/revision evidence, preserve stale
   visible data while performing bounded validation; do not assert confirmed freshness
   without evidence. Explicit refresh remains possible and must not blank a valid list
   before a replacement succeeds. Failed/incomplete pagination never replaces it.
7. Keep real firmware readiness/integrity/quarantine checks truthful. A genuine board
   reboot or changed file can require validation even if the app has a cached listing.
   Do not skip CRC/fault checks, hide a real reboot or label firmware ready just to
   eliminate a spinner. Separate known inventory, revalidation and playback readiness.
8. Prove the reported unchanged-content scenario with request counts, retained snapshot
   identity and no unnecessary full-list/catalog-page work. Prove a real change still
   invalidates the right cache. Use the actual core for settings-read fault/restart and
   long Only playback across media/folder changes, plus shared browser/native transport
   tests. Every regression task must first fail on the unfixed code and record its failure.

## Technical Constraints

- Relevant code: client.js heard/askStatus/recoverLevel/toLevel/askListPart, breaks.cpp
  breaks_start/read_file, and player.cpp Only recovery guards. Reproduce on the latest
  integrated branch before selecting the smallest repair; preserve earlier watchdog fixes.
- Keep current memory/stack/work budgets, atomic settings, protocol compatibility,
  target guards and diagnostic truth. Do not make hardware/power changes or restart
  the board to recover an ordinary app request. No new wire commands are required.
- Seed66 adds intentional browsing restrictions; this seed repairs involuntary recovery
  and playback/data invariants. Keep task boundaries distinct and agree shared seams in S2S.
- Retain minimized fail-first proofs in discovered core/app/emulator suites. Test absent,
  unreadable and corrupt settings separately; unknown state cannot silently become Off.
- Physical intermittent failure and phone readiness acceptance remain owner observations;
  injected-fault evidence must not be presented as a real-board reproduction.

## Open Questions Requiring The Owner

None. The requested invariants and conservative recovery behavior are specified above.
The cause of the owner's exact intermittent incident remains an implementation
investigation/acceptance item, not an unresolved product-policy question.

## Definition Of Done

Fail-first regressions cover every confirmed path and pass after the repair. Confirmed
Only never emits normal root playback or automatically opens the ordinary root. Stable
same-board inventory survives transient failures without needless full repopulation;
real changes and real firmware checking remain visible and safe. Relevant discovered
suites and emulator checks pass, with request-count evidence and physical limits recorded.
