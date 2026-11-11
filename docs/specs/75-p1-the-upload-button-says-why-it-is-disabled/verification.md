# Verification

Seed 75 on the branch `seed-75-upload-button-reason`, pull request #48 of
`korenmic/Odrig` from `master` at b3e8e64. The commits: 955632b the spec, 4c55518 task 1,
58bc19a task 2, f5ad253 task 3; the APK was built from f5ad253 with nothing changed in
`app/`, and the last commit adds this record. Everything below ran on Windows 11 on
2026-11-04.

## The suites, by task

- Task 1: the app's suite through the runner, 447 tests with 26 workers, 440 passed. The
  seven others: the disconnect test of the counts, which followed the old rule of seed 56
  and was changed to this seed's; five conversions and uploads that needed
  `npm ci --prefix converter` in this checkout; one emulator port collision. After the
  `npm ci`, those sixteen tests and the whole counts module passed alone. The new
  invariants of `ready-checks` and the stand-in test of a silent `space` were seen failing
  before the change.
- Task 2: the app's suite, 450 tests, 449 passed; the one failure, the refusals of an
  upload, waited eight seconds for a first reply under load and passed alone. The four
  new stand-in tests were seen failing before the change, each waiting for the line that
  did not exist.
- Task 3: the app's suite, 450 tests, 449 passed, the one failure a layout timing with
  the keyboard open under load, passing alone; the emulator's suite, 657 tests, 19
  skipped; the converter's own suite, 1601 passed and 1 skipped; the onboarding suite,
  88. The docs test was seen failing on the step count before it was changed.
- Task 4: the APK suite, 8 tests, with `ODRIG_TOOLS` pointing at a scratch folder that
  holds `aapt2` under the name the suite looks for, since the SDK on Windows names it
  `aapt2.exe`.

## The APK

`build/app/odrig-debug.apk`, 19,083,943 bytes, SHA-256
`a7271ea4600d021dcd408b0b8425e70b48a22ec5e37e7be51cf63ae3b3aa07b1`, from commit
`f5ad253305f82661d7778a9bde0a8783d92758ee`, the note in it `{"commit": …, "changed":
false}`.

Built as the earlier Windows deliveries were, nothing installed in the system:
`npm ci --prefix app` with Capacitor 8.5.3; the staged web code through
`app.apptool.stage.staged()`; `capacitor sync android`; the Gradle 8.14.3 wrapper without
its daemon with a build-local user home, the JDK 21 of Android Studio and the Android
SDK already on the computer, build-tools 35.0.0 and platform 36, with the Gradle home and
the Android user folder copied from the earlier Windows delivery into
`scratch/seed75-tools/`; then `apksigner sign` with the persistent key
`C:\Users\koren\.codex\signing\odrig\odrig-debug.p12`, its password read from
`odrig-signing.json` into the environment of apksigner alone and never printed.
`apksigner verify --print-certs`: verifies, v2 and v3 schemes, certificate SHA-256
`5a489ec294e53cdec085d71092cf4e7285ae08d4d43c19929d84130f3649f0f1`, the one of the APK on
the Drive; the keystore's SHA-256 `b49e3f8b499571af7ae7281cfeb09eaa7fdb15cebc9a59397eced9e978318324`,
unchanged. `zipalign -c 4`: aligned. The steps and their times are in the Drive's
`odrig-seed75-f5ad253.build.json`: npm ci 4.3 s, sync 1.5 s, Gradle 27.5 s, signing
1.0 s, the two checks under a second each.

## On an Android emulator

The image `Medium_Phone_API_36.1` of Android Studio, x86_64, Android 16, API 36, started
without a window, without audio and without saving its snapshot:

1. The APK now on the Drive, built from edf96d8, installed and launched: `Status: ok`,
   `MainActivity` the resumed activity, the process alive after four seconds.
2. The seed 75 APK installed over it with `adb install -r`, the same key: `Success`,
   launched as above.
3. Uninstalled; the seed 75 APK installed clean: `Success`, launched as above.
4. No `FATAL` line of `AndroidRuntime` in logcat. Uninstalled, the emulator stopped.

## Where it is

- Google Drive, `Artifacts/odrig/odrig archive/seed-75/`: `odrig-seed75-f5ad253.apk`,
  its `.sha256`, read back as `a7271ea4…07b1`, its `.build.json` and a `README.txt`. The
  files above the folder, the earlier deliveries and the signing backups, are untouched.
- The GitHub pre-release was not published: the agent's run was refused the creation of
  a public release, and the record stays truthful rather than worked around. The owner
  publishes it with

  ```
  gh release create apk-seed-75-f5ad253 --repo korenmic/Odrig --target f5ad253305f82661d7778a9bde0a8783d92758ee --prerelease --title "APK of seed 75 (PR #48), built from f5ad253" --notes "The odrig app from PR #48, signed with the persistent key; SHA-256 a7271ea4600d021dcd408b0b8425e70b48a22ec5e37e7be51cf63ae3b3aa07b1." "G:\My Drive\Artifacts\odrig\odrig archive\seed-75\odrig-seed75-f5ad253.apk"
  ```

  after which the link is
  `https://github.com/korenmic/Odrig/releases/download/apk-seed-75-f5ad253/odrig-seed75-f5ad253.apk`.
  Until then the phone gets the file from the Drive folder above, in the Google Drive app.

## Open

- The owner's phone check, step 24 of the check on a phone in `docs/android-app.md`: with
  the spare board and no card, Internal, the button enabled and the upload acknowledged;
  with the installation off, the line under the button naming the failure.
- The pull request's checks, the firmware hosts on Ubuntu and on Windows, were pending
  when this record was written and are read after the push of this commit.
- The seed's state stays `in_progress` until the merge: `AGENTS.md` counts a seed as
  completed when its implementation is merged, and the onboarding suite keeps a
  completed seed out of `What is coming`, where seed 75's line names this pull request.
