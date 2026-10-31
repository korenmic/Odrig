# Cross-platform firmware builds — tasks

- [x] 1. Make firmware setup host-aware and safe across shared toolchains.
  Implement canonical host/executable paths, isolated non-Mac executable caches,
  pinned Python/Node setup and version reporting, explicit host/package failures,
  safe idempotent stamps and shared locking. Add owned process cleanup for setup
  and launcher, preserving current Mac paths. Observe Windows path/cleanup faults
  failing first; verify setup selection, integrity/failure/reuse/locking and real
  dependency installation without global writes. Set seed state in_progress.

- [x] 2. Make the existing firmware build variants portable and traceable.
  Handle quoted/spaced native paths and unprivileged local dependencies, refresh
  copied current sources, serialize checkout builds and clean owned descendants.
  Preserve all eight environment/output mappings and runtime flags. Keep image
  size/checksum checks and add source/host/toolchain/input/output provenance.
  Verify fail-first path/current-source/cleanup cases and every variant mapping.

- [x] 3. Integrate portable firmware verification with the existing runner.
  Port host compiler fixtures using project compiler selection, preserve available
  sanitizers and honest skips, and locate the selected host firmware environment.
  Enable Windows host-only firmware builds through existing runner switches.
  Run firmware and runner suites by discovery; correct host-specific expectations
  without weakening runtime/format/board protections. No board suite is selected.

- [x] 4. Verify local builds and publish the host build matrix and documentation.
  Actually set up/build default microSD locally, test spaced paths and setup/build
  reuse/interruption, inspect ESP32-S3 image/current symbols and provenance. Add a
  read-only Windows/macOS/Linux CI matrix for same-source host proof, with useful
  logs/artifacts and bounded jobs. Update host/setup/output/variant documentation,
  append resolutions and record local verification honestly. Commit software before
  the final delivery task; no unobserved host/variant is reported successful.

- [x] 5. Validate cross-host builds and deliver final APK and firmware.
  Push this tip branch, create/attach the ONE PR targeting master, and own its CI
  handoff, correcting attributable regressions. Confirm actual Windows/macOS build
  evidence and report Linux/variant/architecture coverage. After all software,
  rebuild final fw.py default firmware and shared-code APK, create/reuse a dedicated
  persistent signing key without touching the global key, and upload key/reuse
  details beside the existing Drive APK. Overwrite APK in place, preserve file
  identity and verify all delivered bytes. Record built revisions/hashes and open
  physical acceptance, tick this task only after delivery, then self-audit, notify
  and disable the completion heartbeat. Set seed completed when its proof holds.

Self-review: five planned proof boundaries cover requirements1–3 and all seed
criteria. Software implementation precedes final artifacts; actual remote host
evidence follows the committed matrix. Each task has its own verification,
checkbox and commit. Earlier board/phone tasks stay unchecked.

- [x] 6. Normalize canonical paths in CI fixtures (integrity bridge).
  The actual host matrix exposes alternate path spellings in Windows8.3 temporary
  folders and Mac /var aliases. Compare canonical current-source/configuration/cache
  paths in the affected existing tests, retain all assertions, and verify by discovery
  including an actual Windows8.3 temp root. Commit this minimal repair before task5's
  remote check gate and final delivery. This bridges the committed host matrix and
  its final handoff; no requirement or runtime behavior is added.

- [x] 7. Keep checked scheduling frames within the existing Clang bound (integrity bridge).
  The Mac newcomer run exposes a528-byte checked playlist_turn frame against the
  unchanged512-byte limit. Isolate the bounded clocks-only scheduler without changing
  playback behavior, memory budgets or compiler protections. Add an early Mac checked
  core build to catch this before firmware downloads; run discovered core/emulator
  regression suites locally and own the actual Mac check. Commit this minimal build
  safety repair before final task5 delivery, then rebuild artifacts from that source.
