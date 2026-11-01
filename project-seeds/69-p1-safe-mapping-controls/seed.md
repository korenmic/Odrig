# Safe mapping controls

## Summary

Remove the Snake10 cross-wiring feature and protect accidental mapping edits with a
confirmed lock toggle in Settings. The owner requested both changes on master.

## Priority

`P1`.

## Product Context

Mapping drags and photo fixes currently save immediately. They need a deliberate
unlock before they can alter pin assignments. The dedicated Snake10 cross-wiring
checkbox and wire operations are no longer wanted.

## Required Behavior

1. Remove the dedicated cross-wiring checkbox, app APIs, command routing and command
   documentation. `mapping cross ...` is refused without writes. Mapping replies no
   longer advertise the option. The generic mapping file format remains usable;
   pin-assignment edits preserve the installed geometry rather than rewriting wiring.
2. Settings displays a clear mapping-edit lock toggle, locked by default. Both unlock
   and relock ask "Are you sure?" with explicit confirm/cancel choices. Cancellation
   changes nothing. The lock is an app interaction guard, not a board permission.
3. Lock all mapping mutations: handle dragging, held-row dragging, arrow-key moves,
   Restore defaults and photo Apply/Other reading. Guard the save handlers as well
   as visibly disabling their controls. Reading/Reload, photo analysis and diagnostics
   remain available. Starting a diagnostic does not itself change the mapping.
4. Reset the lock on app load, target change, leaving Settings and app visibility loss.
   Never carry an unlock or an outstanding confirmation to another target. Discard
   unsent queued moves when relocking; an already-sent save must still be reconciled.
5. Keep the single shared app/core, durable revision-checked writes, default pin set,
   canvas, hardware, power and bounded resource use. No board operations are requested.

## Technical Constraints

Preserve generic per-strip mapping data, including existing valid custom starts.
Remove Snake10-specific algorithms rather than introducing silent geometry migration.
Keep the historical seed43 specification as history, with current decisions/docs
explicitly superseding its product controls. Use failing regressions before repairs,
discovered suites and a dedicated branch/PR from current master.

## Open Questions

None. The owner's request authorizes retirement of the option and its prior decision;
the lock uses the current command protocol and needs no new command.

## Definition Of Done

The option is gone, all mapping mutation paths require confirmed unlock, targeted
regressions and supported discovered suites pass, and the focused PR is merged into
master. Actual phone interaction and LED/wiring acceptance remain owner's checks.
