// Each command of the app as a function that sends its line and checks its reply.

import {Failure, address, send} from "./target.js";

// The target answered a command with `"ok":false`. `code` is its error code, and
// `reason` the reason of `bad-file`, or null.
export class Refusal extends Error {
  constructor(code, line, reason = null) {
    super(`${code}: ${line}`);
    this.code = code;
    this.line = line;
    this.reason = reason;
  }
}

// The most bytes a size in a reply has, and the highest id of an item or of a card's file.
const MOST_BYTES = 4294967295;
const MOST_ID = 4294967295;

function whole(value, low, high) {
  return Number.isInteger(value) && value >= low && value <= high;
}

// The reply to a line, when the target carried it out. A refusal throws a Refusal.
async function carriedOut(line) {
  const reply = await send(line);
  if (reply.ok === false) {
    if (typeof reply.error !== "string") {
      throw new Failure("bad-reply", address());
    }
    throw new Refusal(reply.error, line, typeof reply.reason === "string" ? reply.reason : null);
  }
  return reply;
}

// A side of the canvas as `status` reports it: a whole number, or null when the target
// has no mapping it can use or does not report the canvas.
function side(value) {
  return value === undefined || value === null ? null : value;
}

// The readiness of a target after its start, as `status` reports it.
const READINESS = ["checking", "ready", "degraded", "recovery"];

// The most files a count of `status` names.
const MOST_FILES = 1000000;

// The most loops a turn of the playlist has, and the most a saved repeat has.
const MOST_LOOPS = 65535000;
const MOST_SAVED = 65535;

// A count of `status` that may be null, or missing from an older target's reply.
function countOrNull(value, most) {
  return value === undefined || value === null || whole(value, 1, most);
}

// How far a target has read its files after its start, as `status` reports it, or null
// when the target does not report it.
function progressOf(reply) {
  if (reply.readiness === undefined) {
    return null;
  }
  const sound =
    READINESS.includes(reply.readiness) &&
    whole(reply.checked, 0, MOST_FILES) &&
    whole(reply.to_check, 0, MOST_FILES) &&
    whole(reply.unavailable, 0, MOST_FILES) &&
    (reply.checking === null || typeof reply.checking === "string");
  if (!sound) {
    throw new Failure("bad-reply", address());
  }
  return {readiness: reply.readiness, checked: reply.checked, toCheck: reply.to_check, unavailable: reply.unavailable, checking: reply.checking};
}

// What `status` reports: whether the LEDs are on, the brightness, what plays, which is
// "all" for the root playlist, the id of a folder of the card whose playlist is current,
// the id of a cycle or null, the id of the animation on the LEDs or null, the refreshes
// in the last second, the reason of an invalid show or null, the width and the height of
// the canvas, each null when the target gives none; in `progress`, how far it has read
// its files after its start, in `host`, the text that names it, and in `left`, the whole
// seconds left in the window of the current playlist, each null when the target gives
// none; in `file`, the file of the animation on the LEDs, a card's by its path, and in
// `playlist`, the path of the card's folder whose playlist is current, each null when the
// target names none, and undefined from a target that does not name them; and of the
// playlist's turn in progress the loops it plays, `repeat`, the loop in progress, `loop`,
// and its animation's saved repeat, `saved`, each null while the target reports none, with
// `hasRepeat` and `hasSaved` saying whether the target reports them; and whether a clock plays
// between the animations, `clocks`, and the message after each clock, `clockMessage`, each
// null from a target that does not report them.
export async function status() {
  const reply = await carriedOut("status");
  const dimming = reply.dimming;
  const dimmingSound = dimming === undefined || dimming === null ||
    (typeof dimming === "object" && whole(dimming.value, 0, 255) &&
      (dimming.saved === null || whole(dimming.saved, 0, 255)) &&
      (dimming.error === null || typeof dimming.error === "string"));
  const mini = reply.mini;
  const miniSound = mini === undefined || (mini !== null && typeof mini === "object" &&
    typeof mini.supported === "boolean" && (mini.on === null || typeof mini.on === "boolean") &&
    typeof mini.pending === "boolean" && typeof mini.requested === "boolean" &&
    (mini.error === null || typeof mini.error === "string") && whole(mini.brightness, 0, 255));
  const named = (value) => value === undefined || value === null || typeof value === "string";
  const hasClockMode = reply.clock_mode !== undefined;
  const clockMode = hasClockMode ? reply.clock_mode : typeof reply.clocks === "boolean" ? (reply.clocks ? "between" : "off") : null;
  const only = reply.clock_only;
  const modeSound = !hasClockMode ? only === undefined :
    ["off", "between", "only"].includes(clockMode) && typeof reply.clocks === "boolean" && reply.clocks === (clockMode !== "off") &&
    (clockMode === "only" ? only !== null && typeof only === "object" &&
      (only.folder === null || whole(only.folder, 1, MOST_ID)) &&
      ["playing", "no-card", "missing-folder", "no-clocks"].includes(only.state) &&
      (only.state !== "playing" || only.folder !== null) : only === null);
  const sound =
    typeof reply.on === "boolean" &&
    whole(reply.brightness, 0, 255) &&
    (reply.playing === null || reply.playing === "all" || whole(reply.playing, 1, MOST_ID)) &&
    (reply.animation === null || whole(reply.animation, 1, MOST_ID)) &&
    named(reply.file) &&
    named(reply.playlist) &&
    whole(reply.fps, 0, 1000000) &&
    (reply.error === null || typeof reply.error === "string") &&
    (side(reply.width) === null || whole(reply.width, 1, 65535)) &&
    (side(reply.height) === null || whole(reply.height, 1, 65535)) &&
    (reply.host === undefined || reply.host === null || typeof reply.host === "string") &&
    (reply.left === undefined || whole(reply.left, 0, MOST_BYTES)) &&
    countOrNull(reply.repeat, MOST_LOOPS) &&
    countOrNull(reply.loop, MOST_LOOPS) &&
    countOrNull(reply.saved, MOST_SAVED) &&
    (reply.clocks === undefined || typeof reply.clocks === "boolean") &&
    (reply.clock_message === undefined || typeof reply.clock_message === "boolean");
  if (!sound || !miniSound || !dimmingSound || !modeSound) {
    throw new Failure("bad-reply", address());
  }
  return {
    on: reply.on,
    brightness: reply.brightness,
    dimming: dimming == null ? null : {...dimming},
    playing: reply.playing,
    animation: reply.animation,
    fps: reply.fps,
    error: reply.error,
    width: side(reply.width),
    height: side(reply.height),
    progress: progressOf(reply),
    host: typeof reply.host === "string" ? reply.host : null,
    left: reply.left === undefined ? null : reply.left,
    file: reply.file,
    playlist: reply.playlist,
    hasRepeat: reply.repeat !== undefined,
    repeat: reply.repeat ?? null,
    loop: reply.loop ?? null,
    hasSaved: reply.saved !== undefined,
    saved: reply.saved ?? null,
    clocks: reply.clocks ?? null,
    clockMessage: reply.clock_message ?? null,
    hasClockMode,
    clockMode,
    clockOnly: hasClockMode && only !== null ? {...only} : null,
    mini: mini === undefined ? null : {...mini},
  };
}

// The works in which a target meets a fault of a file.
const WORKS = ["start", "play", "upload", "drive"];

// The latest fault of a file the target met since its start, as `{work, file, record,
// bytes, reason}`, or null when it has met none.
export async function fault() {
  const reply = await carriedOut("fault");
  const found = reply.fault;
  const sound =
    found === null ||
    (typeof found === "object" && found !== undefined && WORKS.includes(found.work) && typeof found.file === "string" &&
      whole(found.record, 0, MOST_BYTES) && whole(found.bytes, 0, MOST_BYTES) && typeof found.reason === "string");
  if (!sound) {
    throw new Failure("bad-reply", address());
  }
  return found === null ? null : {work: found.work, file: found.file, record: found.record, bytes: found.bytes, reason: found.reason};
}

// One part of the items of a level, in its order, from a position on: of the root, the
// show's items and the root's folders and files of the card; of the card's folder with the
// id `folder`, its sub-folders and its own files. Each animation as `{id, file, bytes}`
// with the booleans `ignored` and `external` and the text `type` when the target gives
// them and `fault`, the reason it is unavailable, when it has one, and `bytes` null while
// the installation has not read it whole; each folder of the card as `{id, playlist}`
// with its path, and `files`, the number of its own files, when the target gives it; each
// cycle as `{id, cycle: true}`; and `next`, the position to ask for next, or
// null when the part holds the last item.
export async function list(from = 0, folder = null) {
  const reply = folder === null ? await carriedOut(`list ${from}`) : await carriedOut(`list in ${folder} ${from}`);
  const sound =
    Array.isArray(reply.items) &&
    (reply.next === null || whole(reply.next, from + 1, MOST_ID)) &&
    reply.items.every(
      (item) =>
        item !== null &&
        typeof item === "object" &&
        whole(item.id, 1, MOST_ID) &&
        (item.files === undefined || (typeof item.playlist === "string" && whole(item.files, 0, MOST_ID))) &&
        (item.ignored === undefined || typeof item.ignored === "boolean") &&
        (item.inherited_ignored === undefined || typeof item.inherited_ignored === "boolean") &&
        (item.external === undefined || typeof item.external === "boolean") &&
        (item.type === undefined || typeof item.type === "string") &&
        (item.fault === undefined || typeof item.fault === "string") &&
        ((typeof item.file === "string" && item.playlist === undefined && (item.bytes === null || whole(item.bytes, 0, MOST_BYTES))) ||
          (typeof item.playlist === "string" && item.playlist.length > 0 && item.external === true && item.file === undefined && item.cycle === undefined &&
            item.bytes === undefined && item.type === undefined && item.fault === undefined) ||
          (Array.isArray(item.cycle) && item.file === undefined && item.playlist === undefined && item.ignored === undefined && item.external === undefined &&
            item.inherited_ignored === undefined && item.type === undefined && item.fault === undefined)),
    );
  if (!sound) {
    throw new Failure("bad-reply", address());
  }
  return {
    items: reply.items.map((item) => (typeof item.file === "string" ? {id: item.id, file: item.file, bytes: item.bytes, ...(item.ignored === undefined ? {} : {ignored: item.ignored}),
      ...(item.inherited_ignored === undefined ? {} : {inheritedIgnored: item.inherited_ignored}),
      ...(item.external === undefined ? {} : {external: item.external}), ...(item.type === undefined ? {} : {type: item.type}),
      ...(item.fault === undefined ? {} : {fault: item.fault})} : typeof item.playlist === "string" ? {id: item.id, playlist: item.playlist, ...(item.files === undefined ? {} : {files: item.files}),
      ...(item.ignored === undefined ? {} : {ignored: item.ignored}),
      ...(item.inherited_ignored === undefined ? {} : {inheritedIgnored: item.inherited_ignored})} :
      {id: item.id, cycle: true})),
    next: reply.next,
  };
}

// Internal capacity and the external medium's presence, whether the target may write it
// (`read_only`), and its nullable capacity.
export async function space() {
  const reply = await carriedOut("space");
  if (!whole(reply.free, 0, MOST_BYTES) || !whole(reply.total, 0, MOST_BYTES)) {
    throw new Failure("bad-reply", address());
  }
  const external = reply.external;
  if (external !== undefined && (external === null || typeof external.present !== "boolean" || typeof external.read_only !== "boolean" ||
      !((external.free === null && external.total === null) ||
        (external.present && whole(external.free, 0, Number.MAX_SAFE_INTEGER) && whole(external.total, external.free, Number.MAX_SAFE_INTEGER))))) {
    throw new Failure("bad-reply", address());
  }
  if (reply.animations !== undefined && !whole(reply.animations, 0, 65535)) {
    throw new Failure("bad-reply", address());
  }
  return {free: reply.free, total: reply.total, animations: reply.animations === undefined ? null : reply.animations, external: external === undefined ? null : external};
}

// Removes the item with this id from the show.
export async function remove(id) {
  await carriedOut(`remove ${id}`);
}

// Opens the upload of a file of some bytes as the item with this id. Gives the most bytes
// one `upload data` may carry.
export async function uploadBegin(id, file, bytes, createCrc = null) {
  const line = `upload begin ${id} ${file} ${bytes}${createCrc === null ? "" : " " + createCrc}`;
  const reply = createCrc === null
    ? await carriedOut(`upload begin ${id} ${file} ${bytes}`)
    : await carriedOut(`upload begin ${id} ${file} ${bytes} ${createCrc}`);
  if (createCrc !== null && reply.replacing !== false) {
    try { await uploadCancel(); } catch (_) { /* An unchanged upload opens no transaction. */ }
    throw new Refusal(reply.replacing === true || reply.unchanged === true ? "stale" : "unsupported", line);
  }
  if (!whole(reply.chunk, 1, MOST_BYTES)) {
    throw new Failure("bad-reply", address());
  }
  return reply.chunk;
}

// Opens the upload of a file of some bytes to the external storage, which gives the
// animation its id when the upload ends. Gives the most bytes one `upload data` may carry.
export async function uploadBeginExternal(file, bytes) {
  const encoded = file.split("/").map(encodeURIComponent).join("/");
  const reply = await carriedOut(`upload begin external ${encoded} ${bytes}`);
  if (!whole(reply.chunk, 1, MOST_BYTES)) {
    throw new Failure("bad-reply", address());
  }
  return reply.chunk;
}

// Adds a piece of the file, given in base64, at the number of bytes sent before it.
// Gives the number of bytes received so far.
export async function uploadData(offset, base64) {
  const reply = await carriedOut(`upload data ${offset} ${base64}`);
  if (!whole(reply.received, 0, MOST_BYTES)) {
    throw new Failure("bad-reply", address());
  }
  return reply.received;
}

// Lets the open upload go on only while the file of its item has this CRC-32, eight
// hexadecimal digits: the one of the bytes the app read.
export async function uploadExpect(crc) {
  await carriedOut(`upload expect ${crc}`);
}

// Up to 600 bytes of the file of an animation, from an offset, as given in base64, and
// the size of the file.
export async function read(id, offset) {
  const reply = await carriedOut(`read ${id} ${offset}`);
  if (!whole(reply.bytes, 0, MOST_BYTES) || typeof reply.data !== "string" || !/^[A-Za-z0-9_-]*$/.test(reply.data) || reply.data.length % 4 === 1) {
    throw new Failure("bad-reply", address());
  }
  const text = atob(reply.data.replace(/-/g, "+").replace(/_/g, "/") + "=".repeat((4 - (reply.data.length % 4)) % 4));
  const data = new Uint8Array(text.length);
  for (let at = 0; at < text.length; at += 1) {
    data[at] = text.charCodeAt(at);
  }
  return {bytes: reply.bytes, data};
}

// Closes the upload with the CRC-32 of the whole file, eight hexadecimal digits. Gives the
// id of the animation when the reply names it, as one of the external storage does, or
// null.
export async function uploadEnd(crc) {
  const reply = await carriedOut(`upload end ${crc}`);
  if (!(reply.id === undefined || whole(reply.id, 1, MOST_ID))) {
    throw new Failure("bad-reply", address());
  }
  return reply.id === undefined ? null : reply.id;
}

// Gives up the open upload.
export async function uploadCancel() {
  await carriedOut("upload cancel");
}

// Plays the playlist from the animation with this id, or the cycle with this id.
export async function play(id) {
  await carriedOut(`play ${id}`);
}

// Plays the playlist from its first animation.
export async function playAll() {
  await carriedOut("play all");
}

export async function on() {
  await carriedOut("on");
}

export async function off() {
  await carriedOut("off");
}

// Sets the brightness, 0 to 255.
export async function brightness(value) {
  await carriedOut(`brightness ${value}`);
}

export async function brightnessSave(id, value) {
  await carriedOut(`brightness ${id} ${value} save`);
}

export async function brightnessDefault(id) {
  await carriedOut(`brightness ${id} default`);
}

// Gives the playlist's turn in progress of an animation so many loops, for that turn alone.
export async function repeat(id, loops) {
  await carriedOut(`repeat ${id} ${loops}`);
}

// Keeps so many loops as an animation's repeat for every later turn, and gives them to its
// turn in progress.
export async function repeatSave(id, loops) {
  await carriedOut(`repeat ${id} ${loops} save`);
}

// Switches the clocks between the animations on or off.
export async function clocks(on) {
  await carriedOut(`clocks ${on ? "on" : "off"}`);
}

// Selects one of the installation's clock playback modes.
export async function clockMode(mode) {
  if (!["off", "between", "only"].includes(mode)) throw new RangeError("unknown clock mode");
  await carriedOut(`clocks ${mode === "between" ? "on" : mode}`);
}

// Requests a temporary output change; status confirms its physical completion.
export async function debugMini(on) {
  await carriedOut(`debug mini ${on ? "on" : "off"}`);
}

// Switches the message after each clock on or off.
export async function clockMessage(on) {
  await carriedOut(`clocks message ${on ? "on" : "off"}`);
}

// Removes an animation's saved repeat: its turns play its own count again.
export async function repeatDefault(id) {
  await carriedOut(`repeat ${id} default`);
}


// The target's complete assignment, and its transient diagnostic mode.
export async function mappingGet() {
  const reply = await carriedOut("mapping get");
  if (typeof reply.editable !== "boolean" || typeof reply.test !== "boolean" ||
      !whole(reply.revision, 0, MOST_BYTES) || !Array.isArray(reply.pins) ||
      (reply.editable ? reply.pins.length !== 20 || new Set(reply.pins).size !== 20 ||
        reply.pins.some(pin => !whole(pin, 0, 255)) : reply.pins.length !== 0)) {
    throw new Failure("bad-reply", address());
  }
  // `snake` says which test shows, null for the diagonal or none; an older target gives none.
  const snake = reply.snake === undefined ? null : reply.snake;
  if (!(snake === null || (reply.test === true && whole(snake, 1, 20)))) {
    throw new Failure("bad-reply", address());
  }
  // `cross` says that snake 10 is cross-wired; an older target gives none.
  const cross = reply.cross === undefined ? false : reply.cross;
  if (typeof cross !== "boolean") {
    throw new Failure("bad-reply", address());
  }
  return {editable: reply.editable, pins: reply.pins, revision: reply.revision, cross, test: reply.test, snake};
}

// Saves snake 10 as cross-wired, or as wired as the others.
export async function mappingCross(crossed) {
  await carriedOut(`mapping cross ${crossed ? "on" : "off"}`);
}

export async function mappingSet(revision, pins) {
  await carriedOut(`mapping set ${revision} ${pins.join(",")}`);
}

export async function mappingTest(enabled) {
  await carriedOut(`mapping test ${enabled ? "on" : "off"}`);
}

// Shows the test of one snake, 1 to 20.
export async function mappingTestSnake(snake) {
  await carriedOut(`mapping test snake ${snake}`);
}

export async function ignore(id, ignored) {
  await carriedOut(`ignore ${id} ${ignored ? 1 : 0}`);
}

export async function removeMany(ids) {
  await carriedOut(`remove many ${ids.join(",")}`);
}

// One part of the saved playlist order, from a position on: the ids of the listed
// animations in their order, `next`, the position to ask for next or null, and the
// order's revision.
export async function orderGet(from = 0, folder = null) {
  let reply;
  if (folder === null) {
    reply = from === 0 ? await carriedOut("order get") : await carriedOut(`order get ${from}`);
  } else {
    reply = from === 0 ? await carriedOut(`order get in ${folder}`) : await carriedOut(`order get in ${folder} ${from}`);
  }
  if (!Array.isArray(reply.ids) || !reply.ids.every((id) => whole(id, 1, MOST_ID)) || !(reply.next === null || whole(reply.next, from + 1, MOST_ID)) ||
      !whole(reply.revision, 0, MOST_BYTES)) {
    throw new Failure("bad-reply", address());
  }
  return {ids: reply.ids, next: reply.next, revision: reply.revision};
}

// Moves the animation with this id before the one with the id `before`, or to the end
// with "end", in the saved order whose revision the app read.
export async function orderMove(revision, id, before) {
  await carriedOut(`order move ${revision} ${id} ${before}`);
}

// The states of a catalog, why a damaged one is damaged, and the two storages.
const CATALOG_STATES = ["none", "ok", "loading", "damaged", "incompatible", "absent"];
const DAMAGES = ["marker", "page", "line", "interrupted"];
const STORAGES = ["internal", "external"];

// One storage's catalog as `catalog` reports it, with null for what the reply leaves out,
// or null when the reply is not sound. The internal one counts the show's files it has no
// entry for; the external one says whether the drive can be written.
function catalogOf(part, internal) {
  const sound =
    part !== null &&
    typeof part === "object" &&
    CATALOG_STATES.includes(part.state) &&
    (part.detail === undefined || DAMAGES.includes(part.detail)) &&
    (part.generation === undefined || whole(part.generation, 0, MOST_BYTES)) &&
    (part.entries === undefined || whole(part.entries, 0, 65535)) &&
    (internal ? whole(part.uncataloged, 0, 65535) : part.writable === undefined || typeof part.writable === "boolean");
  if (!sound) {
    return null;
  }
  const common = {state: part.state, detail: part.detail ?? null, generation: part.generation ?? null, entries: part.entries ?? null};
  return internal ? {...common, uncataloged: part.uncataloged} : {...common, writable: part.writable ?? null};
}

// The catalog of each storage, and the rebuild under way as `{storage, read, toRead}`, the
// storage "internal" or "external", or null while none runs.
export async function catalog() {
  const reply = await carriedOut("catalog");
  const internal = catalogOf(reply.internal, true);
  const external = catalogOf(reply.external, false);
  const rebuild = reply.rebuild;
  const sound =
    internal !== null &&
    external !== null &&
    (rebuild === null ||
      (typeof rebuild === "object" && STORAGES.includes(rebuild.storage) && whole(rebuild.read, 0, 65535) && whole(rebuild.to_read, 0, 65535)));
  if (!sound) {
    throw new Failure("bad-reply", address());
  }
  return {internal, external, rebuild: rebuild === null ? null : {storage: rebuild.storage, read: rebuild.read, toRead: rebuild.to_read}};
}

// Starts the rebuild of the catalog of a storage, "internal" or "external": the target
// reads every animation of it whole while the show plays.
// Up to 512 bytes of a page of a storage's catalog from an offset: `{generation, text,
// next}`, the generation null for a catalog that is not `ok`, `next` the offset to ask for
// next or null at the page's end.
export async function catalogPage(storage, page, offset) {
  const reply = await carriedOut(`catalog page ${storage} ${page} ${offset}`);
  const sound =
    (reply.generation === null || whole(reply.generation, 0, MOST_BYTES)) &&
    typeof reply.text === "string" &&
    (reply.next === null || whole(reply.next, 1, 2 * MOST_BYTES));
  if (!sound) {
    throw new Failure("bad-reply", address());
  }
  return {generation: reply.generation, text: reply.text, next: reply.next};
}

export async function catalogRebuild(storage) {
  await carriedOut(`catalog rebuild ${storage}`);
}

// Ends the rebuild under way; the catalog stays as it was.
export async function catalogCancel() {
  await carriedOut("catalog cancel");
}
