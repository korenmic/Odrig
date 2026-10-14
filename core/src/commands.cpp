#include "commands.h"

#include "content.h"
#include "odrig_core.h"
#include "player.h"
#include "show.h"
#include "upload.h"

namespace odrig {

namespace {

uint32_t status(const Core &core, uint64_t now, Reply &reply) {
    reply.text("{\"ok\":true,\"on\":");
    reply.text(core.on ? "true" : "false");
    reply.text(",\"brightness\":");
    reply.number(core.brightness);
    reply.text(",\"playing\":");
    reply.id_or_null(core, core.playing);
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
    reply.text("}\n");
    return reply.length;
}

// The most words a command has. A line with more is no valid command.
const uint32_t kMostWords = 5;

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
    if (words.count >= 2 && words.is(1, "begin")) {
        uint32_t id;
        uint32_t bytes;
        char name[33];
        if (words.count != 5 || !number_word(words, 2, 1, 65535, &id) || words.size[3] < 1 || words.size[3] > 32 ||
            !number_word(words, 4, 1, 0xFFFFFFFFu, &bytes)) {
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
        if (!check_complete(core)) {
            // The check after the start has the decoders the check of an upload needs.
            return refuse(reply, "busy");
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

    if (words.is(0, "status")) {
        if (words.count != 1) {
            return refuse(reply, "bad-argument");
        }
        return status(core, now, reply);
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
        // An item of the show, else an animation of the drive.
        uint32_t item = all ? player_first_in_playlist(core) : kNothing;
        for (uint32_t position = 0; !all && item == kNothing && position < core.item_count; ++position) {
            if (core.items[position].id == id) {
                item = position;
            }
        }
        if (!all && item == kNothing && core.drive != nullptr && drive_has_id(core, id)) {
            item = kDriveBase + drive_place_of(core, id);
        }
        if (item == kNothing) {
            return refuse(reply, "unknown-id");
        }
        // An animation is played as its turn of the playlist, which goes on after it.
        if (!is_drive(item) && core.items[item].is_cycle) {
            player_play_cycle(core, item);
        } else {
            player_play_all(core, item);
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
        if (!check_complete(core)) {
            // The size of a file is known when the check after the start has read it.
            return refuse(reply, "busy");
        }
        return content_list(core, from, reply);
    }
    if (words.is(0, "remove")) {
        uint32_t id;
        if (words.count != 2 || !number_word(words, 1, 1, 65535, &id)) {
            return refuse(reply, "bad-argument");
        }
        if (core.invalid) {
            return refuse(reply, "show-invalid");
        }
        if (!check_complete(core)) {
            // The check after the start reads the files the removal would take away.
            return refuse(reply, "busy");
        }
        return content_remove(core, id, reply);
    }
    if (words.is(0, "upload")) {
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
