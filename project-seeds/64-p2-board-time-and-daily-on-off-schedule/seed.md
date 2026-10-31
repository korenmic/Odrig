# Board time and a daily on/off schedule

## Summary

Allow a controller to read and set the board's current civil time through every
existing command transport, including Wi-Fi/HTTP and USB serial. Use a valid board
clock to run one daily on/off schedule, defaulting to On at 18:00 and Off at 06:00.
The APK exposes the schedule in Settings and a visible, enabled-by-default option
to set board time from the phone when connecting after a sufficient interval.
When the board loses its time, ignore the schedule until time is set again.

## Priority

`P2`.

## Product Context

The owner requested this seed on 2026-10-31. A board should retain its daily
operating hours independently of a connected phone, while accepting time from any
controller that uses the board's protocol. A power loss or reset must never cause
an unsynchronized clock to turn the installation on or off at an invented time.

The existing `on` and `off` commands control LED visibility; `off` leaves playback
time running. This seed schedules that existing behavior: the board remains powered
and reachable, with no relay, power-supply switching, deep sleep or wiring change.
Existing animation clocks show imaginary elapsed-time animation, as documented in
`docs/format.md`. This seed's real clock serves control and scheduling; changing
those animations to show actual time is separate work.

## Required Behavior

1. Provide transport-independent operations to read board time and set it from a
   controller. Any existing command transport must reach the same shared state,
   validation and replies; connecting alone does not supply time automatically
   unless that controller performs the synchronization. Do not add a new APK USB
   transport just to implement this seed.
2. A time read distinguishes valid from unset/lost time, reports the current time
   and its applicable local-zone/offset interpretation when valid, and exposes
   enough confirmation for a controller to verify a set. Invalid time is explicit,
   never disguised as midnight, Unix epoch zero or a restored stale timestamp.
   Reject malformed/out-of-range writes without changing the accepted clock.
3. Once valid, advance the clock using monotonic elapsed time without requiring
   the phone, Internet access or NTP. Phone wall-clock changes must not alter
   animation/playback elapsed timers. A later accepted time update may correct
   the civil clock forwards or backwards; evaluate the current schedule state
   rather than replaying every missed on/off boundary.
4. Treat clock validity as boot-local. After power loss, a new core instance or
   reset, consider the clock invalid until a new accepted set, even if the saved
   schedule remains available. Do not restore a previously saved wall-clock value
   and assume the board was powered for the intervening time. No added RTC or
   battery is required. While invalid, bypass the schedule and retain ordinary
   startup/manual on/off behavior; show that scheduling awaits valid time.
5. Store one board-owned, persistent daily pair of minute-resolution times, using
   24-hour `HH:MM`: On defaults to `18:00`, Off to `06:00`. Scheduling is enabled
   by default once valid time exists. Expose an explicit schedule enable control
   alongside the times so the operator can suspend scheduling without erasing
   them. Validate the complete pair, reject equal times, and save atomically with
   confirmed readback. Failed or interrupted changes retain the last valid pair.
6. Support both same-day and overnight intervals. For the defaults, the scheduled
   On window is [18:00, 06:00 across midnight), and the Off window is [06:00, 18:00).
   At exactly 18:00 turn on; at exactly 06:00 turn off. Evaluate immediately when
   valid time first becomes available, after an accepted correction, or after
   schedule settings change, subject to the resolved manual-override policy below.
   Repeated polls within the same window must not cause repeated writes or resets.
7. Share the clock and schedule behavior with the native emulator. Keep ordinary
   playlist timing, off-state playback progression, brightness/current limits,
   miniature mode and command responsiveness intact. A scheduled On must not
   reset brightness or restart an animation merely to make it visible again.
8. Settings shows the confirmed board time, whether it is valid, the schedule
   times and enabled state, and an understandable reason when scheduling is
   disabled or awaiting synchronization. Edits belong to the selected board;
   changing targets cancels pending work and must not apply it to another board.
9. Settings includes `Set board time from phone automatically`, enabled by
   default, as a persistent APK preference. Show whether the most recent attempt
   succeeded, failed or is unconfirmed, with its confirmed time when available.
   Turning this off stops automatic writes; it does not invalidate a previously
   valid board clock or disable the board-owned schedule. Provide a manual
   `Set time from phone now` action and a board-time read/refresh operation.
10. On the first successful connection or reconnection after the agreed interval,
    query clock validity and, with auto-sync enabled, send the phone's current time
    and the agreed zone information. Always synchronize an invalid board clock
    immediately, even if that board was synchronized shortly before it reset.
    Rate limiting is per board; a different board must not inherit another's
    cooldown. Ordinary HTTP requests/status polling are not separate connections
    and must not cause a time write on every poll. The cooldown begins only after
    an acknowledged successful set; failed/uncertain attempts do not report success
    or enter a tight retry loop. This seed does not require periodic background
    synchronization while the app is disconnected.
11. Other controllers can use the same read/set operations. Accepted writes are
    shared board state, not a private APK clock. Handle multiple controllers,
    disconnects and uncertain replies consistently, with re-read confirmation and
    no later replay of a queued write to the wrong target. Older firmware must be
    identified as unsupported without breaking its existing controls.

## Technical Constraints

- Planning only: this request creates a seed, not specs, queued implementation,
  firmware/APK changes or artifact delivery.
- Reuse the one core, serialized command interface and shared `app/www` for APK
  and emulator. New protocol operations need exact wire forms, capability and
  reply/error contracts in S2S; obtain the owner's required approval for actual
  additions to `docs/commands.md` before implementation. The current request
  authorizes the read/set-time and schedule functionality, not guessed spellings.
- Time-zone/DST behavior is an owner question below; do not silently substitute
  UTC, a hardcoded Israel offset or whatever time WLED happens to have at boot.
- Keep schedule configuration across resets but never persist clock validity.
  Use existing bounded storage and atomic-update conventions. Do not write flash
  every tick, time query or automatic time synchronization.
- Preserve current arena, Core-size and stack bounds. Clock calculations and
  schedule evaluation must be bounded and nonblocking and survive monotonic timer
  rollover. Internet availability cannot be a prerequisite for manual time sync.
- Do not change existing imaginary animation clocks, hardware/current settings,
  bootloader, partition table or existing WLED configuration implicitly. During
  design, account for other on/off sources without introducing competing policies.
- Run discovered relevant core, emulator, app, command-tool and firmware-host
  suites with deterministic fake clocks; no real overnight waits. Verify an APK
  against an owned Android emulator when possible. Physical phone/board timing
  and observed LED acceptance remain explicitly open until a person checks them.

## Open Questions Requiring The Owner

1. **Reconnect synchronization interval.** How long is "the first time in a
   while"? Proposed default: 15 minutes since the last confirmed sync to that
   board. Alternatives: one hour or every reconnect. Invalid time always bypasses
   this cooldown when auto-sync is on.
2. **Schedule time zone and daylight saving.** Follow the phone's time zone,
   including its daylight-saving rules (proposed), or keep the board in the Israel
   time zone, including daylight saving, regardless of the connected phone?
   The chosen zone must define schedule behavior while offline and at DST changes;
   it must not rely on the phone being connected at the transition.
3. **Manual On/Off precedence.** Proposed: an explicit manual On or Off overrides
   the schedule until the next scheduled boundary. Alternative: the schedule is
   always authoritative and manual controls cannot override its current window.
   Apply the chosen rule consistently to all command transports and on/off sources.

The seed is **not yet ready for S2S with zero open owner questions**. These three
product decisions remain; the proposals are not recorded as accepted. Exact wire
forms are subsequent specification work with owner approval before coding.

## Definition Of Done

1. Owner questions are answered in the seed; requirements/design/tasks define the
   clock, validity, time zone/DST, schedule persistence, manual precedence and
   reconnection rate limit without implied defaults left for implementation.
2. Every existing transport reads/sets the same board clock and schedule, with
   validation, supported/unsupported behavior and confirmed state.
3. Deterministic tests cover default and edited overnight/same-day windows, exact
   boundaries, day rollover, time jumps, DST under the selected policy, timer
   rollover, invalid time, reset/power loss, disconnected operation, disabled
   auto-sync/schedule, reconnection cooldown, other boards and competing clients.
4. App tests cover visible defaults, manual synchronization, target changes,
   refusal/timeouts and confirmation. Tests prove no per-poll time writes, flash
   write loop, unexpected brightness change or playback restart.
5. Portable relevant suites and firmware/APK verification pass. Firmware and APK
   delivery occurs only under a later implementation request; any unperformed
   physical board/phone checks remain stated openly.
