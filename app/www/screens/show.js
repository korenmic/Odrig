// Animations: what the installation does, power and brightness, the capacity of each
// storage, and the one list of animations, each row with its storage badge and its menu.

import * as client from "../client.js";
import * as capacity from "../capacity.js";
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

// A size in kilobytes of 1,000 bytes, rounded up, so that a small file is never 0.
export function kilobytes(bytes) {
  return String(Math.ceil(bytes / 1000));
}

// What plays, in words: the playlist, a cycle by its id, or nothing.
function playing(status) {
  if (status.error !== null) {
    return messages.ofInvalidShow(status.error);
  }
  if (status.playing === "all") {
    return "Playlist";
  }
  return status.playing === null ? "Nothing plays" : `Cycle ${status.playing}`;
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
  meta.textContent = `${animation.id} \u00b7 ${kilobytes(animation.bytes)} KB`;
  play.append(name, meta);
  play.setAttribute("aria-label", `Play ${animation.id} ${animation.file}`);
  play.addEventListener("click", () => client.play(animation.id));
  const note = document.createElement("span");
  note.className = "row-state";
  const badge = document.createElement("span");
  badge.className = `badge ${isExternal(animation) ? "ex" : "in"}`;
  badge.textContent = isExternal(animation) ? "ex" : "in";
  const where = isExternal(animation) ? "External storage, read-only" : "Internal storage";
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
  return made;
}

// Shows the rows anew only when the list is another one, so that a press is never lost
// to a reply that arrives.
function drawRows(animations) {
  const place = byId("animations-list");
  const shown = [...place.querySelectorAll(":scope > .row")];
  const same =
    shown.length === animations.length &&
    shown.every((made, at) => made.dataset.id === String(animations[at].id) && made.dataset.file === animations[at].file &&
      made.dataset.external === String(isExternal(animations[at])) && made.dataset.editable === String(isEditable(animations[at])) &&
      made.querySelector(".meta").textContent.endsWith(`${kilobytes(animations[at].bytes)} KB`));
  if (!same) {
    place.replaceChildren(...animations.map(row));
  }
}

// Whether the target can be asked to change something now.
export function answers() {
  return client.state.link === "answers";
}

function rowsState(state, animations) {
  const onTheLeds = state.status === null || state.status.playing === null ? null : state.status.animation;
  const version = client.targetVersion();
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
    byId("playing").textContent = playing(status);
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
  const animations = shownOrder(state);
  // A row that is held keeps the rows as they are until it is let go.
  if (!reorder.dragging()) {
    drawRows(animations);
    rowsState(state, animations);
  }
  byId("none").hidden = state.animations === null || animations.length > 0;
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
  selection.start({message, redraw});
  reorder.start({message, redraw, shownOrder});
  extend({menu: reorder.menu, draw: reorder.draw, order: reorder.order});
  tests.start({message, isVisible});
  extend({draw: tests.draw});
  byId("on").addEventListener("click", () => client.switchOn());
  byId("off").addEventListener("click", () => client.switchOff());
  byId("play-all").addEventListener("click", () => client.playAll());
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
