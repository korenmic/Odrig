// A new upload keeps the browsing context it was prepared from.
import {fits} from "./upload.js";

export function present(space) {
  return space?.external?.present === true;
}

// The storage of the level a form was prepared at: the board's own for one of its folders,
// the card for one of the card's.
function levelStorage(form) {
  return form.level.storage === "internal" ? "internal" : "external";
}

// Whether the file goes into the folder of the level, which is of the storage chosen.
function intoLevel(form) {
  return form.level.path !== "" && form.storage === levelStorage(form);
}

export function capture(state, target) {
  const internalLevel = state.level.storage === "internal";
  return {target, level: {...state.level}, storage: internalLevel || !present(state.space) ? "internal" : "external", explicitInternal: internalLevel,
    generations: {internal: state.catalog?.internal?.generation ?? null, external: state.catalog?.external?.generation ?? null}};
}

export function synchronize(form, space) {
  const storage = form.explicitInternal || !present(space) ? "internal" : "external";
  const changed = storage !== form.storage;
  form.storage = storage;
  return changed;
}

export function select(form, storage, space) {
  if (storage === "external" && !present(space)) return;
  form.explicitInternal = storage === "internal";
  synchronize(form, space);
}

// The level a check of the destination reads with `uploadSnapshot`: the level the form was
// prepared at for the card, and for a folder of the board's own storage the file goes into;
// else the root.
export function snapshotLevel(form) {
  return form.storage === "external" || intoLevel(form) ? form.level : {path: "", id: null};
}

export function pathOf(form, name) {
  if (name.length > 32 || !/^[a-z0-9_-][a-z0-9._-]*\.(odrg|odrgx)$/.test(name)) throw new Error("Use a filename of at most 32 lowercase letters, digits, dots, - or _, ending in .odrg or .odrgx.");
  const path = intoLevel(form) ? `${form.level.path}/${name}` : name;
  if (path.length > 100) throw new Error("The destination path exceeds 100 characters; use a shorter filename.");
  return path;
}

export function label(form, name) {
  return `${form.storage === "external" ? "External" : "Internal"} /${intoLevel(form) ? form.level.path + "/" : ""}${name}`;
}

export function reason(form, space) {
  if (!present(space)) return `External storage is disconnected or not detected. Using Internal /${intoLevel(form) ? form.level.path + "/" : form.level.path ? "; the explored folder is on the card" : ""}.`;
  if (form.storage === "external" && space.external.read_only !== false) return "External storage is detected but read-only. It will not be redirected to Internal.";
  if (form.storage === "internal" && form.level.path && !intoLevel(form)) return "This upload goes to the root of Internal storage: the explored folder is on the card.";
  return "The destination stays here even if you browse elsewhere.";
}

export function validate(form, fresh, name, bytes, target) {
  if (target !== form.target) throw new Error("The target changed. Select the file again to prepare its destination.");
  const path = pathOf(form, name);
  const external = form.storage === "external";
  if (external && (!present(fresh.space) || fresh.space.external.read_only !== false)) throw new Error("External storage is absent or read-only. Check the displayed destination before retrying.");
  const current = fresh.catalog?.[form.storage];
  const generation = current?.generation ?? null;
  const captured = form.generations[form.storage];
  if (captured !== null && captured !== generation) throw new Error("The storage catalog changed. Select the file again to revalidate its destination.");
  if (external && (current?.state !== "ok" || current.writable !== true)) throw new Error("External storage needs a ready writable catalog before uploading.");
  if (form.level.id !== null && intoLevel(form) && !fresh.folderValid) throw new Error("The explored folder changed or disappeared. Select the destination again.");
  const rows = form.level.id === null || intoLevel(form) ? fresh.items : fresh.root;
  if (rows.some(item => item.file === path && (external ? item.external === true : item.external !== true))) throw new Error("A file already exists at this destination. Choose another filename; nothing was replaced.");
  const free = external ? fresh.space.external.free : fresh.space.free;
  if (typeof free === "number" && !fits(bytes, free)) return {path, external, noSpace: free};
  return {path, external};
}
