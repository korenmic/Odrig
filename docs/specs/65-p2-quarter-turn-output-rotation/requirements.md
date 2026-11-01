# Requirements

The owner fixes the installation at1:1 and authorizes the proposed Settings and
shared command controls. There are no unanswered product questions.

## 1. Persistent installation orientation

1. Support exactly0,90,180,270 degrees clockwise in the correct front view.
   Existing installations without a saved setting start at0.
2. Read and atomically save one board-owned value through existing command routes.
   Refuse invalid arguments, stale revisions, unsafe concurrent storage operations
   and changes during physical mapping diagnostics. A successful no-op performs no IO.
3. A write/open/close/rename failure preserves the prior live and saved orientation.
   Invalid/unreadable saved data reports an error and uses0, without invalidating a
   playable show. A subsequent deliberate successful save may repair the setting.
4. Save across board resets, app reconnections and ordinary show replacement. Never
   write per frame. Unsupported old firmware remains usable for ordinary controls.

## 2. Square composed output

1. Apply one exact inverse coordinate permutation to the composed playback sample,
   before physical LED mapping/output and before the centered miniature projection.
   Cover RGB, palettes, dynamic text/clock/message and picture-clock overlays.
2. All playback modes, internal/external content and brightness/current limits keep
   their behavior. Source files/previews, pins, mapping geometry and timing are unchanged.
3. Miniature manufacturer wiring and dark columns remain unchanged. Mapping/snake
   diagnostics keep physical coordinates, regardless of saved rotation.
4. The board canvas is permanently square. Legacy rectangular fixtures retain0-degree
   playback and report rotation unsupported; do not add fitting/resampling controls.
5. Native emulator output uses the same core permutation. Keep existing arena/Core,
   stack/work and allocation bounds; no second full-canvas buffer or frame-time IO.

## 3. Confirmed app and command tool control

1. Settings offers a0/90/180/270 dropdown using board-confirmed state. Loading, errors,
   unsupported capability and a pending save are clear and disable inappropriate edits.
2. Do not display an unconfirmed selection as saved. A refusal, lost reply or reconnect
   rereads actual state; no blind replay. Target/visibility changes cancel unsent writes.
3. Read/set semantics and refusals are identical in app, odrigctl and existing transports.
   No new transport or physical operation is added.

## 4. Evidence

1. Check asymmetric corners/interior points, all angles, equivalent source composition,
   miniature projection, diagnostics, persistence and storage failures.
2. Check browser/native output, stale revisions/targets, lost replies and old firmware.
   Run discovered affected suites. Standalone APK/FW delivery follows these implementation checks.
3. Leave physical LED orientation and phone/on-board acceptance unticked.
