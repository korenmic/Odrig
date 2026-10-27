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

// The most bytes a size in a reply has.
const MOST_BYTES = 4294967295;

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
// none.
export async function status() {
  const reply = await carriedOut("status");
  const sound =
    typeof reply.on === "boolean" &&
    whole(reply.brightness, 0, 255) &&
    (reply.playing === null || reply.playing === "all" || whole(reply.playing, 1, 65535)) &&
    (reply.animation === null || whole(reply.animation, 1, 65535)) &&
    whole(reply.fps, 0, 1000000) &&
    (reply.error === null || typeof reply.error === "string") &&
    (side(reply.width) === null || whole(reply.width, 1, 65535)) &&
    (side(reply.height) === null || whole(reply.height, 1, 65535)) &&
    (reply.host === undefined || reply.host === null || typeof reply.host === "string") &&
    (reply.left === undefined || whole(reply.left, 0, MOST_BYTES));
  if (!sound) {
    throw new Failure("bad-reply", address());
  }
  return {
    on: reply.on,
    brightness: reply.brightness,
    playing: reply.playing,
    animation: reply.animation,
    fps: reply.fps,
    error: reply.error,
    width: side(reply.width),
    height: side(reply.height),
    progress: progressOf(reply),
    host: typeof reply.host === "string" ? reply.host : null,
    left: reply.left === undefined ? null : reply.left,
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

// One part of the items of the show, in its order, from a position on: each animation
// as `{id, file, bytes}` with the booleans `ignored` and `external` and the text `type`
// when the target gives them and `fault`, the reason it is unavailable, when it has one,
// and `bytes` null while the installation has not read it whole; each folder of the card
// as `{id, playlist}` with its path; each cycle as `{id, cycle: true}`; and `next`, the
// position to ask for next, or null when the part holds the last item.
export async function list(from = 0) {
  const reply = await carriedOut(`list ${from}`);
  const sound =
    Array.isArray(reply.items) &&
    (reply.next === null || whole(reply.next, from + 1, 65535)) &&
    reply.items.every(
      (item) =>
        item !== null &&
        typeof item === "object" &&
        whole(item.id, 1, 65535) &&
        (item.ignored === undefined || typeof item.ignored === "boolean") &&
        (item.external === undefined || typeof item.external === "boolean") &&
        (item.type === undefined || typeof item.type === "string") &&
        (item.fault === undefined || typeof item.fault === "string") &&
        ((typeof item.file === "string" && item.playlist === undefined && (item.bytes === null || whole(item.bytes, 0, MOST_BYTES))) ||
          (typeof item.playlist === "string" && item.playlist.length > 0 && item.external === true && item.file === undefined && item.cycle === undefined &&
            item.bytes === undefined && item.ignored === undefined && item.type === undefined && item.fault === undefined) ||
          (Array.isArray(item.cycle) && item.file === undefined && item.playlist === undefined && item.ignored === undefined && item.external === undefined &&
            item.type === undefined && item.fault === undefined)),
    );
  if (!sound) {
    throw new Failure("bad-reply", address());
  }
  return {
    items: reply.items.map((item) => (typeof item.file === "string" ? {id: item.id, file: item.file, bytes: item.bytes, ...(item.ignored === undefined ? {} : {ignored: item.ignored}),
      ...(item.external === undefined ? {} : {external: item.external}), ...(item.type === undefined ? {} : {type: item.type}),
      ...(item.fault === undefined ? {} : {fault: item.fault})} : typeof item.playlist === "string" ? {id: item.id, playlist: item.playlist} : {id: item.id, cycle: true})),
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
export async function uploadBegin(id, file, bytes) {
  const reply = await carriedOut(`upload begin ${id} ${file} ${bytes}`);
  if (!whole(reply.chunk, 1, MOST_BYTES)) {
    throw new Failure("bad-reply", address());
  }
  return reply.chunk;
}

// Opens the upload of a file of some bytes to the external storage, which gives the
// animation its id when the upload ends. Gives the most bytes one `upload data` may carry.
export async function uploadBeginExternal(file, bytes) {
  const reply = await carriedOut(`upload begin external ${file} ${bytes}`);
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
  if (!(reply.id === undefined || whole(reply.id, 1, 65535))) {
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
export async function orderGet(from = 0) {
  const reply = from === 0 ? await carriedOut("order get") : await carriedOut(`order get ${from}`);
  if (!Array.isArray(reply.ids) || !reply.ids.every((id) => whole(id, 1, 65535)) || !(reply.next === null || whole(reply.next, from + 1, 65535)) ||
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

// One entry of `limits`, `[leds, budget, estimate, limited]`, as a value.
function limitOf([leds, budget, estimate, limited]) {
  return {leds, budget, estimate, limited: limited === 1};
}

// One part of the current limits, from a position of the mapping's legs on: whether
// budgets are saved; for the wall, and for each leg with its number, the number of LEDs,
// the budget in mA, the estimate of their current in mA and whether the budget dimmed the
// latest refresh; and `next`, the position to ask for next, or null.
export async function limits(from = 0) {
  const reply = from === 0 ? await carriedOut("limits") : await carriedOut(`limits ${from}`);
  const wall = reply.wall;
  const sound =
    typeof reply.saved === "boolean" &&
    Array.isArray(wall) && wall.length === 4 && whole(wall[0], 0, MOST_BYTES) && whole(wall[1], 0, MOST_BYTES) && whole(wall[2], 0, MOST_BYTES) && whole(wall[3], 0, 1) &&
    Array.isArray(reply.legs) &&
    reply.legs.every((leg) => Array.isArray(leg) && leg.length === 5 && whole(leg[0], 1, 255) && whole(leg[1], 0, MOST_BYTES) && whole(leg[2], 0, 65535) &&
      whole(leg[3], 0, MOST_BYTES) && whole(leg[4], 0, 1)) &&
    (reply.next === null || whole(reply.next, from + 1, 65535));
  if (!sound) {
    throw new Failure("bad-reply", address());
  }
  return {saved: reply.saved, wall: limitOf(wall), legs: reply.legs.map(([leg, ...rest]) => ({leg, ...limitOf(rest)})), next: reply.next};
}

// Saves the wall's budget, 0 to 250,000 mA; 0 is no limit.
export async function limitsWall(milliamps) {
  await carriedOut(`limits wall ${milliamps}`);
}

// Saves the budget of a snake, the leg of its number, 0 to 65,535 mA; 0 is no limit.
export async function limitsSnake(snake, milliamps) {
  await carriedOut(`limits snake ${snake} ${milliamps}`);
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
