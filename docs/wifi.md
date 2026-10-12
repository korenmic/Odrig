# Wi-Fi

What the board's Wi-Fi can do, what it does today, and who hosts the network that operators
connect to.

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

## Who hosts the network

**The board hosts. Phones and computers join it.**

- At the event there is no other network. The board is the one device that is always there.
- The board's address on its own network is fixed, so an app does not have to search for it.
- If a phone hosted instead, the board would have to be told that phone's network name and
  password, the installation would stop being controllable whenever that one phone left, and
  an app would have to find the board's address on the phone's network.

The board can also join an existing network while hosting its own, which is useful on a
workbench. It is not needed at the event.

## Not yet decided or verified

- That a phone or a computer joins the network with the password and reaches the board.
- Four phones connected at once. The limit was read in the source and has not been tried.
- Range on site, with the board in its enclosure.
