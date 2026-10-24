#ifndef ODRIG_CLOCK_H
#define ODRIG_CLOCK_H

#include <stdint.h>

#include "container.h"
#include "file_source.h"
#include "reasons.h"

namespace odrig {

// A widget payload (docs/format.md, "The widget payload"): the 20 bytes of a clock.
const uint32_t kWidgetSize = 20;

// Reads and checks a widget payload from the source, where the header left it, as far as
// its end, which must be the file's: its canvas, its length, the widget, its settings and
// its loop. With `into`, the payload is kept there too.
Reason clock_read(FileSource *file, const ContentHeader &header, uint8_t *into);

// The noise after a refresh asked for at a timestamp, and the seed of a clock's turn: the
// noise mixed with the item's id and the turn's start, never 0.
uint32_t clock_stir(uint32_t noise, uint64_t timestamp);
uint32_t clock_seed(uint32_t noise, uint32_t id, uint64_t start);

// The virtual time of a clock of this payload and seed `t` milliseconds into its turn, in
// milliseconds, not taken modulo 12 hours.
int64_t clock_virtual_time(const uint8_t *payload, uint32_t seed, uint64_t t);

// Draws the clock whose payload is in memory, with the seed of its turn, `t` milliseconds
// into the turn, into a picture of three bytes for each pixel in the pixel order of
// docs/format.md.
void clock_draw(const uint8_t *payload, uint32_t seed, uint16_t width, uint16_t height, uint64_t t, uint8_t *pixels);

}  // namespace odrig

#endif
