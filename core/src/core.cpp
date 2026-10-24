#include <string.h>

#include "arena.h"
#include "core_state.h"
#include "mapping.h"
#include "odrig_core.h"
#include "player.h"
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

// Opens one file of the show and the decoder on it, which reads the header, and compares
// the canvas with the mapping's. The palette and the frame records are not read. A file
// that cannot be used is quarantined.
void open_file(Core &core, uint32_t index) {
    const FileInfo &info = core.files[index];
    Reason reason = core.file.open(core.host, info.name);
    if (reason == kNone) {
        reason = core.decoder.open(&core.file, &core.inflate, core.window);
        if (reason == kNone && (core.decoder.width != core.width || core.decoder.height != core.height)) {
            reason = kSizeMismatch;
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
    reason = core.decoder.open(&core.file, &core.inflate, core.window);
    if (reason == kNone && (core.decoder.width != core.width || core.decoder.height != core.height)) {
        core.file.close();
        quarantine_file(core, index, kSizeMismatch, kWorkStart, 0, 0);
        return;
    }
    // Nothing waits on this check: it goes on through every slice of a settling.
    uint64_t total = 0;
    uint32_t record = 0;
    if (reason == kNone) {
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
            reason = core.decoder.finish();
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
    }
}

// What one step of the check of a file came to.
enum StepOutcome { kStepGoingOn, kStepWhole, kStepFault };

// One step of the check of a file through the second decoders: its header and canvas, one
// frame record, its end, after which nothing may follow, or one slice of the settling of a
// defect, after which the same step is taken again. When the file is whole, its size is the
// bytes the second source took and its length the sum of the durations; when it has a
// fault, `reason` says which, and `record` the frame record it was at.
StepOutcome check_file_step(Core &core, const char *name, Reason *reason, uint32_t *record) {
    Checker &checker = *core.checker;
    Reason found;
    *record = 0;
    if (!core.check_header_read) {
        checker.file.open_at(core.host, name);
        found = checker.decoder.open(&checker.file, &checker.inflate, core.check_window);
        if (found == kNone && (checker.decoder.width != core.width || checker.decoder.height != core.height)) {
            found = kSizeMismatch;
        }
        if (found == kNone) {
            memset(core.check_pixels, 0, checker.decoder.n);
            core.check_records_left = checker.decoder.frames;
            core.check_total_ms = 0;
            core.check_header_read = 1;
            return kStepGoingOn;
        }
    } else if (core.check_records_left != 0) {
        uint16_t duration = 0;
        *record = checker.decoder.frames - core.check_records_left;
        found = checker.decoder.next(core.check_pixels, &duration);
        if (found == kPendingWork) {
            return kStepGoingOn;
        }
        core.check_total_ms += duration;
        --core.check_records_left;
        if (found == kNone) {
            return kStepGoingOn;
        }
    } else {
        *record = checker.decoder.frames;
        found = checker.decoder.finish();
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

// Moves the check after the start past the files it has no more to do with: those that
// are quarantined. It is complete once it is past the last file.
void check_passes_done(Core &core) {
    while (core.check_at < core.file_count && core.files[core.check_at].fault != kNone) {
        ++core.check_at;
    }
    core.check_done = core.check_at >= core.file_count;
}

// One step of the check after the start, on the installed file it is at. A file read to
// its end was read whole; a file with a fault is quarantined, and the check goes on with
// the next one.
void check_step(Core &core) {
    FileInfo &info = core.files[core.check_at];
    if (info.fault != kNone) {
        // The player quarantined the file the check is at: it is not read again.
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
        ++core.check_at;
        check_passes_done(core);
    } else if (outcome == kStepFault) {
        quarantine_file(core, core.check_at, reason, kWorkStart, record, core.checker->decoder.body_read);
        ++core.check_at;
        check_passes_done(core);
    }
}

// The lowest id from kDriveFirstId up that no item of the show and no animation of the
// drive has, or 0 when there is none.
uint16_t free_drive_id(const Core &core) {
    for (uint32_t id = kDriveFirstId; id <= 65535; ++id) {
        bool taken = false;
        for (uint32_t item = 0; item < core.item_count && !taken; ++item) {
            taken = core.items[item].id == id;
        }
        for (uint32_t place = 0; place < core.drive_count && !taken; ++place) {
            taken = core.drive[place].state == kDriveInPlaylist && core.drive[place].id == id;
        }
        if (!taken) {
            return static_cast<uint16_t>(id);
        }
    }
    return 0;
}

// One step of the check of the drive's files, after the installed ones. A file that is
// whole and of the canvas becomes an animation of the playlist; one that is not is left out.
void drive_step(Core &core) {
    while (core.drive_check_at < core.drive_count && core.drive[core.drive_check_at].state != kDriveToCheck) {
        ++core.drive_check_at;
    }
    if (core.drive_check_at >= core.drive_count) {
        return;
    }
    const uint32_t place = core.drive_check_at;
    drive_file_name(place, core.drive_check_name);
    Reason reason = kNone;
    uint32_t record = 0;
    const StepOutcome outcome = check_file_step(core, core.drive_check_name, &reason, &record);
    DriveEntry &entry = core.drive[place];
    if (outcome == kStepWhole) {
        const uint16_t id = free_drive_id(core);
        ++core.drive_check_at;
        if (id == 0) {
            // Every id a drive's animation may have is taken.
            entry.state = kDriveLeftOut;
            drive_left_out(core, place, kDuplicateId);
            return;
        }
        entry.bytes = core.checker->file.taken;
        entry.total_ms = core.check_total_ms;
        entry.id = id;
        entry.state = kDriveInPlaylist;
        player_drive_joined(core, place);
    } else if (outcome == kStepFault) {
        ++core.drive_check_at;
        entry.state = kDriveLeftOut;
        char name[kFaultNameSize];
        drive_given_name(core, place, name, sizeof name);
        note_fault(core, kWorkDrive, name, record, core.checker->decoder.body_read, reason);
        drive_left_out(core, place, reason);
    }
}

void start(Core &core) {
    storage_clear_parts(core);

    core.line = static_cast<char *>(arena_take(core, ODRIG_LINE_MAX + 1));
    core.feed_reply = static_cast<char *>(arena_take(core, ODRIG_REPLY_MAX));
    if (core.line == nullptr || core.feed_reply == nullptr) {
        core_fail(core, kOutOfMemory, nullptr, kNone);
        return;
    }

    Reason reason = read_mapping(core);
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
            if (core.drive == nullptr) {
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
    storage_settle_pending(core);

    // The files are opened in the order in which the show first names them. Their bodies
    // are read while the show plays, by the second decoders. A host whose storage cannot
    // be changed has none: for it every file is read to its end here. A file that cannot
    // be used is quarantined, and the others are opened as ever.
    for (uint32_t index = 0; index < core.file_count; ++index) {
        core.files[index].fault = kNone;
    }
    for (uint32_t index = 0; index < core.file_count && !core.invalid; ++index) {
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
}

}  // namespace

bool check_complete(const Core &core) {
    return core.check_done != 0;
}

bool drive_waits(const Core &core) {
    return core.drive != nullptr && core.upload.state == kUploadNone && core.drive_check_at < core.drive_count;
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
    char probe[8];
    while (number != 0 && core.drive_count < kDriveMost &&
           core.host.drive_name(core.host.ctx, number, core.drive_count, probe, sizeof probe) == 1) {
        DriveEntry &entry = core.drive[core.drive_count++];
        entry.bytes = 0;
        entry.total_ms = 0;
        entry.id = 0;
        entry.state = kDriveToCheck;
    }
    player_drive_changed(core);
}

void drive_left_out(Core &core, uint32_t place, Reason reason) {
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

void drive_check_yields(Core &core) {
    if (core.drive != nullptr && check_complete(core) && core.check_header_read) {
        core.checker->file.close();
        core.check_header_read = 0;
    }
}

void check_after_start(Core &core, bool in_step, bool on_time) {
    if (core.invalid || (check_complete(core) && !drive_waits(core))) {
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
    for (uint8_t step = 0; step < steps && !core.invalid && (!check_complete(core) || drive_waits(core)); ++step) {
        if (!check_complete(core)) {
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
