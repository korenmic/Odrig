#pragma once

#include "odrig_core.h"

namespace OdrigRouting {

// Resolve a fixed physical output to the logical leg assigned to it now.
inline bool onPin(odrig_core *core, uint32_t pin, odrig_leg *out) {
  const uint32_t count = odrig_core_leg_count(core);
  for (uint32_t i = 0; i < count; i++) {
    odrig_leg leg;
    if (odrig_core_leg(core, i, &leg) && leg.pin == pin) {
      *out = leg;
      return true;
    }
  }
  return false;
}

inline const odrig_leg *onPin(const odrig_leg *legs, uint32_t count, uint32_t pin) {
  for (uint32_t i = 0; i < count; i++) {
    if (legs[i].pin == pin) return &legs[i];
  }
  return nullptr;
}

}  // namespace OdrigRouting
