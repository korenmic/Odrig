# Cross-platform firmware builds — design

## Baseline and ownership

`firmware/fw.py` delegates to `fwtool.cli`; `toolchain` creates two pinned Python
environments, `wled` owns the fetched/patched checkout and generated override, and
`build` invokes PlatformIO and keeps the image/checksum. Currently Python/Node paths
assume `bin/`, configuration rejects whitespace and processes have no owned-tree
cleanup. Windows runner Python discovery already knows `Scripts/python.exe`, while
some firmware test compilers still assume Unix `c++` and sanitizers.

Preserve the existing entry point and command list. No firmware runtime source is
changed to accommodate a host. Build-input and host-tool defects discovered during
real compilation are repaired here without changing runtime semantics.

## Host and toolchain layout

Add a small host abstraction for canonical OS/architecture, environment executable
directories, Python/Node/npm launch forms and explicit supported-host failures.
Windows uses `Scripts` and executable launchers; Unix retains `bin`. Use the pinned
Node wheel's launchers/module API rather than assuming a Unix npm shell script.

Retain the existing macOS toolchain paths for compatibility. Other host executable
environments and PlatformIO caches use a host namespace below the firmware shared
toolchain root; the fetched WLED source and content-addressed pip/npm caches can
remain shared. `ODRIG_TOOLS` and the common setup lock keep their meanings. Worktree
WLED copies, generated projects and `out/` remain checkout-local. Validate interpreter
identity/stamps so a cache from another host is never silently reused or overwritten.

The pinned package managers select their vendor archives. The project keeps WLED's
exact checked commit and the pinned requirement inputs, and records package/platform
identities after setup/build. Do not invent a replacement archive, downgrade silently
or bypass a checksum. Unavailable/invalid packages fail with a useful setup message.

Vendor references inspected for this design:

- [Pinned newer platform manifest](https://raw.githubusercontent.com/pioarduino/platform-espressif32/55.03.312-1/platform.json).
- [Pinned base platform manifest](https://raw.githubusercontent.com/tasmota/platform-espressif32/2024.06.00/platform.json).
- [Pinned Node wheel metadata](https://pypi.org/pypi/nodejs-wheel-binaries/20.18.0/json).

## Processes and serialization

A reusable fwtool process helper owns each setup/build child and its descendants.
On Windows, create a job object with kill-on-close ownership, assign the child and
hide its console; on Unix create a new session/process group. Drain output with
explicit UTF-8 replacement handling; preserve useful diagnostics and return codes.
On every exit path close/terminate the owned tree and wait. Setup failures never
write the dependency stamp. Tests launch real short-lived parents with lingering
children and verify cleanup, as well as interruption/failure paths.

Use the existing common setup lock for shared mutation and a checkout-local build
lock for restoring patches, refreshing local libraries and compiling. Avoid nested
locking that deadlocks the launcher and its delegated interpreter. Never sweep by
generic executable name or end another checkout's processes.

## Paths and variants

Normalize generated configuration paths and quote include/forced-include arguments.
Keep complete dependency specifications on their own lines. Local Windows libraries
must work without privileged symlinks: use the package manager's supported local
copy form when needed, refreshing only the build's owned dependency copies so core
or usermod edits cannot be cached away. Unix keeps its current symlink behavior.
Verify real builds with a spaced checkout path, beyond configuration-string tests.

| Kind | Environment | Platform family | Output |
|---|---|---|---|
| default | odrig_microsd | newer | odrig-firmware.bin |
| microSD alias | odrig_microsd | newer | odrig-microsd.bin |
| probe | odrig_microsd_probe | newer | odrig-probe.bin |
| stock | esp32s3dev_16MB_opi | base, no patches | stock-built.bin |
| stick | odrig | base | odrig-stick.bin |
| stick-probe | odrig_probe | base | odrig-stick-probe.bin |
| standalone | odrig_standalone | base, separate project | odrig-standalone.bin |
| standalone-probe | odrig_standalone_probe | base, separate project | odrig-standalone-probe.bin |

Keep all current build flags and GPIO/partition definitions. Unit tests verify every
mapping and configuration. The actual default build is mandatory on Windows/macOS;
report optional variant compilation coverage without inferring it from the default.

## Provenance and host verification

Keep the existing `.bin` and `.sha256`; add a UTF-8/LF JSON provenance companion.
Record current source revision/dirty state, selected kind/environment/host, WLED and
platform/Python/Node versions, hashes of core/usermod/patch/config inputs, image size
and SHA-256. Audit the ESP32-S3 image and linked current-player symbols. Compiler
paths, timestamps and application-description/ELF metadata can vary across hosts;
matching hashes of source/configuration and matching expected image properties are
the meaningful comparison. No byte-identity promise is made.

Port firmware host test compiler fixtures through the existing core compiler helper;
keep sanitizers where supported and explicit skips where unavailable. Runner discovery
finds the selected firmware Python and allows host-only setup/build on Windows.
A read-only GitHub Actions host matrix can build the same PR source on Windows,
macOS and Linux, including a checkout path with spaces, without secrets or board
access. Archive logs/provenance, and use its completed checks as actual host evidence.

## Final artifacts and boundaries

After software tasks1–4 are committed, create the one final PR from this stacked
branch and validate its checks. Then rebuild the final default firmware via fw.py
and APK from the same final software sources. Packaging uses the one shared
`app/www`, converter library and preview catalog. A dedicated persistent signing
key stays outside git, is backed up with reuse instructions beside the Drive APK,
and does not replace the global Android key. The prior signer is expressly waived.
Overwrite the existing APK through its existing file, compare identity before/after
and read back hashes. Preserve the established firmware destination and verify it.
Proof-only commits may follow; they must identify the software revision actually
built. Fix any PR-caused CI regression before claiming successful completion.

Board flashing, SD installation, power/electrical changes and human acceptance are
excluded. Seed59's last checkbox and earlier physical checks remain open.

Self-review: host/layout, process, variant, provenance, verification and delivery
sections map to every requirement. Implementation choices are grounded in the
current pipeline and pinned vendors; no unresolved owner decision remains.
