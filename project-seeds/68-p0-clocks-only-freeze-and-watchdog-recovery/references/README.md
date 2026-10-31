# Scheduler candidate evidence

[evidence.json](evidence.json) contains fresh results for both original and repaired
production task bodies, each with immediate-consumer and queued-notification cases.
`longest` is the maximum modeled uninterrupted work in milliseconds; `ticks` counts
blocking scheduler ticks. Every case renders200 virtual frames of32 ms each.

[reproduce-scheduler.py](reproduce-scheduler.py) reads the exact production function
and existing portable fixture from the recorded Git revisions, compiles with the
repository's host compiler checks and executes the four cases. Run it from the root
of an owned checkout with those revisions available and its host compiler set up.
Temporary programs and output JSON remain under ignored `build/`.

Original cases:6400 ms, zero blocking ticks. Candidate cases:32 ms,200 blocking
ticks. This confirms scheduler starvation and the candidate's effect in the model.
It does not reproduce an actual ESP32 restart, Wi-Fi loss, phone stall or the exact
trigger of the owner's incident. Existing native-core runs did not hang.

No board is opened or flashed and no runtime source is edited by replaying this
evidence. The actual existing repair lives in317eca0/PR39 and should be reused.
