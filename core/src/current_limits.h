#ifndef ODRIG_CURRENT_LIMITS_H
#define ODRIG_CURRENT_LIMITS_H

#include <stdint.h>

#include "core_state.h"

namespace odrig {

// The budgets' file, beside `mapping.json`.
const char kLimitsFile[] = "limits.json";

// The largest budget of the wall and of a leg, in mA.
const uint32_t kLargestWallBudget = 250000;
const uint32_t kLargestLegBudget = 65535;

// The level at which nothing is dimmed.
const uint32_t kUndimmed = 255;

// WLED's estimate of what a leg of `leds` LEDs whose bytes add up to `sum` draws, in mA:
// 55 mA for an LED at full white and 1 mA for each LED at rest.
uint32_t limits_estimate(uint32_t sum, uint32_t leds);

// The sum of the bytes of `leds` LEDs.
uint32_t limits_sum(const uint8_t *data, uint32_t leds);

// The budgets in force at the start: those of `limits.json`, read as strictly as the
// mapping, or the defaults, every leg's 0 and the wall's the host's, when it is not there
// or cannot be read, which the log says once, `limits unreadable`. A leg the file names
// that the mapping lacks is passed over. Called right after the mapping is read, whatever
// came of that.
void limits_read(Core &core);

// Limits the LED data a refresh has just written, after the brightness: first each leg by
// its own budget; then every leg by the wall's level, from the bytes the legs' budgets
// left; last, a leg that its own pass brought within its budget and the wall's fade took
// above it, by its own budget again. Sets each leg's `limited` and the wall's.
void limits_apply(Core &core);

}  // namespace odrig

#endif
