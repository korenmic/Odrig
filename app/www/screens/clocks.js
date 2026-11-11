// Clock playback, message and preferred-storage settings follow confirmed status from the
// current target.
import * as client from "../client.js";
import {Refusal} from "../commands.js";

const MODES = ["off", "between", "only"];
const STORAGES = ["sd", "internal"];
const SAVED = {
  off: "Saved: clocks are off.",
  between: "Saved: a clock plays between the animations.",
  only: "Saved: only the Clocks folder plays.",
};
// The words of a target that plays the clocks of both storages, where they differ.
const SAVED_BOTH = {...SAVED, only: "Saved: only the clocks folders play."};
const SAVED_STORAGE = {
  sd: "Saved: matching files play from the SD card.",
  internal: "Saved: matching files play from internal storage.",
};
const DESCRIPTION = "Between animations inserts a clock after every 5 animations or 5 minutes. Clocks only restricts playback to the external clocks folder.";
const DESCRIPTION_BOTH = "Between animations inserts a clock after every 5 animations or 5 minutes. Clocks only restricts playback to the clocks folders.";
const REASONS = {
  "playing": "Only the Clocks folder plays. Browsing stays inside Clocks; leave this mode to browse elsewhere.",
  "no-card": "Clocks only is waiting: no external storage is present.",
  "missing-folder": "Clocks only is waiting: the external clocks folder is missing.",
  "no-clocks": "Clocks only is waiting: no included, available clock face can play.",
};
const REASONS_BOTH = {
  "playing": "Only the clocks folders play. Browsing stays inside Clocks; leave this mode to browse elsewhere.",
  "no-card": "Clocks only is waiting: internal storage has no clocks folder and no external storage is present.",
  "missing-folder": "Clocks only is waiting: neither storage has a clocks folder.",
  "no-clocks": "Clocks only is waiting: no included, available clock face can play.",
};
const OLDER_STORAGE = "This target plays the card's clocks and messages only. Update its firmware to use those of the board's own storage.";
let version = -1;
let sending = null;
let uncertain = null;
let said = "";
let go = () => {};
const byId = (id) => document.getElementById(id);

function words(id, text) {
  const element = byId(id);
  if (element.textContent !== text) element.textContent = text;
  element.hidden = text === "";
}

function current(status, id) {
  return id === "clocks" ? status?.clockMode : id === "clock-storage" ? status?.clockStorage : status?.clockMessage;
}

function saved(request, status) {
  if (request.id === "clocks") return (status?.hasClockStorage ? SAVED_BOTH : SAVED)[request.value];
  if (request.id === "clock-storage") return SAVED_STORAGE[request.value];
  return request.value ? "Saved: a complete message plays after each clock." : "Saved: no message after the clocks.";
}

function draw() {
  const state = client.state;
  const status = state.status;
  const known = status !== null && typeof status.clocks === "boolean";
  const both = status?.hasClockStorage === true;
  byId("clocks-panel").hidden = !known;
  let open = false;
  if (sending?.phase === "confirm" && state.statusFresh && state.statusCount > sending.count) {
    const matches = !status?.clockError && current(status, sending.id) === sending.value;
    said = matches ? saved(sending, status) : "The target reports a different setting. The setting in force is shown.";
    open = matches && sending.id === "clocks" && sending.value === "only" && sending.before !== "only";
    sending = null;
  }
  if (uncertain !== null && state.statusFresh && state.statusCount > uncertain.count) {
    said = "The command reply was not confirmed. The current setting from the target is shown.";
    open = uncertain.id === "clocks" && uncertain.value === "only" && uncertain.before !== "only" && status?.clockMode === "only";
    uncertain = null;
  }
  const ready = known && state.link === "answers" && state.statusFresh && sending === null;
  const mode = byId("clocks");
  mode.value = sending?.id === "clocks" ? sending.value : status?.clockMode ?? "off";
  mode.disabled = !ready;
  mode.querySelector('option[value="only"]').disabled = status?.hasClockMode !== true;
  words("clocks-description", both ? DESCRIPTION_BOTH : DESCRIPTION);
  const storage = byId("clock-storage");
  storage.value = sending?.id === "clock-storage" ? sending.value : both && STORAGES.includes(status.clockStorage) ? status.clockStorage : "sd";
  storage.disabled = !ready || !both || status?.clockError != null;
  words("clock-storage-support", known && !both ? OLDER_STORAGE : "");
  const message = byId("clock-message");
  message.checked = sending?.id === "clock-message" ? sending.value : status?.clockMessage === true;
  message.disabled = !ready || status?.clockError != null || typeof status?.clockMessage !== "boolean";
  words("clocks-support", known && !status.hasClockMode ?
    "This target supports Off and Between animations. Update its firmware for Clocks only." : "");
  words("clocks-state", status?.clockError ?
    "Saved clock settings could not be read. Output stays dark while the board retries. Choose a clock mode to replace the saved setting." :
    status?.clockMode === "only" ? (both ? REASONS_BOTH : REASONS)[status.clockOnly?.state] ?? "" : "");
  words("clocks-said", said);
  if (open) go("animations");
}

function explanation(error) {
  if (error instanceof Refusal) {
    return {
      "busy": "The target is busy checking or uploading files. Try again after it finishes.",
      "show-invalid": "The target has an invalid show. Fix its show before changing the clocks.",
      "storage-error": "The target could not save the setting. The setting in force is shown.",
      "unknown-command": "This target does not support these clock settings yet.",
    }[error.code] || `The target refused the request: ${error.code}.`;
  }
  return "No confirmed reply. The setting in force is shown once the target answers.";
}

// The value a control asks for, or undefined when the control may not send it now.
function wanted(id, status) {
  if (id === "clocks") {
    const value = byId(id).value;
    return MODES.includes(value) && (value !== "only" || status.hasClockMode) ? value : undefined;
  }
  if (id === "clock-storage") {
    const value = byId(id).value;
    return STORAGES.includes(value) && status.hasClockStorage === true && status.clockError == null ? value : undefined;
  }
  return byId(id).checked;
}

async function change(id) {
  const state = client.state;
  const status = state.status;
  if (sending !== null || state.link !== "answers" || !state.statusFresh || status === null ||
      typeof status.clocks !== "boolean") {
    draw();
    return;
  }
  const value = wanted(id, status);
  if (value === undefined) {
    draw();
    return;
  }
  const asked = version;
  const request = {id, value, before: current(status, id), phase: "sending"};
  sending = request;
  uncertain = null;
  said = "";
  draw();
  try {
    if (id === "clocks") await client.clockMode(value);
    else if (id === "clock-storage") await client.clockStorage(value);
    else await client.clockMessage(value);
    if (asked !== version) return;
    request.phase = "confirm";
    request.count = state.statusCount;
    said = "Waiting for the target to confirm its setting\u2026";
  } catch (error) {
    if (asked !== version) return;
    sending = null;
    said = explanation(error);
    if (!(error instanceof Refusal)) uncertain = {...request, count: state.statusCount};
  } finally {
    if (asked === version) draw();
  }
}

export function start(options = {}) {
  go = options.go ?? go;
  for (const id of ["clocks", "clock-storage", "clock-message"]) byId(id).addEventListener("change", () => change(id));
  client.watch(() => {
    if (version !== client.targetVersion()) {
      version = client.targetVersion();
      sending = null;
      uncertain = null;
      said = "";
    }
    draw();
  });
}
