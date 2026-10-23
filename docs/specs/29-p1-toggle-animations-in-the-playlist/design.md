# Design: shared playlist and storage management

## Model and playback

Use two padding bytes in ItemInfo for ignored and explicit-presence flags, preserving
the 16-byte item table. JS and Python readers validate a strict boolean and preserve
absent versus explicit false when packing. The streaming JSON reader gains boolean
parsing; show parser recognizes the optional member on animations only.

Separate playable animations from automatic playlist membership. next_animation and
whole-round duration skip ignored items. An explicit ignored turn consumes its usual
length before the next included item, or idle if none. Do not fold that one-off turn
into the duration of a repeating playlist. Startup skips an ignored start; cycles
still resolve all members. An ignore commit calls a player helper only when the
active playlist item becomes ignored, or an idle player gains an included item.

## Durable mutations

Extend ShowChange with an inclusion override and a bounded removed-id array/count.
The canonical writer preserves presence and value of ignored for every surviving
animation. Ignore writes show.part, closes, atomically renames, then updates memory;
idempotent calls avoid writes and playback changes.

Parse at most 32 ids into a stack array; resolve and validate all in the core before
storage work. Bulk deletion journals each unique unreferenced filename (max1056
bytes), writes the filtered show once, then atomically renames it. Read pending.txt
up to1500 bytes using the existing chunk. Settle prior journal before beginning any
new transaction and refuse storage-error if cleanup remains unresolved. Commit
playback/table removals only after rename; use descending positions and membership
filtering so a removed item cannot be selected as the next turn. File cleanup may
be retried on boot. Never delete a file still referenced by surviving metadata.

## Host capacity and transport

Append optional drive_space(ctx, generation, uint64_t*free, uint64_t*total) to the
host callback table. Existing functions remain unchanged; update ctypes and fixture
layouts. space reads current drive generation and validates free<=total and exact
JSON-integer bounds. Reply.number accepts 64-bit values. External object is always
present in replies; null callback/capacity failure gives null counters.

Expose a read-only capacity query from the pinned MSC VFS adapter using f_getfree,
volume cluster count and sector size, while holding the drive mutex. No formatting
or deletion on external media. Emulator uses shutil.disk_usage on its current drive
folder. odrigctl adds ignore and remove many forms, simply forwarding commands.

## Shared app

Protocol validators accept required ignored on installed list entries, absent on
external entries, and capacity object with safe integer/null validation. Client
keeps one serialized queue for commands, list, space and mapping; snapshots include
inclusion and external capacity. Mutations expose promises tied to target generation.

Show rows separate play and Include in playlist inputs. Storage owns selection by
id, confirmation and sequential <=32 batches. Capture the target generation for a
whole operation; target switch cancels subsequent batches. On failure refresh before
reconciling selection; show partial counts and uncertainty without retrying. Disable
upload/delete/selection while a deletion is pending. Shared capacity rendering is
used by Show and Storage. Existing scheduler refreshes space at startup, recovered
link, upload/delete outcomes and every10seconds in relevant views.

## Validation and delivery

Add regressions in existing discovered converter/Python/core/emulator/firmware/app
suites, observed failing before implementation. Cover parser parity, pagination,
startup and long gaps, explicit ignored turns, cycles, empty state, storage cuts,
shared files, invalid mixed batches, capacity >4GiB/unavailable/hotplug, all routes,
UI errors, stale replies and selections >32. Retain mapping/diagonal regressions.
Record suite counts, hashes and limitations in the verification handoff. Use the
existing debug signing key, rebuild final committed app source, overwrite Drive APK
in place, add WLED image and verify copies/downloads. No owner-only tasks are ticked.
