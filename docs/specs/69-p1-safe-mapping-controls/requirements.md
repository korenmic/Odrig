# Requirements

1. The app exposes no Snake10 cross-wiring control/API. The core rejects the retired
   `mapping cross` forms without storage/output changes and omits `cross` from
   `mapping get`. CLI help/current docs expose no retired operation.
2. Generic valid mapping files still load. Pin edits preserve each installed snake's
   columns and strip starts, including an older saved nonalternating arrangement;
   no special Snake10 transform or implicit geometry migration is performed.
3. A visible Settings button reports whether mapping editing is locked. It starts
   locked. Toggling either direction requires an explicit "Are you sure?" confirmation;
   cancel/Escape preserve the previous state. The dialog is keyboard accessible.
4. While locked or confirmation is open, pointer/held-row/keyboard pin changes,
   Restore defaults and photo Apply/Other reading are disabled and their handlers
   refuse writes. Mapping reads, photo preview/analysis and diagnostics remain usable.
5. Leaving Settings, hiding the document or changing target relocks, cancels any
   pending prompt/drag and drops unsent queued moves. A prompt cannot unlock another
   target. Already-sent work is reconciled, without falsely claiming its cancellation.
6. Existing atomic saves, pin revisions, conflict/error handling and resource bounds
   remain intact. Tests observe regressions fail before repair, then pass discovered
   suites. The focused branch is integrated into current master through one PR.
7. No physical board operation or phone/LED acceptance is claimed.
