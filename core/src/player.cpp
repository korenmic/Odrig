#include "player.h"
#include "mini.h"

#include <string.h>

#include "breaks.h"
#include "catalog.h"
#include "drive.h"
#include "ignored.h"
#include "odrig_core.h"
#include "clock.h"
#include "mapping_control.h"
#include "order.h"
#include "playlist.h"
#include "repeats.h"
#include "brightness.h"
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
        const DriveRow *row = drive_row(core, animation - kDriveBase);
        return row != nullptr ? row->total_ms : 0;
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
    if (is_drive(animation)) {
        const DriveRow *row = drive_row(core, animation - kDriveBase);
        return row != nullptr ? row->id : 0;
    }
    return core.items[animation].id;
}

// What the animation at a position of the playlist holds, as its header says.
uint8_t type_of(const Core &core, uint32_t animation) {
    if (is_drive(animation)) {
        const DriveRow *row = drive_row(core, animation - kDriveBase);
        return row != nullptr ? row->type : kTypeFrames;
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
        return drive_automatic(core, position - kDriveBase);
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
    char drive_name[kDriveOpenRoom];
    const char *name = drive_name;
    if (is_drive(animation)) {
        if (!drive_open_name(core, animation - kDriveBase, drive_name)) {
            return kFileMissing;
        }
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
        // The payload is held whole in the window, which no frames file uses meanwhile; a
        // picture clock's picture is decoded into the pixel buffer once, its palette kept
        // by the decoder, and the window holds its head and parts and then its layer.
        const Picture picture = {&core.decoder, &core.inflate, core.window, core.pixels};
        reason = drawn_read(&core.file, header, core.window, picture);
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
// the seed the turn got when it began; a picture clock's layer is written, and the picture
// in the pixel buffer is left as it is.
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
                core.seed = core.resume_seed != 0 ? core.resume_seed : clock_seed(core.noise, id_of(core, animation), start);
                core.resume_seed = 0;
            }
        }
        if (type == kTypeWidget && clock_is_picture(core.window)) {
            clock_overlay(core.window, core.seed, core.width, core.height, in_turn, core.window + kLayerAt);
            return kNone;
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

// The show's animation that plays with the smallest key above `above` unless `any` is
// set; kNothing when none.
uint32_t lowest_playing(const Core &core, uint32_t above, bool any) {
    uint32_t best = kNothing;
    uint32_t best_key = 0;
    for (uint32_t position = 0; position < core.item_count; ++position) {
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

// A range of the playlist: the show's items with `show`, and the drive's files at the
// positions of its walk from `first` to `last`. A playlist walked through its range plays
// the show's animations in the saved order, then the drive's files in the walk's order,
// which holds a folder's own files and then each of its sub-folders' once, depth first.
struct Range {
    bool show;
    uint32_t first;
    uint32_t last;
};

// The root's range: the show's items and every file of the drive.
Range root_range(const Core &core) {
    const Range range = {true, 0, drive_files(core)};
    return range;
}

// The current playlist's range: its folder's subtree, the root's while the tree is not
// known.
Range current_range(const Core &core) {
    if (!core.tree_known || core.current == 0) {
        return root_range(core);
    }
    const Range range = {false, core.current_folder.first, core.current_folder.last};
    return range;
}

// The range the playlist walks: the current playlist's, or the root's in its place.
Range range_in_use(const Core &core) {
    return core.in_place ? root_range(core) : current_range(core);
}

bool in_range(Range range, uint32_t position) {
    if (!is_drive(position)) {
        return range.show;
    }
    const uint32_t at = position - kDriveBase;
    return at >= range.first && at < range.last;
}

// The first file of the drive at or after a position of the walk within a range that
// plays, or kNothing. Each file passed over is read. Not inlined: the refresh's frame stays
// small.
ODRIG_NOINLINE uint32_t drive_playing_from(const Core &core, Range range, uint32_t from) {
    for (uint32_t at = from > range.first ? from : range.first; at < range.last; ++at) {
        if (breaks_passes_over(core, at)) {
            at = core.clocks_last - 1;
            continue;
        }
        if (drive_automatic(core, at)) {
            return kDriveBase + at;
        }
    }
    return kNothing;
}

uint32_t first_in(const Core &core, Range range) {
    if (range.show) {
        const uint32_t item = lowest_playing(core, 0, true);
        if (item != kNothing) {
            return item;
        }
    }
    return drive_playing_from(core, range, range.first);
}

// The animation after a position within a range: the next show's animation by its key, or
// the next file of the walk, else the range's first.
uint32_t next_in(const Core &core, Range range, uint32_t position) {
    uint32_t after = kNothing;
    if (!is_drive(position)) {
        after = range.show ? lowest_playing(core, order_key(core, position), false) : kNothing;
        if (after == kNothing) {
            after = drive_playing_from(core, range, range.first);
        }
    } else {
        after = drive_playing_from(core, range, position - kDriveBase + 1);
    }
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
    const uint32_t next = core.tree_known && core.current + 1u < drive_folder_count(core) ? core.current + 1u : 0;
    tree_choose(core, next);
    player_playlist_chosen(core, at);
    playlist_changed(core);
}

// The position of the animation after this one in the playlist: the next in the order of
// the range in use, the first after the last; this one again when no other plays. The current playlist takes over from its first animation as soon as it has
// something to play again.
ODRIG_NOINLINE uint32_t next_animation(Core &core, uint32_t position) {
    const bool was_in_place = core.in_place != 0;
    judge_in_place(core);
    if (was_in_place && !core.in_place) {
        return first_in(core, current_range(core));
    }
    return next_in(core, range_in_use(core), position);
}

// The count of the playlist's time is held while the playlist does not play, with the time
// left of its 5 minutes.
void counts_hold(Core &core) {
    if (!core.break_held) {
        core.break_rest = core.break_due > core.latest ? core.break_due - core.latest : 0;
        core.break_held = 1;
    }
}

// Both counts start again at a moment of the playlist.
void counts_from(Core &core, uint64_t at) {
    core.break_turns = 0;
    core.break_held = 0;
    core.break_due = at + kBreakMs;
}

// A break is cut: the turn it paused is not resumed, and both counts start again, the
// time's held until the playlist's next turn begins.
void cut_break(Core &core) {
    core.break_phase = kBreakNone;
    core.break_paused = 0;
    core.resume_seed = 0;
    core.break_turns = 0;
    core.break_held = 1;
    core.break_rest = kBreakMs;
}

// The position the playlist goes on with after a break that resumes nothing: the animation
// whose turn was to begin, else the one after it, else the playlist's first.
uint32_t back_after_break(Core &core) {
    uint32_t back = core.break_back;
    if (back != kNothing && !plays(core, back)) {
        back = next_animation(core, back);
    }
    return back != kNothing ? back : player_first_in_playlist(core);
}

// A break begins at a moment with the next clock that plays, after which the playlist goes
// back to `back`. False when no clock plays: nothing is paused, and the counts start again
// at that moment.
bool break_begins(Core &core, uint64_t at, uint32_t back) {
    const uint32_t clock = breaks_pick(core, at);
    if (clock == kNothing) {
        core.break_paused = 0;
        counts_from(core, at);
        return false;
    }
    core.break_back = back;
    core.break_phase = kBreakClock;
    if (!core.break_paused) core.break_manual = 0;
    core.turn_manual = 0;
    core.break_message = core.clock_message_on;
    core.turn_item = clock;
    core.turn_repeat = 0;
    core.zero = at;
    ++core.turn_number;
    return true;
}

// A break ends at the playlist's zero: the counts start again there. A window that passed
// during it is taken, and the next playlist plays from its first animation; else the
// paused turn goes on from where it was paused, or the playlist goes on where the break
// began.
void break_ends(Core &core) {
    const bool paused = core.break_paused != 0;
    core.turn_manual = 0;
    core.break_phase = kBreakNone;
    core.break_paused = 0;
    counts_from(core, core.zero);
    if (core.zero >= window_end(core)) {
        rotate(core, core.zero);
        core.turn_item = player_first_in_playlist(core);
    } else if (paused && core.break_back != kNothing && (plays(core, core.break_back) ||
               (core.break_manual && is_drive(core.break_back) && drive_plays(core, core.break_back - kDriveBase)))) {
        core.turn_item = core.break_back;
        core.turn_manual = core.break_manual;
        core.zero -= core.break_offset;
        core.turn_repeat = core.break_repeat;
        core.resume_seed = core.break_seed;
    } else {
        core.turn_item = back_after_break(core);
    }
}

// Pauses the playlist's turn in progress where 5 minutes of the playlist's time are
// counted, a moment in it, and begins a break there.
void pause_for_break(Core &core) {
    const uint64_t at = core.break_due > core.zero ? core.break_due : core.zero;
    const uint32_t paused = core.turn_item;
    core.break_offset = at - core.zero;
    core.break_repeat = core.turn_repeat;
    const bool seeded = core.stream_open && core.stream_drawn && core.stream_item == paused && core.stream_turn == core.turn_number &&
                        type_of(core, paused) == kTypeWidget;
    core.break_seed = seeded ? core.seed : 0;
    core.break_paused = 1;
    core.break_manual = core.turn_manual;
    break_begins(core, at, paused);
}

ODRIG_NOINLINE Reason clock_only_turn(Core &core, uint64_t now, uint64_t *in_turn) {
    for (uint32_t step = 0; step < 128; ++step) {
        if (core.playing == kNothing || core.turn_item == kNothing) { *in_turn = 0; return kNone; }
        const uint64_t length = length_of(core, core.turn_item);
        if (length == 0) return kLoopMismatch;
        const uint64_t duration = current_turn_ms(core);
        const uint64_t elapsed = now >= core.zero ? now - core.zero : 0;
        if (elapsed < duration) { *in_turn = elapsed; return kNone; }
        core.zero += duration;
        const uint32_t message = core.break_phase == kBreakClock && (core.break_message || core.clock_message_on)
            ? breaks_message(core, core.zero) : kNothing;
        const uint32_t next = message != kNothing ? message : breaks_pick(core, core.zero);
        close_stream(core);
        if (next == kNothing) { player_halt(core); *in_turn = 0; return kNone; }
        core.turn_item = core.shown = next;
        core.break_phase = message != kNothing ? kBreakMessage : kBreakClock;
        core.break_message = core.clock_message_on;
        core.turn_repeat = message != kNothing ? 1 : 0;
        core.turn_manual = 0;
        ++core.turn_number;
    }
    return kPendingWork;
}

// Moves the playlist on to the turn that a moment falls into, and gives the time since
// that turn began. A turn begins where the one before it ended, however late the moment is.
//
// Whether a turn has ended follows from the length of its animation. While that is not
// known, the first loop is decoded up to the moment, or up to the longest time the turn
// may last when the moment lies beyond it. When the loop ends on the way, the length is
// known. When it does not, the animation is in its first loop and its turn goes on; or
// the loop is longer than the longest time, and the turn ended there.
//
// While the clocks are on, a break's turns come between the playlist's: at the end of a
// turn once 5 turns are counted, or within one where 5 minutes of the playlist's time are.
ODRIG_NOINLINE Reason playlist_turn(Core &core, uint64_t now, uint64_t *in_turn) {
    if (core.clocks_on == kClocksOnly) return clock_only_turn(core, now, in_turn);
    bool rounds_taken = false;
    for (;;) {
        const uint64_t elapsed = now - core.zero;
        const uint32_t seconds = seconds_of(core, core.turn_item);
        uint64_t turn = 0;
        bool ended = true;
        if (length_of(core, core.turn_item) != 0) {
            turn = current_turn_ms(core);
            ended = elapsed >= turn;
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
            ended = beyond;
            turn = longest;
        }
        if (core.clocks_on && core.break_phase == kBreakNone && !core.break_held && core.break_due <= now &&
            (!ended || core.break_due < core.zero + turn)) {
            pause_for_break(core);
            continue;
        }
        if (!ended) {
            *in_turn = elapsed;
            return kNone;
        }
        if (!rounds_taken && !core.indexed && !core.clocks_on && core.break_phase == kBreakNone && core.turn_repeat == 0 &&
            plays(core, core.turn_item) && core.resume_item == kNothing) {
            // Whole rounds of the playlist in use are taken off at once when the length of
            // every animation of it is known, so that a long time without a refresh costs
            // one walk over the items. Not with a drive read from its index: that would
            // read every row of it, and its turns are walked one by one; nor while the
            // clocks are on, whose breaks make the rounds unequal. A turn whose loops a
            // `repeat` gave ends first.
            rounds_taken = true;
            uint64_t round = 0;
            bool all_known = true;
            const Range range = range_in_use(core);
            const uint32_t files = drive_files(core);
            for (uint32_t at = 0; at < core.item_count + files && all_known; ++at) {
                const uint32_t position = at < core.item_count ? at : kDriveBase + (at - core.item_count);
                if (!in_range(range, position) || !plays(core, position)) {
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
                    ++core.turn_number;
                    continue;
                }
            }
        }
        core.zero += turn;
        core.turn_manual = 0;
        core.turn_repeat = 0;
        if (core.break_phase == kBreakClock) {
            // The clock's turn ended: the message plays once after it, else the break ends.
            const uint32_t message = core.break_message || core.clock_message_on ? breaks_message(core, core.zero) : kNothing;
            if (message != kNothing) {
                core.break_phase = kBreakMessage;
                core.turn_item = message;
                core.turn_repeat = 1;
            } else {
                break_ends(core);
            }
        } else if (core.break_phase == kBreakMessage) {
            break_ends(core);
        } else {
            if (core.clocks_on && core.break_turns < 255) {
                ++core.break_turns;
            }
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
            if (core.turn_item != kNothing && core.clocks_on &&
                (core.break_turns >= kBreakTurns || (!core.break_held && core.zero >= core.break_due))) {
                break_begins(core, core.zero, core.turn_item);
            }
        }
        if (core.turn_item == kNothing) {
            close_stream(core);
            core.playing = core.shown = kNothing;
            core.break_phase = kBreakNone;
            core.break_paused = 0;
            counts_hold(core);
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
        close_stream(core);
        drive_faulted(core, animation - kDriveBase, reason);
        player_drive_changed(core);
        return core.clocks_on == kClocksOnly && core.playing == kNothing ? kShowsNothing : kShowsBefore;
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
// current brightness; for a picture clock its layer's colour where the layer has one.
void fill_leds(Core &core) {
    const uint8_t selected = brightness_selected(core);
    if (core.scale[255] != selected) {
        for (uint32_t colour = 0; colour < 256; ++colour) core.scale[colour] = static_cast<uint8_t>((colour * selected + 127) / 255);
    }
    const uint8_t *scale = core.scale;
    const uint16_t *pixel = core.led_pixel;
    uint8_t *out = core.led_data;
    const bool layered = core.stream_open && core.stream_drawn && type_of(core, core.stream_item) == kTypeWidget &&
                         clock_is_picture(core.window);
    if (layered) {
        const uint8_t *palette = core.decoder.palette;
        const uint8_t *layer = core.window + kLayerAt;
        for (uint32_t led = 0; led < core.led_total; ++led) {
            const uint32_t at = pixel[led];
            const uint8_t index = layer[at] != 0 ? static_cast<uint8_t>(layer[at] - 1) : core.pixels[at];
            const uint8_t *colour = palette + 3u * index;
            *out++ = scale[colour[0]];
            *out++ = scale[colour[1]];
            *out++ = scale[colour[2]];
        }
    } else if (core.decoder.colours != 0) {
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
    mini_render(core, layered ? core.window + kLayerAt : nullptr);
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
    const uint8_t selected = brightness_selected(core);
    for (uint32_t colour = 0; colour < 256; ++colour) {
        core.scale[colour] = static_cast<uint8_t>((colour * selected + 127) / 255);
    }
}

uint32_t player_first_animation(const Core &core) {
    const uint32_t first = lowest_playing(core, 0, true);
    return first != kNothing ? first : core.item_count;
}

uint32_t player_first_in_playlist(const Core &core) {
    if (core.clocks_on == kClocksOnly) {
        for (uint32_t i = 0; i < core.clocks_files; ++i)
            if (drive_automatic(core, core.clocks_first + i)) return kDriveBase + core.clocks_first + i;
        return kNothing;
    }
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
    if (core.clocks_on == kClocksOnly) return false;
    if (now < window_end(core)) {
        return false;
    }
    const uint32_t before = core.current;
    rotate(core, now);
    return core.current != before;
}

uint32_t player_window_left(const Core &core) {
    const uint64_t since = core.clocks_on != kClocksOnly && core.latest > core.window_started ? core.latest - core.window_started : 0;
    const uint64_t spent = core.window_spent + since;
    return spent < kWindowMs ? static_cast<uint32_t>((kWindowMs - spent) / 1000) : 0;
}

void player_jump(Core &core, uint32_t item) {
    if (core.clocks_on == kClocksOnly) {
        if (!breaks_position_allowed(core, item)) { player_only_restart(core); return; }
        close_stream(core);
        cut_break(core);
        core.resume_item = kNothing;
        core.playing = kPlaylist;
        core.turn_item = core.shown = item;
        const uint32_t position = item - kDriveBase;
        core.break_phase = position >= core.message_first && position - core.message_first < core.message_files ? kBreakMessage :
            position >= core.clocks_first && position - core.clocks_first < core.clocks_files ? kBreakClock : kBreakNone;
        core.break_message = core.clock_message_on;
        core.turn_repeat = core.break_phase == kBreakMessage ? 1 : 0;
        core.turn_manual = 1;
        core.zero = core.latest;
        core.zero_pending = 1;
        ++core.turn_number;
        core.only_dirty = 0;
        return;
    }
    const uint32_t cut = core.playing == kPlaylist ? core.turn_item : kNothing;
    core.resume_item = cut != kNothing && cut != item && plays(core, cut) && !in_range(range_in_use(core), item) ? cut : kNothing;
    player_play_all(core, item);
    core.turn_manual = 1;
}

void player_drive_joined(Core &core, uint32_t place) {
    if (core.clocks_on == kClocksOnly) { core.only_dirty = 1; return; }
    if (core.playing == kNothing && !core.invalid && !core.mapping_test && drive_automatic(core, place)) {
        player_play_all(core, kDriveBase + place);
    }
}

namespace {

// A position the player holds, after the drive's walk changed at `at` by `delta`: a file's
// at or after the change moves with it, the one that went is kNothing.
uint32_t shifted(uint32_t held, uint32_t at, int32_t delta) {
    if (held == kNothing || !is_drive(held) || held - kDriveBase < at) {
        return held;
    }
    if (delta < 0 && held - kDriveBase == at) {
        return kNothing;
    }
    return delta < 0 ? held - 1 : held + 1;
}

}  // namespace

namespace {

// A position the player holds, after a file of the drive moved from one position of the
// walk to another.
uint32_t moved(uint32_t held, uint32_t from, uint32_t to) {
    if (held == kNothing || !is_drive(held)) {
        return held;
    }
    const uint32_t at = held - kDriveBase;
    if (at == from) {
        return kDriveBase + to;
    }
    if (from < to && at > from && at <= to) {
        return held - 1;
    }
    if (to < from && at >= to && at < from) {
        return held + 1;
    }
    return held;
}

}  // namespace

void player_drive_moved(Core &core, uint32_t from, uint32_t to) {
    if (core.playing == kPlaylist) {
        core.turn_item = moved(core.turn_item, from, to);
    }
    core.resume_item = moved(core.resume_item, from, to);
    core.break_back = moved(core.break_back, from, to);
    core.shown = moved(core.shown, from, to);
    core.mapping_saved_shown = moved(core.mapping_saved_shown, from, to);
    if (core.stream_open && is_drive(core.stream_item)) {
        core.stream_item = moved(core.stream_item, from, to);
    }
    breaks_tree(core);
}

void player_drive_shifted(Core &core, uint32_t position, int32_t delta) {
    const bool turn_went = core.playing == kPlaylist && delta < 0 && core.turn_item == kDriveBase + position;
    if (core.playing == kPlaylist) {
        core.turn_item = shifted(core.turn_item, position, delta);
    }
    core.resume_item = shifted(core.resume_item, position, delta);
    const bool back_went = core.break_phase != kBreakNone && delta < 0 && core.break_back == kDriveBase + position;
    core.break_back = shifted(core.break_back, position, delta);
    core.shown = shifted(core.shown, position, delta);
    core.mapping_saved_shown = shifted(core.mapping_saved_shown, position, delta);
    if (core.stream_open && is_drive(core.stream_item)) {
        const uint32_t moved = shifted(core.stream_item, position, delta);
        if (moved == kNothing) {
            close_stream(core);
        } else {
            core.stream_item = moved;
        }
    }
    breaks_tree(core);
    if (back_went) {
        // The file the playlist goes back to after the break went: it goes on with the one
        // after it, from its first frame.
        core.break_paused = 0;
        core.break_back = drive_playing_from(core, range_in_use(core), position);
    }
    if (turn_went) {
        // The file whose turn it was went: the playlist goes on with the one after it, now at
        // its position, from its first frame.
        const Range range = range_in_use(core);
        uint32_t next = drive_playing_from(core, range, position);
        if (next == kNothing) {
            next = first_in(core, range);
        }
        if (next == kNothing) {
            next = player_first_in_playlist(core);
        }
        if (next == kNothing) {
            core.playing = kNothing;
            core.shown = kNothing;
        } else {
            player_play_all(core, next);
        }
    }
}

void player_drive_changed(Core &core) {
    if (core.clocks_on == kClocksOnly) { core.only_dirty = 1; player_only_refresh(core); return; }
    if (core.stream_open && is_drive(core.stream_item) &&
        !(core.playing == kPlaylist && !core.turn_manual ? plays(core, core.stream_item) : drive_plays(core, core.stream_item - kDriveBase))) {
        close_stream(core);
    }
    if (core.resume_item != kNothing && is_drive(core.resume_item) && !plays(core, core.resume_item)) {
        core.resume_item = kNothing;
    }
    if (core.playing == kPlaylist && is_drive(core.turn_item) &&
        !(core.turn_manual ? drive_plays(core, core.turn_item - kDriveBase) : plays(core, core.turn_item))) {
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
    core.break_phase = kBreakNone;
    core.break_paused = 0;
    core.break_message = 0;
    core.break_back = kNothing;
    core.resume_seed = 0;
    core.break_turns = 0;
    core.break_held = 1;
    core.break_rest = kBreakMs;
    player_set_brightness(core, core.brightness);
    if (core.invalid) {
        return;
    }
    if (core.clocks_on == kClocksOnly) { player_only_restart(core); return; }
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

namespace {

// What plays leaves the playlist's turn in progress: a break is cut, and a turn of the
// playlist that had begun counts one.
void turn_cut(Core &core) {
    if (core.playing == kPlaylist && core.break_phase != kBreakNone) {
        cut_break(core);
    } else if (core.playing == kPlaylist && core.clocks_on && !core.zero_pending && core.break_turns < 255) {
        ++core.break_turns;
    }
    core.resume_seed = 0;
}

}  // namespace

void player_counts_start(Core &core, uint64_t at) {
    if (core.playing == kPlaylist && !core.zero_pending && !core.mapping_test) {
        counts_from(core, at);
    } else {
        core.break_turns = 0;
        core.break_held = 1;
        core.break_rest = kBreakMs;
    }
}

void player_break_leave(Core &core) {
    if (core.playing != kPlaylist || core.break_phase == kBreakNone) {
        return;
    }
    const uint32_t back = back_after_break(core);
    cut_break(core);
    close_stream(core);
    core.turn_item = back;
    core.shown = back;
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
    if (core.break_phase != kBreakNone) {
        cut_break(core);
    }
    counts_hold(core);
    core.resume_seed = 0;
    close_stream(core);
    core.playing = kNothing;
    core.shown = kNothing;
    core.turn_repeat = 0;
}

void player_play_cycle(Core &core, uint32_t item) {
    if (core.clocks_on == kClocksOnly) { player_only_restart(core); return; }
    turn_cut(core);
    counts_hold(core);
    core.cycle_start_entry = 0;
    core.turn_repeat = 0;
    close_stream(core);
    core.playing = item;
    core.zero_pending = 1;
    core.shown = cycle_animation(core, core.items[item], 0);
}

void player_play_all(Core &core, uint32_t from) {
    if (core.clocks_on == kClocksOnly) { player_only_restart(core); return; }
    turn_cut(core);
    close_stream(core);
    core.turn_repeat = 0;
    core.turn_manual = 0;
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
        } else if (core.break_phase != kBreakNone && core.break_back == item) {
            // The paused turn's animation is another now: it plays from its first frame.
            core.break_paused = 0;
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
    if (core.clocks_on == kClocksOnly) { core.only_dirty = 1; return; }
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

void player_external_inclusion_changed(Core &core) {
    if (core.clocks_on == kClocksOnly) { core.only_dirty = 1; player_only_refresh(core); return; }
    if (core.playing == kPlaylist) {
        if (core.break_back != kNothing && !core.break_manual && !plays(core, core.break_back)) core.break_paused = 0;
        if (core.break_phase != kBreakNone && !plays(core, core.turn_item)) player_break_leave(core);
        player_drive_changed(core);
        if (core.turn_item == kNothing) player_halt(core);
    }
    if (core.playing == kNothing) player_item_added(core);
}

void player_only_restart(Core &core) {
    if (core.clocks_on != kClocksOnly) return;
    const uint32_t first = !core.invalid && !core.mapping_test ? breaks_pick(core, core.latest) : kNothing;
    cut_break(core);
    close_stream(core);
    core.resume_item = kNothing;
    core.resume_seed = 0;
    core.break_back = kNothing;
    core.break_manual = 0;
    core.turn_manual = 0;
    core.turn_repeat = 0;
    core.only_dirty = 0;
    if (first == kNothing) { player_halt(core); return; }
    core.playing = kPlaylist;
    core.turn_item = core.shown = first;
    core.break_phase = kBreakClock;
    core.break_message = core.clock_message_on;
    core.zero = core.latest;
    core.zero_pending = 1;
    ++core.turn_number;
}

void player_only_refresh(Core &core) {
    if (core.clocks_on != kClocksOnly) return;
    core.only_dirty = 0;
    const uint32_t item = core.playing == kPlaylist ? core.turn_item : kNothing;
    if (item != kNothing && breaks_position_allowed(core, item) && drive_plays(core, item - kDriveBase) &&
        (core.turn_manual || (drive_automatic(core, item - kDriveBase) &&
         (core.break_phase == kBreakClock || breaks_has_face(core))))) return;
    player_only_restart(core);
}

void player_clock_mode_changed(Core &core, uint8_t previous) {
    if (core.clocks_on == kClocksOnly) {
        const uint64_t elapsed = core.latest > core.window_started ? core.latest - core.window_started : 0;
        const uint64_t spent = core.window_spent + elapsed;
        core.window_spent = static_cast<uint32_t>(spent < kWindowMs ? spent : kWindowMs);
        core.window_started = core.latest;
        player_only_restart(core);
    } else if (previous == kClocksOnly) {
        core.window_started = core.latest;
        core.resume_item = kNothing;
        player_halt(core);
        tree_find_current(core);
        const uint32_t first = player_first_in_playlist(core);
        if (first == kNothing) player_halt(core);
        else player_play_all(core, first);
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
    if (core.break_phase != kBreakNone && core.break_back == item) {
        // The animation the playlist goes back to after the break leaves: it goes on with
        // the one after it, from its first frame.
        const uint32_t next = next_animation(core, item);
        core.break_back = next == item ? kNothing : next;
        core.break_paused = 0;
    }
    if (core.break_back != kNothing && !is_drive(core.break_back) && core.break_back > item) {
        --core.break_back;
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
    if (core.clocks_on == kClocksOnly && core.only_dirty && !core.invalid) player_only_refresh(core);
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
            if (core.playing == kPlaylist && core.break_held) {
                // The playlist plays again: its time is counted on from here.
                core.break_due = grid + core.break_rest;
                core.break_held = 0;
            }
        }
        shows = advance(core, now);
    }
    if (shows == kShowsPicture && core.on) {
        fill_leds(core);
    } else if (shows != kShowsBefore || !core.on) {
        memset(core.led_data, 0, 3u * core.led_total);
        mini_clear(core);
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
        mini_clear(core);
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
