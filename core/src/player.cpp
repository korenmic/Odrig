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
    return kNone;
}

// Brings the pixel buffer to the picture of the item being played, `elapsed` milliseconds
// after its time zero. False when there is no picture to show.
bool advance(Core &core, uint64_t elapsed) {
    // An animation item is one turn without end. A cycle is a row of turns of equal
    // length, each with the next animation of its list, counted from the turn's start.
    const ItemInfo &item = core.items[core.playing];
    uint32_t animation = core.playing;
    uint64_t turn = 0;
    uint64_t in_turn = elapsed;
    if (item.is_cycle) {
        const uint64_t turn_ms = 1000ull * item.seconds;
        turn = elapsed / turn_ms;
        in_turn = elapsed % turn_ms;
        animation = core.entries[item.first + turn % item.count];
    }
    const FileInfo &file = core.files[core.items[animation].first];
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
    if (reason != kNone) {
        // The file cannot be played: the show is invalid from this refresh on.
        close_stream(core);
        core.playing = kNothing;
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

void player_start(Core &core) {
    core.on = 1;
    core.playing = kNothing;
    core.shown = kNothing;
    player_set_brightness(core, core.brightness);
    if (!core.invalid && core.has_start) {
        player_play(core, core.start_item);
    }
}

void player_play(Core &core, uint32_t item) {
    close_stream(core);
    core.playing = item;
    core.zero_pending = 1;
    const ItemInfo &played = core.items[item];
    core.shown = played.is_cycle ? core.entries[played.first] : item;
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
    const ItemInfo &played = core.items[core.playing];
    bool plays = core.playing == item;
    for (uint32_t entry = 0; played.is_cycle && entry < played.count; ++entry) {
        plays = plays || core.entries[played.first + entry] == item;
    }
    if (plays) {
        player_play(core, core.playing);
    }
}

void player_item_leaves(Core &core, uint32_t item) {
    if (core.playing == item) {
        close_stream(core);
        core.playing = kNothing;
        core.shown = kNothing;
        return;
    }
    if (core.playing != kNothing && core.playing > item) {
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
        lit = advance(core, now - core.zero);
    }
    if (lit && core.on) {
        fill_leds(core);
    } else {
        memset(core.led_data, 0, 3u * core.led_total);
    }
    // The LED data is complete. The check of an uploaded file takes one step now, and
    // none when the host was late for this refresh.
    if (in_step) {
        upload_step(core, now);
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
