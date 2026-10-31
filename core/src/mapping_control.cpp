#include "mapping_control.h"
#include "breaks.h"

#include "drive.h"

#include <string.h>

#include "crc32.h"
#include "player.h"
#include "storage.h"

namespace odrig {
namespace {

#include "diagonal_data.h"

const uint32_t kSnakes = 20;
// The snake that may be cross-wired: its chain runs up its first column, up its third and
// down its second.
const uint32_t kCrossedSnake = 10;
// The test of a snake: a white block of 3 x 3 pixels that runs from the bottom of the snake's
// three columns to their top and back, one row every kSnakeStepMs milliseconds.
const uint32_t kSnakeBlock = 3;
const uint64_t kSnakeStepMs = 40;
const char kMappingPart[] = "mapping.part";
const char kMappingFile[] = "mapping.json";

const LegInfo *leg_number(const Core &core, uint32_t number) {
    for (uint32_t i = 0; i < core.leg_count; ++i) {
        if (core.legs[i].leg == number) return &core.legs[i];
    }
    return nullptr;
}

uint32_t revision_of(const Core &core) {
    uint32_t crc = kCrcStart;
    for (uint32_t number = 1; number <= kSnakes; ++number) {
        crc = crc_add(crc, static_cast<uint8_t>(leg_number(core, number)->pin));
    }
    return crc_value(crc);
}

bool parse_pins(const char *text, uint32_t length, uint8_t *pins) {
    uint32_t at = 0;
    for (uint32_t i = 0; i < kSnakes; ++i) {
        uint32_t value = 0;
        const uint32_t start = at;
        while (at < length && text[at] >= '0' && text[at] <= '9') {
            value = value * 10 + static_cast<uint32_t>(text[at++] - '0');
            if (value > 255) return false;
        }
        if (at == start) return false;
        pins[i] = static_cast<uint8_t>(value);
        if (i + 1 == kSnakes) return at == length;
        if (at == length || text[at++] != ',') return false;
    }
    return false;
}

struct MappingWriter {
    Core &core;
    uint32_t length;
    bool ok;

    void flush() {
        if (ok && length != 0) ok = core.host.write(core.host.ctx, core.chunk, length) == 1;
        length = 0;
    }
    void text(const char *value) {
        while (*value != '\0' && ok) {
            if (length == kChunkSize) flush();
            core.chunk[length++] = static_cast<uint8_t>(*value++);
        }
    }
    void number(uint32_t value) {
        char figures[11];
        uint32_t count = 0;
        do {
            figures[count++] = static_cast<char>('0' + value % 10);
            value /= 10;
        } while (value != 0);
        while (count != 0 && ok) {
            if (length == kChunkSize) flush();
            core.chunk[length++] = static_cast<uint8_t>(figures[--count]);
        }
    }
};

// The canvas place, from 0, of LED n, from 0, of snake `number` wired as the snakes are:
// up its first column, down its second, up its third. Cross-wired: up its first column, up
// its third, down its second.
uint32_t place_of(uint32_t number, uint32_t n, bool crossed) {
    const uint32_t strip = n / 60;
    const uint32_t column = crossed ? (strip == 0 ? 0 : 3 - strip) : strip;
    const bool down = crossed ? strip == 2 : strip == 1;
    const uint32_t y = down ? 59 - n % 60 : n % 60;
    return y * 60 + (number - 1) * 3 + column;
}

bool leg_is(const Core &core, const LegInfo &leg, uint32_t number, bool crossed) {
    for (uint32_t n = 0; n < 180; ++n) {
        if (core.led_pixel[leg.first + n] != place_of(number, n, crossed)) return false;
    }
    return true;
}

// Whether the mapping is editable with snake 10 cross-wired.
bool mapping_crossed(const Core &core) {
    return mapping_editable(core) && leg_is(core, *leg_number(core, kCrossedSnake), kCrossedSnake, true);
}

bool persist(Core &core, const uint8_t *pins, bool crossed) {
    const odrig_host &host = core.host;
    if (!storage_changes(core) || core.chunk == nullptr || host.write_open(host.ctx, kMappingPart) != 1) return false;
    MappingWriter out = {core, 0, true};
    out.text("{\"version\":1,\"height\":60,\"legs\":[");
    for (uint32_t i = 0; i < core.leg_count; ++i) {
        const uint32_t number = core.legs[i].leg;
        if (i != 0) out.text(",");
        out.text("{\"leg\":"); out.number(number);
        out.text(",\"pin\":"); out.number(pins[number - 1]);
        out.text(",\"first_led\":\"bottom\",\"columns\":[");
        if (crossed && number == kCrossedSnake) {
            out.number((number - 1) * 3 + 1); out.text(",");
            out.number((number - 1) * 3 + 3); out.text(",");
            out.number((number - 1) * 3 + 2); out.text("],\"starts\":[\"bottom\",\"bottom\",\"top\"]}");
        } else {
            out.number((number - 1) * 3 + 1); out.text(",");
            out.number((number - 1) * 3 + 2); out.text(",");
            out.number((number - 1) * 3 + 3); out.text("]}");
        }
    }
    out.text("]}\n");
    out.flush();
    if (!out.ok || host.write_close(host.ctx) != 1 || host.rename(host.ctx, kMappingPart, kMappingFile) != 1) {
        host.remove(host.ctx, kMappingPart);
        return false;
    }
    return true;
}

// An ODRG file the core holds, read as a host reads a file.
struct Asset {
    const uint8_t *bytes;
    uint32_t size;
    uint32_t offset;
};
int asset_open(void *ctx, const char *) {
    static_cast<Asset *>(ctx)->offset = 0;
    return 1;
}
int32_t asset_read(void *ctx, uint8_t *out, size_t capacity) {
    Asset &asset = *static_cast<Asset *>(ctx);
    size_t count = asset.size - asset.offset;
    if (count > capacity) count = capacity;
    memcpy(out, asset.bytes + asset.offset, count);
    asset.offset += static_cast<uint32_t>(count);
    return static_cast<int32_t>(count);
}
void asset_close(void *) {}

// Decodes the diagonal's one frame into the pixel buffer.
bool decode_diagonal(Core &core) {
    Asset asset = {kDiagonal, static_cast<uint32_t>(sizeof kDiagonal), 0};
    odrig_host host = {};
    host.ctx = &asset;
    host.open = asset_open;
    host.read = asset_read;
    host.close = asset_close;
    Reason reason = core.file.open(host, "test");
    if (reason == kNone) reason = core.decoder.open(&core.file, &core.inflate, core.window);
    if (reason == kNone) {
        memset(core.pixels, 0, core.decoder.n);
        uint16_t duration = 0;
        reason = core.decoder.next(core.pixels, &duration);
    }
    if (reason == kNone) reason = core.decoder.finish();
    core.file.close();
    return reason == kNone;
}

bool available(const Core &core, uint32_t item) {
    if (is_drive(item)) {
        return drive_plays(core, item - kDriveBase);
    }
    return item < core.item_count && !core.items[item].is_cycle && item_usable(core, item);
}

}  // namespace

bool mapping_editable(const Core &core) {
    if (core.invalid || core.width != 60 || core.height != 60 || core.leg_count != kSnakes) return false;
    for (uint32_t number = 1; number <= kSnakes; ++number) {
        const LegInfo *leg = leg_number(core, number);
        if (leg == nullptr || leg->count != 180) return false;
        if (!leg_is(core, *leg, number, false) && !(number == kCrossedSnake && leg_is(core, *leg, number, true))) return false;
    }
    return true;
}

uint32_t mapping_get(const Core &core, Reply &reply) {
    const bool editable = mapping_editable(core);
    reply.text("{\"ok\":true,\"editable\":"); reply.text(editable ? "true" : "false");
    reply.text(",\"pins\":[");
    if (editable) {
        for (uint32_t number = 1; number <= kSnakes; ++number) {
            if (number != 1) reply.text(",");
            reply.number(leg_number(core, number)->pin);
        }
    }
    reply.text("],\"revision\":"); reply.number(editable ? revision_of(core) : 0);
    reply.text(",\"cross\":"); reply.text(mapping_crossed(core) ? "true" : "false");
    reply.text(",\"test\":"); reply.text(core.mapping_test ? "true" : "false");
    reply.text(",\"snake\":");
    if (core.mapping_test && core.mapping_snake != 0) reply.number(core.mapping_snake); else reply.text("null");
    reply.text("}\n");
    return reply.length;
}

uint32_t mapping_set(Core &core, uint32_t revision, const char *text, uint32_t length, Reply &reply) {
    uint8_t pins[kSnakes];
    if (!parse_pins(text, length, pins)) return refuse(reply, "bad-argument");
    if (core.invalid) return refuse(reply, "show-invalid");
    if (!mapping_editable(core)) return refuse(reply, "bad-argument");
    if (!check_complete(core) || core.upload.state != kUploadNone) return refuse(reply, "busy");
    for (uint32_t i = 0; i < kSnakes; ++i) {
        bool found = false;
        for (uint32_t j = 0; j < kSnakes; ++j) found = found || core.legs[j].pin == pins[i];
        if (!found) return refuse(reply, "bad-argument");
        for (uint32_t j = 0; j < i; ++j) {
            if (pins[i] == pins[j]) return refuse(reply, "bad-argument");
        }
    }
    if (revision != revision_of(core)) return refuse(reply, "mapping-conflict");
    bool same = true;
    for (uint32_t i = 0; i < kSnakes; ++i) same = same && leg_number(core, i + 1)->pin == pins[i];
    if (same) return succeed(reply);
    if (!persist(core, pins, mapping_crossed(core))) return refuse(reply, "storage-error");
    for (uint32_t i = 0; i < core.leg_count; ++i) core.legs[i].pin = pins[core.legs[i].leg - 1];
    return succeed(reply);
}

uint32_t mapping_cross(Core &core, bool crossed, Reply &reply) {
    if (core.invalid) return refuse(reply, "show-invalid");
    if (!mapping_editable(core)) return refuse(reply, "bad-argument");
    if (!check_complete(core) || core.upload.state != kUploadNone) return refuse(reply, "busy");
    if (mapping_crossed(core) == crossed) return succeed(reply);
    uint8_t pins[kSnakes];
    for (uint32_t i = 0; i < kSnakes; ++i) pins[i] = static_cast<uint8_t>(leg_number(core, i + 1)->pin);
    if (!persist(core, pins, crossed)) return refuse(reply, "storage-error");
    // The next refresh places the snake's LEDs by the new wiring.
    const LegInfo &leg = *leg_number(core, kCrossedSnake);
    for (uint32_t n = 0; n < 180; ++n) core.led_pixel[leg.first + n] = static_cast<uint16_t>(place_of(kCrossedSnake, n, crossed));
    return succeed(reply);
}

void mapping_test_stop(Core &core) {
    if (!core.mapping_test) return;
    core.mapping_test = 0;
    core.mapping_snake = 0;
    if (core.invalid) return;
    // A window that ended under the test is taken now: the next playlist plays from its
    // first animation in place of the saved one; a saved cycle goes on.
    const bool rotated = player_window_passed(core, core.latest);
    if (core.mapping_saved_playing < core.item_count && core.items[core.mapping_saved_playing].is_cycle) {
        const uint32_t saved = core.mapping_saved_playing;
        player_play_cycle(core, saved);
        const ItemInfo &cycle = core.items[saved];
        for (uint32_t i = 0; i < cycle.count; ++i) {
            if (core.entries[cycle.first + i] == core.mapping_saved_shown) {
                core.cycle_start_entry = i;
                core.shown = core.mapping_saved_shown;
                break;
            }
        }
    } else {
        const uint32_t from = !rotated && available(core, core.mapping_saved_shown) ? core.mapping_saved_shown : player_first_in_playlist(core);
        if (from != kNothing) player_play_all(core, from);
        else player_halt(core);
    }
}

uint32_t mapping_test(Core &core, bool enabled, uint32_t snake, Reply &reply) {
    if (!enabled) {
        mapping_test_stop(core);
        return succeed(reply);
    }
    if (core.clocks_on == kClocksOnly) return refuse(reply, "in-use");
    if (core.mapping_test && core.mapping_snake == snake) return succeed(reply);
    if (core.invalid) return refuse(reply, "show-invalid");
    if (!mapping_editable(core)) return refuse(reply, "bad-argument");
    if (!check_complete(core) || core.upload.state != kUploadNone) return refuse(reply, "busy");
    // A test that follows another one resumes what played before the first.
    if (!core.mapping_test) {
        // A break gives way to the animation it was to give way to, which the test's end
        // plays from its first frame.
        player_break_leave(core);
        core.mapping_saved_playing = core.playing;
        core.mapping_saved_shown = core.shown;
        player_halt(core);
    }
    core.mapping_test = 1;
    core.mapping_snake = static_cast<uint8_t>(snake);
    if (snake == 0 && !decode_diagonal(core)) {
        mapping_test_stop(core);
        return refuse(reply, "storage-error");
    }
    return succeed(reply);
}

void snake_test_draw(Core &core, uint64_t now) {
    const uint32_t travel = core.height - kSnakeBlock;
    const uint64_t step = (now - core.t0) / kSnakeStepMs;
    const uint32_t phase = static_cast<uint32_t>(step % (2u * travel));
    const uint32_t at = phase <= travel ? phase : 2u * travel - phase;
    const uint32_t left = (core.mapping_snake - 1u) * kSnakeBlock;
    // The picture has three bytes a pixel and no palette, as a drawn animation has.
    core.decoder.colours = 0;
    memset(core.pixels, 0, 3u * core.width * core.height);
    for (uint32_t row = at; row < at + kSnakeBlock; ++row) {
        memset(core.pixels + 3u * (row * core.width + left), 255, 3u * kSnakeBlock);
    }
}

}  // namespace odrig
