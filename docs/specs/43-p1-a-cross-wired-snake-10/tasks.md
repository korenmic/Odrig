# Tasks: a cross-wired snake 10

Requirements: [requirements.md](requirements.md). Design: [design.md](design.md).

- [x] 1. The member `starts` of the format, in the three readers. `docs/mapping.md`: rule
      6 and "Where each LED is" with the member, the vocabulary of the ends. The core's
      `read_leg` and `read_mapping` with `starts_far`; `odrig/mapping.py` with `starts`
      on `Leg` and in `position`; `emulator/web/layout.js` with `starts` in `read` and
      `startsLow`. Tests: `tests/core/test_mapping.py`, `tests/converter/test_mapping.py`,
      `tests/emulator/test_layout.py`: a leg with `starts` placed by it, a file without it
      as today, and the rejections: a wrong length, words of the other kind, a first word
      that is not `first_led`. `docs/python-library.md` and `docs/emulator.md` name it;
      `docs/drifts.md` records the vocabulary of the ends. Suites: core, converter's
      Python, emulator, onboarding.
- [x] 2. The bit on the installation: `mapping cross on|off`, `cross` in `mapping get`,
      `mapping_editable` with leg 10 crossed, `persist` with the bit, `place_leg_10`.
      Tests in `tests/mapping/test_core.py`: `cross` false on the target's file; `on`
      rewrites the file with leg 10 as `[28,30,29]` and `starts`, reports true, and the
      diagonal's and the snake test's pixels of leg 10 land by the crossed placement;
      `off` restores; the same bit again writes nothing; `mapping set` keeps the bit; the
      refusals; a power loss at every step of the save leaves a whole file; the bit kept
      across a restart. `docs/commands.md` and `docs/core.md`; `docs/drifts.md` records
      the snake test's meaning with the bit and the revision left to the pins. Suites:
      core, mapping, onboarding.
- [ ] 3. The checkbox in the app: `mappingCross` in `commands.js` and `client.js`, the
      label in `index.html`, `latest.cross`, the poll, the draw and the `change` handler
      in `screens/mapping.js`. Tests in `tests/mapping/test_app.py` with the mapping
      scenario: off by default, on after a tap with `Saved: snake 10 is cross-wired.` and
      the emulator reporting true, the box following a change made by another client, a
      refusal said with the box back, and the box disabled while the mapping is not
      editable. `docs/android-app.md`. Suites: app, mapping, onboarding.
- [ ] 4. The photo reading with the bit off: the wall generator's `crossed` option in
      `tests/app/page/scenarios/photo-analysis.js`, a case with position 10 crossed read
      with the position given the remaining snake, in `tests/app/test_photo.py`; the
      sentence in the photo's paragraph of `docs/android-app.md`. Suites: app, onboarding.
- [ ] 5. The firmware, the APK and every suite: `docs/decisions.md`'s dated line, the
      seed in AGENTS.md's list, every suite that runs on this computer, `fw.py build` and
      `app/app.py build`, both put with the artifacts on the share and on Drive, the
      connected board flashed through its COM socket and seen running with `cross` false,
      and the owner's checks of requirement 5.5 left open in words.
