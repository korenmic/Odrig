#include "upload.h"

#include <string.h>

#include "catalog.h"
#include "crc32.h"
#include "drive.h"
#include "json_reader.h"
#include "player.h"
#include "storage.h"

namespace odrig {

namespace {

// The value of a character of the base64 alphabet, 0 to 63, or 64 for any other.
uint32_t base64_value(char character) {
    if (character >= 'A' && character <= 'Z') {
        return static_cast<uint32_t>(character - 'A');
    }
    if (character >= 'a' && character <= 'z') {
        return static_cast<uint32_t>(character - 'a') + 26;
    }
    if (character >= '0' && character <= '9') {
        return static_cast<uint32_t>(character - '0') + 52;
    }
    if (character == '-') {
        return 62;
    }
    return character == '_' ? 63 : 64;
}

// Decodes a text that base64_size has accepted into the bytes it stands for.
void base64_decode(const char *text, uint32_t length, uint8_t *bytes) {
    uint32_t held = 0;
    uint32_t bits = 0;
    for (uint32_t at = 0; at < length; ++at) {
        held = (held << 6) | base64_value(text[at]);
        bits += 6;
        if (bits >= 8) {
            bits -= 8;
            *bytes++ = static_cast<uint8_t>(held >> bits);
        }
    }
}

// The check has ended: its outcome waits for `upload end`.
void check_ended(Core &core, uint8_t outcome, Reason reason) {
    core.checker->file.close();
    core.upload.state = kUploadChecked;
    core.upload.outcome = outcome;
    core.upload.reason = static_cast<uint8_t>(reason);
}

void pace_down(Upload &upload) {
    if (upload.pace != 0) {
        upload.pace = static_cast<uint8_t>(upload.pace - 1);
    }
    upload.pace_fell = 1;
}

void pace_up(Upload &upload) {
    if (upload.pace != kUploadPaceMost) {
        upload.pace = static_cast<uint8_t>(upload.pace + 1);
    }
}

// One step of the check of an uploaded file: the header, one frame record, the end of the
// file, or one slice of the settling of a defect. Returns its charge, and says in
// `pending` whether it was a slice that did not end the settling.
uint32_t upload_step(Core &core, bool *pending) {
    *pending = false;
    Upload &upload = core.upload;
    Checker &checker = *core.checker;
    Reason reason;
    uint32_t record = 0;
    uint32_t charge = 0;
    if (!upload.header_read) {
        // The header is judged first, then the size against the mapping.
        checker.file.open_at(core.host, upload_part(core));
        reason = content_open(&checker.file, &checker.inflate, core.check_window, &checker.decoder, &core.check_content);
        if (reason == kNone && (core.check_content.width != core.width || core.check_content.height != core.height)) {
            reason = kSizeMismatch;
        }
        if (reason == kNone) {
            // A drawn payload is read and checked whole in one step, as one record.
            const bool drawn = is_drawn(core.check_content.type);
            if (!drawn) {
                memset(core.check_pixels, 0, checker.decoder.n);
            }
            upload.records_left = drawn ? 1 : checker.decoder.frames;
            upload.total_ms = 0;
            upload.header_read = 1;
            return 0;
        }
    } else if (upload.records_left != 0) {
        if (is_drawn(core.check_content.type)) {
            const Picture picture = {&checker.decoder, &checker.inflate, core.check_window, core.check_pixels};
            reason = drawn_read(&checker.file, core.check_content, nullptr, picture);
            upload.total_ms = core.check_content.loop_ms;
        } else {
            uint16_t duration = 0;
            record = checker.decoder.frames - upload.records_left;
            const uint64_t before = checker.decoder.body_read;
            const uint32_t given = checker.file.given();
            reason = checker.decoder.next(core.check_pixels, &duration);
            charge = checker.decoder.charge_since(before, given);
            if (reason == kPendingWork) {
                // A slice of the settling of a defect: the next step goes on with it.
                *pending = true;
                return charge;
            }
            upload.total_ms += duration;
        }
        --upload.records_left;
        if (reason == kNone) {
            return charge;
        }
    } else {
        // After the last record nothing may follow, and what was read back from storage
        // must be what was received.
        record = checker.decoder.frames;
        const bool drawn = is_drawn(core.check_content.type);
        const uint64_t before = checker.decoder.body_read;
        const uint32_t given = checker.file.given();
        reason = content_finish(&checker.file, &checker.decoder, core.check_content, upload.total_ms);
        charge = drawn ? 0 : checker.decoder.charge_since(before, given);
        if (reason == kPendingWork) {
            *pending = true;
            return charge;
        }
        if (reason == kNone) {
            const bool stored = checker.file.taken == upload.size && checker.file.crc == upload.crc;
            check_ended(core, stored ? kCheckPassed : kCheckStorageFailed, kNone);
            return charge;
        }
    }
    note_fault(core, kWorkUpload, upload.name, record, upload.header_read ? checker.decoder.body_read : 0, reason);
    check_ended(core, reason == kReadError ? kCheckStorageFailed : kCheckBadFile, reason);
    return charge;
}

}  // namespace

uint32_t base64_size(const char *text, uint32_t length) {
    const uint32_t rest = length % 4;
    if (length == 0 || rest == 1) {
        return 0;
    }
    for (uint32_t at = 0; at < length; ++at) {
        if (base64_value(text[at]) == 64) {
            return 0;
        }
    }
    // The last character of a group that is not whole carries bits of no byte.
    const uint32_t last = base64_value(text[length - 1]);
    if ((rest == 2 && (last & 0x0Fu) != 0) || (rest == 3 && (last & 0x03u) != 0)) {
        return 0;
    }
    const uint32_t size = length / 4 * 3 + (rest == 0 ? 0 : rest - 1);
    return size <= kChunkSize ? size : 0;
}

uint32_t base64_read(const char *text, uint32_t length, uint8_t *bytes) {
    const uint32_t size = base64_size(text, length);
    if (size != 0) base64_decode(text, length, bytes);
    return size;
}

void upload_touch(Core &core, uint64_t now) {
    if (core.upload.state != kUploadNone && static_cast<uint32_t>(now) - core.upload.progress >= kUploadQuietMs) {
        upload_discard(core);
    }
}

void upload_discard(Core &core) {
    if (core.upload.state == kUploadNone) {
        return;
    }
    core.checker->file.close();
    core.host.remove(core.host.ctx, upload_part(core));
    core.upload.state = kUploadNone;
}

void upload_refresh(Core &core, uint64_t now, bool new_second) {
    Upload &upload = core.upload;
    if (upload.state != kUploadChecking) {
        return;
    }
    // Every refresh of the check is progress, one that only pays a debt too.
    upload.progress = static_cast<uint32_t>(now);
    if (new_second) {
        const uint32_t rate = player_fps(core, now);
        if (rate < kUploadRateSlow) {
            pace_down(upload);
        } else if (rate >= kUploadRateSteady || (rate >= kUploadRateTrial && !upload.pace_fell)) {
            pace_up(upload);
        }
    }
    if (!upload.pace_fell && (now - core.t0) % 1000 >= kUploadMiddleMs && core.count_running <= kUploadTrialFewest) {
        // The rise was a trial that cost the board its rate: it is taken back.
        pace_down(upload);
    }
    const uint32_t budget = kUploadChargeUnit << upload.pace;
    const uint32_t owed = kUploadChargeUnit * upload.debt;
    if (owed >= budget) {
        upload.debt = static_cast<uint8_t>(upload.debt - budget / kUploadChargeUnit);
        return;
    }
    const uint32_t allowance = budget - owed;
    uint32_t charge = 0;
    bool pending = false;
    for (uint32_t steps = 0; upload.state == kUploadChecking && steps < kUploadStepsMost && charge < allowance; ++steps) {
        charge += upload_step(core, &pending);
    }
    // What the steps took beyond the allowance is owed, but not by a slice of settling,
    // whose charge is far above its work.
    const uint32_t over = pending || charge <= allowance ? 0 : (charge - allowance) / kUploadChargeUnit;
    upload.debt = static_cast<uint8_t>(over < kUploadDebtMost ? over : kUploadDebtMost);
}

uint32_t upload_begin(Core &core, uint64_t now, uint32_t id, const char *name, uint32_t bytes, Reply &reply, bool report_creation) {
    Upload &upload = core.upload;
    if (upload.state != kUploadNone) {
        return refuse(reply, "busy");
    }
    uint32_t position = 0;
    while (position < core.item_count && core.items[position].id != id) {
        ++position;
    }
    const bool is_new = position == core.item_count;
    if (!is_new && core.items[position].is_cycle) {
        return refuse(reply, "in-use");
    }
    if (is_new && drive_id_taken(core, id)) {
        // The id is a file's of the drive, or a folder's of its tree.
        return refuse(reply, "in-use");
    }
    // The file name is the item's own, or one that no item has.
    for (uint32_t other = 0; other < core.item_count; ++other) {
        const ItemInfo &item = core.items[other];
        if (other != position && !item.is_cycle && same_text(core.files[item.first].name, name)) {
            return refuse(reply, "in-use");
        }
    }
    if (is_new && (core.item_count >= core.item_capacity || core.file_count >= core.item_capacity)) {
        return refuse(reply, "no-space");
    }
    const odrig_host &host = core.host;
    if (report_creation && is_new && host.read_at != nullptr) {
        uint8_t probe = 0;
        if (host.read_at(host.ctx, name, 0, &probe, 1) >= 0) return refuse(reply, "in-use");
    }
    uint32_t free_bytes = 0;
    uint32_t total_bytes = 0;
    const bool told = host.space != nullptr && host.space(host.ctx, &free_bytes, &total_bytes) == 1;
    if (told && static_cast<uint64_t>(bytes) + bytes / 256 + kUploadReserve > free_bytes) {
        return refuse(reply, "no-space");
    }
    if (!told || !storage_changes(core) || core.checker == nullptr || !catalog_settle(core, kInternal) || host.write_open(host.ctx, kUploadPart) != 1) {
        return refuse(reply, "storage-error");
    }
    // The upload's check takes the second decoders from the check of a drive's file.
    drive_check_yields(core);
    upload.state = kUploadReceiving;
    upload.id = static_cast<uint16_t>(id);
    uint32_t length = 0;
    for (; name[length] != '\0'; ++length) {
        upload.name[length] = name[length];
    }
    upload.name[length] = '\0';
    upload.size = bytes;
    upload.received = 0;
    upload.crc = kCrcStart;
    upload.header_read = 0;
    upload.absent = 0;
    upload.folder = 0;
    upload.installed = 0;
    upload.progress = static_cast<uint32_t>(now);
    reply.text("{\"ok\":true,\"chunk\":");
    reply.number(kChunkSize);
    if (report_creation) {
        reply.text(",\"replacing\":");
        reply.text(is_new ? "false" : "true");
    }
    reply.text("}\n");
    return reply.length;
}

namespace {

// Makes each folder of a path of the drive that is not there, from the top down, on a host
// that makes folders: a folder of the index whose folder an operator removed while it was
// empty is there again before a file is written into it. False on a failed call.
ODRIG_NOINLINE bool folders_there(const Core &core, const char *path) {
    const odrig_host &host = core.host;
    if (host.make_folder == nullptr || path[0] == '\0') {
        return true;
    }
    char name[kDriveOpenRoom] = "drive/";
    uint32_t length = 6;
    for (const char *at = path;; ++at) {
        if (*at == '/' || *at == '\0') {
            name[length] = '\0';
            if (host.make_folder(host.ctx, name) != 1) {
                return false;
            }
            if (*at == '\0') {
                return true;
            }
        }
        name[length++] = *at;
    }
}

}  // namespace

uint32_t upload_begin_external(Core &core, uint64_t now, const char *name, uint32_t bytes, Reply &reply) {
    Upload &upload = core.upload;
    if (upload.state != kUploadNone || catalog_drive_loading(core)) {
        return refuse(reply, "busy");
    }
    if (!catalog_drive_writable(core)) {
        return refuse(reply, "read-only");
    }
    char parent[kDrivePathRoom];
    const char *base = name;
    for (const char *at = name; *at != '\0'; ++at) {
        if (*at == '/') base = at + 1;
    }
    const uint32_t parent_length = base == name ? 0 : static_cast<uint32_t>(base - name - 1);
    memcpy(parent, name, parent_length);
    parent[parent_length] = '\0';
    const uint32_t ordinal = drive_folder_with_path(core, parent);
    IndexFolder destination;
    if (ordinal == kNoFolder || !drive_folder(core, ordinal, destination)) {
        return refuse(reply, "unknown-id");
    }
    const odrig_host &host = core.host;
    uint64_t free_bytes = 0;
    uint64_t total_bytes = 0;
    if (host.drive_space != nullptr && host.drive_space(host.ctx, core.drive_number, &free_bytes, &total_bytes) == 1 &&
        static_cast<uint64_t>(bytes) + bytes / 256 + kUploadReserve > free_bytes) {
        return refuse(reply, "no-space");
    }
    upload.id = 0;
    if (core.checker == nullptr || !catalog_settle(core, kExternal) || !folders_there(core, parent) || host.write_open(host.ctx, upload_part(core)) != 1) {
        return refuse(reply, "storage-error");
    }
    drive_check_yields(core);
    upload.state = kUploadReceiving;
    uint32_t length = 0;
    for (; base[length] != '\0'; ++length) {
        upload.name[length] = base[length];
    }
    upload.name[length] = '\0';
    upload.size = bytes;
    upload.received = 0;
    upload.crc = kCrcStart;
    upload.header_read = 0;
    upload.absent = 0;
    upload.folder = destination.id;
    upload.installed = 0;
    upload.progress = static_cast<uint32_t>(now);
    reply.text("{\"ok\":true,\"chunk\":");
    reply.number(kChunkSize);
    reply.text("}\n");
    return reply.length;
}

uint32_t upload_begin_known(Core &core, uint64_t now, uint32_t id, const char *name, uint32_t bytes, uint32_t crc, Reply &reply) {
    const Upload &last = core.upload;
    uint32_t position = 0;
    while (position < core.item_count && core.items[position].id != id) {
        ++position;
    }
    if (last.installed && last.id == id && same_text(last.name, name) && last.size == bytes && crc_value(last.crc) == crc &&
        position < core.item_count && !core.items[position].is_cycle) {
        const FileInfo &file = core.files[core.items[position].first];
        if (same_text(file.name, name) && file.fault == kNone) {
            // The last upload installed this file, and the item holds it still: nothing is
            // sent, and nothing is written.
            reply.text("{\"ok\":true,\"unchanged\":true}\n");
            return reply.length;
        }
    }
    return upload_begin(core, now, id, name, bytes, reply, true);
}

uint32_t upload_expect(Core &core, uint32_t crc, Reply &reply) {
    Upload &upload = core.upload;
    if (upload.state == kUploadNone) {
        return refuse(reply, "no-upload");
    }
    if (upload.id == 0) {
        if (upload.received != 0 || crc != 0) return refuse(reply, "bad-argument");
        if (!upload_external_absent(core)) {
            upload_discard(core);
            return refuse(reply, "stale");
        }
        upload.absent = 1;
        return succeed(reply);
    }
    uint32_t position = 0;
    while (position < core.item_count && core.items[position].id != upload.id) {
        ++position;
    }
    if (position == core.item_count || core.items[position].is_cycle) {
        // The item the client read is gone.
        upload_discard(core);
        return refuse(reply, "stale");
    }
    const FileInfo &file = core.files[core.items[position].first];
    if (file.bytes > kExpectLargest) {
        return refuse(reply, "bad-argument");
    }
    // The file is read through the chunk buffer, which holds nothing between commands.
    const odrig_host &host = core.host;
    uint32_t running = kCrcStart;
    uint32_t offset = 0;
    for (;;) {
        const int32_t count = host.read_at(host.ctx, file.name, offset, core.chunk, kFileBufferSize);
        if (count < 0) {
            upload_discard(core);
            return refuse(reply, "storage-error");
        }
        if (count == 0) {
            break;
        }
        for (int32_t at = 0; at < count; ++at) {
            running = crc_add(running, core.chunk[at]);
        }
        offset += static_cast<uint32_t>(count);
        if (offset > kExpectLargest) {
            return refuse(reply, "bad-argument");
        }
    }
    if (crc_value(running) != crc) {
        upload_discard(core);
        return refuse(reply, "stale");
    }
    return succeed(reply);
}

uint32_t upload_data(Core &core, uint64_t now, uint32_t offset, const char *text, uint32_t length, uint32_t count, Reply &reply) {
    Upload &upload = core.upload;
    if (upload.state == kUploadNone) {
        return refuse(reply, "no-upload");
    }
    // The bytes follow the ones received so far and stay inside the size of the file.
    if (offset != upload.received || count > upload.size - upload.received) {
        return refuse(reply, "bad-offset");
    }
    const odrig_host &host = core.host;
    base64_decode(text, length, core.chunk);
    if (host.write(host.ctx, core.chunk, count) != 1) {
        upload_discard(core);
        return refuse(reply, "storage-error");
    }
    for (uint32_t at = 0; at < count; ++at) {
        upload.crc = crc_add(upload.crc, core.chunk[at]);
    }
    upload.received += count;
    upload.progress = static_cast<uint32_t>(now);
    if (upload.received == upload.size) {
        // The last byte: the file is closed, and its check begins with the next refresh, at
        // the first pace and with no debt.
        if (host.write_close(host.ctx) != 1) {
            upload_discard(core);
            return refuse(reply, "storage-error");
        }
        upload.state = kUploadChecking;
        upload.pace = kUploadPaceStart;
        upload.debt = 0;
        upload.pace_fell = 0;
    }
    reply.text("{\"ok\":true,\"received\":");
    reply.number(upload.received);
    reply.text("}\n");
    return reply.length;
}

uint32_t upload_end(Core &core, uint32_t crc, Reply &reply) {
    Upload &upload = core.upload;
    if (upload.state == kUploadNone) {
        return refuse(reply, "no-upload");
    }
    if (upload.received < upload.size) {
        return refuse(reply, "incomplete");
    }
    if (crc_value(upload.crc) != crc) {
        upload_discard(core);
        return refuse(reply, "bad-checksum");
    }
    if (upload.state == kUploadChecking) {
        return refuse(reply, "busy");
    }
    if (upload.outcome == kCheckBadFile) {
        const Reason reason = static_cast<Reason>(upload.reason);
        upload_discard(core);
        reply.text("{\"ok\":false,\"error\":\"bad-file\",\"reason\":\"");
        reply.text(reason_name(reason));
        reply.text("\"}\n");
        return reply.length;
    }
    if (upload.id == 0) {
        if (upload.absent && !upload_external_absent(core)) {
            upload_discard(core);
            return refuse(reply, "stale");
        }
        uint32_t id = 0;
        if (upload.outcome != kCheckPassed || !catalog_install_external(core, &id)) {
            upload_discard(core);
            return refuse(reply, "storage-error");
        }
        upload.state = kUploadNone;
        reply.text("{\"ok\":true,\"id\":");
        reply.number(id);
        reply.text("}\n");
        return reply.length;
    }
    if (upload.outcome != kCheckPassed || !storage_install_upload(core)) {
        upload_discard(core);
        return refuse(reply, "storage-error");
    }
    upload.state = kUploadNone;
    upload.installed = 1;
    return succeed(reply);
}

uint32_t upload_cancel(Core &core, Reply &reply) {
    if (core.upload.state == kUploadNone) {
        return refuse(reply, "no-upload");
    }
    upload_discard(core);
    return succeed(reply);
}

bool upload_external_name(const Core &core, char *into) {
    uint32_t length = 0;
    if (core.upload.folder != 0) {
        uint32_t ordinal = 0;
        if (drive_find(core, core.upload.folder, &ordinal) != 'd') return false;
        length = drive_folder_path(core, ordinal, into, kDrivePathRoom);
        if (length == 0 || length >= kDrivePathRoom - 1) return false;
        into[length++] = '/';
    }
    const uint32_t base = static_cast<uint32_t>(strlen(core.upload.name));
    if (base + length >= kDrivePathRoom) return false;
    memcpy(into + length, core.upload.name, base + 1);
    return true;
}

bool upload_external_absent(const Core &core) {
    char path[kDriveOpenRoom] = "drive/";
    if (!upload_external_name(core, path + 6) || drive_position_named(core, path + 6, static_cast<uint32_t>(strlen(path + 6))) != kNothing) return false;
    uint8_t probe = 0;
    return core.host.read_at != nullptr && core.host.read_at(core.host.ctx, path, 0, &probe, 1) < 0;
}

}  // namespace odrig
