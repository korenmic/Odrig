# Persistent per-animation brightness — requirements

No open product questions remain in the approved seed. The owner requested
implementation after seed creation. Firmware compilation is deferred to future
seed60; final APK/key delivery follows all56–59 software. Human checks stay open.

## 1. Selection

1.1 The existing default starts from `show.json`; `brightness VALUE` changes it
only at runtime. It never rewrites the show or a saved animation override.
1.2 A nullable saved override replaces the default, with zero a valid value.
Checking captures the confirmed value without a jump; removing uses the latest
default immediately. Checking again captures that current value, not deleted data.
1.3 Apply selection before each animation's first visible frame, for manual play,
cycles, root/folder playlists, frames, text, widgets and inserted clocks/messages.
Resume uses the resumed animation's override or latest default. Diagnostics without
animation identity use the default. Changes preserve decoding, timing, repeat,
random clock seed, quarantine and mapping state.
1.4 Off is always black. Current limits and mini's cap apply after selection.
Default zero does not suppress a nonzero override; label it as a default.

## 2. Commands and status

2.1 Implement approved `brightness ID VALUE save` and `brightness ID default`
once in the core, on every existing route and odrigctl. They address the listed
file even when noncurrent. Refuse malformed/range errors, unknown ids, cycles and
folders without changes; report busy, storage failure and capacity explicitly.
2.2 Preserve existing `status.brightness` and default syntax. Add selected/saved
brightness, capability and settings-error readback aligned with animation/file
identity, without breaking old clients or the1024-byte reply bound. Old firmware
retains ordinary default controls and explicitly lacks override support.
2.3 Success is durable, not waiting on an invisible debounce. Unchanged saves
write nothing. Coalesce slider traffic into committed edits.

## 3. Identity, storage and bounds

3.1 Store settings internally, including read-only/external files. Identity is
namespace plus full path, consistent with repeats. Different folders/namespaces
are distinct; duplicate internal items share a preference. Remount/id reassignment,
another card at the same external path, replacement/restoration at the same path,
and app/runtime restart retain it. A rename creates a different identity.
3.2 Never evict absent/deleted/unlisted paths, expire entries or fall back for one
turn. Only explicit removal or deliberate storage reset removes a preference.
Document finite limits and refuse new entries with `no-space` when full.
3.3 Use bounded atomic part-write, durable close, verification and rename. A cut
leaves complete old or new settings. Failed updates retain prior usable state.
Missing settings are empty; corrupt/truncated settings report trouble and safely
use defaults without blocking boot/indexing. Never read animation bodies for a
preference or change animation CRCs, catalogs, generations or image formats.
3.4 Keep fixed startup memory, bounded indexed-media work and no per-frame
allocation or media scan. Preserve Core≤4096 and the existing128KiB host bound.
3.5 Firmware tools preserve/read back preferences alongside repeats/playlist
settings; ordinary show/firmware operations retain them unless explicitly replaced.

## 4. Shared app

4.1 Put **Override for this animation** directly beside the shortened slider.
Preserve numeric synchronization/validation, touch targets, pinned panel and
320px/landscape layout without overlap/overflow. APK and Controller use one code.
4.2 Show current file identity and **Default brightness** versus **This animation's
brightness**. Target status controls the checkbox; never save it on the phone.
Unknown/unsupported/no-animation/damaged-settings states are explicitly unavailable.
4.3 Capture a target-confirmed value. Commit a valid dirty numeric edit and read
back before changing mode, or explicitly discard it; invalid text blocks capture.
Checked edits save the override; unchecked edits use the ordinary default command.
4.4 Capture target epoch and animation identity at input start. Transitions cancel
unsent edits, never retarget queued mutations, and ignore late replies for another
identity. Accepted changes wait for readback; refusal, uncertainty, reconnect,
other-client edits and automatic transitions reconcile through fresh status.

## 5. Proof

Cover current/noncurrent selection, zero, every content/playback mode, clocks/resume,
diagnostics, off and mini cap; path/remount/read-only/absent/restored identities;
storage cuts, corruption, no-op writes, exhaustion, memory and reply bounds.
Browser tests cover input/identity transitions, late replies, failures, other clients,
reconnect, old targets and narrow/landscape layouts, including the real emulator.
Run relevant suites by discovery and record platform limitations. Later board/phone
checks stay unchecked, at brightness40 or less, with no implied build/flash proof.

Self-review: sections1–5 cover all18 seed behaviors and its technical constraints.
No new command or owner decision is introduced.
