# Design

## `target.js`

- `link()` gives the link in use, `"wifi"` or `"usb"`, kept as `odrig.link`; `setLink(kind)`
  keeps it. `usbPossible()` says whether the sender exists and has USB. `address()` stays
  the Wi-Fi address.
- `send(line, limit)` goes on `link()`: Wi-Fi as today; USB through `sendSerial`:
  1. `connect` once while the link is not open (the sender asks Android's permission);
  2. `read` with a wait of 0 until it gives nothing, the bytes dropped;
  3. `write` of the line and a line feed;
  4. `read` with waits of at most 250 ms until `replyIn(text)` finds a reply or the limit
     passes.
- `replyIn(text)` is pure: the whole lines of the text, `\r\n` or `\n`, each passed over
  unless it parses as a JSON object with a boolean `ok`; gives the first such object, or
  null with the rest still to be completed.
- Failures on USB carry the detail `USB serial`. The sender's refusal codes `no-usb` and
  `usb-refused` become Failures of those kinds; anything else is `no-answer`.
- `route()` on USB gives `{sender: true, usb: true}`.

## The sender, `TargetPlugin`

New plugin methods beside `send` and `route`:

| Method | Takes | Gives |
|---|---|---|
| `usb` | | `{host, device, permitted, open}` |
| `connect` | | resolves when open; refused `no-usb`, `usb-refused` or `no-answer` |
| `write` | `text` | resolves when written |
| `read` | `timeoutMs` | `{text}`, what arrived, empty after the wait |

The USB work runs on its own single thread, apart from the HTTP worker. `connect` finds the
device of vendor `0x303a` and product `0x1001`, asks `UsbManager.requestPermission` with a
broadcast of this package, opens it, claims the interface of class CDC data with its bulk
in and out endpoints, and sends to the communication interface `SET_LINE_CODING` (115,200,
8N1) and `SET_CONTROL_LINE_STATE` with 0. `read` takes bulk transfers of the in endpoint's
packet size into a buffer of 4,096 bytes until nothing more is there; `write` sends bulk
transfers of the out endpoint's packet size. A detach broadcast of the device closes it.

The manifest gains `<uses-feature android:name="android.hardware.usb.host"
android:required="false" />` and, on the activity, the intent filter of
`USB_DEVICE_ATTACHED` with `res/xml/usb_device.xml` naming `303a:1001`.

## The Target screen

`index.html`: a group `link-choice` of two radio buttons, `Wi-Fi` and `USB serial`, then the
Wi-Fi block (the address field and `connect-wifi`) and the USB block (`usb-state` and
`connect-usb`). `screens/target.js` shows one block by the link, keeps the choice with
`setLink`, calls `client.begin()` on a change and on each connect, and disables `USB serial`
with its reason when `usbPossible()` is false.

## Tests

- `tests/app/test_target.py` and a scenario: the switch, the single Wi-Fi button and the
  filled field, `USB serial` disabled in a browser.
- A scenario with a stand-in sender in the page (`window.Capacitor` made before the app
  loads) whose `write` passes the line to the emulator over HTTP and whose `read` gives the
  reply back in pieces with log lines around it: the app answers, plays and uploads over
  `USB serial`; a reply withheld is a lost reply; a missing device says `no-usb`.
- `tests/app/test_android.py`: the methods, the ids, the line coding and the modem line
  request, the manifest's feature and filter.
