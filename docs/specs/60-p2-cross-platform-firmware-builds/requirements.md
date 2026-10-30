# Cross-platform firmware builds — requirements

The owner subsequently authorized implementation of this seed and final firmware
delivery, superseding the original seeds56–59 deferral. No owner question remains.
The existing setup/build interface is retained; board access is outside scope.

## 1. Supported hosts and pinned setup

1.1 Existing `python firmware/fw.py setup` and `build` produce the default microSD
firmware on Windows10/11 x64 and preserve macOS builds on vendor-supported Intel
and Apple processors. Keep Linux-compatible abstractions; report the actually
observed OS/architecture separately from configured support. Unsupported hosts
fail clearly before running an incompatible binary or changing dependencies.
1.2 Retain WLED16.0.1 at its pinned commit, existing base/newer Python requirements,
PlatformIO6.1.17/6.2.0, Node20.18.0, tasmota2024.06.00 and pioarduino55.03.312-1.
Delegate vendor host-archive selection to the pinned package managers; retain their
integrity validation and the checked WLED identity. Missing artifacts are setup
failures, never an implicit version upgrade or a macOS executable on Windows.
1.3 Install only under the ignored work/toolchain folders. No global compiler,
PlatformIO, persistent PATH change or administrator-only symlink is required.
Preserve `ODRIG_TOOLS`, shared setup locking, idempotence and checkout-local patched
sources/outputs. Different hosts must not overwrite one another's executable caches.
Failed/interrupted setup leaves no successful stamp for incomplete dependencies.

## 2. Portable build behavior

2.1 Support repository/toolchain paths containing spaces, native executable suffixes,
UTF-8 and LF output. Commands carry paths as arguments; generated configuration
must preserve path boundaries. Builds always compile this checkout's current core
and usermod, including when local dependencies are copied instead of symlinked.
2.2 Inventory all existing kinds: default, microSD alias, probe, stock, stick,
stick-probe, standalone and standalone-probe. Preserve their environments, flags,
partitions, artifact filenames and distinctions. Test selection for every kind;
report actual build coverage separately. Standalone remains the unfinished trial
player; a successful compilation grants it no missing runtime capability.
2.3 Bound build concurrency and serialize mutations of checkout-local build inputs.
Every process the setup/build launcher owns is ended on success, failure or
interruption, including descendants. Use Windows job ownership and Unix process
groups; keep background windows hidden. Do not terminate unrelated processes.
2.4 Preserve size/checksum validation and public output paths. Record source commit
and tracked dirty state, host/architecture, pinned toolchain identities, relevant
input hashes, output size and SHA-256 beside the firmware. Do not assume cross-host
byte identity: compare configuration/current-code identity and meaningful image
content while documenting compiler paths and build metadata differences.

## 3. Verification and delivery

3.1 Discover firmware tests on supported hosts and expose Windows firmware builds
through the existing runner. Portable host fixtures must use the project's compiler
selection and truthful sanitizer/host skips. No board/serial/network-board suite is
run by setup/build verification.
3.2 Observe known host/path/process faults failing before fixes. Cover host/architecture
selection, unavailable artifacts/checksum rejection, setup reuse/locking/failure,
paths with spaces, current-source refresh, process cleanup and all variant mappings.
3.3 Actually build the default on Windows and macOS from the same committed source;
verify Linux when a runner is available. A host matrix may provide this proof without
Mac access. Retain logs/provenance and state every unperformed variant/architecture
check honestly. Never call an unperformed build successful.
3.4 Update setup/firmware/getting-started documentation with requirements, cache/output
locations, command examples, support/coverage and limitations. No runtime feature,
command, wiring, power, flash layout, Wi-Fi or current-limit change belongs here.
3.5 After software implementation, rebuild final default firmware and APK. Use one
persistent dedicated Odrig APK signing key, preserving the owner's global key. Upload
the key and reuse information beside the APK. Overwrite the existing Drive APK in
place, preserving file identity; verify delivered APK/key/firmware bytes. The owner
waived the earlier Mac APK's signer. Keep board/phone acceptance from56–59 open.
3.6 Use stacked branches and one final tip-branch PR to master. Follow one task, test,
checkbox and proof commit at a time, with milestone notifications and CI handoff.

Self-review: sections1–3 cover the seed's eight behaviors and four completion
criteria, plus the owner's later delivery instructions. No new product question
or runtime scope is introduced.
