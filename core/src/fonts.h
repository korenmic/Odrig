#ifndef ODRIG_FONTS_H
#define ODRIG_FONTS_H

#include <stdint.h>

namespace odrig {

// One font's table: the glyphs of its characters, in the order of their code points. A
// glyph is `ascent + descent` rows, `rows[index * (ascent + descent) + row]`, whose bit 7
// is its leftmost pixel, and `widths[index]` pixels wide.
struct FontTable {
    uint8_t id;
    uint8_t version;
    uint8_t ascent;
    uint8_t descent;
    uint16_t count;
    const uint16_t *codes;
    const uint8_t *widths;
    const uint8_t *rows;
};

// The table of a font id, 1 small or 2 medium, or null for any other.
const FontTable *font_table(uint8_t id);

// The sine of a whole turn in 1,024 steps, in units of 1/16,384.
const uint32_t kSineEntries = 1024;
const int32_t kSineOne = 16384;
extern const int16_t kSine[kSineEntries];

}  // namespace odrig

#endif
