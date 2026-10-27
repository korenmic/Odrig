// The wall's budget that the firmware gives the core while no budgets are saved, from WLED's
// maximum current as WLED loaded it from its settings: the maximum less what WLED keeps of
// it for the chip, 730 mA for 850; 1 mA for a maximum from 1 to 120 mA, which holds every
// LED at its lowest level; and no limit, 0, for a maximum of 0.
// The code knows nothing of the chip, so that the suite runs it on a computer.
#pragma once

#include <stdint.h>

// What WLED keeps of its maximum for the chip, in mA.
const uint32_t ODRIG_CHIP_MA = 120;

inline uint32_t odrigWallDefault(uint32_t maximum) {
  if (maximum == 0) return 0;
  return maximum > ODRIG_CHIP_MA ? maximum - ODRIG_CHIP_MA : 1;
}
