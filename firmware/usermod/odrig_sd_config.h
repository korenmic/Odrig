// SPI-card settings. No pin is selected until the wiring is known.
#pragma once

#ifndef ODRIG_SD_SCK
#define ODRIG_SD_SCK -1
#endif
#ifndef ODRIG_SD_MISO
#define ODRIG_SD_MISO -1
#endif
#ifndef ODRIG_SD_MOSI
#define ODRIG_SD_MOSI -1
#endif
#ifndef ODRIG_SD_CS
#define ODRIG_SD_CS -1
#endif
#ifndef ODRIG_SD_FREQUENCY
#define ODRIG_SD_FREQUENCY 4000000
#endif
#ifndef ODRIG_SD_MOUNT_PATH
#define ODRIG_SD_MOUNT_PATH "/sd"
#endif

namespace OdrigSdConfig {

// The exposed pins left after the twenty LED outputs, both USB connections, memory,
// boot pins and the two possible on-board RGB pins have been kept for their uses.
inline bool available(int pin) { return pin >= 39 && pin <= 42; }

inline bool pinsValid(int clock, int input, int output, int select) {
  return available(clock) && available(input) && available(output) && available(select) &&
         clock != input && clock != output && clock != select && input != output &&
         input != select && output != select;
}

inline bool valid() {
  return pinsValid(ODRIG_SD_SCK, ODRIG_SD_MISO, ODRIG_SD_MOSI, ODRIG_SD_CS) &&
         ODRIG_SD_FREQUENCY >= 400000 && ODRIG_SD_FREQUENCY <= 20000000;
}

}  // namespace OdrigSdConfig
