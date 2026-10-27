#ifndef ODRIG_CURRENT_LIMITS_H
#define ODRIG_CURRENT_LIMITS_H

#include <stdint.h>

#include "commands.h"
#include "core_state.h"

namespace odrig {

// The budgets' file, beside `mapping.json`, and the next one while it is written, until it
// is renamed.
const char kLimitsFile[] = "limits.json";
const char kLimitsPart[] = "limits.part";

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

// The reply of `limits <from>`: whether budgets are saved; the wall's LED count, budget,
// estimate and whether it was limited; and the same for each leg of the mapping, with its
// number first, in the mapping's order from position `from`, as many as fit, and `next`, the
// position of the first left out, or null. The estimates are those of the LED data of the
// latest refresh that wrote the LEDs.
uint32_t limits_reply(const Core &core, uint32_t from, Reply &reply);

// Saves the budget of the leg numbered `number`, or the wall's with `number` 0, and puts it
// in force from the next refresh that writes the LEDs. The words have been checked, and no
// rebuild runs.
uint32_t limits_set(Core &core, uint32_t number, uint32_t budget, Reply &reply);

// Removes `limits.json`, when there is one, and puts the defaults in force.
uint32_t limits_default(Core &core, Reply &reply);

}  // namespace odrig

#endif
