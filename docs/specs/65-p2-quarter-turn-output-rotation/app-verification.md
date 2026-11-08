# Standalone rotation controls verification

Before control implementation, all6 discovered browser cases recorded the absent
dropdown:1 failure and5 errors from missing observed controls. After the scoped
port, all6 pass, including actual native-core0/90/180/270 output changes and reset
persistence, target changes, legacy firmware, refusals, lost replies and cancellation
of a save queued while leaving Settings.

The standalone implementation uses master's existing four-argument request operation;
its permission guard is the fourth argument. No inherited timing/identity, clocks
recovery, playlist cache, watchdog, power-callback or USB diagnostic code is imported.
The firmware/core inputs remain byte-identical to the core proof1658636.

Full app discovery with one worker passed all452 cases. The original full app
run is clean; the JSON records outcomes, exact run identity and log hashes.
All88 discovered onboarding checks and7 static app scope checks also pass.
Task1's qualified core/emulator/firmware/mapping evidence remains recorded separately;
unchanged native suites were not repeated for these UI-only changes.

Firmware/APK builds, Android VM packaging checks, independent artifact folders and
final PR/CI handoff belong to delivery task3. No board was accessed. Physical LED
orientation, board boot/radio/SD and real phone acceptance remain open.
