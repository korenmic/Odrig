# Verification

## Software

The tasks are the commits f716e067, c60165d6 of the branch `seed-83-display-tests-whenever-play`, pull
request #56. Every suite named by the tasks passed on Windows before each commit; the
suites of the joined branch, pull request #63, pass there too but for
`tests.app.test_message_source`, which needs Pillow and fails on `master` here alike.

## Build

The seed is built with every other unmerged seed in the branch `all-unmerged-seeds`, pull
request #63: the APK from its head f1170603 and the firmware images from its head 0c96de79,
whose core, firmware, emulator, command tool and Python library are those of f1170603
(`git diff --stat 0c96de79 f1170603` over those folders is empty). Built on Windows: each
image verified by `verify_build.py` for its module from a clean tree; the APK signed with
the persistent key, its signature and alignment verified.

| File on the Drive, `odrig archive/fused-0c96de7/` | Bytes | SHA-256 |
|---|---:|---|
| `odrig-fused-f117060.apk` | 19,142,090 | `935478ec4d9a53f8a0d10a9a94bb73251daf4e903e2e792cd9d5f3b1d2383bc2` |
| `odrig-fused-0c96de7-n16r8-installation.bin` | 1,895,280 | `f5b08070d00f1e30cb56e106ef36088a16d84583b9794355f5348b610a09ae39` |
| `odrig-fused-0c96de7-n8r2-spare.bin` | 1,892,752 | `2c8497de3b6f0029837f08662552a03f3de451d6e331109a6b91f98cdf1f3e8c` |

- APK: https://drive.google.com/file/d/1zypfYigiMuWileHUpJjsWSOxPpfROS9T/view
- The installation's image: https://drive.google.com/file/d/111UBFDT7BW9dFsGyP88Js2aWefVpVAu-/view
- The spare's image: https://drive.google.com/file/d/16fcw6QpxMyGDfuLZa_WU_wXqE13jFIn-/view

## The owner's check, open

- [ ] On the board: a display test, the diagonal and a snake, pressed while the board reads its animations after a start, and while an upload is open, starts at once, and the upload ends.
