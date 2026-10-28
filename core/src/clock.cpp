#include "clock.h"

#include <string.h>

#include "fonts.h"
#include "text.h"

namespace odrig {

namespace {

// Positions are in half pixels from the canvas's centre, with y growing downwards; angles
// in 1/2^26 of a turn, from 12 o'clock clockwise; sines in units of 1/16,384.
const int64_t kHalfDay = 43200000;
const int64_t kHour = 3600000;
const int64_t kMinute = 60000;
const int64_t kTurn = 67108864;
const int64_t kStep = 65536;
const int64_t kOne = 16384;
// 2 pi times 16,384, rounded.
const int64_t kTwoPi = 102944;
const uint16_t kLongestClock = 3600;
const uint16_t kFastestClock = 3600;
const uint8_t kAnalog = 1;
const uint8_t kDigital = 2;
// The parts of a dial, and what is drawn of each in which colour of the settings.
const uint8_t kNothing = 0;
const uint8_t kFace = 1;
const uint8_t kRim = 2;
const uint8_t kHands = 3;
// The hour hand, the minute hand and the twelve marks.
const uint32_t kStrokes = 14;
const uint8_t kPictureDial = 4;
const uint8_t kPictureDisplay = 5;
const uint32_t kPictureHead = 12;
const uint32_t kHandSize = 10;
const uint32_t kCapSize = 6;
const uint32_t kFieldSize = 22;
const uint8_t kMostHands = 8;
const uint8_t kMostCaps = 4;
const uint8_t kMostFields = 4;
const uint8_t kMostColours = 8;
const uint8_t kMostTurns = 100;
const uint8_t kWidestHand = 15;
const int64_t kLargestOffset = 12;
const uint8_t kRandom = 2;
// The margin, in half pixels, beyond which no pixel can be a hand's whatever the table's
// sines: they are within a few parts in a million of a whole turn's.
const int64_t kHandMargin = 2;


uint16_t u16(const uint8_t *bytes) {
    return static_cast<uint16_t>(bytes[0] | (bytes[1] << 8));
}

// Floor division of whole numbers by a positive one.
int64_t fdiv(int64_t x, int64_t y) {
    int64_t q = x / y;
    if (x % y != 0 && x < 0) {
        --q;
    }
    return q;
}

int64_t fmod(int64_t x, int64_t y) {
    return x - fdiv(x, y) * y;
}

int64_t smaller(int64_t a, int64_t b) {
    return a < b ? a : b;
}

int64_t magnitude(int64_t a) {
    return a < 0 ? -a : a;
}

int64_t signed_byte(uint8_t byte) {
    return byte >= 128 ? static_cast<int64_t>(byte) - 256 : byte;
}

// The characters of a field's pattern, and the time of one turn of a hand of each unit:
// the hour's, the minute's and the second's.
const char kPatternCharacters[] = "HIhMmSs: ";
const int64_t kUnits[3] = {kHalfDay, kHour, kMinute};

// Whether a byte is a character of a field's pattern.
bool pattern_character(uint8_t byte) {
    for (uint32_t at = 0; at + 1 < sizeof kPatternCharacters; ++at) {
        if (byte == static_cast<uint8_t>(kPatternCharacters[at])) {
            return true;
        }
    }
    return false;
}

bool is_picture(uint8_t widget) {
    return widget == kPictureDial || widget == kPictureDisplay;
}

// The offsets of a widget's least and greatest speed.
uint32_t speeds_at(const uint8_t *payload) {
    return is_picture(payload[0]) ? 4 : 16;
}

// MurmurHash3's finalizer.
uint32_t mix(uint32_t h) {
    h ^= h >> 16;
    h *= 0x85ebca6bu;
    h ^= h >> 13;
    h *= 0xc2b2ae35u;
    h ^= h >> 16;
    return h;
}

uint32_t xorshift(uint32_t x) {
    x ^= x << 13;
    x ^= x >> 17;
    x ^= x << 5;
    return x;
}

// What a seed chooses, in this order from xorshift32: the start of the virtual time, its
// base speed, the swing of the speed about it, the swing's period and its phase; then the
// melting watch's tilt in degrees, where it folds, as a percentage of its radius below its
// centre, how far the hanging face stretches and how fast it narrows, in percent, its shear
// and the wave of the fold in half pixels; then whether a picture clock's turn of a random
// way starts backward, and its chance of turning at each slowest point, in percent.
struct Clock {
    int32_t start;
    int32_t base;
    int32_t swing;
    int32_t period;
    int32_t phase;
    int32_t tilt;
    int32_t fold;
    int32_t stretch;
    int32_t narrow;
    int32_t shear;
    int32_t wave;
    int32_t back;
    int32_t chance;
};

Clock clock_of(const uint8_t *payload, uint32_t seed) {
    uint32_t state = seed == 0 ? 1 : seed;
    Clock made;
    state = xorshift(state);
    made.start = static_cast<int32_t>(state % kHalfDay);
    const int64_t least = u16(payload + speeds_at(payload));
    const int64_t greatest = u16(payload + speeds_at(payload) + 2);
    state = xorshift(state);
    const int64_t base = least + state % (greatest - least + 1);
    made.base = static_cast<int32_t>(base);
    state = xorshift(state);
    made.swing = static_cast<int32_t>(fdiv(smaller(base - least, greatest - base) * (state % 101), 102));
    state = xorshift(state);
    made.period = static_cast<int32_t>(6000 + state % 14001);
    state = xorshift(state);
    made.phase = static_cast<int32_t>(state % 1024);
    state = xorshift(state);
    made.tilt = static_cast<int32_t>(25 + state % 16);
    state = xorshift(state);
    made.fold = static_cast<int32_t>(state % 21);
    state = xorshift(state);
    made.stretch = static_cast<int32_t>(130 + state % 41);
    state = xorshift(state);
    made.narrow = static_cast<int32_t>(20 + state % 31);
    state = xorshift(state);
    made.shear = static_cast<int32_t>(10 + state % 21);
    state = xorshift(state);
    made.wave = static_cast<int32_t>(2 + state % 3);
    state = xorshift(state);
    made.back = static_cast<int32_t>(state % 2);
    state = xorshift(state);
    const uint32_t turns = is_picture(payload[0]) ? payload[9] : 0;
    made.chance = static_cast<int32_t>(state % (turns + 1));
    return made;
}

// The sine of an angle from the table, read between its entries in steps of 1/65,536.
int64_t sine(int64_t angle) {
    const int64_t at = fmod(angle, kTurn);
    const int64_t index = at / kStep;
    const int64_t low = kSine[index];
    const int64_t high = kSine[(index + 1) % kSineEntries];
    return low + fdiv((high - low) * (at % kStep), kStep);
}

int64_t cosine(int64_t angle) {
    return sine(angle + kTurn / 4);
}

int64_t virtual_time(const Clock &clock, int64_t t) {
    const int64_t period = clock.period;
    const int64_t turned = fdiv(kTurn * (t % period), period);
    const int64_t from = clock.phase * kStep;
    const int64_t swing = clock.swing;
    const int64_t swung = fdiv(swing * period * (cosine(from) - cosine(from + turned)), kTwoPi);
    const int64_t base = clock.base;
    return clock.start + base * t + swung;
}

// A straight part of a dial: its direction and the band along it that is drawn. A dial's
// radius is below 150 half pixels, as a canvas that is drawn on has at most 65,534 bytes.
struct Stroke {
    int16_t x;
    int16_t y;
    int16_t from;
    int16_t to;
    int16_t half;
};

void add(Stroke *stroke, int64_t angle, int64_t from, int64_t to, int64_t half) {
    stroke->x = static_cast<int16_t>(sine(angle));
    stroke->y = static_cast<int16_t>(-cosine(angle));
    stroke->from = static_cast<int16_t>(from);
    stroke->to = static_cast<int16_t>(to);
    stroke->half = static_cast<int16_t>(half);
}

// The hour hand, the minute hand and the twelve marks of a dial of a radius.
void strokes_of(int64_t time, int64_t radius, Stroke *made) {
    add(&made[0], fdiv(kTurn * (time % kHalfDay), kHalfDay), 0, fdiv(radius * 55, 100), 2);
    add(&made[1], fdiv(kTurn * (time % kHour), kHour), 0, fdiv(radius * 85, 100), 1);
    const int64_t outer = radius - 6;
    const int64_t inner = outer - fdiv(radius, 7);
    for (int64_t mark = 0; mark < 12; ++mark) {
        add(&made[2 + mark], fdiv(mark * kTurn, 12), inner, outer, 1);
    }
}

// What a point of a dial is: nothing outside its disc, the rim, the pivot, a hand or a mark,
// or the face. Where the canvas shows the dial narrower, `wide` percent widens the strokes
// so that none falls between the pixels.
uint8_t dial_at(int64_t u, int64_t w, int64_t radius, const Stroke *made, int64_t wide) {
    const int64_t distance = u * u + w * w;
    if (distance > radius * radius) {
        return kNothing;
    }
    if (distance > (radius - 4) * (radius - 4)) {
        return kRim;
    }
    if (distance <= 16) {
        return kHands;
    }
    for (uint32_t one = 0; one < kStrokes; ++one) {
        const Stroke &stroke = made[one];
        const int64_t along = u * stroke.x + w * stroke.y;
        if (along < stroke.from * kOne || along > stroke.to * kOne) {
            continue;
        }
        if (100 * magnitude(u * stroke.y - w * stroke.x) <= stroke.half * kOne * wide) {
            return kHands;
        }
    }
    return kFace;
}

void put(uint8_t *pixels, int64_t width, int64_t height, int64_t x, int64_t y, const uint8_t *colour) {
    memcpy(pixels + 3 * ((height - 1 - y) * width + x), colour, 3);
}

// The radius of the largest dial the canvas holds, in half pixels, a pixel from its edge.
int64_t dial_radius(int64_t width, int64_t height) {
    return 2 * (smaller(width, height) / 2 - 1);
}

// Where the payload has the colour of each part of a dial: the background, the face, the
// rim, the hands.
const uint8_t kColourAt[4] = {13, 4, 10, 7};

const uint8_t *colour_of(const uint8_t *payload, uint8_t part) {
    return payload + kColourAt[part];
}

void draw_analog(const uint8_t *payload, int64_t time, int64_t width, int64_t height, uint8_t *pixels) {
    const int64_t radius = dial_radius(width, height);
    Stroke made[kStrokes];
    strokes_of(time, radius, made);
    for (int64_t y = 0; y < height; ++y) {
        for (int64_t x = 0; x < width; ++x) {
            const uint8_t part = radius > 0 ? dial_at(2 * x + 1 - width, 2 * y + 1 - height, radius, made, 100) : kNothing;
            put(pixels, width, height, x, y, colour_of(payload, part));
        }
    }
}

// The place of a character in the small font's table.
uint32_t glyph_of(const FontTable *table, uint16_t code) {
    uint32_t low = 0;
    uint32_t high = table->count;
    while (low + 1 < high) {
        const uint32_t middle = (low + high) / 2;
        if (table->codes[middle] <= code) {
            low = middle;
        } else {
            high = middle;
        }
    }
    return low;
}

// The digital clock: h:mm in the large font, centred, the colon shown in the first half of
// each real second.
void draw_digital(const uint8_t *payload, int64_t time, int64_t t, int64_t width, int64_t height, uint8_t *pixels) {
    for (int64_t y = 0; y < height; ++y) {
        for (int64_t x = 0; x < width; ++x) {
            put(pixels, width, height, x, y, payload + 13);
        }
    }
    const FontTable *table = font_table(1);
    const int64_t scale = 2;
    const int64_t rows = static_cast<int64_t>(table->ascent) + table->descent;
    int64_t hour = time / kHour % 12;
    if (hour == 0) {
        hour = 12;
    }
    const int64_t minute = time / kMinute % 60;
    char shown[5];
    uint32_t count = 0;
    if (hour >= 10) {
        shown[count++] = static_cast<char>('0' + hour / 10);
    }
    shown[count++] = static_cast<char>('0' + hour % 10);
    shown[count++] = ':';
    shown[count++] = static_cast<char>('0' + minute / 10);
    shown[count++] = static_cast<char>('0' + minute % 10);
    uint32_t glyphs[5];
    int64_t block = -scale;
    for (uint32_t at = 0; at < count; ++at) {
        glyphs[at] = glyph_of(table, static_cast<uint16_t>(shown[at]));
        block += (table->widths[glyphs[at]] + 1) * scale;
    }
    int64_t left = fdiv(width - block, 2);
    const int64_t top = fdiv(height - rows * scale, 2);
    const bool colon = t % 1000 < 500;
    for (uint32_t at = 0; at < count; ++at) {
        const uint32_t glyph = glyphs[at];
        const bool is_colon = shown[at] == ':';
        const uint8_t *colour = payload + (is_colon ? 10 : 4);
        for (int64_t row = 0; (!is_colon || colon) && row < rows; ++row) {
            const uint8_t bits = table->rows[glyph * rows + row];
            for (int64_t column = 0; column < table->widths[glyph]; ++column) {
                if ((bits & (0x80 >> column)) == 0) {
                    continue;
                }
                for (int64_t down = 0; down < scale; ++down) {
                    for (int64_t across = 0; across < scale; ++across) {
                        const int64_t x = left + column * scale + across;
                        const int64_t y = top + row * scale + down;
                        if (x >= 0 && x < width && y >= 0 && y < height) {
                            put(pixels, width, height, x, y, colour);
                        }
                    }
                }
            }
        }
        left += (table->widths[glyph] + 1) * scale;
    }
}

// The time a picture widget shows `t` milliseconds into its turn, not taken modulo 12
// hours: the way forward of the other clocks, gone forward or back as its direction says,
// and with a random way turned at the swing's slowest points as the seed says.
int64_t picture_time(const uint8_t *payload, const Clock &clock, uint32_t seed, int64_t t) {
    const bool random = payload[8] == kRandom;
    int64_t way = payload[8] == 1 || (random && clock.back == 1) ? -1 : 1;
    const int64_t period = clock.period;
    const int64_t first = fdiv(period * fmod(3 * (kTurn / 4) - clock.phase * kStep, kTurn), kTurn);
    const int64_t start = clock.start;
    if (t < first) {
        return start + way * (virtual_time(clock, t) - start);
    }
    const int64_t passed = fdiv(t - first, period) + 1;
    const int64_t round = static_cast<int64_t>(clock.base) * period;
    const uint32_t chosen = seed == 0 ? 1 : seed;
    const int64_t at_first = virtual_time(clock, first) - start;
    int64_t gone = way * at_first;
    for (int64_t point = 1; point <= passed; ++point) {
        if (random && mix(chosen ^ static_cast<uint32_t>(point)) % 100 < static_cast<uint32_t>(clock.chance)) {
            way = -way;
        }
        if (point < passed) {
            gone += way * round;
        }
    }
    return start + gone + way * (virtual_time(clock, t) - start - at_first - (passed - 1) * round);
}

int64_t part_time(int64_t time, int64_t offset) {
    return fmod(time + offset * kHour, kHalfDay);
}

void mark(uint8_t *layer, int64_t width, int64_t height, int64_t x, int64_t y, uint8_t colour) {
    layer[(height - 1 - y) * width + x] = static_cast<uint8_t>(colour + 1);
}

// The columns or rows of pixels whose centres lie within `reach` half pixels of a place.
void span(int64_t place, int64_t reach, int64_t size, int64_t *from, int64_t *to) {
    *from = fdiv(place - reach, 2);
    *to = fdiv(place + reach, 2);
    if (*from < 0) {
        *from = 0;
    }
    if (*to > size - 1) {
        *to = size - 1;
    }
}

void draw_hand(const uint8_t *hand, int64_t time, int64_t width, int64_t height, uint8_t *layer) {
    const int64_t unit = kUnits[hand[0]];
    const int64_t angle = fdiv(kTurn * fmod(part_time(time, signed_byte(hand[9])), unit), unit);
    const int64_t across = sine(angle);
    const int64_t down = -cosine(angle);
    const int64_t px = u16(hand + 2);
    const int64_t py = u16(hand + 4);
    const int64_t length = hand[6];
    const int64_t tail = hand[7];
    const int64_t half = hand[8];
    const int64_t reach = (length > tail ? length : tail) + half + kHandMargin;
    int64_t x0, x1, y0, y1;
    span(px, reach, width, &x0, &x1);
    span(py, reach, height, &y0, &y1);
    for (int64_t y = y0; y <= y1; ++y) {
        for (int64_t x = x0; x <= x1; ++x) {
            const int64_t u = 2 * x + 1 - px;
            const int64_t w = 2 * y + 1 - py;
            const int64_t along = u * across + w * down;
            if (along < -tail * kOne || along > length * kOne) {
                continue;
            }
            if (magnitude(u * down - w * across) <= half * kOne) {
                mark(layer, width, height, x, y, hand[1]);
            }
        }
    }
}

void draw_cap(const uint8_t *cap, int64_t width, int64_t height, uint8_t *layer) {
    const int64_t px = u16(cap);
    const int64_t py = u16(cap + 2);
    const int64_t radius = cap[4];
    int64_t x0, x1, y0, y1;
    span(px, radius, width, &x0, &x1);
    span(py, radius, height, &y0, &y1);
    for (int64_t y = y0; y <= y1; ++y) {
        for (int64_t x = x0; x <= x1; ++x) {
            const int64_t u = 2 * x + 1 - px;
            const int64_t w = 2 * y + 1 - py;
            if (u * u + w * w <= radius * radius) {
                mark(layer, width, height, x, y, cap[5]);
            }
        }
    }
}

// The characters a field's pattern shows at a time of day; at most 8.
uint32_t pattern_text(const uint8_t *pattern, int64_t time, char *shown) {
    int64_t hour = time / kHour % 12;
    if (hour == 0) {
        hour = 12;
    }
    const int64_t minute = time / kMinute % 60;
    const int64_t second = time / 1000 % 60;
    uint32_t count = 0;
    for (uint32_t at = 0; at < 8 && pattern[at] != 0; ++at) {
        const char character = static_cast<char>(pattern[at]);
        if (character == 'H') shown[count++] = static_cast<char>('0' + hour / 10);
        else if (character == 'I') { if (hour >= 10) shown[count++] = '1'; }
        else if (character == 'h') shown[count++] = static_cast<char>('0' + hour % 10);
        else if (character == 'M') shown[count++] = static_cast<char>('0' + minute / 10);
        else if (character == 'm') shown[count++] = static_cast<char>('0' + minute % 10);
        else if (character == 'S') shown[count++] = static_cast<char>('0' + second / 10);
        else if (character == 's') shown[count++] = static_cast<char>('0' + second % 10);
        else shown[count++] = character;
    }
    return count;
}

void draw_field(const uint8_t *field, int64_t time, int64_t t, int64_t width, int64_t height, uint8_t *layer) {
    const int64_t box_left = u16(field);
    const int64_t box_top = u16(field + 2);
    const int64_t box_width = u16(field + 4);
    const int64_t box_height = u16(field + 6);
    const uint8_t font = field[8];
    const FontTable *table = font_table(font == 3 ? 1 : font);
    const int64_t scale = font == 3 ? 2 : 1;
    char shown[8];
    const uint32_t count = pattern_text(field + 14, part_time(time, signed_byte(field[12])), shown);
    uint32_t glyphs[8];
    int64_t line = -scale;
    for (uint32_t at = 0; at < count; ++at) {
        glyphs[at] = glyph_of(table, static_cast<uint16_t>(static_cast<uint8_t>(shown[at])));
        line += (table->widths[glyphs[at]] + 1) * scale;
    }
    int64_t left = box_left + fdiv(box_width - line, 2);
    const int64_t top = box_top + fdiv(box_height - static_cast<int64_t>(table->ascent) * scale, 2);
    const int64_t rows = static_cast<int64_t>(table->ascent) + table->descent;
    const bool colon = field[11] == 0 || t % 1000 < 500;
    for (uint32_t at = 0; at < count; ++at) {
        const uint32_t glyph = glyphs[at];
        const bool is_colon = shown[at] == ':';
        const uint8_t colour = is_colon ? field[10] : field[9];
        for (int64_t row = 0; (!is_colon || colon) && row < rows; ++row) {
            const uint8_t bits = table->rows[glyph * rows + row];
            for (int64_t column = 0; column < table->widths[glyph]; ++column) {
                if ((bits & (0x80 >> column)) == 0) {
                    continue;
                }
                for (int64_t down = 0; down < scale; ++down) {
                    for (int64_t across = 0; across < scale; ++across) {
                        const int64_t x = left + column * scale + across;
                        const int64_t y = top + row * scale + down;
                        if (x >= box_left && x < box_left + box_width && y >= box_top && y < box_top + box_height) {
                            mark(layer, width, height, x, y, colour);
                        }
                    }
                }
            }
        }
        left += (table->widths[glyph] + 1) * scale;
    }
}

// The melting watch. Its dial is drawn as the analog clock's, smaller, tilted, and folded:
// above the fold it lies flat; below it the face hangs straight down, stretched, narrowing
// towards a drip, and darker the deeper it hangs. The fold waves with the real time. A
// crown and a ring sit at the top of the rim.
void draw_melting(const uint8_t *payload, const Clock &clock, int64_t time, int64_t t, int64_t width, int64_t height,
                  uint8_t *pixels) {
    const int64_t whole = dial_radius(width, height);
    const int64_t radius = fdiv(whole * 66, 100);
    Stroke made[kStrokes];
    strokes_of(time, radius, made);
    const int64_t tilt = fdiv(static_cast<int64_t>(clock.tilt) * kTurn, 360);
    const int64_t c = cosine(tilt);
    const int64_t s = sine(tilt);
    const int64_t centre_x = -fdiv(whole * 6, 100);
    const int64_t centre_y = -fdiv(whole * 12, 100);
    const int64_t fold_at = fdiv(radius * clock.fold, 100);
    const int64_t phase = fdiv(kTurn * (t % 7000), 7000);
    const int64_t ring = radius + 9;
    for (int64_t y = 0; y < height; ++y) {
        for (int64_t x = 0; x < width; ++x) {
            uint8_t colour[3];
            memcpy(colour, payload + 13, 3);
            if (radius > 4) {
                const int64_t dx = 2 * x + 1 - width - centre_x;
                const int64_t dy = 2 * y + 1 - height - centre_y;
                // The place along the fold above this pixel, and the fold's height there.
                const int64_t guess = fdiv(dx * kOne - fold_at * s, c);
                const int64_t fold = fold_at + fdiv(static_cast<int64_t>(clock.wave) * sine(fdiv(guess * kTurn, 2 * radius) + phase), kOne);
                const int64_t along = fdiv(dx * kOne - fold * s, c);
                const int64_t fold_y = fdiv(fold * c - along * s, kOne);
                int64_t u;
                int64_t w;
                int64_t shade = 256;
                int64_t wide = 100;
                if (dy <= fold_y) {
                    u = fdiv(dx * c - dy * s, kOne);
                    w = fdiv(dx * s + dy * c, kOne);
                } else {
                    const int64_t deep = dy - fold_y;
                    const int64_t narrowed = radius + fdiv(deep * clock.narrow, 100);
                    w = fold + fdiv(deep * 100, clock.stretch);
                    u = fdiv((along - fdiv(deep * clock.shear, 100)) * narrowed, radius);
                    wide = fdiv(100 * narrowed, radius);
                    shade = deep <= 2 ? 150 : 256 - smaller(140, fdiv(deep * 140, radius));
                }
                uint8_t part = dial_at(u, w, radius, made, wide);
                if (part == kNothing && dy <= fold_y) {
                    const int64_t to_ring = u * u + (w + ring) * (w + ring);
                    if ((magnitude(u) <= 2 && w < 0 && w >= -(radius + 5)) || (to_ring >= 9 && to_ring <= 36)) {
                        part = kRim;
                    }
                }
                if (part != kNothing) {
                    const uint8_t *chosen = colour_of(payload, part);
                    for (uint32_t channel = 0; channel < 3; ++channel) {
                        colour[channel] = static_cast<uint8_t>(chosen[channel] * shade / 256);
                    }
                }
            }
            put(pixels, width, height, x, y, colour);
        }
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

// Reads the bytes of a picture widget's parts after its head, each checked as it is read,
// into `head`; gives the greatest colour they name in `highest`.
Reason parts_read(FileSource *file, const ContentHeader &header, uint8_t *head, uint32_t *size, uint8_t *highest) {
    const bool dial = head[0] == kPictureDial;
    const uint32_t parts = head[10];
    const uint32_t caps = head[11];
    const uint32_t width = 2u * header.width;
    const uint32_t height = 2u * header.height;
    for (uint32_t one = 0; one < parts + caps; ++one) {
        const bool cap = one >= parts;
        const uint32_t bytes = !dial ? kFieldSize : cap ? kCapSize : kHandSize;
        uint8_t *part = head + *size;
        for (uint32_t at = 0; at < bytes; ++at) {
            const Reason reason = take(file, &part[at]);
            if (reason != kNone) {
                return reason;
            }
        }
        *size += bytes;
        if (dial && !cap) {
            if (part[0] > 2 || u16(part + 2) > width || u16(part + 4) > height || part[6] < 1 || part[8] < 1 ||
                part[8] > kWidestHand || magnitude(signed_byte(part[9])) > kLargestOffset) {
                return kBadSettings;
            }
            *highest = part[1] > *highest ? part[1] : *highest;
        } else if (cap) {
            if (u16(part) > width || u16(part + 2) > height || part[4] < 1) {
                return kBadSettings;
            }
            *highest = part[5] > *highest ? part[5] : *highest;
        } else {
            const uint32_t left = u16(part);
            const uint32_t top = u16(part + 2);
            const uint32_t wide = u16(part + 4);
            const uint32_t high = u16(part + 6);
            if (wide < 1 || high < 1 || left + wide > header.width || top + high > header.height) {
                return kBadSettings;
            }
            if (part[8] < 1 || part[8] > 4) {
                return kUnknownFont;
            }
            *highest = part[9] > *highest ? part[9] : *highest;
            *highest = part[10] > *highest ? part[10] : *highest;
            if (part[11] > 1 || magnitude(signed_byte(part[12])) > kLargestOffset || part[13] != 0) {
                return kBadSettings;
            }
            if (part[14] == 0) {
                return kBadSettings;
            }
            for (uint32_t at = 14; at < kFieldSize; ++at) {
                if (part[at] == 0) {
                    continue;
                }
                if ((at > 14 && part[at - 1] == 0) || !pattern_character(part[at])) {
                    return kBadSettings;
                }
            }
        }
    }
    return kNone;
}

// Reads a picture clock on from its first byte, in `head`: its head, its parts, its
// picture with the decoder of `picture`, the end and the loop; keeps the head and the parts
// in `into` when that is given.
Reason picture_read(FileSource *file, const ContentHeader &header, uint8_t *head, uint8_t *into, const Picture &picture) {
    for (uint32_t at = 1; at < kPictureHead; ++at) {
        const Reason reason = take(file, &head[at]);
        if (reason != kNone) {
            return reason;
        }
    }
    const uint16_t seconds = u16(head + 2);
    const uint16_t least = u16(head + 4);
    const uint16_t greatest = u16(head + 6);
    if (head[1] != 0 || seconds < 1 || seconds > kLongestClock || least < 1 || least > kFastestClock || greatest < least ||
        greatest > kFastestClock || head[8] > kRandom || head[9] > kMostTurns || (head[8] != kRandom && head[9] != 0)) {
        return kBadSettings;
    }
    const bool dial = head[0] == kPictureDial;
    if (head[10] < 1 || head[10] > (dial ? kMostHands : kMostFields) || head[11] > (dial ? kMostCaps : 0)) {
        return kBadSettings;
    }
    uint32_t size = kPictureHead;
    uint8_t highest = 0;
    Reason reason = parts_read(file, header, head, &size, &highest);
    if (reason != kNone) {
        return reason;
    }
    OdrgDecoder &decoder = *picture.decoder;
    reason = decoder.open(file, picture.inflate, picture.window);
    if (reason != kNone) {
        return reason;
    }
    if (decoder.width != header.width || decoder.height != header.height) {
        return kCanvasMismatch;
    }
    if (decoder.frames != 1 || decoder.colours < 1 || decoder.colours > kMostColours) {
        return kBadPicture;
    }
    if (highest >= decoder.colours) {
        return kBadSettings;
    }
    memset(picture.pixels, 0, decoder.n);
    uint16_t duration = 0;
    do {
        reason = decoder.next(picture.pixels, &duration);
    } while (reason == kPendingWork);
    while (reason == kNone && (reason = decoder.finish()) == kPendingWork) {
    }
    if (reason != kNone) {
        return reason;
    }
    if (file->taken != kContainerHeaderSize + static_cast<uint64_t>(header.payload)) {
        return kPayloadSize;
    }
    if (header.loop_ms != 1000ull * seconds) {
        return kLoopMismatch;
    }
    if (into != nullptr) {
        memcpy(into, head, size);
    }
    return kNone;
}

}  // namespace

Reason clock_read(FileSource *file, const ContentHeader &header, uint8_t *into, const Picture &picture) {
    if (3ull * header.width * header.height > kLargestDrawn) {
        return kCanvasTooLarge;
    }
    uint8_t fixed[kLayerAt];
    Reason first = take(file, &fixed[0]);
    if (first != kNone) {
        return first;
    }
    if (fixed[0] < kAnalog || fixed[0] > kPictureDisplay) {
        return kUnknownWidget;
    }
    if (is_picture(fixed[0])) {
        return picture_read(file, header, fixed, into, picture);
    }
    if (header.payload != kWidgetSize) {
        return kPayloadSize;
    }
    for (uint32_t at = 1; at < kWidgetSize; ++at) {
        const Reason reason = take(file, &fixed[at]);
        if (reason != kNone) {
            return reason;
        }
    }
    const uint16_t seconds = u16(fixed + 2);
    const uint16_t least = u16(fixed + 16);
    const uint16_t greatest = u16(fixed + 18);
    if (fixed[1] != 0 || seconds < 1 || seconds > kLongestClock || least < 1 || least > kFastestClock || greatest < least ||
        greatest > kFastestClock) {
        return kBadSettings;
    }
    const int after = file->get();
    if (after == -kReadError) {
        return kReadError;
    }
    if (after != -kEnd) {
        return kTrailingBytes;
    }
    if (header.loop_ms != 1000ull * seconds) {
        return kLoopMismatch;
    }
    if (into != nullptr) {
        memcpy(into, fixed, kWidgetSize);
    }
    return kNone;
}

uint32_t clock_stir(uint32_t noise, uint64_t timestamp) {
    return mix(noise ^ static_cast<uint32_t>(timestamp));
}

uint32_t clock_seed(uint32_t noise, uint32_t id, uint64_t start) {
    const uint32_t seed = mix(noise ^ mix(id ^ static_cast<uint32_t>(start)));
    return seed == 0 ? 1 : seed;
}

uint32_t clock_shuffle(uint32_t key, uint32_t count, uint32_t index) {
    if (count <= 1) {
        return 0;
    }
    uint32_t bits = 2;
    while (bits < 32 && (1ull << bits) < count) {
        bits += 2;
    }
    const uint32_t half = bits / 2;
    const uint32_t mask = (1u << half) - 1u;
    uint32_t value = index;
    do {
        uint32_t left = value >> half;
        uint32_t right = value & mask;
        for (uint32_t round = 0; round < 4; ++round) {
            const uint32_t next = left ^ (mix(key ^ (round * 0x9E3779B9u) ^ right) & mask);
            left = right;
            right = next;
        }
        value = (left << half) | right;
    } while (value >= count);
    return value;
}

bool clock_is_picture(const uint8_t *payload) {
    return is_picture(payload[0]);
}

int64_t clock_virtual_time(const uint8_t *payload, uint32_t seed, uint64_t t) {
    const Clock clock = clock_of(payload, seed);
    if (is_picture(payload[0])) {
        return picture_time(payload, clock, seed, static_cast<int64_t>(t));
    }
    return virtual_time(clock, static_cast<int64_t>(t));
}

void clock_draw(const uint8_t *payload, uint32_t seed, uint16_t width, uint16_t height, uint64_t t, uint8_t *pixels) {
    const Clock clock = clock_of(payload, seed);
    const int64_t elapsed = static_cast<int64_t>(t);
    const int64_t time = fmod(virtual_time(clock, elapsed), kHalfDay);
    if (payload[0] == kAnalog) {
        draw_analog(payload, time, width, height, pixels);
    } else if (payload[0] == kDigital) {
        draw_digital(payload, time, elapsed, width, height, pixels);
    } else {
        draw_melting(payload, clock, time, elapsed, width, height, pixels);
    }
}

void clock_overlay(const uint8_t *payload, uint32_t seed, uint16_t width, uint16_t height, uint64_t t, uint8_t *layer) {
    memset(layer, 0, static_cast<size_t>(width) * height);
    const int64_t elapsed = static_cast<int64_t>(t);
    const int64_t time = picture_time(payload, clock_of(payload, seed), seed, elapsed);
    const uint32_t parts = payload[10];
    if (payload[0] == kPictureDial) {
        for (uint32_t one = 0; one < parts; ++one) {
            draw_hand(payload + kPictureHead + kHandSize * one, time, width, height, layer);
        }
        for (uint32_t one = 0; one < payload[11]; ++one) {
            draw_cap(payload + kPictureHead + kHandSize * parts + kCapSize * one, width, height, layer);
        }
        return;
    }
    for (uint32_t one = 0; one < parts; ++one) {
        draw_field(payload + kPictureHead + kFieldSize * one, time, elapsed, width, height, layer);
    }
}

}  // namespace odrig
