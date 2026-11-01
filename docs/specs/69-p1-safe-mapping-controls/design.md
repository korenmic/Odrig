# Design

Retire the dedicated cross command, reply member, app wrappers and checkbox. Replace
special-case wiring serialization with generic preservation of the loaded column
geometry. An editable target is twenty180-LED snakes, each confined to its assigned
three columns on a60x60 canvas. The validated mapping file already guarantees complete
strips and unique coordinates. Derive each strip's column and starting end from its
first LED, and emit optional starts only when they do not alternate. Revisions remain
the CRC of pin bytes; a pin no-op remains write-free. No geometry is changed by pin
saves and no extra frame/state allocation is introduced.

Keep an app-local locked flag in the mapping screen. It is not persisted or sent to
the board. A dedicated modal dialog has descriptive text, explicit confirm/cancel,
normal Escape handling and focus restoration. Capture the target version for the
prompt; accept only while still on the same visible Settings screen with a fresh
editable mapping. Both directions require confirmation. No native blocking alert.

Include the flag/prompt in the shared mutation guard. Guard want/pump, pointer/key
entry, defaults and saveFromPhoto, and expose canEdit/watch to the photo UI. Disabled
controls communicate the guard; programmatic activation cannot bypass it. Reading
and photo analysis are separate from applying a result. Relock on screen exit,
visibility loss and target reset; discard unsent wanted moves and cancel gestures.
Do not cancel a command already on the wire; retain its existing reconciliation.

Keep historical seed43 material as history; current docs and append-only decisions
and drift entries explain the owner's retirement request. New regressions cover the
removed operation and non-destructive legacy-file pin saving, followed by real-browser
lock/cancel/unlock/relock and photo/target/visibility paths. Existing editable mapping
scenarios explicitly perform the newly required confirmed unlock.
