# Design

Use the shared client as the navigation authority. Retain the last confirmed Only
policy for the active target through missing mode metadata and communication errors.
A path is inside when it equals `clocks` or starts `clocks/`, with resolved folder
identity. The status already provided by master establishes this policy; no firmware
or protocol change is required.

Validate before mutating the trail or notifying watchers. Back stops at Clocks.
The visible controls derive their affordances from the same guard; Settings, Target
and leaving Only remain available. Unknown destinations show an unavailable Clocks
view rather than publishing an ordinary root list. Existing inventory refresh and
catalog behavior remain as on master; this feature adds no inventory cache or automatic
ID remapping/recovery subsystem.

Upload preparation and final fresh-policy preflight require a writable external
Clocks destination in Only. There is no internal-root fallback in that mode. The
flat-root authoring form can preview but cannot save outside this boundary. Invisible
root-name collision queries remain permitted, and normal-mode upload fallback remains.
Guard each shared upload job as well, cancelling an opened staging transaction if a
mode change makes its destination invalid before commit.

Browser regressions exercise direct calls, visible controls, stale/unknown policy,
prefix collisions, destination capture/preflight and mode changes. The emulator tests
continue to use master's firmware. Physical phone and board checks remain open.
