// Animations: what the installation does, power and brightness, the capacity of each
// storage, and the one list of animations, one level of the card's folders at a time as
// a file explorer shows them, each row with its storage badge and its menu.

import * as client from "../client.js";
import * as capacity from "../capacity.js";
import * as filters from "./filters.js";
import {Refusal} from "../commands.js";
import {Failure} from "../target.js";
import * as messages from "../messages.js";
import * as reorder from "./reorder.js";
import * as selection from "./selection.js";
import * as tests from "./tests.js";

// The shortest time between two brightness commands while the slider is moved.
const BRIGHTNESS_EVERY_MS = 200;
// How long after a brightness command a status does not move the slider.
const SLIDER_RESTS_MS = 1000;

// Whether the operator holds the slider, the value and the time of the newest brightness
// command, and the timer of one that waits for its time.
let held = false;
let sentValue = null;
let sentAt = -Infinity;
let waiting = null;
// The inclusion changes under way, by id, each with the target it was sent to.
const pending = new Map();
// The row whose menu is open, and the button that opened it.
let menuFor = null;
let menuButton = null;
let visible = false;
let message = () => {};
// What other parts of the screen add to a row's menu and to drawing.
const extensions = {menu: [], draw: [], order: null};

function byId(id) {
  return document.getElementById(id);
}

function say(id, text) {
  const place = byId(id);
  place.textContent = text === null ? "" : text;
  place.hidden = text === null;
}

// Whether an animation is on the external storage. `list` says so; a target that does
// not lists external animations without `ignored`.
export function isExternal(animation) {
  return typeof animation.external === "boolean" ? animation.external : typeof animation.ignored !== "boolean";
}

// Whether the app may change an animation's inclusion or delete it: an internal animation
// of a target that reports its inclusion.
export function isEditable(animation) {
  return !isExternal(animation) && typeof animation.ignored === "boolean";
}

// Whether an animation is on a card the target may write, so that the app may delete it.
function onWritableCard(animation) {
  return isExternal(animation) && capacity.cardWritable(client.state.space);
}

// A size in kilobytes of 1,000 bytes, rounded up, so that a small file is never 0.
export function kilobytes(bytes) {
  return String(Math.ceil(bytes / 1000));
}

// The line under a row's name: its id and its size, or that the size is not known while
// the installation has not read the file whole.
function metaOf(animation) {
  return `${animation.id} \u00b7 ${animation.bytes === null ? "size not read yet" : `${kilobytes(animation.bytes)} KB`}`;
}

// The folder of an animation of the card, read from its path: the part before its last
// `/`, or the root, "", for a loose file and for every animation of the board.
export function folderOf(animation) {
  return isExternal(animation) && animation.file.includes(`/`) ? animation.file.slice(0, animation.file.lastIndexOf(`/`)) : "";
}

// Whether a file of the card lies in a folder of the tree or in one below it.
function under(file, path) {
  return file.startsWith(`${path}/`);
}

// The time left in the window of the current playlist, in words.
export function timeLeft(left) {
  return `${Math.floor(left / 3600)} h ${Math.floor((left % 3600) / 60)} min left`;
}

// What plays, in words: the root playlist, or a folder's by its path, each with the time
// left in its window, the root playing in a folder's place said so; a cycle by its id;
// or nothing.
function playing(status, state) {
  if (status.error !== null) {
    return messages.ofInvalidShow(status.error);
  }
  if (status.playing === null) {
    return "Nothing plays";
  }
  if (status.playing === "all") {
    return state.folders.length > 0 && status.left !== null ? `Playlist \u00b7 ${timeLeft(status.left)}` : "Playlist";
  }
  if (state.cycles.includes(status.playing)) {
    return `Cycle ${status.playing}`;
  }
  const folder = state.folders.find((item) => item.id === status.playing);
  if (folder !== undefined) {
    const shown = status.animation === null || state.animations === null ? undefined : state.animations.find((animation) => animation.id === status.animation);
    const elsewhere = shown !== undefined && !(isExternal(shown) && under(shown.file, folder.playlist));
    const words = `Playlist ${folder.playlist}${elsewhere ? ", the root plays for now" : ""}`;
    return status.left === null ? words : `${words} \u00b7 ${timeLeft(status.left)}`;
  }
  // A number the list has neither as a cycle nor as a folder: a folder of a card just put
  // in, while the list is asked for again; a cycle, for a target without the time left.
  return status.left === null ? `Cycle ${status.playing}` : `Playlist ${status.playing} \u00b7 ${timeLeft(status.left)}`;
}

// The playlist that is current: "" for the root, a folder's path, or null while a cycle
// or nothing plays.
function markedPath(status, state) {
  if (status === null || status.playing === null) {
    return null;
  }
  if (status.playing === "all") {
    return "";
  }
  const folder = state.folders.find((item) => item.id === status.playing);
  return folder === undefined ? null : folder.playlist;
}

// The level shown, as a file explorer shows one folder at a time: the path of the folder
// opened, "" for the root.
let opened = "";

// The parent of a folder's path: the part before its last `/`, the root for a folder of
// the card's folder itself; and a folder's own name, the part after it.
function parentOf(path) {
  return path.includes(`/`) ? path.slice(0, path.lastIndexOf(`/`)) : "";
}

function nameOf(path) {
  return path.includes(`/`) ? path.slice(path.lastIndexOf(`/`) + 1) : path;
}

// The level shown and what it holds: its folder of the list, null at the root; its own
// rows in the shown order and those of them the filters show; and its sub-folders in the
// order of the list, each with the count of the files directly in it.
function levelOf(state, all) {
  const folder = opened === "" ? null : state.folders.find((item) => item.playlist === opened) ?? null;
  const rows = all.filter((animation) => folderOf(animation) === opened);
  const folders = state.folders.filter((item) => parentOf(item.playlist) === opened).map((item) => ({
    path: item.playlist, id: item.id, name: nameOf(item.playlist), count: all.filter((animation) => folderOf(animation) === item.playlist).length,
  }));
  return {path: opened, folder, rows, shown: rows.filter(filters.matches), folders};
}

// The level shown, for the other parts of the screen.
export function shownLevel() {
  return opened;
}

// Enters a folder of the card, or the root for "", as a tap on a folder row or on Back
// does.
export function enter(path) {
  opened = path;
  closeMenu();
  draw(client.state);
}

function countWords(count) {
  return count === 1 ? "1 animation" : `${count} animations`;
}

// The row of a sub-folder of the level: its name, the count of its own files, and a way
// in. It is no row of an animation: the filters, the moves and the selection pass it by.
function folderRow(entry) {
  const made = document.createElement("button");
  made.type = "button";
  made.className = "folder-row";
  made.dataset.path = entry.path;
  made.dataset.id = String(entry.id);
  made.setAttribute("aria-label", `Open folder ${entry.path}`);
  const text = document.createElement("span");
  text.className = "folder-text";
  const name = document.createElement("span");
  name.className = "name";
  name.textContent = entry.name;
  const meta = document.createElement("span");
  meta.className = "meta";
  meta.textContent = countWords(entry.count);
  text.append(name, meta);
  const chevron = document.createElement("span");
  chevron.className = "chevron";
  chevron.setAttribute("aria-hidden", "true");
  chevron.textContent = "\u203a";
  made.append(text, chevron);
  made.addEventListener("click", () => enter(entry.path));
  return made;
}

// The animation on the LEDs: its id, and its file name when the list has it.
function now(status, animations) {
  if (status.animation === null) {
    return null;
  }
  const found = animations === null ? undefined : animations.find((animation) => animation.id === status.animation);
  return found === undefined ? `Now ${status.animation}` : `Now ${found.id} ${found.file}`;
}

// The animations in the order the list shows them: the saved order when another part of
// the screen gives it, else the order of `list`.
export function shownOrder(state) {
  const animations = state.animations === null ? [] : state.animations;
  return extensions.order === null ? animations : extensions.order(state, animations);
}

function row(animation) {
  const made = document.createElement("div");
  made.className = "row";
  made.setAttribute("role", "listitem");
  made.dataset.id = String(animation.id);
  made.dataset.file = animation.file;
  made.dataset.external = String(isExternal(animation));
  made.dataset.editable = String(isEditable(animation));
  made.dataset.writable = String(onWritableCard(animation));
  made.dataset.fault = animation.fault ?? "";
  if (isEditable(animation)) {
    const pick = document.createElement("label");
    pick.className = "pick";
    const check = document.createElement("input");
    check.type = "checkbox";
    check.setAttribute("aria-label", `Select animation ${animation.id} ${animation.file}`);
    check.addEventListener("change", () => selection.choose(animation.id, check.checked));
    pick.append(check);
    made.append(pick);
  }
  const play = document.createElement("button");
  play.type = "button";
  play.className = "play";
  play.dataset.id = String(animation.id);
  const name = document.createElement("span");
  name.className = "name";
  name.textContent = animation.file;
  const meta = document.createElement("span");
  meta.className = "meta";
  meta.textContent = metaOf(animation);
  play.append(name, meta);
  play.setAttribute("aria-label", `Play ${animation.id} ${animation.file}`);
  play.addEventListener("click", () => client.play(animation.id));
  const note = document.createElement("span");
  note.className = "row-state";
  const badge = document.createElement("span");
  badge.className = `badge ${isExternal(animation) ? "ex" : "in"}`;
  badge.textContent = isExternal(animation) ? "ex" : "in";
  const where = !isExternal(animation) ? "Internal storage" : onWritableCard(animation) ? "External storage" : "External storage, read-only";
  badge.setAttribute("role", "img");
  badge.setAttribute("aria-label", where);
  badge.title = where;
  const more = document.createElement("button");
  more.type = "button";
  more.className = "more";
  more.textContent = "\u22ef";
  more.setAttribute("aria-haspopup", "menu");
  more.setAttribute("aria-expanded", "false");
  more.setAttribute("aria-label", `Actions for ${animation.id} ${animation.file}`);
  more.addEventListener("click", (event) => {
    event.stopPropagation();
    if (menuFor === animation.id) {
      closeMenu();
    } else {
      openMenu(animation.id, more);
    }
  });
  made.append(play, note, badge, more);
  if (typeof animation.fault === "string") {
    // An animation whose file had a fault: grayed, its reason in words, and no Play.
    made.classList.add("unavailable");
    play.disabled = true;
    const why = document.createElement("p");
    why.className = "fault";
    why.textContent = messages.ofFault(animation.fault);
    made.append(why);
    // A file of a card the app cannot write is mended on a computer; one it can write is
    // deleted from its menu, or uploaded again under its name.
    if (isExternal(animation) && !onWritableCard(animation)) {
      const mended = document.createElement("p");
      mended.className = "fault";
      mended.textContent = messages.MENDED_ELSEWHERE;
      made.append(mended);
    }
  }
  return made;
}

// What tells a row of the list from another, as the list holds it and as the rows would
// be drawn now.
function rowKey(animation) {
  return [animation.id, animation.file, isExternal(animation), isEditable(animation), onWritableCard(animation), animation.fault ?? "", metaOf(animation)].join("|");
}

function keyOfChild(child) {
  if (child.classList.contains("folder-row")) {
    return `#${child.dataset.path}|${child.dataset.id}`;
  }
  if (!child.classList.contains("row")) {
    return "?";
  }
  return [child.dataset.id, child.dataset.file, child.dataset.external, child.dataset.editable, child.dataset.writable, child.dataset.fault,
    child.querySelector(".meta").textContent].join("|");
}

// Shows the rows and the folder rows of the level anew only when they are others, so that
// a press is never lost to a reply that arrives: the rows the filters show, then the
// sub-folders.
function drawRows(here) {
  const place = byId("animations-list");
  const wanted = [...here.shown.map(rowKey), ...here.folders.map((entry) => `#${entry.path}|${entry.id}`)];
  const shown = [...place.children].map(keyOfChild);
  if (shown.length === wanted.length && shown.every((key, at) => key === wanted[at])) {
    return;
  }
  place.replaceChildren(...here.shown.map((animation) => {
    const made = row(animation);
    made.dataset.group = here.path;
    return made;
  }), ...here.folders.map(folderRow));
}

// Whether the target can be asked to change something now.
export function answers() {
  return client.state.link === "answers";
}

function rowsState(state, animations, here) {
  const onTheLeds = state.status === null || state.status.playing === null ? null : state.status.animation;
  const version = client.targetVersion();
  // The level's head: its title, Back inside a folder, and the mark while its playlist is
  // current; each folder row's count, and its mark when it leads to the current playlist.
  const marked = markedPath(state.status, state);
  byId("level-title").textContent = here.path === "" ? "Root" : here.path;
  byId("level-back").hidden = here.path === "";
  byId("level-head").setAttribute("aria-current", String(marked === here.path));
  for (const made of byId("animations-list").querySelectorAll(":scope > .folder-row")) {
    const entry = here.folders.find((item) => item.path === made.dataset.path);
    if (entry === undefined) {
      continue;
    }
    made.querySelector(".meta").textContent = countWords(entry.count);
    made.setAttribute("aria-current", String(marked !== null && (marked === entry.path || marked.startsWith(`${entry.path}/`))));
  }
  for (const made of byId("animations-list").querySelectorAll(":scope > .row")) {
    const animation = animations.find((item) => String(item.id) === made.dataset.id);
    if (animation === undefined) {
      continue;
    }
    const current = animation.id === onTheLeds;
    made.setAttribute("aria-current", String(current));
    made.querySelector(".play").setAttribute("aria-current", String(current));
    const saving = pending.get(animation.id) === version;
    made.classList.toggle("ignored", animation.ignored === true);
    made.dataset.saving = String(saving);
    const note = made.querySelector(".row-state");
    note.textContent = saving ? "Saving\u2026" : animation.ignored === true ? "\u2298 Ignored" : "";
    note.hidden = note.textContent === "";
    const check = made.querySelector(".pick input");
    if (check) {
      check.checked = selection.has(animation.id);
      check.disabled = selection.locked();
    }
    made.querySelector(".more").disabled = !answers();
  }
}

function draw(state) {
  const counted = capacity.counts(state);
  byId("show-space").textContent = `Internal storage: ${capacity.internal(state.space, counted.internal)}`;
  byId("show-external-space").textContent = capacity.external(state.space, counted.external);
  const status = state.status;
  say("readiness", status === null ? null : messages.ofProgress(status.progress));
  if (status === null) {
    for (const id of ["power", "brightness", "playing", "fps"]) {
      byId(id).textContent = "-";
    }
    say("now", null);
    byId("on").setAttribute("aria-pressed", "false");
    byId("off").setAttribute("aria-pressed", "false");
  } else {
    byId("power").textContent = status.on ? "ON" : "OFF";
    byId("brightness").textContent = `Brightness ${status.brightness}`;
    byId("playing").textContent = playing(status, state);
    say("now", now(status, state.animations));
    byId("fps").textContent = `${status.fps} refreshes a second`;
    byId("on").setAttribute("aria-pressed", String(status.on));
    byId("off").setAttribute("aria-pressed", String(!status.on));
    // A status does not move the slider while it is held, nor right after a command.
    if (!held && performance.now() - sentAt >= SLIDER_RESTS_MS) {
      byId("level").value = String(status.brightness);
      byId("level-number").textContent = String(status.brightness);
    }
  }
  const all = shownOrder(state);
  // A folder gone from the list, with the card or with a new target, brings the list to
  // the root.
  if (opened !== "" && !state.folders.some((item) => item.playlist === opened)) {
    opened = "";
  }
  const here = levelOf(state, all);
  const animations = here.shown;
  filters.draw(state);
  // A row that is held keeps the rows as they are until it is let go.
  if (!reorder.dragging()) {
    drawRows(here);
    rowsState(state, animations, here);
  }
  byId("none").hidden = state.animations === null || all.length > 0;
  byId("filter-empty").hidden = here.rows.length === 0 || animations.length > 0;
  selection.draw(state);
  if (menuFor !== null && !animations.some((animation) => animation.id === menuFor)) {
    closeMenu();
  } else if (menuFor !== null) {
    fillMenu();
  }
  for (const extra of extensions.draw) {
    extra(state);
  }

  const silent = state.link === "no-answer";
  byId("state").classList.toggle("stale", silent);
  byId("now-panel").classList.toggle("stale", silent);
  byId("space-panel").classList.toggle("stale", silent);
  byId("animations-list").classList.toggle("stale", silent);
  say("silent", silent ? messages.ofSilence(Math.floor((Date.now() - (state.heardAt === null ? state.since : state.heardAt)) / 1000)) : null);
  say("silent-why", silent ? messages.ofFailure(state.failure) : null);
}

// Sends an inclusion change and shows it as saving until the target has answered.
async function include(animation, included) {
  const version = client.targetVersion();
  pending.set(animation.id, version);
  draw(client.state);
  try {
    await client.ignore(animation.id, !included);
  } catch (error) {
    if (version === client.targetVersion()) {
      if (error instanceof Refusal) message(messages.ofRefusal(error));
      else if (error instanceof Failure) message(messages.ofFailure(error));
      else message("No confirmed reply. The list is read again before another change.");
    }
  } finally {
    if (pending.get(animation.id) === version) pending.delete(animation.id);
    draw(client.state);
  }
}

// The actions of a row's menu, each `{label, act, disabled, danger}`, or a line of text as
// `{note}`.
function actions(animation) {
  const items = [];
  const free = answers() && !selection.locked();
  if (isEditable(animation)) {
    const saving = pending.get(animation.id) === client.targetVersion();
    items.push(animation.ignored ? {label: "Restore to playlist", act: () => include(animation, true), disabled: !free || saving}
      : {label: "Ignore in playlist", act: () => include(animation, false), disabled: !free || saving});
  }
  for (const extra of extensions.menu) {
    items.push(...extra(animation));
  }
  if (isEditable(animation)) {
    items.push({label: "Select", act: () => selection.enter(animation.id), disabled: !free});
    items.push({label: "Delete", act: () => selection.askOne(animation), disabled: !free, danger: true});
  } else if (onWritableCard(animation)) {
    items.push({label: "Delete", act: () => selection.askOne(animation), disabled: !free, danger: true});
  } else if (isExternal(animation)) {
    items.push({note: "External storage is read-only: this animation cannot be ignored or deleted from the app."});
  } else {
    items.push({note: "This installation's software does not let the app change this animation."});
  }
  return items;
}

function fillMenu() {
  const animation = (client.state.animations || []).find((item) => item.id === menuFor);
  const menu = byId("row-menu");
  if (animation === undefined) {
    closeMenu();
    return;
  }
  const items = actions(animation);
  const key = JSON.stringify(items.map((item) => [item.label, item.note, item.disabled]));
  if (menu.dataset.key === key) {
    return;
  }
  menu.dataset.key = key;
  menu.replaceChildren(...items.map((item) => {
    if (item.note !== undefined) {
      const note = document.createElement("p");
      note.className = "small";
      note.textContent = item.note;
      return note;
    }
    const button = document.createElement("button");
    button.type = "button";
    button.setAttribute("role", "menuitem");
    button.textContent = item.label;
    button.disabled = item.disabled === true;
    if (item.danger) button.classList.add("danger");
    button.addEventListener("click", (event) => {
      event.stopPropagation();
      closeMenu();
      item.act();
    });
    return button;
  }));
}

function placeMenu() {
  const menu = byId("row-menu");
  if (menuButton === null || menu.hidden) return;
  const box = menuButton.getBoundingClientRect();
  const room = document.querySelector("nav").getBoundingClientRect().top;
  menu.style.right = `${Math.max(8, window.innerWidth - box.right)}px`;
  menu.style.top = "";
  menu.style.bottom = "";
  // On a low screen, held sideways, the menu scrolls within the room above the tabs.
  menu.style.maxHeight = `${Math.max(120, room - 16)}px`;
  const height = menu.getBoundingClientRect().height;
  // Below the button when it fits above the tabs, else above it, and always on the screen.
  const below = box.bottom + 4;
  const top = below + height <= room - 8 ? below : box.top - 4 - height;
  menu.style.top = `${Math.max(8, Math.min(top, room - 8 - height))}px`;
}

function openMenu(id, button) {
  closeMenu();
  menuFor = id;
  menuButton = button;
  button.setAttribute("aria-expanded", "true");
  const menu = byId("row-menu");
  delete menu.dataset.key;
  fillMenu();
  if (menuFor === null) return;
  menu.hidden = false;
  placeMenu();
  menu.querySelector("button:not(:disabled)")?.focus({preventScroll: true});
}

export function closeMenu() {
  if (menuButton !== null) {
    menuButton.setAttribute("aria-expanded", "false");
  }
  menuFor = null;
  menuButton = null;
  byId("row-menu").hidden = true;
}

// Sends the slider's value as a brightness command, now or as soon as the shortest time
// since the one before has passed. A value that was the last one sent is not sent again.
function sendLevel() {
  clearTimeout(waiting);
  waiting = null;
  const left = sentAt + BRIGHTNESS_EVERY_MS - performance.now();
  if (left > 0) {
    waiting = setTimeout(sendLevel, left);
    return;
  }
  const value = Number(byId("level").value);
  if (value !== sentValue) {
    sentValue = value;
    sentAt = performance.now();
    client.setBrightness(value);
  }
}

// Lets another part of the screen add actions to a row's menu, draw with the screen, or
// give the order of the rows.
export function extend({menu, draw: drawing, order}) {
  if (menu) extensions.menu.push(menu);
  if (drawing) extensions.draw.push(drawing);
  if (order) extensions.order = order;
}

export function redraw() {
  draw(client.state);
}

export function showing(shown) {
  visible = shown;
  if (!shown) closeMenu();
}

export function isVisible() {
  return visible;
}

// Starts the screen. While the target does not answer, the line that says for how long
// is written again every second.
export function start(options) {
  message = options.message;
  filters.start({redraw});
  selection.start({message, redraw});
  reorder.start({message, redraw, shownOrder, groupOf: folderOf});
  extend({menu: reorder.menu, draw: reorder.draw, order: reorder.order});
  tests.start({message, isVisible});
  extend({draw: tests.draw});
  byId("on").addEventListener("click", () => client.switchOn());
  byId("off").addEventListener("click", () => client.switchOff());
  // The level's button: the root's playlist at the root, the folder's inside one.
  byId("play-all").addEventListener("click", () => {
    const folder = opened === "" ? undefined : client.state.folders.find((item) => item.playlist === opened);
    if (folder === undefined) client.playAll();
    else client.play(folder.id);
  });
  byId("level-back").addEventListener("click", () => enter(parentOf(opened)));
  const level = byId("level");
  level.addEventListener("input", () => {
    held = true;
    byId("level-number").textContent = level.value;
    sendLevel();
  });
  level.addEventListener("change", () => {
    held = false;
    byId("level-number").textContent = level.value;
    // The value at which the slider is let go is always sent: once more when it was
    // sent a while ago, because somebody else may have set another since.
    if (performance.now() - sentAt >= SLIDER_RESTS_MS) {
      sentValue = null;
    }
    sendLevel();
  });
  // A press anywhere else closes the menu of a row, and so does Escape.
  document.addEventListener("click", (event) => {
    if (menuFor !== null && !byId("row-menu").contains(event.target)) {
      closeMenu();
    }
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && menuFor !== null) {
      const button = menuButton;
      closeMenu();
      button?.focus();
    }
  });
  window.addEventListener("resize", placeMenu);
  window.addEventListener("scroll", placeMenu);
  client.watch(draw);
  setInterval(() => {
    if (client.state.link === "no-answer") {
      draw(client.state);
    }
  }, 1000);
}
