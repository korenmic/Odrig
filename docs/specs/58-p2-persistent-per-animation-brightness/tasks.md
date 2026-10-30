# Persistent per-animation brightness — tasks

- [x] 1. Add durable core animation brightness and shared selection.
  Implement bounded atomic path settings, retained entries/capacity, startup/remount
  caches, approved commands and additive status. Select before scaling for every
  playback/diagnostic case and miniature cap without changing default/timing.
  Preserve memory/reply bounds by compacting private metadata without narrowing
  domains. Test identity/zero/default, corruption, every storage-call cut, no-op,
  exhaustion, clocks/resume, read-only media and bounds. Run core/emulator suites.

- [ ] 2. Integrate preference preservation and existing command routes.
  Extend odrigctl forms/help and firmware settings inclusion/preservation, explicit
  replacement/readback and emulator/transport contracts. Prove animation/catalog
  bytes/default behavior unchanged. Run emulator suite and relevant pure firmware
  tool tests; full firmware build remains deferred and no board is written.

- [ ] 3. Add identity-safe override controls to the shared app.
  Add adjacent checkbox, default/animation labels and file identity. Integrate
  numeric/slider commit rules, confirmed capture/readback, coalesced durable edits
  and captured identities. Cover input transitions, late replies, other clients,
  failures, unsupported/unknown/reconnect states and320px/landscape/pinned layouts
  against stand-ins and real emulator. Run app/emulator suites by discovery.

- [ ] 4. Document brightness preferences and record integrated verification.
  Update command/core/app/emulator/firmware/storage docs and vocabulary, append
  technical resolutions and record limits/recovery/default-zero behavior. Run
  supported suites and deterministic emulator persistence/transition smoke. Keep
  firmware deferred and APK until all56–59 software is complete.

- [ ] 5. Verify saved brightness on the board and phone with the owner.
  Later approved session at brightness40 or less: save A, change default while B
  plays, return to A, restart board/app, verify retention, then remove A's override
  and verify immediate/persistent default restoration, clocks and safety caps.
  Leave unchecked until observed.

Self-review: tasks1–4 cover software requirements; task5 retains human acceptance.
One task, checkbox and proof commit at a time. New faults must fail first and be
recorded in proof commits. No seed60 implementation or firmware build in this run.
