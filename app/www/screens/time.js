import * as client from "../client.js";
import {timing} from "../timing.js";

const byId = id => document.getElementById(id);
const HOUR = /^(?:[01][0-9]|2[0-3]):[0-5][0-9]$/;
let version = -1;
let board = null;
let draft = null;
let visible = false;

function words(id, text) {
  if (byId(id).textContent !== text) byId(id).textContent = text;
}

function valid() {
  return draft !== null && HOUR.test(draft.on) && HOUR.test(draft.off) && draft.on !== draft.off;
}

function draw() {
  const state = timing.state;
  if (version !== client.targetVersion()) {
    version = client.targetVersion();
    board = null;
    draft = null;
  }
  if (state.supported === false) { board = null; draft = null; }
  if (state.board !== null && state.board !== board) { board = state.board; draft = null; }
  const saved = state.supported === true ? state.schedule : null;
  if (saved !== null && (draft === null || !draft.dirty)) draft = {...saved, board, dirty: false};
  const ready = state.connected && state.supported === true;
  const editable = ready && saved !== null && board !== null && saved.error !== "settings-unreadable" && !state.busy;
  byId("time-auto").checked = state.auto;
  byId("time-auto").disabled = state.phase === "saving" || state.phase === "resuming";
  byId("time-refresh").disabled = !ready || state.busy;
  byId("time-sync").disabled = !ready || state.busy;
  byId("schedule-enabled").checked = draft?.enabled === true;
  byId("schedule-enabled").disabled = !editable;
  for (const key of ["on", "off"]) {
    const field = byId(`schedule-${key}`);
    const value = draft?.[key] ?? "";
    if (field.value !== value) field.value = value;
    field.disabled = !editable;
  }
  byId("schedule-save").disabled = !editable || !draft?.dirty || !valid();
  byId("schedule-resume").disabled = !editable || saved?.override === null || draft?.dirty === true;
  const clock = state.supported === true ? state.clock : null;
  words("time-reading", clock?.valid ?
    `Board time: ${new Date((clock.utc + clock.offset) * 1000).toISOString().slice(0, 19).replace("T", " ")} (${clock.zone}). At last refresh.` :
    clock !== null ? "Board time is not set. Scheduled hours are ignored until the time is set." : "Waiting for the board's time.");
  const pending = {reading: "Reading board time and schedule...", preparing: "Preparing this phone's time zone...",
    synchronizing: "Synchronizing board time...", saving: "Saving scheduled hours...", resuming: "Resuming the schedule..."};
  let said = state.busy ? pending[state.phase] : state.supported === false ? "Update the board firmware to use time and scheduled hours." :
    state.error ?? (!state.connected ? "Connect to the board to read or change its time and schedule." : state.message ?? "Ready.");
  if (!state.busy && draft?.dirty) {
    const result = state.error ?? (["synchronized", "zone-updated"].includes(state.lastResult) ? state.message : null);
    const edit = valid() ? "Hours edited. Save to apply them." : "Choose two different valid On and Off times.";
    said = result ? `${result} ${edit}` : edit;
  }
  if (!state.preferenceSaved) said += " This phone could not remember automatic sync; the choice applies for this session.";
  words("time-state", said);
  words("schedule-state", saved === null ? "Waiting for the board's schedule." : saved.error === "settings-unreadable" ?
    "The board's saved schedule could not be read. Refresh before changing it." : saved.override !== null ?
    `Manual ${saved.override === "on" ? "On" : "Off"} is active until Resume schedule.${saved.saved ? "" : " This choice could not be saved and may be lost on restart."}` :
    !saved.enabled ? "Scheduled hours are disabled." : !clock?.valid ? "Scheduled hours are ignored until the board's time is set." :
    `Scheduled hours are active. LEDs are ${saved.power ? "on" : "off"}.`);
}

async function refresh() {
  const asked = client.targetVersion();
  const before = draft;
  if (await timing.refresh() && asked === client.targetVersion() && before === draft) { draft = null; draw(); }
}

async function save() {
  if (!draft?.dirty || !valid()) return;
  const asked = client.targetVersion();
  const before = draft;
  if (await timing.saveSchedule({...draft}) && asked === client.targetVersion() && before === draft) { draft = null; draw(); }
}

export function showing(value) {
  if (value && !visible && !timing.state.busy) void timing.refresh();
  visible = value;
}

export function start() {
  byId("time-auto").addEventListener("change", () => timing.setAuto(byId("time-auto").checked));
  byId("time-refresh").addEventListener("click", refresh);
  byId("time-sync").addEventListener("click", () => timing.syncNow());
  byId("schedule-resume").addEventListener("click", () => timing.resumeSchedule());
  byId("schedule-save").addEventListener("click", save);
  for (const key of ["enabled", "on", "off"]) {
    const field = byId(`schedule-${key}`);
    field.addEventListener(key === "enabled" ? "change" : "input", () => {
      if (draft === null || field.disabled) return;
      draft[key] = key === "enabled" ? field.checked : field.value;
      draft.dirty = true;
      draw();
    });
  }
  timing.watch(draw);
}
