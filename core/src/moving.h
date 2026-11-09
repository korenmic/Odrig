#ifndef ODRIG_MOVING_H
#define ODRIG_MOVING_H

#include <stdint.h>

#include "core_state.h"

namespace odrig {

// The journal of a move of a drive's file to another folder, in the drive's folder, and the
// file it is written into until it is renamed: `odrig-moving 1 <generation>`, the file's old
// path and its new one, one line each. The saved settings of the board that name the drive's
// files by their paths, the lines `x` of `repeats.txt` and `brightness.txt` and the lines `f`
// of `ignored.txt`, follow the file once the commit of the generation is made.
const char kMovingFile[] = "drive/moving.txt";
const char kMovingPart[] = "drive/moving.part";

// Before the commit of the move of the file `from` to `to`, whose generation is the one
// given: writes the journal. False on a failed storage call, nothing then being left.
bool moving_begin(Core &core, uint32_t generation, const char *from, const char *to);

// The commit was not made: the journal is removed.
void moving_given_up(Core &core);

// After the commit: the saved settings of `from` are given to `to`, in each file that has
// any, those `to` had there being dropped, and the journal is removed once they are. A
// failed storage call leaves the journal for the next mount.
void moving_end(Core &core, const char *from, const char *to);

// The journal that a cut or a failed call left, on a drive the core may change while no upload
// is open and no rebuild runs: finished as moving_end does when the drive's catalog is of its
// generation and has a file of its new path, else removed.
void moving_settle(Core &core);

}  // namespace odrig

#endif
