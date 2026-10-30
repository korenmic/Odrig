# Message clock widgets and clocks-only mode — tasks

- [x] 1. Add the bounded message-clock widget format and shared renderer.
  Implement subtype6 source/encode/decode and strict JS/Python/C++ validation,
  deterministic elapsed/seed rendering and existing app preview integration.
  Document byte layout/math. Prove malformed/truncated inputs, every timing/stop/
  countdown/sweep boundary, seek/loop reproducibility, renderer pixel equivalence,
  old payload compatibility,32KiB payload and unchanged memory/stack bounds.
  Run converter, Python library, core and relevant browser/emulator suites.

- [ ] 2. Extend persistent Ignore to external files and folders.
  Implement atomic path/kind preferences, retained128-record capacity, compact cache,
  own/inherited list state and one automatic eligibility rule. Preserve internal
  Ignore and manual availability; update firmware settings preservation/readback.
  Test ancestor inclusion, changed IDs/remount, read-only SD, every failed save,
  stale/current candidates, index refill boundaries and fixed memory. Run core,
  emulator and relevant pure firmware-tool suites by discovery.

- [ ] 3. Implement persistent clocks-only mode and complete message bags.
  Add approved command/CLI/status, v1 migration/v2 atomic settings, separate shuffled
  message bag in both enabled modes, complete message turns, and shared enforcement
  at every play/diagnostic/automatic/resume/cleanup entry. Preserve prior normal
  playlist and handle missing/all-excluded/quarantined media dark without fallback.
  Verify all transport/bag/inclusion transitions, timing, reply/memory bounds and
  regression compatibility. Run core/emulator and settings-tool verification.

- [ ] 4. Add shared mode dropdown and external inclusion controls.
  Implement confirmed Off/Between/Only UI, old-target fallback, once-only navigation,
  unrestricted browsing, inside/outside Play states and inherited folder/file
  exclusions. Cover target changes, late replies, pending/refusal/uncertainty,
  reconnect, other clients, small/landscape layouts and real emulator behavior.
  Run app/emulator suites by discovery.

- [ ] 5. Generate and deliver the seven widgets with integrated proof.
  Build reproducible source masks/metadata, exact Hebrew sequences, widget/GIF/.md
  assets and thumbnail entries, preserving the old message. Visually compare with
  the retained HTML at fixed times/seeds; document font/decoration adaptations.
  Copy matching artifacts to the resolved share and verify bytes. Update remaining
  public/provenance docs and append resolutions. Run all supported suites and
  complete-loop/mode/inclusion emulator smokes. Defer final APK/FW until60 finishes.

- [ ] 6. Verify physical deployment and phone behavior with the owner.
  Later approved catalog-managed SD/board/phone session: compare all seven complete
  sequences, stops/RTL, mode boundaries, ignored ancestors, restarts and output
  rates at brightness40 or less. Keep unchecked until actually observed; no board
  write or bare SD copy is authorized by the software run.

Self-review: tasks1–5 cover all22 software behaviors and required proof; task6
retains human acceptance. One task/test/checkbox/proof commit at a time. Then
seed60 on the next stacked branch; one final PR and final APK/FW uploads afterward.
