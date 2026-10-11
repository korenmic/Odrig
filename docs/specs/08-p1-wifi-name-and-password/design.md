# Design: The board's Wi-Fi name and password (seed 08)

## Overview

The access point is WLED's. WLED keeps its name in `/cfg.json` and its password in
`/wsec.json`, two files of the file system in the board's storage, reads both at every
start and opens the access point with what it read. So the name and the password are set
by editing those two files, and the firmware tool of seed 04 already edits that file system
over USB to install a show.

This design adds:

- `firmware/wifi.json`, the tracked settings file with the name and the password;
- `firmware/fwtool/wifi.py`, which reads and checks a settings file and edits WLED's two
  files in a storage image;
- the command `set-wifi`, which applies the settings to the board the way `install-show`
  installs a show, and the command `install-firmware`, which flashes the firmware as
  `flash` does and then applies the settings;
- two members in the probe build's report, `ap_name` and `ap_auth`, read from the radio, so
  that a board test can see the network's name and protection over USB.

The firmware is not changed. `flash` and `restore-stock` are not changed. WLED's web
interface and every other setting of WLED stay as they are.

No password is written in this design. Examples show `<the operators' password>`.

Decisions taken where the seed left a point open are listed in `docs/drifts.md` under
"Seed 08".

## What this design relies on

Seed 04's code, as it is in the repository. A task that finds one of these different
records the difference in `docs/drifts.md` and follows the real code.

| From | Used here |
|---|---|
| `firmware/fwtool/cli.py` | `storage_of(port)`, which reads the partition table and gives esptool on the port, the storage region and a file holding storage as it is; `write_application()`; the body of `_install_show` that writes a new storage image; `main`, `report`, the parser. |
| `firmware/fwtool/storage.py` | `mount`, `files_in`, `geometry`, `runs`, `from_board`, `pending`, `keep`, `discard`, `kept_images`; the reasons `no-space`, `verify-failed`, `layout-mismatch`. |
| `firmware/fwtool/flasher.py` | `Flasher.write(..., data=True)`, `verify`, `restart`; the check of every address against the regions. |
| `firmware/fwtool/board.py` | `find`, `status`, `probe`, `WAIT_SECONDS`. |
| `firmware/fwtool/build.py` | `image_path("firmware")`, `checked_image`, `check_size`. |
| `odrig/strictjson.py` | `loads`, the strict JSON reader of seed 01. |
| `firmware/usermod/odrig_probe.cpp` | `report()`, which builds the answer to `#probe` and already has `ap`. |
| `tests/firmware/support.py` | `RecordedEsptool`, `no_board`, `untouched_board`, `storage_image`, `small_layout`, `run_main`, `reason_of`. |
| `tests/board/support.py` | `ensure`, `on_port`, `probe`, `storage_image`, `leave_the_board`. |

## WLED 16.0.1: what was read, what the board holds, and what is assumed

The first table was read in WLED's source at the tag `v16.0.1`, commit
`29b389df1c1aaec6ff53aea742d17063b985906c`, in the checkout the tool keeps in the work
folder; the lines of `wled00/cfg.cpp` about `ap` were also compared with
`https://raw.githubusercontent.com/wled/WLED/v16.0.1/wled00/cfg.cpp`. Facts about the
Arduino core were read in Tasmota's core 2.0.18, the package
`framework-arduinoespressif32` that WLED's build uses. Nothing was built, run or flashed.

### Read in the source

| # | Fact | Where |
|---|---|---|
| W1 | The name is `apSSID`, 33 bytes, empty at first. The password is `apPass`, 65 bytes, at first `WLED_AP_PASS`, which is `DEFAULT_AP_PASS`: `wled1234`. `WLED_AP_SSID` is `DEFAULT_AP_SSID`: `WLED-AP`. This build defines neither macro and not `WLED_AP_SSID_UNIQUE`. | `wled00/wled.h`, `wled00/const.h`, `platformio.ini`; `firmware/platformio_override.ini.in` of this repository |
| W2 | `WLED::setup()` mounts the file system, calls `WLED_SET_AP_SSID()`, which copies `WLED-AP` into `apSSID`, checks `/cfg.json` with `verifyConfig()`, and calls `deserializeConfigFromFS()`. A `/cfg.json` that is not valid JSON is replaced from `/bkp.cfg.json` (`restoreConfig()`), or renamed away (`resetConfig()`). | `wled00/wled.cpp`, `wled00/cfg.cpp`, `wled00/file.cpp` (`validateJsonFile`, `restoreFile`) |
| W3 | `deserializeConfigFromFS()` first calls `deserializeConfigSec()`, which reads `/wsec.json`, then reads `/cfg.json` and calls `deserializeConfig(root, true)`. A file that is not there changes nothing: `readObjectFromFile()` returns false and every value stays. | `wled00/cfg.cpp`, `wled00/file.cpp` |
| W4 | `deserializeConfig()` takes from the object `ap`: `ssid` into `apSSID`, at most 32 characters; `psk` into `apPass` when it is there, with the comment "normally not present due to security"; `chan`, 1 to 13, else 6; `hide`; `behav`. A member that is absent leaves its value. `pskl` is not read. A file without `hw.led.ins` gets WLED's default output and one without `hw.btn.ins` its default button, as a missing file does. | `wled00/cfg.cpp` |
| W5 | `serializeConfig()` writes `ap.ssid`, `ap.pskl`, which is `strlen(apPass)`, `ap.chan`, `ap.hide`, `ap.behav` and `ap.ip`. It never writes `ap.psk`. | `wled00/cfg.cpp` |
| W6 | `deserializeConfigSec()` takes from `/wsec.json`: `nw.ins[].psk`, `ap.psk` into `apPass`, at most 64 characters, `if.mqtt.psk`, `if.hue.key`, `pin`, `ota.pwd`, `ota.lock`, `ota.lock-wifi` and `ota.aota`. A member that is absent leaves its value. `serializeConfigSec()` writes all of them. `serializeConfigToFS()` writes `/wsec.json`, copies `/cfg.json` to `/bkp.cfg.json`, and writes `/cfg.json`. | `wled00/cfg.cpp`, `wled00/file.cpp` (`backupFile`) |
| W7 | WLED writes its settings files when a settings page is saved or `/json/cfg` is posted (`configNeedsWrite`), after its outputs were made again in `WLED::loop()` (`doInitBusses`), and at start only when a usermod's settings ask for it (`needsSave`, set from `UsermodManager::readFromConfig()` alone). The usermod of this project has no settings. | `wled00/wled.cpp`, `wled00/cfg.cpp`, `wled00/set.cpp` |
| W8 | `WLED::initAP(resetAP)` returns without opening anything when `apBehavior` is `AP_BEHAVIOR_BUTTON_ONLY` and `resetAP` is false. Otherwise it gives the board the address `4.3.2.1`, calls `WiFi.softAP(apSSID, apPass, apChannel, apHide)`, and sets `apActive`, whatever `softAP` returned. With `resetAP` it first puts WLED's default name and password into `apSSID` and `apPass`. | `wled00/wled.cpp` |
| W9 | When no network to join is configured (`isWiFiConfigured()` is false: one entry whose name is empty or `Your_Network`), `handleConnection()` waits 2 seconds after start and `initConnection()` then calls `initAP()` at once. With a network configured, `ap.behav` decides when `initAP()` is called: 0, the default, after 12 seconds without a connection since start; 1, after 12 seconds whenever there is no connection; 2, at once and always. In both cases 3 opens the access point only by the button (W8), and 4 closes it again five minutes after start when no device is joined then. | `wled00/wled.cpp`, `wled00/network.cpp`, `wled00/const.h` |
| W10 | `WiFiAPClass::softAP()` of the Arduino core refuses an empty name and a password of 1 to 7 characters. `wifi_softap_config()` copies at most 32 bytes of the name and sets `ssid_len`; with a password that is not empty it sets the protection to `WIFI_AUTH_WPA2_PSK` and copies at most 64 bytes, and with none it leaves `WIFI_AUTH_OPEN`. It allows 4 devices at once unless told otherwise, and WLED's call does not tell it. The configuration is given to the radio with `esp_wifi_set_config(WIFI_IF_AP, ...)`. | `libraries/WiFi/src/WiFiAP.cpp`, `WiFiAP.h` of the core |
| W11 | `esp_wifi_get_config(WIFI_IF_AP, &config)` gives the radio's access-point configuration: `config.ap.ssid`, 32 bytes, `ssid_len`, `authmode`, where `WIFI_AUTH_OPEN` is 0 and `WIFI_AUTH_WPA2_PSK` is 3, and `max_connection`. `wled.h` includes `esp_wifi.h` for the ESP32. The core's own `softAPSSID()` reads the name in this way. | `tools/sdk/esp32s3/include/esp_wifi/include/esp_wifi_types.h` of the core; `wled00/wled.h`; `WiFiAP.cpp` |
| W12 | `serializeInfo()`, the output of `/json/info`, reports `wifi.ap`, which is `apActive`, and nothing else about the access point: not its name. `GET /json/cfg` gives the output of `serializeConfig()`, with `ap.ssid` and `ap.pskl`. | `wled00/json.cpp` |
| W13 | A path the web server has no handler for goes through `handleStaticContent()` to `handleFileRead()`, which serves the file of that name from the file system and refuses every path that has `sec` in it. The handler of the file editor leaves `wsec.json` out of its list and answers 403 for it. So WLED serves `/cfg.json` to every device on the network and `/wsec.json` to none. | `wled00/wled_server.cpp` (`initServer`, `createEditHandler`), `wled00/file.cpp` |
| W14 | WLED's Wi-Fi settings page shows the name, and the password as asterisks. When the page is saved, `handleSettingsSet()` takes the name as it is, and takes the password when it is empty or has 8 characters or more and is not asterisks only. Both files are then written (W6). | `wled00/xml.cpp`, `wled00/set.cpp` |
| W15 | `handleButton()`: when button 0 is released after more than 5 seconds (`WLED_LONG_AP`), WLED calls `initAP(true)`: the access point has WLED's default name and password until the next restart, and a save of WLED's settings in that time stores them. After more than 10 seconds (`WLED_LONG_FACTORY_RESET`) WLED formats its file system and restarts. Button 0 is on pin 0 (`BTNPIN`) unless `/cfg.json` names buttons. | `wled00/button.cpp`, `wled00/wled.h`, `wled00/cfg.cpp` |
| W16 | After several crashes in a row at start, `handleBootLoop()` restores `/cfg.json` from `/bkp.cfg.json`, then renames it away, and can print the JSON files of the top folder to the port with `dumpFilesToSerial()`, which leaves out every file whose name begins with `wsec`. | `wled00/util.cpp`, `wled00/file.cpp` |
| W17 | `WLED::setup()` calls `WiFi.persistent(true)` on the ESP32, and the core switches the Wi-Fi driver's own storage to memory only when that is false. So the driver keeps the access point's configuration in the `nvs` partition as well. WLED sets the configuration again at every start (W8, W10). | `wled00/wled.cpp`; `libraries/WiFi/src/WiFiGeneric.cpp` of the core |

### What the board holds

Looked up, without writing anything, in the newest storage image that seed 04's work left in
the work folder on 2026-10-11:

| # | Observation |
|---|---|
| B1 | `/cfg.json` has 392 bytes and two members: `hw`, with the two LED outputs, the matrix and `fps`, and `def`. It has no `ap`, no `nw` and no `id`. The proof-of-concept deploy script writes the file in this form, with littlefs-python, and WLED has not saved its settings over it: a save writes every member (W5). |
| B2 | There is no `/wsec.json` and no `/bkp.cfg.json`. By W1 to W4 the access point therefore has the name `WLED-AP` and the password `wled1234`. |
| B3 | `/cfg.json` is JSON without spaces, and Python's `json.dumps` with the separators `,` and `:` gives its bytes back exactly. |
| B4 | In a copy held in memory, littlefs-python 0.19.0 added an `ap` object to `/cfg.json` and created `/wsec.json`: two blocks changed, blocks 0 and 1, and the disk version stayed 2.0. |

### Assumed, to be verified by an early task

| # | Assumption | Verified in |
|---|---|---|
| A1 | `esp_wifi_get_config(WIFI_IF_AP, ...)` compiles in the usermod with `wled.h` alone, can be called from the loop task, and after WLED opened its access point gives the name and the protection that access point has. Before the settings are applied it is expected to give `WLED-AP` and 3. | Task 2 |
| A2 | WLED on the board reads the `/cfg.json` to which the tool added `ap` and the `/wsec.json` the tool created, opens the access point under that name with that password, and is otherwise as before: the same outputs, the same show, the same replies. | Task 4 |
| A3 | WLED does not write its settings files at a start because of the edit (W7): storage read back after the restart is the image the tool wrote. | Task 4 |
| A4 | A file littlefs-python wrote into the top folder of the file system is read by WLED. Seed 04 showed this for files in `/odrig`, and the board's `/cfg.json` was written in this way by the proof-of-concept deploy script (B1). A `/wsec.json` made in this way is new. | Task 4 |
| A5 | A phone or a computer joins the network with the password and reaches `http://4.3.2.1/odrig`. No agent can join the board's network. | Task 7, the owner's check |

Read in the source and tried by no task, because no task presses a button, removes the
board's `/cfg.json` or brings five phones: that a `/cfg.json` holding only `ap` leaves
WLED as a missing one does (W3, W4); the button (W15); the limit of four devices (W10).
`docs/wifi.md` gives the last two as read, not as tried.

## Repository layout

New and changed files:

```
firmware/
  wifi.json                      new: the settings file
  fwtool/
    wifi.py                      new: a settings file read and checked; WLED's two files
                                 edited in a storage image
    cli.py                       changed: set-wifi, install-firmware; the writing of a
                                 storage image as one function, used by install-show too
    paths.py                     changed: WIFI_SETTINGS
  usermod/
    odrig_probe.cpp              changed: ap_name and ap_auth in the report
tests/
  firmware/
    test_wifi_settings.py        new
    test_wifi_storage.py         new
    test_wifi_commands.py        new
    test_wifi_docs.py            new
    support.py                   changed: files as WLED writes them when it saves
    test_cli.py, test_docs.py, test_usermod_files.py      changed
  board/
    test_wifi.py                 new
    support.py                   changed
  air/
    test_wifi.py                 new
docs/
  wifi.md, firmware.md           changed
```

Nothing new is created in the work folder. The storage images it already keeps,
`build/firmware/storage/*.bin`, hold `/wsec.json` like the board does.

## The settings file

`firmware/wifi.json`:

```json
{
  "name": "odrig",
  "password": "<the operators' password>"
}
```

A UTF-8 JSON object with exactly the members `name` and `password`, each a string. It is
read with `odrig.strictjson.loads`, as `show.json` is: no byte-order mark, exactly one JSON
value, no member named twice. `.gitattributes` already keeps git from changing the line
ends of `*.json`.

The file is the only tracked file that holds the password. The name is also written in the
documents, which describe the network, and in one test, which checks that the file names
`odrig`; no source of the tool holds either value.

Where the password is, besides the file:

| Place | Tracked | Written by |
|---|---|---|
| `/wsec.json` in the board's storage | no | `set-wifi`, `install-firmware`; WLED when it saves its settings (W6) |
| The storage images of `build/firmware/storage/`, the newest eight | no: git ignores `/build/` | the tool, as copies of the board's storage |
| The `nvs` partition of the board | no | the chip's Wi-Fi driver (W17); no tool of this repository reads or writes it |
| The history of this repository | yes | every password that was ever committed stays in earlier commits |

## The tool

```
python3 firmware/fw.py set-wifi [--port P] [--settings FILE] [--wait SECONDS]
python3 firmware/fw.py install-firmware [--port P] [--settings FILE] [--wait SECONDS]
```

`--port P` is the port, chosen as for every command of the tool. `--settings FILE` names
another settings file than `firmware/wifi.json`. `--wait SECONDS` is the time the command
waits for the board's reply after a restart, 20 seconds without it.

New reasons, beside those of seed 04:

| Reason | Condition |
|---|---|
| `wifi-settings-missing` | The settings file to read is not there or is not a file. |
| `wifi-settings-malformed` | It is not a JSON object with exactly the strings `name` and `password`. |
| `wifi-name-invalid` | The name does not have 1 to 32 characters of printable ASCII. |
| `wifi-password-invalid` | The password does not have 8 to 63 characters of printable ASCII. |
| `wled-settings-malformed` | `/cfg.json` or `/wsec.json` in the board's storage is not a JSON object, or its `ap` is not an object. Nothing was written to the board. |

### Reading and checking a settings file (`wifi.py`)

```python
class Settings:
    """A name and a password. Its text form does not show the password."""
    name: str
    password: str

def read(path=paths.WIFI_SETTINGS) -> Settings: ...
def apply(image: bytes, settings: Settings) -> bytes: ...
def holds(image: bytes, settings: Settings) -> bool: ...
def name_in(image: bytes) -> str | None: ...
```

`read`:

1. The path is not a file: `wifi-settings-missing`.
2. `strictjson.loads` of its bytes. A rejection is `wifi-settings-malformed`, with the
   line and column for a fault of the JSON text.
3. The value is not an object, lacks `name` or `password`, has another member, or one of
   the two is not a string: `wifi-settings-malformed`.
4. The name: 1 to 32 characters, each from U+0020 to U+007E, else `wifi-name-invalid`.
5. The password: 8 to 63 characters, each from U+0020 to U+007E, else
   `wifi-password-invalid`.

The limits are those of WPA2 and of a network name, and both fit WLED's fields (W1, W4,
W6, W10). By the rules of WPA2, 64 characters are a key written in hexadecimal, not a
password.
With printable ASCII a character is a byte, so the count the seed gives in characters is
the count the radio makes in bytes. The values are taken as they are in the file: nothing
is trimmed.

No detail of these refusals quotes text from the file. A refused length is given as a
number: `the password has 7 characters; a Wi-Fi password has 8 to 63`. `Settings` defines
`__repr__`, and with it `__str__`, as `Settings(name='odrig', password=<hidden>)`.

Every command reads and checks its settings file before `board.find()` and before any
esptool call.

### Editing WLED's stored settings (`wifi.apply`)

Given a storage image and the settings, `apply` returns the image with the two files
changed, checked, or the image itself when nothing has to change.

1. Mount the image with `storage.mount`, which keeps the disk version the file system has.
2. Read `/cfg.json` and `/wsec.json`. A file that is absent counts as the empty object.
   Each is parsed with Python's `json.loads`, which keeps the order of the members. A file
   that is not valid JSON or not an object, or whose `ap` is there and is not an object, is
   `wled-settings-malformed`.
3. In `/cfg.json`: `ap.ssid` becomes the name, `ap.pskl` the number of characters of the
   password, and `ap.psk` is removed when it is there. In `/wsec.json`: `ap.psk` becomes
   the password. An `ap` object that is missing is added as the last member of its file.
4. A file whose content, so changed, equals what was parsed is left alone: its bytes stay.
   Any other is written with `json.dumps(value, separators=(",", ":"),
   ensure_ascii=False)` in UTF-8, the form WLED itself writes (B3). Every member the tool
   does not set keeps its value and its place. A number keeps its value; an integer keeps
   its text, and a number with a fraction is written in the shortest form that reads back
   as the same number.
5. When neither file changed, the image is returned as it is.
6. Unmount. An error of the file system with the code for no room left is `no-space`; any
   other is `verify-failed`.
7. Check the new image before returning it, each failure being `verify-failed` with the
   file's name and no value:
   - the disk version, the block size and the number of blocks are those of the old image;
   - every file other than `/cfg.json` and `/wsec.json` has the bytes it had;
   - `holds(new, settings)` is true;
   - for each of the two files, what the new one parses to, without `ap.ssid`, `ap.pskl`
     and `ap.psk`, equals what the old one parsed to without them, the order of the
     members included; an `ap` left empty by this counts as absent.

`holds` is true when `/cfg.json` is an object whose `ap.ssid` is the name and whose
`ap.pskl` is the password's length and which has no `ap.psk`, and `/wsec.json` is an object
whose `ap.psk` is the password. `name_in` gives `ap.ssid` of `/cfg.json`, or `None`.

Why these members:

- `ap.ssid` and `ap.psk` are what WLED reads (W4, W6).
- `ap.pskl` is not read by WLED (W4). It is set so that `/cfg.json` is what WLED itself
  would write for this password (W5), and stays that when WLED saves next.
- `ap.psk` must not be in `/cfg.json`: WLED would take it in place of the password of
  `/wsec.json` (W3, W4), WLED serves `/cfg.json` to every device on the network (W13), and
  can print it to the port (W16).
- `ap.chan`, `ap.hide`, `ap.behav` and `nw` are WLED's other Wi-Fi settings. They are left
  alone, also where they are absent, as on this board (B1): WLED then uses its defaults.

On the board as it is today (B1, B2), the edit adds `"ap":{"ssid":"odrig","pskl":N}` to the
end of `/cfg.json`, N being the password's length, and creates `/wsec.json` with one
member, `ap`, that holds `psk` only. Such a `/wsec.json` leaves every other secret of WLED
at its default (W6): no settings PIN, no OTA password.

`/bkp.cfg.json` is WLED's own copy of `/cfg.json` from before its last save (W6). The tool
does not edit it. This board has none (B2).

### Writing a storage image (`cli.py`)

The steps with which `install-show` puts a new storage image on the board become one
function, `write_storage(on_port, region, before, after)`, with the code `_install_show`
has today from `storage.pending` to `storage.keep` and its handling of a failure:

1. Keep the new image in the work folder under a name that is not yet a kept image.
2. `storage.runs`: the blocks that differ, neighbouring ones joined.
3. One `write-flash` call for all runs, as data, with every address checked against the
   storage region. With no run there is no call.
4. `verify-flash` of the whole partition against the new image, and restart.
5. `storage.keep`: the new image is now the newest kept image.
6. On a failure: discard the new image, restart the board, pass the failure on.

`install-show` calls this function and behaves as before.

### `set-wifi`

1. `wifi.read(--settings or firmware/wifi.json)`.
2. `board.find(--port)`.
3. `storage_of(port)`: the partition table is read and checked, and the tool gets storage
   as it is: the newest kept image when the chip confirms its checksum, else the whole
   partition, read into the work folder. The chip stays in its bootloader.
4. `wifi.apply(before, settings)`. A failure here restarts the board and is reported;
   nothing was written.
5. `write_storage(on_port, region, before, after)`.
6. `board.status(port, --wait)`: the reply to `status`, or `no-reply`.
7. Print `name: <name>`, `password: set` and the reply. Status 0.

On a board that already holds the settings, step 4 returns the image it was given, step 5
finds no run and writes nothing, the partition is compared once more, and the board
restarts. The command is expected to take about as long as `install-show` of a small show,
36 seconds, and the wait; task 4 records the time.

The reply to `status` shows that the firmware runs again. `set-wifi` does not look into it:
an invalid show is `install-show`'s matter. On a board that runs something that answers no
`status`, stock WLED for one, the command ends with `no-reply` after the settings were
stored and checked.

### `install-firmware`

1. `wifi.read(--settings or firmware/wifi.json)`.
2. `build.checked_image(build.image_path("firmware"))` and `build.check_size`.
3. `board.find(--port)`.
4. `write_application(port, image, expect="status", wait=--wait)`: what `flash` does. The
   board starts the firmware and answers `status`; by then WLED has mounted its file
   system, or made one where there was none (seed 04's fact R24).
5. Steps 3 to 7 of `set-wifi`.

Steps 1 and 2 need no board. When one of them fails, nothing was written.

`flash` is not given this step. Requirement 4 of the seed 04 requirements says that `flash`
writes the first application partition only and leaves storage as it was, and the board
suite relies on it. `install-firmware` is the command for a board from scratch;
`docs/firmware.md` puts it in place of `flash` in "From nothing to a playing board":

```
python3 firmware/fw.py build
python3 firmware/fw.py install-firmware
python -m odrig pack --show shows/example/show.json --mapping mapping/legs-2.json \
    --sources animations --out build/example-show
python3 firmware/fw.py install-show build/example-show
```

A board that only ever got `flash` keeps whatever name and password its storage gives it:
WLED's defaults, when nothing was set.

### Keeping the password out of sight

- The password enters the tool in one place, `wifi.read`, and leaves it in one place, the
  bytes of `/wsec.json` inside a storage image.
- `Settings` hides it in its text form. No message, no detail of a `Failure` and no
  assertion is built from it.
- On success the tool prints `password: set`: not the value and not its length. Only the
  refusal of a length names a number.
- esptool is given paths and addresses. Its output, of which the tool passes on the last
  400 characters when it fails, holds no content of a file.
- The tool writes no log file. The pieces of an image that it writes into the work folder
  for one `write-flash` call are removed after the call, as today.
- No command has an option for a name or a password, so neither can land in a shell
  history or in the list of running programs.

## The probe build's report

`report()` of `firmware/usermod/odrig_probe.cpp` gets two members after `ap`:

```cpp
wifi_config_t radio;
const bool known = apActive && esp_wifi_get_config(WIFI_IF_AP, &radio) == ESP_OK;
line += F(",\"ap_name\":");      // the name as a JSON string, or null
line += F(",\"ap_auth\":");      // radio.ap.authmode as a number, or null
```

```json
{"probe":1, ..., "ap":1,"ap_name":"odrig","ap_auth":3,"error":null, ...}
```

| Member | Meaning |
|---|---|
| `ap_name` | The name in the configuration the radio holds for its access point: the first `ssid_len` bytes of `ssid`, or up to the first zero byte when `ssid_len` is 0. `null` while `ap` is 0. |
| `ap_auth` | The protection in that configuration, as the chip numbers it: 0 open, 3 WPA2 with a password. `null` while `ap` is 0. |

A byte of the name outside printable ASCII, a quotation mark and a backslash are written as
`\u00XX`, so the line stays valid JSON whatever name somebody set in WLED's own page.

Both are `null` while `ap` is 0, because the radio keeps the configuration of the start
before (W17) until WLED opens the access point again (W8): only with `ap` 1 does the
configuration belong to this start.

The call reads and changes nothing. It is in the probe file, inside `#ifdef ODRIG_PROBE`,
like the rest of the report: the firmware has none of it. No other source of the usermod
names a Wi-Fi function, and none sets a Wi-Fi setting.

## How a program establishes the network over USB

| What | How |
|---|---|
| The network is up | `ap` is 1: WLED has opened its access point (W8). |
| Under the new name | `ap_name` is the name: what the radio was given (W10), read from the radio itself (W11), not from WLED's variable. |
| A password is set | `ap_auth` is 3: the core sets WPA2 only for a password that is not empty (W10). |
| It is the password of the settings file | Storage is read back from the board: `wifi.holds(image, settings)` is true. WLED gives the radio `ap.psk` of `/wsec.json` (W6, W8). |
| WLED left the files alone | The image read back equals the image the tool wrote (A3). |

`ap` alone would not do: WLED sets it whatever `softAP` returned (W8).

What no program on this Mac establishes: that a device can join with the password. That is
the owner's check.

The firmware answers none of this on its port. Its port carries the commands of
`docs/commands.md`, and a command is added only with the owner's approval. So the check
uses the probe build, as seed 04's check of `ap` does, and the board suite puts the
firmware back at its end. The settings are in storage, which no flash changes: what the
probe build reports is what the firmware hosts.

## What is left as it is

| Left as it is | Consequence |
|---|---|
| The firmware and the usermod outside the probe code | The firmware is compiled from the same code as before this seed. |
| `flash`, `restore-stock`, `install-show`, `read-show` | Storage is written by `install-show`, `set-wifi` and `install-firmware` only. The name and the password stay through `flash` and `restore-stock`; stock WLED, restored, hosts the same network. |
| WLED's channel, hidden name, opening behaviour and networks to join | With a network to join configured, or the behaviour "never", WLED opens the access point later or not at all (W8, W9). The tool does not change that. |
| WLED's web interface and its Wi-Fi settings page | Whoever has joined the network can change the name and the password there (W14). The settings file then no longer says what the board has; `set-wifi` puts its values back. |
| WLED's button | Button 0 held for more than 5 seconds brings back the default name and password until the next restart, and for good when WLED's settings are saved in that time; more than 10 seconds formats the file system, the show included (W15). `set-wifi` and `install-show` put both back. |
| `/bkp.cfg.json` | When WLED restores it (W2, W16), the name is the one of the backup; the password stays, because it is in `/wsec.json`. `set-wifi` puts the name back. |
| `status` and `docs/commands.md` | No command is added. |

## Error handling

- A settings file that is refused stops the command before the board is touched.
- `wled-settings-malformed`, `no-space` and `verify-failed` from `wifi.apply` come before
  the first write: the board's storage is as it was, and the board is restarted.
- A failure while writing or comparing: the new image is discarded, the board is restarted,
  the failure is reported. The copy of storage from before is in the work folder. Running
  the command again writes what still differs.
- `no-reply` after a successful write: the settings are stored; the firmware did not answer
  in time. A show that takes long to check needs `--wait`.
- `install-firmware` that fails after flashing leaves the firmware on the board with the
  name and password its storage had. Running it again, or `set-wifi`, finishes the work.
- An edit that left `/cfg.json` broken would make WLED restore or rename it (W2). The check
  of step 7 of `wifi.apply` reads both files back before anything is written.

## Testing strategy

Three suites, as seed 04 has them, each found by discovery:

```
python3 firmware/fw.py test
python3 firmware/fw.py test-board
python3 firmware/fw.py test-air --http ADDRESS
```

Passwords in tests are texts made for the test. In `tests/firmware/` they are fixed and
plainly no secret; in `tests/board/` the one that is not the settings file's is made at run
time. A test never asserts on a password with a method that prints both sides: it asserts
on `wifi.holds(...)` or on the result of `==`.

### `tests/firmware/`: no board

| File | What it proves |
|---|---|
| `test_wifi_settings.py` | Names of 1 and 32 characters and passwords of 8 and 63 are accepted; an empty name and one of 33 are `wifi-name-invalid`; passwords of 7 and 64 are `wifi-password-invalid`; a tab, a letter outside ASCII and a zero character in either are refused with that value's reason; a missing file is `wifi-settings-missing`; a file that is not UTF-8, begins with a byte-order mark, holds two values, names a member twice, is an array, lacks a member, has a third member, or has a number for a value is `wifi-settings-malformed`. Each refusal, through `set-wifi --settings` and through `install-firmware --settings`, has status 1 and one error line and happens inside `support.untouched_board()`. The settings file itself is accepted, names `odrig`, and its password is not `wled1234`. No other file that `git ls-files` lists holds the password's bytes; a failure names the file only. `repr` and `str` of `Settings` do not hold the password. |
| `test_wifi_storage.py` | On images made with `support.storage_image`. With the files of B1 and B2: afterwards `/cfg.json` is the old object with `ap` added last, holding `ssid` and `pskl` only, and `/wsec.json` holds `ap.psk` only. With files as WLED writes them when it saves: only `ap.ssid`, `ap.pskl` and `ap.psk` differ, and `ap.chan`, `ap.hide`, `ap.behav`, `nw`, `ota` and the order of all members are as before. An `ap.psk` in `/cfg.json` is gone afterwards. Without `/cfg.json` the file is created with `ap` only. Numbers with a fraction and text outside ASCII in other members read back equal. Every other file has its bytes; the disk version, also 2.1, and the size stay. Applying the same settings again returns the same image and no run. Applying other settings and then the first gives the first. The runs of changed blocks, applied to the old image, give the new one. A `/cfg.json` that is an array, an `ap` that is a number and a `/wsec.json` that is not JSON are `wled-settings-malformed`. A file system with no room is `no-space`. `holds` and `name_in` answer for each of these images. |
| `test_wifi_commands.py` | With the stand-in for esptool on a small layout. `set-wifi` reads the partition table and storage, makes one `write-flash` call with `--force` whose addresses are all inside storage, compares the partition, erases nothing, and prints the three lines; its status is 0 also when the reply has an `error`. Run again on what was written, it makes no `write-flash` call. `--wait` reaches the wait for the reply. A reply that does not come is `no-reply`; a comparison that fails is `verify-failed`, the board is restarted and no new image is kept. `install-firmware` erases the boot selection, writes the image at `0x10000` without `--force`, and then does what `set-wifi` does, in that order; with a refused settings file or without an image it makes no call at all. `flash` still makes no call that reads or writes storage. Neither command has an option other than `--port`, `--settings` and `--wait`. With a password found nowhere else: it is in no line of standard output or standard error of any of these runs, in no argument of any esptool call, and in no file of the test's work folder other than a storage image. |
| `test_wifi_docs.py` | `docs/wifi.md` names the network `odrig`, the settings file, `set-wifi` and `install-firmware`, the limits, the address `4.3.2.1`, the owner's check as numbered steps with what must be seen, and no longer says that the access point has WLED's defaults or that its name and password are undecided. It does not hold the password. |
| `test_docs.py`, `test_cli.py`, `test_usermod_files.py` (changed) | The set of commands has `set-wifi` and `install-firmware`, each with a section, an example and every option in `docs/firmware.md`; an unknown option of either is a usage error; `esp_wifi_` appears in the usermod only as `esp_wifi_get_config` and only in `odrig_probe.cpp`, and the test that the usermod names no Wi-Fi function of WLED passes unchanged. |

### `tests/board/`: the board on USB

| File | What it proves |
|---|---|
| `test_wifi.py` | Probe build. (1) With a settings file made in the test, whose name begins with `odrig-test` and whose password is made with `secrets`: `set-wifi --settings` ends with status 0 and three lines; within 30 seconds the report has `ap` 1, `ap_name` that name, `ap_auth` 3; storage read back holds those settings. (2) Then `set-wifi` with the settings file: the same with the name `odrig`, and the image read back is the image the tool kept. (3) Between the storage from before (1) and after (2): every file other than `/cfg.json` and `/wsec.json` has its bytes, and `/cfg.json` differs in `ap` only; `status` reports the show playing as before. (4) `install-firmware`: status 0, the firmware answers `status`, and storage read back holds the settings of the settings file. |
| `support.py` (changed) | A helper runs `install-firmware` and remembers that the board then runs the firmware, as `flash()` does. `leave_the_board()` also applies the settings file when the board's storage does not hold its settings. |

A run that is stopped between (1) and (2) leaves the board with the test name and a
password nobody has. The board is still reached over USB, and `python3 firmware/fw.py
set-wifi` puts the settings file's values back.

### `tests/air/`: this Mac on the board's network

| File | What it proves |
|---|---|
| `test_wifi.py` | `GET /json/cfg` has `ap.ssid` equal to the name of the settings file and `ap.pskl` equal to the length of its password; `GET /cfg.json` is served and its `ap` has no `psk`; `GET /wsec.json` is not answered with 200. |

No agent runs this suite. It is written, and run by the owner, who joins the network.

### Who checks what

| Item of the definition of done | Checked by |
|---|---|
| 1. A password of 7 and of 64 characters and a name of 33 are refused | `tests/firmware/test_wifi_settings.py` |
| 2. The board reports its network up under `odrig`; stored settings read back show the name and that a password is set | `tests/board/test_wifi.py` |
| 3. Joining with the password and one command over HTTP | The owner |

## Documentation

`docs/wifi.md` after this seed. The sections on what the chip can do, what WLED adds and
who hosts the network stay.

| Section | Says |
|---|---|
| The board's network | The name `odrig`; WPA2 with the password of `firmware/wifi.json`; that this file is the only place in the repository with the password and that whoever reads the repository can read it; the address `4.3.2.1`; that WLED opens the network about two seconds after the firmware has started when no network to join is configured, and what a configured network or the setting "never" change; four devices at once, as read in the source. It replaces "What our board does today". |
| Changing the name or the password | Edit `firmware/wifi.json`; run `python3 firmware/fw.py set-wifi` with each board on USB; commit the file; give every phone the new password. The limits. A new board: `install-firmware`. |
| What else changes them | WLED's Wi-Fi settings page; the button; that `flash` and `restore-stock` keep them; that the work folder's storage images hold the password too. |
| The owner's check | Numbered steps, each with what must be seen. |
| Not yet verified | Four devices at once, read and not tried; range on site. It replaces "Not yet decided or verified", without the item on the name and the password. |

`docs/firmware.md`: the two commands in the list of commands, each with a section, an
example and its options; the five reasons; `install-firmware` in "From nothing to a playing
board"; `set-wifi` and `install-firmware` beside `install-show` in the table of regions;
`ap_name` and `ap_auth` in the table of the probe build's report; one sentence under
"Wi-Fi is WLED's" that names the settings file and `docs/wifi.md`; in the owner's checks of
seed 04, the network's name where the text says "the board's Wi-Fi network".

`docs/decisions.md` already states the name and that the password may be kept in the
repository. `docs/android-app.md` still asks whether the network should have a password; it
is the page of seed 09 and is not edited here.

## Risks

1. **WLED and files the tool wrote into the top folder** (A2, A4). The edit was tried in
   memory only (B4). Task 4 is the first time the board starts on it; the copy of storage
   from before is in the work folder.
2. **The password is as public as the repository**, and stays in its history after a
   change. The owner allows it. A board keeps an old password until `set-wifi` is run on
   it.
3. **WLED's interface stays open to everyone who joined.** A person on the network can
   read `/cfg.json`, change the name and the password, or change when the access point
   opens (W13, W14). The owner wants the interface left as it is for now.
4. **The button** (W15). Five seconds on button 0 give WLED's public password back until
   the next restart; ten seconds remove the settings and the show until `set-wifi` and
   `install-show` are run again.
5. **Four devices** (W10). A fifth phone is not let in. Nothing here changes the limit.
6. **A board left with the test name** when a board run is stopped half way; see above.
7. **The air test is not run by an agent**, like the air tests of seed 04.
8. **The board suite takes longer**: two runs of `set-wifi`, one of `install-firmware` and
   three readings of storage, about five minutes.
