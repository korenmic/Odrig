// Settings' current limits: the wall's budget, and each snake's while the mapping is the
// installation's twenty snakes, each a field in mA with the installation's estimate of the
// current beside it. Changed text is saved when its field is entered or left; the budgets
// and the estimates are read when Settings is shown and every two seconds while it is, but
// never while a save is out, and a read never changes the text of a field that has the
// focus or text not saved yet.
import * as client from "../client.js";
import {Refusal} from "../commands.js";
import * as mapping from "./mapping.js";

const SNAKES = 20;
const MOST = {wall: 250000, snake: 65535};
const READ_EVERY_MS = 2000;
// The timer's read waits until this long after the last read began, so that the read after
// a save is not followed at once by another.
const READ_AGAIN_MS = 1500;
const NONE = "This installation's software has no current limits.";
const LOWEST = "At this budget every LED is held at its lowest level.";

let visible = false;
let ready = false;
let version = -1;
// The budgets and the estimates as the installation gave them last: `saved`, the wall's
// entry and each leg's by its number, each `{leds, budget, estimate, limited}`, with the
// budgets saved since; null until the first read.
let latest = null;
// Whether the installation's software does not know `limits`.
let none = false;
let reading = false;
let readBegun = -Infinity;
// The save that is out, as `{key, value}`, the saves waiting after it in their order, and
// how many saves were begun.
let saving = null;
let waiting = [];
let begun = 0;
// What the panel says under one field: `{key, text, problem}`, or null.
let said = null;
// The rows on the screen by their key, "wall" or the number of a snake.
const rows = new Map();

const byId = (id) => document.getElementById(id);
const grouped = (number) => String(number).replace(/\B(?=(\d{3})+(?!\d))/g, ",");
const textOf = (value) => (value === 0 ? "" : String(value));
const valueOf = (text) => (text === "" ? 0 : Number(text));
const snakeKeys = () => Array.from({length: SNAKES}, (_, at) => String(at + 1));

// Sets a text, or a state, only when it differs, so that nothing under a finger changes.
function setText(element, text) {
  if (element.textContent !== text) element.textContent = text;
}

function setHidden(element, hidden) {
  if (element.hidden !== hidden) element.hidden = hidden;
}

function entryOf(key) {
  return key === "wall" ? latest.wall : latest.legs.get(Number(key));
}

// The value a field is to have once what was asked for is saved.
function intended(key) {
  const asked = [saving, ...waiting].filter((save) => save !== null && save.key === key);
  return asked.length > 0 ? asked[asked.length - 1].value : entryOf(key).budget;
}

function pending(key) {
  return (saving !== null && saving.key === key) || waiting.some((save) => save.key === key);
}

// Puts a budget into a field as the app shows it: no text for 0.
function put(row, value) {
  const text = textOf(value);
  if (row.input.value !== text) row.input.value = text;
  row.shown = text;
}

function savedSentence(key, value) {
  if (key === "wall") return value === 0 ? "Saved: the wall has no limit." : `Saved: the wall's budget is ${grouped(value)} mA.`;
  return value === 0 ? `Saved: snake ${key} has no limit.` : `Saved: snake ${key}'s budget is ${grouped(value)} mA.`;
}

function rangeSentence(key) {
  return key === "wall" ? `The wall's budget is 0 to ${grouped(MOST.wall)} mA, 0 for no limit. Its saved budget is shown.` :
    `A snake's budget is 0 to ${grouped(MOST.snake)} mA, 0 for no limit. Its saved budget is shown.`;
}

function explanation(error) {
  if (error instanceof Refusal) {
    const messages = {
      "unknown-command": NONE,
      "bad-argument": "The installation cannot take this budget: the value is out of its range, or its mapping has no such snake.",
      "busy": "The installation is busy reading its animations, uploading or rebuilding a catalog. Try again after it finishes.",
      "show-invalid": "The installation has an invalid show. Fix its show before setting a budget.",
      "storage-error": "The installation could not save its budgets. Its saved budget is shown.",
    };
    return messages[error.code] || `The installation refused the budget: ${error.code}.`;
  }
  return "No confirmed reply. The budgets were read again; check this one before setting it again.";
}

// Takes what a field holds: digits only.
function digitsOnly(row) {
  const digits = row.input.value.replace(/[^0-9]/g, "");
  if (digits !== row.input.value) row.input.value = digits;
}

// A field was entered or left: its text is saved when it differs from the value it is to
// have, and only when it is in range.
function commit(row) {
  if (latest === null || none || entryOf(row.key) === undefined) return;
  digitsOnly(row);
  const value = valueOf(row.input.value);
  if (value > MOST[row.key === "wall" ? "wall" : "snake"]) {
    said = {key: row.key, text: rangeSentence(row.key), problem: true};
    put(row, intended(row.key));
    draw();
    return;
  }
  if (value === intended(row.key)) {
    put(row, value);
    return;
  }
  waiting.push({key: row.key, value});
  pump();
}

// Sends the saves one after another, then reads the budgets and the estimates again.
async function pump() {
  if (saving !== null || waiting.length === 0) return;
  const asked = version;
  const save = waiting.shift();
  saving = save;
  begun += 1;
  said = {key: save.key, text: "Saving\u2026", problem: false};
  draw();
  try {
    if (save.key === "wall") await client.limitsWall(save.value);
    else await client.limitsSnake(Number(save.key), save.value);
    if (asked !== version) return;
    const entry = entryOf(save.key);
    if (save.key === "wall") latest.wall = {...entry, budget: save.value};
    else if (entry !== undefined) latest.legs.set(Number(save.key), {...entry, budget: save.value});
    latest.saved = true;
    said = {key: save.key, text: savedSentence(save.key, save.value), problem: false};
    const row = rows.get(save.key);
    if (row !== undefined && valueOf(row.input.value) === save.value) put(row, save.value);
  } catch (error) {
    if (asked !== version) return;
    if (error instanceof Refusal && error.code === "unknown-command") {
      none = true;
      waiting = [];
    }
    said = {key: save.key, text: explanation(error), problem: true};
    // The saved value is shown again, unless other text was typed meanwhile.
    const row = rows.get(save.key);
    if (row !== undefined && entryOf(save.key) !== undefined && !waiting.some((other) => other.key === save.key) && valueOf(row.input.value) === save.value) {
      put(row, entryOf(save.key).budget);
    }
  } finally {
    if (asked === version) {
      saving = null;
      draw();
      if (waiting.length > 0) pump();
      else read();
    }
  }
}

// Reads the budgets and the estimates, unless a save is out or waits: a reply that comes
// after a save was begun may be older than the save, and is dropped.
async function read() {
  if (!ready || none || reading || saving !== null || waiting.length > 0 || document.hidden) return;
  const asked = version;
  const saves = begun;
  reading = true;
  readBegun = performance.now();
  try {
    const reply = await client.limitsRead();
    if (asked !== version || saves !== begun) return;
    latest = {saved: reply.saved, wall: reply.wall, legs: new Map(reply.legs.map((leg) => [leg.leg, leg]))};
  } catch (error) {
    if (asked !== version) return;
    if (error instanceof Refusal && error.code === "unknown-command") none = true;
    // Otherwise what was read last stays; the top bar says whether the target answers.
  } finally {
    if (asked === version) {
      reading = false;
      draw();
    }
  }
}

// A row: the label, the field, the estimate with the mark of a dimmed one, the warning of
// the lowest level and the line of what a save said.
function build(key, id, words) {
  const element = document.createElement("div");
  element.className = "limit";
  element.dataset.key = key;
  const label = document.createElement("label");
  label.htmlFor = id;
  label.textContent = words;
  const line = document.createElement("div");
  line.className = "limit-line";
  const input = document.createElement("input");
  input.id = id;
  input.type = "text";
  input.inputMode = "numeric";
  input.autocomplete = "off";
  input.placeholder = "No limit";
  const estimate = document.createElement("p");
  estimate.className = "limit-estimate";
  const figure = document.createElement("span");
  figure.className = "limit-figure";
  const dimmed = document.createElement("span");
  dimmed.className = "limit-dimmed";
  dimmed.textContent = "Dimmed";
  dimmed.hidden = true;
  estimate.append(figure, " ", dimmed);
  line.append(input, estimate);
  const warning = document.createElement("p");
  warning.className = "limit-warning small";
  warning.textContent = LOWEST;
  warning.hidden = true;
  const told = document.createElement("p");
  told.className = "limit-said";
  told.setAttribute("role", "status");
  told.setAttribute("aria-live", "polite");
  told.hidden = true;
  element.append(label, line, warning, told);
  const row = {key, element, input, figure, dimmed, warning, told, shown: ""};
  input.addEventListener("input", () => digitsOnly(row));
  input.addEventListener("change", () => commit(row));
  // Enter saves only text the operator changed: a field with the focus keeps the text it
  // had when its budget was changed elsewhere, and that text is not sent back.
  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && input.value !== row.shown) commit(row);
  });
  return row;
}

// Whether the rows of the snakes are shown: while the mapping is the installation's twenty
// snakes, and the installation reports each of them.
function snakesShown() {
  const current = mapping.mapping();
  return current !== null && current.editable === true && current.pins.length === SNAKES && snakeKeys().every((key) => latest.legs.has(Number(key)));
}

// Makes the rows the panel has now: none before the first read and for software without
// limits, the wall's, and the snakes' while they are shown.
function layout() {
  const known = latest !== null && !none;
  if (known && !rows.has("wall")) {
    const row = build("wall", "limits-wall-budget", "The wall's budget, mA");
    byId("limits-wall").append(row.element);
    rows.set("wall", row);
  } else if (!known && rows.has("wall")) {
    byId("limits-wall").replaceChildren();
    rows.delete("wall");
  }
  const snakes = known && snakesShown();
  const place = byId("limits-rows");
  if (snakes && !rows.has("1")) {
    const heading = document.createElement("h3");
    heading.textContent = "Each snake's budget, mA";
    const made = snakeKeys().map((key) => {
      const snake = Number(key);
      const row = build(key, `limits-snake-${key}`, `Snake ${snake} \u00b7 columns ${snake * 3 - 2}\u2013${snake * 3}`);
      rows.set(key, row);
      return row.element;
    });
    place.replaceChildren(heading, ...made);
  } else if (!snakes && rows.has("1")) {
    for (const key of snakeKeys()) rows.delete(key);
    place.replaceChildren();
  }
}

function fill(row) {
  const entry = entryOf(row.key);
  setText(row.figure, `Estimate ${grouped(entry.estimate)} mA`);
  setHidden(row.dimmed, !entry.limited);
  setHidden(row.warning, !(entry.budget >= 1 && entry.budget <= entry.leds));
  const told = said !== null && said.key === row.key ? said.text : "";
  setText(row.told, told);
  setHidden(row.told, told === "");
  row.told.classList.toggle("problem", told !== "" && said.problem);
  // A field keeps its text while it has the focus, holds text not saved yet or waits for
  // its save.
  if (document.activeElement !== row.input && row.input.value === row.shown && !pending(row.key)) put(row, entry.budget);
}

function draw() {
  if (!ready) return;
  byId("limits").classList.toggle("stale", client.state.link === "no-answer");
  const summary = none ? NONE : latest === null ? "Reading the current limits\u2026" : "";
  setText(byId("limits-summary"), summary);
  setHidden(byId("limits-summary"), summary === "");
  setHidden(byId("limits-default"), none || latest === null || latest.saved);
  layout();
  for (const row of rows.values()) fill(row);
}

// Forgets what an earlier target said.
function reset() {
  version = client.targetVersion();
  latest = null;
  none = false;
  reading = false;
  readBegun = -Infinity;
  saving = null;
  waiting = [];
  said = null;
  rows.clear();
  byId("limits-wall").replaceChildren();
  byId("limits-rows").replaceChildren();
}

// Says whether Settings is on the screen of the phone; the limits are read each time it
// is shown.
export function showing(shown) {
  visible = shown;
  if (shown) read();
  draw();
}

export function start() {
  ready = true;
  client.watch(() => {
    if (version !== client.targetVersion()) {
      reset();
      if (visible) read();
    }
    draw();
  });
  setInterval(() => {
    if (visible && !document.hidden && performance.now() - readBegun >= READ_AGAIN_MS) read();
  }, READ_EVERY_MS);
}
