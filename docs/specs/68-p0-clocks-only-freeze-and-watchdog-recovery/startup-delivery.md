# Power callback repair delivery

The firmware was built through `firmware/fw.py build` from clean runtime commit
`22758471c861fd6a0d10dfad49839a741e5bf0a7`, then inspected through
`firmware/verify_build.py`. The clean build is byte-identical to the application
tested in the bounded ESP32-S3 emulation run recorded in `startup-verification.json`.

The existing `Artifacts/odrig/odrig-firmware.bin` on the mounted Google Drive was
overwritten in place, together with its checksum, build manifest, offline
verification and image inspection. The release record was updated. Read-back
bytes, sizes and device/inode identity were verified; there was no independent
Drive API file-ID lookup. `startup-delivery.json` records the publication evidence.

- Application image: ESP32-S3, `odrig_microsd`, offset **`0x10000`**, no Erase.
- Bytes: **1,890,944**.
- SHA-256: `429d2ebe8072923acbd11a40b1e764ac29e08f20cfb3830d5dfe00b8cdddf0bb`.
- The existing APK and signing backups were not rebuilt or replaced; their bytes
  and mounted-file identities were verified unchanged. USB diagnostic capture
  remains available in the APK's Target panel.

The confirmed callback defect and passing before/after harness are described in
`startup-regression.md`. The affected suites cover 2,470 cases with 21 skips and
four corrected fixture-warning cases rechecked successfully on GNU and MSVC.
The exact physical no-hotspot/reset incident was **not** reproduced in full-chip
emulation; real radio, SD, output, USB and power acceptance remain open. No board
was accessed, erased or flashed from this workstation. The operator must retest
the new application image; a boot log is still needed if the physical fault remains.

Both proof commits belong to PR41. Its checks report the final pushed head;
earlier Windows/Ubuntu successes are not claimed for a new commit.
