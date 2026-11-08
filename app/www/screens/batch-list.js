// The list of ready-made files picked several at once on Upload: each file checked by its
// start, named for one destination, and sent as one run of `batch.js`.

import * as batch from "../batch.js";
import * as capacity from "../capacity.js";
import * as client from "../client.js";
import * as destinations from "../upload-destination.js";
import {inspect, prepare} from "../ready.js";
import {fileName, fits} from "../upload.js";
import {kilobytes} from "./show.js";

// The most files the list holds.
export const MOST = 512;
const MEND = "Mend the names marked in the list.";
const TWICE = "Another file of this batch has this name.";

// The list, or null: its destination form, its rows, and the generation of the catalog the
// pick captured.
let list = null;

function byId(id) {
  return document.getElementById(id);
}

export function open() {
  return list !== null;
}

// The names the destination has, by the list the app holds of it: the root's of the
// board's storage, the browsed folder's of either storage, none without a list.
function destinationNames(form) {
  const state = client.state;
  const internal = form.storage === "internal";
  const folder = destinations.folderOf(form);
  const here = state.animations !== null && state.level.path === folder && (folder === "" || (state.level.storage === "internal") === internal);
  if (here) return new Set(state.animations.filter((item) => (item.external === true) !== internal).map((item) => item.file.slice(item.file.lastIndexOf("/") + 1)));
  return new Set(internal && folder === "" ? state.rootNames?.files ?? [] : []);
}

// Names rows against the destination's names and the names the list already holds, in the
// list's order: the rows a pick adds, or every row not edited when the storage changes.
function name(rows) {
  const taken = destinationNames(list.form);
  for (const row of list.rows) {
    if (row.refused === null && !rows.includes(row)) taken.add(row.name);
  }
  for (const row of rows) {
    if (row.refused !== null) continue;
    row.name = fileName(row.file.name, taken, row.ending);
    taken.add(row.name);
  }
}

// Why a row's name cannot be taken, or null.
function why(row) {
  if (row.refused !== null) return null;
  try {
    destinations.pathOf(list.form, row.name);
  } catch (error) {
    return error.message;
  }
  return list.rows.some((other) => other !== row && other.refused === null && other.name === row.name) ? TWICE : null;
}

function sendable() {
  return list.rows.filter((row) => row.refused === null);
}

function sum() {
  return sendable().reduce((total, row) => total + row.size, 0);
}

// Adds files to the list, each checked by its start; a file already listed by its name and
// size is listed once. Gives how many were left out past the most.
async function add(files) {
  const known = new Set(list.rows.map((row) => `${row.file.name}\u0000${row.size}`));
  const fresh = [];
  for (const file of files) {
    const key = `${file.name}\u0000${file.size}`;
    if (known.has(key)) continue;
    known.add(key);
    fresh.push(file);
  }
  const room = MOST - list.rows.length;
  const taken = fresh.slice(0, Math.max(0, room));
  const canvas = client.state.status;
  const captured = list;
  const rows = await Promise.all(taken.map(async (file) => {
    const row = {file, size: file.size, name: file.name, edited: false, ending: /\.odrgx$/i.test(file.name) ? ".odrgx" : ".odrg", refused: null};
    try {
      await inspect(file, canvas);
    } catch (error) {
      row.refused = error.message;
    }
    return row;
  }));
  if (list !== captured) return 0;
  list.rows.push(...rows);
  name(rows);
  return fresh.length - taken.length;
}

// Opens the list with the files of a pick, or adds them to it.
export async function take(files, message) {
  if (batch.running()) {
    message("A batch upload is under way. Choose these when it has ended.");
    return;
  }
  if (list === null || list.ran) {
    list = {form: destinations.capture(client.state, client.targetVersion()), rows: [], ran: false, pressing: false};
  }
  const left = await add([...files]);
  if (left > 0) message(`At most ${MOST} animations are listed; ${left} were left out.`);
  draw(client.state);
}

// Forgets the list, as a pick of one file does.
export function close() {
  if (batch.running()) return;
  list = null;
  draw(client.state);
}

function remove(row) {
  if (list === null || list.ran || batch.running()) return;
  list.rows.splice(list.rows.indexOf(row), 1);
  if (list.rows.length === 0) list = null;
  draw(client.state);
}

// What a row says of its state.
function stateOf(row) {
  if (row.refused !== null) return `refused: ${row.refused}`;
  const run = batch.rowOf(row);
  return run === null ? "waiting" : run;
}

function drawRows(locked) {
  const rows = byId("batch-rows");
  const items = [...rows.children];
  if (items.length !== list.rows.length || items.some((item, at) => item.row !== list.rows[at])) {
    rows.replaceChildren(...list.rows.map((row) => {
      const item = document.createElement("li");
      item.row = row;
      const file = document.createElement("span");
      file.className = "batch-file";
      file.textContent = row.file.name;
      const field = document.createElement("input");
      field.className = "batch-name";
      field.type = "text";
      field.maxLength = 32;
      field.autocomplete = "off";
      field.spellcheck = false;
      field.setAttribute("aria-label", `The name of ${row.file.name} on the installation`);
      field.addEventListener("input", () => {
        row.name = field.value;
        row.edited = true;
        draw(client.state);
      });
      const size = document.createElement("span");
      size.className = "batch-size small";
      size.textContent = `${kilobytes(row.size)} KB`;
      const state = document.createElement("span");
      state.className = "batch-state small";
      const reason = document.createElement("p");
      reason.className = "batch-why small";
      reason.setAttribute("role", "alert");
      const out = document.createElement("button");
      out.type = "button";
      out.className = "batch-remove";
      out.textContent = "Remove";
      out.addEventListener("click", () => remove(row));
      item.append(file, field, size, state, reason, out);
      return item;
    }));
  }
  for (const item of rows.children) {
    const row = item.row;
    const field = item.querySelector(".batch-name");
    const fixed = row.refused !== null || locked;
    field.hidden = fixed;
    item.querySelector(".batch-file").hidden = !fixed;
    if (fixed) item.querySelector(".batch-file").textContent = row.refused !== null ? row.file.name : row.name;
    if (!fixed && field.value !== row.name && document.activeElement !== field) field.value = row.name;
    item.querySelector(".batch-state").textContent = stateOf(row);
    const said = locked ? null : why(row);
    const reason = item.querySelector(".batch-why");
    reason.hidden = said === null;
    reason.textContent = said ?? "";
    item.querySelector(".batch-remove").hidden = locked;
  }
}

// Why the list's button is disabled now, or null.
function lockedReason(state, reason) {
  if (list.rows.some((row) => why(row) !== null)) return MEND;
  const external = list.form.storage === "external";
  const space = state.space;
  const free = space === null ? null : external ? space.external?.free ?? null : space.free;
  if (typeof free === "number" && !fits(sum(), free)) {
    return `These animations need ${kilobytes(sum())} KB and ${external ? "the card" : "the installation"} has ${kilobytes(free)} KB free.`;
  }
  return reason;
}

// Draws the list. `reason` is the Upload screen's reason that an upload cannot begin now,
// or null.
export function draw(state, reason = null) {
  const shown = list !== null;
  byId("batch").hidden = !shown;
  if (!shown) return;
  const running = batch.running();
  const ran = running || list.ran;
  if (!ran) destinations.synchronize(list.form, state.space);
  if (!ran && list.lastStorage !== undefined && list.form.storage !== list.lastStorage) name(list.rows.filter((row) => !row.edited));
  list.lastStorage = list.form.storage;
  const count = sendable().length;
  byId("batch-sum").textContent = `${count} ${count === 1 ? "animation" : "animations"}, ${kilobytes(sum())} KB.`;
  byId("batch-capacity").textContent = list.form.storage === "external" ? capacity.external(state.space, undefined) ?? "" : `Internal storage: ${capacity.internal(state.space, undefined)}`;
  const selector = byId("batch-storage");
  selector.value = list.form.storage;
  selector.options[0].disabled = !destinations.present(state.space);
  selector.disabled = ran;
  byId("batch-destination").textContent = destinations.label(list.form, "");
  byId("batch-destination-reason").textContent = destinations.reason(list.form, state.space);
  drawRows(ran);
  byId("batch-add").hidden = ran;
  const button = byId("batch-upload");
  button.hidden = ran;
  button.textContent = `Upload ${count} ${count === 1 ? "animation" : "animations"}`;
  const said = ran ? null : lockedReason(state, reason);
  button.disabled = said !== null || count === 0 || list.pressing;
  const line = byId("batch-locked-reason");
  line.hidden = said === null;
  line.textContent = said ?? "";
  byId("batch-stop").hidden = !running;
  byId("batch-retry").hidden = running || !list.ran || !list.rows.some((row) => ["failed", "not sent"].includes(batch.outcomeOf(row)));
}

// Moves the list's destination to a storage the operator chose.
export function choose(storage, state) {
  if (list === null || list.ran || batch.running()) return;
  destinations.select(list.form, storage, state.space);
  draw(state);
}

export function rowsOf() {
  return list === null ? [] : list.rows;
}

export function formOf() {
  return list === null ? null : list.form;
}

// Marks the list as sent: from here its names are fixed until a new pick.
export function ran() {
  if (list !== null) list.ran = true;
}

// The item a row gives the run: its bytes read whole at its turn, with every check of a
// single file.
export function itemOf(row) {
  return {
    row,
    name: row.name,
    storage: list.form.storage,
    folder: destinations.folderOf(list.form),
    size: row.size,
    replace: false,
    read: async () => {
      try {
        return await prepare(row.file, client.state.status);
      } catch (error) {
        throw new Error(error instanceof TypeError || error.name === "NotReadableError" || error.name === "NotFoundError" ? "The selected animation changed while it was read." : error.message);
      }
    },
  };
}

// The press of `Upload <n> animations`: a preflight that may move the list's destination,
// as the single form's does, and then the run of every row not refused.
export async function press(message) {
  if (list === null || list.ran || list.pressing || batch.running()) return;
  const form = list.form;
  const external = form.storage === "external";
  list.pressing = true;
  draw(client.state);
  try {
    const fresh = await client.uploadSnapshot(external ? form.level : {path: "", id: null});
    if (destinations.synchronize(form, fresh.space)) {
      draw(client.state);
      message(`The destination changed to ${byId("batch-destination").textContent}. Review it and press Upload again.`);
      return;
    }
  } catch (error) {
    message(destinations.refusalWords(error, external, sum(), client.state));
    return;
  } finally {
    list.pressing = false;
    draw(client.state);
  }
  list.ran = true;
  batch.start(sendable().map(itemOf), form, {guarded: true});
}

// Sends the rows that failed or were not sent once more, with their names and destination.
export function retry() {
  if (list === null || batch.running()) return;
  const rows = list.rows.filter((row) => ["failed", "not sent"].includes(batch.outcomeOf(row)));
  if (rows.length > 0) batch.start(rows.map(itemOf), list.form, {guarded: false});
}
