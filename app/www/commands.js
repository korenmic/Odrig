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

// What `status` reports: whether the LEDs are on, the brightness, what plays, which is
// "all" for the playlist, the id of a cycle or null, the id of the animation on the
// LEDs or null, the refreshes in the last second, and the reason of an invalid show or
// null.
export async function status() {
  const reply = await carriedOut("status");
  const sound =
    typeof reply.on === "boolean" &&
    whole(reply.brightness, 0, 255) &&
    (reply.playing === null || reply.playing === "all" || whole(reply.playing, 1, 65535)) &&
    (reply.animation === null || whole(reply.animation, 1, 65535)) &&
    whole(reply.fps, 0, 1000000) &&
    (reply.error === null || typeof reply.error === "string");
  if (!sound) {
    throw new Failure("bad-reply", address());
  }
  return {on: reply.on, brightness: reply.brightness, playing: reply.playing, animation: reply.animation, fps: reply.fps, error: reply.error};
}

// One part of the items of the show, in its order, from a position on: each animation
// as `{id, file}` and each cycle as `{id, cycle: true}`, and `next`, the position to
// ask for next, or null when the part holds the last item.
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
        (typeof item.file === "string" || (Array.isArray(item.cycle) && item.file === undefined)),
    );
  if (!sound) {
    throw new Failure("bad-reply", address());
  }
  return {
    items: reply.items.map((item) => (typeof item.file === "string" ? {id: item.id, file: item.file} : {id: item.id, cycle: true})),
    next: reply.next,
  };
}
