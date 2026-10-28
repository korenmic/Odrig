// Settings' panel Clocks: whether a clock of the card's folder clocks plays between the
// animations, and whether the message flashes after each clock. Each box shows what `status`
// reports, and a tap saves at once, as the box of snake 10's wiring does.
import * as client from "../client.js";
import {Refusal} from "../commands.js";

// Each box: the member of `status` it shows, the call that saves it, and what is said once
// it is saved on and off.
const BOXES = {
  "clocks": {member: "clocks", save: (on) => client.clocks(on),
    saved: ["Saved: no clock plays between the animations.", "Saved: a clock plays between the animations."]},
  "clock-message": {member: "clockMessage", save: (on) => client.clockMessage(on),
    saved: ["Saved: no message after the clocks.", "Saved: the message flashes after each clock."]},
};

let version = -1;
// The box whose line is out, or null.
let sending = null;
// A box that was saved, with the setting it was saved as and the count of `status` replies
// then: it shows that setting until a newer reply reports it.
let kept = null;
let said = "";

const byId = (id) => document.getElementById(id);

function setText(element, text) {
  if (element.textContent !== text) element.textContent = text;
}

function setHidden(element, hidden) {
  if (element.hidden !== hidden) element.hidden = hidden;
}

function setDisabled(element, disabled) {
  if (element.disabled !== disabled) element.disabled = disabled;
}

function answers() {
  return client.state.link === "answers";
}

function draw() {
  const status = client.state.status;
  const known = status !== null && typeof status.clocks === "boolean";
  setHidden(byId("clocks-panel"), !known);
  if (kept !== null && client.state.statusCount > kept.count) kept = null;
  for (const [id, box] of Object.entries(BOXES)) {
    const element = byId(id);
    if (sending !== id) {
      const checked = kept !== null && kept.id === id ? kept.on : known && status[box.member] === true;
      if (element.checked !== checked) element.checked = checked;
    }
    setDisabled(element, !known || sending !== null || !answers());
  }
  setText(byId("clocks-said"), said);
  setHidden(byId("clocks-said"), said === "");
}

function explanation(error) {
  if (error instanceof Refusal) {
    const messages = {
      "busy": "The target is busy checking or uploading files. Try again after it finishes.",
      "show-invalid": "The target has an invalid show. Fix its show before changing the clocks.",
      "storage-error": "The target could not save the setting. The setting in force is shown.",
      "unknown-command": "This target does not support clocks between the animations yet.",
    };
    return messages[error.code] || `The target refused the request: ${error.code}.`;
  }
  return "No confirmed reply. The setting in force is shown once the target answers.";
}

// Saves a box as it was set, at once.
async function change(id) {
  const element = byId(id);
  const status = client.state.status;
  if (sending !== null || !answers() || status === null || typeof status.clocks !== "boolean") {
    draw();
    return;
  }
  const on = element.checked;
  const asked = version;
  sending = id;
  kept = null;
  said = "";
  draw();
  try {
    await BOXES[id].save(on);
    if (asked !== version) return;
    kept = {id, on, count: client.state.statusCount};
    said = BOXES[id].saved[on ? 1 : 0];
  } catch (error) {
    if (asked !== version) return;
    said = explanation(error);
  } finally {
    if (asked === version) {
      sending = null;
      draw();
    }
  }
}

export function start() {
  for (const id of Object.keys(BOXES)) {
    byId(id).addEventListener("change", () => change(id));
  }
  client.watch(() => {
    if (version !== client.targetVersion()) {
      version = client.targetVersion();
      sending = null;
      kept = null;
      said = "";
    }
    draw();
  });
}
