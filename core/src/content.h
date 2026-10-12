#ifndef ODRIG_CONTENT_H
#define ODRIG_CONTENT_H

#include <stdint.h>

#include "commands.h"
#include "core_state.h"

namespace odrig {

// The reply to `space`: the free and the total bytes of the host's storage and the number
// of animation items of the show, which is 0 while the show is invalid. `storage-error`
// when the host cannot tell the space.
uint32_t content_space(const Core &core, Reply &reply);

}  // namespace odrig

#endif
