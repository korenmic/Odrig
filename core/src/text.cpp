#include "text.h"

#include <string.h>

#include "fonts.h"

namespace odrig {

namespace {

const uint8_t kStatic = 0;
const uint8_t kMarquee = 1;
const uint8_t kSlide = 2;
const uint8_t kFastest = 240;
const uint16_t kShortestStatic = 20;

uint16_t u16(const uint8_t *bytes) {
    return static_cast<uint16_t>(bytes[0] | (bytes[1] << 8));
}

// The table of a font id and its scale: `small` and `medium` at 1, `large`, which is
// `small`, at 2. False for an id or a version the core does not have.
bool font_of(uint8_t id, uint8_t version, const FontTable **table, int64_t *scale) {
    if (id < 1 || id > 3) {
        return false;
    }
    *table = font_table(id == 3 ? 1 : id);
    *scale = id == 3 ? 2 : 1;
    return *table != nullptr && (*table)->version == version;
}

// The settings of a payload's first bytes, as numbers.
struct Settings {
    uint8_t effect;
    uint8_t motion;
    uint8_t align;
    uint8_t valign;
    int64_t speed;
    int64_t pause;
    int64_t block_width;
    int64_t block_height;
};

Settings settings_of(const uint8_t *fixed) {
    Settings made;
    made.effect = fixed[2];
    made.motion = fixed[3];
    made.align = fixed[4];
    made.valign = fixed[5];
    made.speed = u16(fixed + 14);
    made.pause = u16(fixed + 16);
    made.block_width = u16(fixed + 22);
    made.block_height = u16(fixed + 24);
    return made;
}

bool horizontal(const Settings &settings) {
    return settings.motion < 2;
}

// Where the block rests: by the alignment across, by the vertical alignment down.
void rest(const Settings &settings, int64_t width, int64_t height, int64_t *x, int64_t *y) {
    const int64_t free_x = width - settings.block_width;
    *x = settings.align == 1 ? (free_x >= 0 ? free_x / 2 : -((1 - free_x) / 2)) : settings.align == 2 ? free_x : 0;
    const int64_t free_y = height - settings.block_height;
    *y = settings.valign == 1 ? (free_y >= 0 ? free_y / 2 : -((1 - free_y) / 2)) : settings.valign == 2 ? free_y : 0;
}

bool fits(const Settings &settings, int64_t width, int64_t height) {
    const bool wide = settings.block_width <= width;
    const bool tall = settings.block_height <= height;
    if (settings.effect == kStatic || settings.effect == kSlide) {
        return wide && tall;
    }
    return horizontal(settings) ? tall : wide;
}

// The milliseconds a distance takes at the speed, rounded up, and the pixels moved after
// some milliseconds, rounded down.
int64_t steps(int64_t distance, int64_t speed) {
    return (distance * 1000 + speed - 1) / speed;
}

int64_t moved(int64_t t, int64_t speed) {
    return t * speed / 1000;
}

// The motion along one axis: the canvas's size, the block's length, its rest, and whether
// it goes towards the right or down.
struct Axis {
    int64_t size;
    int64_t length;
    int64_t rest;
    bool forward;
};

Axis axis_of(const Settings &settings, int64_t width, int64_t height) {
    int64_t x;
    int64_t y;
    rest(settings, width, height, &x, &y);
    Axis made;
    if (horizontal(settings)) {
        made.size = width;
        made.length = settings.block_width;
        made.rest = x;
        made.forward = settings.motion == 1;
    } else {
        made.size = height;
        made.length = settings.block_height;
        made.rest = y;
        made.forward = settings.motion == 3;
    }
    return made;
}

// The parts of a pass, in milliseconds: a slide's way in, its hold and its way out; a
// pan's hold and the way between its ends, of `travel` pixels; a marquee's way across.
struct Parts {
    int64_t inward;
    int64_t hold;
    int64_t outward;
    int64_t move;
    int64_t travel;
};

Parts parts_of(const Settings &settings, const Axis &line) {
    Parts made;
    memset(&made, 0, sizeof made);
    made.hold = settings.pause;
    if (settings.effect == kMarquee) {
        made.move = steps(line.size + line.length, settings.speed);
    } else if (settings.effect == kSlide) {
        made.inward = steps(line.forward ? line.rest + line.length : line.size - line.rest, settings.speed);
        made.outward = steps(line.forward ? line.size - line.rest : line.rest + line.length, settings.speed);
    } else if (settings.effect != kStatic) {
        made.travel = line.length > line.size ? line.length - line.size : 0;
        made.move = steps(made.travel, settings.speed);
    }
    return made;
}

int64_t pass_of(const Settings &settings, int64_t width, int64_t height) {
    if (settings.effect == kStatic) {
        return settings.pause;
    }
    const Parts parts = parts_of(settings, axis_of(settings, width, height));
    if (settings.effect == kMarquee) {
        return parts.move;
    }
    if (settings.effect == kSlide) {
        return parts.inward + parts.hold + parts.outward;
    }
    const int64_t pan = 2 * parts.hold + 2 * parts.move;
    return pan > kShortestStatic ? pan : kShortestStatic;
}

int64_t smaller(int64_t a, int64_t b) {
    return a < b ? a : b;
}

int64_t larger(int64_t a, int64_t b) {
    return a > b ? a : b;
}

// The block's top left corner on the canvas `t` milliseconds into the pass, rows counted
// from the top.
void place_at(const Settings &settings, int64_t width, int64_t height, int64_t t, int64_t *x, int64_t *y) {
    rest(settings, width, height, x, y);
    if (settings.effect == kStatic) {
        return;
    }
    const Axis line = axis_of(settings, width, height);
    const Parts parts = parts_of(settings, line);
    const int64_t speed = settings.speed;
    int64_t place;
    if (settings.effect == kMarquee) {
        place = line.forward ? -line.length + moved(t, speed) : line.size - moved(t, speed);
    } else if (settings.effect == kSlide) {
        if (t < parts.inward) {
            place = line.forward ? smaller(line.rest, -line.length + moved(t, speed)) : larger(line.rest, line.size - moved(t, speed));
        } else if (t < parts.inward + parts.hold) {
            place = line.rest;
        } else {
            const int64_t out = moved(t - parts.inward - parts.hold, speed);
            place = line.forward ? line.rest + out : line.rest - out;
        }
    } else {
        const int64_t from = parts.travel == 0 ? line.rest : line.forward ? line.size - line.length : 0;
        const int64_t sign = line.forward ? 1 : -1;
        const int64_t far = from + sign * parts.travel;
        if (t < parts.hold) {
            place = from;
        } else if (t < parts.hold + parts.move) {
            place = from + sign * smaller(parts.travel, moved(t - parts.hold, speed));
        } else if (t < 2 * parts.hold + parts.move) {
            place = far;
        } else {
            place = far - sign * smaller(parts.travel, moved(t - 2 * parts.hold - parts.move, speed));
        }
    }
    if (horizontal(settings)) {
        *x = place;
    } else {
        *y = place;
    }
}

// The next byte of the payload, or why there is none.
Reason take(FileSource *file, uint8_t *byte) {
    const int got = file->get();
    if (got >= 0) {
        *byte = static_cast<uint8_t>(got);
        return kNone;
    }
    return got == -kReadError ? kReadError : kTruncated;
}

// UTF-8 as the standard has it, one byte after the other.
struct Utf8 {
    uint8_t need;
    uint8_t low;
    uint8_t high;

    bool feed(uint8_t byte) {
        if (need != 0) {
            if (byte < low || byte > high) {
                return false;
            }
            --need;
            low = 0x80;
            high = 0xBF;
            return true;
        }
        low = 0x80;
        high = 0xBF;
        if (byte <= 0x7F) {
            return true;
        }
        if (byte >= 0xC2 && byte <= 0xDF) {
            need = 1;
        } else if (byte == 0xE0) {
            need = 2;
            low = 0xA0;
        } else if ((byte >= 0xE1 && byte <= 0xEC) || byte == 0xEE || byte == 0xEF) {
            need = 2;
        } else if (byte == 0xED) {
            need = 2;
            high = 0x9F;
        } else if (byte == 0xF0) {
            need = 3;
            low = 0x90;
        } else if (byte >= 0xF1 && byte <= 0xF3) {
            need = 3;
        } else if (byte == 0xF4) {
            need = 3;
            high = 0x8F;
        } else {
            return false;
        }
        return true;
    }
};

}  // namespace

Reason text_read(FileSource *file, const ContentHeader &header, uint8_t *into) {
    const int64_t width = header.width;
    const int64_t height = header.height;
    if (3 * width * height > kLargestDrawn) {
        return kCanvasTooLarge;
    }
    uint8_t fixed[kTextSettingsSize];
    for (uint32_t at = 0; at < kTextSettingsSize; ++at) {
        const Reason reason = take(file, &fixed[at]);
        if (reason != kNone) {
            return reason;
        }
    }
    const FontTable *table = nullptr;
    int64_t scale = 1;
    if (!font_of(fixed[0], fixed[1], &table, &scale)) {
        return kUnknownFont;
    }
    if (fixed[2] > 3 || fixed[3] > 3 || fixed[4] > 2 || fixed[5] > 2 || fixed[6] > 2 || fixed[7] > 1) {
        return kBadSettings;
    }
    const Settings settings = settings_of(fixed);
    if (settings.speed < 1 || settings.speed > kFastest || (settings.effect == kStatic && settings.pause < kShortestStatic)) {
        return kBadSettings;
    }
    const uint32_t text_bytes = u16(fixed + 18);
    if (text_bytes < 1 || text_bytes > kLargestText) {
        return kBadText;
    }
    const uint32_t glyphs = u16(fixed + 20);
    if (glyphs > kMostGlyphs || settings.block_width == 0 || settings.block_height == 0 || u16(fixed + 26) != 0) {
        return kBadSettings;
    }
    if (header.payload != kTextSettingsSize + text_bytes + kGlyphSize * glyphs) {
        return kPayloadSize;
    }
    if (!fits(settings, width, height)) {
        return kDoesNotFit;
    }
    if (into != nullptr) {
        memcpy(into, fixed, kTextSettingsSize);
    }
    Utf8 utf8 = {0, 0x80, 0xBF};
    for (uint32_t at = 0; at < text_bytes; ++at) {
        uint8_t byte = 0;
        const Reason reason = take(file, &byte);
        if (reason != kNone) {
            return reason;
        }
        if (!utf8.feed(byte)) {
            return kBadText;
        }
        if (into != nullptr) {
            into[kTextSettingsSize + at] = byte;
        }
    }
    if (utf8.need != 0) {
        return kBadText;
    }
    const uint32_t rows = static_cast<uint32_t>(table->ascent) + table->descent;
    for (uint32_t one = 0; one < glyphs; ++one) {
        uint8_t bytes[kGlyphSize];
        for (uint32_t at = 0; at < kGlyphSize; ++at) {
            const Reason reason = take(file, &bytes[at]);
            if (reason != kNone) {
                return reason;
            }
        }
        const uint32_t glyph = u16(bytes);
        const int64_t x = u16(bytes + 2);
        const int64_t y = u16(bytes + 4);
        if (glyph >= table->count || x + table->widths[glyph] * scale > settings.block_width ||
            y + static_cast<int64_t>(rows) * scale > settings.block_height) {
            return kBadGlyph;
        }
        if (into != nullptr) {
            memcpy(into + kTextSettingsSize + text_bytes + kGlyphSize * one, bytes, kGlyphSize);
        }
    }
    const int after = file->get();
    if (after == -kReadError) {
        return kReadError;
    }
    if (after != -kEnd) {
        return kTrailingBytes;
    }
    return static_cast<uint64_t>(pass_of(settings, width, height)) == header.loop_ms ? kNone : kLoopMismatch;
}

uint64_t text_pass(const uint8_t *payload, uint16_t width, uint16_t height) {
    return static_cast<uint64_t>(pass_of(settings_of(payload), width, height));
}

void text_draw(const uint8_t *payload, uint16_t width, uint16_t height, uint64_t t, uint8_t *pixels) {
    const Settings settings = settings_of(payload);
    const FontTable *table = nullptr;
    int64_t scale = 1;
    font_of(payload[0], payload[1], &table, &scale);
    const uint8_t *colour = payload + 8;
    const uint8_t *background = payload + 11;
    const uint32_t count = static_cast<uint32_t>(width) * height;
    for (uint32_t pixel = 0; pixel < count; ++pixel) {
        memcpy(pixels + 3 * pixel, background, 3);
    }
    int64_t left;
    int64_t top;
    place_at(settings, width, height, static_cast<int64_t>(t), &left, &top);
    const uint32_t text_bytes = u16(payload + 18);
    const uint32_t glyphs = u16(payload + 20);
    const uint8_t *glyph_at = payload + kTextSettingsSize + text_bytes;
    const uint32_t rows = static_cast<uint32_t>(table->ascent) + table->descent;
    for (uint32_t one = 0; one < glyphs; ++one, glyph_at += kGlyphSize) {
        const uint32_t glyph = u16(glyph_at);
        const int64_t cell_x = left + u16(glyph_at + 2);
        const int64_t cell_y = top + u16(glyph_at + 4);
        const int64_t glyph_width = table->widths[glyph];
        if (cell_x >= width || cell_y >= height || cell_x + glyph_width * scale <= 0 || cell_y + static_cast<int64_t>(rows) * scale <= 0) {
            continue;
        }
        for (uint32_t row = 0; row < rows; ++row) {
            const uint8_t bits = table->rows[glyph * rows + row];
            for (int64_t column = 0; bits != 0 && column < glyph_width; ++column) {
                if ((bits & (0x80 >> column)) == 0) {
                    continue;
                }
                for (int64_t down = 0; down < scale; ++down) {
                    for (int64_t across = 0; across < scale; ++across) {
                        const int64_t x = cell_x + column * scale + across;
                        const int64_t y = cell_y + static_cast<int64_t>(row) * scale + down;
                        if (x >= 0 && x < width && y >= 0 && y < height) {
                            memcpy(pixels + 3 * ((height - 1 - y) * width + x), colour, 3);
                        }
                    }
                }
            }
        }
    }
}

}  // namespace odrig
