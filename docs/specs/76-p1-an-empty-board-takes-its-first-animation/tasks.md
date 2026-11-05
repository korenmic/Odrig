# Tasks

Each task is one commit on the branch `seed-76-empty-board-first-animation` from
`master`, with only its own checkbox ticked. Every test of a fault is seen failing
before the change, and the failure seen goes into the commit message. Code carries no
history.

- [x] 1. The built-in mapping
  - `core/mapping_data.py` and `core/src/mapping_data.h`, the bytes of
    `mapping/legs-20.json`; `core/src/asset.h`, the in-memory host, used by
    `decode_diagonal()` as before; `core/src/mapping.cpp` reading the built-in bytes
    when `mapping.json` is not there; `core.mapping_builtin` in `core_state.h`;
    `persist()` clearing it.
  - `tests/core/support.py`: the model's `_check()` takes the target file's legs when
    there is no mapping file. `tests/core/test_mapping.py`: `BuiltInMapping`, seen
    failing first; `tests/core/test_startup.py`, `test_status.py`, `test_json.py` and
    the others that read `mapping-missing` as the answer to a missing file, changed to
    the new rule; `tests/core/test_build.py` checking `mapping_data.py --check`.
  - Set the seed's state to `in_progress`. Run the core's suite.
  - Requirements: 1.1–1.4, 4.3, 7.1.

- [x] 2. The empty show, and the mapping file written with the first show file
  - `core/src/show.cpp`: `empty_show()` in place of `kShowMissing`; `show.h`'s comment.
    `core/src/mapping_control.cpp` and `.h`: `mapping_materialize()`;
    `core/src/content.cpp`: `content_write_show()` calling it first.
  - `tests/core/support.py`: the empty show, and the mapping file written before the
    show file. `tests/core/test_first_animation.py`, new, seen failing first;
    `tests/core/test_startup.py`, `test_status.py`, `test_mapping.py`, `test_json.py`
    and the others that read `show-missing` as the answer to a missing file, changed to
    the new rule, with the sequence of host calls of an empty file set.
  - Run the core's suite.
  - Requirements: 2.1–2.5, 3.1–3.4, 4.3, 7.1.

- [ ] 3. The emulator and the app's suite
  - `emulator/httpd.py`: the built-in mapping served when the folder has no mapping
    file. `tests/emulator/test_binding.py` and `test_events.py`: the empty folder's
    legs, no reason, the served mapping, seen failing first; `tests/emulator/test_docs.py`
    with the check list's new reason. `tests/app/test_upload.py`: the first upload into
    an empty installation, seen failing first.
  - Run the emulator's suite and the app's suite.
  - Requirements: 5.1, 5.2, 7.2.

- [ ] 4. The documentation
  - `docs/core.md`, `docs/reasons.md` with `tests/core/test_docs.py`, `docs/commands.md`,
    `docs/mapping.md`, `docs/emulator.md` with step 22 of its check list,
    `docs/android-app.md`, `agent/getting-started.md`, the change log of
    `docs/decisions.md`, and `docs/drifts.md`.
  - Run the core's documentation tests, the emulator's, the converter's, the app's and
    the onboarding suite.
  - Requirements: 4.1, 4.2, 5.3, 6.1–6.3.

- [ ] 5. The pull request and the firmware
  - Push the branch and open the pull request from `master`, its description naming
    the seed, the verdict and the owner's open check. Build the firmware from the
    pushed head on this computer, verify it, run the firmware's host suites, place the
    image with its hashes, its build record, its verification files and a README on the
    Drive under `odrig archive/seed-76/`, and write `verification.md` with the commit,
    the hashes, the checks and what stays open. Set the `AGENTS.md` line of seed 76 to
    name the open pull request; the state stays `in_progress`. Commit, push, read the
    CI, and notify the owner.
  - Requirements: 7.3, 7.4.

## Owner acceptance (not claimed by automated tasks)

On the phone with the spare board flashed with the firmware of this seed: `Choose a
ready-made animation`, `Internal storage`, `Upload to the installation`, `Uploaded as
animation 1 <file>. It plays in the playlist.`, and the animation on the LEDs. This
remains open until the owner reports it.
