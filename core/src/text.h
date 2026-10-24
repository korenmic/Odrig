#ifndef ODRIG_TEXT_H
#define ODRIG_TEXT_H

#include <stdint.h>

#include "container.h"
#include "file_source.h"
#include "reasons.h"

namespace odrig {

// A text payload (docs/format.md, "The text payload"): 28 bytes of settings, the text and
// its glyphs.
const uint32_t kTextSettingsSize = 28;
const uint32_t kGlyphSize = 6;
const uint32_t kLargestText = 512;
const uint32_t kMostGlyphs = 512;
const uint32_t kLargestTextPayload = kTextSettingsSize + kLargestText + kGlyphSize * kMostGlyphs;
// The largest picture the core draws into: three bytes for each pixel.
const uint32_t kLargestDrawn = 65534;

// Reads and checks a text payload from the source, where the header left it, as far as its
// end, which must be the file's: its settings, its length, whether its block fits the
// canvas, its text, its glyphs and its loop. With `into`, the payload is kept there too,
// which has room for kLargestTextPayload bytes.
Reason text_read(FileSource *file, const ContentHeader &header, uint8_t *into);

// The length of the text's pass, from its settings in memory and its canvas.
uint64_t text_pass(const uint8_t *payload, uint16_t width, uint16_t height);

// Draws the text whose payload is in memory, `t` milliseconds into its pass, into a
// picture of three bytes for each pixel in the pixel order of docs/format.md.
void text_draw(const uint8_t *payload, uint16_t width, uint16_t height, uint64_t t, uint8_t *pixels);

}  // namespace odrig

#endif
