// The selection of the files and the folders of both storages in the list, the
// removal of one animation or of the selected internal ones, each asked about first, the
// move of the selected files, and their download.

import * as capacity from "../capacity.js";
import * as client from "../client.js";
import {Refusal} from "../commands.js";
import * as messages from "../messages.js";
import * as downloads from "./downloads.js";
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

// Whether an animation can be selected: a file of either storage, of a target that reports
// its inclusion, in the level the screen shows, which the filters show. A file of a card
// the target may not write is selected by hand, for a download only.
function selectable(item) {
  return typeof item.file === "string" && typeof item.ignored === "boolean" && visible(item) && filters.matches(item);
}

// Whether `Select all` takes an animation: one that can be selected, of the board's storage
// or of a card the target may write.
function takenByAll(item) {
  return selectable(item) && (item.external !== true || capacity.cardWritable(client.state.space));
}

function storageName(external) {
  return external ? "External storage" : "Internal storage";
}

// Whether a folder of either storage can be selected, for a download: one of a target that
// reports its inclusion. The filters pass folders by.
export function folderSelectable(item) {
  return typeof item.playlist === "string" && typeof item.ignored === "boolean";
}

// The selected rows of files, as the list has them.
export function rows() {
  return (client.state.animations || []).filter((item) => selected.has(item.id));
}

// The selected rows of folders, as the list has them.
export function folders() {
  return client.state.folders.filter((item) => selected.has(item.id));
}

// Ends the selection mode after a run that changed the list.
export function finished() {
  leave();
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
  client.setContentBusy("deletion");
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
  const ids = new Set([...animations.filter(selectable), ...state.folders.filter(folderSelectable)].map((item) => item.id));
  for (const id of selected) if (!ids.has(id)) selected.delete(id);
  if (awaitingRefresh !== null && state.listVersion > awaitingRefresh) awaitingRefresh = null;
  byId("bulk-progress").dataset.refreshing = String(awaitingRefresh !== null);
  const canSelect = animations.some(selectable);
  const canSelectAll = animations.some(takenByAll);
  byId("selection-bar").hidden = !selecting;
  byId("animations-list").classList.toggle("selecting", selecting);
  const mode = byId("select-mode");
  if (mode !== null) {
    mode.hidden = selecting;
    mode.disabled = locked() || !canSelect;
  }
  byId("select-all").disabled = locked() || !canSelectAll;
  byId("clear-selection").disabled = locked() || selected.size === 0;
  const chosen = rows();
  const external = chosen.filter((item) => item.external === true).length;
  const chosenFolders = folders().length;
  const externalFolders = folders().filter((item) => item.external === true).length;
  const readOnly = chosen.some((item) => item.external === true) && !capacity.cardWritable(state.space);
  byId("delete-selected").disabled = locked() || selected.size === 0 || external > 0 || chosenFolders > 0;
  byId("delete-selected").title = external > 0 || chosenFolders > 0 ? "Delete selected removes internal animations; clear the folders and the card's files from the selection." : "";
  byId("move-selected").disabled = locked() || chosen.length === 0 || chosenFolders > 0 || readOnly;
  byId("move-selected").title = chosenFolders > 0 ? "Move to\u2026 moves files; clear the folders from the selection." :
    readOnly ? "External storage is read-only: its files can be downloaded, not moved." : "";
  byId("download-selected").disabled = locked() || selected.size === 0 || downloads.busy();
  const files = chosen.length;
  const folderWords = [[chosenFolders - externalFolders, false], [externalFolders, true]].filter(([count]) => count > 0)
    .map(([count, inCard]) => `${count} folder${count === 1 ? "" : "s"} of ${storageName(inCard)}`);
  byId("selection-summary").textContent = selected.size === 0 ? "" :
    `${selected.size} selected: ${files - external} in Internal storage, ${external} in External storage.` +
    (chosenFolders > 0 ? ` ${folderWords.join(" and ")}, with everything in ${chosenFolders === 1 ? "it" : "them"}.` : "");
  byId("selection-done").disabled = deleting;
}

export function start(options) {
  message = options.message;
  redraw = options.redraw;
  if (options.visible) visible = options.visible;
  byId("select-mode")?.addEventListener("click", () => enter());
  byId("selection-done").addEventListener("click", leave);
  byId("select-all").addEventListener("click", () => {
    for (const item of client.state.animations || []) if (takenByAll(item)) selected.add(item.id);
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
