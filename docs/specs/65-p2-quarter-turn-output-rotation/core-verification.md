# Shared square output verification

The owner fixes the installation at1:1. No rectangular fitting choice is required.
The core uses three spare state bits and a shared inverse coordinate permutation;
no allocation, frame buffer, arena/Core limit, wiring or power policy was enlarged.

## Observed before implementation

`build/seed65-task1-red.log` ran the first ten native regressions against missing
support: rotation operations returned unknown-command, required fields were absent,
and output remained unchanged instead of the independent quarter-turn expectation.
The expected-matrix helper's clockwise convention was corrected before runtime
implementation to match bottom-left coordinates growing upward.

## Native checks

The first ten focused checks passed in5.076s after implementation. Full core
discovery then passed1097 tests in413.969s (11 compiler-specific skips), including
the expanded twelve rotation cases and unchanged resource guards.

Coverage includes RGB and indexed asymmetric pictures, text and clock widgets,
message-clock masks, both picture-clock overlay types, exact four-angle output and
miniature chain projection, reset persistence, malformed/read-failed saved settings,
no-op/frame IO absence, read-only storage, active upload, stale/invalid requests,
every injected atomic save failure and unchanged physical diagnostics.

Initial compile failures identified a guessed reply include and incomplete miniature
type; actual command/mini headers fixed them. The strict test host then correctly
rejected the new metadata names; only rotation.txt/rotation.part were added to its
allowlist. No runtime file-ownership workaround or relaxed validator was introduced.

## Discovered suites

- Core:1097 tests,11 compiler skips, passed (`seed65-task1-core-discovered.log`).
- Firmware:654 tests,1 Windows symlink-privilege skip, passed167s
  (`seed65-task1-suites.log`, run20261101-102600-82692). Ordinary show preservation,
  explicit replacement and readback include rotation metadata.
- Mapping:42 tests passed54s, including confirmed edit-lock behavior.
- Emulator:687 tests passed228s,20 platform skips, final run20261101-103541-5280,
  `seed65-task1-emulator-final.log`. Initial687-test run passed native
  rotation/output/transports but failed four stale command inventory/documentation
  expectations. Those expectations/examples were updated without weakening the
  session reply/log assertions. The full corrected run is retained separately.

The firmware-only selector was initially repeated with an abbreviated option and
selected only its last value; it is counted only as firmware. Core used independent
unittest discovery, and emulator/mapping used the correct comma-separated selector.
No two report runners ran together, and no active emulator/app library was rebuilt.

The emulator's native core/frame/miniature and real HTTP/TCP checks verify shared
software behavior; they do not establish physical LED orientation, electrical
behavior or a real phone's acceptance. Those owner checkboxes remain open.
