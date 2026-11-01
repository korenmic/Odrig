# Confirmed Settings rotation

Settings offers exactly0/90/180/270 clockwise for the permanently square installation.
It keeps the confirmed value while a save is pending. Reads reconcile refusal/loss;
target, visibility, connection and Settings lifetime guards cancel unsent writes.
Unsupported firmware disables this control without disabling the rest of the app.

## Observed regression and focused verification

Before app implementation, the actual native-core browser case failed its explicit
presence assertion (`seed65-task2-ui-red.log`, present=False). The first five checks
then exercised the implemented behavior; one fixture assertion used a string folder
as a Path, corrected without runtime changes.

All25 rotation/protocol/documentation checks passed12.351s. Six browser cases cover:
actual native four-angle saves and reopen, non-optimistic pending values, busy refusal,
lost acknowledgement/reconnect without replay, stale target callbacks, legacy support
and cancelling a save queued behind a held reply when Settings is left. The shared
command parser validates replies/degrees/revisions; the inherited native HTTP/TCP and
odrigctl checks verify the same protocol and saved bytes.

## Full discovered verification and retained qualifications

The all-ten-suite run20261101-104520-81768 completed937s. Core1097 (7 compiler
skips), emulator687 (20 platform skips), firmware654 (1 symlink privilege skip),
mapping42, firmware-host28, converter552, converter JavaScript1602 and runner26
passed. App539 had two failures: a missing refusal-table entry/count for the newly
added rotation-conflict code and an initial8s connection timeout in the unchanged
now-bar size case. Onboarding88 exposed the missing command-vocabulary entry/list.

Added a clear conflict message and plain rotation-specific refusal wording, updated
the code inventory and added rotation to the vocabulary. All11 message-table and
rotation checks passed26.684s after those fixes. No clock/playback/network runtime
patch, assertion removal, timeout extension or resource-limit change was made.

Corrected full app/onboarding discovery20261101-110159-19936 completed797s:
onboarding88 passed; app539 had538 successes and one initial8s connection timeout in
the unchanged catalog Not now case. The former now-bar failure passed in this run.
The sole catalog case then passed unchanged in isolation3.114s, recorded in
`build/seed65-task2-catalog-recheck.log`. Every app case therefore has passing
verification on this source, including the isolated recheck; neither failed full
run is relabeled as a clean full-suite run.

Logs are `seed65-task2-all-suites.log`, `seed65-task2-app-final.log`,
`seed65-task2-focused.log` and `seed65-task2-message-recheck.log`. Complete original
all-ten results/report are retained outside report pruning at
`build/seed65-task2-original-proof/`. The current report honestly retains the app
run's timeout; the successful isolated case is separate evidence.

## Release boundary

This proof completes software task2. Task68.3 owns clean-source APK/FW builds,
offline verification, actual Android VM upgrade/installation/shared UI checks,
existing-file Drive replacement/readback, PR handoff and final notifications.
Physical phone, wall/miniature orientation, Wi-Fi, electrical and board acceptance
remain open and are not inferred from host or VM checks.
