# Startup regression investigation and repair

The operator repeated the old/new firmware comparison on the same ESP32-S3:
the previous backup boots and advertises Wi-Fi, whereas this PR's image gives a
steady blinking LED and no usable hotspot. The operator used the application image
at `0x10000` without Erase. Master is the requested stable source baseline. No
board, serial boot log or physical reset reason was available locally.

## Confirmed code fault

The new WLED `onStateChange` adapter called `manualPower`, which waited in
`while (OdrigFiles::holding()) delay(1)` **before** checking initialization or
whether the observed power state changed. WLED invokes its state hooks during
preset initialization and unrelated state changes as well as manual power changes.
With storage pacing continuously occupied, even these no-op callbacks could wait
indefinitely. They run inside WLED's state handling, so this can prevent completion
of initialization and further main-loop/network service. A real power request also
performed filesystem writes synchronously inside the callback and its caller's
resources. Master has no such power callback.

`tests/firmware/test_power_callbacks.py` compiles the **actual production callback
body**, with the same harness convention as the refresh fairness regression. The
host supplies permanently busy storage and raises a sentinel if the callback tries
to delay. Before repair, six scenarios failed with result `10` (storage wait):
initialization, unchanged power, explicit requests, observed transitions, and an
initialization event following an explicit JSON value. This is an executable
reproduction of the callback fault, not a measurement of the physical reset.

Callbacks now only record intent using a short independent critical section;
neither the state callback nor JSON-state hook takes the player lock or performs
storage work. The main loop nonblockingly checks pacing and applies one latest
queued manual request through the ordinary core command route. Scheduled feedback
still does not create a manual override, initialization discards its explicit value,
and repeated explicit On/Off requests retain their existing semantics. The core,
wire protocol, watchdog, task priorities, stacks, output wiring and current limits
are unchanged. All seven harness scenarios pass after repair.

## Actual-image emulation and limits

The delivered failing image was preserved before rebuilding: 1,890,736 bytes,
SHA-256 `2a5acf5027444a1f658c32289f8db922082da0585dd8f1158fc1a81486524eba`.
Its factory image's application bytes matched the delivered file exactly. The
linked ELF had one consistent `Core` layout and one consistent `odrig_host` layout
across the compiled core and firmware adapter units; no stale-object ABI mismatch
was found. Its ESP32-S3 header and image checksum were valid.

Espressif QEMU 9.2.2 stopped in the SDK's ADC calibration constructor, before our
startup code; that is an emulator peripheral limitation, not this regression.
Espressif ESP-EMU 0.51.0's portable WASM interpreter booted the actual PR image and
a fresh master-equivalent image with identical populated LittleFS storage. Both
answered periodic UART `status` and `fault`, with no reset across a bounded
300-second host run. This did **not** reproduce the operator's failure. Both also
kept `fps:0` and initial checking state, so this model cannot establish successful
physical LED playback. The SD card was absent, and there was no real radio, phone,
USB cable or board power supply in that run.

The independently reproduced callback fault is repaired. **The exact cause of the
operator's physical reboot/no-hotspot incident remains unconfirmed.** Installing
the new application image without erasing storage, checking Wi-Fi/playback and
reading a boot/reset log if the fault persists remain operator acceptance. The
phone USB diagnostic APK from seed 70 remains available for collecting that log.

The affected discovered suites cover 2,470 cases: core 1,097, emulator 687,
firmware 658 and firmware-host 28, including 21 platform skips. The full run
recorded four failures from the fixture's empty guard generating an unused-variable
warning before that fixture correction was loaded. All four corrected cases passed
with both GNU and MSVC; the failed full run is retained, not relabeled clean.
`startup-verification.json` records the counts, rechecks and log hashes. The repaired
application image also answered four `status` and four `fault` reads with zero
resets in a 120-second bounded ESP-EMU run; the same playback/peripheral limits apply.

Clean-source firmware publication is recorded separately with delivery.
