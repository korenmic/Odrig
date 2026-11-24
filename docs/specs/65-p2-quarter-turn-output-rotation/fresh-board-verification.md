# Fresh-board orientation configuration

The failure was reproduced before the fix in both shared-core tests and the exact
shipped ESP32-S3 application image. An empty LittleFS store produced
`mapping-missing` and `rotation` returned `supported:false`. The binary model used
image SHA256`7a62b36ca4bb6e90811e9e9ff0e64b6a00b19fb624dc9e9a34ea869146e66c9d`;
the first reproduction ran9.686 host seconds/0.25047 emulated seconds, with zero
resets. This establishes the fresh-storage fault, not physical radio/LED behavior.

Native regressions also failed before the fix for absent/malformed mapping/show
content, a read-only empty installation returning show-invalid instead of the real
storage error, and inventory validation blocking the independent setting. The
owner clarified that the installation is always60x60 and orientation must remain
configurable independently of its content.

The production firmware now initializes only a fresh store with the existing
canonical square mapping and a valid empty show. The transaction's compiled host
tests cover every mutation interruption, failed/short writes, failed readback,
complete/partial/unrelated operator files and unknown folders. A separately observed
regression reproduced a saved rotation interrupting initialization; its retry now
preserves independent rotation files while completing its own defaults.

Verification performed before the task4 proof commit:

- Full discovered core suite:1065 tests,1063 passed,1 skipped,1 outdated invalid-show
  file-open expectation failed. Independent orientation now deliberately opens its
  saved file after a content fault. Corrected the two exact sequence expectations;
  all44 discovered startup tests then passed.
- Rotation scope:16 tests passed. The integration case obtains the persisted bytes
  from the compiled production bootstrap, starts the actual shared core, uploads an
  asymmetric animation through the ordinary protocol, checks its original bytes,
  verifies exact output for all four angles and restarts to confirm saved state.
- Full discovered firmware suite with the existing littlefs-enabled repository
  interpreter:658 tests,656 passed,1 skipped,1 environment assertion failed because
  the invocation inherited an external shared ODRIG_TOOLS cache. With that variable
  unset, all7 discovered environment tests passed. The initial system-Python attempt
  lacked littlefs and is retained as an environment failure, not a passing run.
- Bootstrap scope:8 tests cover canonical mapping equivalence, empty dark show,
  interruption retries, storage/readback faults, operator-data preservation and
  rotation saved during interrupted initialization.

Logs are retained under`build/rotation-fresh-board/`; the exact pre-fix ESP32-S3
image evidence is under the parent worktree's`build/rotation-fresh-s3/before/`.
`tests.firmware.test_fresh_board.materialize(folder)` runs the compiled production
transaction and materializes its exact files into an empty folder for subsequent
native integration checks. No firmware image was built or published in this task.
Rebuilt-image/Android-VM checks and delivery belong to task6. Physical LED/radio and
phone-on-board acceptance remain open.

## Rebuilt image and installed APK

The official Windows firmware pipeline built clean committed source
`9d7aa6a453763eb270403ebb9345e465f8d94fd0` and passed offline ESP32-S3 header,
source/provenance and linked-symbol inspection. The1885056-byte application has
SHA256 `062de8d4723e9db8b3246f0984f8c0409483b5a67005b5d21ef27bc26b99929a`.

The exact binary passed three ESP32-S3 instruction/peripheral-model fixtures:

| Initial store | Player status | Rotation |
|---|---|---|
| Empty LittleFS | Ready,60x60, no animations | All four saves;270 restored after CPU reset |
| Partial installation, no mapping | Mapping missing/recovery | All four saves;270 restored after CPU reset |
| Canonical mapping, malformed show | Show malformed/recovery | All four saves;270 restored after CPU reset |

Each case had zero spontaneous resets. Total emulated time across its intentional
reset was1.343,1.301 and1.314 seconds, respectively; host time was42.539,38.281
and46.352 seconds. These are bounded configuration/persistence checks, not sustained
rendering, radio, SD, USB cable, flash readback or physical LED acceptance.

APK source is clean integration commit
`e08ba55e4c16cac91af5896a820ccbfd4690063f`; all core, firmware and canonical
mapping inputs are byte-identical to the firmware source. The19088118-byte APK
has SHA256 `fb2f13e5afb561c48dbd22316159f01b7f0100947205d2e2fc7d8d9b76c894c3`.
It retains the existing dedicated signer. All8 discovered APK checks and88
onboarding checks passed after integrating master.

The installed APK passed upgrade from the previous PR44 APK, clean installation,
launch and all four enabled rotation controls on the dedicated read-only Android16
VM. Its unchanged native Android Target sender and Wi-Fi availability gate used an
ADB reverse tunnel and transparent HTTP-to-UART adapter to this actual ESP32-S3
binary, starting from empty LittleFS. No native-core stand-in or command/reply mocks
were used in this APK integration. Captured native sends for90,180,270 and0 each
returned HTTP200 with matching `ok:true`, `supported:true` and degrees. The model
bridge recorded31 commands/31 firmware replies and zero resets over5.938 emulated
seconds/188.403 host seconds. The VM, reverse/forward ports and bridge were closed;
the owned AVD configuration was unchanged. Native tests separately prove exact
rotated output pixels. Physical radio and LED acceptance remains open.

Both existing payload files in `Artifacts/odrig/standalone-rotation` were overwritten
in place, with no rename, and their mounted bytes and local file identities verified.
The existing share URLs are retained. Usual root artifacts and all signing backups
were hashed before and after and remained unchanged. Updated provenance, model,
Android and checksum sidecars accompany the files. Independent cloud-server/phone
byte readback was unavailable; an anonymous download returned HTML rather than an
image. The complete delivery record is in `standalone-delivery.json`.

GitHub Windows/Linux checks on the final pushed head are a separate ready-handoff
gate; the delivery record does not claim those checks before they finish.
