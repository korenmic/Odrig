#include "mapping.h"

#include "arena.h"
#include "json_reader.h"
#include "odrg_decoder.h"

namespace odrig {

namespace {

const uint32_t kMostLegs = 255;
const uint32_t kNameSize = 12;

// The two kinds of mapping file: the strips of its legs are rows of the canvas, or columns.
const uint8_t kUnknown = 0;
const uint8_t kRows = 1;
const uint8_t kColumns = 2;

// What one reading of the file has seen so far. A strip is one row of a row leg or one
// column of a column leg, and the length is the number of LEDs in every strip.
struct Seen {
    uint8_t kind;       // the kind of the legs: the first reading finds it, the second is given it
    uint32_t length;
    uint32_t legs;
    uint32_t strips;
    bool starts;        // a leg has `starts`, whose ends the second reading keeps a bit each
};

// Whether strip `at`, a row or a column of the canvas, has been marked before; marks it.
bool mark_strip(uint8_t *strip_check, uint32_t at) {
    uint8_t bit = static_cast<uint8_t>(1u << ((at - 1) & 7));
    uint8_t &byte = strip_check[(at - 1) >> 3];
    bool marked = (byte & bit) != 0;
    byte |= bit;
    return marked;
}

// Reads one entry of `legs`. Every leg is of the kind of the first one. The second reading
// of the file also checks the leg against those before it and its strips against their
// number, and fills the tables by the kind, the width and the height the first reading
// found.
bool read_leg(Core &core, JsonReader &json, uint8_t *strip_check, uint8_t *starts_far, Seen &seen) {
    const bool fill = strip_check != nullptr;
    // For the second reading: the number of LEDs in a strip, and the number of strips of
    // the canvas.
    uint32_t length = 0;
    uint32_t across = 0;
    if (fill) {
        length = seen.kind == kColumns ? core.height : core.width;
        across = seen.kind == kColumns ? core.width : core.height;
    }
    char name[kNameSize];
    uint32_t members = 0;
    uint32_t leg = 0;
    uint32_t pin = 0;
    uint32_t strips = 0;
    uint8_t kind = kUnknown;
    // `first_led` is one of four words: the kind it belongs to, and whether it is the end
    // of a strip where x or y is largest. It may come before `rows` or `columns`, so it is
    // held against the kind of the leg when the leg has ended.
    uint8_t word_kind = kUnknown;
    bool first_far = false;
    // `starts`, one end word for each strip in chain order: the kind of its words, how
    // many there are, and whether the first names the far end. In the second reading each
    // word's far-ness goes to its strip's bit of `starts_far`.
    uint8_t starts_kind = kUnknown;
    uint32_t starts_count = 0;
    bool starts_first_far = false;

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
        } else if (same_text(name, "rows") || same_text(name, "columns")) {
            // One bit for the two: a leg has exactly one of them.
            member = 8;
        } else if (same_text(name, "starts")) {
            member = 16;
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
            char word[8];
            if (!json.string(word, sizeof word)) {
                return false;
            }
            if (same_text(word, "left") || same_text(word, "right")) {
                word_kind = kRows;
                first_far = same_text(word, "right");
            } else if (same_text(word, "bottom") || same_text(word, "top")) {
                word_kind = kColumns;
                first_far = same_text(word, "top");
            } else {
                return false;
            }
        } else if (member == 16) {
            seen.starts = true;
            // The bits of the ends are taken only when the first reading saw a `starts`: a
            // file that has one only at the second reading is not the file read first.
            if (fill && starts_far == nullptr) {
                return false;
            }
            if (!json.array_begin()) {
                return false;
            }
            while (json.array_next()) {
                char word[8];
                if (!json.string(word, sizeof word)) {
                    return false;
                }
                uint8_t kind_of_word;
                bool far;
                if (same_text(word, "left") || same_text(word, "right")) {
                    kind_of_word = kRows;
                    far = same_text(word, "right");
                } else if (same_text(word, "bottom") || same_text(word, "top")) {
                    kind_of_word = kColumns;
                    far = same_text(word, "top");
                } else {
                    return false;
                }
                if (starts_kind == kUnknown) {
                    starts_kind = kind_of_word;
                } else if (starts_kind != kind_of_word) {
                    return false;
                }
                if (starts_count == 0) {
                    starts_first_far = far;
                }
                if (fill) {
                    const uint32_t strip_index = seen.strips + starts_count;
                    if (strip_index >= across) {
                        return false;
                    }
                    if (far) {
                        starts_far[strip_index >> 3] |= static_cast<uint8_t>(1u << (strip_index & 7));
                    }
                }
                if (starts_count < kLargestPicture + 1) {
                    ++starts_count;
                }
            }
            if (json.failed || starts_count == 0) {
                return false;
            }
        } else {
            kind = same_text(name, "rows") ? kRows : kColumns;
            if (seen.kind == kUnknown) {
                seen.kind = kind;
            } else if (seen.kind != kind) {
                return false;
            }
            if (!json.array_begin()) {
                return false;
            }
            while (json.array_next()) {
                uint32_t at;
                if (!json.integer(&at)) {
                    return false;
                }
                if (fill) {
                    if (seen.strips + strips >= across || at < 1 || at > across || mark_strip(strip_check, at)) {
                        return false;
                    }
                    // The strip's y or x waits in the strip's first entry until the end
                    // it starts at is known.
                    core.led_pixel[(seen.strips + strips) * length] = static_cast<uint16_t>(at);
                }
                if (strips < kLargestPicture + 1) {
                    ++strips;
                }
            }
            if (json.failed || strips == 0) {
                return false;
            }
        }
    }
    if (json.failed || (members != 15 && members != 31) || word_kind != kind) {
        return false;
    }
    // With `starts`, one word for each strip, of the leg's kind, the first being `first_led`.
    const bool has_starts = (members & 16) != 0;
    if (has_starts && (starts_count != strips || starts_kind != kind || starts_first_far != first_far)) {
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
        info.first = seen.strips * length;
        info.count = strips * length;
        for (uint32_t s = 0; s < strips; ++s) {
            uint16_t *strip = core.led_pixel + info.first + s * length;
            const uint32_t at = strip[0];
            // The strips of a leg alternate their direction along the chain, unless `starts`
            // names the end each one starts at.
            const uint32_t strip_index = seen.strips + s;
            const bool from_far = has_starts
                ? (starts_far[strip_index >> 3] & static_cast<uint8_t>(1u << (strip_index & 7))) != 0
                : first_far != ((s & 1) != 0);
            for (uint32_t i = 0; i < length; ++i) {
                // Where the LED is along its strip: its x in a row, its y in a column.
                const uint32_t along = from_far ? length - i : 1 + i;
                const uint32_t x = kind == kRows ? along : at;
                const uint32_t y = kind == kRows ? at : along;
                strip[i] = static_cast<uint16_t>((y - 1) * width + (x - 1));
            }
        }
    }
    if (seen.legs <= kMostLegs) {
        ++seen.legs;
    }
    seen.strips += strips;
    if (seen.strips > kLargestPicture + 1) {
        seen.strips = kLargestPicture + 1;
    }
    return true;
}

// Reads the whole file once. False when it breaks a rule that this reading checks.
bool read_file(Core &core, JsonReader &json, uint8_t *strip_check, uint8_t *starts_far, Seen &seen) {
    const bool fill = strip_check != nullptr;
    char name[kNameSize];
    uint32_t members = 0;
    // The kind the top level tells: rows with `width`, columns with `height`. `legs` may
    // come before it, so it is held against the kind of the legs when the object has ended.
    uint8_t top_kind = kUnknown;
    if (!json.object_begin()) {
        return false;
    }
    while (json.object_next(name, sizeof name)) {
        uint32_t member;
        if (same_text(name, "version")) {
            member = 1;
        } else if (same_text(name, "width") || same_text(name, "height")) {
            // One bit for the two: a file has exactly one of them.
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
            top_kind = same_text(name, "width") ? kRows : kColumns;
            if (!json.integer(&seen.length) || seen.length < 1 || seen.length > 65535) {
                return false;
            }
            if (fill && seen.length != (seen.kind == kColumns ? core.height : core.width)) {
                return false;
            }
        } else {
            if (!json.array_begin()) {
                return false;
            }
            while (json.array_next()) {
                if (!read_leg(core, json, strip_check, starts_far, seen)) {
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
    return !json.failed && members == 7 && top_kind == seen.kind && json.end();
}

// Opens the file and reads it once. With `strip_check` and `starts_far` it is the second
// reading, and `kind` is the kind the first reading found.
Reason read_once(Core &core, uint8_t *strip_check, uint8_t *starts_far, uint8_t kind, Seen &seen) {
    seen.kind = kind;
    seen.length = 0;
    seen.legs = 0;
    seen.strips = 0;
    seen.starts = false;
    Reason opened = core.file.open(core.host, "mapping.json");
    if (opened == kFileMissing) {
        return kMappingMissing;
    }
    if (opened != kNone) {
        return kReadError;
    }
    JsonReader json;
    json.start(&core.file);
    bool sound = read_file(core, json, strip_check, starts_far, seen);
    core.file.close();
    if (json.read_failed) {
        return kReadError;
    }
    return sound ? kNone : kMappingMalformed;
}

}  // namespace

Reason read_mapping(Core &core) {
    // The first reading checks the form of the file, finds its kind and counts the legs and
    // the strips. The strips are the rows of a row-leg file and the columns of a column-leg
    // file, so the other side of the canvas is the length of a strip.
    Seen first;
    Reason reason = read_once(core, nullptr, nullptr, kUnknown, first);
    if (reason != kNone) {
        return reason;
    }
    const uint32_t width = first.kind == kColumns ? first.strips : first.length;
    const uint32_t height = first.kind == kColumns ? first.length : first.strips;
    if (static_cast<uint64_t>(width) * height > kLargestPicture) {
        return kMappingMalformed;
    }
    const uint32_t leds = width * height;

    core.legs = static_cast<LegInfo *>(arena_take(core, first.legs * static_cast<uint32_t>(sizeof(LegInfo))));
    core.led_pixel = static_cast<uint16_t *>(arena_take(core, leds * 2));
    core.led_data = static_cast<uint8_t *>(arena_take(core, leds * 3));
    uint8_t *strip_check = static_cast<uint8_t *>(arena_take(core, (first.strips + 7) / 8));
    if (core.legs == nullptr || core.led_pixel == nullptr || core.led_data == nullptr || strip_check == nullptr) {
        return kOutOfMemory;
    }
    // One bit for each strip, whether it starts at its far end, when a leg has `starts`.
    uint8_t *starts_far = nullptr;
    if (first.starts) {
        starts_far = static_cast<uint8_t *>(arena_take(core, (first.strips + 7) / 8));
        if (starts_far == nullptr) {
            return kOutOfMemory;
        }
    }

    // The second reading checks the legs against each other and the strips against their
    // number, and fills the tables. The legs are counted only when it has ended well.
    core.width = static_cast<uint16_t>(width);
    core.height = static_cast<uint16_t>(height);
    core.leg_count = first.legs;
    Seen second;
    reason = read_once(core, strip_check, starts_far, first.kind, second);
    if (reason == kNone && (second.legs != first.legs || second.strips != first.strips)) {
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
