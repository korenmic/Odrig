# Only upload and authoring verification

Observed before repair:

- The shared destination module selected internal root both when external storage was
  absent and when Internal was explicitly chosen in Only
  (`build/seed66-task2-destination-red.log`).
- A direct job bypassed the form and received an outside commit acknowledgement from
  the controlled peer. Another job begun Off also sent commit after Only became
  confirmed; no cancellation was sent. Root preflight
  accepted both current Only and an unobserved change by another controller
  (`seed66-task2-guards-red.log`).
- With valid text and absent-media protocol fixtures, authoring still enabled its
  internal save and ready upload left Internal enabled (`seed66-task2-ui-contract-red.log`).
  The earlier UI fixture setup failures are not fault evidence.

Only now retains External without fallback, disables Internal and unavailable
submission, and preserves the prepared location rather than silently moving a Root
draft. Preflight reads fresh policy through shared status acceptance. Shared jobs carry
storage identity and check their destination before transfer steps. A policy rejection
cancels an opened staging transaction, or ends locally before begin. Authoring preview
continues but its flat internal-root save waits for confirmed normal mode. Invisible
Root-name collision queries remain allowed. No wire command or firmware policy changes.

Verification on Windows:

- Twelve new focused checks passed (`build/seed66-task2-invariants.log`), covering
  missing storage, internal selection, direct jobs, policy-change races/cancellation,
  current preflight, frozen drafts, option availability and normal-mode restoration.
- The actual native player accepted a ready-made file into `clocks/ready.odrg` with
  byte-identical contents, no internal/root copy, and Only still selected. The same
  focused run verified that authoring preview remains usable and saving returns after Off.
- The preceding UI/ordinary-ready-upload run passed16 checks
  (`build/seed66-task2-ui-green.log`).
- Discovered run `20261101-031436-62632` executed app532, emulator682 and onboarding88
  (`build/seed66-task2-suites.log`,516seconds). Onboarding passed. App531 passed; one
  menu fixture sampled movement controls before their asynchronous order response.
  That assertion now explicitly waits for the order it tests, and its six-case storage
  class passed (`seed66-task2-storage-recheck.log`).
- Emulator had20 expected skips and one Windows10053 connection-abort error while
  rejecting unsupported HTTP methods. The unchanged affected HTTP module passed all18
  checks on isolated recheck (`seed66-task2-http-recheck.log`). The full run is retained
  as failed; these successful rechecks are recorded separately.
- No runtime source changed during the discovered run. The native core and its memory
  bounds are unchanged by this task. Final integrated suites and exact-head CI remain
  part of delivery.

The owner's physical phone/media acceptance remains open. Native and browser tests
do not establish behavior on that physical installation.
