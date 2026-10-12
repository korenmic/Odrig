#include "content.h"

#include "storage.h"

namespace odrig {

uint32_t content_space(const Core &core, Reply &reply) {
    uint32_t free_bytes = 0;
    uint32_t total_bytes = 0;
    if (core.host.space == nullptr || core.host.space(core.host.ctx, &free_bytes, &total_bytes) != 1) {
        return refuse(reply, "storage-error");
    }
    uint32_t animations = 0;
    for (uint32_t item = 0; !core.invalid && item < core.item_count; ++item) {
        if (!core.items[item].is_cycle) {
            ++animations;
        }
    }
    reply.text("{\"ok\":true,\"free\":");
    reply.number(free_bytes);
    reply.text(",\"total\":");
    reply.number(total_bytes);
    reply.text(",\"animations\":");
    reply.number(animations);
    reply.text("}\n");
    return reply.length;
}

}  // namespace odrig
