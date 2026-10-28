#ifndef ODRIG_REPEATS_H
#define ODRIG_REPEATS_H

#include <stdint.h>

#include "commands.h"
#include "core_state.h"

namespace odrig {

// The file of the saved repeats, and the file its next version is written into until it is
// renamed. No show names them: a name in `show.json` ends in `.odrg` or `.odrgx`.
const char kRepeatsFile[] = "repeats.txt";
const char kRepeatsPart[] = "repeats.part";

// The most lines the file holds.
const uint32_t kRepeatsLines = 512;

// The loops of the saved repeat of the animation at a position of the playlist, an item of
// the item table or kDriveBase and a position of the drive's walk; 0 when it has none.
uint32_t repeats_of(const Core &core, uint32_t position);

// The start, once the order is read: the saved repeats of the show's items from the file.
void repeats_start(Core &core);

// Reads the whole file again at once and sets every saved repeat, of the items and of the
// drive's files.
void repeats_reload(Core &core);

// A drive's files were counted, or it left: its saved repeats are dropped until its lines
// are read.
void repeats_drive_found(Core &core);

// A drive is taken up: the file is read whole at once and its lines `x` give their loops to
// the files of the drive of their names, the first kRepeatsDriveMost of them, before any of
// its files plays. The log says `repeats over` once when more would.
void repeats_drive_taken(Core &core);

// The reply to `repeat <id> <n> save`: the listed animation with the id keeps `n` loops for
// every later turn, and its reported turn plays them. The whole file is saved before the
// reply.
uint32_t repeats_save(Core &core, uint32_t id, uint32_t loops, uint64_t now, Reply &reply);

// The reply to `repeat <id> default`: the listed animation with the id has no saved repeat
// any more, and its reported turn plays its own count again.
uint32_t repeats_restore(Core &core, uint32_t id, uint64_t now, Reply &reply);

}  // namespace odrig

#endif
