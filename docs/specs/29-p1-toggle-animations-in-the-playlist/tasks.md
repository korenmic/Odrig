# Tasks: playlist and storage management

Use the combined seeds29+30 branch in the existing temporary worktree. One task per
commit, named staging only, checkbox in its proof commit. Observe fault regressions
failing before fixes. No flash, phone installation or external-drive writes.

- [x] 1. Extend show validation and packing with persisted playlist inclusion
  - Add strict optional ignored boolean to JS converter and Python library; preserve
    absence and explicit false. Cover malformed values/cycles, packing and old shows.
  - Update show/tool format documentation. Start seed29 in_progress.
  - Verify: converter npm suite and Python converter/library suite by discovery.
  - Requirements: 1.1, 1.5.

- [x] 2. Implement shared-core inclusion and atomic bulk removal
  - Add ignored state/parser/writer, idempotent ignore, filtered playlist scheduling,
    one-off manual turns, cycle independence and empty/resume semantics.
  - Add remove many parsing/validation, durable filtered metadata transaction,
    complete journal recovery and shared-file cleanup; retain single remove behavior.
  - Extend list with inclusion flags and paginate within1024bytes. Preserve mapping
    diagnostic busy rules, no allocation and memory bounds. Update core/command docs
    and append approved playlist decision extension and technical drift resolutions.
  - Verify: core suite by discovery, converter/library suite and packaged diagonal check.
  - Requirements: 1.2–1.5, 2.1–2.3, 4.2.

- [ ] 3. Add shared capacity reporting and route every new command
  - Add optional 64-bit drive capacity callback, safe core schema, emulator filesystem
    capacity and firmware read-only FAT capacity query. Update host fixtures/layouts.
  - Extend odrigctl, emulator reference behavior and protocol routing regressions.
  - Update emulator/firmware docs and additions, memory accounting and command schema.
  - Verify: core, emulator and firmware suites by discovery.
  - Requirements: 3.1–3.2, 4.1–4.2.

- [ ] 4. Implement shared app inclusion toggles, bulk selection and capacity views
  - Extend validated protocol/client snapshots and mutation promises; refresh capacity
    on boot/reconnect/upload/delete and active view polling. Ignore stale target replies.
  - Add Show toggles and capacity; Storage selection, confirmation, sequential batches,
    partial/error reconciliation and capacity, accessible on phone and emulator.
  - Test browser app against emulator including refusal, restart, target change,
    external read-only entries and more than32selected items. Update app docs.
  - Verify: app and emulator suites by discovery.
  - Requirements: 1.6, 2.4, 3.3, 4.1.

- [ ] 5. Verify the combined implementation and rebuild delivery artifacts
  - Run every suite that works locally, retaining seed30 regressions; exercise a full
    local show in emulator, including both mapping test and new storage controls.
  - Build WLED and standalone firmware with fw.py, build/sign APK with app.py; run APK
    suite on exact delivery binary. Record hashes, evidence and deferred checks.
  - Push the combined branch, create one PR, inspect remote checks, overwrite usual
    Drive APK and upload WLED firmware beside it; verify delivered bytes.
  - Keep both seed states in_progress until owner acceptance. Notify milestones/finish.
  - Requirements: 4.1–4.4 and all automated acceptance.

- [ ] 6. Owner verifies phone controls and real installation
  - Deferred by explicit no-flash instruction. At a later authorized session check
    inclusion, bulk deletion and capacity on phone/board, plus seed30 physical diagonal.
  - Record what was seen and left on board; only then complete the seeds.
  - Requirements: 4.4.
