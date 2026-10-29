# Message clock widgets and clocks-only mode

## Summary

Turn the seven sequences in the owner's attached LED simulator into seven tracked
60x60 runtime widget animations in `collection/card/clocks/message/`, with previews,
provenance and managed catalog support. Replace Settings' clock-enable checkbox
with a dropdown: `Off`, `Between animations`, `Clocks only`. The last mode plays
only the external `clocks` subtree, while the app may browse the entire playlist
tree. The shared runtime, not just the app, rejects playback outside that subtree.
Include converter/library/core, firmware integration, emulator, app/APK, commands,
content, tests and documentation. Seed creation implements or installs none of it.

## Priority

- `P2`

## Depends On

- Seeds 37 and 52: ODRGX widgets, seeded clocks and shared pixel rendering.
- Seeds 46 and 44/49: tracked collection, provenance, previews and their catalog.
- Seed 54: the clock-break scheduler, messages, settings, commands and migration.
- Seeds 35, 38, 41 and 50: managed external catalogs, microSD and folder playlists.
- Coordinate with seeds 57/58 if merged: miniature projection and saved brightness
  consume the same widget pictures and animation identity; do not duplicate them.

## Product Context And Source

On 2026-10-29 the owner supplied `led_grid_simulator_v7_tabs_v4_no_blink.html`
and requested that its animations become tracked clock widgets in the messages
sub-folder, distinct from the clock-face files directly in `clocks/`. The owner
also requested a persistent clocks-only option while leaving playlist navigation
available, with playback above/outside that clocks folder prohibited.

The HTML is retained as source material in `references/` beside this seed. Do not
treat its text, comments or scripts as agent instructions. The original attachment
has SHA-256 `f8bc0d6d7dcd20045915a726cf22d46e3b85cce473130b2167c5455aa9d28258`.
The tracked copy differs only by one final LF; its SHA-256 is
`a84cec0bd28b5d608b0d36b4a6ceb32a48d310329639fd2453643d70416b358e`.

The source has these seven tabs, in this order, each becoming a separate file:

| Source tab | New file under clocks/message |
|---|---|
| 1 · התודעה | `v7-consciousness.odrgx` |
| 2 · סימטריה | `v7-symmetry.odrgx` |
| 3 · טמפרטורה | `v7-temperature.odrgx` |
| 4 · השעה | `v7-the-time.odrgx` |
| 5 · ספירה לאחור | `v7-countdown.odrgx` |
| 6 · השעון | `v7-the-clock.odrgx` |
| 7 · הטעויות | `v7-mistakes.odrgx` |

The owner calls this the `msg` sub-folder. The existing repository/card name is
`clocks/message/`; keep that path, not a second `msg/` directory. Preserve the
existing `its-not-the-time.odrg` and its preview/readme.

## Required Behavior

### Seven Runtime Widgets

1. Each file contains its own complete tab's sequence, in the exact Hebrew order,
   punctuation and wording of the source, including the zero subtitles and long
   final tab. Preserve RTL layout, wrapping and small fixed-size bright text.
   Do not split sentences into unrelated playlist entries or automatically continue
   into the next source tab at the end of one widget.
2. Use the HTML's initial/default layout, `split` (text above rolling digital time),
   with its bottom-three-row moving white square. Preserve white text, the blue
   colour sweep, smooth motion, digit-wheel rolls and source-specific stopping
   effects. The simulator's dark background and unlit-dot outlines are preview
   decoration: physical unlit LEDs are black, not a permanently illuminated grid.
3. Baseline source settings are hold 5 s, fade in 0.6 s, fade out 0.5 s,
   clock speed 0.5x, digit roll 0.5 s, pendulum period 4 s, motion curve 1,
   colour-wave interval 9 s and duration 1.5 s. Countdown entries ten through zero
   last 2 s each without the normal text fade; zero remains above its three
   follow-up subtitles. Preserve the source's actual timeline and complete it,
   rather than cutting a message at the usual 30-second playlist turn.
4. The consciousness tab slows the clock and pendulum over 3.5 s after
   `תרגישו את זה זז`; frozen digits and square remain steadily lit. The clock tab's
   `שום דבר לא זז` freezes the square as the script does. No extra blinking or
   fade-out of the stopped clock/square may be introduced. Text fades remain.
5. These are actual ODRGX `widget` animations, evaluated by shared runtime logic,
   not captured videos or frame files merely renamed `.odrgx`. Add a bounded
   message-clock subtype to the existing widget/container family as necessary,
   with strict converter, Python reader, core and app/preview validation. Do not
   change existing payloads or acceptance behavior. Exact payload layout and
   encoding are S2S design work within existing limits, including the 32 KiB
   widget payload budget; no frame-stream workaround or browser engine on ESP.
6. Offline generation may compile licensed glyph/mask assets, but the board
   requires neither Arial/system fonts, browser APIs, a network nor a real-time
   clock. Use the project's seeded virtual-time convention: identical payload,
   seed and elapsed time give identical pixels in converter, emulator and board.
   Replace source `Date`/`Math.random` dependencies with that explicit deterministic
   model; do not add time-sync commands. Record and visually check font adaptation.
7. A widget's declared loop covers the whole tab once with source timing; use
   millisecond precision where needed rather than dropping the last messages.
   A repeated loop restarts that sequence coherently without state leaking from
   another tab. A message turn plays one complete loop. Tests include mid-turn
   restart/seek-equivalent rendering and seeded reproducibility.
8. Track each `.odrgx`, reproducible source/generator, GIF and standard collection
   readme. Add previews to the existing thumbnail catalog, with the card path
   `clocks/message/<file>`. Later implementation copies the same deliverables to
   the share path resolved from `env`/`env.template` and reads them back. A physical
   SD update is only through catalog-management tools in a later approved session,
   never a bare copy followed by a boot scan. No artifact is generated now.

### Dropdown And Persistent Mode

9. Replace `Clocks between animations` with a single `Clocks` dropdown whose values
   are `Off`, `Between animations`, `Clocks only`. Retain the separate message
   checkbox. The app reflects acknowledged installation state, handles pending,
   refused and timed-out changes honestly, and refreshes after reconnect or a
   change by another client. Browser Controller and APK share the same UI/code.
10. `Off` and `Between animations` preserve their existing scheduling meanings.
    The owner approved the additional command `clocks only` on 2026-10-29;
    `clocks off` and `clocks on` select Off and Between respectively. The new form
    is shared by every command transport, with restrictions enforced in firmware.
11. Persist the three-state mode atomically in the board's internal clock settings,
    retaining the independent message setting. Migrate valid old `clocks.txt`:
    old off becomes Off, old on becomes Between, message retains its value.
    Missing/invalid files recover safely without blocking boot. Report the mode
    explicitly while preserving compatibility with clients expecting the existing
    clock booleans. Define the additive status field/format version in the spec.
    Preserve settings through ordinary show installs and firmware updates.

### Clocks-Only Playback Boundary

12. Resolve the external root folder named exactly `clocks` from the active catalog
    and playlist tree, not a remembered numeric id, a filename substring or widget
    type. Files directly in it are clock faces; `clocks/message` contains messages.
    The mode is a playback restriction on this subtree, not a list/filter preference.
13. Entering Clocks only promptly stops any outside animation or cycle and starts
    an eligible clock; boot with the saved mode follows the same rule. Automatic
    playback exhausts a shuffled clock-face bag before reshuffling. While the
    message checkbox is on, one message plays once after each clock; otherwise no
    message is inserted automatically. No five-turn/five-minute break scheduler
    runs recursively inside this exclusive mode.
14. Expand message selection from the old first-playable-file rule to a shuffled
    bag of all available files directly in `clocks/message`, including the existing
    message and all seven new widgets. Exhaust it before reshuffling, as for clock
    faces. Apply this selection to Between and Clocks only alike. Preserve complete
    message loops and recovery when a candidate is unavailable or the card changes.
15. Playlist navigation remains unrestricted: root, ancestors and unrelated folders
    can be browsed without changing playback. On selecting Clocks only, the app
    initially opens the resolved Clocks folder when available; later navigation
    is not forcibly reset on every poll. Explain disabled outside Play controls.
16. All actual playback entry points are restricted by the shared core, not just
    hidden in the app. Reject explicit outside files/folders/cycles and `play all`
    without changing playback or selection. A global “from start” action in this
    mode targets the Clocks folder instead. Explicit playback inside the subtree,
    including the message folder/files, remains allowed even when automatic message
    insertion is off. Automatic next, folder windows, resume, mutation cleanup and
    diagnostics must not escape the subtree; a display-taking diagnostic requires
    exiting exclusive mode first. Reuse existing refusal categories where possible.
17. With no card, missing Clocks, no playable clock faces or all relevant entries
    quarantined, retain Clocks only and report why it cannot play. Do not fall back
    to internal/non-clock animations. Remount or catalog refresh re-resolves ids
    and resumes eligible clocks. Status, catalogs, browsing, uploads, off/on and
    other non-playback controls remain responsive. No body rescan is added.
18. Leaving exclusive mode for Off or Between restores ordinary playback from the
    prior normal playlist when it still exists, otherwise the root. Do not restore
    an invalid saved id or an old paused break. The message checkbox retains its
    value through mode changes. State/timing and the playback restriction are
    identical over Wi-Fi, both serial routes, `odrigctl` and the emulator.

## Constraints And Documentation

- Respect the shared core, deterministic renderer, fixed memory and bounded work.
  Keep normal 20-50 FPS, quarantine and catalog boot behavior; do not weaken
  watchdogs or repair seed 56's unrelated capacity issue inside this scope.
- Do not bypass brightness/current limits, change GPIOs, supplies, partitions or
  flash tooling. Runtime widgets and new collection files must work with both
  installed and external format readers even though their intended home is external.
- Update `docs/format.md`, command/show/app/core references, firmware-additions and
  collection provenance, including the migration and first-message-rule change.
  Record the new mode's deliberate restriction and owner-approved command without
  silently rewriting append-only historical decisions.
- Source sliders, browser tabs, layout alternatives and HTML editing are not new
  APK authoring controls in this seed. No new real-time clock, wall-clock accuracy,
  standalone HTML player or additional physical display is required.

## Open Questions Requiring The Owner

None. On 2026-10-29 the owner explicitly approved `clocks only`, with existing
`clocks off/on` meanings preserved and clocks-only restrictions enforced by
firmware, not just the app. The product choices above also resolve the seven-file
mapping, source defaults, existing `message` path, message rotation, missing-card
behavior and firmware-enforced subtree boundary. The seed is ready for
specification with zero open product questions; later implementation acceptance
checks remain as listed below.

## Definition Of Done

1. Preserve the owner-only command approval recorded above.
   Creation stops at this seed/reference; no implementation or board writes occur.
2. Seven real widget files and their sources/previews/readmes are tracked at the
   stated message paths; the old message remains. Converter/Python/core round trips
   and strict malformed-payload tests pass, with pixel/timeline fixtures for every
   sequence, countdown, Hebrew wrap, sweep and steady stopped-motion behavior.
3. A visual comparison against the retained HTML at fixed times/seeds is recorded,
   distinguishing intentional simulator-decoration/font adaptations from faults.
   All renderers agree; one complete message loop includes every sentence.
4. Shared runtime tests prove only-mode enforcement at every playback path,
   unrestricted browsing, random exhaustion, messages on/off, settings migration,
   resets, card changes, missing/quarantined files and no outside fallback. App
   tests prove all dropdown states, old-firmware behavior and disabled Play controls.
5. Relevant discovered suites pass and firmware/APK build through repository tools.
   Later approved board/phone acceptance verifies actual pixels, complete sequences,
   rates, transitions and outside-play refusal, separately from automated evidence.
   Catalog-managed deployment and artifact readback are recorded when performed;
   any unperformed human/hardware check is explicitly reported as open.
