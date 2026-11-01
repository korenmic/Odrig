# Tasks

- [x] 1. Implement phone USB capture, bounded lifecycle, sharing, shared Target UI and documentation.
  Run discovered app suite and native Java model checks; compile the Android plugin.
  Verification: all 550 app cases have passing verification with the full-run qualifications
  and exact rechecks in verification.md; actual Android Java compilation passes.
- [x] 2. Verify the signed APK in Android VM, publish it in place, push and record delivery proof.
  Reuse the persistent signer. Verify published APK bytes and leave firmware unchanged.
  Actual Android checks, APK packaging and byte verification pass with the VM/reporting
  qualifications in delivery-verification.md and delivery.json. Physical USB remains open.
- [ ] 3. Owner: verify USB permissions, reset-line behavior, COM/UART boot logs and log sharing on the real phone/board.
  Physical acceptance remains open without holding software delivery in progress after merge.
