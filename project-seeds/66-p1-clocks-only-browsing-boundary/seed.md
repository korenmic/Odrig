# Browsing stays inside Clocks in Only mode

## Summary

While Clocks Only is selected, restrict user-visible browsing to the resolved Clocks
folder itself and its descendants. Root, parents and unrelated folders cannot be
opened through Back, breadcrumbs, ordinary rows, restored navigation or other app
entry points. Missing/unavailable Clocks shows an explicit Clocks-unavailable view.

## Priority

`P1`.

## Product Context

The owner explicitly requested this restriction on2026-11-01. It replaces the older
seed59/show.md policy that allowed unrestricted browsing in Only while refusing
outside playback. Current client.enter/back have no mode boundary; automatic entry
on the first Only status is not a navigation guard.

## Required Behavior

1. On confirmed entry into Only, display Clocks if the current folder is outside it.
   Preserve a current descendant instead of jumping upward on every status poll.
   Include Clocks itself; do not mistake a string prefix such as `clocks-other` for
   a descendant. Resolve the authoritative folder identity/path for the active media.
2. At Clocks, hide or disable Back/upward breadcrumbs. Below it, Back stops at Clocks.
   Enforce the same boundary in shared navigation functions, not only visible buttons.
   Handle keyboard/back actions, saved navigation, direct client calls, target changes,
   reloads and delayed replies. No frame may briefly reveal an unrelated folder.
3. Keep Settings/Target and the explicit control that leaves Only accessible. This is
   an app browsing boundary, not a new filesystem security model or a ban on every
   background metadata read. Shared protocol listing remains compatible.
4. While the board is temporarily unreachable, retain its last confirmed Only boundary
   as stale for that same board. Do not apply it to a different board. Unknown status
   must not be treated as explicit Off. Confirm Off/Between before restoring ordinary
   navigation, using its last valid location or a deliberate normal root fallback.
5. Missing/excluded/unmounted/unreadable Clocks stays inside a virtual unavailable
   Clocks boundary, with a reason and retry. Never use the normal root as a visible
   fallback. Recover to the resolved Clocks identity/descendant once available.
6. Apply the visible boundary consistently to Animations, Upload destinations and
   authoring-related navigation. Necessary background root-name queries may remain
   invisible for ID collision checks. Disable an upload that would silently fall back
   to an unrelated internal root when a valid in-bound destination is unavailable.
7. This does not change the clock/message shuffle, Ignore/manual-play semantics or
   permit outside playback. Off and Between retain normal browsing. Existing firmware
   that cannot report/implement Only gets an explicit unsupported state.

## Technical Constraints

- One app/www for APK and emulator. Reuse folder identity/target-generation handling.
- Coordinate with seed67:67 repairs automatic recovery/data loss;66 adds the owner's
  explicit navigation policy. Do not bundle both into an unreviewable task or require
  rotation65. Resolve overlapping client work in S2S before enqueueing both.
- No new wire commands or hardware/power changes. Amend the older unrestricted-browse
  documentation as an explicit owner-requested policy change, preserving append-only logs.
- Regression tasks must observe escaping navigation fail on original code first.
  Cover nested Clocks, missing media, transient errors, stale IDs/replies, reconnection,
  mode transitions, old firmware and upload fallback with discovered app/emulator tests.

## Open Questions Requiring The Owner

None. The owner explicitly chooses the Clocks subtree as the Only browsing boundary.
The unavailable view and normal-mode restoration rules above settle edge cases.

## Definition Of Done

Every visible navigation path respects the boundary while Only is active or awaiting
confirmation after a disconnect. Mode controls remain usable; normal modes browse
normally. Relevant discovered suites and emulator checks pass. Physical phone acceptance
remains open until observed; no implementation is part of creating this seed.
