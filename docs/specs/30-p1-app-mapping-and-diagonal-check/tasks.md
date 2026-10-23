# Tasks: app mapping and a diagonal check (seed 30)

Run in an isolated branch/worktree. One task is one commit, including its checkbox; stage named paths only and inspect git show --stat. New regression tests are observed failing first. Existing unrelated preview failures caused by the owner's running emulator on port 8600 must be reported, not fixed by stopping it. No flash or phone installation in this run.

- [x] 1. Implement shared-core mapping transactions and the packaged diagonal diagnostic
  - Add the tracked JSON source, converter-based asset generator/check, embedded ODRG, protocol parser and durable mapping.part transaction.
  - Add diagnostic pause/resume, output generation and busy rules without runtime allocation; preserve old shows and mappings.
  - Start the seed as in_progress. Update command/mapping/core decisions and docs together with protocol changes; append resolution notes.
  - Verify: converter asset check, core suite and Python library suite by discovery. Prove new command/persistence/diagnostic tests fail first.
  - Requirements: 1.2, 1.4, 2.1-2.3, 3.1-3.5, 4.3.

- [x] 2. Apply complete live routing in firmware and emulator transports
  - Synchronize WLED's cached descriptors by physical pin and protect whole-refresh copying. Provide equivalent fallback output routing support.
  - Refresh emulator leg metadata and publish mapping changes for HTTP, serial and TCP; rebuild its Mapping view live. Add the basic odrigctl mapping forms alongside this transport integration.
  - Add transport, per-pin and output-adapter regressions, including restart and atomic updates.
  - Verify: emulator and firmware suites by discovery, plus core regressions. Prove stale cached-routing behavior fails first.
  - Requirements: 2.1, 2.4, 4.1-4.3.

- [ ] 3. Add the shared app mapping editor, diagonal controls and serial CLI
  - Implement protocol clients, one serialized request stream, target-change handling, revision conflicts, draft swap/save/cancel/defaults and test controls.
  - Use one responsive, accessible Mapping screen everywhere app/www runs. Include readable failure and off-state messages.
  - Verify odrigctl mapping forms end to end and add browser/protocol/CLI regressions.
  - Verify: app and emulator suites by discovery; run new UI tests against the emulator. Prove missing editor/commands fail first.
  - Requirements: 1.1-1.3, 2.4-2.5, 3.6, 4.1.

- [ ] 4. Complete no-board verification, build artifacts and document the handoff
  - Update app/emulator/firmware docs and additions/prerequisites; document commands, limitations, actual verification and deferred owner checks.
  - Run all suites that work locally; diagnose any new failures. Build both firmware variants and a fresh APK with the repository tools; run the APK suite against that exact APK.
  - Prepare an ignored local copy of the owner's full animation show for emulator testing, avoiding user files and the live emulator.
  - Verify spec coverage and source/asset parity. Record artifact hashes and test evidence. Leave seed in_progress pending task 5.
  - Requirements: 4.3-4.5 and all automated acceptance checks.

- [ ] 5. Owner verifies mapping and diagonal on the real installation
  - Deferred: the owner explicitly requested no flashing yet. Requires an approved later flash and a phone connected to the twenty-snake installation.
  - Observe a wrong assignment, correct it from the APK, save, see the continuous diagonal, restart, then stop the test and check normal playback.
  - Record what was actually seen and left on the board. Only then mark the seed completed.
  - Requirements: 4.5.
