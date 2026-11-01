# Tasks

Seed, requirements and design reviewed against the owner's request and current
master. No new command, hardware change or owner question is needed.

- [x] 1. Retire dedicated Snake10 cross-wiring controls
  - Observe retired-operation/UI regressions failing first. Remove app/core/CLI
    controls and special-case geometry code; preserve generic saved mapping geometry.
  - Update current docs and append the owner's superseding decision. Update obsolete
    tests to assert retirement/compatibility. Run discovered core, mapping, emulator
    and app suites; record proof and set the seed in_progress in this task commit.
- [ ] 2. Require confirmed unlock for every Settings mapping mutation
  - Observe accidental-edit regression failing first. Add the default-locked toggle,
    confirmation/cancellation and session/target/visibility resets. Guard every write
    path including photos and queued movement, with accessible disabled controls.
  - Exercise keyboard/pointer/photo/target cases in the browser and run all supported
    discovered suites on the up-to-date branch. Record limits/proof, commit this task,
    push one focused PR, gate its exact head and merge into master as requested.

## Owner acceptance

- [ ] Check the lock interaction on a real phone and the mapping/LEDs on the installation.
