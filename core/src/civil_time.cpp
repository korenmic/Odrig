#include "civil_time.h"

#include <string.h>

#include "catalog.h"
#include "commands.h"
#include "core_state.h"
#include "crc32.h"
#include "storage.h"
#include "upload.h"

namespace odrig {
namespace {

const uint32_t kFirst = 946684800u;
const uint32_t kUntil = 4102444800u;
const uint32_t kHeaderSize = 120;
const char kZoneFile[] = "timezone.bin";
const char kZonePart[] = "timezone.part";
const char kScheduleFile[] = "schedule.txt";
const char kSchedulePart[] = "schedule.part";
const char kScheduleHeader[] = "odrig-schedule 1\n";

uint32_t little32(const uint8_t *bytes) {
    return static_cast<uint32_t>(bytes[0]) | static_cast<uint32_t>(bytes[1]) << 8 |
           static_cast<uint32_t>(bytes[2]) << 16 | static_cast<uint32_t>(bytes[3]) << 24;
}

uint32_t little16(const uint8_t *bytes) {
    return static_cast<uint32_t>(bytes[0]) | static_cast<uint32_t>(bytes[1]) << 8;
}

struct Source {
    const odrig_host &host;
    const char *name;
    const uint8_t *data;
    uint32_t size;
    uint32_t base;
    uint32_t held;
    uint8_t buffer[128];

    bool get(uint32_t offset, uint8_t *out, uint32_t count) {
        if (data != nullptr) {
            if (offset > size || count > size - offset) return false;
            memcpy(out, data + offset, count);
            return true;
        }
        while (count != 0) {
            if (offset < base || offset - base >= held) {
                if (host.read_at == nullptr) return false;
                const int32_t got = host.read_at(host.ctx, name, offset, buffer, sizeof buffer);
                if (got <= 0 || static_cast<uint32_t>(got) > sizeof buffer) return false;
                base = offset;
                held = static_cast<uint32_t>(got);
            }
            const uint32_t available = held - (offset - base);
            const uint32_t take = count < available ? count : available;
            memcpy(out, buffer + (offset - base), take);
            out += take;
            offset += take;
            count -= take;
        }
        return true;
    }

    bool ends_at(uint32_t offset) const {
        if (data != nullptr) return offset == size;
        if (offset >= base && offset - base < held) return false;
        uint8_t extra;
        return host.read_at != nullptr && host.read_at(host.ctx, name, offset, &extra, 1) == 0;
    }
};

bool zone_name(const uint8_t *header) {
    const uint32_t length = header[20];
    if (length == 0 || length > 63 || header[56] == '/' || header[55 + length] == '/') return false;
    for (uint32_t at = 0; at < 64; ++at) {
        const uint8_t c = header[56 + at];
        if (at >= length) {
            if (c != 0) return false;
        } else if (!((c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') ||
                     c == '_' || c == '-' || c == '+' || (c == '/' && header[55 + at] != '/'))) return false;
    }
    return true;
}

ODRIG_NOINLINE bool validate(Source &source, CivilTime &state, uint64_t now) {
    uint8_t header[kHeaderSize];
    if (!source.get(0, header, sizeof header) || memcmp(header, "ODTZ0001", 8) != 0 ||
        header[21] != 0 || header[22] != 0 || header[23] != 0 || !zone_name(header)) return false;
    const uint32_t from = little32(header + 8);
    const uint32_t until = little32(header + 12);
    const uint32_t offsets = header[17];
    const uint32_t count = little16(header + 18);
    if (from < kFirst || until > kUntil || from >= until || offsets == 0 || offsets > 8 ||
        header[16] >= offsets || count > 276) return false;
    for (uint32_t at = 0; at < 8; ++at) {
        const int32_t value = static_cast<int32_t>(little32(header + 24 + 4 * at));
        if (at >= offsets) {
            if (value != 0) return false;
        } else {
            if (value < -86400 || value > 86400) return false;
            for (uint32_t before = 0; before < at; ++before) {
                if (little32(header + 24 + 4 * before) == static_cast<uint32_t>(value)) return false;
            }
        }
    }
    uint32_t crc = kCrcStart;
    for (uint32_t at = 0; at < sizeof header; ++at) crc = crc_add(crc, header[at]);
    const uint64_t elapsed = now >= state.anchor ? (now - state.anchor) / 1000 : 0;
    const uint64_t utc = state.valid ? static_cast<uint64_t>(state.utc) + elapsed : from;
    uint32_t previous = from;
    state.offset = static_cast<int32_t>(little32(header + 24 + 4 * header[16]));
    state.next = kNothing;
    state.next_index = static_cast<uint16_t>(count);
    for (uint32_t at = 0; at < count; ++at) {
        uint8_t entry[5];
        if (!source.get(kHeaderSize + at * 5, entry, sizeof entry)) return false;
        const uint32_t instant = little32(entry);
        if (instant <= previous || instant >= until || entry[4] >= offsets) return false;
        previous = instant;
        for (uint32_t byte = 0; byte < sizeof entry; ++byte) crc = crc_add(crc, entry[byte]);
        if (instant <= utc) state.offset = static_cast<int32_t>(little32(header + 24 + 4 * entry[4]));
        else if (state.next == kNothing) {
            state.next = instant;
            state.next_index = static_cast<uint16_t>(at);
        }
    }
    if (!source.ends_at(kHeaderSize + count * 5)) return false;
    state.from = from;
    state.until = until;
    state.transitions = static_cast<uint16_t>(count);
    state.zone_size = static_cast<uint16_t>(kHeaderSize + count * 5);
    state.revision = crc_value(crc);
    state.zone_ok = 1;
    state.zone_error = 0;
    return true;
}

ODRIG_NOINLINE bool load(Core &core, CivilTime &candidate, uint64_t now) {
    Source source = {core.host, kZoneFile, nullptr, 0, 0, 0, {0}};
    return validate(source, candidate, now);
}

ODRIG_NOINLINE bool read_zone_name(Core &core, char *name) {
    Source source = {core.host, kZoneFile, nullptr, 0, 0, 0, {0}};
    if (!source.get(56, reinterpret_cast<uint8_t *>(name), 64)) return false;
    name[63] = 0;
    return true;
}

ODRIG_NOINLINE bool verified_bytes(Core &core, const char *name, const uint8_t *expected, uint32_t size) {
    uint8_t buffer[128];
    for (uint32_t at = 0; at < size;) {
        const uint32_t wanted = size - at < sizeof buffer ? size - at : sizeof buffer;
        const int32_t got = core.host.read_at(core.host.ctx, name, at, buffer, wanted);
        if (got <= 0 || static_cast<uint32_t>(got) > wanted || memcmp(buffer, expected + at, static_cast<uint32_t>(got)) != 0) return false;
        at += static_cast<uint32_t>(got);
    }
    return core.host.read_at(core.host.ctx, name, size, buffer, 1) == 0;
}

void hex(Reply &reply, uint32_t value) {
    char digits[9];
    for (uint32_t at = 0; at < 8; ++at) digits[at] = "0123456789abcdef"[(value >> (28 - 4 * at)) & 15];
    digits[8] = 0;
    reply.text(digits);
}

void signed_number(Reply &reply, int32_t value) {
    if (value < 0) {
        reply.text("-");
        reply.number(static_cast<uint32_t>(-value));
    } else reply.number(static_cast<uint32_t>(value));
}

uint32_t settings_bytes(const CivilTime &state, char *bytes) {
    Reply text = {bytes, 0};
    text.text(kScheduleHeader);
    text.number(state.enabled);
    text.text(" ");
    text.number(state.on_minute);
    text.text(" ");
    text.number(state.off_minute);
    text.text(" ");
    text.number(state.manual);
    text.text("\n");
    return text.length;
}

uint32_t bytes_crc(const char *bytes, uint32_t size) {
    uint32_t value = kCrcStart;
    for (uint32_t at = 0; at < size; ++at) value = crc_add(value, static_cast<uint8_t>(bytes[at]));
    return crc_value(value);
}

bool decimal(const uint8_t *bytes, uint32_t size, uint32_t *at, uint32_t maximum, uint32_t *value, uint8_t end) {
    const uint32_t first = *at;
    *value = 0;
    while (*at < size && bytes[*at] >= '0' && bytes[*at] <= '9') {
        *value = *value * 10 + bytes[(*at)++] - '0';
        if (*value > maximum || *at - first > 4) return false;
    }
    if (*at == first || (*at - first > 1 && bytes[first] == '0') || *at >= size || bytes[(*at)++] != end) return false;
    return true;
}

bool parse_settings(const uint8_t *bytes, uint32_t size, CivilTime &state) {
    const uint32_t header = sizeof kScheduleHeader - 1;
    if (size < header || memcmp(bytes, kScheduleHeader, header) != 0) return false;
    uint32_t at = header, enabled = 0, on = 0, off = 0, manual = 0;
    if (!decimal(bytes, size, &at, 1, &enabled, ' ') || !decimal(bytes, size, &at, 1439, &on, ' ') ||
        !decimal(bytes, size, &at, 1439, &off, ' ') || !decimal(bytes, size, &at, 2, &manual, '\n') ||
        at != size || on == off) return false;
    state.enabled = static_cast<uint8_t>(enabled);
    state.on_minute = static_cast<uint16_t>(on);
    state.off_minute = static_cast<uint16_t>(off);
    state.manual = static_cast<uint8_t>(manual);
    state.schedule_revision = bytes_crc(reinterpret_cast<const char *>(bytes), size);
    return true;
}

bool settings_writable(const Core &core) {
    return core.host.write_open != nullptr && core.host.write != nullptr && core.host.write_close != nullptr &&
           core.host.rename != nullptr && core.host.remove != nullptr && core.host.read_at != nullptr;
}

ODRIG_NOINLINE uint32_t publish_settings(Core &core, CivilTime &candidate, Reply &reply) {
    if (core.civil.settings_error) return refuse(reply, "storage-error");
    if (!settings_writable(core)) return refuse(reply, "unsupported");
    if (core.upload.state != kUploadNone || catalog_rebuilding(core)) return refuse(reply, "busy");
    char bytes[64];
    const uint32_t size = settings_bytes(candidate, bytes);
    const uint32_t revision = bytes_crc(bytes, size);
    if (revision == core.civil.schedule_revision) {
        candidate.manual_unsaved = 0;
        core.civil = candidate;
        return succeed(reply);
    }
    const odrig_host &host = core.host;
    bool written = host.write_open(host.ctx, kSchedulePart) == 1;
    if (written) {
        const bool body = host.write(host.ctx, reinterpret_cast<const uint8_t *>(bytes), size) == 1;
        const bool closed = host.write_close(host.ctx) == 1;
        written = body && closed;
    }
    if (!written || !verified_bytes(core, kSchedulePart, reinterpret_cast<const uint8_t *>(bytes), size) ||
        host.rename(host.ctx, kSchedulePart, kScheduleFile) != 1) {
        host.remove(host.ctx, kSchedulePart);
        return refuse(reply, "storage-error");
    }
    candidate.schedule_revision = revision;
    candidate.manual_unsaved = 0;
    core.civil = candidate;
    return succeed(reply);
}

void minute_text(Reply &reply, uint16_t minute) {
    char text[6];
    text[0] = static_cast<char>('0' + minute / 60 / 10);
    text[1] = static_cast<char>('0' + minute / 60 % 10);
    text[2] = ':';
    text[3] = static_cast<char>('0' + minute % 60 / 10);
    text[4] = static_cast<char>('0' + minute % 10);
    text[5] = 0;
    reply.text(text);
}

}  // namespace

void civil_start(Core &core) {
    core.civil.valid = 0;
    CivilTime candidate = core.civil;
    if (load(core, candidate, 0)) core.civil = candidate;
    else {
        uint8_t first;
        core.civil.zone_error = core.host.read_at != nullptr &&
            core.host.read_at(core.host.ctx, kZoneFile, 0, &first, 1) >= 0 ? 1 : 0;
        if (core.civil.zone_error && core.host.log != nullptr) core.host.log(core.host.ctx, "time zone unreadable");
    }
}

bool civil_utc(const Core &core, uint64_t now, uint32_t *utc) {
    const CivilTime &state = core.civil;
    if (!state.valid || !state.zone_ok) return false;
    const uint64_t elapsed = now >= state.anchor ? (now - state.anchor) / 1000 : 0;
    const uint64_t value = static_cast<uint64_t>(state.utc) + elapsed;
    if (value < state.from || value >= state.until || value >= kUntil) return false;
    *utc = static_cast<uint32_t>(value);
    return true;
}

void civil_touch(Core &core, uint64_t now) {
    uint32_t utc;
    if (!civil_utc(core, now, &utc) || core.civil.next == kNothing || utc < core.civil.next) return;
    CivilTime candidate = core.civil;
    if (load(core, candidate, now) && candidate.revision == core.civil.revision) core.civil = candidate;
    else {
        core.civil.zone_ok = 0;
        core.civil.zone_error = 1;
    }
}

uint32_t civil_reply(Core &core, uint64_t now, Reply &reply) {
    civil_touch(core, now);
    char name[64];
    if (core.civil.zone_ok && !read_zone_name(core, name)) return refuse(reply, "storage-error");
    uint32_t utc = 0;
    const bool valid = civil_utc(core, now, &utc);
    reply.text("{\"ok\":true,\"valid\":");
    reply.text(valid ? "true,\"utc\":" : "false,\"utc\":");
    if (valid) reply.number(utc); else reply.text("null");
    reply.text(",\"zone\":");
    if (core.civil.zone_ok) {
        reply.text("\"");
        reply.escaped(name);
        reply.text("\"");
    } else reply.text("null");
    reply.text(",\"offset\":");
    if (core.civil.zone_ok) signed_number(reply, core.civil.offset); else reply.text("null");
    reply.text(",\"revision\":");
    if (core.civil.zone_ok) { reply.text("\""); hex(reply, core.civil.revision); reply.text("\""); }
    else reply.text("null");
    reply.text(",\"from\":");
    if (core.civil.zone_ok) reply.number(core.civil.from); else reply.text("null");
    reply.text(",\"until\":");
    if (core.civil.zone_ok) reply.number(core.civil.until); else reply.text("null");
    reply.text(",\"error\":");
    reply.text(core.civil.zone_error ? "\"zone-unreadable\"}\n" : "null}\n");
    return reply.length;
}

uint32_t civil_set(Core &core, uint64_t now, uint32_t utc, uint32_t revision, Reply &reply) {
    if (utc < kFirst || utc >= kUntil) return refuse(reply, "bad-argument");
    if (!core.civil.zone_ok) return refuse(reply, "zone-unset");
    if (revision != core.civil.revision) return refuse(reply, "stale");
    CivilTime candidate = core.civil;
    candidate.utc = utc;
    candidate.anchor = now;
    candidate.valid = 1;
    if (!load(core, candidate, now)) return refuse(reply, "storage-error");
    if (candidate.revision != revision) return refuse(reply, "stale");
    if (utc < candidate.from || utc >= candidate.until) return refuse(reply, "bad-argument");
    core.civil = candidate;
    schedule_touch(core, now);
    return succeed(reply);
}

ODRIG_NOINLINE uint32_t civil_zone(Core &core, uint64_t now, const char *text, uint32_t length, Reply &reply) {
    const uint32_t size = base64_size(text, length);
    if (size < kHeaderSize) return refuse(reply, "bad-argument");
    const odrig_host &host = core.host;
    if (core.chunk == nullptr || host.write_open == nullptr || host.write == nullptr || host.write_close == nullptr ||
        host.rename == nullptr || host.remove == nullptr || host.read_at == nullptr) return refuse(reply, "unsupported");
    if (core.upload.state != kUploadNone || catalog_rebuilding(core)) return refuse(reply, "busy");
    base64_read(text, length, core.chunk);
    CivilTime candidate = core.civil;
    Source source = {host, nullptr, core.chunk, size, 0, 0, {0}};
    if (!validate(source, candidate, now)) return refuse(reply, "bad-argument");
    if (core.civil.zone_ok && candidate.revision == core.civil.revision) return succeed(reply);
    bool written = host.write_open(host.ctx, kZonePart) == 1;
    if (written) {
        const bool body = host.write(host.ctx, core.chunk, size) == 1;
        const bool closed = host.write_close(host.ctx) == 1;
        written = body && closed;
    }
    if (!written || !verified_bytes(core, kZonePart, core.chunk, size) || host.rename(host.ctx, kZonePart, kZoneFile) != 1) {
        host.remove(host.ctx, kZonePart);
        return refuse(reply, "storage-error");
    }
    core.civil = candidate;
    schedule_touch(core, now);
    return succeed(reply);
}

ODRIG_NOINLINE void schedule_start(Core &core) {
    CivilTime &state = core.civil;
    state.enabled = 1;
    state.on_minute = 1080;
    state.off_minute = 360;
    state.manual = state.manual_unsaved = state.settings_error = 0;
    char defaults[64];
    state.schedule_revision = bytes_crc(defaults, settings_bytes(state, defaults));
    const odrig_host &host = core.host;
    const int opened = host.open(host.ctx, kScheduleFile);
    if (opened == 0) return;
    bool sound = opened == 1;
    if (sound) {
        uint8_t data[64];
        uint32_t size = 0;
        while (size < sizeof data) {
            const int32_t got = host.read(host.ctx, data + size, sizeof data - size);
            if (got < 0 || static_cast<uint32_t>(got) > sizeof data - size) { sound = false; break; }
            if (got == 0) break;
            size += static_cast<uint32_t>(got);
        }
        host.close(host.ctx);
        CivilTime candidate = state;
        sound = sound && size < sizeof data && parse_settings(data, size, candidate);
        if (sound) state = candidate;
    }
    if (!sound) {
        state.enabled = 0;
        state.settings_error = 1;
        if (host.log != nullptr) host.log(host.ctx, "schedule unreadable");
    }
}

void schedule_touch(Core &core, uint64_t now) {
    civil_touch(core, now);
    const CivilTime &state = core.civil;
    if (state.manual != 0) { core.on = state.manual == 1 ? 1 : 0; return; }
    uint32_t utc = 0;
    if (state.settings_error || !state.enabled || !civil_utc(core, now, &utc)) return;
    const int64_t local = static_cast<int64_t>(utc) + state.offset;
    const uint32_t minute = static_cast<uint32_t>((local % 86400 + 86400) % 86400) / 60;
    const bool on = state.on_minute < state.off_minute ? minute >= state.on_minute && minute < state.off_minute :
                    minute >= state.on_minute || minute < state.off_minute;
    core.on = on ? 1 : 0;
}

bool schedule_minute(const char *text, uint32_t length, uint16_t *minute) {
    if (length != 5 || text[2] != ':') return false;
    for (uint32_t at = 0; at < 5; ++at) if (at != 2 && (text[at] < '0' || text[at] > '9')) return false;
    const uint32_t hour = static_cast<uint32_t>((text[0] - '0') * 10 + text[1] - '0');
    const uint32_t part = static_cast<uint32_t>((text[3] - '0') * 10 + text[4] - '0');
    if (hour > 23 || part > 59) return false;
    *minute = static_cast<uint16_t>(hour * 60 + part);
    return true;
}

uint32_t schedule_reply(Core &core, uint64_t now, Reply &reply) {
    schedule_touch(core, now);
    const CivilTime &state = core.civil;
    uint32_t utc = 0;
    const bool active = state.enabled && !state.settings_error && state.manual == 0 && civil_utc(core, now, &utc);
    reply.text("{\"ok\":true,\"enabled\":");
    reply.text(state.enabled ? "true,\"on\":\"" : "false,\"on\":\"");
    minute_text(reply, state.on_minute);
    reply.text("\",\"off\":\"");
    minute_text(reply, state.off_minute);
    reply.text("\",\"override\":");
    reply.text(state.manual == 1 ? "\"on\"" : state.manual == 2 ? "\"off\"" : "null");
    reply.text(",\"revision\":\"");
    hex(reply, state.schedule_revision);
    reply.text(core.on ? "\",\"power\":true" : "\",\"power\":false");
    reply.text(active ? ",\"active\":true,\"reason\":" : ",\"active\":false,\"reason\":");
    reply.text(state.settings_error ? "\"settings-unreadable\"" : state.manual ? "\"manual\"" :
               !state.enabled ? "\"disabled\"" : !active ? "\"time-unset\"" : "null");
    reply.text(state.manual_unsaved ? ",\"saved\":false,\"error\":" : ",\"saved\":true,\"error\":");
    reply.text(state.settings_error ? "\"settings-unreadable\"" : state.manual_unsaved ? "\"manual-not-saved\"" : "null");
    reply.text("}\n");
    return reply.length;
}

uint32_t schedule_set(Core &core, uint64_t now, uint32_t revision, uint16_t on, uint16_t off, bool enabled, Reply &reply) {
    if (on >= 1440 || off >= 1440 || on == off) return refuse(reply, "bad-argument");
    if (revision != core.civil.schedule_revision) return refuse(reply, "stale");
    CivilTime candidate = core.civil;
    candidate.on_minute = on;
    candidate.off_minute = off;
    candidate.enabled = enabled ? 1 : 0;
    const uint32_t result = publish_settings(core, candidate, reply);
    schedule_touch(core, now);
    return result;
}

uint32_t schedule_resume(Core &core, uint64_t now, uint32_t revision, Reply &reply) {
    if (revision != core.civil.schedule_revision) return refuse(reply, "stale");
    CivilTime candidate = core.civil;
    candidate.manual = 0;
    const uint32_t result = publish_settings(core, candidate, reply);
    schedule_touch(core, now);
    return result;
}

uint32_t schedule_manual(Core &core, bool on, Reply &reply) {
    core.on = on ? 1 : 0;
    core.civil.manual = on ? 1 : 2;
    core.civil.manual_unsaved = 1;
    if (!settings_writable(core)) return succeed(reply);
    CivilTime candidate = core.civil;
    return publish_settings(core, candidate, reply);
}

}  // namespace odrig
