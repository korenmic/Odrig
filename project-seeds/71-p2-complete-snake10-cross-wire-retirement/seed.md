# Complete Snake10 cross-wire retirement

## Summary

Finish removing the dedicated Snake10 cross-wire feature from the maintained
product. No checkbox, hidden control, app API, special runtime observer or
successful command path may expose or enable that option.

## Priority

`P2`.

## Product Context

The owner requested complete removal on 2026-11-02 because the feature is no
longer needed. Seed69 is completed and already removed the visible checkbox,
app API, core command routing and advertised reply member. This is a completion
sweep of the remaining feature-specific paths, not a restart of that seed.

Current master still counts successful `mapping cross` operations through
`wiring_saves` in `emulator/binding.py`, and `emulator/engine.py` observes that
counter for layout refresh. Those special paths remain even though the core no
longer accepts the command.

## Required Behavior

1. Remove every remaining maintained, dedicated Snake10 cross-wire toggle,
   handler, algorithm, observer, counter and current-facing instruction. Check
   the shared app, emulator Controller, packaged APK assets, native core,
   firmware integration and command tool; do not merely hide a checkbox.
2. Remove the obsolete successful-command tracking and its dependent layout
   invalidation plumbing. Preserve ordinary mapping-change refresh, miniature
   output and all other legitimate routing updates.
3. The retired `mapping cross` operation remains unsupported on every existing
   transport and cannot write files, change the mapping or advance its revision.
   Negative compatibility tests and a brief retirement explanation may remain;
   they must not implement a dormant option that can be switched back on.
4. Preserve ordinary logical snake10, its regular display test and editable pin
   assignment. The removal concerns the special cross-wire feature, not one of
   the installation's twenty normal snakes.
5. Preserve the generic mapping format and valid installed per-strip geometry.
   Do not migrate or rewrite an operator's mapping, change chain directions,
   rewire hardware or introduce a replacement exception for another snake.
6. Keep old seed/spec/decision records as explicitly historical evidence. Update
   maintained product guidance when needed without deleting append-only history.

## Technical Constraints

Use the existing single shared app and native core. No new commands, hardware,
power, storage-format or boot-pipeline changes are needed. Build the eventual
APK from the same app code served by the emulator. An audit that finds a layer
already clean records that evidence rather than changing unrelated behavior.

## Open Questions

None. The owner's request confirms complete retirement. Ordinary snake10,
generic custom geometry and historical records remain in scope as preserved
behavior, not as an optional cross-wire product feature.

## Definition Of Done

The remaining feature-specific paths are removed; targeted regressions prove
the retired command cannot mutate state and normal mapping refresh still works;
discovered affected suites pass; the emulator Controller and packaged app expose
no such option; and current documentation agrees. Any physical phone/LED checks
remain explicitly unperformed until the owner carries them out.
