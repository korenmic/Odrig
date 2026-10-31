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
    uint32_t schedule_revision;
    uint16_t on_minute;
    uint16_t off_minute;
    uint8_t enabled;
    uint8_t manual;
    uint8_t settings_error;
    uint8_t manual_unsaved;
};

void civil_start(Core &core);
bool civil_board(const Core &core, char *name);
void civil_touch(Core &core, uint64_t now);
bool civil_utc(const Core &core, uint64_t now, uint32_t *utc);
uint32_t civil_reply(Core &core, uint64_t now, Reply &reply);
uint32_t civil_set(Core &core, uint64_t now, uint32_t utc, uint32_t revision, Reply &reply);
uint32_t civil_zone(Core &core, uint64_t now, const char *text, uint32_t length, Reply &reply);
void schedule_start(Core &core);
void schedule_touch(Core &core, uint64_t now);
bool schedule_minute(const char *text, uint32_t length, uint16_t *minute);
uint32_t schedule_reply(Core &core, uint64_t now, Reply &reply);
uint32_t schedule_set(Core &core, uint64_t now, uint32_t revision, uint16_t on, uint16_t off, bool enabled, Reply &reply);
uint32_t schedule_resume(Core &core, uint64_t now, uint32_t revision, Reply &reply);
uint32_t schedule_manual(Core &core, bool on, Reply &reply);

}  // namespace odrig
#endif
