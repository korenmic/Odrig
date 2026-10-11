#ifndef ODRIG_CORE_STATE_H
#define ODRIG_CORE_STATE_H

#include <stdint.h>

#include "file_source.h"
#include "inflate.h"
#include "odrg_decoder.h"
#include "odrig_core.h"
#include "reasons.h"

namespace odrig {

// The longest reason text: `file-malformed`, a file name of 32 characters and the longest
// reason of an ODRG file, with the spaces between them, is 65 characters.
const uint32_t kErrorTextSize = 96;

// One leg of the mapping: its LEDs are `count` entries of the LED tables, from `first` on.
struct LegInfo {
    uint16_t leg;
    uint16_t pin;
    uint32_t first;
    uint32_t count;
};

// Everything the core knows. The host holds the one object; no part of the core keeps
// anything outside it.
struct Core {
    odrig_host host;

    // True while odrig_core_begin runs. Memory is asked for only then.
    uint8_t starting;

    // Whether the show is invalid, and the text that says why.
    uint8_t invalid;
    char error_text[kErrorTextSize];

    // From the mapping file. Without a valid mapping there are no legs.
    uint16_t width;
    uint16_t height;
    uint32_t leg_count;
    uint32_t led_total;
    LegInfo *legs;
    uint16_t *led_pixel;    // for each LED, the position of its pixel in pixel order
    uint8_t *led_data;      // for each LED, red, green and blue of the last refresh

    uint8_t *pixels;        // the pixel buffer of the decoder
    uint8_t *window;        // the window of the DEFLATE decoder

    FileSource file;
    Inflate inflate;
    OdrgDecoder decoder;
};

}  // namespace odrig

// The type the host interface names is the core object itself.
struct odrig_core {
    odrig::Core state;
};

static_assert(sizeof(odrig_core) <= 4096, "the core object is at most 4,096 bytes");

#endif
