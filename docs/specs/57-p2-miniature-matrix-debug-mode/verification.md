# Miniature matrix verification

## Shared app controls

Windows browser/emulator run `20261030-080018-196332` discovered376 app tests
and647 emulator tests. The emulator suite passed, with19 skips. The app run
reported five failures: the new source needed ASCII escapes, the approved
command needed adding to the app's command contract, the error-code table
needed its twentieth entry and explanation, and two existing screen-data waits
failed under the combined run. The source/contracts were corrected; both wait
cases passed unchanged in the isolated recheck.

The29-case recheck covered the full miniature, message and scope modules plus
both failed wait cases.28 passed; the additional late-reply test needed to wait
for the old command to reach its target before switching addresses. That test
then passed with the explicit synchronization. No remaining failed assertion is
being deferred. The final integrated suite pass is recorded below when run.

Browser checks cover accepted-but-pending requests, actual acknowledgement,
refusal, lost reply, fresh readback, malformed status, legacy/unsupported targets,
failed setup retry and restoration, another controller, reload without resending,
target changes including late completion, and320/360-pixel/landscape layouts.
The shared app also enables and disables the real emulator's miniature mode.
An initial focused run first exposed the legacy null-member crash; its missing
capability path was corrected before the successful focused run.

These are automated browser and host checks. Physical phone, electrical and
board acceptance remain open. No firmware or final APK was built at this point.

## Core and host-output proof

The shared core uses one optional 192-byte startup block, including one 180-byte
physical RGB image. Measured total host allocation with a drive is 131041 bytes,
below 131072; the ordinary core object remains within its 4096-byte bound.
The earlier full core run passed 963 tests with one skip. Vectors cover logical
RGB, palettes, text and widget layers, cap rounding before averaging, black side
columns, corners/axes, normal mapping permutations, off/blank output and unchanged
normal legs. No per-frame allocation or second decoder is added.

The actual LED output adapter and staged transition controller compile and run
against host stand-ins. Checks cover clear/drain/setup order, renewed in-flight
transfers, setup failure, dark output, retry, restoration, selected GPIO/length
and current-accounting inputs. Earlier regressions first found a stale20-output
summary after selecting one bus and setup attempted during a resumed transfer.
The integration's lock and service ordering are also checked. This does not
compile the complete WLED usermod or prove physical transfers/current limiting.
The WLED interface was reviewed at pinned revision
`29b389df1c1aaec6ff53aea742d17063b985906c`.

## Orientation evidence

The manufacturer sources linked in the root README are the Eagle schematic/PCB
archive and the linked XL-1010RGBC-WS2812B datasheet. Archive SHA256:
`0095e346fbfe0f5f3315b010d4990827268dad60c50f481bd1cd8e2ac4c8efea`.
The DIN-to-DOUT traversal contains 60 LEDs, LED116 through LED39. Rotating the
component view into landscape front view with IN at left yields straight columns
and physical index `x*6+y` from bottom left. The datasheet's page5 threshold is
2.8V minimum at5V. These are source-derived facts for the documented part;
received-part correspondence, signal margin and powered orientation are open.

## Deterministic emulator smoke

On Windows, 150 virtual ticks at20ms intervals produced150 refreshes. Every
180-byte miniature frame exactly matched independently accumulated gradient
block averages, with maximum channel34 and black side columns. SHA256:
`a2905446947302d726f2807c4235f45f4c78c4f9a4ab2916599b87015d0dad33`.
The normal10800-byte frame stayed unchanged at requested brightness255 while
miniature brightness was40. No installed files changed; disabling restored normal
output and a new core started with miniature off. This is virtual timing, not
a50FPS hardware measurement. The local report is `build/seed57-smoke.json`.

## Acceptance still open

- Actual matrix part, assembly, direct-data margin and powered corners/axes.
- ESP5V supply/protection/current and simultaneous USB paths, including boot,
  failed setup and restored normal brightness; the mini cap is not power proof.
- Physical internal/microSD frame, text and widget playback, dark transitions,
  responsive USB/Wi-Fi routes and20–50FPS.
- Real Android checkbox/readback, other-client changes, reconnect and reboot.
- Complete firmware compilation is expressly deferred to future seed60. No board
  was connected or flashed. The final APK is built only after seeds56–59 software.

Task5 remains unchecked until those human observations actually occur. Software
proof does not accept the full wall's mapping or replace its earlier open checks.

## Integrated Windows verification

Run `20261030-082054-117352` discovered every normal suite supported by this
computer. Results, including the explicitly identified rechecks:

| Suite | Discovered tests | Result |
|---|---:|---|
| JavaScript converter | 1581 | Passed |
| Python converter/library | 552 | Passed |
| Core | 963 | Passed,1 skip |
| Emulator/command tool | 647 | One Windows socket error; that case passed unchanged in isolation;19 skips |
| Shared app | 377 | One Windows socket error; all other376 passed; serving class7/7 passed after connection reuse |
| Mapping | 43 | Full recheck passed after scoping unsupported wait |
| Onboarding | 88 | Full recheck passed after vocabulary/command contract update |
| Runner | 22 | Passed |

The first aggregate execution exited with errors; no clean single aggregate run
is claimed. The vocabulary assertion first omitted the approved `debug` family.
The mapping browser first matched the miniature panel's unsupported text before
its own error arrived; its wait now reads the mapping error specifically. Both
full suites passed in `build/seed57-task4-doc-recheck.log`.

Two tests met `WinError10055` while opening sockets. The emulator upload test
passed unchanged in the isolated recheck. The app catalog-serving case met the
same error again; its loop opened a connection for each of538 files. It now
reuses the server's existing HTTP/1.1 connection, retaining every file/byte/type,
cache and rejected-path assertion. The whole serving class passed7 tests in
`build/seed57-task4-serve-recheck.log`; no production server behavior changed.
No failed assertion or error case remains unverified. Logs are retained outside
the runner's automatically pruned per-run folders.

The normal firmware suite/pipeline requires unavailable Mac tooling; it is not
reported as passing here. Complete firmware compilation is waived for this run.
Firmware host-output stand-ins are part of the discovered emulator suite. The
PlatformIO configuration uses the entire usermod directory, including its new
header; this source-inclusion check is not a firmware compilation. APK and manual
walkthrough suites are separate release/acceptance work, not normal host suites.
