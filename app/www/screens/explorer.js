// The explorer's actions on the list: a new folder at the level shown, of the board's own
// storage or of the card, and the move of the selected files to a storage and a folder the
// operator names in full, each destination shown before anything is sent.

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
let done = () => {};
// The folder dialog's level, the move dialog's files and plan, and the run under way.
let folderAt = null;
let moving = null;
let running = null;
let reconciledFor = null;

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

// Every folder of the card, its root first, by their paths, walked level by level.
async function cardFolders() {
  const found = [""];
  const pending = [null];
  while (pending.length > 0 && found.length < 256) {
    const folder = pending.shift();
    let from = 0;
    do {
      const reply = await client.operation("move", () => commands.list(from, folder));
      for (const row of reply.items) {
        if (typeof row.playlist === "string" && row.external === true && !found.includes(row.playlist)) {
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
  if (storage === "internal") {
    return (await client.uploadSnapshot({path: "", id: null})).root;
  }
  const level = folder ? await levelId(folder) : null;
  return (await client.uploadSnapshot({path: folder, id: level})).items;
}

// The id of the card's folder with this path, or null when there is none.
async function levelId(path) {
  return (await moves.folderId(client.operation, path, "external")) ?? null;
}

function drawPlan() {
  const list = byId("move-preview");
  list.replaceChildren();
  if (moving === null || moving.plan === null) return;
  for (const entry of moving.plan) {
    const item = document.createElement("li");
    const line = document.createElement("span");
    line.textContent = `${moves.label(entry.source.external === true ? "external" : "internal", entry.source.file)} \u2192 ${moves.label(entry.storage, entry.path)}`;
    item.append(line);
    if (entry.skip !== null) {
      item.classList.add("skipped");
      const why = document.createElement("span");
      why.className = "small";
      why.textContent = ` Skipped: ${entry.skip}`;
      item.append(why);
      if (/name/.test(entry.skip)) {
        const rename = document.createElement("input");
        rename.type = "text";
        rename.value = entry.name;
        rename.setAttribute("aria-label", `Another name for ${entry.source.file}`);
        rename.addEventListener("change", () => {
          moving.names.set(entry.source.id, rename.value.trim());
          replan();
        });
        item.append(rename);
      }
    }
    list.append(item);
  }
  const count = moving.plan.filter((entry) => entry.skip === null).length;
  byId("move-go").textContent = `Move ${count} file${count === 1 ? "" : "s"}`;
  byId("move-go").disabled = count === 0 || running !== null;
}

function replan() {
  if (moving === null || moving.rows === null) return;
  moving.plan = moves.plan(moving.files, moving.destination, moving.rows, moving.names, moving.blocked);
  drawPlan();
}

async function chooseDestination() {
  if (moving === null) return;
  const storage = byId("move-storage").value;
  const folder = storage === "external" ? byId("move-folder").value : "";
  byId("move-folder").disabled = storage !== "external";
  moving.destination = {storage, folder};
  moving.rows = null;
  moving.plan = null;
  byId("move-go").disabled = true;
  byId("move-preview").replaceChildren();
  const asked = moving;
  try {
    const rows = await destinationRows(storage, folder);
    if (moving !== asked) return;
    moving.rows = rows;
    replan();
  } catch (error) {
    if (moving === asked) byId("move-state").textContent = `The destination could not be read. ${refusalText(error)}`;
  }
}

async function openMove() {
  const files = chosen();
  if (files.length === 0 || running !== null) return;
  moving = {files, names: new Map(), blocked: new Map(), destination: null, rows: null, plan: null, version: client.targetVersion()};
  const reason = cardReason(client.state);
  const storage = byId("move-storage");
  storage.querySelector('option[value="external"]').disabled = reason !== null;
  storage.value = reason === null ? "external" : "internal";
  byId("move-storage-reason").textContent = reason === null ? "" : `${reason} Only Internal storage can take the files now.`;
  byId("move-state").textContent = `${files.length} file${files.length === 1 ? "" : "s"} selected.`;
  const folder = byId("move-folder");
  folder.replaceChildren();
  byId("move-dialog").hidden = false;
  const asked = moving;
  try {
    const blocked = await blockedOf(files);
    if (moving === asked) moving.blocked = blocked;
  } catch (error) {
    byId("move-state").textContent = `The show could not be read. ${refusalText(error)}`;
  }
  if (reason === null) {
    try {
      for (const path of await cardFolders()) {
        const option = document.createElement("option");
        option.value = path;
        option.textContent = `/${path}`;
        folder.append(option);
      }
      folder.value = client.state.level.path && [...folder.options].some((option) => option.value === client.state.level.path) ? client.state.level.path : "";
    } catch (error) {
      byId("move-state").textContent = `The card's folders could not be read. ${refusalText(error)}`;
    }
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
  const skipped = moving.plan.filter((entry) => entry.skip !== null);
  running = {stop: false};
  const progress = byId("move-progress");
  const moved = [];
  const failed = [];
  let unstarted = 0;
  client.setContentBusy("move");
  drawPlan();
  byId("move-stop").hidden = false;
  const context = {
    client,
    address: target.address(),
    report: (text) => { progress.textContent = text; },
    stopped: () => running.stop || version !== client.targetVersion(),
  };
  try {
    for (const [at, entry] of entries.entries()) {
      if (context.stopped()) {
        unstarted = entries.length - at;
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
  } finally {
    running = null;
    byId("move-stop").hidden = true;
    client.setContentBusy(false);
    client.refreshContent();
  }
  const words = [`Moved ${moved.length} of ${entries.length + skipped.length}.`];
  if (skipped.length) words.push(`Skipped ${skipped.length}: ${skipped.map((entry) => entry.source.file).join(", ")}.`);
  if (failed.length) words.push(`Failed ${failed.length}: ${failed.join("; ")}.`);
  if (unstarted) words.push(`Not started after Stop: ${unstarted}.`);
  progress.textContent = words.join(" ");
  message(words.join(" "));
  moving = null;
  byId("move-dialog").hidden = true;
  done();
}

// Finishes the moves a lost reply, a lost link or a restart of the app left for this
// target, once its list answers.
async function reconcile(state) {
  const address = target.address();
  if (reconciledFor === address || running !== null || state.link !== "answers" || state.animations === null || client.contentBusy()) return;
  reconciledFor = address;
  if (moves.pending(address).length === 0) return;
  running = {stop: false};
  client.setContentBusy("move");
  try {
    const {finished, notMoved} = await moves.reconcile({client, address, report: () => {}, stopped: () => false});
    const words = [];
    if (finished.length) words.push(`Finished the interrupted move of ${finished.join(", ")}.`);
    if (notMoved.length) words.push(`Not moved, left where they were: ${notMoved.join(", ")}.`);
    if (words.length) message(words.join(" "));
  } catch (error) {
    reconciledFor = null;
    message(`An interrupted move could not be finished yet. ${refusalText(error)}`);
  } finally {
    running = null;
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
