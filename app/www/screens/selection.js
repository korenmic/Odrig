// The selection of internal animations in the list, and the removal of one animation or
// of the selected ones, each asked about first.

import * as client from "../client.js";
import {Refusal} from "../commands.js";
import * as messages from "../messages.js";
import * as filters from "./filters.js";

// The most ids one `remove many` carries.
const BATCH = 32;

let selecting = false;
const selected = new Set();
// The question that is open: `{animation}` for one, `{animations}` for the selected ones,
// with the target it was asked for; or null.
let asked = null;
let deleting = false;
let awaitingRefresh = null;
let version = -1;
let message = () => {};
let redraw = () => {};
// Whether an animation is in the level the screen shows.
let visible = () => true;

function byId(id) {
  return document.getElementById(id);
}

// Whether an animation can be selected: an internal one of a target that reports its
// inclusion, in the level the screen shows, which the filters show.
function selectable(item) {
  return typeof item.ignored === "boolean" && item.external !== true && visible(item) && filters.matches(item);
}

// Whether a deletion, a refresh after one, an upload or the link keeps the list's
// mutations off.
export function locked() {
  return deleting || awaitingRefresh !== null || client.contentBusy() || client.state.link !== "answers";
}

export function has(id) {
  return selected.has(id);
}

export function isSelecting() {
  return selecting;
}

// Whether a deletion is under way or waits for the list it changed.
export function busy() {
  return deleting || awaitingRefresh !== null;
}

export function choose(id, chosen) {
  if (chosen) selected.add(id);
  else selected.delete(id);
  redraw();
}

// Turns the selection mode on, with an animation selected when one is given.
export function enter(id) {
  selecting = true;
  if (id !== undefined) selected.add(id);
  redraw();
}

function leave() {
  selecting = false;
  selected.clear();
  redraw();
}

function close() {
  asked = null;
  byId("confirm").hidden = true;
}

// Asks whether one animation is to be removed.
export function askOne(animation) {
  if (locked()) return;
  asked = {animation, version: client.targetVersion()};
  byId("confirm-text").textContent = messages.ofRemoval(animation);
  byId("confirm").hidden = false;
}

function askSelected() {
  if (locked() || selected.size === 0) return;
  const animations = client.state.animations.filter((item) => selected.has(item.id));
  asked = {animations, version: client.targetVersion()};
  byId("confirm-text").textContent = `Delete ${animations.length} animations from internal storage? ` + animations.map((item) => `${item.id} ${item.file}`).join(", ");
  byId("confirm").hidden = false;
}

async function deleteSelected(question) {
  const ownVersion = question.version;
  if (ownVersion !== client.targetVersion() || locked()) return;
  const ids = question.animations.map((item) => item.id);
  let done = 0;
  deleting = true;
  client.setContentBusy(true);
  try {
    while (done < ids.length) {
      if (ownVersion !== client.targetVersion() || document.hidden) throw new Error("deletion stopped");
      const batch = ids.slice(done, done + BATCH);
      await client.removeMany(batch);
      if (ownVersion !== client.targetVersion()) return;
      done += batch.length;
      for (const id of batch) selected.delete(id);
      byId("bulk-progress").textContent = `Deleted ${done} of ${ids.length}.`;
    }
    message(`Deleted ${done} animations.`);
  } catch (error) {
    if (ownVersion !== client.targetVersion()) return;
    const detail = error instanceof Refusal ? messages.ofRefusal(error) :
      "No confirmed reply. The last batch may already be deleted. Refreshing the list before another attempt.";
    message(`Deleted ${done} of ${ids.length}. ${detail}`);
  } finally {
    if (ownVersion === client.targetVersion()) {
      deleting = false;
      awaitingRefresh = client.state.listVersion;
      client.setContentBusy(false);
      client.refreshContent();
      redraw();
    }
  }
}

// Draws the selection mode with the screen.
export function draw(state) {
  if (version !== client.targetVersion()) {
    version = client.targetVersion();
    selected.clear();
    selecting = false;
    deleting = false;
    awaitingRefresh = null;
    close();
    byId("bulk-progress").textContent = "";
  }
  const animations = state.animations === null ? [] : state.animations;
  // A row that the list no longer has, or that a filter hides, leaves the selection.
  const ids = new Set(animations.filter(selectable).map((item) => item.id));
  for (const id of selected) if (!ids.has(id)) selected.delete(id);
  if (awaitingRefresh !== null && state.listVersion > awaitingRefresh) awaitingRefresh = null;
  byId("bulk-progress").dataset.refreshing = String(awaitingRefresh !== null);
  const canSelect = animations.some(selectable);
  byId("selection-bar").hidden = !selecting;
  byId("animations-list").classList.toggle("selecting", selecting);
  const mode = byId("select-mode");
  if (mode !== null) {
    mode.hidden = selecting;
    mode.disabled = locked() || !canSelect;
  }
  byId("select-all").disabled = locked() || !canSelect;
  byId("clear-selection").disabled = locked() || selected.size === 0;
  byId("delete-selected").disabled = locked() || selected.size === 0;
  byId("selection-done").disabled = deleting;
}

export function start(options) {
  message = options.message;
  redraw = options.redraw;
  if (options.visible) visible = options.visible;
  byId("select-mode")?.addEventListener("click", () => enter());
  byId("selection-done").addEventListener("click", leave);
  byId("select-all").addEventListener("click", () => {
    for (const item of client.state.animations || []) if (selectable(item)) selected.add(item.id);
    redraw();
  });
  byId("clear-selection").addEventListener("click", () => {
    selected.clear();
    redraw();
  });
  byId("delete-selected").addEventListener("click", askSelected);
  byId("confirm-yes").addEventListener("click", () => {
    const question = asked;
    close();
    if (question === null || question.version !== client.targetVersion()) return;
    if (question.animations) deleteSelected(question);
    else client.remove(question.animation, (removed) => message(messages.ofRemoved(removed)));
  });
  byId("confirm-no").addEventListener("click", close);
}
