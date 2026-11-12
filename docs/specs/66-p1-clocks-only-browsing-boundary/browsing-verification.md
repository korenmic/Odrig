# Standalone browsing verification

The branch starts directly from master. Its runtime change is confined to the shared
Android/browser client and its Animations screen; core, firmware and command protocol
are unchanged. It imports no time/schedule, rotation, inventory fingerprint/cache,
rendering fairness, power callback or USB diagnostic implementation.

Before the navigation guard, seven of eight discovered boundary cases failed:
Back published root, direct calls published `other` and `clocks-other`, descendants
could back out beyond Clocks, missing Clocks published root content, and unknown or
disconnected policy allowed the escape. The visible Back button also remained available.
The unchanged Between-mode release case passed. The eight cases passed after the guard.
The reload fixture was corrected to import the new frame's client after reloading;
its failed intermediate run was not treated as a production regression.

A subsequent removed-folder regression observed the old folder ID remaining active
after a failed lookup. The boundary now publishes unresolved Clocks with no list request,
and a subsequent status can establish the folder again. This prevents the clamp from
turning master's root fallback into immediate stale-ID retries. It adds no inventory
retention or automatic ID remapping subsystem.

Fresh discovery covering all nine boundary cases passed after the unavailable-folder
guard. One intervening recheck attempted a GNU rebuild while an MSVC-built library
was loaded by the interim runner; Windows refused the link and preserved the running
DLL. That environment/import failure is not counted as a passing test. The successful
recheck explicitly reused the already-built unchanged core and aligned the compiler.

An interim full app/emulator run started before the final guard/test was added; it is
retained as interim evidence, not a final frozen-source claim. Task2 owns the final
frozen selected-suite verification after destination guards are implemented.
Final selected-suite results and delivery are recorded separately.
Physical phone navigation and media acceptance remain open.
