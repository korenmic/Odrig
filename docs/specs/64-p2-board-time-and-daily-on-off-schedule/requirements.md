# Requirements: board time and a daily on/off schedule

Source: [seed](../../../project-seeds/64-p2-board-time-and-daily-on-off-schedule/seed.md).
The owner resolved every product question and authorized autonomous protocol choices,
implementation, verification and delivery. No owner question blocks this specification.

## 1. A shared civil clock

1.1 Every existing transport reads and sets the same boot-local board clock. The
native emulator uses the same core implementation as firmware.
1.2 Before an accepted time set, and after reset/power loss, time is explicitly
invalid. A saved schedule or time zone never makes a stale clock valid.
1.3 Accept UTC seconds in 2000-01-01 through 2099-12-31. Reject invalid numbers,
unknown zone revisions and malformed writes without changing the accepted clock.
1.4 Once set, advance using monotonic elapsed time without a phone, Internet or NTP.
Clock corrections never change playback elapsed time, animation seeds or brightness.
1.5 Readback distinguishes invalid time, zone errors and usable current UTC/local
time. Confirm a successful write; do not claim an uncertain response succeeded.

## 2. The phone's time zone and DST

2.1 Use the phone's IANA zone and its offset-transition rules, including offline DST.
Do not assume Israel or infer future behavior from the current offset alone.
2.2 Transfer and atomically verify a bounded zone snapshot for the supported time
range. Preserve its identifier, offsets and transition instants; no Internet fetch
is required. An unchanged snapshot does not write flash.
2.3 A changed phone zone is reflected when auto-sync is enabled without resetting
the 15-minute clock-sync interval. An explicitly disabled auto-sync performs no
automatic time or zone writes.
2.4 A malformed, unsupported or failed zone update retains the prior accepted zone.
Missing/corrupt zone data or uncovered UTC never causes guessed scheduled switching.

## 3. Daily scheduled LED visibility

3.1 Persist one minute-resolution On/Off pair and an enabled flag. Defaults are On
18:00, Off 06:00, enabled. Equal times and invalid HH:MM are rejected atomically.
3.2 Support overnight and same-day On windows, inclusive at On and exclusive at Off.
Evaluate the present window at time acceptance, corrections, relevant settings
changes and refreshes; never replay missed boundaries after a time jump.
3.3 Ignore scheduling while time/zone is unusable. Keep ordinary startup/manual
behavior, expose why scheduling is inactive, and resume evaluation when usable.
3.4 Scheduled Off blacks out LEDs while the board remains powered and reachable.
Playback continues; scheduled On preserves its position and brightness.
3.5 Never write storage per tick, poll, boundary or routine clock synchronization.
Failed settings publication keeps the prior complete settings.

## 4. Manual control always wins

4.1 Existing manual On/Off from any command transport establishes a persistent
override. It outlives boundaries, time/zone updates, reconnects and reset/power loss.
4.2 Only explicit Resume schedule releases the override. Editing times or enabling
auto-sync does not release it. Resume immediately evaluates a usable enabled schedule.
4.3 Expose override, effective On/Off, enabled state and errors separately. A failed
manual-state save must not prevent immediate manual LED control; report that its
persistence failed. Hosts without writable settings retain ordinary manual controls.
4.4 Disabling scheduling retains times and manual mode. No relay, supply, wiring,
WLED settings, existing imaginary animation clock or partition behavior changes.

## 5. Connection-triggered phone synchronization

5.1 APK auto-sync is visible in Settings, persistent, enabled by default and separate
from schedule enablement. Manual Set time from phone now is also available.
5.2 On a successful connection/reconnection, inspect time. With auto-sync enabled,
set an invalid clock immediately, otherwise sync only if at least 15 minutes have
elapsed since the last confirmed sync to that board, including a manual sync.
5.3 The timer expiring does not itself cause synchronization. HTTP/status polls are
not connections. No periodic background time-sync timer or retry storm is introduced.
5.4 Keep per-board cooldown and target guards across awaits and queued operations.
Switching boards must neither carry another board's cooldown nor replay stale writes.
5.5 Confirm time/zone after setting, retain a truthful success/failure/unconfirmed
indicator, and avoid counting failures as successful cooldown starts.
5.6 Older firmware is identified as unsupported while its ordinary controls continue.

## 6. Settings and delivery

6.1 Settings shows confirmed board time/zone, invalid-time explanation, auto-sync
preference, latest result, On/Off time fields, schedule enablement, manual override
and Resume schedule. Controls reflect current target and pending/unsupported states.
6.2 A clock read/refresh and a time set both use the serialized request path; long
zone preparation leaves the UI responsive. The shared web app is the APK UI.
6.3 Deterministic discovered tests cover boundaries, DST skips/repeated hours, jumps,
rollovers, persistence/failure, resets, transport parity, target races and cooldowns.
6.4 Preserve existing arena/Core/reply/stack bounds and allocation discipline.
6.5 Build firmware through fw.py on Windows; build the APK using the existing
persistent signer; verify install/update/launch in an owned Android emulator.
6.6 Overwrite existing Drive APK and firmware in place, verify bytes/identity, retain
signing backups, push the implementation and send notify milestones/completion.
Record physical phone/board acceptance as unperformed; do not flash/erase a board.
