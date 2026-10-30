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
