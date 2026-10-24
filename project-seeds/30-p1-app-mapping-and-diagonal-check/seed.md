# App mapping and a diagonal check

## Summary

The operators' app lets an operator choose which physical ESP32-S3 data pin drives
each of the twenty three-strip snakes. The complete assignment is saved on the
target, takes effect without reflashing or uploading animations again, and survives
a restart. The same screen can show a single diagonal line on the real LEDs so an
operator can check the mapping by eye. Both features belong to this one seed.

## Priority

- `P1`

## Depends On

- Seeds 02, 03 and 04, for the shared player, emulator and firmware.
- Seed 05, for twenty column snakes and the 60 x 60 canvas.
- Seed 06, for the JavaScript converter used to prepare the diagnostic animation.
- Seed 07, for durable changes to the installed file set.
- Seed 09, for the shared Android and browser app and emulator Controller view.
- Seed 16, for the playlist to restore after a mapping check.

## Product Context

The owner requested these features together on 2026-10-23. The installation has
twenty independent snakes, each three strips of 60 LEDs, with one data wire for
each snake. If two data wires reach different pins from those expected, the
operator should be able to correct the software assignment from the app.

Today `mapping.json` defines the canvas and each leg's data pin, but the app cannot
change that installed mapping. The default assigns snakes 1 to 18 to GPIO 1 to 18,
snake 19 to GPIO 21, and snake 20 to GPIO 47. These are defaults; this feature makes
the assignment editable on a target. An uninterrupted diagonal across the actual
canvas makes a misplaced group of three columns apparent to the operator.

The feature does not identify wiring electronically or claim that an operator has
confirmed it. Changing wires, supplying power and deciding which physical pins are
safe remain the owner's work. This seed changes software assignments only.

## Technical Constraints

- Put mapping controls and the diagonal-test controls in `app/www/` once. The APK,
  browser app and emulator's Controller view use those same files and behavior.
- The shared core owns mapping validation, persistence and diagnostic playback.
  The emulator and every firmware use the same rules. Hosts apply output routing
  changes to the actual driver; changing labels alone is not an implementation.
- Keep `mapping.json` as the sole persisted mapping definition. Store assignments
  in its existing `pin` members, preserving geometry, leg identities and direction.
  Do not add a second settings file that can disagree with it.
- Expose the necessary read, whole-assignment update and diagnostic start/stop
  operations as one mapping command family on every existing transport, including
  serial, HTTP and the emulator's TCP port. Extend `odrigctl` and document the
  protocol during specification. No app-only HTTP settings endpoint is added.
- Keep the existing command and reply size limits. Twenty assignments fit in a
  bounded reply. Report enough target state for another controller to display the
  saved mapping and whether the diagonal test is active.
- Prepare the diagonal as a tracked JSON-frames source and encode it with the
  JavaScript converter. Package the generated ODRG asset with the emulator and
  each firmware build. Play it through the normal decoder and mapping pipeline;
  do not convert or generate media on the board or implement a separate LED driver.
- The diagnostic is a built-in service animation. It needs no user upload, item id
  or ordinary show entry, cannot fill user animation storage, and never joins the
  normal playlist or a cycle. It does not depend on seed 29 being implemented.
- Follow existing core memory constraints, durable-storage guarantees and the
  accepted board refresh range of 20 to 50 a second. Existing shows and mappings
  retain their behavior until an operator explicitly saves a change.

## Required Behavior

1. On a valid target mapping of twenty three-column snakes and a 60 x 60 canvas,
   the app shows twenty rows labelled by physical canvas position, from left to
   right: snake 1, columns 1-3; snake 2, columns 4-6; through snake 20, columns
   58-60. Each row shows its assigned GPIO number, matching the board's pin label.
   Canvas position and GPIO are visibly different concepts.
2. An operator edits the assignment as a permutation of the same twenty distinct
   output pins already present in the target's valid mapping. Selecting a pin
   assigned to another snake swaps those two assignments. The app does not offer
   arbitrary new GPIOs, USB pins, power pins or a change in the number of outputs.
3. Edits are a local draft until Save. Save sends the complete assignment in one
   transaction. Cancel restores the last read target assignment. Provide a draft
   action to restore the default assignment above, enabled only when those pins
   are the target's current pin set; it still requires Save to take effect.
4. The target validates all twenty assignments before changing anything: one pin
   per snake, each current output pin used exactly once, and unchanged dimensions,
   geometry and snake directions. Reject partial, duplicate, missing or foreign-pin
   assignments without altering routing or storage. A non-target bench mapping
   remains playable, but this editor and diagnostic are unavailable with a clear
   explanation; they never rewrite it into the twenty-snake target.
5. A successful Save durably replaces the pin assignments, applies them to the
   actual LED outputs and reports success only when they are in effect. A power
   cut or storage failure leaves a complete old or new valid mapping. Never emit
   a refresh assembled from a mixture of both assignments. Preserve animation
   files, playlist exclusions, timing settings and the rest of the show.
6. Keep the current animation running when routing changes, except for the bounded
   interruption needed to reconfigure outputs. When testing, the diagonal continues
   through the new assignment as soon as it is committed. No board reboot,
   reflashing, rewiring or re-upload of animation files is needed.
7. The app reads authoritative state from the target on entry and after Save.
   Prevent stale drafts from silently overwriting a mapping saved by another
   controller: detect the changed base assignment, explain the conflict and let
   the operator reload before trying again. Disable Save while a request is
   pending. A failed or uncertain request is not shown as a confirmed save.
8. "Show diagonal" enters a target-wide diagnostic mode, pauses ordinary show
   progression and loops the diagnostic until explicitly stopped. Exactly the
   sixty pixels with x = y, from (1,1) at the bottom left to (60,60) at the top
   right, are white; every other pixel is black. The line is one LED wide, stays
   still and is the only visible pattern. Do not add text, grid lines or markers.
9. "Stop diagonal" exits diagnostic mode and resumes the previous playlist or
   cycle from the beginning of the animation that was current on entry, if it
   still exists. If it no longer exists, resume the first available playlist
   animation under the current playlist rules, or idle if none is available.
   Explicit ordinary play also exits the diagnostic and performs that play.
   Starting or stopping the diagnostic again is harmless and does not lose the
   original resume selection. Reject upload, remove and playlist-setting mutations
   with the existing busy behavior while the diagnostic is active; mapping saves,
   status, list, power and brightness controls remain available.
10. Diagnostic entry and exit do not change brightness, on/off state or current
    limiting. If output is off, the app explains why the diagonal is not visible
    and the operator can use the existing On control. A restart keeps the saved
    mapping and starts the normal show, with the diagnostic off. Closing the app
    does not terminate a test another controller may still be using; any connected
    controller can see and stop it.
11. The app clearly distinguishes a locally edited draft from the mapping saved
    on the target. While a diagnostic is active, explain that it uses the saved
    mapping and that the operator must save a draft to check it. The operator
    confirms by eye that the real line is continuous and has the expected slope;
    software never labels the physical wiring as verified automatically.
12. The emulator refreshes its served mapping and Mapping view after a save,
    including pin labels and routing, without restarting. Its LED output uses the
    same mapping and diagnostic as the board. Tests separately inspect per-pin
    data because a correctly rendered logical canvas alone cannot prove routing
    on a physical installation.
13. Update mapping, core, commands, app, emulator and firmware documentation, the
    firmware additions list, and the relevant default-pin and command decisions
    with an append-only change-log entry during implementation. State that the
    original pin table is the default and installed runtime mappings may permute
    it. Ship both halves together: remapping and its diagonal check.

## Definition Of Done

1. One requirements/design/tasks trio covers both features together and resolves
   the mapping command syntax, persistence transaction and host-routing handoff.
   These are engineering design work, not remaining product questions.
2. All suites that need no board pass. Core tests cover identity and swapped
   assignments, invalid assignments, stale updates, durable recovery at every
   storage step, preserving the show, diagnostic pixels, enter/exit behavior,
   power and brightness, and restart recovery.
3. The converter checks and encodes the tracked diagonal source. Decoded pixels
   are exactly the sixty specified white pixels and otherwise black. Both
   firmware builds and the emulator use the same encoded pattern.
4. Browser tests against the emulator exercise editing, swaps, Save, Cancel,
   default restoration, another controller changing the mapping, failures and
   diagnostic controls through the shared web UI. Transport tests verify the
   same behavior over every supported route. Existing bench mappings still work.
5. Automated routing checks deliberately swap at least two GPIO assignments and
   inspect per-pin LED data before and after Save, including across a restart.
   A mapping view screenshot by itself is insufficient evidence.
6. Build the Android APK and both firmware variants with the repository tools.
   An owner checks the app on a phone against the real twenty-snake installation:
   start the diagonal, observe a deliberately wrong assignment, correct it in the
   app, Save and see a continuous bottom-left-to-top-right line. Restart and check
   the saved assignment, then stop the test and confirm ordinary playback.
   Board tooling uses brightness at most 40, one program at a time, and never
   changes wiring or power. Report the firmware, mapping and show left installed.
7. Any unavailable real-LED or phone check is explicitly reported as open
   verification; it is never claimed from the emulator alone.

## Open Questions

None. The behavior and scope above are resolved. Physical verification is an
implementation acceptance check for the owner, not a prerequisite to writing the spec.
