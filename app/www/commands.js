// Each command of the app as a function that sends its line and checks its reply.

import {Failure, address, send} from "./target.js";

// The target answered a command with `"ok":false`. `code` is its error code.
export class Refusal extends Error {
  constructor(code, line) {
    super(`${code}: ${line}`);
    this.code = code;
    this.line = line;
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
    throw new Refusal(reply.error, line);
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
// as `{id, file, bytes}` and each cycle as `{id, cycle: true}`, and `next`, the position
// to ask for next, or null when the part holds the last item.
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
        ((typeof item.file === "string" && whole(item.bytes, 0, MOST_BYTES)) || (Array.isArray(item.cycle) && item.file === undefined)),
    );
  if (!sound) {
    throw new Failure("bad-reply", address());
  }
  return {
    items: reply.items.map((item) => (typeof item.file === "string" ? {id: item.id, file: item.file, bytes: item.bytes} : {id: item.id, cycle: true})),
    next: reply.next,
  };
}

// The free and the total bytes of the target's storage.
export async function space() {
  const reply = await carriedOut("space");
  if (!whole(reply.free, 0, MOST_BYTES) || !whole(reply.total, 0, MOST_BYTES)) {
    throw new Failure("bad-reply", address());
  }
  return {free: reply.free, total: reply.total};
}

// Removes the item with this id from the show.
export async function remove(id) {
  await carriedOut(`remove ${id}`);
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
