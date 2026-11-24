#ifndef ODRIG_BREAKS_H
#define ODRIG_BREAKS_H

#include <stdint.h>

#include "commands.h"
#include "core_state.h"

namespace odrig {

// The file of the settings of the clocks between the animations: the mode, the message after
// each clock and the preferred storage of copies; and the file its next version is written
// into until it is renamed. No show names them.
const char kClocksFile[] = "clocks.txt";
const char kClocksPart[] = "clocks.part";

// The phases of a break: none, the clock's turn, the message's turn.
const uint8_t kBreakNone = 0;
const uint8_t kBreakClock = 1;
const uint8_t kBreakMessage = 2;

// A break comes once this many turns of the playlist, or this much of its time, are
// counted.
const uint8_t kBreakTurns = 5;
const uint64_t kBreakMs = 300000;
const uint8_t kClocksOff = 0;
const uint8_t kClocksBetween = 1;
const uint8_t kClocksOnly = 2;

// The settings a line of `clocks` changes: the mode, the message after each clock, and the
// storage whose copy of a clock or a message plays.
const uint8_t kClockSettingMode = 0;
const uint8_t kClockSettingMessage = 1;
const uint8_t kClockSettingStorage = 2;

// The start, before the show is read: removes a `clocks.part` a cut left, and reads
// `clocks.txt` whole and strictly. A missing file is the mode and the message off and the
// card's copies preferred, as are versions 1 and 2; a file out of its form or unreadable
// fails closed with `clocks unreadable` in the log, the card's copies preferred.
void breaks_start(Core &core);

// Retries uncertain settings at most once a second without using the player's file.
void breaks_poll(Core &core, uint64_t now);

// The reply to a line that changes the mode, the message or the preferred storage, the value
// a mode, 1 for on or 0 for off, 1 for the board's own storage or 0 for the card. The file
// is written, verified and renamed before the setting takes effect; a setting already in
// force writes nothing. A new preferred storage draws both orders anew at their next draw.
uint32_t breaks_command(Core &core, uint8_t setting, uint8_t value, Reply &reply);

const char *breaks_mode(const Core &core);

// The preferred storage of copies, as `status` names it: `sd` or `internal`.
const char *breaks_storage(const Core &core);

// Why Clocks only plays or waits. Without an internal folder `clocks`: `no-card`, else
// `missing-folder` without the card's folder `clocks`, else `no-clocks` while nothing plays,
// else `playing`. With one: `playing` while something plays, else `no-clocks`.
const char *breaks_only_state(const Core &core);

// Whether a position of the playlist may play: outside Clocks only, any; in it, a file of the
// card's Clocks subtree or an animation of the show whose file is in the internal one.
bool breaks_position_allowed(const Core &core, uint32_t position);
bool breaks_folder_allowed(const Core &core, uint32_t ordinal);

// Whether a face of either storage plays automatically.
bool breaks_has_face(const Core &core);

// The drive's tree was built, found again or cleared, or the positions of its walk moved:
// the clocks' folders are found again by their paths, and a new order of the clocks is
// drawn at the next break.
void breaks_tree(Core &core);

// Whether the position of the drive's walk is in the clocks' folders while the clocks are
// on, so that every playlist passes over it.
bool breaks_passes_over(const Core &core, uint32_t at);

// The clock of a break that begins at a moment: the next in the order that plays, as a
// position of the playlist, a new order drawn when it is used up or when the number of the
// faces of both storages changes; kNothing when none plays. Of two copies that play, the
// one of the preferred storage takes the turn of both.
uint32_t breaks_pick(Core &core, uint64_t at);

// The next eligible message of both storages in its independent shuffled bag, or kNothing.
uint32_t breaks_message(Core &core, uint64_t at);

}  // namespace odrig

#endif
