# Tasks

Each task is one proof commit with only its own checkbox ticked. A test for a fault is
seen failing first.

- [ ] 1. Read a compressed body as a stream, in two passes
  - `inflateStream()`, `odrg.records`, the two-pass maker; the converter's tests seen
    failing first, the count of steps changed after.
  - Requirements: 4.1–4.4.

- [ ] 2. Make the preview as the upload starts, and keep its place
  - `previews.js`'s queue, store `uploads` and places; `client.js`'s order; the uploads of
    every form and the batch; `previewSafe`; the form's note; the app's tests seen failing
    first.
  - Requirements: 1.1–1.6, 2.1–2.4, 3.1–3.4, 4.5, 5.1–5.2.

- [ ] 3. The documents and the measurement
  - `docs/android-app.md`, `docs/converter.md`, the check on a phone and
    `tests/app/test_docs.py`, `docs/drifts.md` with the times.
  - Requirements: 6.1.

- [ ] 4. Deliver
  - Every suite that runs here; the pull request; the APK built from the branch that joins
    every unmerged seed, and its place on the Drive in `verification.md`.
  - Requirements: 6.1.
