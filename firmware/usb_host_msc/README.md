# USB host driver for flash drives

Espressif's driver of the USB mass storage class, `usb_host_msc` version 1.1.1, as it is
in the folder `usb/usb_host_msc` of
[espressif/idf-extra-components](https://github.com/espressif/idf-extra-components) at
commit `5c5fdc1da4`: the last version for ESP-IDF 4.4, on which the firmware's framework
is built. Its licence is Apache 2.0, in `LICENCE`.

The files are as they were taken, without the driver's tests, its build file for ESP-IDF
and its change log. `library.json` is this repository's, so that PlatformIO builds the
driver as a library of the firmware. [docs/firmware.md](../../docs/firmware.md) says what
the firmware does with it.
