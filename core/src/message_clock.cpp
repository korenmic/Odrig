#include "message_clock.h"

#include <string.h>
#include "fonts.h"

namespace odrig {
namespace {

uint16_t u16(const uint8_t *p) { return static_cast<uint16_t>(p[0] | (p[1] << 8)); }
uint32_t u32(const uint8_t *p) {
    return static_cast<uint32_t>(p[0]) | static_cast<uint32_t>(p[1]) << 8 |
           static_cast<uint32_t>(p[2]) << 16 | static_cast<uint32_t>(p[3]) << 24;
}
Reason take(FileSource *file, uint8_t *byte, uint8_t *into, uint32_t at) {
    const int read = file->get();
    if (read < 0) return read == -kReadError ? kReadError : kTruncated;
    *byte = static_cast<uint8_t>(read);
    if (into != nullptr) into[at] = *byte;
    return kNone;
}
uint32_t random(uint32_t x) { x ^= x << 13; x ^= x >> 17; x ^= x << 5; return x; }
uint32_t duration(const uint8_t *p, uint32_t i) { return u32(p + 24 + i * 12); }
uint8_t flags(const uint8_t *p, uint32_t i) { return p[24 + i * 12 + 4]; }
uint32_t motion(uint32_t t, uint32_t stop) {
    if (stop == 0xffffffffu || t < stop) return t;
    const uint64_t u = t - stop < 3500 ? t - stop : 3500;
    return stop + static_cast<uint32_t>(u - u * u * u / 12250000 + u * u * u * u / 85750000000ull);
}
int64_t floor_div(int64_t value, int64_t denominator) {
    return value / denominator - ((value < 0 && value % denominator != 0) ? 1 : 0);
}
int32_t cosine(uint32_t t) {
    const uint64_t angle = static_cast<uint64_t>(t) * 67108864 / 4000 + 16777216;
    const uint32_t i = static_cast<uint32_t>(angle / 65536 % 1024);
    const int64_t part = angle % 65536;
    return kSine[i] + static_cast<int32_t>(floor_div((kSine[(i + 1) % 1024] - kSine[i]) * part, 65536));
}
int32_t square(uint32_t t) { return (60 * 16384 + 53 * cosine(t)) / 32768; }
uint32_t alpha(const uint8_t *p, uint32_t at) { return ((at & 1) ? p[at / 2] & 15 : p[at / 2] >> 4) * 17u; }
uint32_t glyph_row(const uint8_t *p, uint32_t glyph, int32_t x, int32_t y) {
    return y < 0 || y >= 16 ? 0 : alpha(p, glyph * 128 + static_cast<uint32_t>(y * 8 + x));
}
uint32_t glyph(const uint8_t *p, uint32_t index, int32_t x, int32_t row_q) {
    if (x < 0 || x >= 8) return 0;
    const int32_t y = static_cast<int32_t>(floor_div(row_q, 256));
    const uint32_t f = static_cast<uint32_t>(row_q - y * 256);
    return (glyph_row(p, index, x, y) * (256 - f) + glyph_row(p, index, x, y + 1) * f) / 256;
}
struct Digits {
    uint8_t current[6];
    uint8_t before[6];
    int32_t rolled[6];
};
void roll(Digits &d, uint32_t i, int32_t way, uint32_t when) {
    d.before[i] = d.current[i];
    d.current[i] = static_cast<uint8_t>((d.current[i] + way + 10) % 10);
    d.rolled[i] = static_cast<int32_t>(when);
}
Digits digits(const uint8_t *p, uint32_t seed, uint32_t m) {
    uint32_t r = random(seed == 0 ? 1 : seed);
    const uint32_t start = r % 86400;
    Digits d = {};
    d.current[0] = static_cast<uint8_t>(start / 36000);
    d.current[1] = static_cast<uint8_t>(start / 3600 % 10);
    d.current[2] = static_cast<uint8_t>(start / 600 % 6);
    d.current[3] = static_cast<uint8_t>(start / 60 % 10);
    d.current[4] = static_cast<uint8_t>(start / 10 % 6);
    d.current[5] = static_cast<uint8_t>(start % 10);
    for (uint32_t i = 0; i < 6; ++i) { d.before[i] = d.current[i]; d.rolled[i] = -10000; }
    for (uint32_t when = 2000; when <= m; when += 2000) {
        uint32_t at = 0;
        bool boost = false;
        for (uint32_t i = 0; i < p[3]; ++i) {
            if (when >= at && when < at + duration(p, i)) boost = (flags(p, i) & 16) != 0;
            at += duration(p, i);
        }
        roll(d, 5, 1, when);
        if (d.current[5] == 0) roll(d, 4, 1, when);
        r = random(r);
        const bool minute = static_cast<uint64_t>(r) * 100 < static_cast<uint64_t>(boost ? 48 : 14) * 4294967296ull;
        r = random(r);
        const bool hour = static_cast<uint64_t>(r) * 1000 < static_cast<uint64_t>(boost ? 250 : 45) * 4294967296ull;
        if (minute) {
            r = random(r); const int32_t way = r < 2147483648u ? -1 : 1;
            roll(d, 3, way, when);
            if (d.current[3] == (way > 0 ? 0 : 9)) roll(d, 2, way, when);
        }
        if (hour) {
            r = random(r); const int32_t way = r < 2147483648u ? -1 : 1;
            roll(d, 1, way, when);
            if (d.current[1] == (way > 0 ? 0 : 9)) roll(d, 0, way, when);
        }
    }
    return d;
}
uint32_t clock_pixel(const uint8_t *atlas, const Digits &d, uint32_t m, bool stopped, int32_t x, int32_t y) {
    const int32_t origins[8] = {2, 9, 23, 30, 43, 50, 16, 36};
    uint32_t value = 0;
    for (uint32_t slot = 0; slot < 8; ++slot) {
        const int32_t xx = x - origins[slot];
        uint32_t a;
        const int32_t q = (y - 34) * 256;
        if (slot >= 6) a = glyph(atlas, 60 + slot - 6, xx, q);
        else {
            const int32_t age = static_cast<int32_t>(m) - d.rolled[slot];
            if (age < 500 && !stopped) {
                const int32_t shift = static_cast<int32_t>(4096ll * age * age * (1500 - 2 * age) / 125000000);
                a = glyph(atlas, slot * 10 + d.before[slot], xx, q + shift) +
                    glyph(atlas, slot * 10 + d.current[slot], xx, q + shift - 4096);
            } else a = glyph(atlas, slot * 10 + d.current[slot], xx, q);
        }
        value += a - value * a / 255;
        if (value > 255) value = 255;
    }
    return value;
}
}  // namespace

Reason message_clock_read(FileSource *file, const ContentHeader &header, uint8_t *into) {
    if (header.width != 60 || header.height != 60) return kBadSettings;
    uint8_t head[24] = {6};
    if (into != nullptr) into[0] = 6;
    for (uint32_t i = 1; i < 24; ++i) {
        const Reason r = take(file, head + i, into, i); if (r != kNone) return r;
    }
    const uint32_t count = head[3], text_size = u16(head + 8);
    if (head[1] != 1 || head[2] < 1 || head[2] > 7 || count < 1 || count > 24 || u16(head + 10) || text_size < 1 || text_size > 4096) return kBadSettings;
    const uint32_t masks = 24 + 12 * count + text_size, glyphs = masks + count * 900, total = glyphs + 3968;
    if (u32(head + 12) != masks || u32(head + 16) != glyphs) return kBadSettings;
    if (u32(head + 20) != total || header.payload != total || total > 32768) return kPayloadSize;
    uint16_t lengths[24] = {};
    uint32_t text_at = 0, elapsed = 0, stops = 0, freezes = 0, position = 24;
    for (uint32_t i = 0; i < count; ++i) {
        uint8_t record[12];
        for (uint32_t j = 0; j < 12; ++j, ++position) {
            const Reason r = take(file, record + j, into, position); if (r != kNone) return r;
        }
        const uint8_t f = record[4];
        const uint32_t size = u16(record + 8);
        if (record[5] || u16(record + 10) || (f & ~31) || (f & 3) == 3 ||
            ((f & 3) && head[2] != 5) || ((f & 4) && head[2] != 1) || ((f & 24) && head[2] != 6) ||
            size < 1 || size > 256 || u16(record + 6) != text_at || u32(record) != ((f & 1) ? 2000u : 6100u)) return kBadSettings;
        if (((f & 4) && ++stops > 1) || ((f & 8) && ++freezes > 1)) return kBadSettings;
        lengths[i] = static_cast<uint16_t>(size); text_at += size; elapsed += u32(record);
    }
    if (text_at != text_size) return kBadSettings;
    for (uint32_t i = 0; i < count; ++i) {
        uint32_t cp = 0, minimum = 0, remaining = 0;
        for (uint32_t j = 0; j < lengths[i]; ++j, ++position) {
            uint8_t b; const Reason r = take(file, &b, into, position); if (r != kNone) return r;
            if (remaining == 0) {
                if (b < 128) cp = b;
                else if (b >= 194 && b <= 223) { cp = b & 31; remaining = 1; minimum = 128; }
                else if (b >= 224 && b <= 239) { cp = b & 15; remaining = 2; minimum = 2048; }
                else if (b >= 240 && b <= 244) { cp = b & 7; remaining = 3; minimum = 65536; }
                else return kBadText;
            } else {
                if ((b & 192) != 128) return kBadText;
                cp = (cp << 6) | (b & 63);
                if (--remaining == 0 && (cp < minimum || cp > 0x10ffff || (cp >= 0xd800 && cp <= 0xdfff))) return kBadText;
            }
            if (remaining == 0 && (cp < 32 || (cp >= 127 && cp <= 159))) return kBadText;
        }
        if (remaining != 0) return kBadText;
    }
    for (; position < total; ++position) {
        uint8_t b; const Reason r = take(file, &b, into, position); if (r != kNone) return r;
    }
    const int after = file->get();
    if (after == -kReadError) return kReadError;
    if (after != -kEnd) return kTrailingBytes;
    return elapsed != u32(head + 4) || elapsed != header.loop_ms ? kLoopMismatch : kNone;
}

void message_clock_draw(const uint8_t *p, uint32_t seed, uint64_t elapsed, uint8_t *pixels) {
    const uint32_t t = static_cast<uint32_t>(elapsed % u32(p + 4));
    uint32_t stop = 0xffffffffu, freeze = 0xffffffffu, at = 0, chosen = 0, chosen_at = 0;
    for (uint32_t i = 0; i < p[3]; ++i) {
        if (flags(p, i) & 4) stop = at;
        if (flags(p, i) & 8) freeze = at;
        if (t >= at) { chosen = i; chosen_at = at; }
        at += duration(p, i);
    }
    const uint32_t m = motion(t, stop), phase = t - chosen_at;
    const bool stopped = stop != 0xffffffffu && t >= stop + 3500;
    const Digits d = digits(p, seed, m);
    const int32_t centre = square(freeze != 0xffffffffu && t >= freeze ? motion(freeze, stop) : m);
    const bool countdown = (flags(p, chosen) & 1) != 0;
    const uint32_t numerator = countdown ? 1 : phase < 600 ? phase : phase < 5600 ? 1 : 6100 - phase;
    const uint32_t denominator = countdown ? 1 : phase < 600 ? 600 : phase < 5600 ? 1 : 500;
    const uint8_t *mask = p + u32(p + 12) + chosen * 900, *atlas = p + u32(p + 16);
    memset(pixels, 0, 10800);
    for (int32_t y = 0; y < 60; ++y) for (int32_t x = 0; x < 60; ++x) {
        uint32_t value = 0; bool blue = false;
        if (y < 30) {
            value = alpha(mask, static_cast<uint32_t>(y * 60 + x)) * numerator / denominator;
            const int32_t wave = static_cast<int32_t>(t % 9000);
            const int32_t delta = x * 150000 - (135 * wave - 22500) * 60;
            blue = wave < 1500 && value >= 8 && delta > -630000 && delta < 630000;
            if (value < 4) value = 0;
        } else if (y >= 34 && y < 50) value = clock_pixel(atlas, d, m, stopped, x, y);
        else if (y >= 57 && x >= centre - 1 && x <= centre + 1) value = 255;
        const uint32_t pixel = static_cast<uint32_t>(3 * ((59 - y) * 60 + x));
        pixels[pixel] = static_cast<uint8_t>(blue ? value * 90 / 255 : value);
        pixels[pixel + 1] = static_cast<uint8_t>(blue ? value * 205 / 255 : value);
        pixels[pixel + 2] = static_cast<uint8_t>(value);
    }
}

}  // namespace odrig
