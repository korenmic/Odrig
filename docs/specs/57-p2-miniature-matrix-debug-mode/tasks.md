# Miniature matrix debug mode — tasks

- [x] 1. Add shared miniature state, acknowledged commands and logical projection.
  Implement startup-only fixed storage, opt-in public host helpers, revision-safe
  acknowledgement/failure/retry, status and approved command syntax. Build the
  letterboxed10x6 core frame from raw logical RGB/palette/widget layers at the cap,
  preserving normal leg output and clearing blank/off frames. Extend the Python
  declarations and test reference status as needed for the public contract. Verify
  independent projection vectors, mapping permutations, boot/control/failure,
  brightness/off and memory bounds. Run discovered core and emulator suites.

- [x] 2. Integrate safe firmware output transitions and emulator miniature preview.
  Switch only between normal cached legs and oneGPIO1/60LED source, clear outgoing
  buses, wait without the core lock, check setup before ack, retain current limits
  and dark output on failure. Test the host transition controller using stand-ins,
  including transfers, failures and retry/restoration. Emulator acknowledges using
  the same core helpers and sends/draws its core-generated miniature event without
  changing normal recording geometry. Run discovered core/emulator suites and
  relevant host-output stand-in suites; firmware compilation is deferred.

- [x] 3. Add acknowledged miniature controls to the shared operators' app.
  Settings checkbox, wiring explanation and global active indication use target
  status. Cover pending/refusal/timeout/readback, unsupported firmware, target
  changes, reconnect and changes from another client without saved local state.
  Run discovered app and emulator suites with browser/emulator integration.

- [ ] 4. Document exact approved miniature wiring and record integrated verification.
  Add the essential root README pin table, source-derived orientation, safe
  transitions/reboot and electrical acceptance boundaries. Update core, commands,
  mapping, app, emulator and firmware docs; append design resolutions to drifts.
  Run all suites supported on this computer plus deterministic emulator projection
  smoke. Record results and limitations without claiming a firmware build or
  physical proof. Final APK follows all four software seeds.

- [ ] 5. Verify miniature electrical readiness, board pixels and phone behavior with the owner.
  Later approved session: actual part and DIN threshold,5V/USB paths and current
  budget under startup/failure/load, assembly, powered corners/axes, internal/SD
  frame/text/widget playback, transition clearing, responsive USB/Wi-Fi controls,
 20–50FPS and phone acknowledgement/reconnect. Leave unchecked until observed.

Self-review: tasks1–4 cover every software/documentation requirement in order;
task5 retains all human acceptance. No existing fault is alleged by this feature;
if implementation uncovers a fault, demonstrate its regression failing first and
record that failure in the corresponding proof commit. One task per proof commit.
