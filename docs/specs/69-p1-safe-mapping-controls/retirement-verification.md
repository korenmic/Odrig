# Cross-wiring control retirement

Valid failing regressions were observed before changing production code in
`build/seed69-task1-red-verified.log`: both retired commands returned success rather
than refusal, the checkbox and both app APIs were present, and a pin save on another
snake's valid custom strip geometry was refused. The initial attempt had incomplete
new-checkout test setup and is not counted as regression evidence.

The dedicated command, reply member, checkbox, app APIs and Snake10 geometry branch
are removed. Pin saves now preserve generic validated column/start data. This keeps
existing mapping files usable without silently changing physical wiring. Ordinary
pin revisions, no-op saves, atomic persistence, diagnostics and miniature projection
retain their coverage. Historical seed43 material remains history; current docs and
append-only decision/drift entries describe the owner's retirement request.

The discovered mapping suite passed all36 checks, including refusal without mutation,
actual browser/API absence, generic geometry preservation and normal mapping controls.
One new fixture initially used a helper that throws for a missing element; its absence
check was corrected to use `getElementById` and then passed.

## Integrated task gate

Run `build/tests/20261101-042904-117612`, log `build/seed69-task1-suites.log`.
Core:1050 tests passed with7 compiler-specific skips. Mapping:36 passed.
Emulator:657 tests,636 passed,20 platform skips and one upload-tool failure.
App:446 tests,442 passed and four setup/environment failures. The parallel run
finished in1084s with an unsuccessful exit; all failing checks were rechecked below.

An upload-tool test returned status3/no reply in the parallel emulator run. The same
unchanged full upload/play/restart/remove case passed in isolation in19.999s
(`build/seed69-task1-upload-recheck.log`). Three app conversion tests initially lacked
this new checkout's locked GIF/video decoder packages. After `npm ci --prefix converter`,
the complete eight-test conversion module passed in53.059s
(`build/seed69-task1-conversion-recheck.log`). Neither incident required production
changes. One app toolchain fixture assumes default checkout-local build paths, while
the initial helper overrode `ODRIG_TOOLS` to another checkout's shared cache. That
unchanged fixture passed with the override removed in
`build/seed69-task1-local-path-recheck.log`. Final app verification uses default paths;
firmware fixtures can separately reuse their shared tool cache. The original failed
run is retained rather than relabeled all-green.

No board was accessed or flashed, no published APK/FW was replaced, and actual phone
interaction/physical LED acceptance remains open. The confirmed Settings edit lock is
the next separate task.
