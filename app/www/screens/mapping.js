// Settings' mapping editor: the target owns the saved assignment; edits stay local until
// Save.
import * as client from "../client.js";
import {Refusal} from "../commands.js";

const DEFAULTS = [...Array.from({length: 18}, (_, at) => at + 1), 21, 47];
let visible = false;
let ready = false;
let version = -1;
let latest = null;
let base = null;
let draft = [];
let pending = false;
// A read in the background is under way: it neither disables nor redraws anything until
// its reply shows that something changed.
let polling = false;
let needsReload = false;
let problem = "";
let note = "";
let fresh = false;

const byId = id => document.getElementById(id);
const same = (a, b) => a.length === b.length && a.every((value, at) => value === b[at]);
const dirty = () => base !== null && !same(draft, base.pins);
const conflict = () => base !== null && latest !== null && base.revision !== latest.revision;
const defaultsAvailable = () => latest?.editable && same([...latest.pins].sort((a,b) => a-b), [...DEFAULTS].sort((a,b) => a-b));

function adopt(reply) {
  base = reply;
  draft = [...reply.pins];
  needsReload = false;
}

function reset() {
  version = client.targetVersion();
  latest = null;
  base = null;
  draft = [];
  pending = false;
  needsReload = false;
  problem = "";
  note = "";
  fresh = false;
  byId("mapping-rows").replaceChildren();
}

function rows() {
  const place = byId("mapping-rows");
  if (latest?.editable !== true) {
    place.replaceChildren();
    return;
  }
  const pins = [...latest.pins].sort((a,b) => a-b);
  const key = pins.join(",");
  if (place.dataset.pins !== key || place.children.length !== 20) {
    place.dataset.pins = key;
    place.replaceChildren(...pins.map((_, at) => {
      const row = document.createElement("div");
      const label = document.createElement("label");
      label.htmlFor = `mapping-pin-${at+1}`;
      label.textContent = `Snake ${at+1} \u00b7 columns ${at*3+1}\u2013${at*3+3}`;
      const select = document.createElement("select");
      select.id = label.htmlFor;
      for (const pin of pins) {
        const option = document.createElement("option");
        option.value = String(pin);
        option.textContent = `GPIO ${pin}`;
        select.append(option);
      }
      select.addEventListener("change", () => {
        const other = draft.indexOf(Number(select.value));
        if (other < 0 || pending || needsReload || conflict()) {
          draw();
          return;
        }
        [draft[at], draft[other]] = [draft[other], draft[at]];
        note = "";
        draw();
      });
      row.append(label, select);
      return row;
    }));
  }
  // Only what differs is set, so that an open picker is left as it is.
  for (let at=0; at<20; at++) {
    const select = byId(`mapping-pin-${at+1}`);
    const value = String(draft[at]);
    if (select.value !== value) select.value = value;
    const off = pending || needsReload || conflict() || !fresh;
    if (select.disabled !== off) select.disabled = off;
  }
}

function draw() {
  if (!ready) return;
  rows();
  const editable = latest?.editable === true;
  const blocked = pending || !editable || !fresh;
  const changed = conflict();
  let summary = "Reading mapping\u2026";
  if (latest !== null) {
    summary = pending ? "Waiting for the target\u2026" : dirty() ? "Unsaved draft. Selecting an occupied pin swaps the two snakes." : "Saved mapping. Selecting an occupied pin swaps the two snakes.";
  }
  byId("mapping-summary").textContent = note || summary;
  const error = problem || (changed ? "Mapping changed on the target. Your draft is kept; Reload or Cancel before saving." : latest !== null && !editable ? "This editor only supports the 60 \u00d7 60 installation with twenty three-column snakes." : "");
  byId("mapping-error").textContent = error;
  byId("mapping-error").hidden = error === "";
  byId("mapping-save").disabled = blocked || !dirty() || changed || needsReload;
  byId("mapping-cancel").disabled = pending || latest === null || (!dirty() && !needsReload && !changed);
  byId("mapping-reload").disabled = pending;
  byId("mapping-defaults").disabled = blocked || !defaultsAvailable() || changed || needsReload;
}

function explanation(error) {
  if (error instanceof Refusal) {
    const messages = {
      "unknown-command": "This target does not support mapping controls yet.",
      "mapping-conflict": "Mapping changed on the target. Your draft is kept; Reload or Cancel before saving.",
      "storage-error": "The target could not save its mapping. Reload to check the saved assignment.",
      "busy": "The target is busy checking or uploading files. Try again after it finishes.",
      "show-invalid": "The target has an invalid show. Fix its show before changing the mapping.",
      "bad-argument": "The target cannot use this mapping or diagnostic.",
    };
    return messages[error.code] || `The target refused the request: ${error.code}.`;
  }
  return "No confirmed reply. Reload to check the target before trying again.";
}

async function read(replace = false) {
  if (!ready || pending || document.hidden) return;
  const asked = version;
  pending = true;
  draw();
  try {
    const reply = await client.mappingGet();
    if (asked !== version) return;
    latest = reply;
    fresh = true;
    if (replace || base === null || (!dirty() && !needsReload)) adopt(reply);
    if (replace) {problem = "";note = "";}
    else if (!needsReload) problem = "";
  } catch (error) {
    if (asked !== version) return;
    problem = explanation(error);
    fresh = false;
  } finally {
    if (asked === version) {pending = false;draw();}
  }
}

// The read every two seconds while Settings shows: the editor changes only when the target's
// mapping did, and a reply that does not come changes nothing.
async function poll() {
  if (!ready || pending || polling || document.hidden) return;
  const asked = version;
  polling = true;
  try {
    const reply = await client.mappingGet();
    if (asked !== version || pending) return;
    const changed = latest === null || !fresh || latest.revision !== reply.revision || latest.editable !== reply.editable || !same(latest.pins, reply.pins);
    latest = reply;
    fresh = true;
    if (changed && (base === null || (!dirty() && !needsReload))) adopt(reply);
    if (changed) {
      if (!needsReload) problem = "";
      draw();
    }
  } catch (_) {
    // The next read, or Save or Reload, says what the target answers.
  } finally {
    if (asked === version) polling = false;
  }
}

async function change(carry, saved = false) {
  if (pending) return;
  const asked = version;
  pending = true;
  problem = "";
  note = "";
  draw();
  try {
    await carry();
    if (asked !== version) return;
    const reply = await client.mappingGet();
    if (asked !== version) return;
    latest = reply;
    fresh = true;
    if (saved) {adopt(reply);note = "Mapping saved.";}
  } catch (error) {
    if (asked !== version) return;
    problem = explanation(error);
    needsReload = true;
    fresh = false;
    // A failed mutation may have reached the target. Read once; never repeat it.
    try {
      const reply = await client.mappingGet();
      if (asked !== version) return;
      latest = reply;
      fresh = true;
    } catch (_) {
      // Reload remains available when even the recovery read failed.
    }
  } finally {
    if (asked === version) {pending = false;draw();}
  }
}

export function showing(shown) {
  visible = shown;
  if (shown) {
    if (base === null) read();
    else poll();
  }
}

export function start() {
  ready = true;
  byId("mapping-save").addEventListener("click", () => change(() => client.mappingSet(base.revision, [...draft]), true));
  byId("mapping-cancel").addEventListener("click", () => {
    if (latest !== null && fresh) {adopt(latest);problem = "";note = "";draw();}
    else read(true);
  });
  byId("mapping-reload").addEventListener("click", () => read(true));
  byId("mapping-defaults").addEventListener("click", () => {draft = [...DEFAULTS];note = "Defaults are a draft. Save to apply them.";draw();});
  client.watch(() => {
    if (version !== client.targetVersion()) {reset();polling = false;if (visible) read();}
    draw();
  });
  setInterval(() => {if (visible && !document.hidden) poll();}, 2000);
}
