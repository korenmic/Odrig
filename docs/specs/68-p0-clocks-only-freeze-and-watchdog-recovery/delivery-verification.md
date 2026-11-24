# Integrated delivery

The paired software artifacts are built from clean runtime commit
`e7f09ee7e9bedb09f234ba84b3f32a8452175c96`, including the inherited timing/fairness
work, seeds65–68 and merged master mapping-safety seed69. The installation is
permanently1:1; no rectangular fit choice remains. This delivery proof commit adds
metadata only after artifact verification/publication.

## Verification

The discovered host suites exercised5315 cases with28 platform skips. Nine latest
suite outcomes passed. The full app run had538 successes and one initial8s connection
timeout in an unchanged catalog case; that case then passed unchanged in isolation
3.114s. The earlier now-bar timeout passed in the corrected full app run. Both failed
full runs and corrected message/vocabulary contracts remain recorded; no failed
full run is relabeled green. See seed65's app-verification.md and the delivery JSON.

Firmware built successfully through fw.py on Windows in78.93s using the unchanged
default odrig_microsd configuration. Offline image/source/symbol inspection confirms
the ESP32-S3 application image and clean source provenance. No board was contacted.
APK signing reused the dedicated persistent key; signature, alignment, source bytes
and all eight discovered packaging tests passed.

An actual Android16 read-only clone of the existing AVD passed upgrade from the
previously published APK, clean installation and launch. Its native Wi-Fi/plugin
and module-worker path confirmed phone-zone/UTC sync, daily hours, manual precedence
and Resume. The shared native square clocks/messages fixture then confirmed all four
saved rotation choices, default-locked mapping edits, deliberate Only startup and
actual Wi-Fi disable/enable recovery. During disconnection the known inventory stayed
visible and unsafe controls were disabled. On reconnect the same list, keys, version
and DOM row survived; observed paths never left Clocks. Original AVD configuration
was unchanged and only the owned clone was stopped.

The first Android attempt already passed installations, then stopped on a private
fixture's incorrect emulator constructor keyword. Corrected it to the existing
--drive option, retained the first log, and completed the full second attempt. No
product change or Mac-dependent verification was needed.

## Publication

The existing files in Google Drive Artifacts/odrig were overwritten in place:

- odrig-debug.apk:19112989 bytes,
  SHA256`7a9c171ee5793bcd8ecc9bcda2415c24ae1e6540e5290dc87039f2dbdebaabab`.
- odrig-firmware.bin:1890736 bytes,
  SHA256`2a5acf5027444a1f658c32289f8db922082da0585dd8f1158fc1a81486524eba`.
- Existing firmware checksum, build/inspection records and odrig-delivery.json updated.

Readback verified bytes, sizes, mounted-drive device/inode identity and in-place
replacement for all seven files. This is mounted-client evidence; no independent
Drive API file-ID lookup is claimed. Persistent signing key/configuration/certificate
and reuse README backups remain unchanged and were verified beside the artifacts.
The certificate SHA256 remains
`5a489ec294e53cdec085d71092cf4e7285ae08d4d43c19929d84130f3649f0f1`.
The firmware file remains an application image for offset0x10000, not a full-flash
erase/factory operation. No physical board was flashed.

## Handoff and remaining acceptance

One combined PR41 targets master on the authorized branch above the inherited PR39
work. Exact final pushed-head Windows/Ubuntu CI is the remaining remote handoff gate
and is reported in the PR after completion. No history is rewritten. Seed/task
software completion does not tick physical LED/phone/electrical acceptance: the
operator still needs to observe the actual board's Only playback, Wi-Fi, orientation
and phone behavior after installing the paired artifacts.
