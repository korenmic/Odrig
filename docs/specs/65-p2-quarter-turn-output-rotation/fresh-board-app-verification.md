# Rotation Settings configuration verification

The initial browser discovery ran 10 cases and recorded 3 expected failures: missing
mapping, malformed show and unconfirmed canvas replies were all described as an
unsupported feature. The Settings feedback now shows the configuration reason and
refresh guidance only when the target itself reports `supported:false`. A confirmed
legacy command refusal clears an older capability reply, so its latest answer is not
hidden by a stale configuration diagnosis.

The additional refusal regression failed before that correction. Its 11-case red run
also recorded an incidental failure in the existing queued-cancellation timing case;
the complete final focused run passed all 11 cases in 24.754 seconds, including that
cancellation check. An earlier full app run was stopped when this final correction
was added; it is not counted as successful verification.

The final complete discovered app suite ran 457 cases with one worker,
run `20261102-121106-149884`. It recorded one unrelated existing order-case startup
timeout:
the browser remained on Target/Checking and did not reach Animations within 8 seconds.
The complete discovered order scope then passed all 12 cases without a source change.
The original
full run is qualified, not relabeled clean. All 11 rotation cases passed in the full
run. The JSON retains exact counts, outcomes, the original failure and evidence hashes.

The browser also drives the actual native shared core against an empty store and a
square mapping with a malformed show. In both cases status remains in recovery with
a real installation error while the rotation dropdown is enabled, 90 degrees saves,
the persistent bytes are exactly `1 90\n`, and reopening the app confirms 90 degrees.
No stand-in supplies those rotation or status replies. Existing all-four-angle,
reconnect, lost-reply, target-change, cancellation and genuine legacy compatibility
checks remain green. No shared client guard, command or protocol changed.

This is host/browser evidence. Installed Android VM, final firmware model and artifact
publication belong to delivery task 6. Physical radio, flash, wall and real-phone
acceptance remain with the operator.
