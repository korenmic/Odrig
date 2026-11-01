# Sustained playback and reconnect verification

The native core was exercised with the real 60x60 clock format and all seven shipped
message variants, using temporary managed external catalogs. Source collection files
were not changed. Existing policy, inventory, navigation and upload proofs in specs
66/67 remain applicable; their implementation was not repeated.

## Observed residual fault and repair

The browser connected to a real native emulator through a controlled HTTP peer with
150ms status delays and one deliberately failed status reply. Before the repair,
the test retained the animation array, preview-key array and list version but failed
`sameRow`: transient unknown capacity changed the row's writable identity and rebuilt
its DOM node. This was observed in `build/seed68-task2-native-reconnect.log` before
changing the renderer.

The renderer now keeps the last rendered writable badge in its identity comparison
while capacity is unknown. Action permissions still use current observations, and
the selection checkbox is disabled if current write eligibility is absent. A known
permission or content change still changes row identity. The same native reconnect
test then passed in 4.670s (`build/seed68-task2-reconnect-green.log`), including:

- Known rows remain visible, stale inventory is marked and playback is disabled.
- Recovery stays inside Clocks, with no root transition.
- Animation/key arrays, list version and the actual DOM row remain identical.
- Recovery sends no new list or catalog-page request for unchanged authoritative data.

## Sustained native coverage

`test_only_sustained.py` passed all three checks in 4.714s
(`build/seed68-task2-native-proof.log`). Two runs each advance five accelerated
minutes, with and without messages, 33ms polls, periodic 234ms late steps, and delayed
external reads. Each checks over 1,000 produced frames, lit output, over 200 status
replies and over 50 fragmented byte-feed commands. Playback never reports a root
animation or error, and card bytes remain identical. The messages run observes more
than one shipped message. A third test exchanges 30 HTTP/TCP status pairs during
live Only playback, checking their bounded response time and valid current file.

These native checks exercise the production core and existing transports. Accelerated
time is not a five-minute wall-clock endurance test and does not execute ESP32 Wi-Fi
or FreeRTOS. Scheduler coverage is recorded separately in `fairness-audit.md`.

## Discovered suites and exact outcomes

The integrated run `build/tests/20261101-035236-45704`, logged in
`build/seed68-task2-suites.log`, ran core, emulator, app and firmware by discovery
with eight workers. Runtime inputs were frozen throughout the run.

| Suite | Result |
| --- | --- |
| Core | 1,085 tests, passed; 7 compiler-specific skips |
| Firmware | 654 tests, passed; 28 platform/compiler skips |
| Emulator | 685 tests, 664 passed, 20 platform skips, 1 socket resource error |
| App | 533 tests, 532 passed, 1 initial connection timeout |

The full run exited unsuccessfully; it is not represented as an all-green run.
The emulator error was Windows socket error 10055 while the unchanged page-serving
test opened a connection. The app timed out while initially checking its target,
before its changed-animation assertions. With the same runtime and test sources,
the complete page-files module plus that exact app test then passed all 26 checks
in 11.203s (`build/seed68-task2-environment-rechecks.log`). No network/security
configuration or test assertions were changed to obtain that result.

The firmware skips include 27 POSIX-SD fixture checks requiring a GNU-style compiler
and one Windows symlink privilege check. The same unchanged firmware sources already
passed the discovered GNU firmware run for task 1 (654 tests, only the symlink check
skipped). Other skips cover Windows pseudo-terminal/process limitations and core
GNU-tool inspection. Final delivery includes the separate integrated CI gate.

## Acceptance left open

No board was flashed, erased or observed in this task. The affected board's installed
revision/reset cause, sustained physical Wi-Fi and LED behavior, and real-phone
acceptance remain unperformed. Firmware/APK rebuilding and Drive publication belong
to the final delivery task after all authorized software, including rotation.
