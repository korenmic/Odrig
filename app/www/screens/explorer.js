// The explorer's actions on the list: a new folder at the level shown, of the board's own
// storage or of the card, and the move of the selected files and folders to a storage and a
// folder the operator names in full, each destination shown before anything is sent.

import * as client from "../client.js";
import * as commands from "../commands.js";
import {Refusal} from "../commands.js";
import * as messages from "../messages.js";
import * as moves from "../moves.js";
import * as target from "../target.js";
import {Failure} from "../target.js";

let message = () => {};
let redraw = () => {};
let chosen = () => [];
let chosenFolders = () => [];
let done = () => {};
// The folder dialog's level, the move dialog's files and plan, and the run under way.
let folderAt = null;
let moving = null;
let running = null;
let reconciledFor = null;
// The target whose kept moves wait until Clocks only is left.
let heldFor = null;

function byId(id) {
  return document.getElementById(id);
}

// Whether the app may write the card now: present, writable, and its catalog read.
export function cardWritable(state) {
  const card = state.space?.external;
  return card?.present === true && card.read_only === false && state.catalog?.external?.state === "ok";
}

// Whether it is known whether the board may write the card: its space is known, and a card
// that is present and not read-only has had its catalog read.
function cardSettled(state) {
  if (state.space === null || state.space === undefined) return false;
  const card = state.space.external;
  if (card?.present !== true || card.read_only !== false) return true;
  const catalog = state.catalog?.external?.state;
  return catalog !== undefined && catalog !== "loading";
}

// Why the card cannot be a destination now, or null.
function cardReason(state) {
  const card = state.space?.external;
  if (card?.present !== true) return "External storage is not detected.";
  if (card.read_only !== false) return "External storage is read-only.";
  if (state.catalog?.external?.state !== "ok") return "External storage has no ready catalog.";
  return null;
}

export function busy() {
  return running !== null;
}

function refusalText(error) {
  if (error instanceof Refusal && error.code === "unknown-command") return "This installation's firmware cannot do this. Install the newer firmware.";
  if (error instanceof Refusal) return messages.ofRefusal(error, client.state.status?.error ?? null, client.state.status?.hasClockStorage === true);
  if (error instanceof Failure) return messages.ofFailure(error);
  return error.message;
}

// Why a folder's name cannot be made under a parent, or null.
export function folderProblem(parent, name) {
  const path = parent ? `${parent}/${name}` : name;
  if (!name || !/^[ -~]+$/.test(name) || /[\\/:*?"<>|]/.test(name) || /^[ .]|[ .]$/.test(name)) {
    return "Use printable letters without \\ / : * ? \" < > |, not beginning or ending with a space or a dot.";
  }
  if (/\.odrgx?$/i.test(name)) return "A folder's name does not end in .odrg or .odrgx.";
  if (path.split("/").length > 3) return "The card keeps folders three levels deep at most.";
  if (path.length + 7 > 100) return "The folder's path is too long for a file to fit in it.";
  return null;
}

// The storage of a new folder at the level shown: the level's own inside a folder, and at
// the root the one chosen, the card only while it may be written.
function folderStorage(state) {
  if (state.level.id !== null) return state.level.storage === "internal" ? "internal" : "external";
  const chosen = byId("folder-storage").value;
  return chosen === "external" && cardWritable(state) ? "external" : "internal";
}

function showWhere() {
  if (folderAt === null) return;
  folderAt.storage = folderStorage(client.state);
  byId("folder-where").textContent = `In ${moves.label(folderAt.storage, folderAt.path ? `${folderAt.path}/` : "")}`;
}

function openFolder(playlist) {
  const state = client.state;
  const level = state.level;
  folderAt = {path: level.path, playlist, version: client.targetVersion(), storage: "internal"};
  byId("folder-dialog-title").textContent = playlist ? "New playlist folder" : "New folder";
  const atRoot = level.id === null;
  const chooser = byId("folder-storage");
  chooser.hidden = !atRoot;
  byId("folder-storage-label").hidden = !atRoot;
  chooser.querySelector('option[value="external"]').disabled = !cardWritable(state);
  if (atRoot) chooser.value = cardWritable(state) ? "external" : "internal";
  showWhere();
  byId("folder-name").value = "";
  byId("folder-problem").textContent = "";
  byId("folder-dialog").hidden = false;
  byId("folder-name").focus();
}

function closeFolder() {
  folderAt = null;
  byId("folder-dialog").hidden = true;
}

async function makeFolder() {
  const asked = folderAt;
  if (asked === null) return;
  const name = byId("folder-name").value.trim();
  const problem = folderProblem(asked.path, name);
  if (problem !== null) {
    byId("folder-problem").textContent = problem;
    return;
  }
  closeFolder();
  if (asked.version !== client.targetVersion()) return;
  const path = asked.path ? `${asked.path}/${name}` : name;
  try {
    const made = await client.operation("folder", () => commands.folderMake(path, asked.storage));
    message(made.made ? `Made the folder ${moves.label(asked.storage, path)}. It plays as a playlist once files are in it.` : `The folder ${moves.label(asked.storage, path)} was there already.`);
  } catch (error) {
    message(`The folder was not made. ${refusalText(error)}`);
  } finally {
    client.refreshContent();
  }
}

// Every folder of a storage, "external" the card, its root first, by their paths, walked
// level by level.
async function foldersOf(storage) {
  const found = [""];
  const pending = [null];
  while (pending.length > 0 && found.length < 256) {
    const folder = pending.shift();
    let from = 0;
    do {
      const reply = await client.operation("move", () => commands.list(from, folder));
      for (const row of reply.items) {
        if (typeof row.playlist === "string" && (row.external === true) === (storage === "external") && !found.includes(row.playlist)) {
          found.push(row.playlist);
          pending.push(row.id);
        }
      }
      from = reply.next;
    } while (from !== null);
  }
  return found;
}

// The reasons some files cannot move at all, by id, from the root's rows with its cycles and
// the rows of each file's own level.
async function blockedOf(files) {
  const reasons = new Map();
  const levels = new Map();
  for (const file of files) {
    const key = `${file.external === true}:${moves.sourceFolder(file)}`;
    if (!levels.has(key)) levels.set(key, await moves.sourceRows(client.operation, file));
    const held = moves.heldBy(levels.get(key), file);
    if (held !== null) reasons.set(file.id, held);
  }
  return reasons;
}

async function destinationRows(storage, folder) {
  const level = folder ? await moves.folderId(client.operation, folder, storage) : null;
  if (level === undefined) throw new Error("The folder is gone; choose another.");
  return (await client.uploadSnapshot({path: folder, id: level, storage})).items;
}

function storageOfRow(row) {
  return row.external === true ? "external" : "internal";
}

// A line of the preview: the source and its destination, and why it is skipped, with a
// field for another name when the skip is about its name.
function previewLine(from, to, skip, name, key, what, inner = false) {
  const item = document.createElement("li");
  if (inner) item.classList.add("inner");
  const line = document.createElement("span");
  line.textContent = `${from} \u2192 ${to}`;
  item.append(line);
  if (skip !== null) {
    item.classList.add("skipped");
    const why = document.createElement("span");
    why.className = "small";
    why.textContent = ` Skipped: ${skip}`;
    item.append(why);
    if (/name/.test(skip)) {
      const rename = document.createElement("input");
      rename.type = "text";
      rename.value = name;
      rename.setAttribute("aria-label", `Another name for ${what}`);
      rename.addEventListener("change", () => {
        moving.names.set(key, rename.value.trim());
        replan();
      });
      item.append(rename);
    }
  }
  return item;
}

function drawPlan() {
  const list = byId("move-preview");
  list.replaceChildren();
  if (moving === null || moving.plan === null) return;
  for (const entry of moving.plan) {
    list.append(previewLine(moves.label(storageOfRow(entry.source), entry.source.file), moves.label(entry.storage, entry.path), entry.skip, entry.name, entry.source.id, entry.source.file));
  }
  for (const planned of moving.folderPlans) {
    const from = moves.label(storageOfRow(planned.folder), `${planned.folder.playlist}/`);
    list.append(previewLine(`Folder ${from}`, moves.label(planned.storage, `${planned.path}/`), planned.skip, planned.name, `folder:${planned.folder.id}`, planned.folder.playlist));
    for (const entry of planned.skip === null ? planned.entries : []) {
      list.append(previewLine(moves.label(storageOfRow(entry.source), entry.source.file), moves.label(entry.storage, entry.path), entry.skip, entry.name, entry.source.id, entry.source.file, true));
    }
  }
  const files = moving.plan.filter((entry) => entry.skip === null).length;
  const folders = moving.folderPlans.filter((planned) => planned.skip === null);
  const inside = folders.reduce((sum, planned) => sum + planned.entries.filter((entry) => entry.skip === null).length, 0);
  const counted = (count, word) => `${count} ${word}${count === 1 ? "" : "s"}`;
  const words = [];
  if (files > 0 || folders.length === 0) words.push(counted(files, "file"));
  if (folders.length > 0) words.push(`${counted(folders.length, "folder")} with ${counted(inside, "file")}`);
  byId("move-go").textContent = `Move ${words.join(" and ")}`;
  byId("move-go").disabled = (files === 0 && folders.length === 0) || running !== null;
}

function replan() {
  if (moving === null || moving.rows === null || moving.trees === null) return;
  moving.plan = moves.plan(moving.files, moving.destination, moving.rows, moving.names, moving.blocked);
  const planned = [];
  moving.folderPlans = moving.trees.map((tree) => {
    const made = moves.folderPlan(tree, moving.destination, moving.rows, moving.names, moving.blocked, planned);
    if (made.skip === null) planned.push(made.name);
    return made;
  });
  drawPlan();
}

// The folders of a storage the chooser offers, each by its full path, the level shown chosen
// when it is one of them: in Clocks only those the mode lets files into alone.
function offerFolders(storage) {
  const folder = byId("move-folder");
  folder.replaceChildren();
  for (const path of (moving.folders[storage] ?? [""]).filter((each) => client.canMoveInto(storage, each))) {
    const option = document.createElement("option");
    option.value = path;
    option.textContent = `/${path}`;
    folder.append(option);
  }
  const level = client.state.level;
  const here = level.id !== null && (level.storage ?? "external") === storage ? level.path : "";
  folder.value = [...folder.options].some((option) => option.value === here) ? here : "";
}

async function chooseDestination(event) {
  if (moving === null) return;
  const storage = byId("move-storage").value;
  if (event?.target?.id !== "move-folder") offerFolders(storage);
  const folder = byId("move-folder").value;
  moving.destination = {storage, folder};
  moving.rows = null;
  moving.plan = null;
  byId("move-go").disabled = true;
  byId("move-preview").replaceChildren();
  if (byId("move-folder").options.length === 0 || !client.canMoveInto(storage, folder)) {
    byId("move-state").textContent = messages.onlyDestination(client.state.status?.hasClockStorage === true);
    return;
  }
  // Only the destination chosen last is read into the preview.
  const asked = moving;
  const request = {};
  moving.request = request;
  try {
    const rows = await destinationRows(storage, folder);
    if (moving !== asked || moving.request !== request) return;
    moving.rows = rows;
    replan();
  } catch (error) {
    if (moving === asked && moving.request === request) byId("move-state").textContent = `The destination could not be read. ${refusalText(error)}`;
  }
}

async function openMove() {
  const files = chosen();
  const folders = chosenFolders();
  if ((files.length === 0 && folders.length === 0) || running !== null) return;
  moving = {files, chosenFolders: folders, trees: null, folderPlans: [], folders: {}, names: new Map(), blocked: new Map(), destination: null, rows: null, plan: null,
    version: client.targetVersion()};
  const reason = cardReason(client.state);
  const storage = byId("move-storage");
  storage.querySelector('option[value="external"]').disabled = reason !== null;
  storage.value = reason === null ? "external" : "internal";
  byId("move-storage-reason").textContent = reason === null ? "" : `${reason} Only Internal storage can take them now.`;
  const words = [];
  if (files.length > 0) words.push(`${files.length} file${files.length === 1 ? "" : "s"}`);
  if (folders.length > 0) words.push(`${folders.length} folder${folders.length === 1 ? "" : "s"}, with everything in ${folders.length === 1 ? "it" : "them"}`);
  byId("move-state").textContent = `${words.join(" and ")} selected.`;
  byId("move-folder").replaceChildren();
  byId("move-dialog").hidden = false;
  const asked = moving;
  try {
    const trees = [];
    for (const folder of folders) trees.push(await moves.subtree(client.operation, folder));
    const blocked = await blockedOf([...files, ...trees.flatMap((tree) => tree.files)]);
    if (moving === asked) {
      moving.trees = trees;
      moving.blocked = blocked;
    }
  } catch (error) {
    if (moving === asked) {
      moving.trees = [];
      byId("move-state").textContent = `The show could not be read. ${refusalText(error)}`;
    }
  }
  for (const each of reason === null ? ["internal", "external"] : ["internal"]) {
    try {
      const found = await foldersOf(each);
      if (moving === asked) moving.folders[each] = found;
    } catch (error) {
      if (moving === asked) byId("move-state").textContent = `The folders could not be read. ${refusalText(error)}`;
    }
  }
  if (moving !== asked) return;
  if (client.clocksOnly()) {
    // Clocks only keeps the files inside Clocks: a storage without a folder there is not offered.
    const inside = (each) => (moving.folders[each] ?? []).some((path) => client.canMoveInto(each, path));
    for (const each of ["internal", "external"]) {
      const option = storage.querySelector(`option[value="${each}"]`);
      option.disabled = option.disabled || !inside(each);
    }
    if (storage.querySelector(`option[value="${storage.value}"]`).disabled) storage.value = inside("external") ? "external" : "internal";
    const why = byId("move-storage-reason");
    why.textContent = `${why.textContent ? `${why.textContent} ` : ""}${messages.onlyDestination(client.state.status?.hasClockStorage === true)}`;
  }
  await chooseDestination();
}

function closeMove() {
  if (running !== null) return;
  moving = null;
  byId("move-dialog").hidden = true;
}

function waitVisible() {
  return new Promise((resolve) => {
    if (!document.hidden) {
      resolve();
      return;
    }
    const seen = () => {
      if (!document.hidden) {
        document.removeEventListener("visibilitychange", seen);
        resolve();
      }
    };
    document.addEventListener("visibilitychange", seen);
  });
}

async function runMove() {
  if (moving === null || moving.plan === null || running !== null) return;
  const version = moving.version;
  if (version !== client.targetVersion()) return;
  const entries = moving.plan.filter((entry) => entry.skip === null);
  const folderPlans = moving.folderPlans.filter((planned) => planned.skip === null);
  const skipped = [...moving.plan.filter((entry) => entry.skip !== null).map((entry) => entry.source.file),
    ...moving.folderPlans.filter((planned) => planned.skip !== null).map((planned) => `${planned.folder.playlist}/`),
    ...folderPlans.flatMap((planned) => planned.entries.filter((entry) => entry.skip !== null).map((entry) => entry.source.file))];
  const total = entries.length + folderPlans.reduce((sum, planned) => sum + planned.entries.filter((entry) => entry.skip === null).length, 0);
  running = {stop: false};
  const progress = byId("move-progress");
  const moved = [];
  const failed = [];
  const folderWords = [];
  let unstarted = 0;
  client.setContentBusy("move");
  drawPlan();
  byId("move-stop").hidden = false;
  let cutWords = null;
  const context = {
    client,
    address: target.address(),
    report: (text) => { progress.textContent = text; },
    stopped: () => running.stop || version !== client.targetVersion(),
    switched: () => version !== client.targetVersion(),
    waitVisible,
    playlist: () => client.state.status,
    allowed: client.canMoveInto,
  };
  try {
    for (const [at, entry] of entries.entries()) {
      if (context.stopped()) {
        unstarted += entries.length - at;
        break;
      }
      await waitVisible();
      progress.textContent = `Moving ${at + 1} of ${entries.length}: ${entry.source.file}`;
      try {
        await moves.move(entry, context);
        moved.push(entry.path);
      } catch (error) {
        failed.push(`${entry.source.file}: ${refusalText(error)}`);
      }
    }
    for (const [at, planned] of folderPlans.entries()) {
      const from = moves.label(storageOfRow(planned.folder), `${planned.folder.playlist}/`);
      if (context.stopped()) {
        unstarted += folderPlans.slice(at).reduce((sum, rest) => sum + rest.entries.filter((entry) => entry.skip === null).length, 0);
        break;
      }
      await waitVisible();
      try {
        const done = await moves.moveFolder(planned, context);
        moved.push(...done.moved);
        failed.push(...done.failed.map((each) => `${each.file}: ${refusalText(each.error)}`));
        if (done.cut !== null) {
          const rest = folderPlans.slice(at + 1).reduce((sum, other) => sum + other.entries.filter((entry) => entry.skip === null).length, 0);
          cutWords = `The move of ${from} was cut short: ${refusalText(done.cut)} Its ${done.unstarted} file${done.unstarted === 1 ? "" : "s"} left ` +
            `${done.unstarted === 1 ? "moves" : "move"} when the app reaches the installation again.${rest ? ` Not started: ${rest}.` : ""}`;
          break;
        }
        unstarted += done.unstarted;
        folderWords.push(`${from} is now ${moves.label(planned.storage, `${planned.path}/`)}.` +
          (done.followed ? " Its playlist plays there." : "") +
          (done.sourceGone ? "" : ` ${from} stays at its old place with what was not moved, or folders without files, which are not removed.`));
      } catch (error) {
        failed.push(`${planned.folder.playlist}/: ${refusalText(error)}`);
      }
    }
  } finally {
    running = null;
    // A job cut short is taken up once the installation answers again.
    if (moves.pending(context.address).length > 0) reconciledFor = null;
    byId("move-stop").hidden = true;
    client.setContentBusy(false);
    client.refreshContent();
  }
  const words = [`Moved ${moved.length} of ${total + skipped.length}.`, ...folderWords];
  if (skipped.length) words.push(`Skipped ${skipped.length}: ${skipped.join(", ")}.`);
  if (failed.length) words.push(`Failed ${failed.length}: ${failed.join("; ")}.`);
  if (cutWords !== null) words.push(cutWords);
  if (unstarted) words.push(`Not started after Stop: ${unstarted}.`);
  progress.textContent = words.join(" ");
  message(words.join(" "));
  moving = null;
  byId("move-dialog").hidden = true;
  done();
}

// Finishes the moves a lost reply, a lost link or a restart of the app left for this
// target, once its list answers while the app is on the screen. Moves cut short again are
// taken up when the target answers again after it did not, or when the app is shown again;
// a move the target refuses is said and not asked again. In Clocks only a move whose
// destination is outside Clocks is not finished, since that would take its files out of
// Clocks: it waits until the mode is left, and one that moved nothing ends.
async function reconcile(state) {
  const address = target.address();
  if (state.link !== "answers" || document.hidden) {
    if (running === null) reconciledFor = null;
    return;
  }
  if (heldFor === address && running === null && !client.clocksOnly()) {
    heldFor = null;
    reconciledFor = null;
  }
  if (reconciledFor === address || running !== null || state.animations === null || client.contentBusy()) return;
  reconciledFor = address;
  if (moves.pending(address).length === 0) return;
  const version = client.targetVersion();
  running = {stop: false};
  client.setContentBusy("move");
  let again = false;
  try {
    const done = await moves.reconcile({client, address, report: (text) => message(`Finishing a move cut short earlier: ${text}`),
      stopped: () => version !== client.targetVersion(), switched: () => version !== client.targetVersion(), waitVisible, playlist: () => client.state.status,
      allowed: client.canMoveInto});
    const words = [];
    if (done.finished.length) words.push(`Finished the interrupted move of ${done.finished.join(", ")}.`);
    if (done.notMoved.length) words.push(`Not moved, left where they were: ${done.notMoved.join(", ")}.`);
    if (done.held.length) heldFor = address;
    if (done.failed.length) words.push(`Failed ${done.failed.length}: ${done.failed.map((each) => `${each.file}: ${refusalText(each.error)}`).join("; ")}.`);
    for (const each of done.givenUp) words.push(`The interrupted move of ${each.path}/ was given up: ${refusalText(each.error)}`);
    if (done.cut.length) {
      again = true;
      words.push(`The interrupted move of ${done.cut.join(", ")} goes on when the installation answers again.`);
    }
    if (words.length) message(words.join(" "));
  } catch (error) {
    message(`An interrupted move could not be finished. ${refusalText(error)}`);
  } finally {
    running = null;
    if (again) reconciledFor = null;
    client.setContentBusy(false);
    client.refreshContent();
  }
}

// Draws the explorer's buttons with the screen.
export function draw(state) {
  const level = state.level;
  // The board's own storage makes folders at its root, once it is known whether the card may
  // be written, and in its folders; the card at its levels while it may be written.
  const offered = state.status?.clockMode !== "only" && ((level.id === null && cardSettled(state)) || level.storage === "internal" || cardWritable(state));
  for (const id of ["new-folder", "new-playlist-folder"]) {
    const button = byId(id);
    button.hidden = !offered;
    button.disabled = running !== null || client.contentBusy() || state.link !== "answers";
  }
  const storage = level.id === null ? (cardWritable(state) ? "external" : "internal") : level.storage === "internal" ? "internal" : "external";
  byId("new-folder").title = `Makes a folder in ${moves.label(storage, level.path)}`;
  reconcile(state);
}

export function start(options) {
  message = options.message;
  redraw = options.redraw;
  chosen = options.chosen;
  chosenFolders = options.chosenFolders ?? (() => []);
  done = options.done ?? (() => {});
  byId("new-folder").addEventListener("click", () => openFolder(false));
  byId("new-playlist-folder").addEventListener("click", () => openFolder(true));
  byId("folder-make").addEventListener("click", makeFolder);
  byId("folder-storage").addEventListener("change", showWhere);
  byId("folder-cancel").addEventListener("click", closeFolder);
  byId("folder-name").addEventListener("keydown", (event) => {
    if (event.key === "Enter") makeFolder();
  });
  byId("move-selected").addEventListener("click", openMove);
  byId("move-storage").addEventListener("change", chooseDestination);
  byId("move-folder").addEventListener("change", chooseDestination);
  byId("move-go").addEventListener("click", runMove);
  byId("move-cancel").addEventListener("click", closeMove);
  byId("move-stop").addEventListener("click", () => {
    if (running !== null) running.stop = true;
  });
}
