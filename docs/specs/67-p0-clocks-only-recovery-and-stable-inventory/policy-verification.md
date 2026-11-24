# Standalone saved-policy recovery verification

The extraction starts directly from master `56e2d58`. No time/schedule, rotation,
inventory fingerprint/cache, producer fairness, power callback or USB diagnostic
implementation is included.

The original seed's global inventory redesign remains deferred in aggregate PR41.
This standalone extraction does not claim completion of that combined seed.

Before repair, the five actual-core saved-policy regression methods produced
12 subtest failures on master. Initial/partial read failures and malformed saved
bytes produced `normal frame at 0`; the failed sequential-open case produced a
normal frame at 100 ms. After the policy-only port, all five methods pass.
The original failed log is retained in ignored `build/policy-before.log`.

The MSVC native test host measures the following allocations after the repair:

| Fixture | Bytes | Blocks |
|---|---:|---:|
| 100-item target | 125185 | 18 |
| Target with drive | 130973 | 21 |
| Example show | 88474 | 17 |
| Target without writable storage | 77645 | 13 |

The Core object is 3720 bytes. The existing 131072-byte arena, 4096-byte object
and 512-byte frame limits remain unchanged. The independent retry timestamp adds
eight bytes; no allocation is added after startup.

The discovered core suite completed 1050 cases. Its original full run recorded one
failure because the documentation class had loaded the old allocation table before
its correction. The corrected documentation class and an unchanged HTTP class pass
all 13 rechecks. The latter had encountered Windows socket-buffer exhaustion in the
broad run; no HTTP code change was made.

The initial broad emulator/app run was stopped after retaining partial results to
avoid duplicating browser work before the automatic-recovery change. It is not
reported as a successful full run. The five native saved-policy methods pass, and
the discovered unreadable-policy Settings scenario passes. Task2 owns final frozen
app/emulator discovery. `policy-verification.json` contains exact partial counts.

No physical board or phone was accessed. The owner's boot/no-hotspot incident
is not reproduced or claimed repaired by these native policy tests.
