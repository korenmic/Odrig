// A stand-in for the core: ten legs on pins 1 to 10 with 180 LEDs each, every LED with a
// fixed dim colour of its own, due again every 20 ms.
#pragma once

#include <stdint.h>

#include "odrig_leds.h"

namespace OdrigPattern {

void begin();

// Whether a refresh is due at this time. The colours never change.
bool poll(uint64_t now_ms);

OdrigLegSource legs();

}  // namespace OdrigPattern
