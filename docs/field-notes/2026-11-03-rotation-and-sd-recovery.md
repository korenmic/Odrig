# Field recovery journal: rotation boot and microSD

Report date: 2026-11-03, Israel time. Source: the owner's field report in this chat.
This is a live operational record, not a diagnosis or proof that hardware is damaged.
Later owner reports update the current summary and append an observation; corrections
supersede earlier claims explicitly. Do not repeat a completed test unless a relevant
condition changed or the owner requests it.

## Current situation

| Item | Confirmed or reported observation | Still unknown |
|---|---|---|
| Original installation ESP32S3 | Owner reports persistent failure to finish boot/no hotspot with the supplied rotation firmware. Green LED blinks continually. | Exact failure stage/reset cause; exact selected firmware hash in this report. |
| Original outside installation | Same symptom when removed from the breadboard and all installation connections, powered only from the phone. | This does not identify a damaged component or distinguish software from stored state. |
| Master control | Owner previously confirmed master firmware boots the original board. | Not a fresh controlled reflash in today's report. |
| Spare ESP32S3 | Rotation firmware boots and the phone app connects. Owner reports zero internal animations. | Not necessarily an empty filesystem: mapping/settings/partition layout are not recorded. Actual wall rotation is not yet verified. |
| Internal content | Original contains many animations; spare has none. | Exact bytes, inventory, settings and partition layout of each board. Board identity and stored state are confounded in this comparison. |
| microSD | App reports external storage as "absent". | Card/reader/contact/board/configuration cause; "absent" alone is not proof of card damage. |
| SD connecting wires | Owner has already replaced them. | Per-attempt timing/configuration not separately captured; SD is still absent in the overall report. |
| SD reader module | Owner has already replaced it. | This was the reader module, not the physical microSD card. |
| Physical microSD card | Has not been replaced. Owner prefers to keep it. | Its condition and contents have not been independently checked. |
| Clock assets | Claude prepared the final required clock animations with rotation baked into the files. Owner estimates roughly 3 MB. | Exact archive/version/size in this report; whether total or currently free internal storage is insufficient. |
| Available operator tools | Phone only at the installation; owner is walking there, estimated 10–15 minutes from the report. | Windows is not physically available at the installation. |

The spare's successful boot is evidence against a failure inevitable on every board
with this rotation firmware. It does not prove the original board is physically
damaged. Content, saved configuration, partition layout, exact firmware bytes and
hardware identity are not isolated yet.

The original's standalone failure means the installation breadboard/reader/wiring is
not required for that original-board boot symptom. It does not rule out a separate
breadboard/contact problem affecting SD detection.

## Attempts already performed

| ID | Board / changed condition | Owner-reported result | Status |
|---|---|---|---|
| F01 | Original, installation/breadboard connections, rotation firmware | Persistent failure/no hotspot | Done |
| F02 | Original, standalone off breadboard, nothing connected except phone power | Same persistent failure | Done; no reason to repeat unchanged |
| F03 | Spare, no internal animations, rotation firmware | Boots; app connects | Done; physical wall orientation unverified |
| F04 | Replaced SD connecting wires | Already tried; SD remains absent in overall report | Done |
| F05 | Replaced SD reader module | Already tried; SD remains absent in overall report | Done |
| F06 | Replace original board at installation with the already-flashed spare | No result reported yet | Planned |
| F07 | Bypass breadboard for SD reader using direct connecting wires | No result reported yet | Optional/planned if SD remains absent |
| F08 | Replace physical microSD card | Not tried; owner prefers not to do this | Deferred; not a required immediate step |

## Next observations, following the owner's plan

1. **F06: swap the board only.** Disconnect power before changing connections. Use the
   already-flashed spare and retain the current physical microSD card, latest reader,
   wires and connection path as far as practical. Record boot/hotspot, app connection
   and the exact external-storage state. Do not silently mark these three as one result.
2. **If SD appears:** browse a known clock folder and play a known file. Record whether
   playback works and what orientation is actually visible. A restored listing alone
   does not prove a file can be read and played.
3. **If SD stays absent and the owner proceeds with F07:** disconnect power first;
   keep the same spare, firmware, reader and card, and change only the breadboard
   connection path to the owner's planned direct-wire path. Record recognition and
   playback separately. Do not change pin assignments, voltage or power design here.
4. **Read storage figures when the app connects:** internal total/free bytes and
   external state/total/free if available. Treat unknown space as unknown. Do not erase
   or replace the original board's stored animations to manufacture an empty control.
5. **Keep F08 deferred** unless the owner chooses it after the above observations.
   No factory reset, filesystem format, flash-layout change or card replacement is
   part of this journal's immediate plan.

If several variables change together, record all of them and limit attribution.
Once the required working configuration is obtained, do not add diagnostic changes
merely to complete the matrix.

### Interpreting the next result

- Spare works in the installation and sees the existing card: useful working
  configuration established; original hardware versus original stored state remains
  unresolved.
- Spare boots but the card stays absent: track boot and SD as separate symptoms.
- Spare works standalone but fails only when installed: installation dependence is
  newly established for the spare; it does not invalidate F02 for the original.
- Direct connection restores SD: the bypassed connection path is implicated, without
  identifying one precise defective component.
- Card appears but files will not open: record the read/playback error separately;
  do not call this the same result as "absent".

## Rotation and capacity notes

Record the file variant (original or pre-rotated), the runtime rotation setting and
the observed wall orientation together. A file pre-rotated90 degrees plus another
90-degree runtime rotation is180 degrees relative to its original; do not accidentally
count a double rotation as a new boot or SD fault.

"Zero internal animations" is not proof that both boards share the same filesystem
layout or configuration. Application-only flashing does not establish identical
partition tables or erase saved state.

The earlier seed73 text recorded a particular113-file archive at1,255,654 unpacked
bytes and one board at13,500,416 total bytes. Those are historical measurements from
a different report, not guarantees for today's spare, archive or free space. Preserve
the owner's current ~3MB estimate as a report until the actual selected bytes and
target-reported capacity are recorded.

## Software planning requested now

- Seed73 already exists on master and is being hardened: phone ZIP selection,
  Select all/manual selection, byte-preserving sequential upload and live projected
  capacity for an explicitly selected Internal/External destination.
- Seed74 is separate: backup/download selected installed animations, real folder
  creation, folder playlists, cut/paste and actual path changes on the board, with
  recoverable catalog/settings updates.
- Both are planning work. Neither adds working phone bulk-upload/explorer features
  to today's APK. Exact new protocol additions for seed74 require owner approval
  before implementation.
- Existing diagnostic model tests did not reproduce the field failure. Their
  controlled populated fixture is not a byte-for-byte copy of the original board's
  complete internal storage, settings and partition layout.

## Update format

For each new attempt record: time; attempt ID; board original/spare; firmware filename
and build/hash if known; internal-animation state; standalone/breadboard/direct path;
power source; whether card/reader/wires were retained; hotspot; app connection;
SD state; read/playback result; asset variant/runtime rotation/observed orientation;
exact error text when available. Missing values stay "not reported".

### Observation log

- **2026-11-03, initial owner report:** F01–F05 reported as already performed; F06/F07
  planned, F08 deferred. No installation result for the spare has yet been reported.

## Artifact delivery preference

Use a direct Google Drive file share URL when available. Otherwise give the complete
absolute local mounted path as quoted text. A Drive search URL is not an acceptable
replacement.

Existing separate diagnostic-only firmware (not a repair):
"G:\My Drive\Artifacts\odrig\rotation-boot-diagnostics\odrig-rotation-boot-trace-81b4af6.bin"

Existing rotation release artifact, now archived:
"G:\My Drive\Artifacts\odrig\odrig archive\standalone-rotation\odrig-rotation-firmware.bin"

Do not infer which of these was flashed in today's field report from its description
alone. Preserve the original board's files and existing archive artifacts.

