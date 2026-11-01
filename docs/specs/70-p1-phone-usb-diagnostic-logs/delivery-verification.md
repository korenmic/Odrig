# APK delivery

The APK from clean implementation commit `edf96d8` was built with the existing persistent
dedicated signer. Its certificate SHA-256 remains
`5a489ec294e53cdec085d71092cf4e7285ae08d4d43c19929d84130f3649f0f1`.
Signature/alignment inspection and all eight discovered APK packaging tests pass.

An actual Android 16 VM verified upgrade from the previous published APK, clean install,
launch, real Capacitor USB plugin registration, no-Wi-Fi/no-device handling, refused
missing-port/read/share requests and the native background-open gate. The temporary
AVD `Odrig_Usb_Diagnostics_70` was created under this checkout's ignored build directory
using an already installed image; all ADB commands targeted its owned serial. It was
stopped after testing. No physical USB peripheral or real captured log was emulated.
The real APK screenshot was inspected.

## VM qualifications

The first attempt could not start a read-only instance of the other project's busy AVD.
The second used the owned fresh AVD, passed installation/native checks, but its Home-based
background probe did not establish a stopped activity. The third completed the checks
after provisioning the owned VM and explicitly launching Settings; the native background
gate then passed. No APK/product change was needed between these attempts.

The third attempt's old summary writer subsequently requested nonexistent timing proof
files. Its installation report was reconstructed from the preserved successful command
results and native USB proof, without rerunning passed device checks or changing their
results. The qualification is included in delivery.json. An independent before/after
hash of the other project's AVD configuration was not persisted for this run; that AVD
was not used by the successful run. Original logs are retained.

## Published files

`G:/My Drive/Artifacts/odrig/odrig-debug.apk` was overwritten in place:

- Bytes: `22385971`.
- SHA-256: `7058f799edce216286a3cd8004eb48b9c418fa2209fbcdf95ae59a6f711bf8dd`.
- Readback, size and mounted-file inode identity match. The existing delivery JSON was
  updated in place too. No independent Drive API file-ID/cloud-download comparison is claimed.
- Persistent signing backups are unchanged and still match the local signing files.
- `odrig-firmware.bin` was neither rebuilt nor overwritten; its SHA-256 remains
  `2a5acf5027444a1f658c32289f8db922082da0585dd8f1158fc1a81486524eba`.

Local evidence: `build/app/delivery-proof.json`, `build/app/apk-test-proof.json`,
`build/seed70-android3/commands.json`, `usb-proof.json`, `installation-proof.json`,
`usb-diagnostics.png`, `build/seed70-android-validation3.log` and
`build/seed70-drive-upload-proof.json`. Full app qualifications remain in verification.md.

## Operator next step

Install the updated APK, close the flasher, then open Target > USB diagnostics.
Use the COM/UART USB port through OTG for the full log. Start capture, request
Read status + fault, and Share log. Capturing earlier boot output may require a later
manual reset after current status/fault evidence has been collected. Capture sends no
automatic reset/bootloader/flash operation. Physical permission/control-line behavior,
real logs and real-recipient sharing remain open. The missing-Wi-Fi/steady-blinking
board incident is still undiagnosed; this delivery supplies evidence collection only.
