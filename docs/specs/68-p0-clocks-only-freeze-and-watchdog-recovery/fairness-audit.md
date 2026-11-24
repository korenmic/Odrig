# Retained fairness repair audit

The inherited candidate is317eca0c23586038772f07936f3abddef6458a65. Exact Git comparison
against the integrated runtime e8924ab4367bdb0086dd156f57ace9b1c9978c7e found no changes
in `firmware/usermod/odrig_usermod.cpp` or `tests/firmware/test_refresh_fairness.py`.
The repair is reused; no duplicate runtime patch is introduced.

The producer remains pinned to CPU0, priority1, stack8192. Update/output gates retain
their50ms notification wait. Every ordinary poll is followed by `vTaskDelay(1)` after
`refreshDue` returns and its local lock has been released. Watchdog feeding, timeout,
priority, stack and output behavior were not changed by this work. The existing clean
candidate's offline SDK proof records the enabled five-second CPU0-idle watchdog and
1000Hz scheduler; final delivery will recheck the rebuilt image/configuration.

Fresh source-based comparison compiled the actual task bodies from the pre-repair
9b64f48b117f70febfe08f459064725f2a315a8b and retained e8924ab source using the tracked
scheduler fixture. Both immediate consumption and already queued notifications showed
6400ms of uninterrupted modeled work and zero blocking ticks before repair. Retained
source showed32ms and200 blocking ticks for200 overdue32ms renders. Results are in
`fairness-audit.json`; the local audit log is `build/seed68-task1-before-after-proof.log`.

Discovered firmware verification on Windows:

- Microsoft compiler:654 tests,28 skips, passed in247seconds
  (`build/seed68-task1-firmware.log`, run20261101-032712-154064). Twenty-seven skips need
  the GNU POSIX-SD stand-in; one filesystem-link check needs Windows symlink privileges.
- Installed GNU compiler:654 tests,1 symlink skip, passed in160seconds
  (`build/seed68-task1-firmware-gnu.log`, run20261101-033256-190500), covering those SD cases.
- Production-body fairness, idle polling and suspended-output cases are included in
  both discovered runs. No security settings were modified.

This is a compiled production-body scheduling model and native host coverage. It is
not instruction-level ESP32/Wi-Fi emulation. The affected board's installed revision
and reset cause are unknown; the model proves a starvation path but does not identify
that particular physical reset. No board was flashed, erased, observed or reconfigured.
Physical sustained Only playback, Wi-Fi and phone acceptance remain open.
