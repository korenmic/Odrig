# Tasks

Each task is one commit on the branch `seed-75-upload-button-reason` from `master`,
with only its own checkbox ticked. Every test of a fault is seen failing before the
change, and the failure seen goes into the commit message. Code carries no history.

- [x] 1. The destination line speaks of the destination, and a failed request moves nothing
  - `app/www/upload-destination.js`: `absent()`, `synchronize()` moving nowhere on no
    reply, `reason()` with `Storage not known yet: the installation has not answered.`
    for no reply and the card sentence only for an absent card.
  - `app/www/client.js`: `failed()` leaves `state.space`; `begin()` and the
    `storage-error` refusal still forget it.
  - `tests/app/page/scenarios/ready-checks.js`: the five invariants of the design and
    the absent reply in `flat_root_explanation`, seen failing first; the new scenario
    `tests/app/page/scenarios/upload-lock.js` with its snapshots of the destination
    line, the storage select and the capacity line, and `tests/app/test_upload_lock.py`
    with the `space-silent` test of the destination facts, seen failing first.
  - Set the seed's state to `in_progress`. Run the app's suite.
  - Requirements: 2.1–2.3, 3.1–3.3, 4.2.

- [ ] 2. The reason under the button
  - `app/www/client.js`: the holder of the content lock, `setContentBusy(holder)`,
    `contentHolder()`; `app/www/screens/selection.js` and `storage.js` naming
    themselves.
  - `app/www/index.html`, `app/www/screens/storage.js`, `app/www/style.css` if needed:
    the line `upload-locked-reason`, `aria-describedby`, `lockReason()` in the order of
    requirement 1.2, shown while the button is on the screen and disabled.
  - `tests/app/test_upload_lock.py` and `upload-lock.js`: the `status-fails` test at
    320, 360 and 740 pixels with the look facts, the lock line of `space-silent`, the
    `deletion` test and the `preflight` test, each seen failing first; the emulator's
    Internal fallback test unchanged. Run the app's suite.
  - Requirements: 1.1–1.4, 4.1, 4.3, 5.1.

- [ ] 3. The documentation
  - `docs/android-app.md`: the paragraph of `Ready-made files and upload
    destinations`, step 24 of the check on a phone, the bullets of `What is verified`
    and `What is open`; `tests/app/test_docs.py` counting 25 steps and 27 `*Seen:*`,
    seen failing first against the changed page.
  - Run the app's suite, the converter's, the emulator's and the onboarding suite.
  - Requirements: 5.2, 5.3.

- [ ] 4. The pull request and the APK
  - Push the branch and open the pull request from `master`, its description naming
    the seed, the verdict and the owner's open check. Build the APK from the pushed
    head with the persistent key as the design says, verify signer, alignment and
    packaging, place it on the Drive under `odrig archive/seed-75/`, publish it as
    the assets of the pre-release `apk-seed-75-<short sha>`, and write
    `verification.md` with the link, the commit, the hashes and the checks; no secret
    printed or committed. Set the seed's state to `completed` and the `AGENTS.md` line
    of seed 75 to name the open pull request. Commit, push, read the CI, and notify
    the owner with the link.
  - Requirements: 5.4.

## Owner acceptance (not claimed by automated tasks)

On the phone with the spare board and no card: a ready-made file, `Internal storage`,
`Upload to the installation` enabled, and `Uploaded as animation <id> <file>. It plays
in the playlist.`; with the installation off, the line under the button says that it
does not answer, with the failure's kind. These remain open until the owner reports
them.
