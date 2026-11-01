# Standalone rotation core verification

The standalone branch starts directly on master and imports only saved output rotation,
its shared command/CLI contract and metadata preservation. The firmware adapter and
public host ABI are identical to master. No time/schedule, recovery/inventory, rendering
fairness, power callback or phone USB diagnostic implementation is included.

Before implementation, discovery of the12 rotation tests against master recorded34
subtest failures and7 errors from missing commands/fields and unchanged output. The
earlier broad baseline was stopped before these cases and is not counted as a pass.

The affected discovered run covers2,412 cases: core1,062; emulator659; firmware649;
mapping42. Core, firmware and mapping passed. The original emulator run retained one
documentation failure (rotation examples outside its command-tool section) and one
unchanged static-file HTTP test error (Windows socket buffer exhaustion10055).
The corrected documentation passed all21 discovered documentation checks. After the
full runner ended, all25 unchanged discovered static-file checks passed. No timeout,
assertion, OS networking or production behavior was weakened. The original failed
run remains retained; it is not relabeled a clean full run. The JSON records exact
counts, failures and log hashes.

All angles match independently computed RGB, palette and composed text/clock/message
and picture permutations in native tests, including miniature projection. Diagnostics,
atomic save failures, no-op writes, reset persistence and existing memory limits are
covered. The square fixture requests124,515 bytes in18 blocks; orientation uses spare
state bits and adds no canvas allocation. Real firmware/APK packaging is a later task.

No board was accessed. Physical boot, radio/SD behavior, LED orientation and phone
acceptance remain open; native success does not establish a physical boot-loop fix.
