#include <string.h>

#include "arena.h"
#include "catalog.h"
#include "crc32.h"
#include "core_state.h"
#include "current_limits.h"
#include "mapping.h"
#include "odrig_core.h"
#include "order.h"
#include "player.h"
#include "playlist.h"
#include "reasons.h"
#include "show.h"
#include "storage.h"
#include "upload.h"

namespace odrig {

namespace {

// Adds a text to the reason text, as far as it fits.
void append(Core &core, const char *text) {
    uint32_t length = 0;
    while (core.error_text[length] != '\0') {
        ++length;
    }
    while (*text != '\0' && length + 1 < kErrorTextSize) {
        core.error_text[length++] = *text++;
    }
    core.error_text[length] = '\0';
}

// Opens one file of the show and reads its header: an ODRG file's, or a container's and
// that of its payload, and compares the canvas with the mapping's. The palette and the
// frame records are not read. A drawn type's length is its header's loop from here on. A
// file that cannot be used is quarantined.
void open_file(Core &core, uint32_t index) {
    FileInfo &info = core.files[index];
    Reason reason = core.file.open(core.host, info.name);
    if (reason == kNone) {
        ContentHeader header;
        reason = content_open(&core.file, &core.inflate, core.window, &core.decoder, &header);
        if (reason == kNone && (header.width != core.width || header.height != core.height)) {
            reason = kSizeMismatch;
        }
        info.type = header.type;
        if (reason == kNone && is_drawn(header.type)) {
            info.total_ms = header.loop_ms;
        }
        core.file.close();
    }
    if (reason != kNone) {
        quarantine_file(core, index, reason, kWorkStart, 0, 0);
    }
}

// Decodes one file of the show from its first frame record to its last, and notes its
// size and its total duration. The header is checked first, then the size
// against the mapping, then the body. A file with a fault is quarantined.
void check_file(Core &core, uint32_t index) {
    FileInfo &info = core.files[index];
    Reason reason = core.file.open(core.host, info.name);
    if (reason != kNone) {
        quarantine_file(core, index, reason, kWorkStart, 0, 0);
        return;
    }
    ContentHeader header;
    reason = content_open(&core.file, &core.inflate, core.window, &core.decoder, &header);
    if (reason == kNone && (header.width != core.width || header.height != core.height)) {
        core.file.close();
        quarantine_file(core, index, kSizeMismatch, kWorkStart, 0, 0);
        return;
    }
    // Nothing waits on this check: it goes on through every slice of a settling.
    info.type = header.type;
    uint64_t total = 0;
    uint32_t record = 0;
    if (reason == kNone && is_drawn(header.type)) {
        reason = drawn_read(&core.file, header, nullptr);
        total = header.loop_ms;
    } else if (reason == kNone) {
        memset(core.pixels, 0, core.decoder.n);
        for (; record < core.decoder.frames; ++record) {
            uint16_t duration = 0;
            do {
                reason = core.decoder.next(core.pixels, &duration);
            } while (reason == kPendingWork);
            if (reason != kNone) {
                break;
            }
            total += duration;
        }
    }
    if (reason == kNone) {
        do {
            reason = content_finish(&core.file, &core.decoder, header, total);
        } while (reason == kPendingWork);
    }
    // A file that was read to its end was read whole.
    const uint32_t bytes = core.file.taken;
    core.file.close();
    if (reason != kNone) {
        quarantine_file(core, index, reason, kWorkStart, record, core.decoder.body_read);
    } else {
        info.bytes = bytes;
        info.total_ms = total;
        info.checked = 1;
    }
}

}  // namespace

StepOutcome check_file_step(Core &core, const char *name, Reason *reason, uint32_t *record) {
    Checker &checker = *core.checker;
    Reason found;
    *record = 0;
    if (!core.check_header_read) {
        checker.file.open_at(core.host, name);
        found = content_open(&checker.file, &checker.inflate, core.check_window, &checker.decoder, &core.check_content);
        if (found == kNone && (core.check_content.width != core.width || core.check_content.height != core.height)) {
            found = kSizeMismatch;
        }
        if (found == kNone) {
            // A drawn payload is read and checked whole in one step, as one record.
            const bool drawn = is_drawn(core.check_content.type);
            if (!drawn) {
                memset(core.check_pixels, 0, checker.decoder.n);
            }
            core.check_records_left = drawn ? 1 : checker.decoder.frames;
            core.check_total_ms = 0;
            core.check_header_read = 1;
            return kStepGoingOn;
        }
    } else if (core.check_records_left != 0) {
        if (is_drawn(core.check_content.type)) {
            found = drawn_read(&checker.file, core.check_content, nullptr);
            core.check_total_ms = core.check_content.loop_ms;
        } else {
            uint16_t duration = 0;
            *record = checker.decoder.frames - core.check_records_left;
            found = checker.decoder.next(core.check_pixels, &duration);
            if (found == kPendingWork) {
                return kStepGoingOn;
            }
            core.check_total_ms += duration;
        }
        --core.check_records_left;
        if (found == kNone) {
            return kStepGoingOn;
        }
    } else {
        *record = checker.decoder.frames;
        found = content_finish(&checker.file, &checker.decoder, core.check_content, core.check_total_ms);
        if (found == kPendingWork) {
            return kStepGoingOn;
        }
        if (found == kNone) {
            checker.file.close();
            core.check_header_read = 0;
            return kStepWhole;
        }
    }
    checker.file.close();
    core.check_header_read = 0;
    *reason = found;
    return kStepFault;
}

namespace {

// Moves the check after the start past the files it has no more to do with: those that
// are quarantined or were read whole by an upload's check. It is complete once it is past
// the last file.
void check_passes_done(Core &core) {
    while (core.check_at < core.file_count && (core.files[core.check_at].fault != kNone || core.files[core.check_at].checked)) {
        ++core.check_at;
    }
    core.check_done = core.check_at >= core.file_count;
}

// One step of the check after the start, on the installed file it is at. A file read to
// its end was read whole; a file with a fault is quarantined, and the check goes on with
// the next one.
void check_step(Core &core) {
    FileInfo &info = core.files[core.check_at];
    if (info.fault != kNone || info.checked) {
        // The player quarantined the file the check is at, or an upload replaced it: it is
        // not read again.
        if (core.check_header_read) {
            core.checker->file.close();
            core.check_header_read = 0;
        }
        ++core.check_at;
        check_passes_done(core);
        return;
    }
    Reason reason = kNone;
    uint32_t record = 0;
    const StepOutcome outcome = check_file_step(core, info.name, &reason, &record);
    if (outcome == kStepWhole) {
        info.bytes = core.checker->file.taken;
        info.total_ms = core.check_total_ms;
        info.checked = 1;
        info.type = core.check_content.type;
        ++core.check_at;
        check_passes_done(core);
    } else if (outcome == kStepFault) {
        quarantine_file(core, core.check_at, reason, kWorkStart, record, core.checker->decoder.body_read);
        ++core.check_at;
        check_passes_done(core);
    }
}

// Whether two names are the same, byte for byte.
bool same_name(const char *one, const char *other) {
    while (*one != 0 && *one == *other) {
        ++one;
        ++other;
    }
    return *one == *other;
}

}  // namespace

bool drive_id_taken(const Core &core, uint32_t id) {
    for (uint32_t place = 0; place < core.drive_count; ++place) {
        if (core.drive[place].id == id) {
            return true;
        }
    }
    for (uint32_t folder = 1; core.folders != nullptr && folder <= core.folder_count; ++folder) {
        if (core.folders[folder].id == id) {
            return true;
        }
    }
    return false;
}

uint16_t free_drive_id(const Core &core) {
    for (uint32_t id = kDriveFirstId; id <= 65535; ++id) {
        bool taken = drive_id_taken(core, id);
        for (uint32_t item = 0; item < core.item_count && !taken; ++item) {
            taken = core.items[item].id == id;
        }
        if (!taken) {
            return static_cast<uint16_t>(id);
        }
    }
    return 0;
}

namespace {

// The file of a drive left out in this boot that has this name and the first read of the
// file the check is at, or null.
const Remembered *remembered_file(const Core &core, const char *name) {
    for (uint32_t at = 0; core.remembered != nullptr && at < kRememberedMost; ++at) {
        const Remembered &one = core.remembered[at];
        if (one.reason != kNone && one.first_read == core.drive_first_read && one.crc == core.drive_first_crc && same_name(one.name, name)) {
            return &one;
        }
    }
    return nullptr;
}

// Keeps a file of a drive left out for a fault, in place of the oldest one kept.
void remember_file(Core &core, const char *name, Reason reason) {
    if (core.remembered == nullptr || !is_file_fault(reason)) {
        return;
    }
    Remembered &one = core.remembered[core.remembered_next];
    core.remembered_next = (core.remembered_next + 1) % kRememberedMost;
    uint32_t length = 0;
    for (; name[length] != 0 && length + 1 < kFaultNameSize; ++length) {
        one.name[length] = name[length];
    }
    one.name[length] = 0;
    one.reason = static_cast<uint8_t>(reason);
    one.first_read = core.drive_first_read;
    one.crc = core.drive_first_crc;
}

// One step of the check of the drive's files, after the installed ones. A file that is
// whole and of the canvas becomes an animation of the playlist; one that is not is left out.
void drive_step(Core &core) {
    if (catalog_drive_loading(core)) {
        catalog_drive_step(core);
        return;
    }
    if (order_drive_due(core)) {
        // The saved order of the drive's files is known before any of them joins the playlist.
        order_drive_step(core);
        return;
    }
    while (core.drive_check_at < core.drive_count && core.drive[core.drive_check_at].state != kDriveToCheck) {
        ++core.drive_check_at;
    }
    if (core.drive_check_at >= core.drive_count) {
        return;
    }
    const uint32_t place = core.drive_check_at;
    drive_file_name(place, core.drive_check_name);
    DriveEntry &entry = core.drive[place];
    char name[kFaultNameSize];
    if (!core.check_header_read) {
        // The file's first read: its first 512 bytes and their CRC-32, whatever pieces the
        // host gives them in. A file left out in this boot is left out again after it.
        FileSource &source = core.checker->file;
        source.open_at(core.host, core.drive_check_name);
        uint32_t crc = kCrcStart;
        uint32_t count = 0;
        int byte;
        while (count < kFileBufferSize && (byte = source.get()) >= 0) {
            crc = crc_add(crc, static_cast<uint8_t>(byte));
            ++count;
        }
        source.close();
        core.drive_first_read = static_cast<uint16_t>(count);
        core.drive_first_crc = crc;
        drive_given_name(core, place, name, sizeof name);
        const Remembered *found = remembered_file(core, name);
        if (found != nullptr) {
            ++core.drive_check_at;
            entry.state = kDriveLeftOut;
            drive_left_out(core, place, static_cast<Reason>(found->reason));
            return;
        }
    }
    Reason reason = kNone;
    uint32_t record = 0;
    const StepOutcome outcome = check_file_step(core, core.drive_check_name, &reason, &record);
    if (outcome == kStepWhole) {
        ++core.drive_check_at;
        if (entry.id == 0) {
            // Every id a drive's animation may have is taken.
            entry.state = kDriveLeftOut;
            drive_left_out(core, place, kDuplicateId);
            return;
        }
        entry.bytes = core.checker->file.taken;
        entry.total_ms = drive_length(core.check_total_ms);
        entry.type = core.check_content.type;
        entry.state = kDriveInPlaylist;
        player_drive_joined(core, place);
    } else if (outcome == kStepFault) {
        ++core.drive_check_at;
        entry.state = kDriveLeftOut;
        drive_given_name(core, place, name, sizeof name);
        note_fault(core, kWorkDrive, name, record, core.checker->decoder.body_read, reason);
        remember_file(core, name, reason);
        drive_left_out(core, place, reason);
    }
}

void start(Core &core) {
    // The current playlist's window and its saved file, before the file is read.
    core.window_started = 0;
    core.window_spent = 0;
    core.playlist_saved = 0;
    core.save_due = 0;
    core.file_present = 0;
    // A change of the catalog that was committed is finished before the parts of a change
    // are cleared away: its upload's part may be the file it puts in place.
    catalog_finish_internal(core);
    storage_clear_parts(core);

    core.line = static_cast<char *>(arena_take(core, ODRIG_LINE_MAX + 1));
    core.feed_reply = static_cast<char *>(arena_take(core, ODRIG_REPLY_MAX));
    if (core.line == nullptr || core.feed_reply == nullptr) {
        core_fail(core, kOutOfMemory, nullptr, kNone);
        return;
    }

    Reason reason = read_mapping(core);
    // The budgets, whatever came of the mapping: they are known without legs too.
    limits_read(core);
    if (reason != kNone) {
        core_fail(core, reason, reason == kReadError ? "mapping.json" : nullptr, kNone);
        return;
    }

    const uint32_t rgb_picture = 3u * core.led_total;
    core.pixels = static_cast<uint8_t *>(arena_take(core, rgb_picture < kLargestPicture ? rgb_picture : kLargestPicture));
    core.window = static_cast<uint8_t *>(arena_take(core, kWindowSize));
    if (core.pixels == nullptr || core.window == nullptr) {
        core_fail(core, kOutOfMemory, nullptr, kNone);
        return;
    }
    if (storage_changes(core)) {
        // What only a change of the show needs: the chunk buffer, and for the check of an
        // uploaded file a second set of decoders with a pixel buffer and a window.
        core.chunk = static_cast<uint8_t *>(arena_take(core, kChunkSize));
        core.checker = static_cast<Checker *>(arena_take(core, sizeof(Checker)));
        core.check_pixels = static_cast<uint8_t *>(arena_take(core, rgb_picture < kLargestPicture ? rgb_picture : kLargestPicture));
        core.check_window = static_cast<uint8_t *>(arena_take(core, kWindowSize));
        if (core.chunk == nullptr || core.checker == nullptr || core.check_pixels == nullptr || core.check_window == nullptr) {
            core_fail(core, kOutOfMemory, nullptr, kNone);
            return;
        }
        // A host with a drive: an entry for each place of the drive's list.
        if (core.host.drive != nullptr && core.host.drive_name != nullptr) {
            core.drive = static_cast<DriveEntry *>(arena_take(core, kDriveMost * sizeof(DriveEntry)));
            core.remembered = static_cast<Remembered *>(arena_take(core, kRememberedMost * sizeof(Remembered)));
            if (core.drive == nullptr || core.remembered == nullptr) {
                core_fail(core, kOutOfMemory, nullptr, kNone);
                return;
            }
        }
    }

    char id_text[kIdTextSize];
    reason = read_show(core, id_text);
    if (reason != kNone) {
        const char *about = id_text[0] != '\0' ? id_text : nullptr;
        core_fail(core, reason, reason == kReadError ? kShowFile : about, kNone);
        return;
    }
    if (!order_begin(core)) {
        core_fail(core, kOutOfMemory, nullptr, kNone);
        return;
    }
    storage_settle_pending(core);

    // The files are opened in the order in which the show first names them. Their bodies
    // are read while the show plays, by the second decoders. A host whose storage cannot
    // be changed has none: for it every file is read to its end here. A file that cannot
    // be used is quarantined, and the others are opened as ever. A file the catalog has an
    // entry for is neither opened nor read.
    for (uint32_t index = 0; index < core.file_count; ++index) {
        core.files[index].fault = kNone;
        core.files[index].checked = 0;
    }
    catalog_read_internal(core);
    for (uint32_t index = 0; index < core.file_count && !core.invalid; ++index) {
        if (core.files[index].checked != 0 || core.files[index].fault != kNone) {
            continue;
        }
        if (core.checker == nullptr) {
            check_file(core, index);
        } else {
            open_file(core, index);
        }
    }
    core.check_at = 0;
    if (core.checker == nullptr) {
        core.check_done = 1;
    } else {
        check_passes_done(core);
    }
    if (!core.invalid) {
        order_start(core);
        playlist_start(core);
    }
}

}  // namespace

bool check_complete(const Core &core) {
    return core.check_done != 0;
}

bool drive_waits(const Core &core) {
    return core.drive != nullptr && core.upload.state == kUploadNone && (core.drive_check_at < core.drive_count || catalog_drive_loading(core));
}

void drive_file_name(uint32_t place, char *name) {
    const char head[] = "drive/";
    uint32_t length = 0;
    while (head[length] != '\0') {
        name[length] = head[length];
        ++length;
    }
    char figures[10];
    uint32_t count = 0;
    do {
        figures[count++] = static_cast<char>('0' + place % 10);
        place /= 10;
    } while (place != 0);
    while (count != 0) {
        name[length++] = figures[--count];
    }
    name[length] = '\0';
}

void drive_touch(Core &core) {
    if (core.drive == nullptr) {
        return;
    }
    const uint32_t number = core.host.drive(core.host.ctx);
    if (number == core.drive_number) {
        return;
    }
    if (check_complete(core) && core.upload.state == kUploadNone) {
        // The check may be in a file of the drive that went.
        core.checker->file.close();
        core.check_header_read = 0;
    }
    core.drive_number = number;
    core.drive_count = 0;
    core.drive_check_at = 0;
    tree_clear(core);
    catalog_drive_went(core);
    catalog_drive_plugged(core);
    if (catalog_drive_loading(core)) {
        // A host that is given the names: the drive's catalog is read first.
        player_drive_changed(core);
        order_drive_found(core);
        return;
    }
    drive_take_listed(core);
}

void drive_take_listed(Core &core) {
    const uint32_t number = core.drive_number;
    core.drive_count = 0;
    core.drive_check_at = 0;
    tree_clear(core);
    if (number != 0 && core.host.drive_list != nullptr) {
        // A host that lists the folder only when asked.
        core.host.drive_list(core.host.ctx, number);
    }
    char name[kDriveListedName];
    while (number != 0 && core.drive_count < kDriveMost &&
           core.host.drive_name(core.host.ctx, number, core.drive_count, name, sizeof name) == 1) {
        order_drive_named(core, core.drive_count, name);
        DriveEntry &entry = core.drive[core.drive_count++];
        entry.bytes = 0;
        entry.total_ms = 0;
        entry.id = 0;
        entry.state = kDriveToCheck;
        entry.fault = kNone;
    }
    // Every file has its id at once, in the order of the list, before it is checked; the
    // folders come after them.
    for (uint32_t place = 0; place < core.drive_count; ++place) {
        core.drive[place].id = free_drive_id(core);
    }
    tree_build(core);
    // The playlist goes on after an animation that left by the keys it had.
    player_drive_changed(core);
    order_drive_found(core);
}

void drive_left_out(Core &core, uint32_t place, Reason reason) {
    core.drive[place].fault = static_cast<uint8_t>(reason);
    if (core.host.log == nullptr) {
        return;
    }
    // `drive file <name> left out: <reason>`, with the name cut to what fits.
    char text[256];
    const char head[] = "drive file ";
    const char middle[] = " left out: ";
    const char *why = reason_name(reason);
    uint32_t length = 0;
    while (head[length] != '\0') {
        text[length] = head[length];
        ++length;
    }
    uint32_t why_length = 0;
    while (why[why_length] != '\0') {
        ++why_length;
    }
    const uint32_t room = sizeof text - length - (sizeof middle - 1) - why_length - 1;
    if (core.host.drive_name(core.host.ctx, core.drive_number, place, text + length, room) == 1) {
        while (text[length] != '\0') {
            ++length;
        }
    } else {
        drive_file_name(place, text + length);
        while (text[length] != '\0') {
            ++length;
        }
    }
    for (uint32_t at = 0; middle[at] != '\0'; ++at) {
        text[length++] = middle[at];
    }
    for (uint32_t at = 0; at < why_length; ++at) {
        text[length++] = why[at];
    }
    text[length] = '\0';
    core.host.log(core.host.ctx, text);
}

uint32_t drive_place_of(const Core &core, uint32_t id) {
    for (uint32_t place = 0; place < core.drive_count; ++place) {
        if (core.drive[place].state == kDriveInPlaylist && core.drive[place].id == id) {
            return place;
        }
    }
    return kDriveMost;
}

bool drive_has_id(const Core &core, uint32_t id) {
    return drive_place_of(core, id) != kDriveMost;
}

uint32_t drive_place_holding(const Core &core, uint32_t id) {
    for (uint32_t place = 0; core.drive != nullptr && place < core.drive_count; ++place) {
        if (core.drive[place].id == id && id != 0) {
            return place;
        }
    }
    return kDriveMost;
}

void drive_check_yields(Core &core) {
    if (core.checker != nullptr && core.check_header_read) {
        core.checker->file.close();
        core.check_header_read = 0;
    }
    catalog_drive_yields(core);
    order_drive_yields(core);
}

void check_file_left(Core &core, uint32_t file) {
    if (check_complete(core)) {
        return;
    }
    if (file < core.check_at) {
        --core.check_at;
    } else if (file == core.check_at && core.check_header_read) {
        core.checker->file.close();
        core.check_header_read = 0;
    }
    check_passes_done(core);
}

void check_after_start(Core &core, bool in_step, bool on_time) {
    if (core.invalid || (check_complete(core) && !drive_waits(core) && !catalog_rebuilding(core))) {
        return;
    }
    if ((!check_complete(core) || catalog_rebuilding(core)) && core.upload.state != kUploadNone) {
        // The upload has the second decoders; the check waits for them.
        return;
    }
    uint8_t steps;
    if (in_step && on_time) {
        if (core.check_row < kCheckMostSteps) {
            ++core.check_row;
        }
        steps = core.check_row;
    } else {
        core.check_row = 0;
        steps = core.check_idle >= kCheckLongestWait ? 1 : 0;
    }
    core.check_idle = steps != 0 ? 0 : static_cast<uint8_t>(core.check_idle + 1);
    for (uint8_t step = 0; step < steps && !core.invalid && (!check_complete(core) || drive_waits(core) || catalog_rebuilding(core)); ++step) {
        if (catalog_rebuilding(core)) {
            catalog_rebuild_step(core);
        } else if (!check_complete(core)) {
            check_step(core);
        } else {
            drive_step(core);
        }
    }
}

void drive_given_name(const Core &core, uint32_t place, char *name, uint32_t room) {
    if (core.host.drive_name(core.host.ctx, core.drive_number, place, name, room) != 1) {
        drive_file_name(place, name);
    }
}

bool is_file_fault(Reason reason) {
    return reason == kFileMissing || reason == kReadError || reason == kSizeMismatch || reason >= kTruncated;
}

void quarantine_file(Core &core, uint32_t file, Reason reason, uint8_t work, uint32_t record, uint64_t body_bytes) {
    FileInfo &info = core.files[file];
    if (info.fault != kNone) {
        return;
    }
    info.fault = static_cast<uint8_t>(reason);
    note_fault(core, work, info.name, record, body_bytes, reason);
    if (core.host.log != nullptr) {
        // `file <name> unavailable: <reason>`.
        char text[80];
        const char *parts[] = {"file ", info.name, " unavailable: ", reason_name(reason)};
        uint32_t length = 0;
        for (const char *part : parts) {
            for (; *part != '\0' && length + 1 < sizeof text; ++part) {
                text[length++] = *part;
            }
        }
        text[length] = '\0';
        core.host.log(core.host.ctx, text);
    }
    if (!core.starting) {
        player_file_failed(core, file);
    }
}

bool item_usable(const Core &core, uint32_t item) {
    const ItemInfo &info = core.items[item];
    if (!info.is_cycle) {
        return core.files[info.first].fault == kNone;
    }
    for (uint32_t entry = 0; entry < info.count; ++entry) {
        const ItemInfo &member = core.items[core.entries[info.first + entry]];
        if (core.files[member.first].fault == kNone) {
            return true;
        }
    }
    return false;
}

void note_fault(Core &core, uint8_t work, const char *name, uint32_t record, uint64_t body_bytes, Reason reason) {
    FaultContext &fault = core.fault;
    fault.present = 1;
    fault.work = work;
    fault.reason = static_cast<uint8_t>(reason);
    uint32_t length = 0;
    for (; name[length] != 0 && length + 1 < sizeof fault.name; ++length) {
        fault.name[length] = name[length];
    }
    fault.name[length] = 0;
    fault.record = record;
    fault.body_bytes = body_bytes;
}

void core_fail(Core &core, Reason reason, const char *about, Reason detail) {
    if (core.invalid) {
        return;
    }
    core.invalid = 1;
    core.error_text[0] = '\0';
    append(core, reason_name(reason));
    if (about != nullptr) {
        append(core, " ");
        append(core, about);
    }
    if (detail != kNone) {
        append(core, " ");
        append(core, reason_name(detail));
    }
    if (core.host.log != nullptr) {
        core.host.log(core.host.ctx, core.error_text);
    }
    // An invalid show takes no upload and plays nothing.
    upload_discard(core);
    player_halt(core);
}

}  // namespace odrig

odrig_core *odrig_core_begin(const odrig_host *host) {
    if (host == nullptr) {
        return nullptr;
    }
    odrig_core *core = static_cast<odrig_core *>(odrig::host_memory(*host, sizeof(odrig_core)));
    if (core == nullptr) {
        return nullptr;
    }
    core->state.host = *host;
    // The wall's default budget, the host's, in force until the budgets' file is read.
    core->state.wall_default = host->limit_default != nullptr ? host->limit_default(host->ctx) : 0;
    core->state.wall_budget = core->state.wall_default;
    core->state.starting = 1;
    odrig::start(core->state);
    odrig::player_start(core->state);
    core->state.starting = 0;
    return core;
}

uint32_t odrig_core_leg_count(const odrig_core *core) {
    return core != nullptr ? core->state.leg_count : 0;
}

int odrig_core_leg(const odrig_core *core, uint32_t index, odrig_leg *out) {
    if (core == nullptr || out == nullptr || index >= core->state.leg_count) {
        return 0;
    }
    const odrig::LegInfo &info = core->state.legs[index];
    out->leg = info.leg;
    out->pin = info.pin;
    out->led_count = info.count;
    out->rgb = core->state.led_data + 3u * info.first;
    return 1;
}

const char *odrig_core_error(const odrig_core *core) {
    if (core == nullptr || !core->state.invalid) {
        return nullptr;
    }
    return core->state.error_text;
}
