#ifndef ODRIG_PLAN_H
#define ODRIG_PLAN_H

#include <stdint.h>

#include "commands.h"
#include "core_state.h"

namespace odrig {

// The noise a draw takes: while planning is on, the noise of the moment it was switched on,
// so that a turn decided ahead and the same turn as it plays draw the same seed and the same
// order of the clocks or of the messages.
inline uint32_t draw_noise(const Core &core) {
    return core.plan_on ? core.plan_noise : core.noise;
}

// The plan's state at the start: version 1, planning off.
void plan_start(Core &core);

// What the plan says changed, or may have: its version grows by one.
void plan_bump(Core &core);

// After a refresh: a change of what the refresh found counts as a change of the plan.
void plan_refreshed(Core &core);

// Whether a command line only reads, and so changes nothing of the plan.
bool plan_reads_only(const char *line, uint32_t length);

// `plan on` and `plan off`.
uint32_t plan_switch(Core &core, bool on, Reply &reply);

// `plan`: the plan, decided now, in one reply.
uint32_t plan_answer(Core &core, uint64_t now, Reply &reply);

// `plan since <version>`: a short reply while the version is the one given, else the plan.
uint32_t plan_since(Core &core, uint64_t now, uint32_t version, Reply &reply);

}  // namespace odrig

#endif
