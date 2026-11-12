// The run of a batch of animations: one after another through the app's upload, to one
// destination, while the operator uses the rest of the app. A file that fails is marked and
// the run goes on; a pause of the link or of the app makes it wait.

import * as client from "./client.js";
import {Refusal} from "./commands.js";
import * as destinations from "./upload-destination.js";
import * as messages from "./messages.js";
import * as previews from "./previews.js";
import {Failure} from "./target.js";
import {fits, freeId, uploading} from "./upload.js";

// How often a `busy` preflight or `upload begin` is tried, and how long the app waits on the
// screen between two tries.
export const BUSY_TRIES = 30;
const BUSY_WAIT_MS = 2000;
// How often a wait looks again whether the link answers and the app is on the screen.
const LOOK_MS = 100;
const PAUSED = "Paused while the app was not on the screen.";
const ROOM = "The installation has no room for another animation until it restarts or one is removed. (no-space)";
const TARGET = "The target changed.";

// The run under way, or null: its items, its destination, and what its line says.
let run = null;
// What the run says of each row, and how it ended, by the row of the list.
const said = new Map();
const ends = new Map();
// The line's words after the run ended, until it is seen.
let ended = null;
const watchers = new Set();

function changed() {
  for (const watcher of watchers) watcher();
}

export function watch(watcher) {
  watchers.add(watcher);
}

export function running() {
  return run !== null;
}

// What the run says of a row: `checking`, `sending 45%`, `uploaded as animation 7`, and so
// on, or null while the row has been in no run.
export function rowOf(row) {
  return said.get(row) ?? null;
}

// How a row ended: "uploaded", "failed" or "not sent", or null.
export function outcomeOf(row) {
  return ends.get(row) ?? null;
}

// The words of the line on every screen, or null when it is not shown.
export function line() {
  if (run === null) return ended;
  if (run.waiting !== null) return run.waiting;
  if (run.current === null) return null;
  const item = run.current;
  const part = item.percent === null ? "" : `, ${item.percent}%`;
  return `Uploading ${run.items.indexOf(item) + 1} of ${run.items.length}: ${item.name}${part}`;
}

// The line was tapped: its end sentence goes.
export function seen() {
  if (run === null && ended !== null) {
    ended = null;
    changed();
  }
}

// Ends the run after the file in progress; a file waiting out a `busy` is not sent.
export function stop() {
  if (run !== null) {
    run.stopping = true;
    changed();
  }
}

function setState(item, words) {
  said.set(item.row, words);
  changed();
}

function finish(item, outcome, words) {
  ends.set(item.row, outcome);
  setState(item, words);
}

// A row's words for a reason, without a clause that asks to select the file again or press
// Upload again.
function rowWords(text) {
  return text.replace(/\s*(Select the (file|destination) again[^.]*\.|Review it and press Upload again\.|Prepare it again\.|press Upload again[^.]*\.)/g, "").trim();
}

function fail(item, text) {
  finish(item, "failed", `failed: ${rowWords(text)}`);
}

function notSent(item) {
  finish(item, "not sent", "not sent");
}

// Waits a number of milliseconds, counted only while the app is on the screen. False when
// the run was stopped meanwhile.
async function onScreen(ms) {
  let left = ms;
  while (left > 0) {
    if (run.stopping) return false;
    await new Promise((resolve) => setTimeout(resolve, LOOK_MS));
    if (!document.hidden) left -= LOOK_MS;
  }
  return !run.stopping;
}

// Waits while the app is not on the screen or the installation does not answer. Gives
// "ready", "stopped" or "target" when the target changed.
async function ready() {
  for (;;) {
    if (client.targetVersion() !== run.form.target) return "target";
    if (run.stopping) return "stopped";
    if (document.hidden) {
      run.waiting = PAUSED;
      run.paused = true;
    } else if (client.state.link !== "answers") {
      run.waiting = "Waiting for the installation to answer.";
    } else {
      if (!run.paused) run.waiting = null;
      return "ready";
    }
    changed();
    await new Promise((resolve) => setTimeout(resolve, LOOK_MS));
  }
}

// Whether the destination still holds: the card there and writable, its catalog ready, and
// the browsed folder the same, of either storage. The reason when it does not, else null.
function gone(fresh) {
  const form = run.form;
  if (form.storage !== "external") {
    return destinations.folderOf(form) !== "" && form.level.id !== null && !fresh.folderValid ? "The explored folder changed or disappeared." : null;
  }
  if (!destinations.present(fresh.space) || fresh.space.external.read_only !== false) return "External storage is absent or read-only. Check the displayed destination before retrying.";
  const catalog = fresh.catalog?.external;
  if (catalog != null && (catalog.state !== "ok" || catalog.writable !== true)) return "External storage needs a ready writable catalog before uploading.";
  if (form.level.id !== null && !fresh.folderValid) return "The explored folder changed or disappeared.";
  return null;
}

// Sends a file with the app's upload job. Gives how it ended, with whether its first line
// was answered, whether the last byte's reply came, and whether the app left the screen.
function sendFile(item, id, path, external, replace) {
  return new Promise((resolve) => {
    let begun = false;
    let atEnd = false;
    let over = false;
    let hidden = document.hidden;
    const look = () => {
      if (document.hidden) hidden = true;
    };
    document.addEventListener("visibilitychange", look);
    const job = uploading(
      {id, file: path, bytes: item.bytes, external, create: !replace, expect: external && !replace ? "00000000" : null},
      {
        report(part) {
          // A reply that comes after the job ended changes nothing of the row.
          if (over) return;
          begun = true;
          atEnd = part >= 1;
          item.percent = Math.floor(part * 100);
          setState(item, `sending ${item.percent}%`);
        },
        end(how) {
          over = true;
          document.removeEventListener("visibilitychange", look);
          resolve({...how, begun, atEnd, hidden});
        },
        wake: client.wake,
      },
    );
    client.upload(job);
  });
}

// Takes back an upload the installation may still hold open after a lost reply.
async function cancelOpen() {
  try {
    await client.uploadCancel();
  } catch {
    // Nothing was open, or the installation does not answer yet: the next begin says.
  }
}

// A file that was uploaded keeps its preview and its place; the run waits for the preview of
// the file before it, so that the phone holds at most two files of the batch.
async function preview(item, making, storage, path) {
  previews.keep(making);
  client.uploadedTo(storage, path, making.key);
  making.release();
  if (run.preview !== null) await run.preview;
  run.preview = making.done;
}

// One file's turn. Gives "end" when the run ends with it.
async function turn(item, guarded) {
  const form = run.form;
  const external = form.storage === "external";
  let tries = 0;
  const again = {stale: 0, dropped: 0, lost: 0};
  const busy = async () => {
    tries += 1;
    if (tries > BUSY_TRIES) return false;
    setState(item, `waiting: the installation is busy (try ${tries} of ${BUSY_TRIES})`);
    return onScreen(BUSY_WAIT_MS);
  };
  for (;;) {
    const state = await ready();
    if (state === "target") {
      fail(item, TARGET);
      return "end";
    }
    if (state === "stopped") {
      notSent(item);
      return null;
    }
    run.current = item;
    run.paused = false;
    run.waiting = null;
    item.percent = null;
    setState(item, "checking");
    if (item.bytes === undefined) {
      try {
        item.facts = await item.read();
        item.bytes = item.facts.bytes;
      } catch (error) {
        fail(item, error.message);
        return null;
      }
    }
    let fresh;
    try {
      fresh = await client.uploadSnapshot(destinations.snapshotLevel(form));
    } catch (error) {
      if (error instanceof Refusal && error.code === "busy") {
        if (await busy()) continue;
        if (run.stopping) {
          notSent(item);
          return null;
        }
        fail(item, messages.ofRefusal(error, client.state.status?.error ?? null, client.state.status?.hasClockStorage === true));
        return null;
      }
      if (error instanceof Refusal) {
        fail(item, messages.ofRefusal(error, client.state.status?.error ?? null, client.state.status?.hasClockStorage === true));
        return null;
      }
      if (client.targetVersion() !== form.target) continue;
      // A lost reply, or a preflight cancelled by leaving the screen: the turn starts again.
      if (error instanceof Failure || document.hidden || error.message === "the request was cancelled") continue;
      fail(item, error.message);
      return null;
    }
    if (client.targetVersion() !== form.target) continue;
    const lost = gone(fresh);
    if (lost !== null) {
      fail(item, lost);
      return "end";
    }
    // An item with a path of its own on the card goes into its folder, not the form's.
    const folder = item.path == null ? form.level : {path: item.path.includes("/") ? item.path.slice(0, item.path.lastIndexOf("/")) : "", id: null};
    let checked;
    try {
      checked = destinations.validate({...form, level: folder, generations: {...form.generations, [form.storage]: guarded ? form.generations[form.storage] : null}},
        fresh, item.name, item.size, client.targetVersion(), {replace: item.replace === true});
    } catch (error) {
      fail(item, error.message);
      return null;
    }
    if (checked.noSpace !== undefined) {
      fail(item, messages.ofNoSpace(item.size, checked.noSpace, external ? "the card" : undefined));
      return null;
    }
    // A file replaced in a folder of the board's own storage is found in that folder's rows.
    const rows = destinations.folderOf({...form, level: folder}) !== "" ? fresh.items : fresh.root;
    const there = item.replace === true && !external ? rows.find((row) => row.file === checked.path && row.external !== true && typeof row.id === "number") : undefined;
    const id = external ? null : there !== undefined ? there.id : freeId(new Set(fresh.ids ?? fresh.root.map((row) => row.id)));
    if (!external && id === null) {
      fail(item, "Internal storage has no free animation id.");
      return null;
    }
    setState(item, "sending 0%");
    const making = previews.makeOwn(item.bytes);
    const how = await sendFile(item, id, checked.path, external, item.replace === true);
    if (how.done) {
      finish(item, "uploaded", external && how.id === null ? "uploaded to the card" : `uploaded as animation ${external ? how.id : id}`);
      await preview(item, making, form.storage, checked.path);
      item.bytes = undefined;
      return null;
    }
    making.release();
    const error = how.error;
    if (error instanceof Error && error.message === "the address changed") {
      fail(item, TARGET);
      return "end";
    }
    if (error instanceof Refusal && error.code === "busy" && !how.begun) {
      if (await busy()) continue;
      if (run.stopping) {
        notSent(item);
        return null;
      }
    } else if (error instanceof Refusal && error.code === "stale" && !external && !how.begun && again.stale++ === 0) {
      continue;
    } else if (error instanceof Refusal && error.code === "no-upload" && how.hidden && again.dropped++ === 0) {
      continue;
    } else if (error instanceof Failure && !how.atEnd && again.lost++ === 0) {
      await ready();
      await cancelOpen();
      continue;
    }
    if (error instanceof Refusal && error.code === "no-space" && !external && typeof fresh.space?.free === "number" && fits(item.size, fresh.space.free)) {
      fail(item, ROOM);
      return null;
    }
    // A folder of the board's own storage gone since the check: the run ends with the file.
    if (error instanceof Refusal && error.code === "unknown-id" && !external && !how.begun && destinations.folderOf(form) !== "") {
      fail(item, destinations.refusalWords(error, external, item.size, client.state));
      return "end";
    }
    fail(item, destinations.refusalWords(error, external, item.size, client.state));
    return null;
  }
}

// Sends items, `{row, name, storage, folder, size, read, replace}`, one after another to the
// destination of a form. With `guarded` the catalog's generation the form captured guards the
// first file sent.
export async function start(items, form, {guarded = false} = {}) {
  if (run !== null) return;
  ended = null;
  run = {items: items.map((item) => ({...item, bytes: undefined, percent: null})), form, stopping: false, waiting: null, paused: false, current: null, preview: null};
  for (const item of run.items) {
    said.set(item.row, "waiting");
    ends.delete(item.row);
  }
  client.setContentBusy("batch");
  changed();
  let first = guarded;
  try {
    for (const item of run.items) {
      if (run.stopping) {
        notSent(item);
        continue;
      }
      const result = await turn(item, first);
      first = false;
      if (result === "end") {
        for (const rest of run.items.slice(run.items.indexOf(item) + 1)) notSent(rest);
        break;
      }
    }
  } finally {
    const counted = run.items.map((item) => ends.get(item.row));
    const uploaded = counted.filter((outcome) => outcome === "uploaded").length;
    const failed = counted.filter((outcome) => outcome === "failed").length;
    const left = counted.filter((outcome) => outcome === "not sent").length;
    ended = `${uploaded} of ${run.items.length} uploaded${failed > 0 ? `, ${failed} failed` : ""}${left > 0 ? `, ${left} not sent` : ""}.`;
    run = null;
    client.setContentBusy(false);
    changed();
  }
}

// While the app is away from the screen the run sends nothing, and its line says so until
// the next file's turn.
document.addEventListener("visibilitychange", () => {
  if (run !== null && document.hidden) {
    run.waiting = PAUSED;
    run.paused = true;
    changed();
  }
});

// A new upload of any screen takes the place of the line's end sentence.
export function otherUpload() {
  if (run === null && ended !== null) {
    ended = null;
    changed();
  }
}
