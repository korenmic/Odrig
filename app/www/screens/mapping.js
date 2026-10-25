// Settings' mapping editor. The target's twenty output pins stand in a column in rising
// order, and beside each pin stands the snake it carries. A snake is dragged by its handle,
// or held, up or down and let go between two others: the pins keep their places, the
// snakes between move one place, and the new assignment is saved on the target at once.
import * as client from "../client.js";
import {Refusal} from "../commands.js";

const DEFAULTS = [...Array.from({length: 18}, (_, at) => at + 1), 21, 47];
const SNAKES = 20;
// How long a press on a snake is held before it lifts (its handle lifts it at once), how
// far it may move before that and still be a press, how near the top or the tabs the
// pointer scrolls the page, and how far it scrolls in one frame.
const LIFT_MS = 450;
const SLOP = 8;
const EDGE = 56;
const STEP = 12;

let visible = false;
let ready = false;
let version = -1;
// The target's last reply to `mapping get`.
let latest = null;
// A save, or a read the operator asked for, is under way.
let pending = false;
// The read every two seconds is under way: it changes nothing until its reply shows that
// the target's mapping changed.
let polling = false;
// The order of the snakes shown while a move is saved.
let saving = null;
let problem = "";
let note = "";
let fresh = false;
// The press that may become a drag, and once lifted the placeholder and the marks.
let press = null;
// The snake whose handle had the focus when the list was drawn again.
let focused = null;
// A click right after a drag is no press on a handle.
let swallowClick = false;

const byId = id => document.getElementById(id);
const same = (a, b) => a.length === b.length && a.every((value, at) => value === b[at]);
const editable = () => latest?.editable === true && latest.pins.length === SNAKES;
// The target's pins in rising order: the places of the column.
const places = () => [...latest.pins].sort((a, b) => a - b);
// The snakes in the order of the pins they are on.
const orderOf = pins => [...pins].sort((a, b) => a - b).map(pin => pins.indexOf(pin) + 1);
const shownOrder = () => saving !== null ? saving : editable() ? orderOf(latest.pins) : [];
const locked = () => pending || !fresh || !editable();
const defaultsAvailable = () => editable() && same(places(), [...DEFAULTS].sort((a, b) => a - b));

// The pins of snakes 1 to 20 when the snakes stand in this order beside these pins.
function pinsOf(order, pins) {
  const assigned = new Array(SNAKES);
  order.forEach((snake, at) => {
    assigned[snake - 1] = pins[at];
  });
  return assigned;
}

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
  saving = null;
  problem = "";
  note = "";
  fresh = false;
  focused = null;
  const place = byId("mapping-rows");
  place.replaceChildren();
  place.dataset.key = "";
}

function card(snake, pin) {
  const item = document.createElement("li");
  item.className = "map-snake";
  item.dataset.snake = String(snake);
  item.dataset.pin = String(pin);
  const handle = document.createElement("button");
  handle.type = "button";
  handle.className = "handle";
  handle.textContent = "\u2261";
  handle.setAttribute("aria-label", `Move snake ${snake}, now on GPIO ${pin}; the arrow keys move it one place`);
  const words = document.createElement("span");
  words.className = "words";
  words.textContent = `Snake ${snake} \u00b7 columns ${snake * 3 - 2}\u2013${snake * 3}`;
  item.append(handle, words);
  return item;
}

function rows() {
  const place = byId("mapping-rows");
  if (!editable()) {
    if (place.childElementCount !== 0) place.replaceChildren();
    place.dataset.key = "";
    return;
  }
  // Nothing is drawn again under a finger that holds a snake.
  if (press !== null && press.lifted) return;
  const order = shownOrder();
  const pins = places();
  const key = `${pins.join(",")}|${order.join(",")}`;
  if (place.dataset.key !== key) {
    place.dataset.key = key;
    const column = document.createElement("ol");
    column.className = "map-pins";
    column.replaceChildren(...pins.map((pin) => {
      const item = document.createElement("li");
      item.textContent = `GPIO ${pin}`;
      return item;
    }));
    const snakes = document.createElement("ol");
    snakes.id = "mapping-snakes";
    snakes.className = "map-snakes";
    snakes.replaceChildren(...order.map((snake, at) => card(snake, pins[at])));
    place.replaceChildren(column, snakes);
    if (focused !== null) {
      place.querySelector(`.map-snake[data-snake="${focused}"] .handle`)?.focus();
    }
  }
  // While a move is saved no snake can be taken, but the handles stay enabled: a disabled
  // one would lose the focus.
  place.dataset.locked = String(locked());
  const off = !fresh || !editable();
  for (const handle of place.querySelectorAll(".handle")) setDisabled(handle, off);
}

function draw() {
  if (!ready) return;
  rows();
  let summary = "Reading mapping\u2026";
  if (latest !== null && editable()) {
    summary = saving !== null ? "Saving the mapping\u2026" : pending ? "Reading mapping\u2026" :
      "Drag a snake by \u2261, or hold it, up or down and let it go between two others. The pins keep their places, and each move is saved at once.";
  }
  setText(byId("mapping-summary"), note || summary);
  const error = problem || (latest !== null && !editable() ? "This editor only supports the 60 \u00d7 60 installation with twenty three-column snakes." : "");
  setText(byId("mapping-error"), error);
  setHidden(byId("mapping-error"), error === "");
  setDisabled(byId("mapping-defaults"), locked() || !defaultsAvailable() || same(latest.pins, DEFAULTS));
  setDisabled(byId("mapping-reload"), pending);
}

function explanation(error) {
  if (error instanceof Refusal) {
    const messages = {
      "unknown-command": "This target does not support mapping controls yet.",
      "mapping-conflict": "The mapping changed on the target meanwhile. Its saved assignment is shown; move the snake again if it is still needed.",
      "storage-error": "The target could not save its mapping. Its saved assignment is shown.",
      "busy": "The target is busy checking or uploading files. Try again after it finishes.",
      "show-invalid": "The target has an invalid show. Fix its show before changing the mapping.",
      "bad-argument": "The target cannot use this mapping or diagnostic.",
    };
    return messages[error.code] || `The target refused the request: ${error.code}.`;
  }
  return "No confirmed reply. The saved assignment was read again; check it before moving again.";
}

// A read the operator asked for, or the first one: it says that it reads.
async function read() {
  if (!ready || pending || document.hidden) return;
  const asked = version;
  pending = true;
  draw();
  try {
    const reply = await client.mappingGet();
    if (asked !== version) return;
    latest = reply;
    fresh = true;
    problem = "";
  } catch (error) {
    if (asked !== version) return;
    problem = explanation(error);
    fresh = false;
  } finally {
    if (asked === version) {
      pending = false;
      draw();
    }
  }
}

// The read every two seconds while Settings shows: the editor changes only when the target's
// mapping did, never while a snake is held, and a reply that does not come changes nothing.
async function poll() {
  if (!ready || pending || polling || press !== null || document.hidden) return;
  const asked = version;
  polling = true;
  try {
    const reply = await client.mappingGet();
    if (asked !== version || pending) return;
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

// Saves the snakes in this order beside these pins, on the revision they were read with,
// and shows the order meanwhile.
async function save(order, revision, pins, moved) {
  if (pending) return;
  const asked = version;
  pending = true;
  saving = order;
  problem = "";
  note = "";
  draw();
  try {
    await client.mappingSet(revision, pinsOf(order, pins));
    if (asked !== version) return;
    const reply = await client.mappingGet();
    if (asked !== version) return;
    latest = reply;
    fresh = true;
    note = moved === null ? "Saved: the default assignment." : `Saved: snake ${moved} is on GPIO ${reply.pins[moved - 1]}.`;
  } catch (error) {
    if (asked !== version) return;
    problem = explanation(error);
    // A failed save may have reached the target. Read once; never repeat it.
    try {
      const reply = await client.mappingGet();
      if (asked !== version) return;
      latest = reply;
      fresh = true;
    } catch (_) {
      fresh = false;
    }
  } finally {
    if (asked === version) {
      saving = null;
      pending = false;
      draw();
    }
  }
}

// Moves a snake to a place of the column and saves.
function moveTo(snake, at) {
  if (locked()) return;
  const order = shownOrder();
  const rest = order.filter((other) => other !== snake);
  rest.splice(Math.max(0, Math.min(at, rest.length)), 0, snake);
  if (same(rest, order)) return;
  save(rest, latest.revision, places(), snake);
}

function cards() {
  const list = byId("mapping-snakes");
  return list === null ? [] : [...list.querySelectorAll(":scope > .map-snake")];
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
  // Where the other snakes stand, in the page, with the placeholder in the held one's
  // place: the held snake lands before the first of them whose middle lies below it.
  press.marks = cards().filter((other) => other !== item).map((other) => {
    const at = other.getBoundingClientRect();
    return {item: other, middle: at.top + window.scrollY + at.height / 2};
  });
  item.setAttribute("aria-grabbed", "true");
  if (navigator.vibrate) {
    try {
      navigator.vibrate(15);
    } catch (_) {
      // A web view without vibration lifts the snake all the same.
    }
  }
  scrolling();
}

// Puts the placeholder where a snake held at this height would land.
function place(y) {
  press.item.style.top = `${y - press.offset}px`;
  const inPage = y + window.scrollY;
  const mark = press.marks.find((other) => inPage < other.middle);
  const list = byId("mapping-snakes");
  if (mark === undefined) {
    if (list.lastElementChild !== press.placeholder) list.append(press.placeholder);
  } else if (press.placeholder.nextElementSibling !== mark.item) {
    list.insertBefore(press.placeholder, mark.item);
  }
}

// Scrolls the page while the held snake is near the top or the tabs, one step a frame.
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

// Puts a held snake back where it was, and moves nothing.
function cancel() {
  if (press === null) return;
  if (press.lifted) {
    settle();
    swallow();
  } else {
    clearTimeout(press.timer);
  }
  press = null;
  draw();
}

function drop() {
  const held = press;
  const snake = Number(held.item.dataset.snake);
  // The place is the number of snakes before the placeholder.
  let at = 0;
  for (let other = held.placeholder.previousElementSibling; other !== null; other = other.previousElementSibling) {
    if (other !== held.item && other.classList.contains("map-snake")) at += 1;
  }
  settle();
  press = null;
  swallow();
  const order = held.order.filter((other) => other !== snake);
  order.splice(at, 0, snake);
  if (same(order, held.order)) {
    draw();
    return;
  }
  save(order, held.revision, held.pins, snake);
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
    const item = event.target instanceof Element ? event.target.closest("#mapping-snakes > .map-snake") : null;
    if (item === null || press !== null || locked() || (event.pointerType === "mouse" && event.button !== 0)) return;
    note = "";
    press = {pointerId: event.pointerId, item, x: event.clientX, y: event.clientY, lastY: event.clientY, lifted: false,
      order: shownOrder(), revision: latest.revision, pins: places()};
    if (event.target.closest(".handle") !== null) {
      // The handle lifts the snake at once.
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
        // The finger moves before the snake lifts: it scrolls the page.
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
  // While a snake is held the page does not scroll under the finger.
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
  // On a handle the arrow keys move its snake one place and save.
  column.addEventListener("keydown", (event) => {
    const handle = event.target instanceof Element ? event.target.closest(".handle") : null;
    if (handle === null || (event.key !== "ArrowUp" && event.key !== "ArrowDown") || press !== null) return;
    event.preventDefault();
    const snake = Number(handle.closest(".map-snake").dataset.snake);
    const at = shownOrder().indexOf(snake);
    focused = snake;
    moveTo(snake, at + (event.key === "ArrowUp" ? -1 : 1));
  });
  column.addEventListener("focusout", () => {
    setTimeout(() => {
      const handle = document.activeElement instanceof Element ? document.activeElement.closest("#mapping-rows .handle") : null;
      focused = handle === null ? null : Number(handle.closest(".map-snake").dataset.snake);
    }, 0);
  });
  byId("mapping-defaults").addEventListener("click", () => {
    if (locked() || !defaultsAvailable()) return;
    note = "";
    save(orderOf(DEFAULTS), latest.revision, places(), null);
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
