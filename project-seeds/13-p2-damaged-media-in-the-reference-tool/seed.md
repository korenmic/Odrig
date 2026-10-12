# Damaged media in the reference tool

## Summary

Make the Python reference tool refuse a damaged video or GIF with a named reason, where
today it crashes or ends in a traceback.

## Priority

- `P2`

## Depends On

- Seed 01, which wrote the Python tool and its `import`.
- Seed 06, whose work found the faults and whose JavaScript tool is the converter people use.

## Product Context

The Python tool is the reference that the test suites compare the JavaScript converter with.
People no longer use it to convert, but the suites run it, and anyone may still run it by
hand.

Three faults were found in its `import`:

- A video whose first stream has no decoder makes the Python process crash. On macOS this
  puts a "Python quit unexpectedly" dialog on the screen. A video file cut short at the wrong
  place is enough to cause it.
- A video with metadata that is not valid UTF-8 ends in a traceback.
- A GIF cut short ends in a traceback.

A crash is not a refusal. `docs/reasons.md` promises that every file the tools cannot use is
refused with a named reason.

The suites were changed to stop handing the Python tool such files. That hides the faults
and leaves them in place.

## Technical Constraints

- The fix is in the Python tool only. The JavaScript converter's behaviour does not change.
- No file may be decoded twice or more slowly for valid input because of the check.
- A test that reproduces a crash must not put a crash dialog on the screen of whoever runs
  the suite: the crashing case is run in a child process and its failure is observed there.
- Each test for one of these faults is shown failing before the fix.
- The reason names come from `docs/reasons.md`. A new name is added there only if none fits.

## Required Behavior

1. `import` of a video whose first stream has no decoder is refused with a named reason and a
   non-zero exit status, without crashing.
2. `import` of a video with metadata that is not valid UTF-8 either succeeds, when the
   picture can be decoded, or is refused with a named reason.
3. `import` of a GIF cut short is refused with a named reason.
4. For each of these inputs the JavaScript converter's answer is recorded beside the Python
   tool's, and where both refuse they give the same reason.
5. The suites again hand the Python tool these files.

## Definition Of Done

1. A test for each of the three faults fails before the fix and passes after it.
2. Running the whole converter suite on macOS produces no crash report.
3. `docs/reasons.md` and the reference tool's document describe the refusals.

## Open Questions

None. Use the resolved behavior in this seed.
