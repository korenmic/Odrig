# Design

Add a small Capacitor UsbDiagnostics plugin using usb-serial-for-android 3.11.0. Discover
CDC-ACM and the library's USB/UART bridges without opening them. Explicit Start requests
the system's device permission, opens the selected port on a worker, clears RTS then DTR,
and sets 115200/8N1. A session token prevents late grants or I/O from reviving closed work.
The reader has bounded read timeouts and only writes the two existing read commands on
explicit request. No generic write endpoint is exposed to JavaScript.

A pure Java capture model stores bounded bytes and state and is exercised with fake ports.
The plugin owns physical USB resources and forwards snapshots to shared Target UI through
polling. The view shows a short tail as read-only text, a byte count, state, Stop, Read
status + fault and Share log. An explicit new capture replaces the previous log; stopping
does not. Disconnect and background preserve text. Share snapshots a private UTF-8 file,
adds metadata, and opens Android's chooser with FileProvider read permission.

The native USB/JTAG interface and COM/UART interface are shown as discovered ports. The
view explains that COM/UART carries the full log; capture cannot recover earlier bytes
or prove that a silent target is healthy. This app update needs no firmware rebuild.

Use discovered app tests for shared UI and a Java harness for the production session model.
Gradle builds the actual plugin against Android SDK. Android VM validates bridge registration,
no-device handling, UI and package upgrades; no USB hardware emulation is claimed.
