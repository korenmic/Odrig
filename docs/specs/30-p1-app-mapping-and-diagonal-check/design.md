# Design: app mapping and a diagonal check

## Scope and protocol

The editor supports only the canonical 60x60 geometry: leg identities 1-20, three columns each, bottom/up/down/up snake direction. Detect it from the core's LED-to-pixel table, rather than accepting an arbitrary 20-leg shape. Pins are looked up by leg identity even when mapping file entries are reordered.

One command family uses existing routes and limits:

- `mapping get` returns `{ok:true,editable:true,pins:[...20 pins in snake order...],revision:N,test:false}`. Unsupported/invalid mappings return editable false and an empty pin list.
- `mapping set REV P1,P2,...,P20` validates an exact permutation and a decimal CRC-32 revision of the current pin list. A stale revision returns `mapping-conflict`; bad syntax/pins return `bad-argument`. Read-only storage returns `storage-error`; an upload or unfinished startup check returns `busy`.
- `mapping test on` and `mapping test off` are idempotent. Unsupported geometry returns `bad-argument`; invalid shows return `show-invalid`; startup/upload work returns `busy` for entry.

No status members are added: while diagnostic mode is active status reports playing and animation null. `mapping get` is the authoritative test state. Errors and new protocol forms are documented across routes and clients together.

## Persistence

Serialize the validated canonical mapping into `mapping.part`, close durably, then atomically rename over `mapping.json`. Only after rename succeeds update all in-memory pins under the caller's existing core lock. Failures discard the part and keep the current mapping. Startup removes an interrupted mapping.part. Reordered file entries are preserved in their original order, with their geometry unchanged. The canonical serializer emits equivalent geometry already verified against the LED-to-pixel table. A no-op save performs no writes.

The revision is the CRC-32 of twenty pin bytes in snake order, so the revision is stable across restarts. An acknowledged save is the new persisted mapping with its complete routing ready for the next refresh. Lost replies are recovered by re-reading the mapping before retrying. Conflict handling never overwrites another controller's changes.

## Diagnostic asset and playback

A single 1000ms JSON frame contains white at x=y and black elsewhere. A build helper invokes converter/odrig.js encode and writes a C++ include containing the encoded bytes; the source remains tracked. A deterministic generated include is checked into the core so standalone core builds need no extra toolchain and firmware embeds the same bytes. A regeneration check verifies it against the converter.

Diagnostic entry saves playback selection, halts its stream, decodes the embedded ODRG through FileSource and OdrgDecoder into existing core pixel memory, and closes the asset stream. Poll uses the normal palette/brightness and LED mapping functions on that picture until exit. No new runtime allocation or second driver is needed. A cycle resume offset selects the previously current entry; normal play resets this offset. Mutation commands are busy while testing. Drive removal still updates availability; resume falls back if needed.

## Physical output routing

Drivers retain the physical pin list established at startup because a permutation changes no hardware resources. After a core command, refresh the cached output descriptors by matching each fixed physical pin to the current logical leg and RGB pointer. Copy a complete refresh under the same lock as mapping changes. This avoids rebuilding WLED buses and prevents stale cached pointers or partial routing. Add a shared pin-routing helper usable by the fallback adapter. The current standalone firmware remains the documented seed-12 trial; building it is not evidence of full player support.

The emulator binding refreshes leg metadata after successful mapping commands. Engine publishes a mapping event after a committed update, including serial/feed commands. Its page refetches the served mapping and updates labels and routing without a reload. Existing frame order remains logical mapping-entry order.

## Shared app

Add a Mapping screen in app/www with twenty labelled selects, a draft/saved summary, Save, Cancel, Restore defaults, Reload, Show diagonal and Stop diagonal. The existing client scheduler serializes new requests with ordinary commands. Read mapping on screen entry and periodically while visible; target changes clear the draft and stale replies are ignored. A background refresh preserves a dirty draft but marks conflicts; Reload or Cancel adopts the new base. A save sends the base revision and full draft, disables actions while pending, then re-reads state. Uncertain replies are explained and never retried blindly. Diagnostic state stays target-owned, including across app reloads.

The screen is responsive, labelled for accessibility, and does not rely on color. Existing On/Off and brightness controls remain available; the test explains when power is off. No target IP, implementation setting or transport detail is exposed in this product flow.

## Verification and exclusions

Use regression tests seen failing before fixing defects. Test atomic failures/cuts, malformed pins, startup, timing/cycle restoration, idempotence, protocol routes, concurrent clients, driver data and shared UI. Run suites by discovery and build official APK/firmware artifacts. Keep every task as one commit with its checkbox. Hardware/phone checks are explicitly deferred by the user; do not flash. Build artifacts stay ignored. Update defining documents and append drift/decision history only at the end.
