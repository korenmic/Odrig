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

## Any output

| Reason | Condition |
|---|---|
| `cannot-write` | An output file or folder cannot be written, for example because its folder does not exist. |
