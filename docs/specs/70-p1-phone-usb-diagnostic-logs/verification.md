# Software verification

## Host and Android compilation

- The production Java capture model passes nine cases: passive reads, explicit status/fault,
  permission denial/retry, cancelled grant/open, overlapping capture refusal, late reads,
  fragmented UTF-8/untrusted text, bounded full export and I/O closure.
- Two discovered browser cases verify Android-only availability, selecting a visible port,
  retaining its identity after reordering, readable unplug/permission states, explicit
  report/share actions, retained text, no HTML execution and cancellation when leaving.
- The actual Android plugin compiles against SDK 36 and pinned USB driver 3.11.0.
  Deprecation notes are present; compilation succeeds. The driver sources were inspected
  for open/close/control-line behavior; electrical reset-line behavior is not proven.

## Failures seen before corrections

The new selection regression initially failed because the first option became blank
(`selectedVisible` was false); it now passes, including retaining a selected device
when enumeration order changes. The full app suite also caught a readonly-log text
selection violation, an ASCII-source violation and transport access outside target.js.
Those product rules remain intact: the extra selection override was removed, source text
uses ASCII, and USB native calls are behind the existing target transport boundary.

Legacy assertions were updated for four native classes and the new documentation section
and HTTPS reference. No board command or Wi-Fi command behavior changed.

## Complete suite and exact rechecks

Full app run `20261101-153513-152652` executed 550 cases: 547 passed, two old documentation
assertions failed, and an unchanged brightness case timed out waiting for initial app
startup at eight seconds. The two documentation assertions were corrected. All three
exact cases then passed in 3.829 seconds; the brightness case needed no product change.
All 550 cases therefore have passing verification. The full run itself was not clean
and is preserved, along with the earlier five-failure run. No failed report was rewritten.

Local evidence: `build/seed70-app-final.log`, `build/tests/20261101-153513-152652/`,
`build/seed70-case-rechecks.json`, `build/seed70-case-rechecks.log`,
`build/seed70-selection-red.log`, `build/seed70-selection-green.log`,
`build/seed70-scope.log`, `build/seed70-docs.log`, `build/seed70-long-press.log`,
`build/app/usb-native-compile.log`.

## Open physical evidence

The operator has only a phone. APK/VM delivery is the next task. Physical USB drivers,
permissions, reset-line behavior, real board output and sharing a real capture are not
proven by the host or Android VM tests. The reported missing Wi-Fi/steady-blinking incident
is still undiagnosed; this APK feature collects the evidence needed to investigate it.
No firmware change, board access, flash or erase was performed for this feature.
