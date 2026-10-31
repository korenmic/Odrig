# Quarter-turn output rotation

## Summary

Add board-owned output orientation with all four quarter turns:0°,90°,180° and270°
clockwise, relative to the currently correct front view. Propose one persistent
Settings dropdown and shared read/set operations. Default to0° for existing shows.

## Priority

`P2`.

## Product Context

The owner requested all four90-degree orientations on2026-11-01. This rotates the
displayed playback picture; it does not require converting animations, physically
changing wiring or changing a clock's time. The installation's logical canvas is
60x60; miniature mode projects it into the existing centered6x6 area of the10x6
matrix. Legacy rectangular canvases also exist, so their quarter-turn fitting
policy must be explicit rather than silently clipping or stretching content.

## Proposed Required Behavior

1. Support exactly0/90/180/270 clockwise with a visible Settings dropdown. Read
   and confirm the board's value on connection; pending/refused/lost replies do not
   masquerade as a successful change or apply a write to another board.
2. Save one installation-wide value atomically, across app disconnects and board
   resets. Missing settings mean0°; malformed/failed changes retain the last valid
   value and show a clear error. Do not write storage per frame or for a no-op save.
3. Rotate the complete composed playback picture, including ODRG frames, text,
   clock widgets, pictures and messages, for internal and external files and every
   playback mode. Keep timing, repeats, randomness, exclusions and source bytes.
4. On a square canvas each angle is an exact coordinate permutation. Apply it
   before physical leg/snake mapping and before miniature projection, exactly once.
   Preserve the manufacturer's miniature wiring transform and existing dark columns.
5. Proposed rectangular policy: keep the output canvas dimensions, preserve aspect
   ratio, fit the whole rotated picture and fill unused pixels black. Never crop,
   stretch or rewrite file/mapping dimensions implicitly. This proposal awaits the
   owner's confirmation below.
6. The native emulator's live output reflects the same orientation as the board.
   Catalog thumbnails/source previews retain the file's canonical picture. Physical
   mapping/snake diagnostics retain their physical coordinates and pin identities;
   refuse an orientation change while an output-taking diagnostic is active.
7. Proposed shared wire forms: `rotation` reads value/revision/capability;
   `rotation set <revision> <0|90|180|270>` atomically sets and saves. Setting0°
   restores the default orientation. Use identical semantics on existing transports
   and in odrigctl; no new transport. These command additions require owner approval.
8. Keep brightness/current limits, power, pin assignment, matrix wiring and existing
   memory/stack/work budgets. Avoid another full-canvas allocation and frame-time IO.
   Old firmware is shown as unsupported without breaking its ordinary controls.

## Technical Constraints

- Reuse the single shared core and app/www. Relevant sources are player.cpp,
  mini.cpp, mapping_control.cpp and the existing physical output adapters.
- Resolve coordinate direction and rectangular sampling precisely in S2S. Verify
  corners, an asymmetric labelled pattern and four successive quarter turns.
- Test all angles with plain/palette/layered content, mini on/off, persistence,
  storage failures, target changes and native output equivalence by discovery.
- Real LED orientation remains an owner's check; no wiring/power changes are authorized.

## Open Questions Requiring The Owner

1. Approve the proposed saved control and shared `rotation` / `rotation set` command
   additions. AGENTS.md reserves every addition to the command list for the owner.
2. Confirm the proposed preserve-aspect/black-bars behavior for rectangular canvases,
   or choose a different explicit quarter-turn fitting policy. Square60x60 output and
   its miniature projection need no resampling policy question.

Other defaults above are concrete proposals, not additional unresolved questions.
This seed is not yet zero-question ready; the other two requested seeds are independent.

## Definition Of Done

After the two owner answers, S2S has no owner questions remaining. All four angles
work through the shared core/app/command tool with confirmed persistence and bounded
resource use. Relevant discovered suites and emulator checks pass; physical LED
orientation and any unavailable phone checks remain explicitly open.
