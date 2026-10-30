// One edit flow for the slider, numeric value and saved animation preference.
import * as client from "../client.js";
import {Refusal} from "../commands.js";

const EVERY_MS = 200;
const RESTS_MS = 1000;
const RANGE = "The brightness is 0 to 255.";
const REFUSALS = {
  busy: "The target is busy. Try saving brightness again when it finishes.",
  "storage-error": "The target could not save brightness. The confirmed setting is shown.",
  "no-space": "Saved brightness settings are full. Remove an unused preference before adding another.",
  "unknown-id": "This animation is no longer listed. Read fresh status before trying again.",
  stale: "The animation or target changed. The current setting is shown.",
  "show-invalid": "The show is invalid. Fix it before saving brightness.",
  unsupported: "This target does not support saved animation brightness.",
};
let held = false;
let sentValue = null;
let sentAt = -Infinity;
let waiting = null;
let inForce = null;
let edit = null;
let binding = "";
let pending = null;
let unconfirmedAt = -1;
let switching = false;
let modeChanging = false;
let defaultAwaiting = null;
let note = null;
let redraw = () => {};

const byId = (id) => document.getElementById(id);
function say(id, text) {
  byId(id).textContent = text ?? "";
  byId(id).hidden = text === null;
}
function snapshot() {
  const status = client.state.status;
  return {version: client.targetVersion(), animation: status?.animation, file: status?.file,
    override: status?.dimming?.saved != null};
}
function key(of, mode = true) {
  return JSON.stringify([of.version, of.animation, of.file, ...(mode ? [of.override] : [])]);
}
function valueOf(status) {
  return status?.dimming?.value ?? status?.brightness ?? null;
}
function writeLevel(value) {
  inForce = value;
  byId("level-number").value = value === null ? "" : String(value);
}
function showValue(value) {
  writeLevel(value);
  byId("level").value = String(value ?? 0);
}
function unsent() {
  return byId("level-number").value !== (inForce === null ? "" : String(inForce));
}
function typing() {
  return document.activeElement === byId("level-number") && document.body.classList.contains("typing");
}
function cancelEdit() {
  clearTimeout(waiting);
  waiting = null;
  held = false;
  edit = null;
  sentValue = null;
  sentAt = -Infinity;
  switching = false;
  defaultAwaiting?.finish(false);
  defaultAwaiting = null;
}

export function draw(state) {
  const status = state.status;
  const current = snapshot();
  const changed = binding !== key(current);
  if (pending !== null && key(pending.snapshot, false) !== key(current, false)) {
    pending.finish(false);
    pending = null;
  }
  if (changed) {
    binding = key(current);
    cancelEdit();
    note = null;
    unconfirmedAt = -1;
    showValue(valueOf(status));
  }
  if (defaultAwaiting !== null && defaultAwaiting.count !== null &&
      state.statusCount > defaultAwaiting.count && state.link === "answers") {
    const request = defaultAwaiting;
    defaultAwaiting = null;
    request.finish(status.brightness === request.value);
  }
  if (pending !== null && pending.count !== null && state.statusCount > pending.count && state.link === "answers") {
    const request = pending;
    pending = null;
    const confirmed = request.saved === undefined ? status.brightness === request.value :
      status.dimming !== null && status.dimming.saved === request.saved;
    note = confirmed ? null : "The setting changed before confirmation. The current value is shown.";
    showValue(valueOf(status));
    request.finish(confirmed);
  }
  const fresh = state.link === "answers" && state.statusFresh && status !== null && state.statusCount > unconfirmedAt;
  const dimming = status?.dimming;
  const known = fresh && dimming != null;
  const canSave = known && status.error === null && status.animation !== null &&
    typeof status.file === "string" && dimming.error === null;
  const box = byId("level-override");
  box.checked = known && dimming.saved !== null;
  box.indeterminate = !fresh;
  box.disabled = !canSave || pending !== null || modeChanging;
  byId("level-label").textContent = current.override ? "This animation\u2019s brightness" : "Default brightness";
  say("level-file", typeof status?.file === "string" ? `Animation ${status.animation}: ${status.file}` : null);
  let explanation = note;
  if (!fresh) explanation = "Brightness setting unknown. Waiting for fresh status.";
  else if (dimming == null) explanation = "This target does not support saved animation brightness. The default can still be changed.";
  else if (dimming.error !== null) explanation = "Saved brightness settings are unreadable. The default is in use; repair the saved settings before saving.";
  else if (!canSave) explanation = "Play an animation with a known file to save its brightness.";
  else if (pending !== null || modeChanging) explanation = "Saving brightness; waiting for confirmed status.";
  say("level-said", explanation);
  byId("level").disabled = pending !== null || (current.override && !canSave);
  byId("level-number").disabled = pending !== null || (current.override && !canSave);
  if (!held && pending === null && performance.now() - sentAt >= RESTS_MS && !unsent() && !typing()) {
    showValue(valueOf(status));
  }
}

// A reply acknowledges the command; only a later status confirms the setting.
function mutate(value, captured, saved) {
  if (pending !== null || document.hidden || !client.state.statusFresh || key(captured) !== key(snapshot())) return Promise.resolve(false);
  clearTimeout(waiting);
  waiting = null;
  return new Promise((finish) => {
    const request = {snapshot: captured, value, saved, count: null, finish};
    pending = request;
    note = null;
    redraw();
    const operation = saved === undefined ? client.brightnessValue(value, captured) :
      saved === null ? client.brightnessDefault(captured.animation, captured) :
        client.brightnessSave(captured.animation, value, captured);
    operation.then(() => {
      if (pending !== request) return;
      request.count = client.state.statusCount;
      redraw();
    }).catch((error) => {
      if (pending !== request) return;
      pending = null;
      unconfirmedAt = client.state.statusCount;
      note = error instanceof Refusal ? (REFUSALS[error.code] ?? "Brightness was not saved. Read fresh status before trying again.") :
        "Brightness result unknown. Read fresh status before trying again.";
      showValue(valueOf(client.state.status));
      finish(false);
      redraw();
    });
  });
}

function sendLevel() {
  clearTimeout(waiting);
  waiting = null;
  const captured = edit ?? snapshot();
  if (key(captured) !== key(snapshot()) || document.hidden) return;
  const value = Number(byId("level").value);
  if (captured.override) {
    if (!held && value !== sentValue) {
      sentValue = value;
      sentAt = performance.now();
      void mutate(value, captured, value);
    }
    return;
  }
  const left = sentAt + EVERY_MS - performance.now();
  if (left > 0) { waiting = setTimeout(sendLevel, left); return; }
  if (value !== sentValue) {
    sentValue = value;
    sentAt = performance.now();
    defaultAwaiting?.finish(false);
    const request = {snapshot: captured, value, count: null, finish: () => {}};
    request.confirmed = new Promise((finish) => { request.finish = finish; });
    defaultAwaiting = request;
    client.setBrightness(value, captured).then((accepted) => {
      if (defaultAwaiting !== request) return;
      if (!accepted) {
        defaultAwaiting = null;
        request.finish(false);
      } else {
        request.count = client.state.statusCount;
      }
    });
  }
}

function numeric() {
  const digits = byId("level-number").value.replace(/[^0-9]/g, "");
  return digits === "" || Number(digits) > 255 ? null : Number(digits);
}
function commitLevel() {
  if (switching || !unsent()) return;
  const value = numeric();
  if (document.hidden || value === null) {
    say("level-range", !document.hidden && byId("level-number").value !== "" ? RANGE : null);
    showValue(inForce);
    return;
  }
  say("level-range", null);
  if (value === inForce) { showValue(inForce); return; }
  showValue(value);
  if (performance.now() - sentAt >= RESTS_MS) sentValue = null;
  sendLevel();
}

async function switchOverride() {
  const box = byId("level-override");
  const enable = box.checked;
  switching = false;
  const captured = snapshot();
  box.checked = captured.override;
  if (pending !== null || modeChanging) return;
  modeChanging = true;
  redraw();
  try {
    if (defaultAwaiting !== null && !(await defaultAwaiting.confirmed)) return;
    if (key(captured) !== key(snapshot())) return;
    if (unsent()) {
      const value = numeric();
      if (value === null) { say("level-range", RANGE); return; }
      showValue(value);
      const confirmed = await mutate(value, captured, captured.override ? value : undefined);
      if (!confirmed || key(captured) !== key(snapshot())) return;
    }
    const status = client.state.status;
    if (status?.dimming == null || status.animation === null || typeof status.file !== "string") return;
    const value = status.dimming.value;
    await mutate(value, snapshot(), enable ? value : null);
  } finally {
    modeChanging = false;
    redraw();
  }
}

export function start(options) {
  redraw = options.redraw;
  const level = byId("level");
  const field = byId("level-number");
  level.addEventListener("input", () => {
    if (edit === null) edit = snapshot();
    held = true;
    const dropped = unsent();
    writeLevel(Number(level.value));
    if (dropped && document.activeElement === field) field.blur();
    say("level-range", null);
    sendLevel();
  });
  level.addEventListener("change", () => {
    if (edit === null) return;
    held = false;
    writeLevel(Number(level.value));
    say("level-range", null);
    if (edit.override || performance.now() - sentAt >= RESTS_MS) sentValue = null;
    sendLevel();
  });
  field.addEventListener("input", () => {
    if (edit === null) edit = snapshot();
    const digits = field.value.replace(/[^0-9]/g, "");
    if (digits !== field.value) field.value = digits;
    say("level-range", null);
    if (digits !== "" && Number(digits) <= 255) level.value = String(Number(digits));
  });
  field.addEventListener("keydown", (event) => { if (event.key === "Enter") commitLevel(); });
  field.addEventListener("change", commitLevel);
  byId("level-override").addEventListener("pointerdown", () => { switching = true; });
  byId("level-override").addEventListener("pointercancel", () => { switching = false; });
  document.addEventListener("pointerup", (event) => {
    if (!event.target.closest('label[for="level-override"]')) switching = false;
  });
  byId("level-override").addEventListener("change", () => { void switchOverride(); });
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) { cancelEdit(); showValue(valueOf(client.state.status)); }
  });
}
