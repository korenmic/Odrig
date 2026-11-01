# Automatic Only recovery verification

The shared browser regression first observed the forbidden path trace
`['clocks', '', '', '', '', '']`: a failed folder ID followed by an empty root and absent
catalog published Root, and subsequent Only statuses could not restore one-shot entry.
This failure is retained in `build/seed67-task3-recovery-red.log`.

The client now keeps reconciled Only recovery context, resolves changed IDs without
publishing Root, and preserves valid descendants. Missing Clocks becomes a virtual
unavailable location. Its null ID cannot request a visible root list. Last-good rows
remain stale, ancestry checks retry at bounded intervals, and returning storage resolves
the preferred path. Unknown policy metadata retains the last confirmed context;
confirmed Off/Between or a target change releases it. Settings and Target remain usable.

Two further observed regressions showed that a still-reported but missing folder ID
enabled Restart clocks and allowed a direct restart to reach the transport. Both now
reject the unresolved ID locally (`seed67-task3-restart-red.log` and
`seed67-task3-direct-restart-red.log`), without claiming a board reply.

Verification on Windows:

- Final focused recovery and clock-mode modules:31 tests passed, including10 new
  recovery/availability checks (`build/seed67-task3-final-targeted.log`).
- Discovered app suite:510 tests were run before the final two restart regressions
  were added. One obsolete missing-folder fixture expected Root rows. That expectation
  was corrected to unavailable Clocks and passed the isolated check and final31-test run.
  The other509 checks passed (`build/seed67-task3-suites.log`).
- Discovered emulator suite:682 tests,20 skips. Runtime checks passed. Three build
  consistency checks were disturbed by an operator recheck recompiling objects while
  the suite held its library. After the suite ended, normal rebuilding and both affected
  binding/build modules passed86 tests,1 skip (`seed67-task3-build-recheck.log`). This
  was test orchestration interference; no security setting or runtime source was changed
  to bypass a check.
- The final restart guards were then covered by the31-test run above. The native core
  is unchanged from the preceding inventory proof; its memory limits remain unchanged.

Deliberate enter/Back restrictions belong to the following browsing-boundary work.
The original physical incident and phone/LED acceptance remain unperformed; controlled
browser and native-emulator evidence does not establish their exact cause.
