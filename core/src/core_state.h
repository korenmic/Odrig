#ifndef ODRIG_CORE_STATE_H
#define ODRIG_CORE_STATE_H

#include <stdint.h>

#include "file_source.h"
#include "inflate.h"
#include "odrg_decoder.h"
#include "odrig_core.h"
#include "reasons.h"

namespace odrig {

// Room for the reason text of an invalid show: the longest, `duplicate-id` and an id of 11
// characters, is 24 characters.
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
    uint8_t ignored;
    uint8_t has_ignored;
    uint32_t first;
    uint32_t count;
};

// One `.odrg` file the show names. `bytes` is its size, known once a check has read its
// body to its end. `total_ms` is its length, the sum of the durations of its frames, and 0
// while it is not known: a check finds it, and so does playing the file through once.
// `fault` is the Reason of a fault of the file in this boot, kNone while it is usable: a
// file with a fault is quarantined, and its animations are unavailable until an upload
// replaces it.
struct FileInfo {
    char name[33];
    uint8_t fault;
    uint32_t bytes;
    uint64_t total_ms;
};

// The work in which a file came to a reason: the check at the start or after it, playback,
// the check of an upload, the check of a drive's file.
const uint8_t kWorkStart = 1;
const uint8_t kWorkPlay = 2;
const uint8_t kWorkUpload = 3;
const uint8_t kWorkDrive = 4;

// Room for the name of a file in the fault's context: 32 characters and the closing zero.
const uint32_t kFaultNameSize = 33;

// The latest fault of a file: in which work, the file's name (cut to 32 characters), the
// frame record it was at counted from 0 (the number of records after the last one), the
// bytes of its body read so far, inflated ones of a compressed body, and the reason.
// Each fault replaces the one before; `present` is 0 until the first.
struct FaultContext {
    uint8_t present;
    uint8_t work;
    uint8_t reason;
    char name[kFaultNameSize];
    uint32_t record;
    uint64_t body_bytes;
};

// Stands for no item, and for the playlist: every animation item of the show in turn.
const uint32_t kNothing = 0xFFFFFFFFu;
const uint32_t kPlaylist = 0xFFFFFFFEu;

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

// What the core knows of the file at one place of a drive's list: its size and its
// length once the check has read it whole, the id it got, and its state.
struct DriveEntry {
    uint64_t total_ms;
    uint32_t bytes;
    uint16_t id;
    uint8_t state;
};

// The states of a drive's file: to be checked; an animation of the playlist; left out.
const uint8_t kDriveToCheck = 0;
const uint8_t kDriveInPlaylist = 1;
const uint8_t kDriveLeftOut = 2;

// The most files of a drive, the position in the playlist of the file at place 0, and the
// first id a drive's animation can get.
const uint32_t kDriveMost = 256;
const uint32_t kDriveBase = 0x10000u;
const uint32_t kDriveFirstId = 60001;
// Room for the name the core gives the host for a drive's file, `drive/<place>`.
const uint32_t kDriveNameSize = 16;
// Room for the name of a drive's file as `list` writes it: a longer one is cut to 127 bytes.
// Written as a JSON string it takes at most 762 bytes, so that its item fits into a reply.
const uint32_t kDriveListedName = 128;

// Whether a position of the playlist is a drive's file.
inline bool is_drive(uint32_t position) {
    return position >= kDriveBase && position < kDriveBase + kDriveMost;
}

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
    uint8_t pending_cleanup;

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

    // The check after the start, which reads the body of every file with the second
    // decoders while the show plays: whether it has read them all, which is for good; the
    // position in the file table of the file it is at; of that file, whether its header
    // was read, the records still to decode, and the sum of the durations so far; how
    // many refreshes in a row came without a grid time left out, counted to
    // kCheckMostSteps; and at how many refreshes in a row the check took no step.
    uint32_t check_at;
    uint32_t check_records_left;
    uint64_t check_total_ms;
    uint8_t check_done;
    uint8_t check_header_read;
    uint8_t check_row;
    uint8_t check_idle;

    // The drive, for a host that has one: an entry for each place of its list, the number
    // of the drive the entries are of, 0 for none, how many places it has, and the place
    // the check is at, with the name of its file, which the check reads by.
    DriveEntry *drive;
    uint32_t drive_number;
    uint32_t drive_count;
    uint32_t drive_check_at;
    char drive_check_name[kDriveNameSize];

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

    // The diagnostic holds a decoded picture and a selection to resume.
    uint8_t mapping_test;
    uint32_t mapping_saved_playing;
    uint32_t mapping_saved_shown;
    uint32_t cycle_start_entry;

    // Playback.
    uint8_t on;
    uint8_t scale[256];     // what each colour value is sent as, at the current brightness
    uint32_t playing;       // the position of the cycle being played, kPlaylist, or kNothing
    uint32_t shown;         // the position of the animation item the latest refresh chose
    uint8_t zero_pending;   // the item's time zero is the grid time of the next refresh
    uint64_t zero;          // the item's time zero; of the playlist, the start of the turn
    uint32_t turn_item;     // of the playlist: the position of the animation whose turn it is
    uint64_t turn_number;   // of the playlist: counts its turns, so that each opens its file anew

    // The file that is open for playback: an animation item in one turn and one loop.
    uint8_t stream_open;
    uint32_t stream_item;
    uint64_t stream_turn;
    uint64_t stream_loop;
    uint64_t frame_end;     // where the frame in the pixel buffer ends, counted in the loop
    uint32_t stream_records;    // the frame records of the open file that were decoded
    // At the refresh being made: the body bytes the player may still decode, and whether
    // it has decoded a record.
    uint32_t catch_up_left;
    uint8_t catch_up_begun;

    FileSource file;
    Inflate inflate;
    OdrgDecoder decoder;

    // The latest fault of a file, kept for reporting.
    FaultContext fault;
};

// Keeps the context of a file's fault, in place of the one before.
void note_fault(Core &core, uint8_t work, const char *name, uint32_t record, uint64_t body_bytes, Reason reason);

// Whether a reason belongs to one `.odrg` file of the show, and not to the show itself.
bool is_file_fault(Reason reason);

// Quarantines the file at this place of the file table for the rest of the boot: its
// animations are unavailable, the log says why, the fault's context is kept, and the
// player goes on without them. A file that is quarantined already stays as it is.
void quarantine_file(Core &core, uint32_t file, Reason reason, uint8_t work, uint32_t record, uint64_t body_bytes);

// Whether the item at a position can be played: an animation whose file is not
// quarantined, or a cycle that lists one.
bool item_usable(const Core &core, uint32_t item);

// Makes the show invalid with a reason text: `<reason>`, `<reason> <about>` or
// `<reason> <about> <detail>`, and passes the text to the host's log. The first failure
// decides: when the show is invalid already, nothing changes.
void core_fail(Core &core, Reason reason, const char *about, Reason detail);

// The most steps the check after the start takes at one refresh, the most refreshes in a
// row at which it takes none, how late after its grid time a refresh may be and still
// count as on time, and the fewest refreshes the last whole second must have had for it.
const uint8_t kCheckMostSteps = 16;
const uint8_t kCheckLongestWait = 9;
const uint64_t kCheckOnTimeMs = 2;
const uint32_t kCheckLeastRate = 30;

// Whether the check after the start has read every file of the show to its end.
bool check_complete(const Core &core);

// Whether a file of the drive waits for the check, which may take it while no upload holds
// the second decoders.
bool drive_waits(const Core &core);

// The name the core gives the host for the file at a place of the drive, into room for
// kDriveNameSize characters.
void drive_file_name(uint32_t place, char *name);

// The name of the file at a place of the drive as the host gives it, cut to what fits into
// `room` characters with the closing zero; the core's own name for it when the host gives
// none.
void drive_given_name(const Core &core, uint32_t place, char *name, uint32_t room);

// Takes up a drive that was plugged in and drops one that was pulled out, at a refresh.
void drive_touch(Core &core);

// A file of the drive is left out: its state says so, and the host's log says why.
void drive_left_out(Core &core, uint32_t place, Reason reason);

// An upload takes the second decoders: the check of a drive's file begins that file
// again once the upload is over.
void drive_check_yields(Core &core);

// Whether an animation of the drive has this id.
bool drive_has_id(const Core &core, uint32_t id);

// The place of the drive's animation that has this id, or kDriveMost when none has.
uint32_t drive_place_of(const Core &core, uint32_t id);

// The check after the start at one refresh, after the LED data was made. `in_step` says
// whether the refresh followed the one before it without a grid time left out, and
// `on_time` whether it came no later than kCheckOnTimeMs after its grid time while the
// last whole second had kCheckLeastRate refreshes or more, or in the first second. At a
// refresh that is both, the check takes as many steps as refreshes of that kind have
// followed one another, at most kCheckMostSteps: a step opens a file, decodes one frame
// record, reads the end of a file, or takes one slice of the settling of a defect. At any other refresh the count begins again and
// the check takes no step, unless it took none at the kCheckLongestWait refreshes before
// either: then it takes one, so that a host that is always late still comes to the end of
// the check. A fault makes the show invalid with the reason the start gives for it.
void check_after_start(Core &core, bool in_step, bool on_time);

}  // namespace odrig

// The type the host interface names is the core object itself.
struct odrig_core {
    odrig::Core state;
};

static_assert(sizeof(odrig_core) <= 4096, "the core object is at most 4,096 bytes");

#endif
