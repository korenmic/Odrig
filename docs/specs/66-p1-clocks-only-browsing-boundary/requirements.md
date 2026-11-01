# Clocks-only browsing boundary

Source: project-seeds/66-p1-clocks-only-browsing-boundary. Owner questions: none.

1. Confirmed Only constrains every visible navigation entry to the resolved Clocks
   folder and descendants. Entering Only from outside opens Clocks; a valid nested
   location remains. Component ancestry, not string prefix, defines membership.
2. Shared enter/back/restoration guards enforce this before publishing state. At
   Clocks, upward navigation is disabled. Settings, Target and mode exit remain usable.
3. Missing, excluded, unmounted or unreadable Clocks displays an unavailable Clocks
   location with retry and reason, never the ordinary root. Delayed replies cannot
   escape it. Same-board disconnection retains the last confirmed boundary as stale;
   another board must establish its own policy. Unknown is not confirmed Off.
4. Animations, Upload destination and authoring follow the same boundary. Background
   metadata queries may use root invisibly. An upload that would fall back to an
   unrelated root is disabled until a valid destination is available.
5. Confirmed Off/Between restores normal navigation. Old firmware without Only is
   explicitly unsupported. Protocol listing and existing playback/Ignore semantics
   remain compatible; no wire command or hardware/power change is introduced.
6. Discovered app/emulator regressions first demonstrate escaping navigation on the
   original code, then cover nested folders, stale IDs/replies, reconnects, mode
   transitions, unavailable media and upload fallback. Physical phone acceptance is open.
