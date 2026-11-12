# Requirements

This standalone extraction covers the owner's clocks-only recovery feature on
master. Stable inventory caching is a separate feature and is outside this PR.

1. An uncertain or malformed saved clock policy must not start root animations.
   Missing policy retains the established Off default only when absence is authoritative.
2. The core must retry uncertain saved policy through bounded independent reads and
   allow an explicit clock mode to atomically replace it. Message-only edits cannot
   infer an unreadable policy.
3. Automatic app recovery from missing/remapped folder IDs must keep a confirmed Only
   context within Clocks or show an unavailable Clocks location; it must not publish Root.
4. Repeated Only status must preserve valid descendants. Unknown mode metadata must not
   release the last confirmed Only context. Confirmed Off/Between or a target change does.
5. An unresolved Clocks ID must not be sent by Restart clocks. Settings, Target and mode
   exit remain available. Deliberate unrestricted browsing remains master's behavior.
6. No inventory fingerprint protocol, board identity, retained snapshot cache, scheduler,
   rotation, producer-fairness change, power callback or USB diagnostic feature is added.

Physical boot, playback, Wi-Fi and phone acceptance remain operator checks.
