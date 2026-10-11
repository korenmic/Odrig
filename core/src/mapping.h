#ifndef ODRIG_MAPPING_H
#define ODRIG_MAPPING_H

#include "core_state.h"
#include "reasons.h"

namespace odrig {

// Reads `mapping.json` under the rules of docs/mapping.md and sets up the legs and the LED
// tables of the core. Returns kNone, kMappingMissing, kMappingMalformed, kReadError or
// kOutOfMemory. Unless it returns kNone the core has no legs.
Reason read_mapping(Core &core);

}  // namespace odrig

#endif
