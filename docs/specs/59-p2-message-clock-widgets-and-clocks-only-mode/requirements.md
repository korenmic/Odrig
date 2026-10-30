# Message clock widgets and clocks-only mode — requirements

The owner authorized S 2 S, enqueue and implementation of seeds 59 then 60, with one
stacked branch per seed and one final PR from the tip. Both have no open owner
product questions. The later seed 60 now includes the firmware build pipeline;
final APK and firmware uploads follow all software. No board writes are authorized.

## 1. Seven complete runtime messages

1.1 Produce seven separate 60 x 60 ODRGX widget animations, in source tab order:
`v7-consciousness`, `v7-symmetry`, `v7-temperature`, `v7-the-time`, `v7-countdown`,
`v7-the-clock` and `v7-mistakes`, each with `.odrgx` suffix under
`collection/card/clocks/message/`. Preserve the existing message and its assets.
1.2 Preserve every Hebrew sentence, punctuation mark, ordering, wrap and zero
subtitle from the retained HTML. A widget completes only its own tab, including
the long final sequence, without advancing into another source tab.
1.3 Use the default split layout: small fixed bright text above rolling digital
time, white text and blue sweep, smooth wheel motion, and the moving white square
in the bottom three rows. Unlit physical pixels are black; simulator grid outlines
and dark background are decoration, not illuminated output.
1.4 Preserve the source timeline:5 s hold,0.6 s fade-in,0.5 s fade-out,0.5 x clock
speed,0.5 s digit roll,4 s pendulum period, motion curve 1,9 s colour-wave interval
and 1.5 s wave duration. Countdown ten through zero takes 2 s per entry without the
ordinary text fade, retaining zero above its three follow-up subtitles.
1.5 Consciousness slows the clock and pendulum over 3.5 s after the specified source
sentence; its stopped digits/square remain steadily lit. The clock tab freezes its
square at the source's stop sentence. Preserve text fades without introducing
blinking or fading the stopped clock/square.
1.6 Implement a bounded runtime widget subtype within the existing container and
32 KiB widget payload budget. Do not substitute captured video, frame streams or a
browser engine. Existing payloads and their acceptance behavior stay compatible.
1.7 Use explicit seeded virtual time. Payload, seed and elapsed time determine
identical pixels across converter, Python reader/validation, shared core, emulator
and firmware; the board needs no browser, system font, network or real-time clock.
Licensed glyph/mask assets may be compiled offline. Document and visually verify
font adaptation against the source.
1.8 Declare the complete tab duration with millisecond precision. One message turn
plays one whole loop rather than a 30 s cutoff. Loop restart and rendering at an
arbitrary elapsed time are coherent and independent of prior messages.

## 2. Collection and deployment

2.1 Track reproducible source/generator, all seven widgets, GIF previews and normal
collection readmes/provenance. Add thumbnail catalog paths under `clocks/message`;
do not introduce a parallel `msg` folder.
2.2 Resolve the share destination through `env`/`env.template`, copy the same
deliverables there and verify readback bytes. Physical SD deployment remains a
later approved catalog-managed operation, never a bare copy followed by boot scan.

## 3. Persistent three-state clock mode

3.1 Replace the clock-enable checkbox with a `Clocks` dropdown: `Off`, `Between
animations`, `Clocks only`. Keep the independent message checkbox and shared
Controller/APK code, acknowledged state, pending/refusal/uncertainty handling,
reconnect and other-client updates. Do not add source-layout authoring controls.
3.2 Approved `clocks off`, `clocks on`, `clocks only` select those modes through
every existing transport and odrigctl. Preserve the first two meanings.
3.3 Persist mode and message setting atomically on internal storage. Migrate valid
old settings: old off→Off, on→Between, retaining the message flag. Missing/invalid
settings recover safely without blocking boot. Add explicit mode status while
preserving existing boolean clients and normal install/update preservation.

## 4. Exclusive playback boundary

4.1 Resolve external root `clocks` by active catalog/tree path on boot, remount and
catalog refresh. Do not remember transient IDs or infer it from substrings/types.
Direct children are automatic clock faces; direct files of `clocks/message` are
automatic messages. Browsing the full tree stays unrestricted.
4.2 Entering Only promptly stops outside playback and starts an eligible clock.
Exhaust a shuffled clock-face bag before reshuffling. With message enabled, insert
one complete message loop after each clock; exhaust all eligible direct messages
before reshuffling. Apply the message bag to Between too. Do not recursively run
the five-turn/five-minute break scheduler within Only.
4.3 Shared core enforcement covers explicit files/folders/cycles, `play all`,
automatic next, folder windows, resume, mutation cleanup and display diagnostics.
Reject outside play without changing current selection/playback. A global restart
action targets Clocks; an output-taking diagnostic requires leaving Only first.
Explicit inside-subtree messages remain playable with automatic messages disabled.
4.4 Initially open the resolved Clocks folder on selecting Only; later browsing
must not be reset by polls. Explain disabled outside Play controls.
4.5 Missing card/folder/faces, all ignored or quarantined candidates: retain Only,
stay dark and responsive, and report why. Never fall back outside Clocks or spin
over unavailable entries. Re-resolve and resume after valid media/catalog changes,
without animation-body rescanning.
4.6 Leaving Only restores the prior valid normal playlist, else root, without a
stale ID or paused break. Preserve the message flag and identical behavior over
all transports, the emulator and firmware.

## 5. One inclusion model in both modes

5.1 Extend approved `ignore ID 0|1` and existing Ignore/include UI to external
clock/message files and folders, including roots and nested folders. Report own
and inherited exclusion distinctly while keeping entries browsable. Do not add
another independent clock exclusion setting or command spelling.
5.2 A candidate is eligible only when available, not quarantined, not itself
ignored and without an ignored ancestor. Apply this rule to both bags, traversal,
automatic advances, boot/resume and prepared candidates. Parent inclusion must
not erase separately saved descendant exclusions.
5.3 An acknowledged change invalidates stale candidates immediately. If an
automatic current turn becomes excluded, transition at the next safe boundary
without another loop or full-turn wait. In Between, no faces skips the break;
no messages skips only the message. In Only, no faces stays dark in that mode.
Ignoring `clocks/message` suppresses messages; ignoring Clocks suppresses its tree.
Re-inclusion restores eligibility without reboot or body scan.
5.4 Ignore stays automatic exclusion, not deletion, quarantine or manual-play ban.
Manual ignored playback remains allowed within the mode boundary. Persist stable
namespace/path identities across reboot, modes and changed catalog IDs, using
atomic internal settings without writable SD or animation/catalog rewrites.
Failed saves are refusals, never acknowledged success.

## 6. Limits and proof

6.1 Preserve fixed/bounded memory and work, existing decoder/format validation,
quarantine/catalog boot, brightness overrides, miniature projection and current
limits. No GPIO, supply, partition, flashing or time-sync change is introduced.
Do no work merely to increase an acceptable board 20–50 Hz rate.
6.2 Discover relevant suites. Cover strict malformed payloads, source text/timing,
Hebrew layout, countdown, sweep, stopping effects, seeded equivalence and complete
loops. Record visual source comparison and intended font/decoration adaptation.
6.3 Cover all boundary entry points, bags, media changes/missing/quarantine,
migration/atomic failures, own/inherited exclusions, stale prepared candidates,
current-turn exclusion, re-inclusion, changed IDs, read-only SD and manual rules.
Browser tests cover mode choices, old targets, browsing and disabled Play actions.
6.4 Update format/command/show/app/core/firmware-additions and collection docs;
append historical resolutions only. Build final APK/FW after 59 and 60 software,
verify artifact/share readback, and report all unperformed board/phone checks open.

Self-review: sections 1–6 cover all 22 approved seed behaviors and acceptance scope.
No material requirement gap or unanswered owner choice remains; technical design follows separately.
