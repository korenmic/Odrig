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

// One item of the show. An animation item: `first` is its entry of the file table. A cycle
// item: its animations are `count` entries of the entry table, from `first` on, each the
// position of an animation item in the item table.
struct ItemInfo {
    uint16_t id;
    uint16_t seconds;
    uint8_t is_cycle;
    uint32_t first;
    uint32_t count;
};

// One `.odrg` file the show names, with what the check at startup found in it.
struct FileInfo {
    char name[33];
    uint32_t frames;
    uint64_t total_ms;
};

// Stands for no item.
const uint32_t kNothing = 0xFFFFFFFFu;

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

    // From the show file. `brightness` is the show's once its ids are checked.
    ItemInfo *items;
    uint32_t item_count;
    uint16_t *entries;
    uint32_t entry_count;
    FileInfo *files;
    uint32_t file_count;
    uint8_t brightness;
    uint8_t has_start;
    uint32_t start_item;

    uint8_t *pixels;        // the pixel buffer of the decoder
    uint8_t *window;        // the window of the DEFLATE decoder

    // The clock. Every time is a timestamp of the host, in milliseconds.
    uint8_t started;        // a call has carried a timestamp
    uint64_t t0;            // the power-on moment: the first timestamp
    uint64_t latest;        // the latest timestamp
    uint64_t next_due;      // the first grid time that is neither used nor skipped

    // Playback.
    uint8_t on;
    uint8_t scale[256];     // what each colour value is sent as, at the current brightness
    uint32_t playing;       // the position of the item being played, or kNothing
    uint32_t shown;         // the position of the animation item the latest refresh chose
    uint8_t zero_pending;   // the item's time zero is the grid time of the next refresh
    uint64_t zero;          // the item's time zero

    // The file that is open for playback: an animation item in one turn and one loop.
    uint8_t stream_open;
    uint32_t stream_item;
    uint64_t stream_turn;
    uint64_t stream_loop;
    uint64_t frame_end;     // where the frame in the pixel buffer ends, counted in the loop

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
