# Clocks-only stability verification

Source: project-seeds/68-p0-clocks-only-freeze-and-watchdog-recovery. Owner questions: none.

1. Reuse the producer fairness repair already present in PR39 (317eca0); do not
   duplicate its implementation. Preserve a blocking scheduler opportunity outside
   the core lock on all render paths, including overdue and queued notifications.
2. Keep watchdog configuration, priorities, stacks, output ownership, transition
   suspension, hardware/power and accepted frame-rate bounds unchanged.
3. Audit source/proof provenance and identify actual coverage. Sustained Only clocks
   and messages remain responsive over existing HTTP/TCP/byte-feed paths during late
   rendering, delayed storage/replies and reconnection. The native core does not
   execute FreeRTOS; scheduler-model evidence is labeled accordingly.
4. Any demonstrated residual fault requires its own observed failing regression
   before a repair. Do not invent another cause or suppress the watchdog.
5. After all authorized software work, run relevant discovered suites, rebuild both
   APK and firmware through existing tools, inspect image/source identity, test APK
   installation and shared emulator behavior, and publish verified bytes in place to
   the existing Drive artifacts using the persistent signing key. One new PR covers
   this branch, with exact-head CI checked and a completion notification.
6. Installed physical version/reset cause and board/phone acceptance remain explicitly
   unknown/unperformed unless actually observed. Software verification may complete
   without representing those observations as passed.
