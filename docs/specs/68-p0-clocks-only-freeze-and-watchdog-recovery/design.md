# Design

Audit the inherited producer against317eca0 and retain its compiled production-body
regressions. Existing before/after scheduler evidence is authoritative only for the
modeled starvation path:200 overdue32ms renders previously had6400ms uninterrupted
work; the repaired body blocks each iteration. Do not add the same patch again.

Add integrated coverage only where missing: sustained native Only clocks/messages,
late time steps, delayed storage/command replies and reconnect recovery, with bounded
test time and explicit status/command responsiveness assertions. Share invariants
with67 without duplicating its tests or counting core emulation as FreeRTOS/Wi-Fi.
If no residual fault is reproduced, report that fact; do not invent a further fix.

After65–67 are implemented, run all supported suites on the integrated branch. Build
firmware with fw.py, retain offline image/ELF/source proof, and build the same shared
app into an APK using the existing persistent dedicated key. Verify installation and
upgrade on an owned read-only Android AVD clone without altering another project's
VM. Publish both files through in-place writes to the existing mounted Drive paths;
verify hashes/size, mounted file identity and unchanged signing backups. Never output
key passwords. Capture provenance in a delivery document and commit its task proof.

Push one branch/new PR, attach it to the chat and gate the exact final head on CI.
Notifications report actual committed milestones and final upload contents. Leave
installed physical build/reset cause and phone/board acceptance unperformed unless
observed. No flashing or network/power configuration changes are part of this run.
