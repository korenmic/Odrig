# microSD verification through the UART

On 2026-10-23 the owner connected both ESP32-S3 USB-C sockets to the Mac, leaving the
microSD wiring unchanged. Both interfaces were visible:

- Native USB: `/dev/cu.usbmodem1101`.
- Bridge UART: `/dev/cu.usbmodem5C831043631`.

All board access in this run used `odrigctl`, one program at a time. No firmware was
changed or flashed, no storage was installed or formatted, and no hardware or power
change was made by the agent. Brightness stayed at 32.

## Firmware

The prepared 4 MHz image remained unchanged, 1,765,808 bytes:

`fd089753d86c92d9cbfbb2e4823d49428e4b037213b656736636b9dd9a1950a5`

The local image's checksum was checked. Its profile remains SCK39, MISO40, MOSI41 and
CS42, with all twenty LED outputs preserved. The prior flash is recorded in
[the first board trial](board-trial.md).

## Card and list

An initial UART log observation produced no new `#log` lines. UART commands answered
normally, initially listing 43 validated external animations and reporting SD animation
60004 playing at 49 refreshes per second.

The full list was then compared repeatedly with the mounted source folder
`/Volumes/192.168.0.1/artifacts/odrig`:

| Observation | Samples | Observed span | External entries | Lost entries |
|---|---:|---:|---|---:|
| First watch | 108 | 598.5 s | 48 to 118 | 0 |
| Continued watch | 53 | 303.0 s | 118 to 122 | 0 |

The first watch ended only because its 600-second observation window expired. It did
not report a card failure or loss of entries. Validation continued on the unchanged
board during the next watch.

All 122 external filenames and byte sizes matched the source, totaling 16,475,328 bytes.
Their IDs were 60001 through 60122. Together with internal item 1,
`1000313581.odrg` (52,667 bytes), the board listed 123 items. In the continued watch,
all 122 remained present for 35.1 seconds across seven samples before playback tests.

The core lists an external item only after validating the complete file and its canvas.
This is stronger than directory enumeration but is not a byte-for-byte comparison of
card contents with the source. Both watches kept the internal animation playing while
validation proceeded; their refresh figures are not SD playback measurements.

## SD playback

The existing `play` command selected four representative external files. Status was
sampled about once a second and the entire animation list about every five seconds.
Each observation crossed a loop boundary without reaching its normal playlist turn.
All samples retained the selected ID, brightness 32 and a null show error; all 122
external entries remained listed.

| ID | File | Observation | Refreshes per second |
|---:|---|---:|---:|
| 60001 | `01-062cd029337681-5_crop.odrg` | 20.6 s | 50 |
| 60061 | `21-fx-183_crop.odrg` | 24.7 s | 48–50 |
| 60119 | `43-yt-784dsKVrdjQ_center60of256.odrg`, the largest file | 30.7 s | 26–48 |
| 60122 | `alphabet_hebrew.odrg`, the last file | 40.4 s | 46–50 |

The refresh range excludes the first two seconds after selection, when a status sample
can include the preceding animation. Every measured range is within the accepted 20–50.

`play all` was restored and reported internal animation 1. With no subsequent play
command, later status samples reported SD animation 60002 with `playing: "all"`,
46–47 refreshes per second and no error. The complete 123-item list remained available.
This demonstrates automatic inclusion of SD content after the installed show.

## Limits and handoff

Card identification, full-file validation of all 122 animations, representative SD
playback and automatic combined-playlist operation succeeded in the current two-USB
bench setup. The board was left playing that playlist at brightness 32.

No new firmware fix was needed in this run. This does not establish why the prior
single-connection trials dropped the card, or prove that adding the second cable was
the cause of improvement. One-cable and autonomous-power operation were not retested.
Wi-Fi, physical removal timing, all animations played end-to-end, and the owner's
visual checks of the actual LED canvas remain outside this verification.

Logs and check scripts are retained under the ignored `build/` directory:
`microsd-uart-initial.log`, `microsd-uart-board-check.log`,
`microsd-uart-board-check-continued.log`, `microsd-uart-playback-check.log` and
`microsd-uart-auto-playlist.log`.
