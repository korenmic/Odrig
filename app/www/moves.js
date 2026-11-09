// Moves of animation files and folders between and within the two storages, made by the
// app with the board's commands, one file at a time. A file of the card that stays on the
// card is moved by the board with `move external`, which keeps its id and its saved
// settings. Any other file is a job kept on the phone until it is done: its bytes read and
// checked, uploaded to the destination where nothing has its name, its saved settings given
// to the new file and taken from the old one, and only then the old file removed, after its
// id is found again with its path and size; a file that stays in the board's own storage is
// uploaded under its own id, which moves it there. A folder is moved as a job too: its
// folders made at the destination from the top, then its files moved one at a time. A job
// that a lost link, a hidden app or another target cuts short is kept until the next
// connection; one the board refuses ends.

import * as commands from "./commands.js";
import {crc32} from "./crc32.js";
import {Failure} from "./target.js";
import {freeId, uploading} from "./upload.js";

const KEY = "odrig.moves";
const INTERNAL_NAME = /^[a-z0-9_-][a-z0-9._-]*\.(odrg|odrgx)$/;
const EXTERNAL_PART = /^[ -~]+$/;
const LONGEST_PATH = 100;
// The longest path of a folder of the board's own storage, and the most folders a path has.
const LONGEST_INTERNAL_FOLDER = 93;
const DEEPEST = 3;

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

function joined(folder, name) {
  return folder ? `${folder}/${name}` : name;
}

// How a destination is written: `Internal /name` or `External /folder/name`.
export function label(storage, path) {
  return `${storage === "external" ? "External" : "Internal"} /${path}`;
}

// Why a name cannot be a file's name in a folder of a storage, or null when it can.
export function nameProblem(storage, folder, name) {
  const path = joined(folder, name);
  if (storage === "internal") {
    if (!(name.length <= 32 && INTERNAL_NAME.test(name))) return "Internal storage takes names of at most 32 lowercase letters, digits, dots, - or _, ending in .odrg or .odrgx.";
  } else if (!EXTERNAL_PART.test(name) || /[\\/:*?"<>|]/.test(name) || /^[ .]|[ .]$/.test(name.replace(/\.odrgx?$/i, "x")) || !/\.odrgx?$/i.test(name) || /^[0-9]+$/.test(name)) {
    return "Use printable letters without \\ / : * ? \" < > |, not beginning or ending with a space or a dot, ending in .odrg or .odrgx.";
  }
  return path.length <= LONGEST_PATH ? null : "The destination path exceeds 100 characters; use a shorter name.";
}

// Why a name cannot be a folder's name under a parent of a storage, or null when it can.
export function folderNameProblem(storage, parent, name) {
  const path = joined(parent, name);
  if (!name || !/^[ -~]+$/.test(name) || /[\\/:*?"<>|]/.test(name) || /^[ .]|[ .]$/.test(name)) {
    return "Use printable letters without \\ / : * ? \" < > |, not beginning or ending with a space or a dot.";
  }
  if (/\.odrgx?$/i.test(name)) return "A folder's name does not end in .odrg or .odrgx.";
  if (path.split("/").length > DEEPEST) return "Folders are kept three levels deep at most.";
  if (storage === "internal" ? path.length > LONGEST_INTERNAL_FOLDER : path.length + 7 > LONGEST_PATH) return "The folder's path is too long for a file to fit in it.";
  return null;
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
    const path = joined(destination.folder, name);
    const entry = {source, storage: destination.storage, folder: destination.folder, name, path, skip: null};
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

// The plan of a folder's move: the folder with its subtree, `tree` as `subtree` gives it, to
// the destination `{storage, folder}`, whose level has `rows` now. Gives the folder, the
// path it takes, the folders to make there from the top with whether each is ignored, and
// for each of its files an entry as `plan` gives one, or why the whole folder is skipped.
// `names` holds the names given in the preview: of the folder by `folder:<id>`, of a file
// by its id; `blocked` the reasons known before, by a file's id; `others` the names of the
// folders planned before it into the same destination.
export function folderPlan(tree, destination, rows, names = new Map(), blocked = new Map(), others = []) {
  const folder = tree.folders[0];
  const storage = storageOf(folder);
  const name = names.get(`folder:${folder.id}`) ?? baseOf(folder.playlist);
  const top = joined(destination.folder, name);
  const moved = {folder, storage: destination.storage, name, path: top, folders: [], entries: [], skip: null};
  const inside = (path) => path.slice(folder.playlist.length + 1);
  const into = (path) => (path === folder.playlist ? top : `${top}/${inside(path)}`);
  const taken = rows.filter((row) => storageOf(row) === destination.storage && (typeof row.file === "string" || typeof row.playlist === "string"))
    .map((row) => baseOf(row.file ?? row.playlist));
  if (storage === "internal" && destination.storage === "internal") moved.skip = "A folder of Internal storage is not moved inside Internal storage; move it to External storage, or move its files.";
  else if (storage === destination.storage && (destination.folder === folder.playlist || destination.folder.startsWith(`${folder.playlist}/`))) moved.skip = "A folder is not moved into itself or into a folder below it.";
  else if (storage === destination.storage && top === folder.playlist) moved.skip = "It is there already.";
  else if (folderNameProblem(destination.storage, destination.folder, name) !== null) moved.skip = folderNameProblem(destination.storage, destination.folder, name);
  else if (taken.some((other) => sameName("external", other, name))) moved.skip = "The destination has a folder or a file of this name. Give it another name to move it.";
  else if (others.some((other) => sameName("external", other, name))) moved.skip = "Another selected folder takes this name. Give it another name to move it.";
  else {
    for (const below of tree.folders.slice(1)) {
      const problem = folderNameProblem(destination.storage, folderOf(into(below.playlist)), baseOf(below.playlist));
      if (problem !== null) {
        moved.skip = `Its folder ${below.playlist}: ${problem}`;
        break;
      }
    }
  }
  if (moved.skip !== null) return moved;
  moved.folders = tree.folders.map((below) => ({from: below.playlist, path: into(below.playlist), ignored: below.ignored === true}));
  const planned = new Map();
  for (const source of tree.files) {
    const destinationFolder = into(folderOf(source.file));
    const fileName = names.get(source.id) ?? baseOf(source.file);
    const entry = {source, storage: destination.storage, folder: destinationFolder, name: fileName, path: joined(destinationFolder, fileName), skip: null};
    const others = planned.get(destinationFolder) ?? [];
    if (blocked.has(source.id)) entry.skip = blocked.get(source.id);
    else if (typeof source.bytes !== "number") entry.skip = "Its size is not known yet; try again once the list shows it.";
    else if (nameProblem(destination.storage, destinationFolder, fileName) !== null) entry.skip = nameProblem(destination.storage, destinationFolder, fileName);
    else if (others.some((other) => sameName(destination.storage, other, fileName))) entry.skip = "Another file of the folder takes this name. Give it another name to move it.";
    if (entry.skip === null) planned.set(destinationFolder, [...others, fileName]);
    moved.entries.push(entry);
  }
  return moved;
}

// The journal of the moves under way, by target address, kept on the phone: the jobs of
// files, and those of folders, `kind` "folder".
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

function same(job, other) {
  return other.kind === job.kind && other.source.id === job.source.id && other.source.storage === job.source.storage;
}

function record(address, job) {
  keep(address, [...pending(address).filter((other) => !same(job, other)), job]);
}

function forget(address, job) {
  keep(address, pending(address).filter((other) => !same(job, other)));
}

// Whether an error cut a job short, which then waits for the next connection, rather than
// ended its file: no answer, no Wi-Fi, a request withdrawn as the app was hidden, or another
// target chosen.
function cutShort(error, context) {
  const withdrawn = context.client.Withdrawn;
  return (error instanceof Failure && error.kind !== "bad-reply") || (typeof withdrawn === "function" && error instanceof withdrawn) || context.switched?.() === true;
}

// The requests of a job, each sent only while the target it began with is chosen.
function requests(context) {
  return (kind, carry) => {
    if (context.switched?.() === true) return Promise.reject(new Error("Another installation was chosen."));
    return context.client.operation(kind, carry);
  };
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

// A folder of either storage with everything in it: its folders from the top, itself first,
// each level's sub-folders before the files of the next, and its files level by level.
export async function subtree(operation, folder) {
  const folders = [];
  const files = [];
  const waiting = [folder];
  while (waiting.length > 0) {
    const level = waiting.shift();
    folders.push(level);
    for (const row of await levelRows(operation, level.id)) {
      if (typeof row.playlist === "string" && storageOf(row) === storageOf(folder)) waiting.push(row);
      else if (typeof row.file === "string" && storageOf(row) === storageOf(folder)) files.push(row);
    }
  }
  return {folders, files};
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

// Whether a file is still where a job found it: its id with its path and size, in its level.
async function stillThere(operation, source) {
  const level = await folderId(operation, sourceFolder(source), storageOf(source));
  if (level === undefined) return false;
  const row = (await levelRows(operation, level)).find((other) => other.id === source.id);
  return row !== undefined && row.file === source.file && row.bytes === source.bytes && storageOf(row) === storageOf(source);
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

// Refuses, as Clocks only does, a move into a folder of a storage that `context.allowed`
// does not allow, "" for its root.
function allowedInto(context, storage, folder) {
  if (context.allowed !== undefined && !context.allowed(storage, folder)) throw new commands.Refusal("in-use", "move");
}

// Moves one planned file. `context` has the client, the address of the target,
// `report(text)`, `stopped()`, `switched()`, true once another target is chosen, and may have
// `allowed(storage, folder)`, false for a destination the mode keeps files out of. Gives the
// file's id afterwards. A file of the card that stays on the card under its name is moved by
// the board, which keeps its id and its saved settings, and by a job when the board's
// firmware cannot.
export async function move(entry, context) {
  const {client, address} = context;
  const operation = requests(context);
  allowedInto(context, entry.storage, entry.folder);
  if (storageOf(entry.source) === "external" && entry.storage === "external" && entry.name === baseOf(entry.source.file)) {
    context.report(`Moving ${label("external", entry.source.file)}`);
    const moveOnCard = () => operation("move", () => commands.moveExternal(entry.source.id, entry.folder));
    try {
      try {
        await moveOnCard();
      } catch (error) {
        // A reply that did not come: the line is sent once more, as a file moved already
        // answers that it did not move.
        if (!(error instanceof Failure && error.kind === "no-answer")) throw error;
        await moveOnCard();
      }
      return entry.source.id;
    } catch (error) {
      if (!(error instanceof commands.Refusal && error.code === "unknown-command")) throw error;
    }
  }
  const source = {id: entry.source.id, storage: storageOf(entry.source), path: entry.source.file, folder: sourceFolder(entry.source), bytes: entry.source.bytes,
    ignored: entry.source.ignored === true};
  const job = {source, destination: {storage: entry.storage, folder: entry.folder, name: entry.name, path: entry.path}, stage: "read",
    sameId: source.storage === "internal" && entry.storage === "internal"};
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
  if (job.sameId) {
    // The upload under its own id gives the file a stored name of its folder, which has no
    // saved settings: those of its old one are taken first, kept in the job.
    id = source.id;
    try {
      if (saved.brightness !== null) await operation("move", () => commands.brightnessDefault(source.id));
      if (saved.repeat !== null) await operation("move", () => commands.repeatDefault(source.id));
    } catch (error) {
      if (!cutShort(error, context)) await given(job, context);
      throw error;
    }
  } else if (entry.storage === "internal") {
    // Free among the ids of the root and of every folder of the board's own storage.
    const taken = [];
    const waiting = [null];
    while (waiting.length > 0) {
      const rows = await levelRows(operation, waiting.shift());
      for (const row of rows) {
        taken.push(row.id);
        if (typeof row.playlist === "string" && row.external === false) waiting.push(row.id);
      }
    }
    id = freeId(new Set(taken));
    if (id === null) throw new Error("Internal storage has no free animation id.");
  }
  let newId;
  try {
    newId = await upload(client, {id, file: entry.path, bytes, external: entry.storage === "external", create: !job.sameId, expect: entry.storage === "external" ? "00000000" : null},
      (part) => context.report(`Sending ${label(entry.storage, entry.path)}: ${Math.floor(part * 100)}%`));
  } catch (error) {
    if (job.sameId && error instanceof commands.Refusal) await given(job, context);
    throw error;
  }
  job.newId = entry.storage === "external" ? newId : id;
  job.stage = "sent";
  record(address, job);
  return finish(job, context);
}

// The rest of a job once its new file is installed: its settings carried, the old file's
// taken, then the old file removed when its id still names its path and size.
async function finish(job, context) {
  const {address} = context;
  const operation = requests(context);
  const {settings, source, newId} = job;
  if (job.stage === "sent") {
    if (settings.ignored) await operation("move", () => commands.ignore(newId, true));
    if (settings.brightness !== null) await operation("move", () => commands.brightnessSave(newId, settings.brightness));
    if (settings.repeat !== null) await operation("move", () => commands.repeatSave(newId, settings.repeat));
    if (settings.brightness !== null && !job.sameId) await operation("move", () => commands.brightnessDefault(source.id));
    if (settings.repeat !== null && !job.sameId) await operation("move", () => commands.repeatDefault(source.id));
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

// A file of the board's own storage that did not move under its own id is given back the
// saved settings that the job took from it, and the job ends.
async function given(job, context) {
  const operation = requests(context);
  const {settings, source} = job;
  if (settings.brightness !== null) await operation("move", () => commands.brightnessSave(source.id, settings.brightness));
  if (settings.repeat !== null) await operation("move", () => commands.repeatSave(source.id, settings.repeat));
  forget(context.address, job);
}

// The current playlist as the status says it, `{id, path, storage}`, or null for none.
function playlistOf(status) {
  if (typeof status?.playing !== "number" || typeof status.playlist !== "string") return null;
  return {id: status.playing, path: status.playlist, storage: status.playing > 60000 ? "external" : "internal"};
}

// The job of a planned folder, kept on the phone until its files are moved. When the current
// playlist is the folder's or one below it, the job follows it to its new place.
function folderJob(planned, playlist) {
  const folder = planned.folder;
  const followed = playlist !== null && playlist.storage === storageOf(folder) ? planned.folders.find((each) => each.from === playlist.path) : undefined;
  return {
    kind: "folder",
    source: {id: folder.id, storage: storageOf(folder), path: folder.playlist},
    destination: {storage: planned.storage, path: planned.path},
    folders: planned.folders,
    files: planned.entries.filter((entry) => entry.skip === null).map(({source, storage, folder: into, name, path}) => ({source, storage, folder: into, name, path})),
    ...(followed === undefined ? {} : {follows: {id: playlist.id, path: followed.path}}),
  };
}

// Makes a job's folders at its destination, from the top, each with the Ignore of the one it
// stands for, keeping each one's id in the job; one that is there already is taken as made.
// False when the job was stopped first. A destination `context.allowed` does not allow is
// refused before any folder is made.
async function makeFolders(job, context) {
  const operation = requests(context);
  allowedInto(context, job.destination.storage, folderOf(job.destination.path));
  for (const folder of job.folders) {
    if (context.stopped()) return false;
    context.report(`Making ${label(job.destination.storage, folder.path)}`);
    const made = await operation("move", () => commands.folderMake(folder.path, job.destination.storage));
    if (folder.ignored) await operation("move", () => commands.ignore(made.id, true));
    folder.id = made.id;
    record(context.address, job);
  }
  return true;
}

// Once a job has moved every file of a folder whose playlist was current, the board plays
// the root's in its place: the folder's new place is played instead, unless another
// playlist was chosen meanwhile. Gives whether it was.
async function follow(job, context) {
  const folder = job.folders.find((each) => each.path === job.follows.path);
  if (typeof folder?.id !== "number") return false;
  const operation = requests(context);
  try {
    const playing = (await operation("move", () => commands.status())).playing;
    if (playing !== "all" && playing !== job.follows.id) return false;
    await operation("move", () => commands.play(folder.id));
    return true;
  } catch (_) {
    return false;
  }
}

// Moves the files of a folder's job one at a time, after its folders are made; with
// `checking`, only those still where the job found them. A file the board refuses, or that
// fails for itself, is said and passed. A job that a lost link, a hidden app or another
// target cuts short keeps its files, the one under way first, for the next connection; a
// job stopped is forgotten, its files left unstarted where they are; a job whose folders the
// board refuses is forgotten, and the refusal thrown. Gives the paths moved, the files
// failed with why, the number not moved, what cut the job short or null, and whether the
// playlist followed the folder.
async function runFolder(job, context, checking = false) {
  const {address} = context;
  const moved = [];
  const failed = [];
  let cut = null;
  record(address, job);
  let made = false;
  try {
    made = await makeFolders(job, context);
  } catch (error) {
    if (!cutShort(error, context)) {
      forget(address, job);
      throw error;
    }
    cut = error;
  }
  while (made && job.files.length > 0) {
    if (context.stopped()) break;
    if (context.waitVisible) await context.waitVisible();
    const entry = job.files[0];
    try {
      if (!checking || await stillThere(requests(context), entry.source)) {
        context.report(`Moving ${label(storageOf(entry.source), entry.source.file)}`);
        await move(entry, context);
        moved.push(entry.path);
      }
    } catch (error) {
      if (cutShort(error, context)) {
        cut = error;
        break;
      }
      failed.push({file: entry.source.file, error});
    }
    job.files.shift();
    record(address, job);
  }
  if (cut === null && context.switched?.() === true) cut = new Error("Another installation was chosen.");
  let followed = false;
  if (cut === null) {
    forget(address, job);
    if (job.files.length === 0 && job.follows !== undefined) followed = await follow(job, context);
  }
  return {moved, failed, unstarted: job.files.length, cut, followed};
}

// Moves a planned folder: its folders made at the destination from the top, then its files
// one at a time, the job kept on the phone meanwhile. Gives what `runFolder` gives, and
// whether the source folder is gone: it stays while it holds what was not moved or a
// folder without files, which no command removes. A job cut short does not ask.
export async function moveFolder(planned, context) {
  const job = folderJob(planned, context.playlist === undefined ? null : playlistOf(context.playlist()));
  const done = await runFolder(job, context);
  if (done.cut !== null) return {...done, sourceGone: false};
  let left = null;
  try {
    left = await folderId(requests(context), job.source.path, job.source.storage);
  } catch (error) {
    if (!cutShort(error, context)) throw error;
  }
  return {...done, sourceGone: left === undefined};
}

// Finishes or ends the jobs a lost reply, a lost link or a restart left for this target:
// a file's job with its new file there goes on from where it was; without it, the old file
// was never touched and the job ends as not moved. A folder's job then makes its folders
// and moves the files still where it found them. Gives the paths finished and those not
// moved, the files that failed with why, the folders given up with why, and the paths of
// the jobs cut short again, which wait for the next connection.
export async function reconcile(context) {
  const {address} = context;
  const operation = requests(context);
  const done = {finished: [], notMoved: [], failed: [], givenUp: [], cut: []};
  for (const job of pending(address).filter((each) => each.kind !== "folder")) {
    try {
      if (job.stage === "read" || job.stage === "sending") {
        const level = await folderId(operation, job.destination.folder, job.destination.storage);
        const rows = level === undefined ? [] : await levelRows(operation, level);
        const made = fileAt(rows, job.destination.storage, job.destination.path);
        if (made === undefined || made.bytes !== job.source.bytes) {
          if (job.sameId) await given(job, context);
          forget(address, job);
          done.notMoved.push(job.source.path);
          continue;
        }
        job.newId = made.id;
        job.stage = "sent";
        record(address, job);
      }
      await finish(job, context);
      done.finished.push(job.source.path);
    } catch (error) {
      if (!cutShort(error, context)) throw error;
      done.cut.push(job.source.path);
      return done;
    }
  }
  for (const job of pending(address).filter((each) => each.kind === "folder")) {
    try {
      const ran = await runFolder(job, context, true);
      done.failed.push(...ran.failed);
      if (ran.cut !== null) {
        done.cut.push(job.source.path);
        break;
      }
      done.finished.push(`${job.source.path}/ (${ran.moved.length} file${ran.moved.length === 1 ? "" : "s"})`);
    } catch (error) {
      done.givenUp.push({path: job.source.path, error});
    }
  }
  return done;
}
