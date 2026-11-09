// Downloads and backups of installed animations, made by the app with the board's commands:
// one file saved under its own name, or one zip of a selection of one storage, its entries
// named from the level shown, with the manifest `odrig-backup.json` written last. One file
// is in flight at a time. It is read whole, checked against its row before and after the
// read, in the part of its level's list that holds the row, and against the key its
// storage's catalog gives it, and only then written, so that a file that fails leaves no
// entry. Nothing is changed on the target.

import * as commands from "./commands.js";
import {crc32} from "./crc32.js";
import {Failure} from "./target.js";
import {ZipWriter, fits} from "./zip-writer.js";

export const MANIFEST = "odrig-backup.json";
export const FORMAT = "odrig-backup";
export const VERSION = 1;
// The bytes a file is handed to the sink in.
const SLICE = 64 * 1024;
// What the manifest is reckoned to take before it is written: a part of its own and one
// for each file and folder.
const MANIFEST_BASE = 4096;
const MANIFEST_EACH = 512;

export function storageOf(row) {
  return row.external === true ? "external" : "internal";
}

// The name of a file or a folder without the folders it is in.
export function baseOf(path) {
  return path.slice(path.lastIndexOf("/") + 1);
}

// How a storage and a path are written: `Internal /name` or `External /folder/name`.
export function label(storage, path) {
  return `${storage === "external" ? "External" : "Internal"} /${path}`;
}

// The name of an entry for a path under the base, the level shown, "" for the root; why it
// cannot be one is thrown.
export function entryOf(path, base) {
  if (base !== "" && !path.startsWith(`${base}/`)) throw new RangeError(`${path} is not under ${base}.`);
  const name = base === "" ? path : path.slice(base.length + 1);
  if (name === "" || name.startsWith("/") || name.includes("\\") || name.split("/").some((part) => part === "" || part === "." || part === "..")) {
    throw new RangeError(`${path} cannot be named inside the archive.`);
  }
  return name;
}

// The name of a backup's file: its storage, its base and the moment it was begun.
export function archiveName(storage, base, when) {
  const two = (value) => String(value).padStart(2, "0");
  const stamp = `${when.getFullYear()}${two(when.getMonth() + 1)}${two(when.getDate())}-${two(when.getHours())}${two(when.getMinutes())}${two(when.getSeconds())}`;
  const where = base === "" ? "root" : base.replace(/[^A-Za-z0-9._-]+/g, "-").replace(/^-+|-+$/g, "") || "folder";
  return `odrig-${storage}-${where}-${stamp}.zip`;
}

// The bytes as pieces of at most SLICE, as they are handed on.
function* slices(bytes) {
  for (let at = 0; at < bytes.length; at += SLICE) yield bytes.subarray(at, at + SLICE);
}

// The operator's Stop, which ends the file under way.
class Stopped extends Error {}

// Another target was chosen: nothing of the run is saved.
class Changed extends Error {}

// Throws when another target was chosen since the run began.
function sameTarget(context) {
  if (context.changed()) throw new Changed("Another target was chosen while it was read: nothing was saved.");
}

// How many times in all a request is sent while its reply is lost.
const SENDS = 3;

// Waits for a request the client sends in its turn. One withdrawn while the app was hidden is
// asked again once it is shown, for the same target; one whose reply did not come is sent
// again, up to SENDS times in all, as every request of a run only reads. A refusal is the
// target's answer and is not asked again, nor anything after Stop or a change of target.
async function again(context, request) {
  for (let sent = 0; ;) {
    try {
      return await request();
    } catch (error) {
      if (context.stopped() || context.changed()) throw error;
      if (error instanceof context.client.Withdrawn) {
        await context.visible();
      } else if (!(error instanceof Failure && error.kind === "no-answer") || ++sent >= SENDS) {
        throw error;
      }
    }
  }
}

// Sends a command line of the job in its turn, in the background.
function asked(context, carry) {
  return again(context, () => context.client.background("backup", carry));
}

// Keeps the position of each row of a part of a level's list that began at `from`.
function remember(context, level, from, items) {
  let places = context.places.get(level);
  if (places === undefined) {
    places = new Map();
    context.places.set(level, places);
  }
  items.forEach((item, at) => places.set(item.id, from + at));
}

// Every row of a level, all its parts: the root's for null, else a folder's of the card.
async function levelRows(context, level) {
  const rows = [];
  let from = 0;
  do {
    const start = from;
    const reply = await asked(context, () => commands.list(start, level));
    remember(context, level, start, reply.items);
    rows.push(...reply.items);
    from = reply.next;
  } while (from !== null);
  return rows;
}

// The rows of a file's level around its row, read anew: one part of the list, from the
// position the row was last seen at, or the whole level when it is not there.
async function rowsAround(context, file) {
  const at = context.places.get(file.level)?.get(file.id);
  if (at !== undefined) {
    const reply = await asked(context, () => commands.list(at, file.level));
    remember(context, file.level, at, reply.items);
    if (reply.items.some((one) => one.id === file.id)) return reply.items;
  }
  return levelRows(context, file.level);
}

// The file of a level's rows with this id, when it is still the same: its path, its storage
// and its size; else why it is not.
function sameFile(rows, file) {
  const row = rows.find((one) => one.id === file.id && typeof one.file === "string");
  if (row === undefined) return {problem: "It is no longer listed."};
  if (row.file !== file.path || storageOf(row) !== file.storage) return {problem: `Its id now names ${label(storageOf(row), row.file)}.`};
  if (row.bytes !== file.size) return {problem: "Its size changed."};
  if (typeof row.fault === "string") return {problem: `It is unavailable: ${row.fault}.`, fault: row.fault};
  return {row};
}

// The rows around a file for its check before its read, read anew, unless the check that
// ended the file before holds its row: then those rows serve, as nothing came between.
async function freshRows(context, file) {
  const last = context.lastRows;
  context.lastRows = null;
  if (last !== null && last.level === file.level && last.rows.some((one) => one.id === file.id)) return last.rows;
  return rowsAround(context, file);
}

// Reads one file whole, piece by piece, and checks it. `progress(read, size)` is told after
// each piece. Gives the bytes, or throws why they are not the file's.
async function readChecked(context, file, progress) {
  const before = sameFile(await freshRows(context, file), file);
  if (before.problem !== undefined) {
    const error = new Error(before.problem);
    error.fault = before.fault ?? null;
    throw error;
  }
  // The key the catalog gives the file now, which serves when the app has forgotten the keys
  // by the end of the read, as it does when the target answers again after a silence.
  const known = context.client.keyOf(before.row);
  const parts = [];
  let read = 0;
  for (;;) {
    sameTarget(context);
    if (context.stopped()) throw new Stopped("Stopped while it was read.");
    const piece = await again(context, () => context.client.readPiece(file.id, read));
    if (piece.bytes !== file.size) throw new Error("It changed while it was read: its size is another.");
    parts.push(piece.data);
    read += piece.data.length;
    progress(read, file.size);
    if (piece.data.length === 0 || read >= piece.bytes) break;
  }
  if (read !== file.size) throw new Error(`Only ${read} of its ${file.size} bytes could be read.`);
  const bytes = new Uint8Array(read);
  let at = 0;
  for (const part of parts) {
    bytes.set(part, at);
    at += part.length;
  }
  const crc = crc32(bytes);
  const key = context.client.keyOf(before.row) ?? known;
  if (key !== null && key !== `${crc}-${read}`) throw new Error("Its bytes are not the ones its storage's catalog names.");
  const rows = await rowsAround(context, file);
  const after = sameFile(rows, file);
  if (after.problem !== undefined) throw new Error(`It changed while it was read. ${after.problem}`);
  context.lastRows = {level: file.level, rows};
  return {bytes, crc};
}

// What a run is told: `stopped()`, whether the operator pressed Stop; `changed()`, whether
// another target was chosen since it began; and `visible()`, which waits until the app is
// shown.
function contextOf(options) {
  return {
    client: options.client,
    stopped: options.stopped ?? (() => false),
    changed: options.changed ?? (() => false),
    visible: options.visible ?? (() => Promise.resolve()),
    lastRows: null,
    places: new Map(),
  };
}

// The file of a row, as the job checks it: its id, its path, its storage, its size and the
// level whose rows hold it, the root for null.
export function fileOf(row, level) {
  return {id: row.id, path: row.file, storage: storageOf(row), size: typeof row.bytes === "number" ? row.bytes : null, level, row};
}

// Downloads one animation: reads it, checks it and hands it to the sink that `open(name)`
// gives for its base name. Gives what the sink's `finish()` gives, with the CRC-32.
// `report({read, size})` is told how far the read is.
export async function download(options) {
  const context = contextOf(options);
  const file = fileOf(options.row, options.level);
  if (file.size === null) throw new Error("Its size is not known yet; try again once the list shows it.");
  if (typeof options.row.fault === "string") throw new Error(`It is unavailable: ${options.row.fault}.`);
  const {bytes, crc} = await readChecked(context, file, (read, size) => options.report?.({read, size}));
  sameTarget(context);
  const sink = await options.open(baseOf(file.path));
  try {
    for (const piece of slices(bytes)) await sink.write(piece);
    sameTarget(context);
  } catch (error) {
    sink.abandon();
    throw error;
  }
  return {...(await sink.finish()), crc, size: bytes.length};
}

// The files and the folders of a selection of one level, the folders' subtrees walked, each
// file with its entry. `files` are rows of the level shown, `folders` its folder rows of the
// card; `level` is the id of the level shown, null for the root, and `base` its path.
export async function scope(options) {
  return walk(contextOf(options), options);
}

// The scope of a selection, its folders listed in the run's context, which keeps the
// positions of their rows for the checks of their files.
async function walk(context, options) {
  const files = [];
  const folders = [];
  const seen = new Set();
  for (const row of options.files) {
    if (seen.has(row.id)) continue;
    seen.add(row.id);
    files.push({...fileOf(row, options.level), entry: entryOf(row.file, options.base)});
  }
  const pending = options.folders.map((row) => ({row}));
  while (pending.length > 0) {
    const {row} = pending.shift();
    if (seen.has(row.id)) continue;
    seen.add(row.id);
    sameTarget(context);
    if (context.stopped()) throw new Stopped("Stopped while the selection was read.");
    const rows = await levelRows(context, row.id);
    const own = rows.filter((one) => typeof one.file === "string");
    const below = rows.filter((one) => typeof one.playlist === "string");
    folders.push({id: row.id, path: row.playlist, entry: `${entryOf(row.playlist, options.base)}/`, ignored: row.ignored ?? null,
      inheritedIgnored: row.inheritedIgnored ?? false, empty: own.length === 0 && below.length === 0});
    for (const one of own) {
      if (seen.has(one.id)) continue;
      seen.add(one.id);
      files.push({...fileOf(one, row.id), entry: entryOf(one.file, options.base)});
    }
    pending.unshift(...below.map((one) => ({row: one})));
  }
  return {files, folders};
}

// The settings of a file in the manifest: its own and inherited ignore, and what `saved`
// gave, its brightness, its repeat and `start`, with `savedUnknown` null; or, when `saved`
// did not answer, those three null and `savedUnknown` saying why: the code of its refusal,
// or `not-asked` for a file that was not read.
function settingsOf(row, saved) {
  const known = saved !== null && saved.unknown === undefined;
  return {ignored: typeof row.ignored === "boolean" ? row.ignored : null, inheritedIgnored: row.inheritedIgnored === true,
    brightness: known ? saved.brightness : null, repeat: known ? saved.repeat : null, start: known ? saved.start : null,
    savedUnknown: known ? null : saved?.unknown ?? "not-asked"};
}

// How many times `saved` is asked while the board answers `busy`, which it does until it has
// read what it keeps, and how long the app waits between two.
const SAVED_TRIES = 5;
const SAVED_WAIT_MS = 500;

// What the board keeps for an animation, or `{unknown}` with the code of the refusal from a
// target that does not say.
async function savedOf(context, id) {
  for (let tries = 1; ; tries += 1) {
    try {
      return await asked(context, () => commands.saved(id));
    } catch (error) {
      if (!(error instanceof commands.Refusal)) throw error;
      if (error.code !== "busy" || tries >= SAVED_TRIES || context.stopped()) return {unknown: error.code};
      await new Promise((resolve) => setTimeout(resolve, SAVED_WAIT_MS));
    }
  }
}

// The generation of a storage's catalog, or null while it has none that is `ok`, or from a
// target without catalogs.
async function generationOf(context, storage) {
  try {
    const reply = await asked(context, () => commands.catalog());
    return reply[storage].state === "ok" ? reply[storage].generation : null;
  } catch (error) {
    if (error instanceof commands.Refusal) return null;
    throw error;
  }
}

// Backs up a selection of one storage into one zip. `options`: `client`; `storage`; `base`,
// the path of the level shown; `level`, its id; `files` and `folders`, the selected rows of
// that level; `address`, the target's; `when`; `open(name)`, which gives the sink of the
// archive's file; `report(progress)`; and `stopped()`, `changed()` and `visible()`, as a run
// is told them. After Stop the zip is saved with the files read whole before it, as a partial
// backup; after a change of target nothing is saved. Gives `{saved, name, bytes, manifest}`.
export async function backup(options) {
  const context = contextOf(options);
  const when = options.when ?? new Date();
  const report = options.report ?? (() => {});
  report({phase: "scope"});
  const {files, folders} = await walk(context, options);
  const empty = folders.filter((folder) => folder.empty);
  const planned = [...empty.map((folder) => ({name: folder.entry, size: null})), ...files.map((file) => ({name: file.entry, size: file.size ?? 0})),
    {name: MANIFEST, size: MANIFEST_BASE + MANIFEST_EACH * (files.length + folders.length)}];
  if (files.length + empty.length === 0) throw new RangeError("The selection holds no animation and no empty folder.");
  if (!fits(planned)) throw new RangeError("The backup would need zip64, which the app does not write: it holds 4 GiB or more, or 65,535 entries or more. Select less.");
  const generation = await generationOf(context, options.storage);
  const name = archiveName(options.storage, options.base, when);
  const sink = await options.open(name);
  const writer = new ZipWriter(sink, when);
  const outcomes = [];
  try {
    for (const folder of empty) await writer.directory(folder.entry);
    let stopped = false;
    for (const [at, file] of files.entries()) {
      sameTarget(context);
      const outcome = {path: file.path, entry: file.entry, id: file.id, ...(file.storage === "internal" ? {stored: file.row.stored ?? file.path} : {}),
        size: file.size, crc32: null, settings: settingsOf(file.row, null), fault: file.row.fault ?? null, outcome: "not-started", reason: null};
      outcomes.push(outcome);
      if (stopped || context.stopped()) {
        stopped = true;
        continue;
      }
      report({phase: "file", at, count: files.length, path: file.path, read: 0, size: file.size});
      let read;
      try {
        if (file.size === null) throw new Error("Its size is not known yet.");
        if (typeof file.row.fault === "string") throw new Error(`It is unavailable: ${file.row.fault}.`);
        outcome.settings = settingsOf(file.row, await savedOf(context, file.id));
        read = await readChecked(context, file, (done, size) => report({phase: "file", at, count: files.length, path: file.path, read: done, size}));
      } catch (error) {
        // Another target saves nothing; after Stop the file under way is stopped, whatever
        // its last request met.
        if (error instanceof Changed || context.changed()) throw error;
        if (error instanceof Stopped || context.stopped()) {
          Object.assign(outcome, {outcome: "stopped", reason: error instanceof Stopped ? error.message : `Stopped while it was read: ${error instanceof commands.Refusal ? error.code : error.message}.`});
          stopped = true;
        } else {
          Object.assign(outcome, {outcome: "failed", reason: error instanceof commands.Refusal ? error.code : error.message, fault: error.fault ?? outcome.fault});
        }
        continue;
      }
      sameTarget(context);
      // A sink that cannot be written ends the run, as the zip's limits do.
      await writer.file(file.entry, slices(read.bytes));
      Object.assign(outcome, {crc32: read.crc, outcome: "saved"});
    }
    sameTarget(context);
    const manifest = {format: FORMAT, version: VERSION, sourceStorage: options.storage, base: options.base, target: options.address ?? null,
      made: when.toISOString(), catalog: generation === null ? null : {generation}, partial: outcomes.some((outcome) => outcome.outcome !== "saved"),
      files: outcomes, folders: folders.map(({path, entry, ignored, inheritedIgnored}) => ({path, entry, ignored, inheritedIgnored}))};
    await writer.file(MANIFEST, [new TextEncoder().encode(`${JSON.stringify(manifest, null, 2)}\n`)]);
    await writer.finish();
    const saved = await sink.finish();
    return {...saved, name: saved.name ?? name, manifest};
  } catch (error) {
    sink.abandon();
    throw error;
  }
}
