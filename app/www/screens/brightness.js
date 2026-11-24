// One edit flow for the slider, numeric value and saved animation preference. A gesture, a
// drag of the slider, an edit of the number field or a press of the box, is bound when it
// begins to the target, the animation and the mode the panel shows, and is applied to them
// when it ends, whatever plays by then.
import * as client from "../client.js";
import {Refusal} from "../commands.js";
import {playingFile} from "../messages.js";

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
const REFUSED = "Brightness was not saved. Read fresh status before trying again.";
let sentValue = null;
let sentAt = -Infinity;
let waiting = null;
let queued = null;
let inForce = null;
let gesture = null;
let binding = "";
let place = null;
let pending = null;
let unconfirmedAt = -1;
let switching = false;
let modeChanging = false;
let defaultAwaiting = null;
let note = null;
let noteKept = false;
let redraw = () => {};

const byId = (id) => document.getElementById(id);
function say(id, text) {
  byId(id).textContent = text ?? "";
  byId(id).hidden = text === null;
}
function snapshot() {
  const status = client.state.status;
  return {version: client.targetVersion(), animation: status?.animation, file: status?.file,
    fileText: typeof status?.file === "string" ? playingFile(status, client.clockStorageOf(status)) : null,
    override: status?.dimming?.saved != null};
}
function key(of) {
  return JSON.stringify([of.version, of.animation, of.file, of.override]);
}
// Whether status names the animation of a snapshot, on its target.
function plays(of) {
  const status = client.state.status;
  return of.version === client.targetVersion() && status?.animation === of.animation && status?.file === of.file;
}
// The place the panel shows without a gesture, the target and the animation status names, or
// null while status names none.
function placeOf(of) {
  return typeof of.animation === "number" && typeof of.file === "string" ? JSON.stringify([of.version, of.animation, of.file]) : null;
}
// Sets the panel's line. A line that is kept stays when the panel next moves to another
// animation; any other goes then.
function line(text, kept = false) {
  note = text;
  noteKept = kept;
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
function isFresh(state = client.state) {
  return state.link === "answers" && state.statusFresh && state.status !== null && state.statusCount > unconfirmedAt;
}

// A gesture begins bound to what the panel shows; one already lasting stays as it is.
function begin(kind) {
  if (gesture === null) {
    gesture = {kind, bound: snapshot(), value: null};
    note = null;
  }
  return gesture;
}
// Ends the gesture without applying it, and says why.
function drop(why) {
  const ended = gesture;
  gesture = null;
  clearTimeout(waiting);
  waiting = null;
  queued = null;
  if (ended !== null) line(`Not saved for ${ended.bound.fileText}: ${why}.`, true);
}
// Ends the gesture and applies its value to what it is bound to.
function finish() {
  const ended = gesture;
  gesture = null;
  if (ended === null) return;
  const {bound, value} = ended;
  if (bound.version !== client.targetVersion()) {
    line(`Not saved for ${bound.fileText}: another installation was chosen.`, true);
  } else if (document.hidden || !isFresh()) {
    line(`Not saved for ${bound.fileText}: the installation did not answer.`, true);
  } else if (bound.override) {
    void mutate(value, bound, value);
  } else {
    if (performance.now() - sentAt >= RESTS_MS) sentValue = null;
    sendDefault(bound, value);
  }
  redraw();
}

// The default, sent at most every EVERY_MS while the slider moves: the last value waits.
function sendDefault(bound, value) {
  queued = {bound, value};
  clearTimeout(waiting);
  waiting = null;
  const left = sentAt + EVERY_MS - performance.now();
  if (left > 0) {
    waiting = setTimeout(flushDefault, left);
    return;
  }
  flushDefault();
}
function flushDefault() {
  waiting = null;
  const next = queued;
  queued = null;
  if (next === null || document.hidden || next.bound.version !== client.targetVersion() || next.value === sentValue) return;
  sentValue = next.value;
  sentAt = performance.now();
  defaultAwaiting?.finish(false);
  const request = {snapshot: next.bound, value: next.value, count: null, finish: () => {}};
  request.confirmed = new Promise((finish) => { request.finish = finish; });
  defaultAwaiting = request;
  client.setBrightness(next.value, next.bound).then((accepted) => {
    if (defaultAwaiting !== request) return;
    if (!accepted) {
      defaultAwaiting = null;
      request.finish(false);
    } else {
      request.count = client.state.statusCount;
    }
  });
}

// The end of a request: the line of what the target keeps, and the controls from status.
function settle(request, confirmed, kept) {
  pending = null;
  const file = request.snapshot.fileText;
  if (request.saved === undefined) {
    line(confirmed ? null : "The setting changed before confirmation. The current value is shown.");
  } else if (confirmed) {
    line(request.saved === null ? `Removed the saved brightness of ${file}.` : `Saved ${request.saved} for ${file}.`);
  } else {
    line(kept === null || kept === undefined ? `${file} keeps no saved brightness.` : `${file} keeps ${kept}.`);
  }
  showValue(valueOf(client.state.status));
  request.finish(confirmed);
  redraw();
}
function fail(request, error, refused) {
  pending = null;
  unconfirmedAt = client.state.statusCount;
  const file = request.snapshot.fileText;
  line(refused && error instanceof Refusal ? `Not saved for ${file}. ${REFUSALS[error.code] ?? REFUSED}` :
    `Brightness for ${file} is unknown: no reply came. It is not sent again.`);
  showValue(valueOf(client.state.status));
  request.finish(false);
  redraw();
}
// A save or a removal is confirmed by status while status names its animation, else by
// `saved <id>`; a default by status.
function confirm(request, status) {
  if (request.saved === undefined) {
    settle(request, status.brightness === request.value, null);
  } else if (plays(request.snapshot)) {
    settle(request, status.dimming?.saved === request.saved, status.dimming?.saved ?? null);
  } else {
    request.reading = true;
    client.brightnessSaved(request.snapshot.animation, request.snapshot).then((reply) => {
      if (pending !== request) return;
      settle(request, reply.brightness === request.saved, reply.brightness);
    }).catch((error) => {
      if (pending !== request) return;
      fail(request, error, false);
    });
  }
}

export function draw(state) {
  const status = state.status;
  const current = snapshot();
  const fresh = isFresh(state);
  if (gesture !== null && gesture.bound.version !== current.version) drop("another installation was chosen");
  else if (gesture !== null && !fresh) drop("the installation did not answer");
  if (pending !== null && pending.snapshot.version !== current.version) {
    pending.finish(false);
    pending = null;
  }
  const currentBinding = JSON.stringify([key(current), state.statusFresh]);
  if (gesture === null && binding !== currentBinding) {
    binding = currentBinding;
    unconfirmedAt = -1;
    const now = placeOf(current);
    if (now !== null && now !== place) {
      if (noteKept) noteKept = false;
      else note = null;
      place = now;
    }
    showValue(valueOf(status));
  }
  if (defaultAwaiting !== null && defaultAwaiting.count !== null &&
      state.statusCount > defaultAwaiting.count && state.link === "answers") {
    const request = defaultAwaiting;
    defaultAwaiting = null;
    request.finish(status.brightness === request.value);
  }
  if (pending !== null && pending.count !== null && !pending.reading && state.statusCount > pending.count && state.link === "answers") {
    confirm(pending, status);
  }
  const view = gesture !== null ? gesture.bound : current;
  const away = gesture !== null && !plays(gesture.bound);
  const dimming = status?.dimming;
  const known = fresh && dimming != null;
  const canSave = known && status.error === null && typeof view.animation === "number" &&
    typeof view.file === "string" && dimming.error === null;
  const box = byId("level-override");
  box.checked = gesture !== null ? view.override : known && dimming.saved !== null;
  box.indeterminate = !fresh;
  box.disabled = !canSave || pending !== null || modeChanging;
  byId("level-label").textContent = view.override ? "This animation\u2019s brightness" : "Default brightness";
  say("level-file", typeof view.file === "string" ? `Animation ${view.animation}: ${view.fileText}${away ? ", no longer playing" : ""}` : null);
  let explanation = note;
  if (!fresh) explanation = "Brightness setting unknown. Waiting for fresh status.";
  else if (dimming == null) explanation = "This target does not support saved animation brightness. The default can still be changed.";
  else if (dimming.error !== null) explanation = "Saved brightness settings are unreadable. The default is in use; repair the saved settings before saving.";
  else if (!canSave) explanation = "Play an animation with a known file to save its brightness.";
  else if (pending !== null || modeChanging) explanation = "Saving brightness; waiting for confirmed status.";
  say("level-said", explanation);
  // A control in use is never disabled under the finger.
  const locked = gesture === null && (pending !== null || (view.override && !canSave));
  byId("level").disabled = locked;
  byId("level-number").disabled = locked;
  if (gesture === null && pending === null && performance.now() - sentAt >= RESTS_MS && !unsent() && !typing()) {
    showValue(valueOf(status));
  }
}

// A reply acknowledges the command; only a later status, or `saved <id>`, confirms the setting.
function mutate(value, captured, saved) {
  if (pending !== null || document.hidden || !client.state.statusFresh || captured.version !== client.targetVersion()) return Promise.resolve(false);
  clearTimeout(waiting);
  waiting = null;
  queued = null;
  return new Promise((finish) => {
    const request = {snapshot: captured, value, saved, count: null, reading: false, finish};
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
      fail(request, error, true);
    });
  });
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
    if (gesture?.kind === "type") gesture = null;
    return;
  }
  say("level-range", null);
  if (value === inForce) {
    showValue(inForce);
    if (gesture?.kind === "type") gesture = null;
    return;
  }
  showValue(value);
  begin("type").value = value;
  finish();
}

async function switchOverride() {
  const box = byId("level-override");
  const enable = box.checked;
  switching = false;
  const typed = gesture?.kind === "type" ? gesture : null;
  const captured = typed !== null ? typed.bound : snapshot();
  box.checked = captured.override;
  if (pending !== null || modeChanging || (gesture !== null && typed === null)) return;
  modeChanging = true;
  note = null;
  let value = inForce;
  redraw();
  try {
    if (defaultAwaiting !== null && !(await defaultAwaiting.confirmed)) return;
    if (captured.version !== client.targetVersion()) return;
    if (unsent()) {
      const typedValue = numeric();
      if (typedValue === null) { say("level-range", RANGE); return; }
      showValue(typedValue);
      gesture = null;
      const confirmed = await mutate(typedValue, captured, captured.override ? typedValue : undefined);
      if (!confirmed) return;
      value = typedValue;
    }
    gesture = null;
    if (client.state.status?.dimming == null || typeof captured.animation !== "number" || typeof captured.file !== "string") return;
    await mutate(value, captured, enable ? value : null);
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
    if (gesture === null) begin("slide");
    else gesture.kind = "slide";
    const dropped = unsent();
    gesture.value = Number(level.value);
    writeLevel(gesture.value);
    if (dropped && document.activeElement === field) field.blur();
    say("level-range", null);
    if (!gesture.bound.override) sendDefault(gesture.bound, gesture.value);
  });
  level.addEventListener("change", () => {
    if (gesture === null || gesture.kind !== "slide") return;
    gesture.value = Number(level.value);
    writeLevel(gesture.value);
    say("level-range", null);
    finish();
  });
  field.addEventListener("input", () => {
    begin("type");
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
    if (document.hidden) {
      drop("the installation did not answer");
      showValue(valueOf(client.state.status));
    }
  });
}
