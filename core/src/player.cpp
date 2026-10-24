#include "player.h"

#include <string.h>

#include "odrig_core.h"
#include "text.h"
#include "upload.h"

namespace odrig {

namespace {

void close_stream(Core &core) {
    core.file.close();
    core.stream_open = 0;
    core.stream_drawn = 0;
}

// The length of the animation at a position of the playlist, 0 while it is not known. A
// drive's animation is in the playlist only once its length is known.
uint64_t length_of(const Core &core, uint32_t animation) {
    if (is_drive(animation)) {
        return core.drive[animation - kDriveBase].total_ms;
    }
    return core.files[core.items[animation].first].total_ms;
}

// The loops and the longest time of an animation's turn, as its item gives them, 0 when
// it gives none. A drive's animation has neither.
uint32_t loops_of(const Core &core, uint32_t animation) {
    return is_drive(animation) ? 0 : core.items[animation].count;
}

uint32_t seconds_of(const Core &core, uint32_t animation) {
    return is_drive(animation) ? 0 : core.items[animation].seconds;
}

// What the animation at a position of the playlist holds, as its header says.
uint8_t type_of(const Core &core, uint32_t animation) {
    if (is_drive(animation)) {
        return core.drive[animation - kDriveBase].type;
    }
    return core.files[core.items[animation].first].type;
}

// The longest a turn may last, rounded up to whole passes for a text: its pass is never
// cut off by the time a turn is given.
uint64_t whole_passes(const Core &core, uint32_t animation, uint64_t turn) {
    const uint64_t loop = length_of(core, animation);
    if (type_of(core, animation) != kTypeText || loop == 0) {
        return turn;
    }
    return (turn + loop - 1) / loop * loop;
}

// Whether a position of the playlist holds an animation that plays: an animation item of
// the show, or a file of the drive that is in the playlist.
bool plays(const Core &core, uint32_t position) {
    if (is_drive(position)) {
        const uint32_t place = position - kDriveBase;
        return place < core.drive_count && core.drive[place].state == kDriveInPlaylist;
    }
    return position < core.item_count && !core.items[position].is_cycle && !core.items[position].ignored;
}

// The position after this one in the order of the playlist: the show's items, then the
// drive's places, then the first item again.
uint32_t following(const Core &core, uint32_t position) {
    if (is_drive(position)) {
        const uint32_t place = position - kDriveBase + 1;
        return place < core.drive_count ? kDriveBase + place : 0;
    }
    if (position + 1 < core.item_count) {
        return position + 1;
    }
    return core.drive_count != 0 ? kDriveBase : 0;
}

// Opens the file of an animation for one turn and one loop, with the pixel buffer all
// zero and no frame decoded.
Reason open_stream(Core &core, uint32_t animation, uint64_t turn, uint64_t loop) {
    close_stream(core);
    char drive_name[kDriveNameSize];
    const char *name = drive_name;
    if (is_drive(animation)) {
        drive_file_name(animation - kDriveBase, drive_name);
    } else {
        name = core.files[core.items[animation].first].name;
    }
    Reason reason = core.file.open(core.host, name);
    if (reason != kNone) {
        return reason;
    }
    ContentHeader header;
    reason = content_open(&core.file, &core.inflate, core.window, &core.decoder, &header);
    if (reason != kNone) {
        return reason;
    }
    if (header.width != core.width || header.height != core.height) {
        return kSizeMismatch;
    }
    if (is_drawn(header.type)) {
        // The payload is held whole in the window, which no frames file uses meanwhile.
        reason = text_read(&core.file, header, core.window);
        core.file.close();
        if (reason != kNone) {
            return reason;
        }
        core.stream_open = 1;
        core.stream_drawn = 1;
        core.stream_item = animation;
        core.stream_turn = turn;
        core.stream_loop = loop;
        return kNone;
    }
    memset(core.pixels, 0, core.decoder.n);
    core.stream_open = 1;
    core.stream_item = animation;
    core.stream_turn = turn;
    core.stream_loop = loop;
    core.frame_end = 0;
    core.stream_records = 0;
    return kNone;
}

// Decodes the first loop of an animation whose length is not known, up to a time since
// the start of its turn. When every record was decoded and the time lies at their end or
// beyond it, their durations add up to the length, and it is noted.
Reason first_loop_to(Core &core, uint32_t animation, uint64_t turn, uint64_t time) {
    Reason reason = kNone;
    if (!core.stream_open || core.stream_item != animation || core.stream_turn != turn || core.stream_loop != 0) {
        reason = open_stream(core, animation, turn, 0);
    }
    while (reason == kNone && core.frame_end <= time && core.stream_records < core.decoder.frames) {
        uint16_t duration = 0;
        reason = core.decoder.next(core.pixels, &duration);
        core.frame_end += duration;
        ++core.stream_records;
    }
    if (reason == kNone && core.frame_end <= time) {
        // A drive's animation has its length before it plays: here it is an item's file.
        core.files[core.items[animation].first].total_ms = core.frame_end;
    }
    return reason;
}

// Brings the pixel buffer to the picture an animation shows at a time since the start of
// its turn. While the length of the animation is not known, the time lies in its first
// loop. Once it is known, the loop and the place in it are found by division.
Reason show_at(Core &core, uint32_t animation, uint64_t turn, uint64_t in_turn) {
    if (type_of(core, animation) == kTypeText) {
        const uint64_t pass = length_of(core, animation);
        if (pass == 0) {
            return kLoopMismatch;
        }
        if (!core.stream_open || !core.stream_drawn || core.stream_item != animation || core.stream_turn != turn) {
            const Reason reason = open_stream(core, animation, turn, 0);
            if (reason != kNone) {
                return reason;
            }
        }
        core.decoder.colours = 0;
        text_draw(core.window, core.width, core.height, in_turn % pass, core.pixels);
        return kNone;
    }
    uint64_t length = length_of(core, animation);
    if (length == 0) {
        const Reason reason = first_loop_to(core, animation, turn, in_turn);
        length = length_of(core, animation);
        if (reason != kNone || length == 0) {
            return reason;
        }
    }
    const uint64_t loop = in_turn / length;
    const uint64_t within = in_turn % length;
    Reason reason = kNone;
    if (!core.stream_open || core.stream_item != animation || core.stream_turn != turn || core.stream_loop != loop) {
        reason = open_stream(core, animation, turn, loop);
    }
    while (reason == kNone && core.frame_end <= within) {
        uint16_t duration = 0;
        reason = core.decoder.next(core.pixels, &duration);
        core.frame_end += duration;
    }
    return reason;
}

// How long the turn of the animation at this position lasts in the playlist, in
// milliseconds. The length of the animation is known.
uint64_t turn_ms(const Core &core, uint32_t position) {
    const uint64_t loop = length_of(core, position);
    uint64_t loops = loops_of(core, position);
    if (loops == 0) {
        loops = (1000ull * core.min_seconds + loop - 1) / loop;
    }
    const uint64_t turn = loops * loop;
    const uint64_t longest = 1000ull * seconds_of(core, position);
    return longest != 0 && turn > longest ? whole_passes(core, position, longest) : turn;
}

// The position of the animation after this one in the playlist, the first one after the
// last; this one again when no other plays.
uint32_t next_animation(const Core &core, uint32_t position) {
    uint32_t at = position;
    for (uint32_t step = 0; step <= core.item_count + core.drive_count; ++step) {
        at = following(core, at);
        if (plays(core, at)) {
            return at;
        }
    }
    return kNothing;
}

// Moves the playlist on to the turn that a moment falls into, and gives the time since
// that turn began. A turn begins where the one before it ended, however late the moment is.
//
// Whether a turn has ended follows from the length of its animation. While that is not
// known, the first loop is decoded up to the moment, or up to the longest time the turn
// may last when the moment lies beyond it. When the loop ends on the way, the length is
// known. When it does not, the animation is in its first loop and its turn goes on; or
// the loop is longer than the longest time, and the turn ended there.
Reason playlist_turn(Core &core, uint64_t now, uint64_t *in_turn) {
    uint64_t elapsed = now - core.zero;
    bool rounds_taken = false;
    for (;;) {
        const uint32_t seconds = seconds_of(core, core.turn_item);
        uint64_t turn;
        if (length_of(core, core.turn_item) != 0) {
            turn = turn_ms(core, core.turn_item);
            if (elapsed < turn) {
                *in_turn = elapsed;
                return kNone;
            }
        } else {
            const uint64_t longest = 1000ull * seconds;
            const bool beyond = seconds != 0 && elapsed >= longest;
            const Reason reason = first_loop_to(core, core.turn_item, core.turn_number, beyond ? longest : elapsed);
            if (reason != kNone) {
                return reason;
            }
            if (length_of(core, core.turn_item) != 0) {
                continue;
            }
            if (!beyond) {
                *in_turn = elapsed;
                return kNone;
            }
            turn = longest;
        }
        if (!rounds_taken && plays(core, core.turn_item)) {
            // Whole rounds of the playlist are taken off at once when the length of every
            // animation is known, so that a long time without a refresh costs one walk
            // over the items.
            rounds_taken = true;
            uint64_t round = 0;
            bool all_known = true;
            for (uint32_t position = 0; position < core.item_count && all_known; ++position) {
                if (!core.items[position].is_cycle && !core.items[position].ignored) {
                    all_known = core.files[core.items[position].first].total_ms != 0;
                    round += all_known ? turn_ms(core, position) : 0;
                }
            }
            for (uint32_t place = 0; place < core.drive_count && all_known; ++place) {
                if (core.drive[place].state == kDriveInPlaylist) {
                    round += turn_ms(core, kDriveBase + place);
                }
            }
            if (all_known && round != 0 && elapsed >= round) {
                core.zero += elapsed / round * round;
                elapsed %= round;
                ++core.turn_number;
                continue;
            }
        }
        core.zero += turn;
        elapsed -= turn;
        core.turn_item = next_animation(core, core.turn_item);
        if (core.turn_item == kNothing) {
            close_stream(core);
            core.playing = core.shown = kNothing;
            *in_turn = 0;
            return kNone;
        }
        ++core.turn_number;
    }
}

// Brings the pixel buffer to the picture of what is being played at a moment. False when
// there is no picture to show.
bool advance(Core &core, uint64_t now) {
    // The playlist is a row of turns, each as long as its animation makes it. A cycle is
    // a row of turns of equal length, each with the next animation of its list. The time
    // of an animation is counted from the start of its turn.
    uint32_t animation;
    uint64_t turn;
    uint64_t in_turn = 0;
    Reason reason = kNone;
    if (core.playing == kPlaylist) {
        reason = playlist_turn(core, now, &in_turn);
        if (core.playing == kNothing) return false;
        animation = core.turn_item;
        turn = core.turn_number;
    } else {
        // A cycle's turns are `seconds` long each, a text's rounded up to whole passes:
        // whole rounds are taken off by division, then the turns of the round walked.
        const ItemInfo &cycle = core.items[core.playing];
        const uint64_t elapsed = now - core.zero;
        uint64_t round = 0;
        for (uint32_t entry = 0; entry < cycle.count; ++entry) {
            round += whole_passes(core, core.entries[cycle.first + entry], 1000ull * cycle.seconds);
        }
        uint64_t within = elapsed % round;
        uint32_t at = 0;
        for (;;) {
            animation = core.entries[cycle.first + (at + core.cycle_start_entry) % cycle.count];
            const uint64_t length = whole_passes(core, animation, 1000ull * cycle.seconds);
            if (within < length) {
                break;
            }
            within -= length;
            ++at;
        }
        turn = elapsed / round * cycle.count + at;
        in_turn = within;
    }
    if (reason == kNone) {
        reason = show_at(core, animation, turn, in_turn);
    }
    if (reason != kNone && is_drive(animation)) {
        // A drive's file that cannot be played leaves the playlist, and the show stays valid.
        const uint32_t place = animation - kDriveBase;
        close_stream(core);
        core.drive[place].state = kDriveLeftOut;
        drive_left_out(core, place, reason);
        player_drive_changed(core);
        return false;
    }
    if (reason != kNone) {
        // The file cannot be played: the show is invalid from this refresh on.
        const FileInfo &file = core.files[core.items[animation].first];
        if (reason == kFileMissing || reason == kReadError || reason == kSizeMismatch) {
            core_fail(core, reason, file.name, kNone);
        } else {
            core_fail(core, kFileMalformed, file.name, reason);
        }
        return false;
    }
    core.shown = animation;
    return true;
}

// Writes the colour of every LED: its pixel, through the palette in a palette file, at the
// current brightness.
void fill_leds(Core &core) {
    const uint8_t *scale = core.scale;
    const uint16_t *pixel = core.led_pixel;
    uint8_t *out = core.led_data;
    if (core.decoder.colours != 0) {
        const uint8_t *palette = core.decoder.palette;
        for (uint32_t led = 0; led < core.led_total; ++led) {
            const uint8_t *colour = palette + 3u * core.pixels[pixel[led]];
            *out++ = scale[colour[0]];
            *out++ = scale[colour[1]];
            *out++ = scale[colour[2]];
        }
    } else {
        for (uint32_t led = 0; led < core.led_total; ++led) {
            const uint8_t *colour = core.pixels + 3u * pixel[led];
            *out++ = scale[colour[0]];
            *out++ = scale[colour[1]];
            *out++ = scale[colour[2]];
        }
    }
}

}  // namespace

uint64_t clock_touch(Core &core, uint64_t now_ms) {
    if (!core.started) {
        core.started = 1;
        core.t0 = now_ms;
        core.latest = now_ms;
        core.next_due = now_ms;
    }
    if (now_ms < core.latest) {
        return core.latest;
    }
    core.latest = now_ms;
    return now_ms;
}

void player_set_brightness(Core &core, uint8_t value) {
    core.brightness = value;
    for (uint32_t colour = 0; colour < 256; ++colour) {
        core.scale[colour] = static_cast<uint8_t>((colour * value + 127) / 255);
    }
}

uint32_t player_first_animation(const Core &core) {
    uint32_t position = 0;
    while (position < core.item_count && (core.items[position].is_cycle || core.items[position].ignored)) {
        ++position;
    }
    return position;
}

uint32_t player_first_in_playlist(const Core &core) {
    const uint32_t first = player_first_animation(core);
    if (first != core.item_count) {
        return first;
    }
    for (uint32_t place = 0; place < core.drive_count; ++place) {
        if (core.drive[place].state == kDriveInPlaylist) {
            return kDriveBase + place;
        }
    }
    return kNothing;
}

void player_drive_joined(Core &core, uint32_t place) {
    if (core.playing == kNothing && !core.invalid && !core.mapping_test) {
        player_play_all(core, kDriveBase + place);
    }
}

void player_drive_changed(Core &core) {
    if (core.stream_open && is_drive(core.stream_item) && !plays(core, core.stream_item)) {
        close_stream(core);
    }
    if (core.playing == kPlaylist && is_drive(core.turn_item) && !plays(core, core.turn_item)) {
        // Its animation is gone: the playlist goes on with the next one that is left.
        const uint32_t next = next_animation(core, core.turn_item);
        if (plays(core, next)) {
            player_play_all(core, next);
        } else {
            core.playing = kNothing;
            core.shown = kNothing;
        }
    }
}

void player_start(Core &core) {
    core.on = 1;
    core.playing = kNothing;
    core.shown = kNothing;
    player_set_brightness(core, core.brightness);
    if (core.invalid) {
        return;
    }
    if (core.has_start && core.items[core.start_item].is_cycle) {
        player_play_cycle(core, core.start_item);
        return;
    }
    uint32_t from = core.has_start ? core.start_item : player_first_animation(core);
    if (from < core.item_count && core.items[from].ignored) from = next_animation(core, from);
    if (from != core.item_count && from != kNothing) {
        player_play_all(core, from);
    }
}

void player_halt(Core &core) {
    close_stream(core);
    core.playing = kNothing;
    core.shown = kNothing;
}

void player_play_cycle(Core &core, uint32_t item) {
    core.cycle_start_entry = 0;
    close_stream(core);
    core.playing = item;
    core.zero_pending = 1;
    core.shown = core.entries[core.items[item].first];
}

void player_play_all(Core &core, uint32_t from) {
    close_stream(core);
    core.playing = kPlaylist;
    core.zero_pending = 1;
    core.turn_item = from;
    core.shown = from;
}

void player_releases_file(Core &core, uint32_t item) {
    if (core.stream_open && core.stream_item == item) {
        close_stream(core);
    }
}

void player_file_replaced(Core &core, uint32_t item) {
    if (core.playing == kNothing) {
        return;
    }
    if (core.playing == kPlaylist) {
        if (core.turn_item == item) {
            player_play_all(core, item);
        }
        return;
    }
    const ItemInfo &cycle = core.items[core.playing];
    bool plays = false;
    for (uint32_t entry = 0; entry < cycle.count; ++entry) {
        plays = plays || core.entries[cycle.first + entry] == item;
    }
    if (plays) {
        player_play_cycle(core, core.playing);
    }
}

void player_item_added(Core &core) {
    if (core.playing == kNothing) {
        const uint32_t first = player_first_in_playlist(core);
        if (first != kNothing) player_play_all(core, first);
    }
}

void player_inclusion_changed(Core &core, uint32_t item) {
    if (core.playing == kPlaylist && core.turn_item == item && core.items[item].ignored) {
        const uint32_t next = next_animation(core, item);
        if (next == kNothing) player_halt(core);
        else player_play_all(core, next);
    } else if (core.playing == kNothing && !core.items[item].ignored) {
        player_play_all(core, item);
    }
}

void player_item_leaves(Core &core, uint32_t item) {
    if (core.playing == kPlaylist && core.turn_item == item) {
        const uint32_t next = next_animation(core, item);
        if (next == item || next == kNothing) {
            // It was the only animation of the show.
            close_stream(core);
            core.playing = kNothing;
            core.shown = kNothing;
            return;
        }
        player_play_all(core, next);
    } else if (core.playing == item) {
        // A cycle lists an animation, so the show has one.
        const uint32_t first = player_first_in_playlist(core);
        if (first == kNothing) player_halt(core);
        else player_play_all(core, first);
    }
    // The positions of the show's items after it are one lower now; those of a drive's
    // animations stay.
    if (core.playing == kPlaylist) {
        if (core.turn_item > item && !is_drive(core.turn_item)) {
            --core.turn_item;
        }
    } else if (core.playing != kNothing && core.playing > item) {
        --core.playing;
    }
    if (core.shown != kNothing && core.shown > item && !is_drive(core.shown)) {
        --core.shown;
    }
    if (core.stream_open && core.stream_item > item && !is_drive(core.stream_item)) {
        --core.stream_item;
    }
}

int player_poll(Core &core, uint64_t now_ms) {
    const uint64_t now = clock_touch(core, now_ms);
    upload_touch(core, now);
    if (core.leg_count == 0 || now < core.next_due) {
        return 0;
    }
    // A drive plugged in or pulled out is taken up or dropped before the picture is made.
    drive_touch(core);
    // The latest grid time at or before now is used; every earlier one is skipped.
    const uint64_t grid = core.t0 + (now - core.t0) / kGridStep * kGridStep;
    core.next_due = grid + kGridStep;
    // Whether this refresh follows the one before it without a grid time skipped.
    const bool in_step = core.had_refresh && grid == core.last_grid + kGridStep;
    core.had_refresh = 1;
    core.last_grid = grid;

    const uint64_t second = (now - core.t0) / 1000;
    if (second != core.second_running) {
        core.second_before = core.second_running;
        core.count_before = core.count_running;
        core.second_running = second;
        core.count_running = 0;
    }
    ++core.count_running;

    bool lit = core.mapping_test && !core.invalid;
    if (!core.mapping_test && !core.invalid && core.playing != kNothing) {
        if (core.zero_pending) {
            core.zero = grid;
            core.zero_pending = 0;
        }
        lit = advance(core, now);
    }
    if (lit && core.on) {
        fill_leds(core);
    } else {
        memset(core.led_data, 0, 3u * core.led_total);
    }
    // The LED data is complete. The check of an uploaded file takes one step now, and
    // none when the host was late for this refresh. The check after the start takes its
    // steps; when it finds a fault, the show is invalid from this refresh on.
    if (in_step) {
        upload_step(core, now);
    }
    const bool was_valid = !core.invalid;
    const bool steady = second == 0 || player_fps(core, now) >= kCheckLeastRate;
    check_after_start(core, in_step, now - grid <= kCheckOnTimeMs && steady);
    if (was_valid && core.invalid) {
        memset(core.led_data, 0, 3u * core.led_total);
    }
    return 1;
}

uint32_t player_fps(const Core &core, uint64_t now) {
    const uint64_t second = (now - core.t0) / 1000;
    if (second == 0) {
        return 0;
    }
    if (core.second_running == second - 1) {
        return core.count_running;
    }
    if (core.second_before == second - 1) {
        return core.count_before;
    }
    return 0;
}

}  // namespace odrig

int odrig_core_poll(odrig_core *core, uint64_t now_ms) {
    if (core == nullptr) {
        return 0;
    }
    return odrig::player_poll(core->state, now_ms);
}
