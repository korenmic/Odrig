#ifndef ODRIG_CLOCK_H
#define ODRIG_CLOCK_H

#include <stdint.h>

#include "container.h"
#include "file_source.h"
#include "reasons.h"

namespace odrig {

// A widget payload (docs/format.md, "The widget payload"): the 20 bytes of a clock, or a
// picture clock's head, parts and picture, of at most 32,768 bytes.
const uint32_t kWidgetSize = 20;
const uint32_t kLargestWidget = 32768;

// Where the player keeps a picture clock's layer in the window, after its head and parts:
// at most 12 + 8 * 10 + 4 * 6 bytes.
const uint32_t kLayerAt = 128;

// Reads and checks a widget payload from the source, where the header left it, as far as
// its end, which must be the file's: its canvas, its widget, its length and settings, a
// picture clock's parts and picture, and its loop. With `into`, the 20 bytes of a clock,
// or a picture clock's head and parts, are kept there too. A picture clock's picture is
// decoded into the pixel buffer of `picture`, and its decoder holds its palette.
Reason clock_read(FileSource *file, const ContentHeader &header, uint8_t *into, const Picture &picture);

// Whether a payload kept by `clock_read` is a picture clock's.
bool clock_is_picture(const uint8_t *payload);

// The noise after a refresh asked for at a timestamp, and the seed of a clock's turn: the
// noise mixed with the item's id and the turn's start, never 0.
uint32_t clock_stir(uint32_t noise, uint64_t timestamp);
uint32_t clock_seed(uint32_t noise, uint32_t id, uint64_t start);

// The virtual time of a clock of this payload and seed `t` milliseconds into its turn, in
// milliseconds, not taken modulo 12 hours; a picture clock's with its direction.
int64_t clock_virtual_time(const uint8_t *payload, uint32_t seed, uint64_t t);

// Draws the clock whose payload is in memory, with the seed of its turn, `t` milliseconds
// into the turn, into a picture of three bytes for each pixel in the pixel order of
// docs/format.md. Not for a picture clock.
void clock_draw(const uint8_t *payload, uint32_t seed, uint16_t width, uint16_t height, uint64_t t, uint8_t *pixels);

// Writes the layer of a picture clock `t` milliseconds into its turn, with the seed of its
// turn: one byte for each pixel in the pixel order of docs/format.md, 0 where nothing is
// drawn and the palette index plus 1 where a hand, a cap or a digit is.
void clock_overlay(const uint8_t *payload, uint32_t seed, uint16_t width, uint16_t height, uint64_t t, uint8_t *layer);

}  // namespace odrig

#endif
