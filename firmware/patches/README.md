# Patches to WLED

A file here whose name ends in `.patch` is a change to a file of WLED 16.0.1, in the form
`git diff` writes. `python3 firmware/fw.py build` brings WLED's source in the work folder
back to the pinned commit and then applies every patch file with `git apply`, in the order
of the file names, so a name starts with a number: `010-what-it-changes.patch`. A patch that
does not apply stops the build with `patch-failed`.

WLED's source is not stored in this repository, so a patch file is the only place where a
change to one of WLED's own files can live. Each one says in its first lines what it changes
and why the usermod cannot do it from outside.

The folder holds two patches:

| File | What it changes |
|---|---|
| `010-sixteen-parallel-outputs.patch` | On the ESP32-S3 WLED drives sixteen outputs through its parallel driver in place of eight, which with its four RMT outputs makes twenty: one for each leg of the target installation. The patch raises the limit in `wled00/const.h`, switches the types of the parallel outputs in `wled00/bus_wrapper.h` to the sixteen-lane form the LED library has, and corrects WLED's estimate of the driver's memory in `wled00/FX_fcn.cpp`. Nothing changes for another chip. |
| `020-newer-software.patch` | The names and calls of WLED that Arduino-ESP32 3 and ESP-IDF 5.5 changed, for the trial build on the newer USB software: WLED's global `Network` in `wled00/src/dependencies/network/Network.h`, the PWM calls in `wled00/bus_manager.cpp`, and SHA-1 and the chip's information in `wled00/util.cpp`. Every change is held by `ESP_IDF_VERSION_MAJOR >= 5`, so the build known good compiles as before. |

`python3 firmware/fw.py build --stock` applies no patch. `python3 firmware/fw.py test` checks
that every patch file here applies to WLED's files at the pinned commit.
