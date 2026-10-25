// Settings' mapping editor. The twenty snakes stand in a fixed column, snake 1 at the top,
// and beside each stands the data pin that drives it. A pin is dragged by its handle, or
// held, up or down between two others: the snakes keep their places, the pins between move
// one place, and every time the dragged pin passes into another place the new assignment is
// saved on the target at once, while the finger is still down.
import * as client from "../client.js";
import {Refusal} from "../commands.js";
import {crc32} from "../crc32.js";

const DEFAULTS = [...Array.from({length: 18}, (_, at) => at + 1), 21, 47];
const SNAKES = 20;
// How long a press on a pin is held before it lifts (its handle lifts it at once), how far
// it may move before that and still be a press, how near the top or the tabs the pointer
// scrolls the page, and how far it scrolls in one frame.
const LIFT_MS = 450;
const SLOP = 8;
const EDGE = 56;
const STEP = 12;

let visible = false;
let ready = false;
let version = -1;
// The target's last reply to `mapping get`.
let latest = null;
// A read the operator asked for is under way.
let pending = false;
// The read every two seconds is under way: it changes nothing until its reply shows that
// the target's mapping changed.
let polling = false;
// The saving of moves: the assignment the target confirmed last and its revision, the one
// wanted now, whether a call is out, and the pin that was moved.
let live = null;
let problem = "";
let note = "";
let fresh = false;
// The press that may become a drag, and once lifted the placeholder and the marks.
let press = null;
// The pin whose handle had the focus when the column was drawn again.
let focused = null;
// A click right after a drag is no press on a handle.
let swallowClick = false;

const byId = id => document.getElementById(id);
const same = (a, b) => a.length === b.length && a.every((value, at) => value === b[at]);
const editable = () => latest?.editable === true && latest.pins.length === SNAKES;
// The pins of snakes 1 to 20 that the column shows.
const shownPins = () => live !== null ? live.wanted ?? live.confirmed : editable() ? latest.pins : [];
const locked = () => pending || !fresh || !editable();
const defaultsAvailable = () => editable() && same([...latest.pins].sort((a, b) => a - b), [...DEFAULTS].sort((a, b) => a - b));
// The revision of an assignment: the CRC-32 of its twenty pin bytes, snake 1 first.
const revisionOf = pins => parseInt(crc32(Uint8Array.from(pins)), 16);

// Sets a text, or a state, only when it differs, so that nothing under a finger changes.
function setText(element, text) {
  if (element.textContent !== text) element.textContent = text;
}

function setHidden(element, hidden) {
  if (element.hidden !== hidden) element.hidden = hidden;
}

function setDisabled(element, disabled) {
  if (element.disabled !== disabled) element.disabled = disabled;
}

function reset() {
  cancel();
  version = client.targetVersion();
  latest = null;
  pending = false;
  polling = false;
  live = null;
  problem = "";
  note = "";
  fresh = false;
  focused = null;
  const column = byId("mapping-rows");
  column.replaceChildren();
  column.dataset.key = "";
}

function card(pin, snake) {
  const item = document.createElement("li");
  item.className = "map-pin";
  item.dataset.pin = String(pin);
  const handle = document.createElement("button");
  handle.type = "button";
  handle.className = "handle";
  handle.textContent = "\u2261";
  handle.setAttribute("aria-label", `Move GPIO ${pin}, now driving snake ${snake}; the arrow keys move it one place`);
  const words = document.createElement("span");
  words.className = "words";
  words.textContent = `GPIO ${pin}`;
  item.append(handle, words);
  return item;
}

function rows() {
  const column = byId("mapping-rows");
  if (!editable()) {
    if (column.childElementCount !== 0) column.replaceChildren();
    column.dataset.key = "";
    return;
  }
  // Nothing is drawn again under a finger that holds a pin.
  if (press !== null && press.lifted) return;
  const pins = shownPins();
  const key = pins.join(",");
  if (column.dataset.key !== key) {
    column.dataset.key = key;
    const snakes = document.createElement("ol");
    snakes.className = "map-snakes";
    snakes.replaceChildren(...pins.map((_, at) => {
      const item = document.createElement("li");
      item.textContent = `Snake ${at + 1} \u00b7 columns ${at * 3 + 1}\u2013${at * 3 + 3}`;
      return item;
    }));
    const moving = document.createElement("ol");
    moving.id = "mapping-pins";
    moving.className = "map-moving";
    moving.replaceChildren(...pins.map((pin, at) => card(pin, at + 1)));
    column.replaceChildren(snakes, moving);
    if (focused !== null) {
      column.querySelector(`.map-pin[data-pin="${focused}"] .handle`)?.focus();
    }
  }
  // While moves are saved after a pin is let go no pin can be taken, but the handles stay
  // enabled: a disabled one would lose the focus.
  column.dataset.locked = String(locked() || (live !== null && press === null));
  const off = !fresh || !editable();
  for (const handle of column.querySelectorAll(".handle")) setDisabled(handle, off);
}

function draw() {
  if (!ready) return;
  rows();
  let summary = "Reading mapping\u2026";
  if (latest !== null && editable()) {
    summary = live !== null && live.sending ? "Saving the mapping\u2026" : pending ? "Reading mapping\u2026" :
      "Drag a pin by \u2261, or hold it, up or down between two others. The snakes keep their places, and the mapping is saved each time the pin takes a new place.";
  }
  setText(byId("mapping-summary"), note || summary);
  const error = problem || (latest !== null && !editable() ? "This editor only supports the 60 \u00d7 60 installation with twenty three-column snakes." : "");
  setText(byId("mapping-error"), error);
  setHidden(byId("mapping-error"), error === "");
  setDisabled(byId("mapping-defaults"), locked() || live !== null || !defaultsAvailable() || same(latest.pins, DEFAULTS));
  setDisabled(byId("mapping-reload"), pending || live !== null);
}

function explanation(error) {
  if (error instanceof Refusal) {
    const messages = {
      "unknown-command": "This target does not support mapping controls yet.",
      "mapping-conflict": "The mapping changed on the target meanwhile. Its saved assignment is shown; move the pin again if it is still needed.",
      "storage-error": "The target could not save its mapping. Its saved assignment is shown.",
      "busy": "The target is busy checking or uploading files. Try again after it finishes.",
      "show-invalid": "The target has an invalid show. Fix its show before changing the mapping.",
      "bad-argument": "The target cannot use this mapping or diagnostic.",
    };
    return messages[error.code] || `The target refused the request: ${error.code}.`;
  }
  return "No confirmed reply. The saved assignment was read again; check it before moving again.";
}

// Reads the target's mapping; `quiet` leaves the editor as it is until the reply, and keeps
// what the last move said went wrong.
async function read(quiet = false) {
  if (!ready || pending || document.hidden) return;
  const asked = version;
  pending = true;
  if (!quiet) draw();
  try {
    const reply = await client.mappingGet();
    if (asked !== version) return;
    latest = reply;
    fresh = true;
    if (!quiet) problem = "";
  } catch (error) {
    if (asked !== version) return;
    if (!quiet) problem = explanation(error);
    fresh = false;
  } finally {
    if (asked === version) {
      pending = false;
      draw();
    }
  }
}

// The read every two seconds while Settings shows: the editor changes only when the target's
// mapping did, never while a pin is held or moves are saved, and a reply that does not come
// changes nothing.
async function poll() {
  if (!ready || pending || polling || press !== null || live !== null || document.hidden) return;
  const asked = version;
  polling = true;
  try {
    const reply = await client.mappingGet();
    if (asked !== version || pending || live !== null) return;
    const changed = latest === null || !fresh || latest.revision !== reply.revision || latest.editable !== reply.editable || !same(latest.pins, reply.pins);
    latest = reply;
    fresh = true;
    if (changed) {
      problem = "";
      draw();
    }
  } catch (_) {
    // The next read, a move or Reload says what the target answers.
  } finally {
    if (asked === version) polling = false;
  }
}

// Asks for an assignment to be saved: at once, or as soon as the call that is out has been
// answered, so that only the latest of several quick moves waits.
function want(pins, moved) {
  if (live === null) {
    live = {confirmed: [...latest.pins], revision: latest.revision, wanted: null, sending: false, version, moved};
  }
  live.wanted = [...pins];
  live.moved = moved;
  problem = "";
  pump();
}

async function pump() {
  if (live === null || live.sending) return;
  const asked = version;
  while (live !== null && live.wanted !== null && !same(live.wanted, live.confirmed)) {
    const pins = live.wanted;
    live.sending = true;
    draw();
    try {
      await client.mappingSet(live.revision, pins);
      if (asked !== version || live === null) return;
      live.confirmed = pins;
      live.revision = revisionOf(pins);
      const snake = pins.indexOf(live.moved) + 1;
      note = live.moved === null ? "Saved: the default assignment." : `Saved: GPIO ${live.moved} drives snake ${snake}.`;
    } catch (error) {
      if (asked !== version || live === null) return;
      problem = explanation(error);
      note = "";
      // A failed save may have reached the target: the drag ends, and the target is read once,
      // never asked again.
      live = null;
      cancel();
      await read(true);
      return;
    }
    if (live !== null) live.sending = false;
  }
  if (live !== null && (press === null || !press.lifted)) finish();
  else draw();
}

// After the last move is saved and the pin let go, the target is read once and shown.
async function finish() {
  live = null;
  await read(true);
}

// Moves a pin to a place of the column and saves.
function moveTo(pin, at) {
  if (locked() || live !== null) return;
  const pins = shownPins();
  const rest = pins.filter((other) => other !== pin);
  rest.splice(Math.max(0, Math.min(at, rest.length)), 0, pin);
  if (same(rest, pins)) return;
  note = "";
  want(rest, pin);
}

function cards() {
  const list = byId("mapping-pins");
  return list === null ? [] : [...list.querySelectorAll(":scope > .map-pin")];
}

// The pins of snakes 1 to 20 as the column stands with the held pin at the placeholder.
function heldPins() {
  const pins = [];
  for (const child of byId("mapping-pins").children) {
    if (child === press.placeholder) pins.push(Number(press.item.dataset.pin));
    else if (child !== press.item && child.classList.contains("map-pin")) pins.push(Number(child.dataset.pin));
  }
  return pins;
}

// Where the page may be scrolled to by a drag: between the bar at the top and the tabs.
function edges() {
  const top = byId("top").getBoundingClientRect().bottom;
  const nav = document.querySelector("nav").getBoundingClientRect().top;
  return {top: Math.max(0, top), bottom: nav};
}

function lift() {
  const item = press.item;
  const box = item.getBoundingClientRect();
  const placeholder = document.createElement("li");
  placeholder.className = "map-placeholder";
  placeholder.style.height = `${box.height}px`;
  placeholder.setAttribute("aria-hidden", "true");
  item.after(placeholder);
  press.lifted = true;
  press.placeholder = placeholder;
  press.offset = press.y - box.top;
  item.classList.add("lifted");
  item.style.left = `${box.left}px`;
  item.style.width = `${box.width}px`;
  item.style.top = `${box.top}px`;
  // Where the other pins stand, in the page, with the placeholder in the held one's place:
  // the held pin lands before the first of them whose middle lies below it.
  press.marks = cards().filter((other) => other !== item).map((other) => {
    const at = other.getBoundingClientRect();
    return {item: other, middle: at.top + window.scrollY + at.height / 2};
  });
  item.setAttribute("aria-grabbed", "true");
  if (navigator.vibrate) {
    try {
      navigator.vibrate(15);
    } catch (_) {
      // A web view without vibration lifts the pin all the same.
    }
  }
  scrolling();
}

// Puts the placeholder where a pin held at this height would land, and saves the
// assignment as soon as it stands in another place.
function place(y) {
  press.item.style.top = `${y - press.offset}px`;
  const inPage = y + window.scrollY;
  const mark = press.marks.find((other) => inPage < other.middle);
  const list = byId("mapping-pins");
  let moved = false;
  if (mark === undefined) {
    if (list.lastElementChild !== press.placeholder) {
      list.append(press.placeholder);
      moved = true;
    }
  } else if (press.placeholder.nextElementSibling !== mark.item) {
    list.insertBefore(press.placeholder, mark.item);
    moved = true;
  }
  if (moved) want(heldPins(), Number(press.item.dataset.pin));
}

// Scrolls the page while the held pin is near the top or the tabs, one step a frame.
function scrolling() {
  if (press === null || !press.lifted) return;
  const {top, bottom} = edges();
  const y = press.lastY;
  let step = 0;
  if (y < top + EDGE) step = -STEP;
  else if (y > bottom - EDGE) step = STEP;
  if (step !== 0) {
    window.scrollBy(0, step);
    place(y);
  }
  press.frame = window.requestAnimationFrame(scrolling);
}

function settle() {
  const item = press.item;
  item.classList.remove("lifted");
  item.removeAttribute("aria-grabbed");
  item.style.left = "";
  item.style.width = "";
  item.style.top = "";
  if (press.placeholder) press.placeholder.remove();
  if (press.frame) window.cancelAnimationFrame(press.frame);
  clearTimeout(press.timer);
}

function swallow() {
  swallowClick = true;
  setTimeout(() => {
    swallowClick = false;
  }, 0);
}

// Lets a held pin go where it stands; what its moves saved stays saved.
function cancel() {
  if (press === null) return;
  if (press.lifted) {
    settle();
    swallow();
  } else {
    clearTimeout(press.timer);
  }
  press = null;
  if (live !== null && !live.sending) finish();
  else draw();
}

function drop() {
  settle();
  press = null;
  swallow();
  // The pin stays where it was let go: its last place was saved, or is being saved.
  if (live !== null && !live.sending) finish();
  else draw();
}

export function showing(shown) {
  visible = shown;
  if (!shown) cancel();
  if (shown) {
    if (latest === null) read();
    else poll();
  }
}

export function start() {
  ready = true;
  const column = byId("mapping-rows");
  column.addEventListener("pointerdown", (event) => {
    const item = event.target instanceof Element ? event.target.closest("#mapping-pins > .map-pin") : null;
    if (item === null || press !== null || locked() || live !== null || (event.pointerType === "mouse" && event.button !== 0)) return;
    note = "";
    press = {pointerId: event.pointerId, item, x: event.clientX, y: event.clientY, lastY: event.clientY, lifted: false};
    if (event.target.closest(".handle") !== null) {
      // The handle lifts the pin at once.
      event.preventDefault();
      lift();
    } else {
      press.timer = setTimeout(() => {
        if (press !== null && !press.lifted) lift();
      }, LIFT_MS);
    }
  });
  document.addEventListener("pointermove", (event) => {
    if (press === null || event.pointerId !== press.pointerId) return;
    press.lastY = event.clientY;
    if (!press.lifted) {
      if (Math.abs(event.clientX - press.x) > SLOP || Math.abs(event.clientY - press.y) > SLOP) {
        // The finger moves before the pin lifts: it scrolls the page.
        clearTimeout(press.timer);
        press = null;
      }
      return;
    }
    event.preventDefault();
    place(event.clientY);
  });
  document.addEventListener("pointerup", (event) => {
    if (press === null || event.pointerId !== press.pointerId) return;
    if (press.lifted) {
      drop();
    } else {
      clearTimeout(press.timer);
      press = null;
    }
  });
  document.addEventListener("pointercancel", (event) => {
    if (press !== null && event.pointerId === press.pointerId) cancel();
  });
  // While a pin is held the page does not scroll under the finger.
  document.addEventListener("touchmove", (event) => {
    if (press !== null && press.lifted) event.preventDefault();
  }, {passive: false});
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && press !== null) cancel();
  });
  column.addEventListener("click", (event) => {
    if (swallowClick) {
      event.stopPropagation();
      event.preventDefault();
    }
  }, true);
  // On a handle the arrow keys move its pin one place and save.
  column.addEventListener("keydown", (event) => {
    const handle = event.target instanceof Element ? event.target.closest(".handle") : null;
    if (handle === null || (event.key !== "ArrowUp" && event.key !== "ArrowDown") || press !== null) return;
    event.preventDefault();
    const pin = Number(handle.closest(".map-pin").dataset.pin);
    const at = shownPins().indexOf(pin);
    focused = pin;
    moveTo(pin, at + (event.key === "ArrowUp" ? -1 : 1));
  });
  column.addEventListener("focusout", () => {
    setTimeout(() => {
      const handle = document.activeElement instanceof Element ? document.activeElement.closest("#mapping-rows .handle") : null;
      focused = handle === null ? null : Number(handle.closest(".map-pin").dataset.pin);
    }, 0);
  });
  byId("mapping-defaults").addEventListener("click", () => {
    if (locked() || live !== null || !defaultsAvailable()) return;
    note = "";
    want(DEFAULTS, null);
  });
  byId("mapping-reload").addEventListener("click", () => {
    note = "";
    read();
  });
  client.watch(() => {
    if (version !== client.targetVersion()) {
      reset();
      if (visible) read();
    }
    draw();
  });
  setInterval(() => {
    if (visible && !document.hidden) poll();
  }, 2000);
}
