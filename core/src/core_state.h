#ifndef ODRIG_CORE_STATE_H
#define ODRIG_CORE_STATE_H

#include <stdint.h>

#include "container.h"
#include "file_source.h"
#include "inflate.h"
#include "odrg_decoder.h"
#include "odrig_core.h"
#include "reasons.h"

// Marks a function as never inlined, so that its frame stays apart from its caller's: in
// the words of Microsoft's compiler, or in those of GCC and Clang.
#if defined(_MSC_VER)
#define ODRIG_NOINLINE __declspec(noinline)
#else
#define ODRIG_NOINLINE __attribute__((noinline))
#endif

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

// One item of the show. An animation item: `first` is its entry of the file table, the low
// 16 bits of `count` the number of loops of its turn as the show gives it and its high 16
// bits the loops of its saved repeat, and `seconds` the longest its turn lasts, each 0
// when there is none. A cycle item: its animations are `count` entries of the entry
// table, from `first` on, each the position of an animation item in the item table, and
// `seconds` is the length of each of its turns.
struct ItemInfo {
    uint16_t id;
    uint16_t seconds;
    uint8_t is_cycle : 1;
    uint8_t has_brightness : 1;
    uint8_t ignored;
    uint8_t has_ignored;
    uint8_t saved_brightness;
    uint32_t first;
    uint32_t count;
};

// One `.odrg` or `.odrgx` file the show names. `type` is what it holds, as its header says.
// `bytes` is its size, known once a check has read its body to its end. `total_ms` is its
// length, the sum of the durations of its frames, and 0 while it is not known: a check
// finds it, and so does playing the file through once. `fault` is the Reason of a fault of
// the file in this boot, kNone while it is usable: a file with a fault is quarantined, and
// its animations are unavailable until an upload replaces it. `checked` says that its
// `bytes` are known: kCheckedRead when a check has read it whole in this boot,
// kCheckedFromCatalog when they came from the storage's catalog.
const uint8_t kCheckedRead = 1;
const uint8_t kCheckedFromCatalog = 2;
struct FileInfo {
    char name[33];
    uint8_t fault;
    uint8_t checked;
    uint8_t type;
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

// The most entries of `order.txt` the core takes, and what an item or a place that no entry
// names holds.
const uint32_t kOrderMost = 512;
const uint16_t kOrderUnnamed = 0xFFFF;

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
    uint8_t header_read : 1; // the first step of the check has been taken
    uint8_t absent : 1;     // the external destination must remain absent
    uint16_t id;            // the id the item gets, or has
    char name[33];          // the name the file gets
    uint8_t installed;      // the file is installed: the id, the name, the size and the CRC-32 are its
    uint32_t size;          // the size `upload begin` named
    uint32_t received;
    uint32_t crc;           // the running CRC-32 of the bytes received
    uint32_t records_left;  // the frame records the check has still to decode
    uint64_t total_ms;      // the sum of the durations of the records decoded
    uint32_t progress;      // low timestamp bits; quiet intervals use modular subtraction
    uint32_t folder;        // external folder id, zero for the root
};

// What the core knows of the file at one place of a drive's list: its size, its length and
// its type once the check has read it whole, the id it got when the drive was taken up, its
// state, and the Reason it was left out for. The state and the type share a byte. A length
// of 4,294,967,295 ms or more is kept as 4,294,967,295.
struct DriveEntry {
    uint32_t total_ms;
    uint32_t bytes;
    uint16_t id;
    uint8_t state : 4;
    uint8_t type : 4;
    uint8_t fault;
};

// A file of a drive that was left out for a fault in this boot: the name the drive gave it,
// cut to 32 characters, the reason, and the number and the CRC-32 of its first bytes, at
// most 512. A file of a drive taken up later with the same four is left out again after
// reading those bytes.
struct Remembered {
    char name[kFaultNameSize];
    uint8_t reason;
    uint16_t first_read;
    uint32_t crc;
};

// The most files of drives the core remembers; the oldest gives way to a new one. A file of
// a drive whose catalog is read is remembered by its entry's CRC-32, with this as its first
// read.
const uint32_t kRememberedMost = 16;
const uint16_t kRememberedWhole = 0xFFFF;

// The states of a drive's file: to be checked; an animation of the playlist; left out; read
// from the drive's catalog and not published yet; removed by a change of the drive.
const uint8_t kDriveToCheck = 0;
const uint8_t kDriveInPlaylist = 1;
const uint8_t kDriveLeftOut = 2;
const uint8_t kDriveStaged = 3;
const uint8_t kDriveGone = 4;

// The most files of a drive without a catalog, the position in the playlist of the first
// file of the drive's walk, and the first id a drive's animation can get.
const uint32_t kDriveMost = 256;
const uint32_t kDriveBase = 0x10000u;
const uint32_t kDriveFirstId = 60001;
// Room for the name the core gives the host for a drive's file, `drive/<place>`.
const uint32_t kDriveNameSize = 16;
// Room for the name of a drive's file as `list` writes it: a longer one is cut to 127 bytes.
// Written as a JSON string it takes at most 762 bytes, so that its item fits into a reply.
const uint32_t kDriveListedName = 128;

// A saved repeat of a file of the drive: its position in the drive's walk and its loops, 0
// for a free entry. The core keeps kRepeatsDriveMost of them.
struct Position32 {
    uint16_t low;
    uint16_t high;
    operator uint32_t() const { return static_cast<uint32_t>(low) | static_cast<uint32_t>(high) << 16; }
    Position32 &operator=(uint32_t value) {
        low = static_cast<uint16_t>(value);
        high = static_cast<uint16_t>(value >> 16);
        return *this;
    }
};
struct RepeatOf {
    Position32 position;
    uint16_t loops;
};
static_assert(sizeof(RepeatOf) == 6, "compact full-range repeat record");
const uint32_t kRepeatsDriveMost = 32;

struct BrightnessOf {
    uint8_t position[4];
    uint8_t value;
};
static_assert(sizeof(BrightnessOf) == 5, "compact brightness record");
const uint32_t kBrightnessDriveMost = 32;

struct IgnoredOf {
    uint8_t position[4];
    uint8_t kind;
};
static_assert(sizeof(IgnoredOf) == 5, "compact full-range inclusion record");
const uint32_t kIgnoredMost = 128;

// The reading of `order.txt` line by line: the entries taken so far, whether its first line
// was read and was the header, and the line so far without its line feed. A line longer
// than kOrderLineMost is no entry. The line's room is a catalog's longest line: the reading
// of a drive's catalog uses it too, before `order.txt` is read.
const uint32_t kOrderLineMost = 129;
const uint32_t kOrderLineRoom = 162;
struct OrderReader {
    uint32_t entries;
    uint16_t length;
    uint8_t header;     // 0 while no line was read, 1 after the header, 2 after anything else
    uint8_t over;
    char line[kOrderLineRoom];
};

// A length as the drive's table keeps it.
inline uint32_t drive_length(uint64_t total_ms) {
    return total_ms < 0xFFFFFFFFu ? static_cast<uint32_t>(total_ms) : 0xFFFFFFFFu;
}

// The states of a storage's catalog: it has none; it is read and usable; it is being read;
// it cannot be read; its version is another; there is no such storage now.
const uint8_t kCatalogNone = 0;
const uint8_t kCatalogOk = 1;
const uint8_t kCatalogLoading = 2;
const uint8_t kCatalogDamaged = 3;
const uint8_t kCatalogIncompatible = 4;
const uint8_t kCatalogAbsent = 5;
// Where a damaged catalog is damaged.
const uint8_t kDamagedMarker = 1;
const uint8_t kDamagedPage = 2;
const uint8_t kDamagedLine = 3;
const uint8_t kDamagedInterrupted = 4;
// The catalogs of the core: of the internal storage, and of the drive.
const uint32_t kInternal = 0;
const uint32_t kExternal = 1;

// What the core knows of a storage's catalog: its state, where it is damaged, and of one
// that is read its generation and its number of entries.
struct CatalogState {
    uint32_t generation;
    uint32_t entries;
    uint8_t state;
    uint8_t detail;
};

// Whether a position of the playlist is a file of the drive: kDriveBase and the file's
// position in the drive's walk, the root's files first and then each folder's in the
// tree's order.
inline bool is_drive(uint32_t position) {
    return position >= kDriveBase && position < kPlaylist;
}

// One folder of the tree of a drive without a catalog: its id, the place of the first file
// at or below it, which is the first of its own files when it has any, its number of own
// files, its depth below the drive's folder, 1 to 3, and the index after its last
// descendant in the table. The places and the table are in the listing's order, depth
// first, so a folder's subtree is the index range from it to `end`, and its files a range
// of places from `first`.
struct Folder {
    uint16_t id;
    uint16_t first;
    uint16_t files;
    uint8_t depth;
    uint8_t end;
};

// The most folders of the table of a drive without a catalog, the root among them; a
// folder that is none; and the room for the current playlist's path, with its 0.
const uint32_t kFolderMost = 33;
const uint32_t kNoFolder = 0xFFFFFFFFu;
const uint32_t kPlaylistPathRoom = 104;

// Room for a path of the drive, at most 100 bytes, with its 0.
const uint32_t kDrivePathRoom = 101;

// A file of the drive at a position of its walk, or a sub-folder of a level, as the core
// reads it: from the table of a drive without a catalog, or from a line of the index of
// one with a catalog. `kind` is 'f' for a file and 'd' for a folder, whose `files` are its
// own files; `fault` is kNone for a file that plays, else the reason it is left out;
// `listed` says whether `list` lists the file, which a file still to be checked is not;
// its length is as the drive's table keeps it, and its name has the room of a listed
// drive's, whose host may give a name longer than an index holds.
struct DriveRow {
    uint32_t position;
    uint32_t id;
    uint32_t crc;
    uint32_t bytes;
    uint32_t total_ms;
    uint32_t files;
    uint16_t width;
    uint16_t height;
    uint8_t kind;
    uint8_t type;
    uint8_t fault;
    uint8_t listed;
    char name[kDriveListedName];
};

// A folder of the drive's tree: its ordinal in the table, its id, 0 for the root, the
// ordinal after its last descendant, the position in the walk of its first file and the
// one after its subtree's files, its own files and sub-folders, the CRC-32 of its file of
// the index, and its depth.
struct IndexFolder {
    uint32_t ordinal;
    uint32_t id;
    uint32_t end;
    uint32_t first;
    uint32_t last;
    uint32_t files;
    uint32_t folders;
    uint32_t crc;
    uint8_t depth;
};

// Room for the host's name of a file of the index, `drive/index-<id>.txt`, with its 0.
const uint32_t kIndexNameRoom = 28;

// The folder of the index whose own files the last row read was of: its ordinal, its id,
// the position of its first file in the walk and its number of own files, 0 for none.
struct WalkedFolder {
    uint32_t ordinal;
    uint32_t id;
    uint32_t first;
    uint32_t files;
};

// The cursor over the drive, a block of its own for a host with a drive: the room for one
// read of a file of the index, with the host's name of that file and the bytes it holds;
// the lines of the table and of the map and the drive's files, as the marker gives them;
// two rows read, and which of them was read the latest; the folder of the last file row
// read; the files of the drive left out since it was taken up; whether a line of the index
// could not be read, which makes the catalog damaged at the next refresh; and a rebuild's
// state.
struct DriveIndex {
    uint8_t room[kFileCacheSize];
    char room_name[kIndexNameRoom];
    uint32_t room_offset;
    uint32_t room_length;
    uint32_t folders;
    uint32_t ids;
    uint32_t files;
    uint32_t left_out;
    DriveRow rows[2];
    uint8_t latest;
    uint8_t broken;
    WalkedFolder walking;
    // A rebuild of the drive's catalog: its phase and the step of the folder it is at; the
    // line of the scan's file a pass is at, and the scan's lines; the files that passed,
    // which are the walk's, and the folders of the draft; the folder a phase is at, and its
    // row, sub-folder, offset or count; of the folder whose line of the table is made, its
    // end, sub-folders, own files and the running CRC-32 of its file; the lines and CRC-32s
    // of the table and of the map once written; the lines of the old table when the old index
    // is sound, so that its rows' order is kept, 0 otherwise; and where the next search of
    // the old table begins.
    uint8_t rebuild_phase;
    uint8_t rebuild_step;
    uint32_t rebuild_at;
    uint32_t scan_lines;
    uint32_t rebuild_passed;
    uint32_t rebuild_kept;
    uint32_t rebuild_ordinal;
    uint32_t rebuild_row;
    uint32_t rebuild_end;
    uint32_t rebuild_folders;
    uint32_t rebuild_files;
    uint32_t rebuild_sum;
    uint32_t table_lines;
    uint32_t table_crc;
    uint32_t map_lines;
    uint32_t map_crc;
    uint32_t old_folders;
    uint32_t old_search;
};

// Everything the core knows. The host holds the one object; no part of the core keeps
// anything outside it.
struct Mini;
struct Core {
    // Fields are grouped by alignment; comments name related state across these groups.
    odrig_host host;

    Mini *mini;

    LegInfo *legs;

    uint16_t *led_pixel;    // for each LED, the position of its pixel in pixel order

    uint8_t *led_data;      // for each LED, red, green and blue of the last refresh

    // From the show file. The item table and the file table have room for
    // `item_capacity` entries, more than the show has at startup, so that an item can be
    // added while the core runs. `brightness` is the show's once its ids are checked, and
    // what `brightness` commands made of it since; `show_brightness` stays the value of
    // the file.
    ItemInfo *items;

    uint16_t *entries;

    FileInfo *files;

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

    uint64_t check_total_ms;

    // The drive, for a host that has one: an entry for each place of the list of a drive
    // without a catalog, the number of the drive the entries are of, 0 for none, how many
    // places it has, and the place the check is at, with the name of its file, which the
    // check reads by; the cursor over a drive with a catalog, and whether the drive is read
    // from its index.
    DriveEntry *drive;

    DriveIndex *index;

    // The files of drives left out in this boot, the place the next one is written to, and
    // of the drive's file the check is at, the bytes and the CRC-32 of its first read.
    Remembered *remembered;

    // The saved playlist order, for a host whose storage can be changed: for each item of
    // the item table the number of the entry of `order.txt` that names it, or
    // kOrderUnnamed. In the same block, for a host with a drive, the saved repeats of the
    // drive's files.
    uint16_t *order_items;

    RepeatOf *repeats_drive;

    BrightnessOf *brightness_drive;

    // The tree of the drive's folders, for a host with a drive, in the block of the saved
    // order: the table of a drive without a catalog, the root at index 0 and the
    // sub-folders after it in the listing's order, `folder_count` of them; whether the
    // drive's tree is known, the table built or the index read; the current playlist's
    // folder, its index in the table or its ordinal in the index, 0 for the root, and its
    // record; and the room for the current playlist's path, empty for the root.
    Folder *folders;

    char *playlist_path;

    // The current playlist's window: the moment it became current, a timestamp, and the
    // milliseconds spent in the window before that moment, from the saved file.
    uint64_t window_started;

    // The saved file: when it was last written, whether a change waits to be written, and
    // whether the file exists.
    uint64_t playlist_saved;

    uint64_t break_offset;

    // The timestamp at which 5 minutes of the playlist's time are counted, and while the
    // count is held, the time left of the 5 minutes.
    uint64_t break_due;

    uint64_t break_rest;

    uint8_t *pixels;        // the pixel buffer of the decoder

    uint8_t *window;        // the window of the DEFLATE decoder

    uint64_t t0;            // the power-on moment: the first timestamp

    uint64_t latest;        // the latest timestamp

    uint64_t next_due;      // the first grid time that is neither used nor skipped

    uint64_t last_grid;     // the grid time of the latest refresh

    // The refreshes produced in the running second, counted from the power-on moment, and
    // in the second before it that had any.
    uint64_t second_running;

    uint64_t second_before;

    // The byte entry, odrig_core_feed. `line` is a block of ODRIG_LINE_MAX + 1 bytes that
    // holds the first bytes of the unfinished line, a whole line and a carriage return at
    // most; `line_over` says that more than those have arrived. `feed_reply` is a block of
    // ODRIG_REPLY_MAX bytes for the reply to a line. Without the two blocks the entry
    // takes no bytes.
    char *line;

    char *feed_reply;

    uint64_t zero;          // the item's time zero; of the playlist, the start of the turn

    uint64_t turn_number;   // of the playlist: counts its turns, so that each opens its file anew

    uint64_t stream_turn;

    uint64_t stream_loop;

    uint64_t frame_end;     // where the frame in the pixel buffer ends, counted in the loop

    FileSource file;

    Inflate inflate;

    OdrgDecoder decoder;

    // The latest fault of a file, kept for reporting.
    FaultContext fault;

    uint64_t catalog_looked;

    uint32_t leg_count;

    uint32_t led_total;

    uint32_t item_count;

    uint32_t item_capacity;

    uint32_t entry_count;

    uint32_t file_count;

    uint32_t start_item;

    // The check after the start, which reads the body of every file with the second
    // decoders while the show plays: whether it has read them all, which is for good; the
    // position in the file table of the file it is at; of that file, whether its header
    // was read, the records still to decode, and the sum of the durations so far; how
    // many refreshes in a row came without a grid time left out, counted to
    // kCheckMostSteps; and at how many refreshes in a row the check took no step.
    uint32_t check_at;

    // What the file the second decoders read holds, by its header: the file of this check,
    // of a drive's check or of an upload's check, which never read at the same time.
    ContentHeader check_content;

    uint32_t check_records_left;

    uint32_t drive_number;

    uint32_t drive_count;

    uint32_t drive_check_at;

    uint32_t remembered_next;

    uint32_t drive_first_crc;

    OrderReader order_reader;

    uint32_t folder_count;

    uint32_t current;

    IndexFolder current_folder;

    uint32_t resume_item;

    uint32_t window_spent;

    // The clocks' folders of the drive's tree, as positions of its walk: the folder
    // `clocks`, its subtree from `clocks_first` to before `clocks_last` and its own files,
    // `clocks_files` from `clocks_first` on; the folder `clocks/message`, its own files,
    // `message_files` from `message_first` on. All 0 for a folder there is none of.
    uint32_t clocks_first;

    uint32_t clocks_last;

    uint32_t clocks_files;

    uint32_t message_first;

    uint32_t message_files;

    uint32_t clocks_id;
    uint32_t clocks_ordinal;

    uint32_t message_order_key;
    uint32_t message_order_next;
    uint32_t message_order_count;

    // The order of the clocks: the key of its permutation, the place of the next clock in
    // it, and the number of clocks it was drawn for; a new one is drawn once it is used up.
    uint32_t order_key;

    uint32_t order_next;

    uint32_t order_count;

    // The position the playlist goes back to after the break; the paused turn's loops a
    // `repeat` gave it, its clock's seed, 0 for none, and its time when it was paused. The
    // seed a resumed turn of a clock takes in place of a new one, 0 for none.
    uint32_t break_back;

    uint32_t break_repeat;

    uint32_t break_seed;

    uint32_t resume_seed;

    uint32_t count_running;

    uint32_t count_before;

    uint32_t mapping_saved_playing;

    uint32_t mapping_saved_shown;

    uint32_t cycle_start_entry;

    uint32_t playing;       // the position of the cycle being played, kPlaylist, or kNothing

    uint32_t shown;         // the position of the animation item the latest refresh chose

    uint32_t noise;         // what the timestamps of the polls were mixed into

    uint32_t turn_item;     // of the playlist: the position of the animation whose turn it is

    uint32_t turn_repeat;   // of that turn: the loops a `repeat` gave it, 0 while none did

    uint32_t stream_item;

    uint32_t stream_records;    // the frame records of the open file that were decoded

    // At the refresh being made: the body bytes the player may still decode, and whether
    // it has decoded a record.
    uint32_t catch_up_left;

    // The seed of the turn of the clock that is open for playback.
    uint32_t seed;

    // The catalogs of the internal storage and of the drive.
    CatalogState catalogs[2];

    uint32_t catalog_marker_crc;

    uint32_t rebuild_at;

    uint32_t rebuild_read;

    uint32_t rebuild_total;

    uint32_t rebuild_lines;

    uint32_t rebuild_crc;

    // From the mapping file. Without a valid mapping there are no legs.
    uint16_t width;

    uint16_t height;

    // How long an animation without a number of loops plays at least, in seconds, and
    // whether the show file says so itself.
    uint16_t min_seconds;

    uint16_t drive_first_read;

    uint16_t line_length;

    // True while odrig_core_begin runs. Memory is asked for only then.
    uint8_t starting;

    // Whether the show is invalid, and the text that says why.
    uint8_t invalid;

    char error_text[kErrorTextSize];

    uint8_t brightness;

    uint8_t show_brightness;

    uint8_t has_start;

    uint8_t has_min_seconds;

    uint8_t pending_cleanup;

    uint8_t check_done;

    uint8_t check_header_read;

    uint8_t check_row;

    uint8_t check_idle;

    char drive_check_name[kDriveNameSize];

    uint8_t indexed;

    uint8_t brightness_error;
    uint8_t brightness_present;
    uint8_t ignored_error;
    uint8_t ignored_present;
    uint8_t turn_manual : 1;
    uint8_t break_manual : 1;
    uint8_t only_dirty : 1;

    // Whether the saved repeats of a drive without a catalog are to be read before its files
    // are checked.
    uint8_t repeats_due;

    uint8_t tree_known;

    // Whether the root plays in the current playlist's place, since that has nothing to
    // play: judged where a turn ends. And the animation whose turn a jump outside the
    // current playlist cut, which plays again after the jumped turn; kNothing for none.
    uint8_t in_place;

    uint8_t save_due;

    uint8_t file_present;

    // The two settings of `clocks.txt`: the clocks between the animations, and the message
    // after each clock.
    uint8_t clocks_on;

    uint8_t clock_message_on;

    // A break: its phase, kBreakNone, kBreakClock or kBreakMessage; whether it paused a
    // turn of the playlist; whether the message follows its clock; the turns of the
    // playlist counted, at most 255; whether the count of the playlist's time is held, as
    // the playlist does not play, with the time left of it then.
    uint8_t break_phase;

    uint8_t break_paused;

    uint8_t break_message;

    uint8_t break_turns;

    uint8_t break_held;

    // The clock. Every time is a timestamp of the host, in milliseconds.
    uint8_t started;        // a call has carried a timestamp

    uint8_t had_refresh;    // a refresh has been produced

    uint8_t line_over;

    // The diagnostic holds a decoded picture and a selection to resume. `mapping_snake` is the
    // snake whose test shows, 1 to 20, or 0 for the diagonal.
    uint8_t mapping_test;

    uint8_t mapping_snake;

    // Playback.
    uint8_t on;

    uint8_t scale[256];     // what each colour value is sent as, at the current brightness

    uint8_t zero_pending;   // the item's time zero is the grid time of the next refresh

    // The file that is open for playback: an animation item in one turn and one loop. A
    // drawn one is held in the window, its payload read whole, and its file is closed.
    uint8_t stream_open;

    uint8_t stream_drawn;

    uint8_t catch_up_begun;

    // The reading of a drive's catalog in steps: its phase, the CRC-32 of the whole marker,
    // and when it was last looked at.
    uint8_t catalog_phase;

    // A rebuild of a catalog: 0 for none, 1 + the storage's catalog it makes; the page it
    // writes, whether that page's new file is open, the file or the place it is at, the files
    // read and those to read, and the page's lines and running CRC-32. Each page's count and
    // CRC-32 wait at the end of the chunk buffer, from kRebuildPages on. A drive's rebuild
    // keeps the rest of its state in the cursor.
    uint8_t rebuild;

    uint8_t rebuild_page;

    uint8_t rebuild_open;

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

// What one step of the check of a file came to.
enum StepOutcome { kStepGoingOn, kStepWhole, kStepFault };

// One step of the check of a file through the second decoders: its header and canvas, one
// frame record, its end, after which nothing may follow, or one slice of the settling of a
// defect, after which the same step is taken again. When the file is whole, its size is the
// bytes the second source took and its length the sum of the durations; when it has a
// fault, `reason` says which, and `record` the frame record it was at.
StepOutcome check_file_step(Core &core, const char *name, Reason *reason, uint32_t *record);

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

// A drive without a catalog: listed, its first 256 files taken and 32 sub-folders, each
// file given its id, to be checked. `listed`, when given, gets the number of files the
// host's listing holds, or -1 when the drive is gone.
void drive_take_listed(Core &core, int32_t *listed = nullptr);

// The lowest id from kDriveFirstId up that no item of the show, no file of a drive without
// a catalog and no folder of its tree has, or 0 when there is none below 65,536.
uint32_t free_drive_id(const Core &core);

// Whether a file of the drive, whatever its state, or a folder of its tree has this id.
bool drive_id_taken(const Core &core, uint32_t id);

// A file of a drive without a catalog is left out: its state says so, and the host's log
// says why.
void drive_left_out(Core &core, uint32_t place, Reason reason);

// The host's log says that a file of the drive, by its name, is left out, and why.
void drive_log_left_out(Core &core, const char *name, Reason reason);

// An upload, or a change that reads with the second source, takes the second decoders:
// the check after the start, or the check of a drive's file, begins the file it was in
// again once they are free.
void drive_check_yields(Core &core);

// A file left the file table at this place: the check after the start stays at the file
// it was at, and begins it again when it was the one that left.
void check_file_left(Core &core, uint32_t file);

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
