# Tasks

Self-reviewed against the hardened seed and square-only owner answer. One numbered
task and checkbox per proof commit. Standalone packaging/publication is a separate delivery task after these checks.

- [x] 1. Persist and render all four square output orientations in the shared core
  - Add failing native protocol/output regressions first, then bounded atomic saved
    control, startup loading and exact composed sample permutation for main/mini output.
  - Preserve diagnostics, show installs, source bytes and resource limits. Document the
    shared protocol/core behavior and resolved direction/legacy-fixture handling.
  - Run discovered core, emulator and mapping suites, record evidence and tick only1.
- [x] 2. Expose confirmed rotation controls in Settings and odrigctl
  - Add failing browser/command coverage first. Implement strict shared reply parsing,
    guarded serialized read/set and the four-value Settings dropdown with clear state.
  - Verify targets, reconnect/lost replies, queue cancellation, unsupported firmware,
    actual native output and retained mapping lock behavior. Update operator docs.
  - Run discovered app, emulator, core documentation and onboarding checks; record
    evidence and tick only2, then proceed to standalone APK/FW delivery.
- [x] 3. Build and publish the standalone rotation APK and firmware
  - Build clean committed rotation-only source through the repository tools, inspect
    firmware provenance, verify the APK signer and exercise installation and controls
    against the native emulator in an owned Android VM when available.
  - Upload the APK/FW pair and verification/checksum sidecars to its own Drive subfolder,
    preserving usual artifacts and signing backups; push the standalone PR, record CI
    and notify delivery. Physical square-wall and phone/board acceptance stays open.

- [x] 4. Initialize a fresh board safely before exposing rotation
  - Reproduce the empty internal-storage failure before fixing production startup.
  - Provision the existing canonical60x60 mapping and a valid empty dark show only
    for a fresh Odrig store; recover interrupted initialization without replacing
    operator files. Verify all four rotations and saved state after restart through
    the production bootstrap and shared core, with existing installs preserved.
  - Run discovered firmware/core suites, document the fresh-board behavior and
    retain failing-before/passing-after evidence in this proof commit.
- [x] 5. Distinguish installation faults from unsupported rotation in Settings
  - Add failing browser coverage for missing/malformed installation state before
    changing UI feedback. Keep valid-board angle controls and legacy compatibility.
  - Run the discovered app suite and tick this task in its own proof commit.
- [ ] 6. Rebuild, verify and publish the fresh-board rotation artifacts
  - Build clean committed sources using repository tools; test firmware startup and
    rotation commands in the available ESP32S3 model plus installed Android VM.
  - Replace the PR44 Drive artifacts in place, verify hashes, push, check remote CI,
    and notify with the fixed firmware URL and precise physical-test limitations.

## Owner acceptance (not executable queue tasks)

- [ ] Observe correct clockwise orientation on the actual square wall and miniature
  active square, with physical diagnostics unchanged, using the delivered APK/FW.
