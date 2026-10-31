# Cross-platform firmware builds

## Summary

Make the existing `python firmware/fw.py setup` and `build` pipeline compile the
project's firmware on Windows 10 and 11 as well as macOS. A Windows contributor
must be able to produce the default microSD firmware from a fresh checkout,
without a Mac, remote builder, board or global tool installation. Preserve the
existing macOS build, pinned dependencies, artifact layout and firmware behavior.
This is future work; creating this seed does not port or build the firmware.

## Priority

- `P2`

## Product Context

On 2026-10-29 the owner instructed the seeds 56–59 run to continue on Windows
without waiting for access to the Mac firmware toolchain. The owner explicitly
approved deferring that run's firmware build and recording Windows firmware-build
support as a separate seed for later. Software tests, emulator work, the final
APK and its established Drive delivery remain in that run's scope.

The project already builds its shared C++ core and runs its emulator, app tools
and supported suites on Windows. That does not establish that the ESP32 firmware
toolchain builds there. Keep this new scope separate from the nonblocking SD,
miniature display, brightness and clocks features in seeds 56–59.

## Depends On

- Seeds 11, 26 and 51: Windows host tools and core compiler support.
- Seeds 38 and 55: the default microSD toolchain, isolated work folders and
  optionally shared toolchain caches.
- The firmware build as it exists when this seed is specified; carry forward
  feature changes merged before implementation rather than pinning an older app.

## Required Behavior

1. The existing setup/build commands work on Windows and macOS with the same
   meanings. The default produces the microSD firmware with the shared core and
   current usermod. No new command or alternate handwritten build path is added.
2. Select compatible host archives, executables and Python environment paths for
   each supported system and architecture. Retain pinned WLED/Arduino/platform
   versions and verify downloaded archives by the project's existing integrity
   rules. A missing host artifact is a clear unsupported/setup failure, never an
   attempted macOS binary or an undocumented dependency upgrade.
3. Fetch and unpack tools only into the existing ignored work/toolchain folders.
   Do not install system-wide compilers, modify the user's PATH permanently, or
   require a global PlatformIO installation. Preserve `ODRIG_TOOLS`, setup locking,
   checkout-local patched sources and outputs, and safe reuse between checkouts.
4. Handle Windows paths with spaces, executable suffixes, process termination,
   text encoding and line endings. End every owned process on success, failure
   and interruption. Preserve bounded concurrency and Windows job-object cleanup
   used by the project rather than leaving compiler or Node children running.
5. Preserve artifact paths and reporting through `firmware/fw.py`. Record source
   commit, selected host/toolchain versions, output sizes and SHA-256. Firmware
   settings, partitions, capabilities and runtime safety must not change merely
   because the compiler ran on Windows. Cross-host byte identity is not assumed:
   document unavoidable build metadata and compare meaningful firmware content.
6. Preserve the macOS variants and their existing semantics. Inventory the stock,
   probe, microSD, USB-stick and standalone build variants at specification time;
   document and test host support honestly for each. Never imply that a successful
   default build establishes every optional variant or the unfinished standalone
   player's runtime capabilities. Keep Linux-compatible host abstractions; verify
   Linux when a runner is available and state unverified support explicitly.
7. Host compilation, setup tests and artifact checks need no board. No flashing,
   serial operation, hardware/power change or whole-flash erase is part of this
   seed. Existing board and human acceptance remain separate later sessions.
8. Update firmware/setup documentation and runner host selection so Windows builds
   are discoverable through the existing tools. Add discovered regression coverage
   for OS selection, archive validation, paths, setup reuse and cleanup, observing
   each known fault failing before its fix.

## Technical Constraints

- Use `firmware/fw.py`, `firmware/fwtool/` and existing shared toolchain mechanisms.
- Preserve repository rules for builds, protected backup folders and named-path
  commits. Nothing downloaded, compiled or cached is committed.
- No runtime firmware feature or command-list addition belongs here. Do not use
  cross-compilation as a reason to alter GPIOs, current limits, Wi-Fi or storage.
- Resolve host-specific build mechanics during S2S from the actual pinned tools;
  do not promise an unavailable vendor archive or silently change a version.

## Open Questions

None requiring an owner choice before specification. The owner explicitly chose
local Windows firmware compilation as future work and approved skipping the
firmware build in the seeds 56–59 run. Host archive selection and implementation
boundaries are design work grounded in the existing pipeline.

## Definition Of Done

1. A clean Windows checkout sets up and builds the default microSD firmware using
   the documented existing commands, with a recorded source identity and hashes.
2. The same source still sets up and builds on macOS. Relevant discovered suites
   pass on both hosts; platform/variant coverage and any Linux verification are
   reported separately with no unperformed build called successful.
3. Paths with spaces, repeated/concurrent setup and interrupted/failed builds are
   tested, with no global installation, corrupted shared cache or leaked process.
4. Documentation describes host requirements, outputs and honest variant limits.
   No board is touched; the seed's creation alone performs none of this work.
