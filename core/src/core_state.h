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

// One item of the show. An animation item: `first` is its entry of the file table, `count`
// the number of loops of its turn and `seconds` the longest its turn lasts, each 0 when
// the show gives none. A cycle item: its animations are `count` entries of the entry
// table, from `first` on, each the position of an animation item in the item table, and
// `seconds` is the length of each of its turns.
struct ItemInfo {
    uint16_t id;
    uint16_t seconds;
    uint8_t is_cycle;
    uint32_t first;
    uint32_t count;
};

// One `.odrg` file the show names, with what its check found in it: its size in bytes
// and the sum of the durations of its frames.
struct FileInfo {
    char name[33];
    uint32_t bytes;
    uint64_t total_ms;
};

// Stands for no item.
const uint32_t kNothing = 0xFFFFFFFFu;

// What checks an uploaded file beside playback: a second source, which reads the file
// back from storage, and second decoders.
struct Checker {
    FileSource file;
    Inflate inflate;
    OdrgDecoder decoder;
};

// The states of an upload: none is open; its bytes are being received; all have arrived
// and the file is being checked; the check has ended and its outcome waits to be asked for.
const uint8_t kUploadNone = 0;
const uint8_t kUploadReceiving = 1;
const uint8_t kUploadChecking = 2;
const uint8_t kUploadChecked = 3;

// The outcomes of a check: the file can be played; it is not a valid file for the canvas;
// storage could not be read, or did not give back the bytes that were received.
const uint8_t kCheckPassed = 0;
const uint8_t kCheckBadFile = 1;
const uint8_t kCheckStorageFailed = 2;

// The one upload that can be open.
struct Upload {
    uint8_t state;
    uint8_t outcome;        // of a check that has ended
    uint8_t reason;         // why the file is not valid, a Reason
    uint8_t header_read;    // the first step of the check has been taken
    uint16_t id;            // the id the item gets, or has
    char name[33];          // the name the file gets
    uint32_t size;          // the size `upload begin` named
    uint32_t received;
    uint32_t crc;           // the running CRC-32 of the bytes received
    uint32_t records_left;  // the frame records the check has still to decode
    uint64_t total_ms;      // the sum of the durations of the records decoded
    uint64_t progress;      // the time something last moved
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

    // From the show file. The item table and the file table have room for
    // `item_capacity` entries, more than the show has at startup, so that an item can be
    // added while the core runs. `brightness` is the show's once its ids are checked, and
    // what `brightness` commands made of it since; `show_brightness` stays the value of
    // the file.
    ItemInfo *items;
    uint32_t item_count;
    uint32_t item_capacity;
    uint16_t *entries;
    uint32_t entry_count;
    FileInfo *files;
    uint32_t file_count;
    uint8_t brightness;
    uint8_t show_brightness;
    uint8_t has_start;
    uint32_t start_item;
    // How long an animation without a number of loops plays at least, in seconds, and
    // whether the show file says so itself.
    uint16_t min_seconds;
    uint8_t has_min_seconds;

    // A block of kChunkSize bytes for a host whose storage can be changed: a piece of an
    // upload or the text of a file the core writes, on its way to the host, and
    // `pending.txt` as it is read.
    uint8_t *chunk;

    // The upload, and what its check needs, three blocks for a host whose storage can be
    // changed: the second source and decoders, a pixel buffer and a window of their own.
    Upload upload;
    Checker *checker;
    uint8_t *check_pixels;
    uint8_t *check_window;

    uint8_t *pixels;        // the pixel buffer of the decoder
    uint8_t *window;        // the window of the DEFLATE decoder

    // The clock. Every time is a timestamp of the host, in milliseconds.
    uint8_t started;        // a call has carried a timestamp
    uint64_t t0;            // the power-on moment: the first timestamp
    uint64_t latest;        // the latest timestamp
    uint64_t next_due;      // the first grid time that is neither used nor skipped
    uint8_t had_refresh;    // a refresh has been produced
    uint64_t last_grid;     // the grid time of the latest refresh

    // The refreshes produced in the running second, counted from the power-on moment, and
    // in the second before it that had any.
    uint64_t second_running;
    uint64_t second_before;
    uint32_t count_running;
    uint32_t count_before;

    // The byte entry, odrig_core_feed. `line` is a block of ODRIG_LINE_MAX + 1 bytes that
    // holds the first bytes of the unfinished line, a whole line and a carriage return at
    // most; `line_over` says that more than those have arrived. `feed_reply` is a block of
    // ODRIG_REPLY_MAX bytes for the reply to a line. Without the two blocks the entry
    // takes no bytes.
    char *line;
    char *feed_reply;
    uint16_t line_length;
    uint8_t line_over;

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

// Makes the show invalid with a reason text: `<reason>`, `<reason> <about>` or
// `<reason> <about> <detail>`, and passes the text to the host's log. The first failure
// decides: when the show is invalid already, nothing changes.
void core_fail(Core &core, Reason reason, const char *about, Reason detail);

}  // namespace odrig

// The type the host interface names is the core object itself.
struct odrig_core {
    odrig::Core state;
};

static_assert(sizeof(odrig_core) <= 4096, "the core object is at most 4,096 bytes");

#endif
