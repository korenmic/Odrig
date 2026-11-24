# Standalone automatic Clocks recovery verification

This change uses master's current-level inventory model. It adds no snapshots,
inventory fingerprints, board identity or retained-key cache. The original seed's
global inventory redesign remains deferred in the aggregate PR. Explicit browsing
continues to follow master's behavior; this change governs automatic recovery.

## Observed failures and repair

Before repair, the production-function harness observed three failing cases:

- Missing folder followed by absent catalog: visible paths included
  `["clocks","clocks","",""]` and the final level was Root.
- Initially missing Clocks: visible paths were `["",""]`.
- Unknown policy after a missing folder: the final level remained Root.

After adaptation these cases stayed inside Clocks. Ten shared-client Chrome cases
then passed: absent media, missing Clocks initially, valid descendant retention,
remapped IDs, returning storage, unknown mode metadata, target changes, availability
of Settings/Target/mode exit and refusal to restart an unresolved folder.

A later focused check exposed two additional uncertainty paths. Damaged/loading
catalog cases each failed in Chrome and in the production-body model because an
unknown folder ID still enabled Restart clocks. A busy catalog refusal then failed
the model for the same stale-ID condition. Both paths now mark Clocks unavailable,
retain its location and retry rather than enabling the unresolved command.

## Verification and source relationship

The frozen discovered run `20261102-000305-166488` passed all 458 app cases and
642 of 662 emulator cases, with 20 platform/fixture skips and no failures. It used
the task1 commit plus the initial task2 working tree, before the final catalog and
refusal guards described above. Its runtime hashes are preserved in
`recovery-verification.json`; this is not claimed as a full pass of the final client.

After those small guards, final affected discovery passed all 20 test methods:
eight ordinary folder-recovery cases, eleven Clocks-only browser cases (including
both damaged and loading states), and a production-body method with six recovery
scenarios including the busy refusal. Final onboarding discovery passed all 88
cases. The full app suite was not repeated after these focused corrections.

The earlier task1 broad pass was intentionally stopped with partial results and is
not counted as a complete successful run. Its resource error and successful recheck
remain recorded in `policy-verification.md`. Task1's discovered core, native policy
checks and allocation bounds are recorded there separately.

No core or firmware source changed after `1b73c2f`; `git diff --exit-code 1b73c2f --
core firmware` was clean. The recovery firmware built from that clean commit thus
has the same core/firmware inputs as this task's final app source.

These checks use the actual client functions and shared app with stand-in command
targets, plus the native core/emulator. They do not establish ESP32 radio/SD or real
phone acceptance. Physical boot, sustained playback and the reported no-hotspot
incident remain open for owner acceptance. Build, publication and packaged Android
verification belong to the next, still unchecked delivery task.
