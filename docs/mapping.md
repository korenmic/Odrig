# Mapping

How canvas coordinates correspond to physical LEDs: which data pin each LED hangs on, and
where it sits along that pin's chain.

The mapping itself lives in the files under [`mapping/`](../mapping/). The player reads the
installed mapping file when it starts, on the board and in the emulator alike, and nothing
else defines the layout. The drawings and tables on this page are generated from those files.

## Coordinates

- The canvas is a grid of LEDs, 60 columns wide.
- Coordinates are written (x, y) and start at 1. (1,1) is the bottom-left LED, x grows to
  the right and y grows upward.
- LEDs along a leg are numbered from 1, starting at the end that is wired to the board. The
  firmware counts the same LEDs from 0, so its index is the number here minus 1.

## Legs and pins

A leg is one data pin of the board together with three 60-LED rows wired to it as one chain
of 180 LEDs. Leg N uses the pin labelled N on the board. Legs are not chained to each other.

The board seen from above, antenna at the top:

```
                      +-----------------+
                      |     antenna     |
             3V3  o---|                 |---o  GND
             3V3  o---|                 |---o  TX
             RST  o---|                 |---o  RX
   leg 4  --   4  o---|                 |---o  1   --  leg 1
   leg 5  --   5  o---|    ESP32-S3     |---o  2   --  leg 2
   leg 6  --   6  o---|     N16R8       |---o  42
   leg 7  --   7  o---|                 |---o  41
              15  o---|                 |---o  40
              16  o---|                 |---o  39
              17  o---|                 |---o  38
              18  o---|                 |---o  37
   leg 8  --   8  o---|                 |---o  36
   leg 3  --   3  o---|                 |---o  35
              46  o---|                 |---o  0
   leg 9  --   9  o---|                 |---o  45
   leg 10 --  10  o---|                 |---o  48
              11  o---|                 |---o  47
              12  o---|                 |---o  21
              13  o---|                 |---o  20
              14  o---|                 |---o  19
            5Vin  o---|                 |---o  GND
             GND  o---|  [USB]   [USB]  |---o  GND
                      +-----------------+
```

Within a leg the chain is a snake. It starts at the right end of the leg's top row and runs
to the left, continues on the middle row from left to right, and finishes on the bottom row
from right to left. Leg 1 holds the top three rows of the canvas and each following leg holds
the three rows below the previous one.

## Mapping file

One JSON file describes one physical build:

```json
{
  "version": 1,
  "width": 60,
  "legs": [
    {"leg": 1, "pin": 1, "first_led": "right", "rows": [6, 5, 4]},
    {"leg": 2, "pin": 2, "first_led": "right", "rows": [3, 2, 1]}
  ]
}
```

| Field | Meaning |
|---|---|
| `version` | Format version of the mapping file. This is version 1. |
| `width` | Number of LEDs in every row. |
| `legs` | One entry per leg. |
| `leg` | The leg's number. |
| `pin` | The data pin (GPIO number) the leg is wired to. |
| `first_led` | The side of the leg's first row where its first LED sits: `"left"` or `"right"`. |
| `rows` | The canvas row (y) of each of the leg's rows, in chain order. |

The canvas width W is the file's `width`. The canvas height H is the total number of rows in
the file. Every y from 1 to H appears exactly once.

### Rules

A mapping file is valid when all of these hold:

- It is read as strictly as a JSON frames file (see [format.md](format.md)): UTF-8 without a
  byte-order mark, exactly one JSON value, no member named twice in one object, and integers
  written without a fraction and without an exponent.
- The top level is an object with exactly the members `version`, `width` and `legs`.
- `version` is 1, and `width` is an integer from 1 to 65,535.
- `legs` is an array of one or more objects, each with exactly the members `leg`, `pin`,
  `first_led` and `rows`.
- Every `leg` is an integer from 1 to 255, and no two legs have the same number.
- Every `pin` is an integer from 0 to 255, and no two legs have the same pin.
- Every `first_led` is `"left"` or `"right"`.
- Every `rows` is an array of one or more integers. A leg may have any number of rows, and
  the legs need not have the same number of rows.
- The rows of all legs together hold every y from 1 to H exactly once.
- W * H is at most 65,534, the largest canvas an ODRG file can have.

A file that breaks a rule is not used: the tools refuse it as `mapping-malformed`, and a
missing file as `mapping-missing` (see [reasons.md](reasons.md)).

### Where each LED is

A leg whose `rows` has R entries has W * R LEDs. For LED number n (1 to W * R) on that leg:

- r = (n - 1) div W is the position of its row in `rows` (0 to R - 1), and
  i = (n - 1) mod W is how far along that row it is.
- y = `rows[r]`.
- The row starts on the `first_led` side when r is even and on the opposite side when r is
  odd.
- x = W - i when the row starts on the right, and x = 1 + i when it starts on the
  left.

In the two files below W is 60 and every leg has three rows, so each leg has 180 LEDs.

## Today's build: 2 legs, 60 x 6

File: [`mapping/legs-2.json`](../mapping/legs-2.json). The numbers at the two ends of each
row are the LED numbers at x=1 and x=60, and the arrow points the way the numbers increase.

```
       x=1                                            x=60
y=6   |  60 <-------------------------------------------   1 |  leg 1, pin 1
y=5   |  61 -------------------------------------------> 120 |
y=4   | 180 <------------------------------------------- 121 |
y=3   |  60 <-------------------------------------------   1 |  leg 2, pin 2
y=2   |  61 -------------------------------------------> 120 |
y=1   | 180 <------------------------------------------- 121 |
```

| Leg | Pin | Rows (y) | LED 1 | LED 60 | LED 61 | LED 120 | LED 121 | LED 180 |
|---:|---:|---|---|---|---|---|---|---|
| 1 | 1 | 6, 5, 4 | (60,6) | (1,6) | (1,5) | (60,5) | (60,4) | (1,4) |
| 2 | 2 | 3, 2, 1 | (60,3) | (1,3) | (1,2) | (60,2) | (60,1) | (1,1) |

## Target build: 10 legs, 60 x 30

File: [`mapping/legs-10.json`](../mapping/legs-10.json).

```
       x=1                                            x=60
y=30  |  60 <-------------------------------------------   1 |  leg 1, pin 1
y=29  |  61 -------------------------------------------> 120 |
y=28  | 180 <------------------------------------------- 121 |
y=27  |  60 <-------------------------------------------   1 |  leg 2, pin 2
y=26  |  61 -------------------------------------------> 120 |
y=25  | 180 <------------------------------------------- 121 |
y=24  |  60 <-------------------------------------------   1 |  leg 3, pin 3
y=23  |  61 -------------------------------------------> 120 |
y=22  | 180 <------------------------------------------- 121 |
y=21  |  60 <-------------------------------------------   1 |  leg 4, pin 4
y=20  |  61 -------------------------------------------> 120 |
y=19  | 180 <------------------------------------------- 121 |
y=18  |  60 <-------------------------------------------   1 |  leg 5, pin 5
y=17  |  61 -------------------------------------------> 120 |
y=16  | 180 <------------------------------------------- 121 |
y=15  |  60 <-------------------------------------------   1 |  leg 6, pin 6
y=14  |  61 -------------------------------------------> 120 |
y=13  | 180 <------------------------------------------- 121 |
y=12  |  60 <-------------------------------------------   1 |  leg 7, pin 7
y=11  |  61 -------------------------------------------> 120 |
y=10  | 180 <------------------------------------------- 121 |
y=9   |  60 <-------------------------------------------   1 |  leg 8, pin 8
y=8   |  61 -------------------------------------------> 120 |
y=7   | 180 <------------------------------------------- 121 |
y=6   |  60 <-------------------------------------------   1 |  leg 9, pin 9
y=5   |  61 -------------------------------------------> 120 |
y=4   | 180 <------------------------------------------- 121 |
y=3   |  60 <-------------------------------------------   1 |  leg 10, pin 10
y=2   |  61 -------------------------------------------> 120 |
y=1   | 180 <------------------------------------------- 121 |
```

| Leg | Pin | Rows (y) | LED 1 | LED 60 | LED 61 | LED 120 | LED 121 | LED 180 |
|---:|---:|---|---|---|---|---|---|---|
| 1 | 1 | 30, 29, 28 | (60,30) | (1,30) | (1,29) | (60,29) | (60,28) | (1,28) |
| 2 | 2 | 27, 26, 25 | (60,27) | (1,27) | (1,26) | (60,26) | (60,25) | (1,25) |
| 3 | 3 | 24, 23, 22 | (60,24) | (1,24) | (1,23) | (60,23) | (60,22) | (1,22) |
| 4 | 4 | 21, 20, 19 | (60,21) | (1,21) | (1,20) | (60,20) | (60,19) | (1,19) |
| 5 | 5 | 18, 17, 16 | (60,18) | (1,18) | (1,17) | (60,17) | (60,16) | (1,16) |
| 6 | 6 | 15, 14, 13 | (60,15) | (1,15) | (1,14) | (60,14) | (60,13) | (1,13) |
| 7 | 7 | 12, 11, 10 | (60,12) | (1,12) | (1,11) | (60,11) | (60,10) | (1,10) |
| 8 | 8 | 9, 8, 7 | (60,9) | (1,9) | (1,8) | (60,8) | (60,7) | (1,7) |
| 9 | 9 | 6, 5, 4 | (60,6) | (1,6) | (1,5) | (60,5) | (60,4) | (1,4) |
| 10 | 10 | 3, 2, 1 | (60,3) | (1,3) | (1,2) | (60,2) | (60,1) | (1,1) |

## What is confirmed

- Legs 1 and 2 are wired and confirmed on the hardware: an image drawn in canvas coordinates
  appears correctly across both.
- Legs 3 to 10 follow the same rule but are not wired or tested yet.
- Pin 3 is one of the chip's boot-mode pins. It is expected to work for LED data and has not
  been tested.
- The firmware supporting 10 outputs is read from WLED's source (up to 12 on the ESP32-S3)
  and has not been tested on the board.
