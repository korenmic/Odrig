// Moving animations in the saved order: a long press lifts a row, dragging moves a
// placeholder where it would land, and letting go saves the move on the target. Move up
// and Move down in a row's menu do the same without a long press.

import * as client from "../client.js";
import {Refusal} from "../commands.js";
import {Failure} from "../target.js";
import * as messages from "../messages.js";
import * as selection from "./selection.js";

// How long a press is held before the row lifts, how far it may move before that and
// still be a press, how near the top or the tabs the pointer scrolls the list, and how far
// it scrolls in one frame.
const LIFT_MS = 450;
const SLOP = 8;
const EDGE = 56;
const STEP = 12;

// The press that may become a drag: the pointer, the row and where it began, the timer
// of the lift, and once lifted the placeholder and where the pointer holds the row.
let press = null;
// A click right after a drag is no tap on the row.
let swallowClick = false;
// The move that waits for the target: the order it shows meanwhile, the moved id and the
// target it was sent to; and the order version it waits to be replaced by.
let saving = null;
let message = () => {};
let redraw = () => {};
let shownOrder = () => [];

function byId(id) {
  return document.getElementById(id);
}

// Why the order cannot be changed now, in words, or null when it can.
export function blocked() {
  const state = client.state;
  if (state.link !== "answers") return "The installation does not answer, so the order cannot be changed now.";
  if (!state.orderKnown) return "This installation's software keeps no order of its own: the list is in the order of its show.";
  if (state.order === null) return "The order is being read.";
  if (saving !== null) return "Saving the order\u2026";
  if (selection.busy() || client.contentBusy()) return "The order can be changed again when the upload or the deletion has ended.";
  if (selection.isSelecting()) return "Leave the selection with Done to move animations.";
  return null;
}

export function dragging() {
  return press !== null && press.lifted;
}

// The ids in the order the list shows: the saved order, or the one a move waits to save.
function orderedIds(state, animations) {
  const listed = new Set(animations.map((item) => item.id));
  const ids = saving !== null && saving.version === client.targetVersion() ? saving.ids : state.order === null ? null : state.order.ids;
  if (ids === null || ids.length !== listed.size || !ids.every((id) => listed.has(id))) {
    return null;
  }
  return ids;
}

// The animations in the saved order, when the target keeps one that holds them all.
export function order(state, animations) {
  const ids = orderedIds(state, animations);
  if (ids === null) {
    return animations;
  }
  const byIds = new Map(animations.map((item) => [item.id, item]));
  return ids.map((id) => byIds.get(id));
}

// The ids with one moved before another, or to the end for "end".
function moved(ids, id, before) {
  const rest = ids.filter((other) => other !== id);
  const at = before === "end" ? rest.length : rest.indexOf(before);
  rest.splice(at < 0 ? rest.length : at, 0, id);
  return rest;
}

// Saves a move on the target, and shows it as saving until the target's order comes.
export async function move(id, before) {
  if (blocked() !== null) return;
  const version = client.targetVersion();
  const ids = shownOrder(client.state).map((item) => item.id);
  const next = moved(ids, id, before);
  if (next.every((other, at) => other === ids[at])) return;
  saving = {ids: next, id, version, waits: null};
  redraw();
  try {
    await client.orderMove(id, before);
  } catch (error) {
    if (version === client.targetVersion()) {
      if (error instanceof Refusal) message(messages.ofRefusal(error));
      else if (error instanceof Failure) message(`${messages.ofFailure(error)} The order is read again before another move.`);
      else message("No confirmed reply. The order is read again before another move.");
    }
  } finally {
    if (saving !== null && saving.version === version) {
      // The list and the order are asked for again: the move shows until they come.
      saving.waits = client.state.orderVersion;
    }
    redraw();
  }
}

// The id of the row before which a row goes when it moves one place up or down, or
// "end".
function neighbour(id, step) {
  const ids = shownOrder(client.state).map((item) => item.id);
  const at = ids.indexOf(id);
  if (step < 0) return at > 0 ? ids[at - 1] : null;
  if (at < 0 || at >= ids.length - 1) return null;
  return at + 2 < ids.length ? ids[at + 2] : "end";
}

// The actions of a row's menu that move it.
export function menu(animation) {
  const free = blocked() === null;
  const up = neighbour(animation.id, -1);
  const down = neighbour(animation.id, 1);
  return [
    {label: "Move up", act: () => move(animation.id, up), disabled: !free || up === null},
    {label: "Move down", act: () => move(animation.id, down), disabled: !free || down === null},
  ];
}

// Draws what the list says of moving its rows, and lets a saved move go.
export function draw(state) {
  if (saving !== null && (saving.version !== client.targetVersion() || (saving.waits !== null && state.orderVersion > saving.waits))) {
    saving = null;
  }
  if (saving !== null && saving.version === client.targetVersion()) {
    const row = byId("animations-list").querySelector(`:scope > .row[data-id="${saving.id}"]`);
    if (row !== null) {
      row.dataset.saving = "true";
      const note = row.querySelector(".row-state");
      note.textContent = "Saving\u2026";
      note.hidden = false;
    }
  }
  const why = blocked();
  const list = byId("animations-list");
  list.dataset.movable = String(why === null);
  const animations = state.animations || [];
  byId("order-note").textContent = animations.length < 2 ? "" : why === null ? "Hold a row to move it, or use Move up and Move down in its menu." : why;
  if (press !== null && why !== null && why !== "Saving the order\u2026") {
    cancel();
  }
}

function rowAt(target) {
  const row = target instanceof Element ? target.closest("#animations-list > .row") : null;
  return row !== null && target.closest(".more, .pick") === null ? row : null;
}

function rows() {
  return [...byId("animations-list").querySelectorAll(":scope > .row")];
}

// Where the list may be scrolled to by a drag: between the bar at the top and the tabs.
function edges() {
  const top = byId("top").getBoundingClientRect().bottom;
  const nav = document.querySelector("nav").getBoundingClientRect().top;
  return {top: Math.max(0, top), bottom: nav};
}

function lift() {
  const row = press.row;
  const box = row.getBoundingClientRect();
  const placeholder = document.createElement("div");
  placeholder.className = "placeholder";
  placeholder.style.height = `${box.height}px`;
  placeholder.setAttribute("aria-hidden", "true");
  row.after(placeholder);
  press.lifted = true;
  press.placeholder = placeholder;
  press.offset = press.y - box.top;
  row.classList.add("lifted");
  row.style.left = `${box.left}px`;
  row.style.width = `${box.width}px`;
  row.style.top = `${box.top}px`;
  // Where the other rows stand, in the page, with the placeholder in the held row's place:
  // the held row lands before the first of them whose middle lies below it.
  press.marks = rows().filter((other) => other !== row).map((other) => {
    const at = other.getBoundingClientRect();
    return {row: other, middle: at.top + window.scrollY + at.height / 2};
  });
  row.setAttribute("aria-grabbed", "true");
  if (navigator.vibrate) {
    try {
      navigator.vibrate(15);
    } catch (error) {
      // A web view without vibration lifts the row all the same.
    }
  }
  scrolling();
}

// Puts the placeholder where a row held at this height would land.
function place(y) {
  const held = press.row;
  held.style.top = `${y - press.offset}px`;
  const inPage = y + window.scrollY;
  const mark = press.marks.find((other) => inPage < other.middle);
  const before = mark === undefined ? null : mark.row;
  const list = byId("animations-list");
  if (before === null) {
    if (list.lastElementChild !== press.placeholder) list.append(press.placeholder);
  } else if (press.placeholder.nextElementSibling !== before) {
    list.insertBefore(press.placeholder, before);
  }
}

// Scrolls the page while the held row is near the top or the tabs, one step a frame.
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
  const row = press.row;
  row.classList.remove("lifted");
  row.removeAttribute("aria-grabbed");
  row.style.left = "";
  row.style.width = "";
  row.style.top = "";
  if (press.placeholder) press.placeholder.remove();
  if (press.frame) window.cancelAnimationFrame(press.frame);
  clearTimeout(press.timer);
}

// Puts a lifted row back where it was, and moves nothing.
export function cancel() {
  if (press === null) return;
  if (press.lifted) {
    settle();
    swallowClick = true;
    setTimeout(() => {
      swallowClick = false;
    }, 0);
  } else {
    clearTimeout(press.timer);
  }
  press = null;
  redraw();
}

function drop() {
  const placeholder = press.placeholder;
  const id = Number(press.row.dataset.id);
  let next = placeholder.nextElementSibling;
  while (next !== null && (next === press.row || !next.classList.contains("row"))) next = next.nextElementSibling;
  const before = next === null ? "end" : Number(next.dataset.id);
  settle();
  press = null;
  swallowClick = true;
  setTimeout(() => {
    swallowClick = false;
  }, 0);
  move(id, before);
  redraw();
}

export function start(options) {
  message = options.message;
  redraw = options.redraw;
  shownOrder = options.shownOrder;
  const list = byId("animations-list");
  list.addEventListener("pointerdown", (event) => {
    const row = rowAt(event.target);
    if (row === null || press !== null || blocked() !== null || (event.pointerType === "mouse" && event.button !== 0)) return;
    press = {pointerId: event.pointerId, row, x: event.clientX, y: event.clientY, lastY: event.clientY, lifted: false};
    press.timer = setTimeout(() => {
      if (press !== null && !press.lifted) lift();
    }, LIFT_MS);
  });
  document.addEventListener("pointermove", (event) => {
    if (press === null || event.pointerId !== press.pointerId) return;
    press.lastY = event.clientY;
    if (!press.lifted) {
      if (Math.abs(event.clientX - press.x) > SLOP || Math.abs(event.clientY - press.y) > SLOP) {
        // The finger moves before the row lifts: it scrolls the list.
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
  // While a row is held the page does not scroll under the finger.
  document.addEventListener("touchmove", (event) => {
    if (dragging()) event.preventDefault();
  }, {passive: false});
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && press !== null) cancel();
  });
  list.addEventListener("click", (event) => {
    if (swallowClick) {
      event.stopPropagation();
      event.preventDefault();
    }
  }, true);
}
