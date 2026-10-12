// The show screen: what the installation does, and the animations it has.

import * as client from "../client.js";
import * as messages from "../messages.js";

function byId(id) {
  return document.getElementById(id);
}

function say(id, text) {
  const place = byId(id);
  place.textContent = text === null ? "" : text;
  place.hidden = text === null;
}

// What plays, in words: the playlist, a cycle by its id, or nothing.
function playing(status) {
  if (status.error !== null) {
    return messages.ofInvalidShow(status.error);
  }
  if (status.playing === "all") {
    return "Playlist";
  }
  return status.playing === null ? "Nothing plays" : `Cycle ${status.playing}`;
}

// The animation on the LEDs: its id, and its file name when the list has it.
function now(status, animations) {
  if (status.animation === null) {
    return null;
  }
  const found = animations === null ? undefined : animations.find((animation) => animation.id === status.animation);
  return found === undefined ? `Now ${status.animation}` : `Now ${found.id} ${found.file}`;
}

function row(animation, marked) {
  const made = document.createElement("li");
  made.dataset.id = String(animation.id);
  made.setAttribute("aria-current", String(marked));
  const id = document.createElement("span");
  id.className = "id";
  id.textContent = String(animation.id);
  const file = document.createElement("span");
  file.className = "file";
  file.textContent = animation.file;
  made.append(id, file);
  return made;
}

function draw(state) {
  const status = state.status;
  if (status === null) {
    for (const id of ["power", "brightness", "playing", "fps"]) {
      byId(id).textContent = "-";
    }
    say("now", null);
  } else {
    byId("power").textContent = status.on ? "ON" : "OFF";
    byId("brightness").textContent = `Brightness ${status.brightness}`;
    byId("playing").textContent = playing(status);
    say("now", now(status, state.animations));
    byId("fps").textContent = `${status.fps} refreshes a second`;
  }
  const animations = state.animations === null ? [] : state.animations;
  const onTheLeds = status === null ? null : status.animation;
  byId("animations").replaceChildren(...animations.map((animation) => row(animation, animation.id === onTheLeds)));
  byId("none").hidden = state.animations === null || animations.length > 0;

  const silent = state.link === "no-answer";
  byId("state").classList.toggle("stale", silent);
  byId("animations").classList.toggle("stale", silent);
  say("silent", silent ? messages.ofSilence(Math.floor((Date.now() - (state.heardAt === null ? state.since : state.heardAt)) / 1000)) : null);
}

// Starts the screen. While the target does not answer, the line that says for how long
// is written again every second.
export function start() {
  client.watch(draw);
  setInterval(() => {
    if (client.state.link === "no-answer") {
      draw(client.state);
    }
  }, 1000);
}
