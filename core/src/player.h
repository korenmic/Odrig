#ifndef ODRIG_PLAYER_H
#define ODRIG_PLAYER_H

#include <stdint.h>

#include "core_state.h"

namespace odrig {

// The grid: a refresh is due at the power-on moment and every 20 ms after it.
const uint32_t kGridStep = 20;

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

// Plays the playlist: every animation item in turn, in the order of the item table, and
// from the first again without end. It begins with the turn of the animation item at this
// position. A turn is the animation's loops, which are the number the show gives it or
// the fewest that last the show's shortest time, and ends at the animation's longest
// time when it has one.
void player_play_all(Core &core, uint32_t from);

// The position of the first animation item, or the number of items when there is none.
uint32_t player_first_animation(const Core &core);

// The file of the animation item at this position is about to be replaced under its
// name: the player closes it when it has it open. It opens again at the next refresh.
void player_releases_file(Core &core, uint32_t item);

// The animation item at this position has another animation now. When it is the
// animation whose turn it is in the playlist, its turn begins again at the next refresh.
// When the cycle being played lists it, the cycle starts again from its first frame.
void player_file_replaced(Core &core, uint32_t item);

// An animation item was added at the end of the item table. The playlist meets it when
// its turn comes. When nothing plays, the playlist starts from its first animation.
void player_item_added(Core &core);

// The item at this position is about to leave the item table, and every item after it
// moves up by one. When it is the animation whose turn it is in the playlist, the
// playlist goes on with the animation after it, or nothing plays when it was the only
// one. When it is the cycle being played, the playlist plays from its first animation.
// Otherwise the positions the player holds follow the items, and what plays goes on as
// it was.
void player_item_leaves(Core &core, uint32_t item);

// Produces a refresh when a grid time is due: 1 when it did, 0 when none was due.
int player_poll(Core &core, uint64_t now_ms);

void player_set_brightness(Core &core, uint8_t value);

// The number of refreshes produced in the second that ended most recently before this time,
// with the seconds counted from the power-on moment. 0 when no second has ended.
uint32_t player_fps(const Core &core, uint64_t now);

}  // namespace odrig

#endif
