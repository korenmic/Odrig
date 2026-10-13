# Wi-Fi

What the board's Wi-Fi can do, the network the board hosts, how its name and password are
changed, and who hosts the network that operators connect to.

## What the ESP32-S3 can do

| Capability | Supported | Source |
|---|---|---|
| Host its own Wi-Fi network (access point) | Yes | [Espressif Wi-Fi API](https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-reference/network/esp_wifi.html) |
| Join an existing network (station) | Yes | Same |
| Do both at the same time | Yes | Same |
| 2.4 GHz, 802.11 b/g/n | Yes | [Espressif ESP32-S3 product page](https://www.espressif.com/en/products/socs/esp32-s3) |
| 5 GHz | No | Same |

A phone hotspot the board is meant to join must therefore offer 2.4 GHz.

## What WLED adds

WLED, the base firmware, manages the Wi-Fi. Its settings include the access point's name,
password and channel, whether the name is hidden, and when the access point opens: when there
is no connection after start-up, whenever disconnected, always, or never. It can also hold
one or more networks to join. Source:
[WLED settings](https://kno.wled.ge/features/settings/).

## The board's network

The board hosts a Wi-Fi network named `odrig`. It is protected with WPA2, and its
password is the one in `firmware/wifi.json`. That file is the only place in this
repository that holds the password, and whoever can read the repository can read it. The
owner allows that.

On its own network the board has the address `4.3.2.1`. Commands go to
`http://4.3.2.1/odrig`; see [commands.md](commands.md).

The network is WLED's. WLED opens it about two seconds after the firmware has started,
because the board has no network to join configured. With a network to join configured in
WLED's settings, WLED opens it only when that network is not reached, twelve seconds after
the start; with WLED's setting "never", it opens it only by the board's button. The
firmware tool changes neither of the two.

Four devices can be joined at once. That is the limit of the chip's software as WLED
uses it, read in the source and not tried.

The name and the password are put on a board with `python3 firmware/fw.py set-wifi`; see
[firmware.md](firmware.md#set-wifi). On 2026-10-12 the bench board was asked over USB
after that command: it reported its access point as up under the name `odrig`, protected
with WPA2, and its storage held the name and the password of the settings file. That a
phone joins with the password is the owner's check and is open.

## Changing the name or the password

1. Edit `firmware/wifi.json`. A name has 1 to 32 characters and a password 8 to 63, all of
   them printable ASCII; the tool refuses anything else before it touches a board.
2. Run `python3 firmware/fw.py set-wifi` with every board on USB, one after the other. It
   takes 36 seconds for a board and prints the name, `password: set` and the board's
   reply to `status`.
3. Commit the file.
4. Give every phone the new password. A phone that had joined under the old one has to
   join again.

A board that never had the settings, a new one or one with stock WLED, gets them together
with the firmware: `python3 firmware/fw.py install-firmware`. Both commands are described
in [firmware.md](firmware.md#set-wifi).

A board keeps the name and the password it was given until `set-wifi` is run on it again:
changing the file changes no board.

## What else changes them

- **WLED's Wi-Fi settings page.** Whoever has joined the network can open WLED's
  interface at `http://4.3.2.1/` and change the name and the password there. The settings
  file then no longer says what the board has; `set-wifi` puts its values back. WLED also
  serves `/cfg.json`, which holds the name and the length of the password, to every
  device on the network, and `/wsec.json`, which holds the password, to none.
- **The button of the board.** Held for more than five seconds, button 0 makes WLED open
  its access point with WLED's default name and password until the next restart, and for
  good when WLED's settings are saved in that time. Held for more than ten seconds, it
  makes WLED format its storage: the settings and the show are gone. `set-wifi` puts the
  name and the password back, and `install-show` the show. This was read in the source
  and not tried.
- **WLED's own copy of its settings.** When WLED restores `/cfg.json` from the copy it
  keeps, the name is the one of that copy; the password stays. `set-wifi` puts the name
  back.
- **`flash` and `restore-stock` keep them.** Neither writes storage. Stock WLED, restored,
  hosts the same network.

Where the password is, besides the settings file: in `/wsec.json` in the board's storage;
in the copies of storage the tool keeps in `build/firmware/storage/`, the newest eight,
which git ignores; in the chip's own store for its radio; and in the history of this
repository, where every password that was ever committed stays. After a change, the old
password can also stay in blocks of the board's storage that hold no file any more.

## The owner's check

No program on this Mac can show that a device joins the network. A person does, once:

1. Power the board and open the list of Wi-Fi networks on a phone or a computer.
   Seen: `odrig` is there and `WLED-AP` is not.
2. Join `odrig`, first with WLED's old password, `wled1234`, then with the password of
   `firmware/wifi.json`. Seen: the first is refused and the second joins.
3. Send one command. With a computer: `python -m odrigctl --http 4.3.2.1 status`. With a
   phone: `POST http://4.3.2.1/odrig` with the body `status`. Seen: a reply with
   `"ok":true`.
4. With this Mac joined and the board on USB, run
   `python3 firmware/fw.py test-air --http 4.3.2.1`. Seen: the suite ends with `OK`.

## A phone on a network without internet

The board's network has no internet. A phone that joins it keeps its other traffic on
mobile data, and may say that the network has no internet or offer to sign in to it: WLED
answers every name with the board's own address while its access point is up. A request
an app sends in the ordinary way would leave through mobile data and not reach the board.
The operators' app therefore opens its requests on the Wi-Fi network itself;
[android-app.md](android-app.md#the-phone-and-the-installations-network) says how, and
what its target screen shows. Whether a phone stays on the network by itself, and what it
asks, is part of the owner's check of the app and is not known yet.

## Who hosts the network

**The board hosts. Phones and computers join it.**

- At the event there is no other network. The board is the one device that is always there.
- The board's address on its own network is fixed, so an app does not have to search for it.
- If a phone hosted instead, the board would have to be told that phone's network name and
  password, the installation would stop being controllable whenever that one phone left, and
  an app would have to find the board's address on the phone's network.

The board can also join an existing network while hosting its own, which is useful on a
workbench. It is not needed at the event.

## Not yet verified

- That a phone or a computer joins the network with the password and reaches the board:
  the owner's check above.
- Four phones connected at once. The limit was read in the source and has not been tried.
- What the button does, which was read in the source too.
- Range on site, with the board in its enclosure.
