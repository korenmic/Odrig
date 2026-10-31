// Clock playback and message settings follow confirmed status from the current target.
import * as client from "../client.js";
import {Refusal} from "../commands.js";

const MODES = ["off", "between", "only"];
const SAVED = {
  off: "Saved: clocks are off.",
  between: "Saved: a clock plays between the animations.",
  only: "Saved: only the Clocks folder plays.",
};
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
  return id === "clocks" ? status?.clockMode : status?.clockMessage;
}

function saved(request) {
  return request.id === "clocks" ? SAVED[request.value] : request.value ?
    "Saved: a complete message plays after each clock." : "Saved: no message after the clocks.";
}

function draw() {
  const state = client.state;
  const status = state.status;
  const known = status !== null && typeof status.clocks === "boolean";
  byId("clocks-panel").hidden = !known;
  let open = false;
  if (sending?.phase === "confirm" && state.statusFresh && state.statusCount > sending.count) {
    const matches = current(status, sending.id) === sending.value;
    said = matches ? saved(sending) : "The target reports a different setting. The setting in force is shown.";
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
  const message = byId("clock-message");
  message.checked = sending?.id === "clock-message" ? sending.value : status?.clockMessage === true;
  message.disabled = !ready || typeof status?.clockMessage !== "boolean";
  words("clocks-support", known && !status.hasClockMode ?
    "This target supports Off and Between animations. Update its firmware for Clocks only." : "");
  const reasons = {
    "playing": "Only the Clocks folder plays. You can browse anywhere.",
    "no-card": "Clocks only is waiting: no external storage is present.",
    "missing-folder": "Clocks only is waiting: the external clocks folder is missing.",
    "no-clocks": "Clocks only is waiting: no included, available clock face can play.",
  };
  words("clocks-state", status?.clockMode === "only" ? reasons[status.clockOnly?.state] ?? "" : "");
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

async function change(id) {
  const state = client.state;
  const status = state.status;
  const value = id === "clocks" ? byId(id).value : byId(id).checked;
  if (sending !== null || state.link !== "answers" || !state.statusFresh || status === null ||
      typeof status.clocks !== "boolean" || id === "clocks" &&
      (!MODES.includes(value) || value === "only" && !status.hasClockMode)) {
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
  for (const id of ["clocks", "clock-message"]) byId(id).addEventListener("change", () => change(id));
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
