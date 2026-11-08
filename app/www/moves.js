// Moves of animation files between and within the two storages, made by the app with the
// board's commands, one file at a time. Each file is a job kept on the phone until it is
// done: its bytes read and checked, uploaded to the destination where nothing has its name,
// its saved settings given to the new file and taken from the old one, and only then the
// old file removed, after its id is found again with its path and size.

import * as commands from "./commands.js";
import {crc32} from "./crc32.js";
import {freeId, uploading} from "./upload.js";

const KEY = "odrig.moves";
const INTERNAL_NAME = /^[a-z0-9_-][a-z0-9._-]*\.(odrg|odrgx)$/;
const EXTERNAL_PART = /^[ -~]+$/;
const LONGEST_PATH = 100;

// The name of a file without its folders.
export function baseOf(path) {
  return path.slice(path.lastIndexOf("/") + 1);
}

// The folder of a file's path, "" for the root.
export function folderOf(path) {
  const at = path.lastIndexOf("/");
  return at < 0 ? "" : path.slice(0, at);
}

function storageOf(row) {
  return row.external === true ? "external" : "internal";
}

// How a destination is written: `Internal /name` or `External /folder/name`.
export function label(storage, path) {
  return `${storage === "external" ? "External" : "Internal"} /${path}`;
}

// Why a name cannot be a file's name in a storage, or null when it can.
export function nameProblem(storage, folder, name) {
  if (storage === "internal") {
    return name.length <= 32 && INTERNAL_NAME.test(name) ? null : "Internal storage takes names of at most 32 lowercase letters, digits, dots, - or _, ending in .odrg or .odrgx.";
  }
  const path = folder ? `${folder}/${name}` : name;
  if (!EXTERNAL_PART.test(name) || /[\\/:*?"<>|]/.test(name) || /^[ .]|[ .]$/.test(name.replace(/\.odrgx?$/i, "x")) || !/\.odrgx?$/i.test(name) || /^[0-9]+$/.test(name)) {
    return "Use printable letters without \\ / : * ? \" < > |, not beginning or ending with a space or a dot, ending in .odrg or .odrgx.";
  }
  return path.length <= LONGEST_PATH ? null : "The destination path exceeds 100 characters; use a shorter name.";
}

function sameName(storage, a, b) {
  return storage === "external" ? a.toLowerCase() === b.toLowerCase() : a === b;
}

// The plan of a move: for each selected file its destination path, or why it is skipped.
// `destination` is `{storage, folder}`, `rows` the files the destination level has now,
// `names` the names the operator gave in the preview, by source id, and `blocked` the
// reasons known before, by source id.
export function plan(files, destination, rows, names = new Map(), blocked = new Map()) {
  const taken = rows.filter((row) => typeof row.file === "string" && storageOf(row) === destination.storage).map((row) => baseOf(row.file));
  const planned = [];
  return files.map((source) => {
    const name = names.get(source.id) ?? baseOf(source.file);
    const path = destination.storage === "external" && destination.folder ? `${destination.folder}/${name}` : name;
    const entry = {source, storage: destination.storage, folder: destination.storage === "external" ? destination.folder : "", name, path, skip: null};
    if (blocked.has(source.id)) entry.skip = blocked.get(source.id);
    else if (typeof source.bytes !== "number") entry.skip = "Its size is not known yet; try again once the list shows it.";
    else if (storageOf(source) === destination.storage && source.file === path) entry.skip = "It is there already.";
    else if (nameProblem(destination.storage, entry.folder, name) !== null) entry.skip = nameProblem(destination.storage, entry.folder, name);
    else if (taken.some((other) => sameName(destination.storage, other, name))) entry.skip = "The destination has a file of this name. Give it another name to move it.";
    else if (planned.some((other) => sameName(destination.storage, other, name))) entry.skip = "Another selected file takes this name. Give it another name to move it.";
    if (entry.skip === null) planned.push(name);
    return entry;
  });
}

// The journal of the moves under way, by target address, kept on the phone.
function journal() {
  try {
    const kept = JSON.parse(localStorage.getItem(KEY) || "{}");
    return kept !== null && typeof kept === "object" ? kept : {};
  } catch (_) {
    return {};
  }
}

function keep(address, jobs) {
  const all = journal();
  if (jobs.length === 0) delete all[address];
  else all[address] = jobs;
  try {
    localStorage.setItem(KEY, JSON.stringify(all));
  } catch (_) {
    // A phone that keeps nothing still moves; it cannot finish an interrupted move later.
  }
}

export function pending(address) {
  const jobs = journal()[address];
  return Array.isArray(jobs) ? jobs : [];
}

function record(address, job) {
  const jobs = pending(address).filter((other) => other.source.id !== job.source.id || other.source.storage !== job.source.storage);
  keep(address, [...jobs, job]);
}

function forget(address, job) {
  keep(address, pending(address).filter((other) => other.source.id !== job.source.id || other.source.storage !== job.source.storage));
}

// The files of one level of a storage, all its pages.
async function levelRows(operation, folderId) {
  const rows = [];
  let from = 0;
  do {
    const reply = await operation("move", () => commands.list(from, folderId));
    rows.push(...reply.items);
    from = reply.next;
  } while (from !== null);
  return rows;
}

// The name the board keeps an internal file under: its stored name in a folder, else its file.
function keptName(row) {
  return typeof row.stored === "string" ? row.stored : row.file;
}

// Why an internal file cannot move, from the root's rows with its cycles and the rows of its
// own level, or null: a cycle lists it, or another item of the show names its file.
export function heldBy(rows, file) {
  if (file.external === true) return null;
  if (rows.some((row) => Array.isArray(row.members) && row.members.includes(file.id))) return "A cycle of the show lists it; it stays where the cycle names it.";
  if (rows.some((row) => row.id !== file.id && row.external !== true && typeof row.file === "string" && keptName(row) === keptName(file))) return "Another item of the show names the same file; it stays.";
  return null;
}

// The folder of a storage a file of a level is in, by its path, "" for the root: a file of
// the board's own storage is in a folder only when the list gives its stored name.
export function sourceFolder(file) {
  if (file.external === true || typeof file.stored === "string") return folderOf(file.file);
  return "";
}

// The id of the folder of a storage, "external" the card's, with this path, null for the
// root "", or undefined when there is none.
export async function folderId(operation, path, storage = "external") {
  if (!path) return null;
  let rows = await levelRows(operation, null);
  let id;
  let walked = "";
  for (const part of path.split("/")) {
    walked = walked ? `${walked}/${part}` : part;
    const folder = rows.find((row) => typeof row.playlist === "string" && row.playlist === walked && storageOf(row) === storage);
    if (folder === undefined) return undefined;
    id = folder.id;
    if (walked !== path) rows = await levelRows(operation, id);
  }
  return id;
}

// The rows a file's move is judged against: the root's, with the show's cycles, and those
// of the folder the file is in.
export async function sourceRows(operation, file) {
  const rows = await levelRows(operation, null);
  const folder = sourceFolder(file);
  if (!folder) return rows;
  const level = await folderId(operation, folder, storageOf(file));
  return level === undefined ? rows : [...rows, ...await levelRows(operation, level)];
}

// The file of a level that has this path and this storage, or undefined.
function fileAt(rows, storage, path) {
  return rows.find((row) => typeof row.file === "string" && storageOf(row) === storage && row.file === path);
}

// Sends an upload job through the client and waits for its end. Gives the new id.
function upload(client, made, report) {
  return new Promise((resolve, reject) => {
    const job = uploading(made, {
      report,
      end(how) {
        if (how.done) resolve(how.id);
        else reject(how.error ?? new Error("The move was stopped before its file was installed."));
      },
      wake: client.wake,
    });
    client.upload(job);
  });
}

// Moves one planned file. `context` has the client, the address of the target, a function
// `stillTarget()`, `report(text)` and `stopped()`. Gives the new id.
export async function move(entry, context) {
  const {client, address} = context;
  const operation = client.operation;
  const source = {id: entry.source.id, storage: storageOf(entry.source), path: entry.source.file, folder: sourceFolder(entry.source), bytes: entry.source.bytes,
    ignored: entry.source.ignored === true};
  const job = {source, destination: {storage: entry.storage, folder: entry.folder, name: entry.name, path: entry.path}, stage: "read"};
  const held = heldBy(await sourceRows(operation, entry.source), entry.source);
  if (held !== null) throw new Error(held);
  const saved = await operation("move", () => commands.saved(source.id));
  if (saved.start) throw new Error("It is the show's start animation; it stays where the show names it.");
  job.settings = {ignored: source.ignored, brightness: saved.brightness, repeat: saved.repeat};
  context.report(`Reading ${label(source.storage, source.path)}`);
  const bytes = await client.readFile(source.id);
  if (bytes.length !== source.bytes) throw new Error("The file read back is not of its listed size. Nothing was changed.");
  job.source.crc = crc32(bytes);
  const key = client.keyOf(entry.source);
  if (key !== null && key !== `${job.source.crc}-${bytes.length}`) throw new Error("The file read back is not the one the catalog names. Nothing was changed.");
  if (context.stopped()) throw new Error("Stopped before its file was sent.");
  job.stage = "sending";
  record(address, job);
  let id = null;
  if (entry.storage === "internal") {
    // Free among the ids of the root and of every folder of the board's own storage.
    const taken = [];
    const pending = [null];
    while (pending.length > 0) {
      const rows = await levelRows(operation, pending.shift());
      for (const row of rows) {
        taken.push(row.id);
        if (typeof row.playlist === "string" && row.external === false) pending.push(row.id);
      }
    }
    id = freeId(new Set(taken));
    if (id === null) throw new Error("Internal storage has no free animation id.");
  }
  const newId = await upload(client, {id, file: entry.path, bytes, external: entry.storage === "external", create: true, expect: entry.storage === "external" ? "00000000" : null},
    (part) => context.report(`Sending ${label(entry.storage, entry.path)}: ${Math.floor(part * 100)}%`));
  job.newId = entry.storage === "external" ? newId : id;
  job.stage = "sent";
  record(address, job);
  return finish(job, context);
}

// The rest of a job once its new file is installed: its settings carried, the old file's
// taken, then the old file removed when its id still names its path and size.
async function finish(job, context) {
  const {client, address} = context;
  const operation = client.operation;
  const {settings, source, newId} = job;
  if (job.stage === "sent") {
    if (settings.ignored) await operation("move", () => commands.ignore(newId, true));
    if (settings.brightness !== null) await operation("move", () => commands.brightnessSave(newId, settings.brightness));
    if (settings.repeat !== null) await operation("move", () => commands.repeatSave(newId, settings.repeat));
    if (settings.brightness !== null) await operation("move", () => commands.brightnessDefault(source.id));
    if (settings.repeat !== null) await operation("move", () => commands.repeatDefault(source.id));
    job.stage = "carried";
    record(address, job);
  }
  // A job that names no folder of its source moves a file of the root of the board's own
  // storage, or one of the card, whose folder is that of its path.
  const folder = typeof source.folder === "string" ? source.folder : source.storage === "external" ? folderOf(source.path) : "";
  const level = await folderId(operation, folder, source.storage);
  const rows = level === undefined ? [] : await levelRows(operation, level);
  const old = rows.find((row) => row.id === source.id);
  if (old !== undefined && old.file === source.path && old.bytes === source.bytes && storageOf(old) === source.storage) {
    await operation("move", () => commands.remove(source.id));
  }
  forget(address, job);
  return newId;
}

// Finishes or ends the jobs a lost reply, a lost link or a restart left for this target:
// with the new file there, the job goes on from where it was; without it, the old file was
// never touched and the job ends as not moved. Gives the paths finished and those not moved.
export async function reconcile(context) {
  const {address, client} = context;
  const operation = client.operation;
  const finished = [];
  const notMoved = [];
  for (const job of pending(address)) {
    if (job.stage === "read" || job.stage === "sending") {
      const level = await folderId(operation, job.destination.folder, job.destination.storage);
      const rows = level === undefined ? [] : await levelRows(operation, level);
      const made = fileAt(rows, job.destination.storage, job.destination.path);
      if (made === undefined || made.bytes !== job.source.bytes) {
        forget(address, job);
        notMoved.push(job.source.path);
        continue;
      }
      job.newId = made.id;
      job.stage = "sent";
      record(address, job);
    }
    await finish(job, context);
    finished.push(job.source.path);
  }
  return {finished, notMoved};
}
