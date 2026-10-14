#include "player.h"

#include <string.h>

#include "odrig_core.h"
#include "upload.h"

namespace odrig {

namespace {

void close_stream(Core &core) {
    core.file.close();
    core.stream_open = 0;
}

// Opens the file of an animation item for one turn and one loop, with the pixel buffer all
// zero and no frame decoded.
Reason open_stream(Core &core, uint32_t animation, uint64_t turn, uint64_t loop) {
    close_stream(core);
    const FileInfo &file = core.files[core.items[animation].first];
    Reason reason = core.file.open(core.host, file.name);
    if (reason != kNone) {
        return reason;
    }
    reason = core.decoder.open(&core.file, &core.inflate, core.window);
    if (reason != kNone) {
        return reason;
    }
    if (core.decoder.width != core.width || core.decoder.height != core.height) {
        return kSizeMismatch;
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
        core.files[core.items[animation].first].total_ms = core.frame_end;
    }
    return reason;
}

// Brings the pixel buffer to the picture an animation shows at a time since the start of
// its turn. While the length of the animation is not known, the time lies in its first
// loop. Once it is known, the loop and the place in it are found by division.
Reason show_at(Core &core, uint32_t animation, uint64_t turn, uint64_t in_turn) {
    const FileInfo &file = core.files[core.items[animation].first];
    if (file.total_ms == 0) {
        const Reason reason = first_loop_to(core, animation, turn, in_turn);
        if (reason != kNone || file.total_ms == 0) {
            return reason;
        }
    }
    const uint64_t loop = in_turn / file.total_ms;
    const uint64_t within = in_turn % file.total_ms;
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

// How long the turn of the animation item at this position lasts in the playlist, in
// milliseconds. The length of the animation is known.
uint64_t turn_ms(const Core &core, uint32_t position) {
    const ItemInfo &item = core.items[position];
    const uint64_t loop = core.files[item.first].total_ms;
    uint64_t loops = item.count;
    if (loops == 0) {
        loops = (1000ull * core.min_seconds + loop - 1) / loop;
    }
    const uint64_t turn = loops * loop;
    const uint64_t longest = 1000ull * item.seconds;
    return item.seconds != 0 && turn > longest ? longest : turn;
}

// The position of the animation item after this one, the first one after the last.
uint32_t next_animation(const Core &core, uint32_t position) {
    do {
        position = position + 1 < core.item_count ? position + 1 : 0;
    } while (core.items[position].is_cycle);
    return position;
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
        const ItemInfo &item = core.items[core.turn_item];
        const FileInfo &file = core.files[item.first];
        uint64_t turn;
        if (file.total_ms != 0) {
            turn = turn_ms(core, core.turn_item);
            if (elapsed < turn) {
                *in_turn = elapsed;
                return kNone;
            }
        } else {
            const uint64_t longest = 1000ull * item.seconds;
            const bool beyond = item.seconds != 0 && elapsed >= longest;
            const Reason reason = first_loop_to(core, core.turn_item, core.turn_number, beyond ? longest : elapsed);
            if (reason != kNone) {
                return reason;
            }
            if (file.total_ms != 0) {
                continue;
            }
            if (!beyond) {
                *in_turn = elapsed;
                return kNone;
            }
            turn = longest;
        }
        if (!rounds_taken) {
            // Whole rounds of the playlist are taken off at once when the length of every
            // animation is known, so that a long time without a refresh costs one walk
            // over the items.
            rounds_taken = true;
            uint64_t round = 0;
            bool all_known = true;
            for (uint32_t position = 0; position < core.item_count && all_known; ++position) {
                if (!core.items[position].is_cycle) {
                    all_known = core.files[core.items[position].first].total_ms != 0;
                    round += all_known ? turn_ms(core, position) : 0;
                }
            }
            if (all_known && elapsed >= round) {
                core.zero += elapsed / round * round;
                elapsed %= round;
                ++core.turn_number;
                continue;
            }
        }
        core.zero += turn;
        elapsed -= turn;
        core.turn_item = next_animation(core, core.turn_item);
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
        animation = core.turn_item;
        turn = core.turn_number;
    } else {
        const ItemInfo &cycle = core.items[core.playing];
        const uint64_t turn_length = 1000ull * cycle.seconds;
        turn = (now - core.zero) / turn_length;
        in_turn = (now - core.zero) % turn_length;
        animation = core.entries[cycle.first + turn % cycle.count];
    }
    if (reason == kNone) {
        reason = show_at(core, animation, turn, in_turn);
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
    while (position < core.item_count && core.items[position].is_cycle) {
        ++position;
    }
    return position;
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
    const uint32_t from = core.has_start ? core.start_item : player_first_animation(core);
    if (from != core.item_count) {
        player_play_all(core, from);
    }
}

void player_halt(Core &core) {
    close_stream(core);
    core.playing = kNothing;
    core.shown = kNothing;
}

void player_play_cycle(Core &core, uint32_t item) {
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
        player_play_all(core, player_first_animation(core));
    }
}

void player_item_leaves(Core &core, uint32_t item) {
    if (core.playing == kPlaylist && core.turn_item == item) {
        const uint32_t next = next_animation(core, item);
        if (next == item) {
            // It was the only animation of the show.
            close_stream(core);
            core.playing = kNothing;
            core.shown = kNothing;
            return;
        }
        player_play_all(core, next);
    } else if (core.playing == item) {
        // A cycle lists an animation, so the show has one.
        player_play_all(core, player_first_animation(core));
    }
    if (core.playing == kPlaylist) {
        if (core.turn_item > item) {
            --core.turn_item;
        }
    } else if (core.playing != kNothing && core.playing > item) {
        --core.playing;
    }
    if (core.shown != kNothing && core.shown > item) {
        --core.shown;
    }
    if (core.stream_open && core.stream_item > item) {
        --core.stream_item;
    }
}

int player_poll(Core &core, uint64_t now_ms) {
    const uint64_t now = clock_touch(core, now_ms);
    upload_touch(core, now);
    if (core.leg_count == 0 || now < core.next_due) {
        return 0;
    }
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

    bool lit = false;
    if (!core.invalid && core.playing != kNothing) {
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
    check_after_start(core, in_step);
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
