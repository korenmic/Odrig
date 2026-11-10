#include "plan.h"

#include <string.h>

#include "brightness.h"
#include "catalog.h"
#include "drive.h"
#include "mini.h"
#include "player.h"

namespace odrig {

namespace {

// Whether a word of a line is this text, byte for byte.
bool word_is(const char *word, uint32_t size, const char *wanted) {
    return strlen(wanted) == size && memcmp(word, wanted, size) == 0;
}

// The key of the file of an animation: its CRC-32 and its size, from the row of a drive's
// file or, for a file of the board's own storage, from the internal catalog.
bool key_of(Core &core, uint32_t position, uint32_t *crc, uint32_t *bytes) {
    if (is_drive(position)) {
        const DriveRow *row = drive_row(core, position - kDriveBase);
        if (row == nullptr || row->bytes == 0) {
            return false;
        }
        *crc = row->crc;
        *bytes = row->bytes;
        return true;
    }
    const FileInfo &file = core.files[core.items[position].first];
    if (file.bytes == 0 || !catalog_key(core, file.name, crc)) {
        return false;
    }
    *bytes = file.bytes;
    return true;
}

void hex8(Reply &reply, uint32_t value) {
    for (uint32_t digit = 0; digit < 8; ++digit) {
        reply.bytes[reply.length++] = "0123456789abcdef"[value >> (28 - 4 * digit) & 15u];
    }
}

// The reply being written, and whether an item was written into it.
struct Writing {
    Core *core;
    Reply *reply;
    bool any;
};

// Writes one item when it fits with the end of the reply, `]}` and the newline.
bool write_item(const PlanItem &item, void *context) {
    Writing &writing = *static_cast<Writing *>(context);
    Core &core = *writing.core;
    char room[224];
    Reply part;
    part.bytes = room;
    part.length = 0;
    part.text(writing.any ? ",{\"start\":" : "{\"start\":");
    part.number(item.start);
    part.text(",\"end\":");
    if (item.ends) {
        part.number(item.end);
    } else {
        part.text("null");
    }
    if (item.from != 0) {
        part.text(",\"from\":");
        part.number(item.from);
    }
    part.text(",\"id\":");
    part.number(player_id_of(core, item.position));
    part.text(",\"key\":");
    uint32_t crc = 0;
    uint32_t bytes = 0;
    if (key_of(core, item.position, &crc, &bytes)) {
        part.text("\"");
        hex8(part, crc);
        part.text("-");
        part.number(bytes);
        part.text("\"");
    } else {
        part.text("null");
    }
    const uint64_t loop = player_loop_of(core, item.position);
    if (loop != 0) {
        part.text(",\"loop\":");
        part.number(loop);
    }
    if (item.seeded) {
        part.text(",\"seed\":");
        part.number(item.seed);
    }
    const int saved = brightness_saved(core, item.position);
    if (saved >= 0 && saved != core.brightness) {
        part.text(",\"brightness\":");
        part.number(static_cast<uint32_t>(saved));
    }
    part.text("}");
    Reply &reply = *writing.reply;
    if (!reply.fits(part.length + 3)) {
        return false;
    }
    memcpy(reply.bytes + reply.length, room, part.length);
    reply.length += part.length;
    writing.any = true;
    return true;
}

}  // namespace

void plan_start(Core &core) {
    core.plan_version = 1;
    core.plan_on = 0;
    core.plan_projecting = 0;
}

void plan_bump(Core &core) {
    ++core.plan_version;
    if (core.plan_version == 0) {
        core.plan_version = 1;
    }
}

void plan_refreshed(Core &core) {
    const uint16_t sign = player_sign(core);
    if (sign != core.plan_sign) {
        core.plan_sign = sign;
        plan_bump(core);
    }
}

bool plan_reads_only(const char *line, uint32_t length) {
    // The words of the line, at most three of them looked at.
    const char *words[3] = {nullptr, nullptr, nullptr};
    uint32_t sizes[3] = {0, 0, 0};
    uint32_t count = 0;
    uint32_t begin = 0;
    for (uint32_t at = 0; at <= length; ++at) {
        if (at < length && line[at] != ' ' && line[at] != '\r' && line[at] != '\n') {
            continue;
        }
        if (count < 3) {
            words[count] = line + begin;
            sizes[count] = at - begin;
        }
        ++count;
        begin = at + 1;
        if (at < length && (line[at] == '\r' || line[at] == '\n')) {
            break;
        }
    }
    const char *first = words[0];
    const uint32_t size = sizes[0];
    if (word_is(first, size, "status") || word_is(first, size, "space") || word_is(first, size, "fault") ||
        word_is(first, size, "list") || word_is(first, size, "read") || word_is(first, size, "saved")) {
        return true;
    }
    if (count == 1) {
        return word_is(first, size, "catalog") || word_is(first, size, "rotation") || word_is(first, size, "time") ||
               word_is(first, size, "schedule") || word_is(first, size, "plan");
    }
    if (word_is(first, size, "catalog")) {
        return word_is(words[1], sizes[1], "page");
    }
    if (word_is(first, size, "order") || word_is(first, size, "mapping")) {
        return word_is(words[1], sizes[1], "get");
    }
    return word_is(first, size, "plan") && word_is(words[1], sizes[1], "since");
}

uint32_t plan_switch(Core &core, bool on, Reply &reply) {
    if (on && !core.plan_on) {
        core.plan_noise = core.noise;
    }
    core.plan_on = on ? 1 : 0;
    return succeed(reply);
}

uint32_t plan_answer(Core &core, uint64_t now, Reply &reply) {
    reply.text("{\"ok\":true,\"planning\":");
    reply.text(core.plan_on ? "true" : "false");
    reply.text(",\"version\":");
    reply.number(core.plan_version);
    reply.text(",\"now\":");
    reply.number(now);
    reply.text(",\"on\":");
    reply.text(core.on ? "true" : "false");
    reply.text(",\"brightness\":");
    reply.number(core.brightness);
    reply.text(",\"rotation\":");
    reply.number(90u * core.rotation);
    reply.text(",\"mini\":");
    reply.text(core.mini != nullptr && core.mini->active && !core.mini->failed ? "true" : "false");
    reply.text(",\"test\":");
    reply.text(core.mapping_test ? "true" : "false");
    reply.text(",\"snake\":");
    if (core.mapping_test && core.mapping_snake != 0) {
        reply.number(core.mapping_snake);
    } else {
        reply.text("null");
    }
    reply.text(",\"items\":[");
    Writing writing = {&core, &reply, false};
    player_plan(core, write_item, &writing);
    reply.text("]}\n");
    return reply.length;
}

uint32_t plan_since(Core &core, uint64_t now, uint32_t version, Reply &reply) {
    if (version != core.plan_version) {
        return plan_answer(core, now, reply);
    }
    reply.text("{\"ok\":true,\"planning\":");
    reply.text(core.plan_on ? "true" : "false");
    reply.text(",\"version\":");
    reply.number(core.plan_version);
    reply.text(",\"now\":");
    reply.number(now);
    reply.text(",\"unchanged\":true}\n");
    return reply.length;
}

}  // namespace odrig
