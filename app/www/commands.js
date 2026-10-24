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

// What `status` reports: whether the LEDs are on, the brightness, what plays, which is
// "all" for the playlist, the id of a cycle or null, the id of the animation on the
// LEDs or null, the refreshes in the last second, the reason of an invalid show or null,
// and the width and the height of the canvas, each null when the target gives none.
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
    (side(reply.height) === null || whole(reply.height, 1, 65535));
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
  };
}

// One part of the items of the show, in its order, from a position on: each animation
// as `{id, file, bytes}` with the booleans `ignored` and `external` and the text `type`
// when the target gives them and `fault`, the reason it is unavailable, when it has one,
// and `bytes` null while the installation has not read it whole; each cycle as
// `{id, cycle: true}`; and `next`, the position to ask for next, or null when the part
// holds the last item.
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
        ((typeof item.file === "string" && (item.bytes === null || whole(item.bytes, 0, MOST_BYTES))) ||
          (Array.isArray(item.cycle) && item.file === undefined && item.ignored === undefined && item.external === undefined && item.type === undefined &&
            item.fault === undefined)),
    );
  if (!sound) {
    throw new Failure("bad-reply", address());
  }
  return {
    items: reply.items.map((item) => (typeof item.file === "string" ? {id: item.id, file: item.file, bytes: item.bytes, ...(item.ignored === undefined ? {} : {ignored: item.ignored}),
      ...(item.external === undefined ? {} : {external: item.external}), ...(item.type === undefined ? {} : {type: item.type}),
      ...(item.fault === undefined ? {} : {fault: item.fault})} : {id: item.id, cycle: true})),
    next: reply.next,
  };
}

// Internal capacity and the external medium's presence and nullable capacity.
export async function space() {
  const reply = await carriedOut("space");
  if (!whole(reply.free, 0, MOST_BYTES) || !whole(reply.total, 0, MOST_BYTES)) {
    throw new Failure("bad-reply", address());
  }
  const external = reply.external;
  if (external !== undefined && (external === null || typeof external.present !== "boolean" || external.read_only !== true ||
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

// Adds a piece of the file, given in base64, at the number of bytes sent before it.
// Gives the number of bytes received so far.
export async function uploadData(offset, base64) {
  const reply = await carriedOut(`upload data ${offset} ${base64}`);
  if (!whole(reply.received, 0, MOST_BYTES)) {
    throw new Failure("bad-reply", address());
  }
  return reply.received;
}

// Closes the upload with the CRC-32 of the whole file, eight hexadecimal digits.
export async function uploadEnd(crc) {
  await carriedOut(`upload end ${crc}`);
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
  return {editable: reply.editable, pins: reply.pins, revision: reply.revision, test: reply.test, snake};
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
