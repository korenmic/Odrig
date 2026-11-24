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

## Physical retest rejected the callback candidate

The owner subsequently confirmed that the new `429d2ebe...` image retains the same
boot/no-hotspot failure, while the historical working firmware still recovers the
board. The locally reproduced callback defect was real, but repairing it **did not
fix the reported regression**. The startup-repair task is reopened. Windows and
Ubuntu CI passing for `bd71e9b` likewise does not establish physical boot success.

The next control is **master's source built with the same Windows toolchain**, so
the test can separate PR code from the host-build/boot-compatibility difference
between current builds and the historical working binary. The existing clean
control build's tracked `core/` and `firmware/` inputs were compared with freshly
fetched `origin/master` and match exactly. `firmware/verify_build.py` passes.

`Artifacts/odrig/odrig-master-control.bin` is a separately named diagnostic control,
not another claimed fix: 1,879,840 bytes, SHA-256
`df61d0b5828bac4f4bbd487839d5eb01734c4103c7f031a5cae93f0ccabc0c3f`.
It uses the same application offset `0x10000` without Erase. Its checksum, build
record, verification and readme are beside it. The original FW/APK/signing files
were not changed by this delivery. `master-control-delivery.json` records evidence.

Its physical result is pending. If it boots, bisect the PR firmware changes with
controlled builds. If it also fails, investigate the host build/toolchain and boot
compatibility against the operator's known-working binary. A phone USB capture of
panic/reset output remains the quickest way to identify the actual failing path;
an empty or disconnected capture is also useful evidence. Keep the known-working
backup available for normal operation. No repeated speculative repair is warranted.

## Master control boots; physical reset capture analyzed

The operator confirmed that `odrig-master-control.bin` boots correctly, while the
latest PR image still fails. This rules out a general failure of this Windows
build pipeline; the difference remains in the PR image or its delivery/loading.

The supplied USB text capture was located in the desktop transfer cache and copied
to ignored investigation output without changing its source. It is 901,088 bytes,
34,929 lines, SHA-256
`7c599db5146b7ccc659dd45bff9daff0af4e8dff78c5fe95abcb4c965312328e`.
It contains 3,488 complete `RTC_SW_SYS_RST` reset lines and 3,489 occurrences of
`Saved PC:0x403cc9b1`, with no runtime `#log` lines, Guru Meditation or backtrace.
The ROM repeatedly loads a bootloader whose entry is `0x403c885c`. This confirms
a real software-reset loop, but does **not** identify its trigger. The captured
loader differs from the fresh factory loader used in earlier emulator runs.
Nearby official loader symbol files did not match its exact layout; their decoded
addresses are not accepted as the physical fault site.

The captured driver is CDC-ACM, which does not by itself prove which physical
socket was used. The firmware documentation specifies runtime logs on the socket
marked COM at 115200 baud. Clarify the capture socket and obtain any missing
COM-side error/backtrace before assigning the reset to a particular code path.
No bootloader/partition overwrite or erase is proposed.

An isolated midpoint was also built through fw.py from `317eca0` plus current
master, retaining time/schedule integration and producer fairness but excluding
the later clocks recovery, inventory and rotation changes. The clean diagnostic
merge is `09ee6f0b17d785849f830e11fdac7e79800f8d3e`; offline verification passes.
Its application is 1,887,664 bytes, SHA-256
`2320cb37599f6a54faf3593889ca2a8d6ddcef214dd72eae446d9873762bbfe3`.
It remains local and unflashed, not a delivered fix. Source-bisection can use it
if the log cannot narrow the cause. The primary PR and usual Drive artifacts
were not changed by this diagnostic build. The physical boot-repair task remains open.

## Exact retained-loader reset path identified

The owner confirmed the capture used the socket marked USB. An independent audit
found a public copy of `bootloader_s3.bin` matching the historical checksum in
`firmware/stock.sha256`: 13,600 bytes, SHA-256
`53f1e17c81e72cdd99ce362ad9a8181a229d3879b11561b2e76052e1afa17c45`.
Its entry and all three loaded addresses/lengths exactly match the physical trace.
The unmodified vendor header specifies 8 MB; the documented physical loader has
the 16 MB header adjustment. Its code is unchanged by that adjustment.

Disassembly of these exact bytes identifies `0x403cc99c` as the loader's reset
routine. It calls the ROM reset function at `0x403cc9ae`, then loops at
`0x403cc9b1`, exactly the reported saved PC. Callers are failed early loader
initialization (`0x403c8871`) and exhaustion of bootable application candidates
(`0x403cca29`). This locates the captured resets **before application execution**;
it does not by itself distinguish those two callers or prove a corrupted download.
Rotation, WLED power callbacks and the core scheduler are not executing at this site.

The loader's candidate-image wrapper unconditionally uses load mode 3, the
`ESP_IMAGE_LOAD_NO_VALIDATE` mode of ESP-IDF. Its image-error logging is absent.
Consequently another COM capture may also be silent, and a payload bit flip is
not an effective rejection control: the descriptor-bit-flip case still boots.

Isolated 16 MB emulator fixtures use the matched loader, its documented 16 MB
header adjustment, the same partition/storage fixture and the exact published
application bytes. ESP-EMU 0.51 reaches runtime and answers `status` and `fault`
for both master (`df61d0b5...`) and PR (`429d2ebe...`), with zero resets in each
45-second host run. These cover approximately 1.9 seconds of emulated time,
not a sustained physical board/radio/SD test.

A negative control changes only the first application's segment length from an
aligned value to an unaligned value. The same loader then requests a software
reset before runtime, with the windowed return address corresponding to
`0x403cc9b1`. This reproduces the relevant loader rejection path, **not the
unknown original byte difference or physical cause**. QEMU attempts with the
retained loader did not reach the reset breakpoint before their bounds; they
remain inconclusive and are not counted as passes.

`retained-loader-verification.json` records input hashes, exact addresses,
bounded results, negative-control mutation and the outstanding evidence.
The useful next physical evidence is an application-region flash readback,
compared byte-for-byte with the exact file downloaded on the phone. There is
no reason to request a whole-flash/NVS export or overwrite the retained loader.

`Artifacts/odrig/odrig-pr41-429d2ebe.bin` is a freshly named, byte-identical PR
application, with checksum, existing source provenance and a diagnostic readme.
It allows an explicit fresh-file retry with Compression off, at `0x10000`
without Erase, then an application-only readback if needed. This is a controlled
delivery/write-path test, **not a rebuilt or newly repaired firmware**. Mounted
Drive readback is verified; independent cloud/phone bytes are still unverified.
The usual firmware, working master control, APK and signing backups are unchanged.
Task4 and physical acceptance remain open.
