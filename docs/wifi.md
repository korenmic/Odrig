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

## What our board does today

The board has no network to join configured, so it hosts its own access point from power-on.
Asked for its state over USB on 2026-10-11, it reported its access point as up.

The access point still has WLED's default name and password.

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

- The access point's own name and password. The default password is public knowledge, so the
  operators should choose their own before the event.
- How many phones can be connected at once. The limit is set by the firmware and has not been
  looked up or tested.
- Range on site, with the board in its enclosure.
