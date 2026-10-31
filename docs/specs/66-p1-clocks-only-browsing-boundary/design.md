# Design

Use the shared client as the navigation authority. Seed67 first introduces a resolved
Only boundary and unavailable view for automatic recovery; this spec adds deliberate
enter/back and destination guards to the same seam. A path is inside when it equals
`clocks` or starts `clocks/`, with resolved folder identity for the active target.

Validate before mutating the trail or notifying watchers. Back stops at the Clocks
root. Rendering derives its Back affordance and unavailable reason from this state.
Never briefly publish ordinary root during constrained recovery. Keep mode controls
and Settings/Target independent of content navigation. Confirmed Off/Between releases
the boundary; target changes clear it before establishing the new target's state.

Upload preparation and final guarded preflight both require an in-bound destination.
An absent external destination cannot use the old internal-root fallback in Only.
Authoring uses the same client path, not a second navigation implementation. Invisible
root-name collision queries remain permitted. No wire behavior changes.

Browser scenarios drive both DOM controls and direct client calls; stand-in transport
faults cover missing media and stale replies. Emulator tests exercise actual firmware
policy. Tests observe the forbidden escape before the guard is implemented. Amend the
old unrestricted-browsing prose and append the owner's new policy to decision/drift
logs. Human phone/LED acceptance stays open.
