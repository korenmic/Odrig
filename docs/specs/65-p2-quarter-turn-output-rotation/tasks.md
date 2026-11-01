# Tasks

Self-reviewed against the hardened seed and square-only owner answer. One numbered
task and checkbox per proof commit. Standalone packaging/publication is a separate delivery task after these checks.

- [x] 1. Persist and render all four square output orientations in the shared core
  - Add failing native protocol/output regressions first, then bounded atomic saved
    control, startup loading and exact composed sample permutation for main/mini output.
  - Preserve diagnostics, show installs, source bytes and resource limits. Document the
    shared protocol/core behavior and resolved direction/legacy-fixture handling.
  - Run discovered core, emulator and mapping suites, record evidence and tick only1.
- [ ] 2. Expose confirmed rotation controls in Settings and odrigctl
  - Add failing browser/command coverage first. Implement strict shared reply parsing,
    guarded serialized read/set and the four-value Settings dropdown with clear state.
  - Verify targets, reconnect/lost replies, queue cancellation, unsupported firmware,
    actual native output and retained mapping lock behavior. Update operator docs.
  - Run discovered app, emulator, core documentation and onboarding checks; record
    evidence and tick only2, then proceed to standalone APK/FW delivery.
- [ ] 3. Build and publish the standalone rotation APK and firmware
  - Build clean committed rotation-only source through the repository tools, inspect
    firmware provenance, verify the APK signer and exercise installation and controls
    against the native emulator in an owned Android VM when available.
  - Upload the APK/FW pair and verification/checksum sidecars to its own Drive subfolder,
    preserving usual artifacts and signing backups; push the standalone PR, record CI
    and notify delivery. Physical square-wall and phone/board acceptance stays open.

## Owner acceptance (not executable queue tasks)

- [ ] Observe correct clockwise orientation on the actual square wall and miniature
  active square, with physical diagnostics unchanged, using the delivered APK/FW.
