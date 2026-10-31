#ifndef ODRIG_CIVIL_TIME_H
#define ODRIG_CIVIL_TIME_H

#include <stdint.h>

namespace odrig {

struct Core;
struct Reply;

struct CivilTime {
    uint64_t anchor;
    uint32_t utc;
    uint32_t from;
    uint32_t until;
    uint32_t revision;
    uint32_t next;
    int32_t offset;
    uint16_t next_index;
    uint16_t transitions;
    uint16_t zone_size;
    uint8_t valid;
    uint8_t zone_ok;
    uint8_t zone_error;
};

void civil_start(Core &core);
void civil_touch(Core &core, uint64_t now);
bool civil_utc(const Core &core, uint64_t now, uint32_t *utc);
uint32_t civil_reply(Core &core, uint64_t now, Reply &reply);
uint32_t civil_set(Core &core, uint64_t now, uint32_t utc, uint32_t revision, Reply &reply);
uint32_t civil_zone(Core &core, uint64_t now, const char *text, uint32_t length, Reply &reply);

}  // namespace odrig
#endif
