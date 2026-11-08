// A new upload keeps the browsing context it was prepared from.
import {Refusal} from "./commands.js";
import * as messages from "./messages.js";
import {Failure} from "./target.js";
import {fits} from "./upload.js";

export const ONLY_REASON = "Clocks only: choose a writable external folder inside Clocks, or leave this mode in Settings.";

// The words of an upload that did not end with success: of a refusal or a failure of the way
// that ended a file of `size` bytes.
export function refusalWords(error, external, size, state, only = false) {
  if (error instanceof Refusal && error.code === "no-space" && external) {
    const card = state.space === null ? null : state.space.external;
    return messages.ofNoSpace(size, card == null || card.free === null ? null : card.free, "the card");
  }
  if (error instanceof Refusal && error.code === "no-space") return messages.ofNoSpace(size, state.space === null ? null : state.space.free);
  if (error instanceof Refusal && !external && ["unsupported", "stale"].includes(error.code)) {
    return "The chosen id was taken, or the firmware cannot confirm a safe new upload. No file bytes were sent. Select the file again or update the firmware.";
  }
  if (error instanceof Refusal && external && ["bad-argument", "unknown-command", "no-upload", "stale"].includes(error.code)) {
    return "The destination changed, already exists, or the firmware lacks safe folder uploads. Check the folder and filename, or update the firmware. Nothing was acknowledged as installed.";
  }
  if (error instanceof Refusal && error.code === "read-only" && only) return ONLY_REASON;
  if (error instanceof Refusal) return messages.ofRefusal(error, state.status === null ? null : state.status.error);
  if (error instanceof Failure) return `${messages.ofFailure(error)} The upload was not acknowledged as installed; check the destination before retrying.`;
  return error.message;
}

// Whether a `space` reply said a card is present.
export function present(space) {
  return space?.external?.present === true;
}

// Whether a `space` reply came and named no present card: one that says the card is
// absent, or one of an older target that names no external storage at all. Without a
// reply neither this nor `present` holds.
export function absent(space) {
  return space != null && !present(space);
}

export function capture(state, target, only = state.status?.clockMode === "only") {
  return {target, level: {...state.level}, only, storage: only || present(state.space) ? "external" : "internal", explicitInternal: false,
    generations: {internal: state.catalog?.internal?.generation ?? null, external: state.catalog?.external?.generation ?? null}};
}

// Moves the form to the storage a reply allows: Internal when it was chosen, or when the
// reply names no card; External when the reply says a card is present. Without a reply
// the form stays where it is. Gives whether the storage changed.
export function synchronize(form, space, only = form.only) {
  form.only = only;
  const storage = only ? "external" : form.explicitInternal ? "internal" : present(space) ? "external" : absent(space) ? "internal" : form.storage;
  const changed = storage !== form.storage;
  form.storage = storage;
  return changed;
}

export function select(form, storage, space, only = form.only) {
  form.only = only;
  if (only && storage !== "external") return;
  if (storage === "external" && !present(space)) return;
  form.explicitInternal = storage === "internal";
  synchronize(form, space, only);
}

export function blocked(form, space, only = form.only) {
  if (!only) return null;
  const path = form.level.path;
  return form.storage !== "external" || form.level.id === null ||
    !(path === "clocks" || path.startsWith("clocks/")) || !present(space) ||
    space.external.read_only !== false ? ONLY_REASON : null;
}

export function pathOf(form, name) {
  if (name.length > 32 || !/^[a-z0-9_-][a-z0-9._-]*\.(odrg|odrgx)$/.test(name)) throw new Error("Use a filename of at most 32 lowercase letters, digits, dots, - or _, ending in .odrg or .odrgx.");
  const path = form.storage === "external" && form.level.path ? `${form.level.path}/${name}` : name;
  if (path.length > 100) throw new Error("The destination path exceeds 100 characters; use a shorter filename.");
  return path;
}

export function label(form, name) {
  return `${form.storage === "external" ? "External" : "Internal"} /${form.storage === "external" && form.level.path ? form.level.path + "/" : ""}${name}`;
}

export function reason(form, space) {
  const boundary = blocked(form, space);
  if (boundary !== null) return boundary;
  if (!present(space) && !absent(space)) return "Storage not known yet: the installation has not answered.";
  if (absent(space)) return `External storage is disconnected or not detected. Using Internal /${form.level.path ? "; internal storage has no matching subfolders" : ""}.`;
  if (form.storage === "external" && space.external.read_only !== false) return "External storage is detected but read-only. It will not be redirected to Internal.";
  if (form.storage === "internal" && form.level.path) return "Internal storage has a flat root. This upload uses Internal / instead of the explored SD folder.";
  return "The destination stays here even if you browse elsewhere.";
}

// A file that may replace the one of its name skips the check that nothing is there.
export function validate(form, fresh, name, bytes, target, {replace = false, only = form.only} = {}) {
  if (target !== form.target) throw new Error("The target changed. Select the file again to prepare its destination.");
  const boundary = blocked(form, fresh.space, only);
  if (boundary !== null) throw new Error(boundary);
  const path = pathOf(form, name);
  const external = form.storage === "external";
  if (external && (!present(fresh.space) || fresh.space.external.read_only !== false)) throw new Error("External storage is absent or read-only. Check the displayed destination before retrying.");
  const current = fresh.catalog?.[form.storage];
  const generation = current?.generation ?? null;
  const captured = form.generations[form.storage];
  if (captured !== null && captured !== generation) throw new Error("The storage catalog changed. Select the file again to revalidate its destination.");
  if (external && (current?.state !== "ok" || current.writable !== true)) throw new Error("External storage needs a ready writable catalog before uploading.");
  if (external && form.level.id !== null && !fresh.folderValid) throw new Error("The explored folder changed or disappeared. Select the destination again.");
  const rows = external ? fresh.items : fresh.root;
  if (!replace && rows.some(item => item.file === path && (external ? item.external === true : item.external !== true))) throw new Error("A file already exists at this destination. Choose another filename; nothing was replaced.");
  const free = external ? fresh.space.external.free : fresh.space.free;
  if (typeof free === "number" && !fits(bytes, free)) return {path, external, noSpace: free};
  return {path, external};
}
