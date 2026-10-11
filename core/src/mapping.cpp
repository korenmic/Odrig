#include "mapping.h"

#include "arena.h"
#include "json_reader.h"
#include "odrg_decoder.h"

namespace odrig {

namespace {

const uint32_t kMostLegs = 255;
const uint32_t kNameSize = 12;

// What one reading of the file has seen so far.
struct Seen {
    uint32_t width;
    uint32_t legs;
    uint32_t rows;
};

// Whether row y has been marked before; marks it.
bool mark_row(uint8_t *row_check, uint32_t y) {
    uint8_t bit = static_cast<uint8_t>(1u << ((y - 1) & 7));
    uint8_t &byte = row_check[(y - 1) >> 3];
    bool marked = (byte & bit) != 0;
    byte |= bit;
    return marked;
}

// Reads one entry of `legs`. The second reading of the file also checks the leg against
// those before it and the rows against the height, and fills the tables by the width and
// the height the first reading found.
bool read_leg(Core &core, JsonReader &json, uint8_t *row_check, Seen &seen) {
    const bool fill = row_check != nullptr;
    char name[kNameSize];
    uint32_t members = 0;
    uint32_t leg = 0;
    uint32_t pin = 0;
    uint32_t rows = 0;
    bool starts_right = false;

    if (!json.object_begin()) {
        return false;
    }
    while (json.object_next(name, sizeof name)) {
        uint32_t member;
        if (same_text(name, "leg")) {
            member = 1;
        } else if (same_text(name, "pin")) {
            member = 2;
        } else if (same_text(name, "first_led")) {
            member = 4;
        } else if (same_text(name, "rows")) {
            member = 8;
        } else {
            return false;
        }
        if ((members & member) != 0) {
            return false;
        }
        members |= member;

        if (member == 1) {
            if (!json.integer(&leg) || leg < 1 || leg > 255) {
                return false;
            }
        } else if (member == 2) {
            if (!json.integer(&pin) || pin > 255) {
                return false;
            }
        } else if (member == 4) {
            char side[8];
            if (!json.string(side, sizeof side)) {
                return false;
            }
            if (same_text(side, "right")) {
                starts_right = true;
            } else if (!same_text(side, "left")) {
                return false;
            }
        } else {
            if (!json.array_begin()) {
                return false;
            }
            while (json.array_next()) {
                uint32_t y;
                if (!json.integer(&y)) {
                    return false;
                }
                if (fill) {
                    if (seen.rows + rows >= core.height || y < 1 || y > core.height || mark_row(row_check, y)) {
                        return false;
                    }
                    // The row's y waits in the row's first entry until the side is known.
                    core.led_pixel[(seen.rows + rows) * core.width] = static_cast<uint16_t>(y);
                }
                if (rows < kLargestPicture + 1) {
                    ++rows;
                }
            }
            if (json.failed || rows == 0) {
                return false;
            }
        }
    }
    if (json.failed || members != 15) {
        return false;
    }

    if (fill) {
        if (seen.legs >= core.leg_count) {
            return false;
        }
        for (uint32_t before = 0; before < seen.legs; ++before) {
            if (core.legs[before].leg == leg || core.legs[before].pin == pin) {
                return false;
            }
        }
        const uint32_t width = core.width;
        LegInfo &info = core.legs[seen.legs];
        info.leg = static_cast<uint16_t>(leg);
        info.pin = static_cast<uint16_t>(pin);
        info.first = seen.rows * width;
        info.count = rows * width;
        for (uint32_t r = 0; r < rows; ++r) {
            uint16_t *row = core.led_pixel + info.first + r * width;
            const uint32_t y = row[0];
            const bool from_right = starts_right != ((r & 1) != 0);
            for (uint32_t i = 0; i < width; ++i) {
                const uint32_t x = from_right ? width - i : 1 + i;
                row[i] = static_cast<uint16_t>((y - 1) * width + (x - 1));
            }
        }
    }
    if (seen.legs <= kMostLegs) {
        ++seen.legs;
    }
    seen.rows += rows;
    if (seen.rows > kLargestPicture + 1) {
        seen.rows = kLargestPicture + 1;
    }
    return true;
}

// Reads the whole file once. False when it breaks a rule that this reading checks.
bool read_file(Core &core, JsonReader &json, uint8_t *row_check, Seen &seen) {
    char name[kNameSize];
    uint32_t members = 0;
    if (!json.object_begin()) {
        return false;
    }
    while (json.object_next(name, sizeof name)) {
        uint32_t member;
        if (same_text(name, "version")) {
            member = 1;
        } else if (same_text(name, "width")) {
            member = 2;
        } else if (same_text(name, "legs")) {
            member = 4;
        } else {
            return false;
        }
        if ((members & member) != 0) {
            return false;
        }
        members |= member;

        if (member == 1) {
            uint32_t version;
            if (!json.integer(&version) || version != 1) {
                return false;
            }
        } else if (member == 2) {
            if (!json.integer(&seen.width) || seen.width < 1 || seen.width > 65535) {
                return false;
            }
            if (row_check != nullptr && seen.width != core.width) {
                return false;
            }
        } else {
            if (!json.array_begin()) {
                return false;
            }
            while (json.array_next()) {
                if (!read_leg(core, json, row_check, seen)) {
                    return false;
                }
                if (seen.legs > kMostLegs) {
                    return false;
                }
            }
            if (json.failed || seen.legs == 0) {
                return false;
            }
        }
    }
    return !json.failed && members == 7 && json.end();
}

// Opens the file and reads it once. With `row_check` it is the second reading.
Reason read_once(Core &core, uint8_t *row_check, Seen &seen) {
    seen.width = 0;
    seen.legs = 0;
    seen.rows = 0;
    Reason opened = core.file.open(core.host, "mapping.json");
    if (opened == kFileMissing) {
        return kMappingMissing;
    }
    if (opened != kNone) {
        return kReadError;
    }
    JsonReader json;
    json.start(&core.file);
    bool sound = read_file(core, json, row_check, seen);
    core.file.close();
    if (json.read_failed) {
        return kReadError;
    }
    return sound ? kNone : kMappingMalformed;
}

}  // namespace

Reason read_mapping(Core &core) {
    // The first reading checks the form of the file and counts the legs and the rows.
    Seen first;
    Reason reason = read_once(core, nullptr, first);
    if (reason != kNone) {
        return reason;
    }
    const uint32_t width = first.width;
    const uint32_t height = first.rows;
    if (static_cast<uint64_t>(width) * height > kLargestPicture) {
        return kMappingMalformed;
    }
    const uint32_t leds = width * height;

    core.legs = static_cast<LegInfo *>(arena_take(core, first.legs * static_cast<uint32_t>(sizeof(LegInfo))));
    core.led_pixel = static_cast<uint16_t *>(arena_take(core, leds * 2));
    core.led_data = static_cast<uint8_t *>(arena_take(core, leds * 3));
    uint8_t *row_check = static_cast<uint8_t *>(arena_take(core, (height + 7) / 8));
    if (core.legs == nullptr || core.led_pixel == nullptr || core.led_data == nullptr || row_check == nullptr) {
        return kOutOfMemory;
    }

    // The second reading checks the legs against each other and the rows against the
    // height, and fills the tables. The legs are counted only when it has ended well.
    core.width = static_cast<uint16_t>(width);
    core.height = static_cast<uint16_t>(height);
    core.leg_count = first.legs;
    Seen second;
    reason = read_once(core, row_check, second);
    if (reason == kNone && (second.legs != first.legs || second.rows != first.rows)) {
        reason = kMappingMalformed;
    }
    if (reason != kNone) {
        core.width = 0;
        core.height = 0;
        core.leg_count = 0;
        return reason;
    }
    core.led_total = leds;
    return kNone;
}

}  // namespace odrig
