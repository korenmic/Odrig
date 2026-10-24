#ifndef ODRIG_MAPPING_CONTROL_H
#define ODRIG_MAPPING_CONTROL_H

#include "commands.h"

namespace odrig {

bool mapping_editable(const Core &core);
uint32_t mapping_get(const Core &core, Reply &reply);
uint32_t mapping_set(Core &core, uint32_t revision, const char *pins, uint32_t length, Reply &reply);
// Shows the diagonal, with `snake` 0, or snake n's test, or stops the test that shows.
uint32_t mapping_test(Core &core, bool enabled, uint32_t snake, Reply &reply);
void mapping_test_stop(Core &core);

}  // namespace odrig

#endif
