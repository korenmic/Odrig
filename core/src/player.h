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

// The power-on state: switched on, the brightness the startup left, and the `start` item
// playing when the show is valid and has one.
void player_start(Core &core);

// Plays the item at this position of the item table from its first frame.
void player_play(Core &core, uint32_t item);

// The file of the animation item at this position is about to be replaced under its
// name: the player closes it when it has it open. It opens again at the next refresh.
void player_releases_file(Core &core, uint32_t item);

// The animation item at this position has another animation now. When it is the item
// being played, or an animation of the cycle being played, what is played starts again
// from its first frame at the next refresh.
void player_file_replaced(Core &core, uint32_t item);

// The item at this position is about to leave the item table, and every item after it
// moves up by one. When it is the item being played, playback stops and the file that is
// open is closed. Otherwise the positions the player holds follow the items, and what
// plays goes on as it was.
void player_item_leaves(Core &core, uint32_t item);

// Produces a refresh when a grid time is due: 1 when it did, 0 when none was due.
int player_poll(Core &core, uint64_t now_ms);

void player_set_brightness(Core &core, uint8_t value);

// The number of refreshes produced in the second that ended most recently before this time,
// with the seconds counted from the power-on moment. 0 when no second has ended.
uint32_t player_fps(const Core &core, uint64_t now);

}  // namespace odrig

#endif
