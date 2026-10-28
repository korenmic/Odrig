#include "player.h"

#include <string.h>

#include "catalog.h"
#include "odrig_core.h"
#include "clock.h"
#include "mapping_control.h"
#include "order.h"
#include "playlist.h"
#include "repeats.h"
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
    return is_drive(animation) ? 0 : core.items[animation].count & 0xFFFFu;
}

uint32_t seconds_of(const Core &core, uint32_t animation) {
    return is_drive(animation) ? 0 : core.items[animation].seconds;
}

// The id `list` and `status` give the animation at a position of the playlist.
uint32_t id_of(const Core &core, uint32_t animation) {
    return is_drive(animation) ? core.drive[animation - kDriveBase].id : core.items[animation].id;
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
// the show that is neither ignored nor unavailable, or a file of the drive that is in the
// playlist.
bool plays(const Core &core, uint32_t position) {
    if (is_drive(position)) {
        const uint32_t place = position - kDriveBase;
        return place < core.drive_count && core.drive[place].state == kDriveInPlaylist;
    }
    return position < core.item_count && !core.items[position].is_cycle && !core.items[position].ignored &&
           item_usable(core, position);
}

// The animation a cycle shows in one of its turns: the entry of the turn, or the first
// usable entry after it in the cycle's order; kNothing when the cycle lists none.
uint32_t cycle_animation(const Core &core, const ItemInfo &cycle, uint64_t turn) {
    for (uint32_t step = 0; step < cycle.count; ++step) {
        const uint32_t animation = core.entries[cycle.first + (turn + core.cycle_start_entry + step) % cycle.count];
        if (item_usable(core, animation)) {
            return animation;
        }
    }
    return kNothing;
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
        reason = drawn_read(&core.file, header, core.window);
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

// Decodes the next frame record of the file open for playback into the pixel buffer, as
// long as the refresh has bytes left to decode: kPendingWork when it has none, and the
// record is decoded at the next refresh. The first record of a refresh is always decoded.
Reason next_record(Core &core, uint16_t *duration) {
    if (core.catch_up_begun && core.catch_up_left == 0) {
        return kPendingWork;
    }
    const uint64_t before = core.decoder.body_read;
    const Reason reason = core.decoder.next(core.pixels, duration);
    const uint64_t used = core.decoder.body_read - before;
    core.catch_up_left = used >= core.catch_up_left ? 0 : core.catch_up_left - static_cast<uint32_t>(used);
    core.catch_up_begun = 1;
    return reason;
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
        reason = next_record(core, &duration);
        if (reason != kNone) {
            break;
        }
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
// its turn, which began at `start`. While the length of the animation is not known, the
// time lies in its first loop. Once it is known, the loop and the place in it are found by
// division. A text is drawn at its time in its pass; a clock at its time in the turn, with
// the seed the turn got when it began.
Reason show_at(Core &core, uint32_t animation, uint64_t turn, uint64_t in_turn, uint64_t start) {
    const uint8_t type = type_of(core, animation);
    if (is_drawn(type)) {
        const uint64_t loop = length_of(core, animation);
        if (loop == 0) {
            return kLoopMismatch;
        }
        if (!core.stream_open || !core.stream_drawn || core.stream_item != animation || core.stream_turn != turn) {
            const Reason reason = open_stream(core, animation, turn, 0);
            if (reason != kNone) {
                return reason;
            }
            // A clock's turn gets its seed when it begins: its file is opened once in a turn.
            if (type == kTypeWidget) {
                core.seed = clock_seed(core.noise, id_of(core, animation), start);
            }
        }
        core.decoder.colours = 0;
        if (type == kTypeText) {
            text_draw(core.window, core.width, core.height, in_turn % loop, core.pixels);
            return kNone;
        }
        clock_draw(core.window, core.seed, core.width, core.height, in_turn, core.pixels);
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
        reason = next_record(core, &duration);
        if (reason != kNone) {
            break;
        }
        core.frame_end += duration;
        ++core.stream_records;
    }
    return reason;
}

// How long the turn of the animation at this position lasts in the playlist, in
// milliseconds: the loops of its saved repeat, not cut by its longest time, or else the
// loops the show gives it. The length of the animation is known.
uint64_t turn_ms(const Core &core, uint32_t position) {
    const uint64_t loop = length_of(core, position);
    const uint64_t saved = repeats_of(core, position);
    if (saved != 0) {
        return saved * loop;
    }
    uint64_t loops = loops_of(core, position);
    if (loops == 0) {
        loops = (1000ull * core.min_seconds + loop - 1) / loop;
    }
    const uint64_t turn = loops * loop;
    const uint64_t longest = 1000ull * seconds_of(core, position);
    return longest != 0 && turn > longest ? whole_passes(core, position, longest) : turn;
}

// How long the turn in progress of the playlist lasts: the loops a `repeat` gave it, from
// its first frame and not cut by the longest time, or else as its animation's turn lasts.
// The length of its animation is known.
uint64_t current_turn_ms(const Core &core) {
    if (core.turn_repeat != 0) {
        return core.turn_repeat * length_of(core, core.turn_item);
    }
    return turn_ms(core, core.turn_item);
}

// The animation that plays with the smallest key, among the show's items alone or among
// them and the drive's, whose key is above `above` unless `any` is set; kNothing when none.
uint32_t lowest_playing(const Core &core, bool with_drive, uint32_t above, bool any) {
    uint32_t best = kNothing;
    uint32_t best_key = 0;
    const uint32_t places = with_drive ? core.drive_count : 0;
    for (uint32_t at = 0; at < core.item_count + places; ++at) {
        const uint32_t position = at < core.item_count ? at : kDriveBase + (at - core.item_count);
        if (!plays(core, position)) {
            continue;
        }
        const uint32_t key = order_key(core, position);
        if ((any || key > above) && (best == kNothing || key < best_key)) {
            best = position;
            best_key = key;
        }
    }
    return best;
}

// The folder of a position in the drive's tree: 0 for an item of the show and for a place
// of no folder.
uint32_t folder_of(const Core &core, uint32_t position) {
    if (!is_drive(position) || core.drive_folder == nullptr || !core.tree_known) {
        return 0;
    }
    const uint8_t byte = core.drive_folder[position - kDriveBase];
    return byte == kNoFolder ? 0 : byte;
}

// The exhausting key of a position: its folder's index in the table, then its key in the
// saved order. A playlist walked by it plays its own animations in the saved order, then
// each of its sub-folders' once, depth first, since the table is in that order.
uint64_t exhausting_key(const Core &core, uint32_t position) {
    return static_cast<uint64_t>(folder_of(core, position)) << 32 | order_key(core, position);
}

// A range of the tree's table: the folders from `first` to `end`.
struct Range {
    uint32_t first;
    uint32_t end;
};

// The root's range: the whole table, and everything while the tree is not known.
Range root_range(const Core &core) {
    const Range range = {0, core.tree_known ? core.folder_count + 1u : 1u};
    return range;
}

// The current playlist's range: its folder's subtree, the root's while the tree is not
// known.
Range current_range(const Core &core) {
    if (!core.tree_known || core.current == 0 || core.folders == nullptr) {
        return root_range(core);
    }
    const Range range = {core.current, core.folders[core.current].end};
    return range;
}

// The range the playlist walks: the current playlist's, or the root's in its place.
Range range_in_use(const Core &core) {
    return core.in_place ? root_range(core) : current_range(core);
}

bool in_range(const Core &core, Range range, uint32_t position) {
    const uint32_t folder = folder_of(core, position);
    return folder >= range.first && folder < range.end;
}

// The animation that plays with the smallest exhausting key within a range, above `above`
// unless `any` is set; kNothing when none. Not inlined: the refresh's frame stays small.
__attribute__((noinline)) uint32_t lowest_in(const Core &core, Range range, uint64_t above, bool any) {
    uint32_t best = kNothing;
    uint64_t best_key = 0;
    for (uint32_t at = 0; at < core.item_count + core.drive_count; ++at) {
        const uint32_t position = at < core.item_count ? at : kDriveBase + (at - core.item_count);
        if (!plays(core, position) || !in_range(core, range, position)) {
            continue;
        }
        const uint64_t key = exhausting_key(core, position);
        if ((any || key > above) && (best == kNothing || key < best_key)) {
            best = position;
            best_key = key;
        }
    }
    return best;
}

uint32_t first_in(const Core &core, Range range) {
    return lowest_in(core, range, 0, true);
}

// The animation after a position within a range: the lowest key above its key, else the
// lowest in the range.
uint32_t next_in(const Core &core, Range range, uint32_t position) {
    const uint32_t after = lowest_in(core, range, exhausting_key(core, position), false);
    return after != kNothing ? after : first_in(core, range);
}

// When the current playlist's window ends: the moment it became current and the window,
// less what was spent in it before that moment.
uint64_t window_end(const Core &core) {
    const uint64_t spent = core.window_spent < kWindowMs ? core.window_spent : kWindowMs;
    return core.window_started + (kWindowMs - spent);
}

// Whether the root plays in the current playlist's place: it does while the current
// playlist has nothing to play.
void judge_in_place(Core &core) {
    core.in_place = core.tree_known && core.current != 0 && first_in(core, current_range(core)) == kNothing ? 1 : 0;
}

// The window has passed at a moment: the next playlist of the tree is current from then,
// with a window of its own, the root after the last and while the tree is not known.
void rotate(Core &core, uint64_t at) {
    const uint32_t next = core.tree_known && core.current < core.folder_count ? core.current + 1u : 0;
    tree_choose(core, next);
    player_playlist_chosen(core, at);
    playlist_changed(core);
}

// The position of the animation after this one in the playlist: the next in the
// exhausting order of the range in use, the first after the last; this one again when no
// other plays. The current playlist takes over from its first animation as soon as it has
// something to play again.
__attribute__((noinline)) uint32_t next_animation(Core &core, uint32_t position) {
    const bool was_in_place = core.in_place != 0;
    judge_in_place(core);
    if (was_in_place && !core.in_place) {
        return first_in(core, current_range(core));
    }
    return next_in(core, range_in_use(core), position);
}

// Moves the playlist on to the turn that a moment falls into, and gives the time since
// that turn began. A turn begins where the one before it ended, however late the moment is.
//
// Whether a turn has ended follows from the length of its animation. While that is not
// known, the first loop is decoded up to the moment, or up to the longest time the turn
// may last when the moment lies beyond it. When the loop ends on the way, the length is
// known. When it does not, the animation is in its first loop and its turn goes on; or
// the loop is longer than the longest time, and the turn ended there.
__attribute__((noinline)) Reason playlist_turn(Core &core, uint64_t now, uint64_t *in_turn) {
    uint64_t elapsed = now - core.zero;
    bool rounds_taken = false;
    for (;;) {
        const uint32_t seconds = seconds_of(core, core.turn_item);
        uint64_t turn;
        if (length_of(core, core.turn_item) != 0) {
            turn = current_turn_ms(core);
            if (elapsed < turn) {
                *in_turn = elapsed;
                return kNone;
            }
        } else {
            // A turn whose loops a `repeat` gave, or a saved repeat, is not cut by the longest
            // time.
            const uint64_t longest = 1000ull * seconds;
            const bool beyond = seconds != 0 && core.turn_repeat == 0 && repeats_of(core, core.turn_item) == 0 && elapsed >= longest;
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
        if (!rounds_taken && core.turn_repeat == 0 && plays(core, core.turn_item) && core.resume_item == kNothing) {
            // Whole rounds of the playlist in use are taken off at once when the length of
            // every animation of it is known, so that a long time without a refresh costs
            // one walk over the items. A turn whose loops a `repeat` gave ends first.
            rounds_taken = true;
            uint64_t round = 0;
            bool all_known = true;
            const Range range = range_in_use(core);
            for (uint32_t at = 0; at < core.item_count + core.drive_count && all_known; ++at) {
                const uint32_t position = at < core.item_count ? at : kDriveBase + (at - core.item_count);
                if (!plays(core, position) || !in_range(core, range, position)) {
                    continue;
                }
                if (!is_drive(position)) {
                    all_known = core.files[core.items[position].first].total_ms != 0;
                }
                round += all_known ? turn_ms(core, position) : 0;
            }
            if (all_known && round != 0 && elapsed >= round) {
                // Only rounds that end before the window does, so that the turn at which
                // the window passes is met, with the root alone too.
                uint64_t rounds = elapsed / round;
                const uint64_t end = window_end(core);
                const uint64_t before_end = end > core.zero ? (end - core.zero - 1) / round : 0;
                rounds = rounds < before_end ? rounds : before_end;
                if (rounds != 0) {
                    core.zero += rounds * round;
                    elapsed -= rounds * round;
                    ++core.turn_number;
                    continue;
                }
            }
        }
        core.zero += turn;
        elapsed -= turn;
        core.turn_repeat = 0;
        if (core.zero >= window_end(core)) {
            // The window passed during the turn: the next playlist is current from the
            // turn's end, and plays from its first animation; its round is summed anew.
            // The root alone, current again, goes on as it was.
            const uint32_t before = core.current;
            rotate(core, core.zero);
            rounds_taken = false;
            core.turn_item = core.current != before ? player_first_in_playlist(core) : next_animation(core, core.turn_item);
        } else if (core.resume_item != kNothing && plays(core, core.resume_item)) {
            // The turn a jump cut plays again, from its first frame.
            core.turn_item = core.resume_item;
            core.resume_item = kNothing;
        } else {
            core.resume_item = kNothing;
            core.turn_item = next_animation(core, core.turn_item);
        }
        if (core.turn_item == kNothing) {
            close_stream(core);
            core.playing = core.shown = kNothing;
            *in_turn = 0;
            return kNone;
        }
        ++core.turn_number;
    }
}

// What a refresh shows: no picture, the picture in the pixel buffer, or the picture of the
// refresh before, while the player has not come to the picture of the moment yet.
enum Shown { kShowsNothing, kShowsPicture, kShowsBefore };

// Brings the pixel buffer to the picture of what is being played at a moment, decoding at
// most kCatchUpBytes of a body.
Shown advance(Core &core, uint64_t now) {
    // The playlist is a row of turns, each as long as its animation makes it. A cycle is
    // a row of turns of equal length, each with the next animation of its list. The time
    // of an animation is counted from the start of its turn.
    uint32_t animation;
    uint64_t turn;
    uint64_t in_turn = 0;
    Reason reason = kNone;
    core.catch_up_left = kCatchUpBytes;
    core.catch_up_begun = 0;
    if (core.playing == kPlaylist) {
        reason = playlist_turn(core, now, &in_turn);
        if (core.playing == kNothing) return kShowsNothing;
        animation = core.turn_item;
        turn = core.turn_number;
    } else {
        // A cycle's turns are `seconds` long each, a text's rounded up to whole passes:
        // whole rounds are taken off by division, then the turns of the round walked.
        const ItemInfo &cycle = core.items[core.playing];
        const uint64_t elapsed = now - core.zero;
        if (cycle_animation(core, cycle, 0) == kNothing) {
            // Every animation of the cycle is unavailable: the playlist plays.
            const uint32_t first = player_first_in_playlist(core);
            if (first == kNothing) {
                player_halt(core);
                return kShowsNothing;
            }
            player_play_all(core, first);
            return kShowsBefore;
        }
        uint64_t round = 0;
        for (uint32_t at = 0; at < cycle.count; ++at) {
            round += whole_passes(core, cycle_animation(core, cycle, at), 1000ull * cycle.seconds);
        }
        uint64_t within = elapsed % round;
        uint32_t at = 0;
        for (;;) {
            animation = cycle_animation(core, cycle, at);
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
        reason = show_at(core, animation, turn, in_turn, now - in_turn);
    }
    if (reason == kPendingWork) {
        // The rest is decoded at the next refresh, or the file settles a defect and its
        // reason comes at a later one.
        return kShowsBefore;
    }
    if (reason != kNone && is_drive(animation)) {
        // Where the file was: a file that did not open was at its start.
        const bool opened = core.stream_open && core.stream_item == animation;
        char name[kFaultNameSize];
        drive_given_name(core, animation - kDriveBase, name, sizeof name);
        note_fault(core, kWorkPlay, name, opened ? core.stream_records : 0, opened ? core.decoder.body_read : 0, reason);
    }
    if (reason != kNone && is_drive(animation)) {
        // A drive's file that cannot be played leaves the playlist, and the show stays valid.
        const uint32_t place = animation - kDriveBase;
        close_stream(core);
        core.drive[place].state = kDriveLeftOut;
        drive_left_out(core, place, reason);
        catalog_drive_left_out(core, place, reason);
        player_drive_changed(core);
        return kShowsBefore;
    }
    if (reason != kNone) {
        // The file cannot be played: it is quarantined, this refresh keeps the picture
        // before, and the next one goes on without it.
        const bool opened = core.stream_open && core.stream_item == animation;
        const uint32_t record = opened ? core.stream_records : 0;
        const uint64_t body_bytes = opened ? core.decoder.body_read : 0;
        close_stream(core);
        quarantine_file(core, core.items[animation].first, reason, kWorkPlay, record, body_bytes);
        return kShowsBefore;
    }
    core.shown = animation;
    return kShowsPicture;
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
        // The window of the playlist current at power-on runs from the first timestamp,
        // and so does the time to the first periodic write of the saved file.
        core.window_started = now_ms;
        core.playlist_saved = now_ms;
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
    const uint32_t first = lowest_playing(core, false, 0, true);
    return first != kNothing ? first : core.item_count;
}

uint32_t player_first_in_playlist(const Core &core) {
    const uint32_t first = first_in(core, current_range(core));
    return first != kNothing ? first : first_in(core, root_range(core));
}

void player_playlist_chosen(Core &core, uint64_t at) {
    core.window_started = at;
    core.window_spent = 0;
    core.resume_item = kNothing;
    judge_in_place(core);
}

bool player_window_passed(Core &core, uint64_t now) {
    if (now < window_end(core)) {
        return false;
    }
    const uint32_t before = core.current;
    rotate(core, now);
    return core.current != before;
}

uint32_t player_window_left(const Core &core) {
    const uint64_t since = core.latest > core.window_started ? core.latest - core.window_started : 0;
    const uint64_t spent = core.window_spent + since;
    return spent < kWindowMs ? static_cast<uint32_t>((kWindowMs - spent) / 1000) : 0;
}

void player_jump(Core &core, uint32_t item) {
    const uint32_t cut = core.playing == kPlaylist ? core.turn_item : kNothing;
    core.resume_item = cut != kNothing && cut != item && plays(core, cut) && !in_range(core, range_in_use(core), item) ? cut : kNothing;
    player_play_all(core, item);
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
    if (core.resume_item != kNothing && is_drive(core.resume_item) && !plays(core, core.resume_item)) {
        core.resume_item = kNothing;
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
    core.resume_item = kNothing;
    core.in_place = 0;
    player_set_brightness(core, core.brightness);
    if (core.invalid) {
        return;
    }
    if (core.has_start && core.items[core.start_item].is_cycle && item_usable(core, core.start_item)) {
        player_play_cycle(core, core.start_item);
        return;
    }
    if (core.tree_known && core.current != 0) {
        // A folder is current: it plays from its first animation, or the root does in its
        // place.
        const uint32_t first = player_first_in_playlist(core);
        if (first != kNothing) {
            player_play_all(core, first);
        }
        return;
    }
    uint32_t from = core.has_start && !core.items[core.start_item].is_cycle ? core.start_item : player_first_animation(core);
    if (from < core.item_count && !plays(core, from)) from = next_animation(core, from);
    if (from != core.item_count && from != kNothing) {
        player_play_all(core, from);
    }
}

void player_file_failed(Core &core, uint32_t file) {
    if (core.stream_open && !is_drive(core.stream_item) && core.items[core.stream_item].first == file) {
        close_stream(core);
    }
    if (core.playing == kPlaylist && !is_drive(core.turn_item) && !plays(core, core.turn_item)) {
        const uint32_t next = next_animation(core, core.turn_item);
        if (next == kNothing) {
            player_halt(core);
        } else {
            player_play_all(core, next);
        }
    } else if (core.playing != kNothing && core.playing != kPlaylist && !item_usable(core, core.playing)) {
        const uint32_t first = player_first_in_playlist(core);
        if (first == kNothing) {
            player_halt(core);
        } else {
            player_play_all(core, first);
        }
    }
}

void player_halt(Core &core) {
    close_stream(core);
    core.playing = kNothing;
    core.shown = kNothing;
    core.turn_repeat = 0;
}

void player_play_cycle(Core &core, uint32_t item) {
    core.cycle_start_entry = 0;
    core.turn_repeat = 0;
    close_stream(core);
    core.playing = item;
    core.zero_pending = 1;
    core.shown = cycle_animation(core, core.items[item], 0);
}

void player_play_all(Core &core, uint32_t from) {
    close_stream(core);
    core.turn_repeat = 0;
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
        // Nothing played, as no animation was usable: the playlist starts.
        player_item_added(core);
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
    if (core.resume_item != kNothing && !is_drive(core.resume_item)) {
        if (core.resume_item == item) {
            core.resume_item = kNothing;
        } else if (core.resume_item > item) {
            --core.resume_item;
        }
    }
    if (core.shown != kNothing && core.shown > item && !is_drive(core.shown)) {
        --core.shown;
    }
    if (core.stream_open && core.stream_item > item && !is_drive(core.stream_item)) {
        --core.stream_item;
    }
}

int player_poll(Core &core, uint64_t now_ms) {
    core.noise = clock_stir(core.noise, now_ms);
    const uint64_t now = clock_touch(core, now_ms);
    upload_touch(core, now);
    if (core.leg_count == 0 || now < core.next_due) {
        return 0;
    }
    // A drive plugged in or pulled out is taken up or dropped before the picture is made.
    drive_touch(core);
    // The window's end while a cycle or nothing plays: the next playlist is current, and
    // what plays goes on; under a test it waits for the test's end.
    if (!core.mapping_test && !core.invalid && core.playing != kPlaylist && player_window_passed(core, now) && core.playing == kNothing) {
        const uint32_t first = player_first_in_playlist(core);
        if (first != kNothing) {
            player_play_all(core, first);
        }
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

    Shown shows = core.mapping_test && !core.invalid ? kShowsPicture : kShowsNothing;
    if (shows == kShowsPicture && core.mapping_snake != 0) {
        snake_test_draw(core, now);
    }
    if (!core.mapping_test && !core.invalid && core.playing != kNothing) {
        if (core.zero_pending) {
            core.zero = grid;
            core.zero_pending = 0;
        }
        shows = advance(core, now);
    }
    if (shows == kShowsPicture && core.on) {
        fill_leds(core);
    } else if (shows != kShowsBefore || !core.on) {
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
    catalog_drive_look(core);
    playlist_touch(core, now);
    if (was_valid && core.invalid) {
        memset(core.led_data, 0, 3u * core.led_total);
    }
    return 1;
}

bool player_reported(const Core &core) {
    return !core.invalid && !core.mapping_test && core.playing == kPlaylist && core.turn_item != kNothing && core.shown == core.turn_item &&
           !core.zero_pending;
}

bool player_counts(const Core &core, uint64_t now, TurnCounts *counts) {
    if (!player_reported(core)) {
        return false;
    }
    // The turn's own value, else its saved repeat, else its loops by the show's numbers,
    // which need the length of its loop.
    const uint64_t loop = length_of(core, core.turn_item);
    uint64_t repeat = core.turn_repeat != 0 ? core.turn_repeat : repeats_of(core, core.turn_item);
    if (repeat == 0 && loop != 0) {
        repeat = (turn_ms(core, core.turn_item) + loop - 1) / loop;
    }
    uint64_t at = loop == 0 || now <= core.zero ? 1 : (now - core.zero) / loop + 1;
    if (repeat != 0 && at > repeat) {
        at = repeat;
    }
    counts->id = id_of(core, core.turn_item);
    counts->saved = repeats_of(core, core.turn_item);
    counts->repeat = repeat;
    counts->loop = at;
    return true;
}

bool player_set_repeat(Core &core, uint32_t id, uint32_t loops, uint64_t now) {
    TurnCounts counts;
    if (!player_counts(core, now, &counts) || counts.id != id) {
        return false;
    }
    core.turn_repeat = counts.loop > loops ? static_cast<uint32_t>(counts.loop) : loops;
    return true;
}

void player_hold_turn(Core &core, uint32_t loops) {
    core.turn_repeat = loops;
}

void player_default_again(Core &core, uint64_t now, uint64_t loop) {
    core.turn_repeat = 0;
    if (length_of(core, core.turn_item) != 0 && now - core.zero >= turn_ms(core, core.turn_item)) {
        // Its own count has passed: the turn ends with the loop in progress.
        core.turn_repeat = static_cast<uint32_t>(loop);
    }
}

bool player_seed(const Core &core, uint32_t *seed) {
    if (core.invalid || core.playing == kNothing || core.shown == kNothing || !core.stream_open || !core.stream_drawn ||
        core.stream_item != core.shown || type_of(core, core.shown) != kTypeWidget) {
        return false;
    }
    *seed = core.seed;
    return true;
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
