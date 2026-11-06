# Phone storage explorer and animation backups

## Summary

Let the operator manage animations already installed on the ESP32-S3 from the
phone: select files or folders, save their original animation bytes to the
phone for backup, create folders and playlist folders, and cut/paste or move
existing files and folders to an explicitly chosen Internal or External path.
Moving changes the actual stored path; changing playlist order is a separate
existing action. Bulk backup produces one ZIP of paths relative to a captured
source storage and explored base, with their provenance retained in a manifest.
Archive import and upload selection belong to seed73.

## Priority

`P2`.

## Product Context

The owner requested a phone file explorer for the installation's two storages,
including downloading existing animations for backup, creating new folders or
playlist folders, and moving existing files and folders. The phone must expose
actual source and destination paths instead of requiring a computer to arrange
the installed library.

The present app browses a combined root containing Internal show animations and
External root files, then one level of External folders at a time. `order move`
only changes playback order within that level. `read <id> <offset>` already
returns original bytes in small chunks for text/clock editing, but its current
availability restrictions and ID-only addressing are not a complete backup
contract. The app has no general create-folder or filesystem-move workflow.

Internal storage currently installs flat filenames referenced by `show.json`;
its catalog has no general folder index. External storage already has real
relative paths and an indexed folder tree, but an empty folder with no animation
below it has no catalog row. A picker, renamed list heading or order operation
alone cannot provide this feature. It needs compatible real Internal hierarchy,
durable empty-folder visibility and managed path mutations. Seed61's planned
Internal clock/message paths should be reused where available, without assuming
that its narrower path work already supplies a general explorer.

This seed is planning only. It does not introduce command spellings, implement
storage changes, build artifacts or operate a board. The shared protocol
extension is specified by its spec. The owner approved it in advance on
2026-11-06, so implementation follows the spec without a second review (see
"The Owner's Answers").

## Related Work And Boundaries

- Seeds35 and41 and `docs/catalog.md` / `docs/show.md`: catalog transactions,
  indexed folders, playlist order, stable identities and folder playback.
- Seeds48,58 and61: saved repeats, brightness and storage-specific clock/message
  identity, including the preference for matching paths in both storages.
- Seed63: byte-preserving uploads into an existing explored External folder,
  explicit storage/path capture and no in-flight fallback. Preserve that flow.
- Seed73: selecting a ZIP on the phone, extracting it and uploading selected
  animations. Do not duplicate archive-import UI, extraction or upload queues.
  A backup ZIP may later be selected there under its own validation; this seed
  does not promise automatic settings restoration or a new restore command.
- Seeds66 and67: the approved Clocks-only browsing boundary and stable recovery
  after transient lookups, disconnects or catalog changes. Preserve those
  requirements even where an older checkout still describes unrestricted
  browsing or root fallback. This explorer must not restore those old behaviors.

## Required Behavior

1. Extend the shared phone/Controller explorer with clear source storage and
   canonical full relative path for every file and folder. Offer single and
   batch selection of animations and folders, with a visible selection summary,
   Select all shown and Clear selection. Selecting a folder includes its whole
   permitted subtree, including hidden-by-filter descendants; preview that scope
   explicitly. Deduplicate overlapping parent/child selections. Ordinary filters
   never silently add unshown sibling rows to Select all shown. Keep tests,
   cycles, catalog files, mapping, firmware and unrelated filesystem files out of
   the editable animation namespace.

2. Provide Download for a selected animation and Download selected for a batch
   or subtree. Read the original `.odrg` / `.odrgx` bytes, including container
   content, without conversion, re-encoding, resizing or changing timing. A
   readable damaged animation may be backed up as its original bytes, with its
   fault noted; an unavailable size or missing/unreadable file is an explained
   failure, never an empty replacement. Export must not require writable source
   media or change a file's playback eligibility. Existing `read` may be reused
   where its guarantees suffice; any needed extension is shared protocol work.

3. A single-file download keeps its basename. Each bulk/folder backup captures
   one source storage and the explored base before reading, shows them clearly,
   and saves one ZIP on the phone. Animation entries are relative to that base:
   backing up the shown contents of `External /clocks` puts `face.odrg` and
   `message/text.odrgx` in the ZIP, without an added `External/` or second
   `clocks/` prefix. Selecting the `clocks` folder from the storage root instead
   retains its `clocks/` component. Preserve selected subtrees and empty selected
   folders. A combined-root selection from both storages must be split into
   explicit storage-scoped backups; never silently merge same paths or invent a
   restore mapping. Include a versioned non-animation JSON manifest identifying
   `sourceStorage`, `base`, original full paths, observed sizes, CRC-32 or
   equivalent verified content keys, catalog generation/identity and outcomes.
   Record applicable saved file/folder settings as descriptive metadata. Seed73
   lists this manifest as passed over and does not apply its settings; uploading
   the animation entries uses seed73's visible destination-base rules and limits.
   A backup larger than that importer's supported bounds is still a backup,
   never promised to be directly importable. This is not a flash image or
   guaranteed restoration feature. Keep entry names canonical, safe and contained
   within the captured base; no traversal or prefix-based double nesting.

4. Bind each read to the selected target, mounted-medium identity, canonical
   source and content observation; revalidate before and after the download so
   another controller's replacement, move or card swap cannot splice two files
   into one backup. Verify final byte count and content integrity. Save only a
   verified file as complete. Show file/byte progress, per-file failures and the
   actual saved/exported result. A partial batch is explicitly partial, with
   failed paths in the manifest and summary; never label it a complete backup.
   Stream/chunk reads and ZIP creation with stated bounds rather than loading
   an unbounded library or expanding animation frames in phone memory.

5. Offer New folder and New playlist folder in a selected writable storage and
   parent path. Both create real directories in that storage, persist across
   restart/remount, and remain listable while empty. A playlist folder follows
   the existing folder-as-playlist model: its own files then descendants in the
   established saved order, with the current eligibility and folder-window
   rules. There is no arbitrary virtual playlist type or second collection of
   references. New playlist folder makes that existing purpose explicit; New
   folder does not create a populated folder exempt from normal playlist rules.
   Creating either does not start playback or change the active playlist.

6. Supply Cut, Paste and Move to for selected existing files and folder subtrees.
   Cut records a pending source selection and removes nothing. The destination
   chooser names Internal storage or External storage and the complete parent
   path; preview every resulting full path before sending. A successful move
   changes actual stored paths and all authoritative references, not only list
   order, catalog labels or a phone-local alias. Support same-storage moves and
   transfers between the two storages. A folder keeps its descendant structure;
   reject moving it into itself or its descendants. An unchanged destination is
   a no-op. Do not add a general copy-library feature merely to implement moves.

7. Storage choice is explicit for creation and moves. At a combined root, require
   a visible concrete destination instead of inferring one from playback,
   filters or source ordering. Show External disabled with the reason while
   absent or read-only; unknown/stale capability is not permission to write.
   Missing Internal hierarchy support or old firmware gets an honest unsupported
   explanation. Never manufacture a matching Internal folder from an External
   path. Freeze target, medium and destination once an operation starts. The
   upload-specific preflight fallback of seed63 is not a move fallback: missing,
   removed, read-only or changed media must not redirect a mutation to another
   storage, even before bytes are sent, without a new explicit destination.

8. Preflight the complete selected scope incrementally: source and destination
   identity/revisions, folder existence, writable capability, item/ID limits,
   path depth/length/naming limits and capacity including staging, catalog and
   recovery overhead. Preview source/destination collisions and batch-internal
   collisions before writes. Default to no replacement. Offer skip, an explicit
   valid basename rename, or an explicit file replacement only with a stale
   content guard and a visible account of what will be replaced. Do not silently
   merge same-name folders, remove destination subtrees, apply replace-all to
   newly discovered collisions or generate invisible suffixed names. A fresh
   conflict invalidates the affected prepared action and needs review.

9. Use an atomic rename for a same-volume path move where the storage supports
   it, coordinated with durable show/catalog/index/settings publication and
   recovery. A copy is needed when rename is unavailable or storage differs:
   stage the copy, verify every original byte and the complete destination
   subtree, durably publish the destination, then remove the source under the
   same recorded job. Never destroy an original before the destination is
   verified and recoverably committed. Do not claim two volumes are atomically
   committed together: retain enough durable identity/progress information to
   recover when only one is available. If cleanup cannot finish, preserve the
   safe copies and report destination-installed/source-retained as incomplete,
   with reconciliation, rather than success or a destructive blind retry.

10. Keep animation bytes and content keys unchanged by moves. Preserve same-
    storage file/folder IDs where possible, unaffected IDs, descendant relative
    order, own Ignore choices, brightness overrides, repeats, availability and
    quarantine state. Retain global brightness, power, clock mode/preference,
    mapping and unrelated settings. Migrate path-keyed records for a moved
    subtree atomically with the authoritative path update; newly applied ancestor
    exclusions follow the destination tree and are visible in preview. Append
    moved top-level entries at the destination's end in their source order,
    leaving existing destination order unchanged; preserve the order inside a
    moved folder. Do not reset saved repeats/brightness merely because a path or
    storage changes, and do not leak them to an unrelated file later using the
    old path. A replacement retains the destination's valid ID/order position
    and the incoming file's saved settings, explicitly previewing that policy.

11. Specify identity migration where storage namespaces prevent retaining an ID.
    Return/reconcile an explicit old-to-new identity/path mapping and update
    references as one recoverable logical move. Internal show items, cycles,
    startup references and shared physical-file references must remain valid.
    If an existing cycle/start/shared-file reference cannot be represented at
    the destination without changing its meaning, refuse that move before any
    destructive step and explain the dependency; do not silently drop or rewrite
    the show. Numeric IDs alone, matching basenames or matching content keys are
    insufficient to retarget pending operations after a move or remount.

12. Show bounded job progress and distinguish pending, committed, cancelled,
    failed and uncertain completion. Stop/cancel ends unsent work and requests
    cancellation of the current transaction at a documented safe boundary.
    Before commit, abandon staged work without altering published originals;
    after commit, finish/reconcile required publication or cleanup rather than
    pretending it was rolled back. A batch reports completed, skipped, retained
    and unstarted paths separately; it is not silently described as all-or-none.
    Disconnect, target change, app restart, lost acknowledgement or card removal
    must reconcile against the original target and medium before retrying.
    Never replay a possibly completed mutation blindly or delete a different
    card's file after reinsertion. Downloads cancel without mutating the source.

13. Keep playback and normal controls responsive during bounded work. Avoid
    interrupting an unaffected active turn. Safely close/reopen a file if a path
    move requires it; preserve the active animation/playlist and its progress
    when representable, using a defined safe continuation otherwise. Revalidate
    clock/message eligibility when paths change, honoring seed61's matching-path
    storage preference and Ignore semantics. In Clocks only, explorer navigation
    and destination choices remain inside the resolved Clocks subtree as seeds66
    and67 require. A move, read error, missing subtree or changed ID never enables
    ordinary root browsing or playback as a recovery shortcut. Preserve Only and
    its dark/responsive no-eligible-clock state; do not treat storage management
    as authorization to switch modes or bypass the boundary.

14. Publish targeted catalog/index changes and update only affected listing levels,
    ancestor counts, revisions, source/destination breadcrumbs and preview aliases.
    Preserve unaffected content keys and preview caches. A move must not require
    catalog rebuild, a boot-wide animation-body scan, unrelated file reads or a
    full phone inventory refresh. Large folder metadata updates may need bounded
    streaming work; do not hide it in a blocking rebuild. Resolve a moved current
    browsing path from acknowledged identity/path mapping. Recheck a transient
    lookup through fresh parent evidence, retain the last complete rows while
    uncertain, and reject stale replies after Back/target changes. A changed
    reconnect identity invalidates the relevant cached inventory as seed67
    requires; local success is not a reason to reuse stale root data.

15. Keep all behavior in the one shared app and core, available in the emulator
    Controller and Android APK. Use the same approved protocol contract through
    HTTP, wired serial and each existing supported transport; no private HTTP
    filesystem endpoint or phone-only mutation rules. Reuse existing commands
    where sufficient. Specify capability negotiation and old-firmware refusals
    before exposing unsupported actions. Saving/exporting on Android and in a
    browser may use platform file adapters, but must report real user-accessible
    artifacts from the same application workflow.

## Technical Constraints

- Design the Internal real-folder model and compatible migration together with
  show names, catalog/index versions, path resolution and all content operations.
  Preserve every valid flat installed show and its identifiers. Reuse seed61's
  approved path model if implemented; do not weaken one filename validator and
  leave the rest flat. Do not format storage, change partitions or replace the
  whole installed show to create a folder.
- Contain operations in each storage's approved animation root. Validate decoded
  canonical paths once, including components, depth and bytes; reject traversal,
  absolute paths, ambiguous encodings, unsupported names, case-equivalent
  collisions where relevant and links/aliases that escape the root. Folder
  creation, download paths and ZIP entry names share that containment rule.
  Retain the current three-folder/100-byte external path bounds and existing
  basename rules unless the later specification explicitly proposes and approves
  a compatible shared extension. A backup archive's relative name does not grant
  its later upload permission to exceed the target's limits.
- Keep fixed-memory/incremental core protections, bounded phone work, one
  serialized managed mutation owner and durable catalog/settings recovery. An
  ordinary path move does not revalidate unchanged animation bodies unnecessarily;
  cross-storage copy verification does read the copied bytes.
- Preserve the approved core/Python catalog-writer parity where the format or
  transaction model changes. No independent converter, renderer, firmware
  flashing workflow, hardware/power change or cloud backup service is required.
- During later specification/implementation, record routine decisions in the
  append-only drift history and approved contract/decision changes in the proper
  documents. Creation of this seed changes only its two planning files. S2S,
  task queues, implementation, test runs, builds and delivery are separate work.

## Open Questions

None. The one question that needed the owner, the approval of the shared protocol
extension, is answered below.

## The Owner's Answers

On 2026-11-06 the owner was asked how to approve the new board commands this seed
needs: folder creation and listing, guarded path moves within and between the
storages, job and reconciliation operations with progress, cancel and recovery,
and a readback extension where the existing `read` of 600 bytes a request is too
slow for backups. Of four choices, review of the exact forms before
implementation, approval at once, the card only, or no new command, the owner
chose "Approve fully now": the specification designs them, and implementation
goes ahead without a second review by the owner. The specification still states
each command's exact form, limits, replies and parity on every transport; it
records them in `docs/commands.md` and the change log of `docs/decisions.md`
when they are built, citing this answer.

No other product question is left open. The conservative defaults above resolve
bulk ZIP layout, real folder/playlist semantics, conflict handling, move order,
settings migration and partial-job reporting without inventing a virtual playlist
or a destructive automatic replacement policy. Real phone save/share behavior
and physical media/playback acceptance remain owner checks after implementation.

## Definition Of Done

1. A requirements/design/tasks specification states the compatible Internal
   hierarchy, durable empty-folder/catalog representation, identity/settings
   migration, bounded jobs and cross-storage recovery model. Its concrete new
   command contract stands approved by the owner's answer of 2026-11-06, and the
   specification records its exact forms, limits and replies.
2. The shared Controller/APK can select installed animations/subtrees, save
   byte-identical single files or a verified source/base-relative backup ZIP,
   create real folder/playlist folders, and move actual files/folders within and
   between writable storages with the previewed paths and metadata retained.
3. Later discovered core/catalog/app/emulator/command suites verify flat-show
   migration, empty folders, nested/batch moves, cross-storage copies, byte/key
   identity, reference refusal/mapping, order/settings, playback and Clocks-only
   boundaries. Fault injection covers stale selections, concurrent controllers,
   conflicts/replacements, full storage, read-only/missing/swapped media,
   cancellation, lost replies and interruption at each commit/cleanup boundary.
4. Measured work verifies no ordinary move rebuilds the catalogs, scans unrelated
   animation bodies or refreshes the whole phone inventory. Backup tests cover
   readable damaged files, changing sources, integrity failures, partial ZIPs,
   bounded work and actually saved artifacts, without changing source bytes.
5. Portable checks and packaging run only during the later authorized delivery.
   Report actual software/AVD verification separately from the owner's phone
   download, Internal/External media and LED acceptance. This planning task is
   complete when this seed and its remaining state are recorded, with no claim
   that the explorer, protocol or backups already exist.
