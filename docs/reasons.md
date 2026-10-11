# Reasons

When the tool refuses an input it writes one line to standard error,

```
error: <reason>: <detail>
```

and exits with status 1. The reason is a fixed name made of lower-case letters, digits and
hyphens; every implementation that reads the same files uses the same names. The detail is
free text for people and names the file concerned.

When a file has more than one defect, the reason is that of the defect met first when the
file is read from front to back.

## Any input

| Reason | Condition |
|---|---|
| `not-found` | An input path given on the command line does not exist or cannot be read, and no more specific reason applies. |

## JSON frames files

Rules: [format.md](format.md), "JSON frames". `version` is checked before any other member,
so a file of another version is always `bad-version`.

| Reason | Condition |
|---|---|
| `bad-json` | The file is not UTF-8, starts with a byte-order mark, is not one JSON value, uses a member name twice in one object, or its top level is not an object. |
| `missing-member` | A member that the format lists is absent, at the top level or in a frame. |
| `bad-type` | A member, or an entry of `pixels`, is not of the listed type. An integer is a JSON number written without a fraction and without an exponent; `true` and `false` are not integers. |
| `bad-version` | `version` is not 1. |
| `unknown-member` | A member that the format does not list is present, at the top level or in a frame. |
| `out-of-range` | `width` or `height` is below 1, `ms` is below 1, or a colour is below 0 or above 16,777,215. |
| `no-frames` | `frames` is empty. |
| `bad-pixel-count` | A frame's `pixels` does not have exactly W * H entries. |

The checks run in this order: the top level, `version`, the other top-level members (a
missing one before an unknown one), `width`, `height`, `frames`, then each frame in order:
its members, `ms`, the number of pixels, and each pixel in order.

## Any output

| Reason | Condition |
|---|---|
| `cannot-write` | An output file or folder cannot be written, for example because its folder does not exist. |
