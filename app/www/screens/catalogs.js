// Settings' catalogs: what the catalog of the board's own storage and that of the card
// say, and the rebuild of either, asked about first, with its progress and its cancel.
// `catalog` is asked when Settings is shown and every two seconds while it is, unless the
// target keeps no catalogs, which the client knows from any of its answers; each reply is
// handed to the client, whose previews follow the catalogs.

import * as client from "../client.js";
import {Refusal} from "../commands.js";
import * as messages from "../messages.js";
import {Failure} from "../target.js";

const ASK_EVERY_MS = 2000;
const NAMES = {internal: "Board", external: "Card"};
const WHOSE = {internal: "the board", external: "the card"};
// What a damaged catalog has that is damaged, in words.
const DAMAGES = {marker: "its marker", page: "a page", line: "a line", interrupted: "a change was cut off"};

// Whether Settings is on the screen of the phone; the newest reply of `catalog`, or null;
// whether a `catalog` is under way, and
// whether another is due after it; the storage whose rebuild is asked about, or null;
// whether a rebuild or a cancel is under way; and the target all this belongs to.
let visible = false;
let known = null;
let asking = false;
let again = false;
let question = null;
let sending = false;
let version = -1;
let message = () => {};

function byId(id) {
  return document.getElementById(id);
}

function say(id, text) {
  const place = byId(id);
  place.textContent = text === null ? "" : text;
  place.hidden = text === null;
}

function animations(count) {
  return count === 1 ? "1 animation" : `${count} animations`;
}

// What the catalog of a storage, "internal" or "external", says, in words.
export function ofCatalog(storage, part) {
  const name = NAMES[storage];
  const until = storage === "internal" ? "its animations are read whole at every start until a rebuild" : "its animations play only after a rebuild";
  if (part.state === "ok") {
    const more = storage === "internal" && part.uncataloged > 0 ? `; ${part.uncataloged} more not cataloged yet` : "";
    return `${name}: ${animations(part.entries === null ? 0 : part.entries)}, cataloged${more}.`;
  }
  if (part.state === "loading") {
    return `${name}: reading its catalog.`;
  }
  if (part.state === "damaged") {
    return `${name}: catalog damaged${part.detail === null ? "" : ` (${DAMAGES[part.detail]})`}; ${until}.`;
  }
  if (part.state === "incompatible") {
    return `${name}: catalog of another version; ${until}.`;
  }
  if (part.state === "absent") {
    return storage === "internal" ? `${name}: no storage of its own.` : `${name}: none in the installation.`;
  }
  if (storage === "external") {
    return `${name}: not cataloged yet; its animations are read whole each time it goes in.`;
  }
  const read = part.uncataloged === 1 ? "its 1 animation is" : `its ${part.uncataloged} animations are`;
  return `${name}: not cataloged yet${part.uncataloged > 0 ? `; ${read} read whole at every start` : ""}.`;
}

// The question before a rebuild of the catalog of a storage.
export function ofQuestion(storage) {
  return `Rebuild the catalog of ${WHOSE[storage]}? The installation reads every animation of ${WHOSE[storage]} whole, which takes a while; it plays on meanwhile.`;
}

// How far the rebuild under way is.
export function ofRebuild(rebuild) {
  return `Rebuilding the catalog of ${WHOSE[rebuild.storage]}: ${rebuild.read} of ${rebuild.read + rebuild.toRead} animations read.`;
}

// Forgets what an earlier target said.
function forget() {
  version = client.targetVersion();
  known = null;
  question = null;
  sending = false;
}

// Asks for the catalogs, unless the app is away, Settings is not shown, the target does
// not answer or keeps no catalogs. One asked while another is under way follows it.
async function ask() {
  if (asking) {
    again = true;
    return;
  }
  if (!visible || client.state.catalogNone || document.hidden || client.state.link !== "answers") {
    return;
  }
  asking = true;
  again = false;
  const asked = client.targetVersion();
  try {
    const reply = await client.catalog();
    if (asked === client.targetVersion()) {
      // A rebuild that has ended changed the sizes and the animations of the list.
      if (known !== null && known.rebuild !== null && reply.rebuild === null) {
        client.refreshContent();
      }
      known = reply;
      client.noteCatalog(reply);
    }
  } catch (error) {
    if (asked === client.targetVersion() && error instanceof Refusal && ["unknown-command", "bad-argument"].includes(error.code)) {
      client.noCatalogs();
    }
  } finally {
    asking = false;
    draw();
  }
  if (again) {
    ask();
  }
}

// Sends a rebuild or a cancel, says a refusal or a failure, and asks for the catalogs
// again, so that the progress shows at once.
async function perform(carry) {
  const asked = client.targetVersion();
  sending = true;
  draw();
  try {
    await carry();
  } catch (error) {
    if (asked === client.targetVersion()) {
      if (error instanceof Refusal) message(messages.ofRefusal(error, client.state.status === null ? null : client.state.status.error));
      else if (error instanceof Failure) message(messages.ofFailure(error));
    }
  } finally {
    if (asked === client.targetVersion()) {
      sending = false;
    }
    draw();
  }
  ask();
}

function draw() {
  if (version !== client.targetVersion()) {
    forget();
  }
  const answers = client.state.link === "answers";
  const none = client.state.catalogNone;
  say("catalog-summary", none ? "This installation's software keeps no catalogs." : known === null ? "Reading the catalogs\u2026" : null);
  const shown = known !== null && !none;
  const rebuild = shown ? known.rebuild : null;
  say("catalog-internal", shown ? ofCatalog("internal", known.internal) : null);
  say("catalog-external", shown ? ofCatalog("external", known.external) : null);
  const card = shown && known.external.state !== "absent";
  byId("catalog-external-note").hidden = !(card && known.external.writable === false);
  const free = answers && rebuild === null && question === null && !sending;
  byId("rebuild-internal").hidden = !shown;
  byId("rebuild-internal").disabled = !free || !shown || known.internal.state === "absent";
  byId("rebuild-external").hidden = !card;
  byId("rebuild-external").disabled = !free || !card || known.external.writable !== true;
  byId("rebuild-question").hidden = question === null;
  byId("rebuild-question-text").textContent = question === null ? "" : ofQuestion(question);
  byId("rebuild-yes").disabled = !answers || sending;
  say("rebuild-progress", rebuild === null ? null : ofRebuild(rebuild));
  byId("rebuild-cancel").hidden = rebuild === null;
  byId("rebuild-cancel").disabled = !answers || sending;
  byId("catalogs").classList.toggle("stale", client.state.link === "no-answer");
}

// Says whether Settings is on the screen of the phone; the catalogs are asked for each
// time it is shown.
export function showing(shown) {
  visible = shown;
  if (!shown) {
    question = null;
  }
  draw();
  if (shown) {
    ask();
  }
}

// Starts the panel. `message` shows a text in the place for messages.
export function start(options) {
  message = options.message;
  for (const storage of ["internal", "external"]) {
    byId(`rebuild-${storage}`).addEventListener("click", () => {
      question = storage;
      draw();
    });
  }
  byId("rebuild-yes").addEventListener("click", () => {
    const storage = question;
    question = null;
    if (storage !== null) {
      perform(() => client.catalogRebuild(storage));
    }
  });
  byId("rebuild-no").addEventListener("click", () => {
    question = null;
    draw();
  });
  byId("rebuild-cancel").addEventListener("click", () => perform(() => client.catalogCancel()));
  client.watch(() => {
    const changed = version !== client.targetVersion();
    draw();
    if (changed && visible) {
      ask();
    }
  });
  setInterval(() => {
    if (visible && !document.hidden) {
      ask();
    }
  }, ASK_EVERY_MS);
}
