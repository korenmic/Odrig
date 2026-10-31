// Temporary miniature output follows the target's physical acknowledgement.
import * as client from "../client.js";
import {Refusal} from "../commands.js";
import {ofRefusal} from "../messages.js";

let version = -1;
let sending = false;
let awaiting = null;
let staleAt = -1;
let hadSupport = false;
let refusal = "";
const byId = id => document.getElementById(id);

function set(element, member, value) {
  if (element[member] !== value) element[member] = value;
}

function draw() {
  const {status, statusCount, link} = client.state;
  if (link !== "answers") staleAt = statusCount;
  const fresh = link === "answers" && statusCount > staleAt;
  const mini = fresh ? status?.mini : null;
  if (mini?.supported) hadSupport = true;
  if (awaiting !== null && fresh && statusCount > awaiting) awaiting = null;
  const supported = mini?.supported === true;
  const waiting = sending || awaiting !== null || mini?.pending === true;
  const box = byId("debug-mini");
  set(box, "checked", supported && mini.on === true);
  set(box, "indeterminate", !supported || mini.on === null);
  set(box, "disabled", !supported || waiting);
  set(byId("mini-restore"), "hidden", !supported || mini.error === null);
  set(byId("mini-restore"), "disabled", waiting);
  let text = "Reading the miniature mode\u2026";
  if (!fresh && hadSupport) text = "Miniature state unknown. Waiting for a fresh status; no request will be sent automatically.";
  else if (fresh && !supported) text = "This target does not support miniature display mode.";
  else if (supported) {
    if (waiting) text = "Switching outputs\u2026 Waiting for the target to confirm.";
    else if (mini.error !== null) text = "Output setup failed; the outputs are dark. Tap to retry, or turn the mode off.";
    else text = mini.on ? `Miniature mode is active. Output brightness: ${mini.brightness} (maximum 40).` : "Miniature mode is off.";
  }
  set(byId("mini-said"), "textContent", refusal ? `${refusal} ${text}` : text);
  const indicator = byId("mini-indicator");
  set(indicator, "hidden", !(supported && (mini.on === true || mini.pending || mini.error !== null)) && !(!fresh && hadSupport));
  set(indicator, "textContent", !fresh || mini?.on === null ? "Miniature state unknown" :
    mini?.pending ? "Miniature outputs switching\u2026" : "Miniature mode \u00b7 brightness \u2264 40");
}

async function change(on = byId("debug-mini").checked) {
  const mini = client.state.status?.mini;
  if (sending || awaiting !== null || client.state.link !== "answers" || !mini?.supported || mini.pending || client.state.statusCount <= staleAt) {
    draw();
    return;
  }
  const asked = version;
  sending = true;
  refusal = "";
  draw();
  try {
    await client.debugMini(on);
    if (asked === version) awaiting = client.state.statusCount;
  } catch (error) {
    if (asked !== version) return;
    refusal = error instanceof Refusal ? ofRefusal(error) : "No confirmed reply.";
  } finally {
    if (asked === version) {
      sending = false;
      draw();
    }
  }
}

export function start() {
  byId("debug-mini").addEventListener("change", () => change());
  byId("mini-restore").addEventListener("click", () => change(false));
  client.watch(() => {
    if (version !== client.targetVersion()) {
      version = client.targetVersion();
      sending = false;
      awaiting = null;
      staleAt = client.state.statusCount - 1;
      hadSupport = false;
      refusal = "";
    }
    draw();
  });
}
