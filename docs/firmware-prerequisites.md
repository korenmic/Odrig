# Firmware prerequisites

What the firmware on the board must do, as agreed with the owner: one line for each, with
where it comes from and how far it has come. Progress is measured against this list. A
line counts as done only when its proof says so.

The states:

- **Done**: built and shown, by the suites and, where it needs the board, on the board.
- **Done, owner's check open**: done as far as a program can show; a person's check is
  still open.
- **In part**: some of it is built; the line says what is missing.
- **Not done**: nothing of it is built yet.

Where a line comes from:

- **WLED**: stock WLED 16.0.1 gives it, with nothing of ours.
- **Seed NN**: the seed's spec in `docs/specs/` and the commits named, on `master` of
  `korenmic/Odrig`.
- **Owner**: the owner's decision or answer, in [decisions.md](decisions.md) or in a
  spec's requirements, with its date.

The list was first written on 2026-10-15.

## The prerequisites

| # | What the firmware must do | State | Where it comes from | Proof |
|---:|---|---|---|---|
| 1 | Run on the ESP32-S3-N16R8 board (16 MB flash, 8 MB PSRAM) as it was bought, with nothing soldered. | Done | Owner: [decisions.md](decisions.md), "Firmware"; no soldering: the owner's answer to seed 20 on 2026-10-14. | Every measurement in [firmware.md](firmware.md), "Verified on the board". |
| 2 | WLED is the base: it gives the LED output, the storage and the Wi-Fi, and its own web page stays reachable. | Done | Owner: [decisions.md](decisions.md), "Firmware" and "Scope and process". WLED. | Seed 04, tasks 2 and 3 (`9ebc4d2`, `acbbff4`): stock WLED built from source, flashed and restored; a usermod that owns the LEDs. |
| 3 | One output for each leg: twenty legs of three strips of 60 LEDs on pins 1 to 18, 21 and 47, a canvas of 60 x 60, 3,600 LEDs. The bench today has two legs, 60 x 6. | In part | Owner: [decisions.md](decisions.md), "Canvas and coordinates". Seed 05, with the patch `firmware/patches/010-sixteen-parallel-outputs.patch`: stock WLED drives twelve outputs on this chip. | Seed 05 (`8f51c56` to `66423a1`): every one of the twenty pins carries the signal on the board. LEDs have been seen lit on pin 1 only: the owner's checks 5 and 6 of [firmware.md](firmware.md) are open. |
| 4 | Play the project's own animation files, `.odrg`, which the converter makes on a phone or a computer. Nothing is converted on the board. | Done | Owner: [decisions.md](decisions.md), "Conversion" and "Animation formats". Seeds 01 (`3810281` to `f5cd947`), 02 (`1fcb3af` to `9843600`), 04 and 06 (`bd3f751` to `5eb055a`). | Seed 04, task 5 (`08e435c`): the core in the firmware reads and plays the installed files. The suites of the converter and the core. |
| 5 | The same player code runs on the board and in the emulator on a computer. | Done | Owner: [decisions.md](decisions.md), "Runtime architecture". Seeds 02, 03 (`edffa52` to `288e66f`) and 04. | Seed 04, task 5 (`08e435c`): the core compiles unchanged into the firmware, and the replies of a session on the board are those of the emulator. |
| 6 | 20 to 50 refreshes a second, for any content. | Done for what was measured | Owner: [decisions.md](decisions.md), "Firmware", 2026-10-12. | 50 a second for the demo show and 36 to 47 for a dense 60 x 60 clip, seed 05 (`7162b23`). Not measured yet while a file of a USB stick plays: seed 20, task 5. |
| 7 | Play at once after power-on, with no command: the playlist of every animation in turn, each about 30 seconds unless the show says otherwise, or the cycle the show starts with. | In part | The playlist: seed 16 (`15fc7ff` to `219fdab`). Playing at once: seed 14 (`0ee44f4` to `ede085a`). | On the board on 2026-10-14 (`bd8944c`): `status` answered 1.31 s after a restart with 9 MB installed, the playlist playing. Open: seed 14, task 6, the board's whole suite, and task 7. |
| 8 | Animations in the board's own storage, about 10 MB, 13.5 MB with seed 24, kept through a restart: installed from a computer, uploaded and removed by command. | Done, owner's check open | Seed 04, task 4 (`72d7849`): `install-show`. Seed 07 (`d03e9e8` to `4348fe6`): `space`, `list`, `remove`, `upload`. | Seed 07, task 7 (`e943542`): every command over USB on the board. Open: seed 07, task 9, the owner's check. |
| 9 | Animations from a USB stick: FAT32 or FAT16, folder `odrig`, `.odrg` files. They are added after the installed ones and taken up or dropped while the board runs. The stick is never written. | In part | Owner: the answers to seed 20 on 2026-10-14. Seed 20 (spec `aea2a9f`). | The core `2236065`, the emulator `f9548d2`, the app `661f412`; the firmware built and flashed on 2026-10-14, `972e7ed`. No stick has been seen on the board yet: through a hub the board's USB software sees nothing (WLED's information said `odrig drive: none`, 2026-10-15), and the board's own port gives a stick no power. Open: seed 20, tasks 4, 5 and 6; seeds 22 and 23. |
| 10 | A broken file never stops the show, and a power cut never leaves a half-changed show. | Done | Seeds 02, 07 (`ee1c365`), 14 and 20. | The core's suite: power cuts at every storage call, damaged files found while playing, a broken file of a stick left out. |
| 11 | The commands: `play <id>`, `play all`, `on`, `off`, `brightness`, `status`, `space`, `list`, `remove` and `upload`, the same on every route. A command is added only with the owner's yes. | Done | Owner: [decisions.md](decisions.md), "Commands". Seeds 02, 04 and 07. | [commands.md](commands.md); the core's suite; seed 07, task 7 (`e943542`) on the board. |
| 12 | Commands over USB and over the Wi-Fi (`POST /odrig`). | Done, changed on 2026-10-14 | USB on the chip's own port: seed 04, task 5 (`08e435c`). USB on the port of the serial chip: seed 09, task 11 (`5604710`). Wi-Fi: seed 04, task 7 (`d97434a`). | Both USB ports took commands until 2026-10-14. Since the firmware with the stick (`972e7ed`), the chip's own port is the stick's, and USB commands go through the serial chip's port only; see line 15 and seed 21. |
| 13 | The board's own Wi-Fi network: name `odrig`, a password, address 4.3.2.1, with WLED's page there, also while the show plays. | Done, owner's check open | The network, its address and WLED's page: WLED. The name and the password: seed 08 (`9b3aa34` to `0f01515`). WLED's page and its captive portal kept answering while the player runs: seed 04, task 7 (`d97434a`). | Seed 08, task 4 (`5b33041`) on the board. On 2026-10-15 the owner's phone, on that network, ran the app against the board. Open: seed 08, task 7, the owner's check. |
| 14 | The operators' Android app controls the board over its Wi-Fi: what plays, the list of animations with a stick's too, play one, the playlist from the start, on and off, the brightness. | Done, owner's check open | Owner: [decisions.md](decisions.md), "Scope and process". Seed 09 (`f39d3c0` to `5604710`); a stick's animations: seed 20, task 3 (`661f412`). | The APK, seed 09, task 7. On 2026-10-15 the owner's phone showed the board's state and list and played from it. Open: seed 09, task 9, the check on a phone. |
| 15 | Both USB-C ports power the board, and a computer can talk to the board on either. | Not done | Owner, 2026-10-15. | Since `972e7ed` the chip's own port is the stick's and no computer's: seed 21. Which port powers the board is the board's wiring, not the firmware's: on 2026-10-15 the owner saw the board start from one of its ports and not from the other. |
| 16 | A stick is read without soldering: through a powered hub, or through an adapter with a power socket. | Not done | Owner, 2026-10-14 and 2026-10-15. | A hub needs seed 22. An OTG adapter with a power socket and only one USB-A socket needs no new seed; it has not been tried: seed 20, task 4. |
| 17 | The limit of the LED current is a setting that the tool writes into the board's storage. | Done | Seed 15 (`940193e` to `33bb109`). | Seed 15, task 4 (`ac55a59`): the limiter on the board. |
| 18 | A second firmware without WLED, as a fallback for the event. | In part | Owner: seed 12. Seed 12 (`d1816d8` to `cbc96c2`). | Seed 12, tasks 1 to 5: a bare program on the board with the outputs, the storage and the port; the sources both firmwares share; the stored settings; the limiter; the outputs. Open: tasks 6 to 12. |

## Rules for work on the board

These are the owner's, in [AGENTS.md](../AGENTS.md) and the working rules. Every change of
the firmware keeps them.

- Nothing is soldered. The hardware and its power are the owner's.
- The brightness on the bench is 40 or less. One program uses the board at a time.
- The flash is never erased whole, and no eFuse is written.
- The firmware is built only as `python3 firmware/fw.py` builds it.
- The Wi-Fi password is kept in `firmware/wifi.json` and nowhere else.
- A new command needs the owner's yes.

## Seeds not finished

| Seed | What is open | The firmware |
|---|---|---|
| 04, firmware build with the player | Task 10, the owner's checks. | Yes |
| 07, content commands | Task 9, the owner's check. | Yes |
| 08, the board's Wi-Fi name and password | Task 7, the owner's check. | Yes |
| 09, the operators' app | Task 9, the check on a phone. | No: the app |
| 12, standalone firmware as a fallback | Tasks 6 to 12. | Yes |
| 14, playing at once at power-on | Task 6, the board's whole suite, which needs a computer on the chip's own port, and task 7, the documents and the state. | Yes |
| 17, converting and uploading in the app | Task 7, the owner's check on a phone. | No: the app |
| 18, one converter | Every task. | No: the converter |
| 19, previewing one animation | Task 3, the owner looks at one animation. | No: the emulator |
| 20, animations from a USB drive | Task 4, the trial with an adapter that gives the stick power; the rest of task 5, the rate and the board's tests with a stick; task 6, the owner's look. | Yes |

## Seeds not begun

The seeds the owner approved on 2026-10-15: 21 to 23 after a stick was not read on the
board, 24 after a show of 113 animations did not fit into the board's storage.
Their folders are in `project-seeds/`; none has a spec yet.

| Seed | What it will do | For line |
|---|---|---|
| 21, one USB port for a computer or a stick | The chip's own USB port is a computer's port when a computer is plugged into it as the board starts, and the stick's port otherwise. | 12, 15 |
| 22, a USB stick through a hub | The firmware's USB software moves to Espressif's newer software, which reads a stick through a hub. Not certain: as far as is known, WLED does not run on that software officially yet. | 9, 16 |
| 23, a USB log on the serial port | A log on the serial chip's port that stays in the firmware: what the board's USB port sees, a hub or a stick, and why a stick is not read. | 9 |
| 24, a bigger animation space without Wi-Fi updates | The storage grows from 10.35 MB to about 13.5 MB by taking the second firmware slot; the firmware is then updated over the USB cable only. | 8 |

Without a seed, an OTG adapter with a power socket and only one USB-A socket would let the
firmware as it is read a stick: the owner buys one, and seed 20's task 4 tries it.
