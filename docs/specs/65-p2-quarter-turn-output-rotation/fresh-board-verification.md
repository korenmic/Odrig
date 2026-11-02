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
