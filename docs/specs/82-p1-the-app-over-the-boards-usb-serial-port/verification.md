# Verification

## Software

Tasks 1 to 3 are the commits f66dc188, a5e228de and 208dc19 of the branch
`seed-82-app-over-usb-serial`, pull request #55.

- `tests/app/test_serial.py` drives the app on `USB serial` through a stand-in of the APK's
  sender that relays each line to the emulator over HTTP, with log lines before and after
  each reply and the reply in pieces: the app answers, lists and plays; a withheld reply is
  reported as `no-answer` with the words for the cable and the link comes back; without a
  device it says `no-usb` and writes nothing; the switch goes back to Wi-Fi.
- `tests/app/test_target.py`: one `Connect over Wi-Fi` button, the switch with `USB serial`
  disabled in a browser, and an emptied field taking `4.3.2.1`; the scenarios that pressed
  `Use` and `Board` press the new button.
- `tests/app/test_android.py`: the sender's methods, the ids `303a:1001`, the line coding,
  the one modem line request, the broadcast of this package, the detach, the manifest's
  feature and filter.
- The app suite, 452 tests, passed but for eleven tests of a first run that needed the
  converter's packages and the core's test host, which this worktree did not have yet, and
  one serial test while an APK build ran beside it; all twelve pass when run again. The
  onboarding suite passes.

## Build

Built on Windows from the pushed head 208dc19 with a clean tree, Gradle compiling the new
Java, signed with the persistent key, its signature and alignment verified.

| File on the Drive | Bytes | SHA-256 |
|---|---:|---|
| `odrig archive/seed-82/odrig-seed82-208dc19.apk` | 19,092,203 | `add50e8da7a3a53fb75e74b570d8957a775133336ff2b7c294719dfd2f4ccf8d` |

https://drive.google.com/file/d/18idBDGuibJ694-eRlULlp8iP3FGokkAZ/view

## The owner's check, open

- [ ] Step 24 of "The check on a phone" in `docs/android-app.md`: the phone on the board's
  USB port with a cable, `USB serial`, `Connect over USB` and Android's question allowed;
  `Answers`, the list and every action on the LEDs, the board not reset by the connection;
  unplugged and plugged again; back to Wi-Fi.
