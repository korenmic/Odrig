#ifndef ODRIG_PLAYER_H
#define ODRIG_PLAYER_H

#include <stdint.h>

#include "core_state.h"

namespace odrig {

// The grid: a refresh is due at the power-on moment and every 20 ms after it.
const uint32_t kGridStep = 20;

// The window of a current playlist: 24 hours of running time from the moment it became
// current, after which the next playlist of the tree is current.
const uint64_t kWindowMs = 86400000;

// The most bytes of a body the player decodes at one refresh, a record's boundary after
// it: twelve dense records of 60 x 60. It always decodes one record; what is left is
// decoded at the next refresh, from where it stopped.
const uint32_t kCatchUpBytes = 131072;

// Takes the timestamp of a call. The first one is the power-on moment; one below the
// latest counts as the latest. Returns the time the call happens at.
uint64_t clock_touch(Core &core, uint64_t now_ms);

// The power-on state: switched on, the brightness the startup left, and what a valid show
// plays by itself: the cycle its `start` names, or else the playlist, from the animation
// its `start` names or from its first one.
void player_start(Core &core);

// Stops playback and closes the file that is open for it: nothing plays.
void player_halt(Core &core);

// Plays the cycle at this position of the item table, from the first frame of the first
// animation of its list. An animation item is not played by itself: it has its turn of
// the playlist.
void player_play_cycle(Core &core, uint32_t item);

// Plays the playlist: every animation item in turn, in the saved order, and from the
// first again without end. It begins with the turn of the animation item at this
// position. A turn is the animation's loops, which are the number the show gives it or
// the fewest that last the show's shortest time, and ends at the animation's longest
// time when it has one.
void player_play_all(Core &core, uint32_t from);

// The position of the first included animation item in the saved order, one that is not
// unavailable, or the number of items when there is none.
uint32_t player_first_animation(const Core &core);

// The position of the first animation of the current playlist in the exhausting order, or
// of the root's in its place: an item or a drive's animation, or kNothing.
uint32_t player_first_in_playlist(const Core &core);

// A playlist was chosen at a moment, by a command or by the rotation: its window begins
// there, nothing resumes after a jump, and whether the root plays in its place is judged
// now.
void player_playlist_chosen(Core &core, uint64_t at);

// Takes the window's end at a moment, while a cycle or nothing plays or a test showed:
// when the window has passed, the next playlist of the tree is current from that moment,
// the root after the last and while the tree is not known. True when another playlist is
// current now: the root alone, current again, changes nothing that plays.
bool player_window_passed(Core &core, uint64_t now);

// The whole seconds left in the current playlist's window, 0 once it has passed.
uint32_t player_window_left(const Core &core);

// Plays the playlist from the turn of the animation at this position, a jump: inside the
// playlist in use it goes on from the jumped animation; outside, the animation whose turn
// the jump cut plays again after it, from its first frame.
void player_jump(Core &core, uint32_t item);

// A file of the drive has joined the playlist, at a position of the drive's walk. When
// nothing plays, the playlist starts with it.
void player_drive_joined(Core &core, uint32_t position);

// The drive's walk changed under the positions the player holds: a file came in at a
// position, `delta` 1, or the one at a position went, `delta` -1, and the positions after
// it follow. A held position of a file that went is let go.
void player_drive_shifted(Core &core, uint32_t position, int32_t delta);

// A file of the drive moved in the walk, from one position to another, the files between
// following: the positions the player holds follow it, and what plays goes on.
void player_drive_moved(Core &core, uint32_t from, uint32_t to);

// The drive's animations changed: a drive was plugged in or pulled out, or a file of it
// left the playlist. When the animation whose turn it is has gone, the playlist goes on
// with the next one that is left, from its first frame, or nothing plays.
void player_drive_changed(Core &core);

// The file of the animation item at this position is about to be replaced under its
// name: the player closes it when it has it open. It opens again at the next refresh.
void player_releases_file(Core &core, uint32_t item);

// The file at this place of the file table was quarantined. When the playlist's turn is an
// animation of it, the playlist goes on with the next usable animation, from its first
// frame at the next refresh, or nothing plays. A cycle that plays goes on while it lists a
// usable animation, and gives way to the playlist when it lists none.
void player_file_failed(Core &core, uint32_t file);

// The animation item at this position has another animation now. When it is the
// animation whose turn it is in the playlist, its turn begins again at the next refresh.
// When the cycle being played lists it, the cycle starts again from its first frame.
void player_file_replaced(Core &core, uint32_t item);

// An animation item was added at the end of the item table. The playlist meets it when
// its turn comes. When nothing plays, the playlist starts from its first animation.
void player_item_added(Core &core);
void player_inclusion_changed(Core &core, uint32_t item);

// The item at this position is about to leave the item table, and every item after it
// moves up by one. When it is the animation whose turn it is in the playlist, the
// playlist goes on with the animation after it, or nothing plays when it was the only
// one. When it is the cycle being played, the playlist plays from its first animation.
// Otherwise the positions the player holds follow the items, and what plays goes on as
// it was.
void player_item_leaves(Core &core, uint32_t item);

// The counts of the playlist's turn in progress: the id of its animation, the loops it
// plays, 0 while they are not known, the loop in progress, from 1, and the loops of its
// animation's saved repeat, 0 for none.
struct TurnCounts {
    uint32_t id;
    uint32_t saved;
    uint64_t repeat;
    uint64_t loop;
};

// Whether the playlist's turn in progress is reported: the show is valid, no test shows,
// the playlist plays, the animation whose turn it is is the one on the LEDs, and the turn's
// first refresh was made.
bool player_reported(const Core &core);

// The counts of the turn in progress at a moment: false while it is not reported. A turn
// plays the loops a `repeat` gave it, or else its animation's turn; with the length of its
// loop not known, it is in its first loop and its loops are not known unless they were
// given.
bool player_counts(const Core &core, uint64_t now, TurnCounts *counts);

// Makes the reported turn of the animation with this id so many loops long from its first
// frame, or as long as the loop in progress when that is the later end. False when no turn
// of that animation is reported.
bool player_set_repeat(Core &core, uint32_t id, uint32_t loops, uint64_t now);

// Makes the reported turn so many loops long from its first frame.
void player_hold_turn(Core &core, uint32_t loops);

// Gives the reported turn its own count again at a moment, with the loop that was in
// progress before its count changed: a turn whose own count has passed ends with that loop.
void player_default_again(Core &core, uint64_t now, uint64_t loop);

// Both counts of the clocks between the animations start again at a moment: the turns of
// the playlist from 0, and its time, held with its 5 minutes until the playlist plays.
void player_counts_start(Core &core, uint64_t at);

// A break in progress ends at once, its paused turn not resumed: the playlist's turn is the
// animation the break was to give way to, which opens anew.
void player_break_leave(Core &core);

// Produces a refresh when a grid time is due: 1 when it did, 0 when none was due.
int player_poll(Core &core, uint64_t now_ms);

void player_set_brightness(Core &core, uint8_t value);

// The number of refreshes produced in the second that ended most recently before this time,
// with the seconds counted from the power-on moment. 0 when no second has ended.
// The seed of the clock whose turn it is, while it is on the canvas: false when the
// animation whose turn it is is no clock, or its turn has had no refresh yet.
bool player_seed(const Core &core, uint32_t *seed);

uint32_t player_fps(const Core &core, uint64_t now);

}  // namespace odrig

#endif
