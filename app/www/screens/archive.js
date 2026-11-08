// The panel Archive on Upload: one zip opened in the page, its animations listed and checked,
// and the ticked ones sent one after another through the run of `batch.js`.

import * as batch from "../batch.js";
import * as capacity from "../capacity.js";
import * as client from "../client.js";
import {kindAndLength} from "../convert.js";
import * as destinations from "../upload-destination.js";
import {prepare} from "../ready.js";
import {fits} from "../upload.js";
import {MOST_ENTRIES, extract, readZip} from "../zip.js";
import {kilobytes} from "./show.js";

const LONGEST_PATH = 100;
const DEEPEST = 3;
const THERE = "A file of this name is there.";

// The archive opened: its name, its bytes, its rows and the destination of its upload.
let archive = null;

function byId(id) {
  return document.getElementById(id);
}

const lastPart = (path) => path.slice(path.lastIndexOf("/") + 1);

// The checks of an animation's bytes, as a ready-made file's, with its kind and its length.
async function facts(bytes, path) {
  const checked = await prepare(new File([bytes], lastPart(path)), client.state.status);
  return {...checked, ...kindAndLength(bytes)};
}

function storage() {
  return archive.form.storage;
}

// The name a row goes under by default: the last part of its path in the board's storage,
// its path on the card.
function defaultName(row) {
  return storage() === "external" ? row.entry.path : lastPart(row.entry.path);
}

// The names the destination's list has.
function existing() {
  const state = client.state;
  if (state.animations === null) return new Set(state.rootNames?.files ?? []);
  if (storage() === "internal") {
    return state.level.path === "" ? new Set(state.animations.filter((item) => item.external !== true).map((item) => item.file)) : new Set(state.rootNames?.files ?? []);
  }
  return new Set(state.animations.filter((item) => item.external === true).map((item) => item.file));
}

// Why a row's name cannot be taken, or null.
function why(row) {
  const name = row.name;
  const part = lastPart(name);
  if (part.length > 32 || !/^[a-z0-9_-][a-z0-9._-]*\.(odrg|odrgx)$/.test(part)) {
    return "Use a filename of at most 32 lowercase letters, digits, dots, - or _, ending in .odrg or .odrgx.";
  }
  if (storage() === "internal" && name.includes("/")) return "The board's storage has no folders: use a name without /.";
  if (new TextEncoder().encode(name).length > LONGEST_PATH) return "The path on the card is longer than 100 bytes; use a shorter name.";
  if (name.split("/").length - 1 > DEEPEST) return "The card takes at most three folders in a path.";
  const twice = archive.rows.some((other) => other !== row && other.ticked && other.name === name);
  return twice ? "Another ticked file of the archive has this name." : null;
}

function tickable(row) {
  return row.facts !== null && row.reason === null;
}

function ticked() {
  return archive.rows.filter((row) => row.ticked && tickable(row));
}

// Opens a zip: reads its entries, and checks each animation, its bytes let go after.
async function open(file, message) {
  if (batch.running()) {
    message("A batch upload is under way. Choose an archive when it has ended.");
    return;
  }
  let bytes;
  let read;
  try {
    bytes = new Uint8Array(await file.arrayBuffer());
    read = readZip(bytes);
  } catch (error) {
    message(`Cannot open this archive: ${error.message}`);
    return;
  }
  const rows = [];
  for (const entry of read.entries) {
    const row = {entry, facts: null, reason: null, passed: false, ticked: false, replace: false, edited: false, name: entry.path};
    if (!/\.(odrg|odrgx)$/i.test(entry.path)) {
      row.passed = true;
      row.reason = "passed over: not an animation";
    } else if (entry.unreadable !== null) {
      row.reason = `unreadable: ${entry.unreadable}`;
    } else {
      try {
        const found = await facts(extract(bytes, entry), entry.path);
        row.facts = {kind: found.kind, ms: found.ms, previewSafe: found.previewSafe};
      } catch (error) {
        row.reason = error.message.startsWith("The entry is") ? `unreadable: ${error.message}` : `refused: ${error.message}`;
      }
    }
    rows.push(row);
  }
  archive = {name: file.name, bytes, rows, form: destinations.capture(client.state, client.targetVersion()), lastStorage: undefined};
  archive.form.level = {path: "", id: null};
  for (const row of rows) {
    row.name = defaultName(row);
    row.ticked = tickable(row);
  }
  if (read.left > 0) message(`At most ${MOST_ENTRIES} entries are read; ${read.left} were left out.`);
  else if (read.tooLarge) message("The archive unpacks to more than 64 MB; the app does not read the entries past that.");
  draw(client.state);
}

function stateOf(row) {
  if (row.reason !== null) return row.reason;
  const run = batch.rowOf(row);
  return run ?? "";
}

function drawRows(locked, there) {
  const list = byId("archive-rows");
  if (list.children.length !== archive.rows.length || [...list.children].some((item, at) => item.row !== archive.rows[at])) {
    list.replaceChildren(...archive.rows.map((row) => {
      const item = document.createElement("li");
      item.row = row;
      const tick = document.createElement("label");
      tick.className = "check";
      const box = document.createElement("input");
      box.type = "checkbox";
      box.className = "archive-tick";
      box.addEventListener("change", () => {
        row.ticked = box.checked;
        draw(client.state);
      });
      const path = document.createElement("span");
      path.className = "archive-path title";
      path.textContent = row.entry.path;
      tick.append(box, path);
      const field = document.createElement("input");
      field.type = "text";
      field.className = "archive-name";
      field.autocomplete = "off";
      field.spellcheck = false;
      field.setAttribute("aria-label", `The name of ${row.entry.path} on the installation`);
      field.addEventListener("input", () => {
        row.name = field.value;
        row.edited = true;
        draw(client.state);
      });
      const facts = document.createElement("span");
      facts.className = "archive-facts small";
      facts.textContent = row.facts === null ? `${kilobytes(row.entry.size)} KB` :
        `${kilobytes(row.entry.size)} KB, ${row.facts.kind}, ${(row.facts.ms / 1000).toFixed(2)} s`;
      const state = document.createElement("span");
      state.className = "archive-state small";
      const said = document.createElement("p");
      said.className = "archive-why small";
      said.setAttribute("role", "alert");
      const replace = document.createElement("label");
      replace.className = "check archive-replace";
      const replaceBox = document.createElement("input");
      replaceBox.type = "checkbox";
      replaceBox.addEventListener("change", () => {
        row.replace = replaceBox.checked;
        draw(client.state);
      });
      const replaceWords = document.createElement("span");
      replaceWords.textContent = "Replace";
      replace.append(replaceBox, replaceWords);
      item.append(tick, field, facts, state, said, replace);
      return item;
    }));
  }
  for (const item of list.children) {
    const row = item.row;
    const box = item.querySelector(".archive-tick");
    box.checked = row.ticked && tickable(row);
    box.disabled = locked || !tickable(row);
    const field = item.querySelector(".archive-name");
    field.hidden = !tickable(row) || locked;
    if (!field.hidden && field.value !== row.name && document.activeElement !== field) field.value = row.name;
    item.querySelector(".archive-state").textContent = stateOf(row);
    const exists = tickable(row) && there.has(row.name);
    const reason = tickable(row) && row.ticked && !locked ? why(row) ?? (exists && !row.replace ? THERE : null) : null;
    const said = item.querySelector(".archive-why");
    said.hidden = reason === null;
    said.textContent = reason ?? "";
    const replace = item.querySelector(".archive-replace");
    replace.hidden = !exists || locked;
    replace.querySelector("input").checked = row.replace;
  }
}

// Why `Upload ticked` is disabled now, or null.
function lockedReason(state, reason, there) {
  const chosen = ticked();
  if (chosen.length === 0) return "Tick the animations to upload.";
  if (chosen.some((row) => why(row) !== null)) return "Mend the names marked in the list.";
  if (chosen.some((row) => there.has(row.name) && !row.replace)) return "Tick Replace beside a name that is there, or rename the file.";
  const external = storage() === "external";
  const free = state.space === null ? null : external ? state.space.external?.free ?? null : state.space.free;
  const sum = chosen.reduce((total, row) => total + row.entry.size, 0);
  if (typeof free === "number" && !fits(sum, free)) return `These animations need ${kilobytes(sum)} KB and ${external ? "the card" : "the installation"} has ${kilobytes(free)} KB free.`;
  return reason;
}

// Draws the panel. `reason` is the Upload screen's reason that an upload cannot begin now.
export function draw(state, reason = null) {
  byId("archive-list").hidden = archive === null;
  if (archive === null) return;
  const running = batch.running() && archive.sent === true;
  if (!running && !archive.ranSince) destinations.synchronize(archive.form, state.space);
  if (archive.lastStorage !== undefined && archive.lastStorage !== storage()) {
    for (const row of archive.rows) if (!row.edited) row.name = defaultName(row);
  }
  archive.lastStorage = storage();
  const there = existing();
  byId("archive-name").textContent = `${archive.name}: ${archive.rows.filter(tickable).length} animations of ${archive.rows.length} entries.`;
  const selector = byId("archive-storage");
  selector.value = storage();
  selector.options[0].disabled = !(destinations.present(state.space) && state.space.external.read_only === false);
  selector.disabled = running;
  const chosen = ticked();
  const sum = chosen.reduce((total, row) => total + row.entry.size, 0);
  byId("archive-sum").textContent = `${chosen.length} ticked, ${kilobytes(sum)} KB. ${storage() === "external" ? capacity.external(state.space, undefined) ?? "" : `Internal storage: ${capacity.internal(state.space, undefined)}`}`;
  drawRows(running, there);
  byId("archive-all").disabled = running;
  byId("archive-none").disabled = running;
  const button = byId("archive-upload");
  button.hidden = running;
  const said = running ? null : lockedReason(state, reason, there);
  button.disabled = said !== null;
  const line = byId("archive-locked-reason");
  line.hidden = said === null;
  line.textContent = said ?? "";
  byId("archive-stop").hidden = !running;
}

function tickAll(value) {
  if (archive === null || batch.running()) return;
  for (const row of archive.rows) row.ticked = value && tickable(row);
  draw(client.state);
}

// Sends the ticked files one after another, each read and checked again at its turn.
function sendTicked() {
  if (archive === null || batch.running()) return;
  const there = existing();
  const bytes = archive.bytes;
  const external = storage() === "external";
  const items = ticked().map((row) => ({
    row,
    name: lastPart(row.name),
    path: external ? row.name : null,
    storage: storage(),
    folder: external ? row.name.slice(0, Math.max(0, row.name.lastIndexOf("/"))) : "",
    size: row.entry.size,
    replace: row.replace && there.has(row.name),
    read: () => facts(extract(bytes, row.entry), row.entry.path),
  }));
  archive.sent = true;
  batch.start(items, archive.form, {guarded: false});
}

export function start({message}) {
  byId("archive-file").addEventListener("change", () => {
    const file = byId("archive-file").files[0];
    byId("archive-file").value = "";
    if (file !== undefined) open(file, message);
  });
  byId("archive-all").addEventListener("click", () => tickAll(true));
  byId("archive-none").addEventListener("click", () => tickAll(false));
  byId("archive-storage").addEventListener("change", () => {
    if (archive === null || batch.running()) return;
    destinations.select(archive.form, byId("archive-storage").value, client.state.space);
    draw(client.state);
  });
  byId("archive-upload").addEventListener("click", sendTicked);
  byId("archive-stop").addEventListener("click", () => batch.stop());
}
