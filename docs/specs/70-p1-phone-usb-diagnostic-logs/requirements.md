# Requirements

1. Target offers USB log capture independently of Wi-Fi. Android enumerates supported
   ports, obtains USB permission only after Start, and reads at 115200/8N1.
2. Starting capture sends no board commands and never initiates reset, bootloader,
   flashing, erase, time sync or configuration changes. RTS is cleared before DTR.
3. An explicit button sends only `status\nfault\n`; responses and raw serial output
   remain visible even if they do not parse as JSON. Empty capture is reported as waiting.
4. At most 1 MiB is retained; capture stops visibly at the limit without losing its
   beginning. Rendering uses only a bounded tail. Logs survive stop/disconnect in memory
   and are exportable as UTF-8 text with device, time, driver and stop metadata.
5. Reject overlapping opens; correlate permission with its device/session and discard
   late permission/open/read completions after stop or background. One worker owns I/O.
   Leaving Target/background/destroy closes USB; returning never reconnects automatically.
6. Denied permission, missing/unsupported/busy devices and unplug errors are readable.
   Sharing uses a private cached file and a temporary read grant through Android's chooser.
7. Browser and Android share the same view. Browser says USB diagnostics need Android.
   USB is optional in the manifest. Existing Wi-Fi controls and scheduling remain unchanged.
8. Driver/library use is pinned. Host and native tests cover the lifecycle and bounded
   logging; VM proves real APK installation and native no-device/share UI where possible.
   Physical USB drivers/reset lines/board logs remain explicit owner checks.
