#include "brightness.h"

#include <string.h>

#include "crc32.h"
#include "drive.h"
#include "show.h"
#include "storage.h"

namespace odrig {
namespace {
const char kHeader[] = "odrig-brightness 1";
const uint32_t kLineRoom = 135;
const uint32_t kWriteRoom = 1000;

uint32_t position_of(const BrightnessOf &entry) {
    return static_cast<uint32_t>(entry.position[0]) | static_cast<uint32_t>(entry.position[1]) << 8 |
           static_cast<uint32_t>(entry.position[2]) << 16 | static_cast<uint32_t>(entry.position[3]) << 24;
}

void position_set(BrightnessOf &entry, uint32_t position) {
    for (uint32_t byte = 0; byte < 4; ++byte) entry.position[byte] = static_cast<uint8_t>(position >> (8 * byte));
}

struct Line {
    int value;
    char kind;
    const char *name;
    uint32_t length;
};

bool parse(char *text, uint32_t length, Line &line) {
    uint32_t at = 0;
    uint32_t value = 0;
    while (at < length && text[at] >= '0' && text[at] <= '9') {
        value = value * 10 + static_cast<uint32_t>(text[at++] - '0');
        if (at > 3 || value > 255) return false;
    }
    if (at == 0 || (at > 1 && text[0] == '0') || at + 3 >= length || text[at] != ' ' || text[at + 2] != ' ') return false;
    text[length] = '\0';
    line.value = static_cast<int>(value);
    line.kind = text[at + 1];
    line.name = text + at + 3;
    line.length = length - at - 3;
    if (line.kind == 'f') return is_file_name(line.name);
    if (line.kind != 'x' || line.length > 127) return false;
    for (uint32_t index = 0; index < line.length; ++index) {
        if (line.name[index] == '\0' || line.name[index] == '\r') return false;
    }
    return true;
}

enum Ending { kMissing, kSound, kBad, kFailed };
struct Scan {
    Ending ending;
    uint32_t lines;
    uint32_t external;
    uint32_t bytes;
    uint32_t crc;
};

struct Reader {
    const odrig_host &host;
    const char *name;
    uint32_t offset;
    uint16_t position;
    uint16_t length;
    uint8_t buffer[128];
    int get() {
        if (position == length) {
            const int32_t got = host.read_at(host.ctx, name, offset, buffer, sizeof buffer);
            if (got < 0 || static_cast<uint32_t>(got) > sizeof buffer) return -kReadError;
            if (got == 0) return -kEnd;
            offset += static_cast<uint32_t>(got);
            position = 0;
            length = static_cast<uint16_t>(got);
        }
        return buffer[position++];
    }
};

template <typename Each>
ODRIG_NOINLINE Scan scan(Core &core, const char *name, Each each) {
    Reader source = {core.host, name, 0, 0, 0, {0}};
    char text[kLineRoom];
    uint32_t length = 0;
    bool header = false;
    Scan result = {kSound, 0, 0, 0, 0};
    int got = 0;
    uint32_t crc = kCrcStart;
    while ((got = source.get()) >= 0) {
        crc = crc_add(crc, static_cast<uint8_t>(got));
        if (got != '\n') {
            if (length + 1 >= sizeof text) { result.ending = kBad; break; }
            text[length++] = static_cast<char>(got);
            continue;
        }
        if (!header) {
            header = true;
            if (length != sizeof kHeader - 1 || memcmp(text, kHeader, length) != 0) { result.ending = kBad; break; }
        } else {
            Line line;
            if (++result.lines > kBrightnessLines || !parse(text, length, line) ||
                (line.kind == 'x' && ++result.external > kBrightnessDriveMost)) { result.ending = kBad; break; }
            each(line, text, length);
        }
        length = 0;
    }
    result.bytes = source.offset;
    result.crc = crc_value(crc);
    if (result.ending == kSound && got == -kReadError) result.ending = result.bytes == 0 ? kMissing : kFailed;
    if (result.ending == kSound && (!header || length != 0)) result.ending = kBad;
    return result;
}

void clear_items(Core &core) {
    for (uint32_t item = 0; item < core.item_count; ++item) core.items[item].has_brightness = 0;
}

bool named(const char *name, const Line &line) {
    return strlen(name) == line.length && memcmp(name, line.name, line.length) == 0;
}

void apply(Core &core, const Line &line) {
    if (line.kind == 'f') {
        for (uint32_t at = 0; at < core.item_count; ++at) {
            ItemInfo &item = core.items[at];
            if (!item.is_cycle && !item.has_brightness && named(core.files[item.first].name, line)) {
                item.saved_brightness = static_cast<uint8_t>(line.value);
                item.has_brightness = 1;
            }
        }
        return;
    }
    if (core.brightness_drive == nullptr) return;
    const uint32_t position = drive_position_named(core, line.name, line.length);
    if (position == kNothing) return;
    for (uint32_t at = 0; at < kBrightnessDriveMost; ++at) {
        BrightnessOf &entry = core.brightness_drive[at];
        const uint32_t found = position_of(entry);
        if (found == position) return;
        if (found == kNothing) {
            position_set(entry, position);
            entry.value = static_cast<uint8_t>(line.value);
            return;
        }
    }
}

uint32_t animation_with(const Core &core, uint32_t id, bool &in_use) {
    in_use = false;
    for (uint32_t at = 0; at < core.item_count; ++at) {
        if (core.items[at].id == id) {
            in_use = core.items[at].is_cycle != 0;
            return in_use ? kNothing : at;
        }
    }
    uint32_t position = 0;
    const uint8_t kind = drive_find(core, id, &position);
    if (kind == 'f') {
        const DriveRow *row = drive_row(core, position);
        if (row != nullptr && row->listed) return kDriveBase + position;
    }
    in_use = kind == 'd';
    return kNothing;
}

struct Plan {
    int value;
    char kind;
    const char *name;
    uint32_t length;
    uint32_t size;
};

bool same(const Line &line, const Plan &plan) {
    return line.kind == plan.kind && line.length == plan.length && memcmp(line.name, plan.name, line.length) == 0;
}

bool own_line(Core &core, uint32_t position, int value, Plan &plan) {
    const char *name;
    if (is_drive(position)) {
        const DriveRow *row = drive_row(core, position - kDriveBase);
        if (row == nullptr) return false;
        name = row->name;
    } else name = core.files[core.items[position].first].name;
    const uint32_t length = static_cast<uint32_t>(strlen(name));
    if (length == 0 || length > 127) return false;
    for (uint32_t at = 0; at < length; ++at) if (name[at] == '\n' || name[at] == '\r') return false;
    char *out = reinterpret_cast<char *>(core.chunk + kWriteRoom);
    char digits[3];
    uint32_t used = 0;
    uint32_t number = value < 0 ? 0 : static_cast<uint32_t>(value);
    do { digits[used++] = static_cast<char>('0' + number % 10); number /= 10; } while (number != 0);
    uint32_t size = 0;
    while (used != 0) out[size++] = digits[--used];
    out[size++] = ' ';
    plan.kind = is_drive(position) ? 'x' : 'f';
    out[size++] = plan.kind;
    out[size++] = ' ';
    plan.name = out + size;
    memcpy(out + size, name, length + 1);
    plan.value = value;
    plan.length = length;
    plan.size = size + length;
    return true;
}

struct Writer {
    Core &core;
    uint32_t used;
    uint32_t bytes;
    uint32_t crc;
    bool failed;
    void flush() {
        if (used != 0 && !failed && core.host.write(core.host.ctx, core.chunk, used) != 1) failed = true;
        used = 0;
    }
    void line(const char *text, uint32_t length) {
        for (uint32_t at = 0; at <= length && !failed; ++at) {
            const uint8_t byte = at == length ? '\n' : static_cast<uint8_t>(text[at]);
            core.chunk[used++] = byte;
            crc = crc_add(crc, byte);
            ++bytes;
            if (used == kWriteRoom) flush();
        }
    }
};

ODRIG_NOINLINE bool write_file(Core &core, const Plan &plan, bool existed) {
    if (core.host.write_open(core.host.ctx, kBrightnessPart) != 1) return false;
    Writer out = {core, 0, 0, kCrcStart, false};
    out.line(kHeader, sizeof kHeader - 1);
    bool placed = false;
    Ending ending = kSound;
    if (existed) {
        ending = scan(core, kBrightnessFile, [&](const Line &line, const char *text, uint32_t length) {
            if (same(line, plan)) {
                if (!placed && plan.value >= 0) out.line(reinterpret_cast<const char *>(core.chunk + kWriteRoom), plan.size);
                placed = true;
            } else out.line(text, length);
        }).ending;
    }
    if (!placed && plan.value >= 0) out.line(reinterpret_cast<const char *>(core.chunk + kWriteRoom), plan.size);
    out.flush();
    const bool closed = core.host.write_close(core.host.ctx) == 1;
    if (!closed || out.failed || ending != kSound) return false;
    const Scan verified = scan(core, kBrightnessPart, [](const Line &, const char *, uint32_t) {});
    return verified.ending == kSound && verified.bytes == out.bytes && verified.crc == crc_value(out.crc) &&
           core.host.rename(core.host.ctx, kBrightnessPart, kBrightnessFile) == 1;
}

void publish(Core &core, uint32_t position, const Plan &plan) {
    if (!is_drive(position)) {
        for (uint32_t at = 0; at < core.item_count; ++at) {
            ItemInfo &item = core.items[at];
            if (!item.is_cycle && strlen(core.files[item.first].name) == plan.length &&
                memcmp(core.files[item.first].name, plan.name, plan.length) == 0) {
                item.has_brightness = plan.value >= 0 ? 1 : 0;
                item.saved_brightness = static_cast<uint8_t>(plan.value < 0 ? 0 : plan.value);
            }
        }
        return;
    }
    uint32_t empty = kBrightnessDriveMost;
    for (uint32_t at = 0; at < kBrightnessDriveMost; ++at) {
        BrightnessOf &entry = core.brightness_drive[at];
        const uint32_t found = position_of(entry);
        if (found == position - kDriveBase) {
            position_set(entry, plan.value < 0 ? kNothing : found);
            entry.value = static_cast<uint8_t>(plan.value < 0 ? 0 : plan.value);
            return;
        }
        if (found == kNothing && empty == kBrightnessDriveMost) empty = at;
    }
    if (plan.value >= 0 && empty != kBrightnessDriveMost) {
        position_set(core.brightness_drive[empty], position - kDriveBase);
        core.brightness_drive[empty].value = static_cast<uint8_t>(plan.value);
    }
}
}

bool brightness_supported(const Core &core) {
    return storage_changes(core) && core.host.read_at != nullptr && core.order_items != nullptr;
}

int brightness_saved(const Core &core, uint32_t position) {
    if (position == kNothing || core.mapping_test || !brightness_supported(core)) return -1;
    if (!is_drive(position)) {
        if (position >= core.item_count || core.items[position].is_cycle || !core.items[position].has_brightness) return -1;
        return core.items[position].saved_brightness;
    }
    for (uint32_t at = 0; core.brightness_drive != nullptr && at < kBrightnessDriveMost; ++at) {
        if (position_of(core.brightness_drive[at]) == position - kDriveBase) return core.brightness_drive[at].value;
    }
    return -1;
}

uint8_t brightness_selected(const Core &core) {
    const int saved = brightness_saved(core, core.invalid || core.playing == kNothing ? kNothing : core.shown);
    return saved < 0 ? core.brightness : static_cast<uint8_t>(saved);
}

void brightness_drive_found(Core &core) {
    if (core.brightness_drive != nullptr) memset(core.brightness_drive, 0xFF, kBrightnessDriveMost * sizeof(BrightnessOf));
}

void brightness_start(Core &core) {
    if (!brightness_supported(core)) return;
    clear_items(core);
    brightness_drive_found(core);
    const Scan result = scan(core, kBrightnessFile, [&](const Line &line, const char *, uint32_t) { apply(core, line); });
    core.brightness_present = result.ending != kMissing ? 1 : 0;
    core.brightness_error = result.ending == kBad || result.ending == kFailed ? 1 : 0;
    if (core.brightness_error) {
        clear_items(core);
        brightness_drive_found(core);
        if (core.host.log != nullptr) core.host.log(core.host.ctx, "brightness unreadable");
    }
}

uint32_t brightness_change(Core &core, uint32_t id, int value, Reply &reply) {
    bool in_use = false;
    const uint32_t position = animation_with(core, id, in_use);
    if (position == kNothing) return refuse(reply, in_use ? "in-use" : "unknown-id");
    if (!brightness_supported(core) || core.brightness_error || (is_drive(position) && core.brightness_drive == nullptr)) return refuse(reply, "storage-error");
    Plan plan;
    if (!own_line(core, position, value, plan)) return refuse(reply, "storage-error");
    int old = -1;
    bool found = false;
    const Scan before = scan(core, kBrightnessFile, [&](const Line &line, const char *, uint32_t) {
        if (!found && same(line, plan)) { found = true; old = line.value; }
    });
    if (before.ending == kBad || before.ending == kFailed || (before.ending == kMissing && core.brightness_present)) return refuse(reply, "storage-error");
    if ((!found && value < 0) || (found && old == value)) return succeed(reply);
    if (!found && value >= 0 && (before.lines >= kBrightnessLines || (plan.kind == 'x' && before.external >= kBrightnessDriveMost))) return refuse(reply, "no-space");
    if (!write_file(core, plan, before.ending == kSound)) {
        core.host.remove(core.host.ctx, kBrightnessPart);
        return refuse(reply, "storage-error");
    }
    core.brightness_present = 1;
    publish(core, position, plan);
    return succeed(reply);
}
}
