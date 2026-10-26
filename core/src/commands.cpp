#include "commands.h"

#include "catalog.h"

#include "content.h"
#include "mapping_control.h"
#include "odrig_core.h"
#include "order.h"
#include "player.h"
#include "show.h"
#include "upload.h"

namespace odrig {

namespace {

// How far the check after the start is, and what is unavailable: the files whose check has
// ended and those it has still to read, of the show and of a drive, and the animations
// unavailable now. All 0 while the show is invalid.
struct Readiness {
    uint32_t checked;
    uint32_t to_check;
    uint32_t unavailable;
};

Readiness readiness_of(const Core &core) {
    Readiness counts = {0, 0, 0};
    if (core.invalid) {
        return counts;
    }
    if (catalog_rebuilding(core)) {
        // A rebuild's files: those it read and those it has still to read.
        counts.checked = core.rebuild_read;
        counts.to_check = core.rebuild_total > core.rebuild_read ? core.rebuild_total - core.rebuild_read : 1;
        for (uint32_t item = 0; item < core.item_count; ++item) {
            const ItemInfo &info = core.items[item];
            if (!info.is_cycle && core.files[info.first].fault != kNone) {
                ++counts.unavailable;
            }
        }
        return counts;
    }
    for (uint32_t file = 0; file < core.file_count; ++file) {
        const FileInfo &info = core.files[file];
        if (info.checked || info.fault != kNone) {
            ++counts.checked;
        } else {
            ++counts.to_check;
        }
    }
    for (uint32_t item = 0; item < core.item_count; ++item) {
        const ItemInfo &info = core.items[item];
        if (!info.is_cycle && core.files[info.first].fault != kNone) {
            ++counts.unavailable;
        }
    }
    for (uint32_t place = 0; core.drive != nullptr && place < core.drive_count; ++place) {
        const uint8_t state = core.drive[place].state;
        if (state == kDriveGone) {
            continue;
        }
        if (state == kDriveToCheck || state == kDriveStaged) {
            ++counts.to_check;
        } else {
            ++counts.checked;
            counts.unavailable += state == kDriveLeftOut ? 1 : 0;
        }
    }
    return counts;
}

// Writes the name of the file the check is at, as a JSON string, or null: of a rebuild the
// file it is at, and `catalog` while a drive's catalog is read.
void checking_of(const Core &core, Reply &reply) {
    if (!core.invalid && catalog_rebuilding(core)) {
        const uint32_t at = core.rebuild_at;
        char name[kFaultNameSize];
        if (core.rebuild == 1 + kInternal && at < core.file_count) {
            reply.text("\"");
            reply.text(core.files[at].name);
            reply.text("\"");
            return;
        }
        if (core.rebuild == 1 + kExternal && at < core.drive_count) {
            drive_given_name(core, at, name, sizeof name);
            reply.text("\"");
            reply.escaped(name);
            reply.text("\"");
            return;
        }
    }
    if (!core.invalid && catalog_drive_loading(core) && check_complete(core)) {
        reply.text("\"catalog\"");
        return;
    }
    if (!core.invalid && !check_complete(core) && core.check_at < core.file_count) {
        reply.text("\"");
        reply.text(core.files[core.check_at].name);
        reply.text("\"");
        return;
    }
    for (uint32_t place = core.drive_check_at; !core.invalid && core.drive != nullptr && place < core.drive_count; ++place) {
        if (core.drive[place].state == kDriveToCheck) {
            char name[kFaultNameSize];
            drive_given_name(core, place, name, sizeof name);
            reply.text("\"");
            reply.escaped(name);
            reply.text("\"");
            return;
        }
    }
    reply.text("null");
}

// Room for the text `about` gives: 95 bytes and the closing zero.
const uint32_t kAboutSize = 96;

// The names of the works a fault can come in, by their numbers.
const char *const kWorkNames[] = {"start", "start", "play", "upload", "drive"};

// The reply to `fault`: the context of the latest fault of a file, or null.
uint32_t fault_reply(const Core &core, Reply &reply) {
    const FaultContext &fault = core.fault;
    reply.text("{\"ok\":true,\"fault\":");
    if (!fault.present) {
        reply.text("null}\n");
        return reply.length;
    }
    reply.text("{\"work\":\"");
    reply.text(fault.work <= kWorkDrive ? kWorkNames[fault.work] : "start");
    reply.text("\",\"file\":\"");
    reply.escaped(fault.name);
    reply.text("\",\"record\":");
    reply.number(fault.record);
    reply.text(",\"bytes\":");
    reply.number(fault.body_bytes);
    reply.text(",\"reason\":\"");
    reply.text(reason_name(static_cast<Reason>(fault.reason)));
    reply.text("\"}}\n");
    return reply.length;
}

uint32_t status(const Core &core, uint64_t now, Reply &reply) {
    reply.text("{\"ok\":true,\"on\":");
    reply.text(core.on ? "true" : "false");
    reply.text(",\"brightness\":");
    reply.number(core.brightness);
    reply.text(",\"playing\":");
    if (core.playing == kPlaylist && core.tree_known && core.current != 0) {
        // The playlist of a folder of the drive, while the drive is in and holds it.
        reply.number(core.folders[core.current].id);
    } else {
        reply.id_or_null(core, core.playing);
    }
    reply.text(",\"animation\":");
    reply.id_or_null(core, core.playing == kNothing ? kNothing : core.shown);
    reply.text(",\"fps\":");
    reply.number(player_fps(core, now));
    reply.text(",\"error\":");
    if (core.invalid) {
        reply.text("\"");
        reply.text(core.error_text);
        reply.text("\"");
    } else {
        reply.text("null");
    }
    // The canvas of the installed mapping, which the core has while it has legs.
    if (core.leg_count != 0) {
        reply.text(",\"width\":");
        reply.number(core.width);
        reply.text(",\"height\":");
        reply.number(core.height);
    } else {
        reply.text(",\"width\":null,\"height\":null");
    }
    // How far the check is, and what is unavailable.
    const Readiness counts = readiness_of(core);
    reply.text(",\"readiness\":\"");
    reply.text(core.invalid ? "recovery" : counts.to_check != 0 ? "checking" : counts.unavailable != 0 ? "degraded" : "ready");
    reply.text("\",\"checked\":");
    reply.number(counts.checked);
    reply.text(",\"to_check\":");
    reply.number(counts.to_check);
    reply.text(",\"unavailable\":");
    reply.number(counts.unavailable);
    reply.text(",\"checking\":");
    checking_of(core, reply);
    // The name the host gives itself.
    char about[kAboutSize];
    reply.text(",\"host\":");
    if (core.host.about != nullptr && core.host.about(core.host.ctx, about, sizeof about) == 1) {
        about[sizeof about - 1] = '\0';
        reply.text("\"");
        reply.escaped(about);
        reply.text("\"");
    } else {
        reply.text("null");
    }
    uint32_t seed = 0;
    reply.text(",\"seed\":");
    if (player_seed(core, &seed)) {
        reply.number(seed);
    } else {
        reply.text("null");
    }
    // The seconds left in the current playlist's window, the last member.
    reply.text(",\"left\":");
    reply.number(player_window_left(core));
    reply.text("}\n");
    return reply.length;
}

// The most words a command has. A line with more is no valid command.
const uint32_t kMostWords = 6;

// The words of a line. The line is split at every space, so it has one word more than it
// has spaces, and a word may be empty. The first kMostWords of them are kept.
struct Words {
    void split(const char *line, uint32_t length) {
        count = 0;
        uint32_t begin = 0;
        for (uint32_t at = 0; at <= length; ++at) {
            if (at < length && line[at] != ' ') {
                continue;
            }
            if (count < kMostWords) {
                text[count] = line + begin;
                size[count] = at - begin;
            }
            ++count;
            begin = at + 1;
        }
    }

    // Whether a word is this text, byte for byte.
    bool is(uint32_t word, const char *wanted) const {
        const char *given = text[word];
        uint32_t at = 0;
        while (at < size[word] && wanted[at] != '\0' && given[at] == wanted[at]) {
            ++at;
        }
        return at == size[word] && wanted[at] == '\0';
    }

    const char *text[kMostWords];
    uint32_t size[kMostWords];
    uint32_t count;
};

// The value of a word that must be a number from `least` to `most`, written in decimal
// digits only. False for an empty word, for any other character and for any other value.
bool number_word(const Words &words, uint32_t word, uint32_t least, uint32_t most, uint32_t *value) {
    const char *text = words.text[word];
    const uint32_t length = words.size[word];
    if (length == 0) {
        return false;
    }
    uint64_t result = 0;
    for (uint32_t at = 0; at < length; ++at) {
        if (text[at] < '0' || text[at] > '9') {
            return false;
        }
        if (result <= most) {
            result = result * 10 + static_cast<uint32_t>(text[at] - '0');
        }
    }
    if (result < least || result > most) {
        return false;
    }
    *value = static_cast<uint32_t>(result);
    return true;
}

// The value of a word that must be exactly eight hexadecimal digits, 0-9 and a-f.
bool crc_word(const Words &words, uint32_t word, uint32_t *value) {
    if (words.size[word] != 8) {
        return false;
    }
    uint32_t result = 0;
    for (uint32_t at = 0; at < 8; ++at) {
        const char digit = words.text[word][at];
        if (digit >= '0' && digit <= '9') {
            result = result << 4 | static_cast<uint32_t>(digit - '0');
        } else if (digit >= 'a' && digit <= 'f') {
            result = result << 4 | static_cast<uint32_t>(digit - 'a' + 10);
        } else {
            return false;
        }
    }
    *value = result;
    return true;
}

// The four `upload` commands. The words are read first, then the show is asked for.
uint32_t upload(Core &core, uint64_t now, const Words &words, Reply &reply) {
    if (words.count >= 3 && words.is(1, "begin") && words.is(2, "external")) {
        uint32_t bytes;
        uint32_t crc = 0;
        char name[33];
        if ((words.count != 5 && words.count != 6) || words.size[3] < 1 || words.size[3] > 32 || !number_word(words, 4, 1, 0xFFFFFFFFu, &bytes) ||
            (words.count == 6 && !crc_word(words, 5, &crc))) {
            return refuse(reply, "bad-argument");
        }
        for (uint32_t at = 0; at < words.size[3]; ++at) {
            name[at] = words.text[3][at];
        }
        name[words.size[3]] = '\0';
        if (!is_file_name(name)) {
            return refuse(reply, "bad-argument");
        }
        if (core.invalid) {
            return refuse(reply, "show-invalid");
        }
        return upload_begin_external(core, now, name, bytes, reply);
    }
    if (words.count >= 2 && words.is(1, "begin")) {
        uint32_t id;
        uint32_t bytes;
        uint32_t crc = 0;
        char name[33];
        if ((words.count != 5 && words.count != 6) || !number_word(words, 2, 1, 65535, &id) || words.size[3] < 1 || words.size[3] > 32 ||
            !number_word(words, 4, 1, 0xFFFFFFFFu, &bytes) || (words.count == 6 && !crc_word(words, 5, &crc))) {
            return refuse(reply, "bad-argument");
        }
        for (uint32_t at = 0; at < words.size[3]; ++at) {
            name[at] = words.text[3][at];
        }
        name[words.size[3]] = '\0';
        if (!is_file_name(name)) {
            return refuse(reply, "bad-argument");
        }
        if (core.invalid) {
            return refuse(reply, "show-invalid");
        }
        if (words.count == 6) {
            return upload_begin_known(core, now, id, name, bytes, crc, reply);
        }
        return upload_begin(core, now, id, name, bytes, reply);
    }
    if (words.count >= 2 && words.is(1, "data")) {
        uint32_t offset;
        uint32_t count = 0;
        if (words.count != 4 || !number_word(words, 2, 0, 0xFFFFFFFFu, &offset) ||
            (count = base64_size(words.text[3], words.size[3])) == 0) {
            return refuse(reply, "bad-argument");
        }
        if (core.invalid) {
            return refuse(reply, "show-invalid");
        }
        return upload_data(core, now, offset, words.text[3], words.size[3], count, reply);
    }
    if (words.count >= 2 && words.is(1, "end")) {
        uint32_t crc;
        if (words.count != 3 || !crc_word(words, 2, &crc)) {
            return refuse(reply, "bad-argument");
        }
        if (core.invalid) {
            return refuse(reply, "show-invalid");
        }
        return upload_end(core, crc, reply);
    }
    if (words.count == 2 && words.is(1, "cancel")) {
        if (core.invalid) {
            return refuse(reply, "show-invalid");
        }
        return upload_cancel(core, reply);
    }
    if (words.count >= 2 && words.is(1, "expect")) {
        uint32_t crc;
        if (words.count != 3 || !crc_word(words, 2, &crc)) {
            return refuse(reply, "bad-argument");
        }
        if (core.invalid) {
            return refuse(reply, "show-invalid");
        }
        return upload_expect(core, crc, reply);
    }
    return refuse(reply, "bad-argument");
}

}  // namespace

uint32_t command_answer(Core &core, uint64_t now_ms, const char *line, uint32_t length, char *bytes) {
    const uint64_t now = clock_touch(core, now_ms);
    upload_touch(core, now);
    Reply reply;
    reply.bytes = bytes;
    reply.length = 0;

    if (length != 0 && line[length - 1] == '\n') {
        --length;
    }
    if (length != 0 && line[length - 1] == '\r') {
        --length;
    }
    if (length > ODRIG_LINE_MAX) {
        return refuse(reply, "line-too-long");
    }

    Words words;
    words.split(line, length);

    if (words.is(0, "mapping")) {
        if (words.count == 2 && words.is(1, "get")) return mapping_get(core, reply);
        if (words.count == 3 && words.is(1, "test") && (words.is(2, "on") || words.is(2, "off"))) {
            return mapping_test(core, words.is(2, "on"), 0, reply);
        }
        uint32_t snake;
        if (words.count == 4 && words.is(1, "test") && words.is(2, "snake") && number_word(words, 3, 1, 20, &snake)) {
            return mapping_test(core, true, snake, reply);
        }
        uint32_t revision;
        if (words.count == 4 && words.is(1, "set") && number_word(words, 2, 0, 0xFFFFFFFFu, &revision)) {
            if (catalog_rebuilding(core)) return refuse(reply, "busy");
            return mapping_set(core, revision, words.text[3], words.size[3], reply);
        }
        return refuse(reply, "bad-argument");
    }
    if (words.is(0, "catalog")) {
        if (words.count == 1) {
            return catalog_reply(core, reply);
        }
        if (words.count == 2 && words.is(1, "cancel")) {
            return catalog_cancel(core, reply);
        }
        if (words.count == 3 && words.is(1, "rebuild") && (words.is(2, "internal") || words.is(2, "external"))) {
            if (core.invalid) {
                return refuse(reply, "show-invalid");
            }
            return catalog_rebuild(core, words.is(2, "internal") ? kInternal : kExternal, reply);
        }
        return refuse(reply, "bad-argument");
    }
    if (words.is(0, "status")) {
        if (words.count != 1) {
            return refuse(reply, "bad-argument");
        }
        return status(core, now, reply);
    }
    if (words.is(0, "fault")) {
        if (words.count != 1) {
            return refuse(reply, "bad-argument");
        }
        return fault_reply(core, reply);
    }
    const bool switch_on = words.is(0, "on");
    if (switch_on || words.is(0, "off")) {
        if (words.count != 1) {
            return refuse(reply, "bad-argument");
        }
        core.on = switch_on ? 1 : 0;
        return succeed(reply);
    }
    if (words.is(0, "brightness")) {
        uint32_t value;
        if (words.count != 2 || !number_word(words, 1, 0, 255, &value)) {
            return refuse(reply, "bad-argument");
        }
        player_set_brightness(core, static_cast<uint8_t>(value));
        return succeed(reply);
    }
    if (words.is(0, "play")) {
        const bool all = words.count == 2 && words.is(1, "all");
        uint32_t id = 0;
        if (!all && (words.count != 2 || !number_word(words, 1, 1, 65535, &id))) {
            return refuse(reply, "bad-argument");
        }
        if (core.invalid) {
            return refuse(reply, "show-invalid");
        }
        // The root for `play all`; else an item of the show, an animation of the drive or
        // a folder of the drive's tree.
        uint32_t folder = all ? 0 : kFolderMost;
        uint32_t item = kNothing;
        if (all) {
            tree_choose(core, 0);
            player_playlist_chosen(core, core.latest);
            item = player_first_in_playlist(core);
        }
        for (uint32_t position = 0; !all && item == kNothing && position < core.item_count; ++position) {
            if (core.items[position].id == id) {
                item = position;
            }
        }
        if (!all && item == kNothing && core.drive != nullptr && drive_has_id(core, id)) {
            item = kDriveBase + drive_place_of(core, id);
        }
        if (!all && item == kNothing && drive_place_holding(core, id) != kDriveMost &&
            core.drive[drive_place_holding(core, id)].state == kDriveLeftOut) {
            // A file of the drive that was left out for a fault.
            return refuse(reply, "unavailable");
        }
        // A folder of the drive's tree: its playlist becomes current, and it plays from
        // its first animation, or the root does in its place.
        if (!all && item == kNothing) {
            folder = tree_folder_with_id(core, id);
            if (folder != kFolderMost) {
                tree_choose(core, folder);
                player_playlist_chosen(core, core.latest);
                item = player_first_in_playlist(core);
            }
        }
        if (item == kNothing && (all || folder == kFolderMost)) {
            // `play all` while the playlist has no animation, or an id that nothing has.
            return refuse(reply, "unknown-id");
        }
        if (item != kNothing && !is_drive(item) && !item_usable(core, item)) {
            // A quarantined animation, or a cycle that lists only such: nothing is read.
            return refuse(reply, "unavailable");
        }
        if (item == kNothing) {
            // A folder chosen while nothing plays anywhere: the choice stands.
            return succeed(reply);
        }
        core.mapping_test = 0;
        // An animation is played as its turn of the playlist, which goes on after it: a
        // jump, unless a playlist was chosen and plays from its first.
        if (!is_drive(item) && core.items[item].is_cycle) {
            player_play_cycle(core, item);
        } else if (folder != kFolderMost) {
            player_play_all(core, item);
        } else {
            player_jump(core, item);
        }
        return succeed(reply);
    }
    if (words.is(0, "space")) {
        if (words.count != 1) {
            return refuse(reply, "bad-argument");
        }
        return content_space(core, reply);
    }
    if (words.is(0, "list")) {
        uint32_t from = 0;
        if (words.count > 2 || (words.count == 2 && !number_word(words, 1, 0, 65535, &from))) {
            return refuse(reply, "bad-argument");
        }
        if (core.invalid) {
            return refuse(reply, "show-invalid");
        }
        return content_list(core, from, reply);
    }
    if (words.is(0, "order")) {
        uint32_t from = 0;
        if (words.count >= 2 && words.count <= 3 && words.is(1, "get") && (words.count == 2 || number_word(words, 2, 0, 65535, &from))) {
            if (core.invalid) return refuse(reply, "show-invalid");
            return order_get(core, from, reply);
        }
        uint32_t revision, id, before = 0;
        if (words.count == 5 && words.is(1, "move") && number_word(words, 2, 0, 0xFFFFFFFFu, &revision) && number_word(words, 3, 1, 65535, &id) &&
            (words.is(4, "end") || number_word(words, 4, 1, 65535, &before))) {
            if (!core.invalid && catalog_rebuilding(core)) return refuse(reply, "busy");
            return order_move(core, revision, id, before, reply);
        }
        return refuse(reply, "bad-argument");
    }
    if (words.is(0, "read")) {
        uint32_t id;
        uint32_t offset;
        if (words.count != 3 || !number_word(words, 1, 1, 65535, &id) || !number_word(words, 2, 0, 0xFFFFFFFFu, &offset)) {
            return refuse(reply, "bad-argument");
        }
        if (core.invalid) {
            return refuse(reply, "show-invalid");
        }
        return content_read(core, id, offset, reply);
    }
    if (words.is(0, "ignore")) {
        uint32_t id, value;
        if (words.count != 3 || !number_word(words, 1, 1, 65535, &id) || !number_word(words, 2, 0, 1, &value)) return refuse(reply, "bad-argument");
        if (core.invalid) return refuse(reply, "show-invalid");
        if (core.mapping_test || catalog_rebuilding(core)) return refuse(reply, "busy");
        return content_ignore(core, id, value != 0, reply);
    }
    if (words.is(0, "remove") && words.count == 3 && words.is(1, "many")) {
        uint16_t ids[32];
        uint32_t count = 0, value = 0, digits = 0;
        for (uint32_t at = 0; at <= words.size[2]; ++at) {
            const char c = at < words.size[2] ? words.text[2][at] : ',';
            if (c == ',') {
                if (digits == 0 || value == 0 || count == 32) return refuse(reply, "bad-argument");
                for (uint32_t before = 0; before < count; ++before) if (ids[before] == value) return refuse(reply, "bad-argument");
                ids[count++] = static_cast<uint16_t>(value);
                value = digits = 0;
            } else {
                if (c < '0' || c > '9' || value > 6553 || (value == 6553 && c > '5')) return refuse(reply, "bad-argument");
                value = value * 10 + static_cast<uint32_t>(c - '0');
                ++digits;
            }
        }
        if (core.invalid) return refuse(reply, "show-invalid");
        if (core.mapping_test || catalog_rebuilding(core)) return refuse(reply, "busy");
        return content_remove_many(core, ids, count, reply);
    }
    if (words.is(0, "remove")) {
        uint32_t id;
        if (words.count != 2 || !number_word(words, 1, 1, 65535, &id)) {
            return refuse(reply, "bad-argument");
        }
        if (core.invalid) {
            return refuse(reply, "show-invalid");
        }
        if (core.mapping_test || catalog_rebuilding(core)) return refuse(reply, "busy");
        return content_remove(core, id, reply);
    }
    if (words.is(0, "upload")) {
        if (core.mapping_test || (catalog_rebuilding(core) && words.count >= 2 && words.is(1, "begin"))) return refuse(reply, "busy");
        return upload(core, now, words, reply);
    }
    return refuse(reply, "unknown-command");
}

}  // namespace odrig

size_t odrig_core_command(odrig_core *core, uint64_t now_ms, const char *line, size_t length,
                          char *reply, size_t capacity) {
    if (core == nullptr || (line == nullptr && length != 0) || reply == nullptr || capacity < ODRIG_REPLY_MAX) {
        return 0;
    }
    // A line is refused for its length long before its length could not be counted.
    const uint32_t counted = length > 0xFFFFu ? 0xFFFFu : static_cast<uint32_t>(length);
    return odrig::command_answer(core->state, now_ms, line, counted, reply);
}

void odrig_core_feed(odrig_core *core, uint64_t now_ms, const uint8_t *bytes, size_t length,
                     odrig_reply_fn on_reply, void *reply_ctx) {
    if (core == nullptr || (bytes == nullptr && length != 0)) {
        return;
    }
    odrig::Core &state = core->state;
    odrig::upload_touch(state, odrig::clock_touch(state, now_ms));
    if (state.line == nullptr || state.feed_reply == nullptr) {
        return;
    }
    char *reply = state.feed_reply;
    for (size_t at = 0; at < length; ++at) {
        const char byte = static_cast<char>(bytes[at]);
        if (byte != '\n') {
            // Room for a whole line and the carriage return of a line that ends in one.
            if (state.line_length < ODRIG_LINE_MAX + 1) {
                state.line[state.line_length++] = byte;
            } else {
                state.line_over = 1;
            }
            continue;
        }
        // A line that outgrew the room is too long whatever it ends in. The host is handed
        // the line as the command entry reads it: without one carriage return at its end,
        // and its first ODRIG_LINE_MAX characters when it is longer.
        uint32_t kept = state.line_length;
        uint32_t reply_length;
        if (state.line_over) {
            odrig::Reply refusal;
            refusal.bytes = reply;
            refusal.length = 0;
            reply_length = odrig::refuse(refusal, "line-too-long");
        } else {
            reply_length = odrig::command_answer(state, now_ms, state.line, kept, reply);
            if (kept != 0 && state.line[kept - 1] == '\r') {
                --kept;
            }
        }
        if (kept > ODRIG_LINE_MAX) {
            kept = ODRIG_LINE_MAX;
        }
        state.line_length = 0;
        state.line_over = 0;
        if (on_reply != nullptr) {
            on_reply(reply_ctx, state.line, kept, reply, reply_length);
        }
    }
}
