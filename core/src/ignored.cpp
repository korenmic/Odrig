#include "ignored.h"

#include <string.h>

#include "crc32.h"
#include "drive.h"
#include "player.h"
#include "storage.h"

namespace odrig {
namespace {
const char kHeader[] = "odrig-ignored 1";
const uint32_t kWriteRoom = 1000;

IgnoredOf *entries(const Core &core) {
    return core.brightness_drive == nullptr ? nullptr : reinterpret_cast<IgnoredOf *>(
        reinterpret_cast<uint8_t *>(core.brightness_drive) + kBrightnessDriveMost * sizeof(BrightnessOf));
}
uint32_t position_of(const IgnoredOf &entry) {
    return static_cast<uint32_t>(entry.position[0]) | static_cast<uint32_t>(entry.position[1]) << 8 |
           static_cast<uint32_t>(entry.position[2]) << 16 | static_cast<uint32_t>(entry.position[3]) << 24;
}
void set_position(IgnoredOf &entry, uint32_t value) {
    for (uint32_t i = 0; i < 4; ++i) entry.position[i] = static_cast<uint8_t>(value >> (8 * i));
}
bool supported(const Core &core) {
    return entries(core) != nullptr && storage_changes(core) && core.host.read_at != nullptr;
}
enum Ending { kMissing, kSound, kBad, kFailed };
struct Scan { Ending ending; uint32_t lines; uint32_t bytes; uint32_t crc; };
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
            offset += static_cast<uint32_t>(got); position = 0; length = static_cast<uint16_t>(got);
        }
        return buffer[position++];
    }
};
bool valid(char *text, uint32_t length) {
    if (length < 3 || length > 129 || (text[0] != 'f' && text[0] != 'd') || text[1] != ' ') return false;
    for (uint32_t i = 2; i < length; ++i) if (text[i] == '\0' || text[i] == '\r' || text[i] == '\n') return false;
    text[length] = '\0';
    return true;
}
template <typename Each>
ODRIG_NOINLINE Scan scan(Core &core, const char *name, Each each) {
    Reader reader = {core.host, name, 0, 0, 0, {0}};
    char text[131];
    uint32_t length = 0, crc = kCrcStart;
    bool header = false;
    Scan result = {kSound, 0, 0, 0};
    int got = 0;
    while ((got = reader.get()) >= 0) {
        crc = crc_add(crc, static_cast<uint8_t>(got));
        if (got != '\n') {
            if (length + 1 >= sizeof text) { result.ending = kBad; break; }
            text[length++] = static_cast<char>(got);
            continue;
        }
        if (!header) {
            header = true;
            if (length != sizeof kHeader - 1 || memcmp(text, kHeader, length)) { result.ending = kBad; break; }
        } else {
            if (++result.lines > kIgnoredMost || !valid(text, length)) { result.ending = kBad; break; }
            each(text, length);
        }
        length = 0;
    }
    result.bytes = reader.offset; result.crc = crc_value(crc);
    if (result.ending == kSound && got == -kReadError) result.ending = result.bytes == 0 ? kMissing : kFailed;
    if (result.ending == kSound && (!header || length != 0)) result.ending = kBad;
    return result;
}
void apply(Core &core, const char *text, uint32_t length) {
    const uint8_t kind = static_cast<uint8_t>(text[0]);
    const uint32_t position = kind == 'f' ? drive_position_named(core, text + 2, length - 2) : drive_folder_with_path(core, text + 2);
    if (position == kNothing) return;
    IgnoredOf *cache = entries(core);
    for (uint32_t i = 0; i < kIgnoredMost; ++i) {
        if (cache[i].kind == kind && position_of(cache[i]) == position) return;
        if (cache[i].kind == 0) { cache[i].kind = kind; set_position(cache[i], position); return; }
    }
}
struct Plan { const char *text; uint32_t length; bool ignored; };
bool same(const char *text, uint32_t length, const Plan &plan) {
    return length == plan.length && memcmp(text, plan.text, length) == 0;
}
struct Writer {
    Core &core;
    uint32_t used;
    uint32_t bytes;
    uint32_t crc;
    bool failed;
    void flush() {
        if (used && !failed && core.host.write(core.host.ctx, core.chunk, used) != 1) failed = true;
        used = 0;
    }
    void line(const char *text, uint32_t length) {
        for (uint32_t i = 0; i <= length && !failed; ++i) {
            const uint8_t b = i == length ? '\n' : static_cast<uint8_t>(text[i]);
            core.chunk[used++] = b; ++bytes; crc = crc_add(crc, b);
            if (used == kWriteRoom) flush();
        }
    }
};
ODRIG_NOINLINE bool write_file(Core &core, const Plan &plan, bool existed) {
    if (core.host.write_open(core.host.ctx, kIgnoredPart) != 1) return false;
    Writer out = {core, 0, 0, kCrcStart, false};
    out.line(kHeader, sizeof kHeader - 1);
    Ending ending = kSound;
    if (existed) ending = scan(core, kIgnoredFile, [&](const char *text, uint32_t length) {
        if (!same(text, length, plan)) out.line(text, length);
    }).ending;
    if (plan.ignored) out.line(plan.text, plan.length);
    out.flush();
    const bool closed = core.host.write_close(core.host.ctx) == 1;
    if (!closed || out.failed || ending != kSound) return false;
    const Scan verified = scan(core, kIgnoredPart, [](const char *, uint32_t) {});
    return verified.ending == kSound && verified.bytes == out.bytes && verified.crc == crc_value(out.crc) &&
        core.host.rename(core.host.ctx, kIgnoredPart, kIgnoredFile) == 1;
}
}

void ignored_drive_found(Core &core) {
    if (entries(core) != nullptr) memset(entries(core), 0, kIgnoredMost * sizeof(IgnoredOf));
}
void ignored_start(Core &core) {
    ignored_drive_found(core);
    if (!supported(core)) return;
    const Scan result = scan(core, kIgnoredFile, [&](const char *text, uint32_t length) { apply(core, text, length); });
    core.ignored_present = result.ending != kMissing ? 1 : 0;
    core.ignored_error = result.ending == kBad || result.ending == kFailed ? 1 : 0;
    if (core.ignored_error) {
        ignored_drive_found(core);
        if (core.host.log != nullptr) core.host.log(core.host.ctx, "ignored unreadable");
    }
}
bool ignored_own(const Core &core, uint8_t kind, uint32_t position) {
    const IgnoredOf *cache = entries(core);
    for (uint32_t i = 0; cache != nullptr && i < kIgnoredMost; ++i)
        if (cache[i].kind == kind && position_of(cache[i]) == position) return true;
    return false;
}
bool ignored_inherited(const Core &core, uint8_t kind, uint32_t position) {
    const IgnoredOf *cache = entries(core);
    for (uint32_t i = 0; cache != nullptr && i < kIgnoredMost; ++i) {
        if (cache[i].kind != 'd') continue;
        const uint32_t ordinal = position_of(cache[i]);
        IndexFolder folder;
        if (!drive_folder(core, ordinal, folder)) continue;
        if (kind == 'f' ? position >= folder.first && position < folder.last : position > ordinal && position < folder.end) return true;
    }
    return false;
}
bool drive_automatic(const Core &core, uint32_t position) {
    return drive_plays(core, position) && !ignored_own(core, 'f', position) && !ignored_inherited(core, 'f', position);
}
uint32_t ignored_change(Core &core, uint32_t id, bool ignored, Reply &reply) {
    uint32_t position = 0;
    const uint8_t kind = drive_find(core, id, &position);
    if (kind == 0) return refuse(reply, "unknown-id");
    if (!supported(core) || core.ignored_error) return refuse(reply, "storage-error");
    char *text = reinterpret_cast<char *>(core.chunk + kWriteRoom);
    text[0] = static_cast<char>(kind); text[1] = ' ';
    if (kind == 'd') {
        if (drive_folder_path(core, position, text + 2, 128) == 0) return refuse(reply, "storage-error");
    } else {
        const DriveRow *row = drive_row(core, position);
        if (row == nullptr || !row->listed || strlen(row->name) > 127) return refuse(reply, "unknown-id");
        memcpy(text + 2, row->name, strlen(row->name) + 1);
    }
    const Plan plan = {text, static_cast<uint32_t>(strlen(text)), ignored};
    if (!valid(text, plan.length)) return refuse(reply, "storage-error");
    bool found = false;
    const Scan before = scan(core, kIgnoredFile, [&](const char *line, uint32_t length) { found = found || same(line, length, plan); });
    if (before.ending == kBad || before.ending == kFailed || (before.ending == kMissing && core.ignored_present)) return refuse(reply, "storage-error");
    if (found == ignored) return succeed(reply);
    if (ignored && before.lines >= kIgnoredMost) return refuse(reply, "no-space");
    if (!write_file(core, plan, before.ending == kSound)) {
        core.host.remove(core.host.ctx, kIgnoredPart);
        return refuse(reply, "storage-error");
    }
    ignored_start(core);
    player_external_inclusion_changed(core);
    return succeed(reply);
}
}
