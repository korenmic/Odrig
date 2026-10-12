// The show screen: what the installation does, its controls, and the animations it has.

import * as client from "../client.js";
import * as messages from "../messages.js";

// The shortest time between two brightness commands while the slider is moved.
const BRIGHTNESS_EVERY_MS = 200;
// How long after a brightness command a status does not move the slider.
const SLIDER_RESTS_MS = 1000;

// Whether the operator holds the slider, the value and the time of the newest brightness
// command, and the timer of one that waits for its time.
let held = false;
let sentValue = null;
let sentAt = -Infinity;
let waiting = null;

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

function row(animation) {
  const made = document.createElement("button");
  made.type = "button";
  made.dataset.id = String(animation.id);
  made.dataset.file = animation.file;
  const id = document.createElement("span");
  id.className = "id";
  id.textContent = String(animation.id);
  const file = document.createElement("span");
  file.className = "file";
  file.textContent = animation.file;
  made.append(id, " ", file);
  made.addEventListener("click", () => client.play(animation.id));
  return made;
}

// Shows the animations as one button each. The buttons are made again only when the
// list is another one, so that a press is never lost to a status that arrives.
function drawRows(animations, onTheLeds) {
  const place = byId("animations");
  const shown = [...place.children];
  const same = shown.length === animations.length && shown.every((button, at) => button.dataset.id === String(animations[at].id) && button.dataset.file === animations[at].file);
  if (!same) {
    place.replaceChildren(...animations.map(row));
  }
  for (const button of place.children) {
    button.setAttribute("aria-current", String(button.dataset.id === String(onTheLeds)));
  }
}

function draw(state) {
  const status = state.status;
  if (status === null) {
    for (const id of ["power", "brightness", "playing", "fps"]) {
      byId(id).textContent = "-";
    }
    say("now", null);
    byId("on").setAttribute("aria-pressed", "false");
    byId("off").setAttribute("aria-pressed", "false");
  } else {
    byId("power").textContent = status.on ? "ON" : "OFF";
    byId("brightness").textContent = `Brightness ${status.brightness}`;
    byId("playing").textContent = playing(status);
    say("now", now(status, state.animations));
    byId("fps").textContent = `${status.fps} refreshes a second`;
    byId("on").setAttribute("aria-pressed", String(status.on));
    byId("off").setAttribute("aria-pressed", String(!status.on));
    // A status does not move the slider while it is held, nor right after a command.
    if (!held && performance.now() - sentAt >= SLIDER_RESTS_MS) {
      byId("level").value = String(status.brightness);
      byId("level-number").textContent = String(status.brightness);
    }
  }
  const animations = state.animations === null ? [] : state.animations;
  drawRows(animations, status === null ? null : status.animation);
  byId("none").hidden = state.animations === null || animations.length > 0;

  const silent = state.link === "no-answer";
  byId("state").classList.toggle("stale", silent);
  byId("animations").classList.toggle("stale", silent);
  say("silent", silent ? messages.ofSilence(Math.floor((Date.now() - (state.heardAt === null ? state.since : state.heardAt)) / 1000)) : null);
  say("silent-why", silent ? messages.ofFailure(state.failure) : null);
}

// Sends the slider's value as a brightness command, now or as soon as the shortest time
// since the one before has passed. A value that was the last one sent is not sent again.
function sendLevel() {
  clearTimeout(waiting);
  waiting = null;
  const left = sentAt + BRIGHTNESS_EVERY_MS - performance.now();
  if (left > 0) {
    waiting = setTimeout(sendLevel, left);
    return;
  }
  const value = Number(byId("level").value);
  if (value !== sentValue) {
    sentValue = value;
    sentAt = performance.now();
    client.setBrightness(value);
  }
}

// Starts the screen. While the target does not answer, the line that says for how long
// is written again every second.
export function start() {
  byId("on").addEventListener("click", () => client.switchOn());
  byId("off").addEventListener("click", () => client.switchOff());
  byId("play-all").addEventListener("click", () => client.playAll());
  const level = byId("level");
  level.addEventListener("input", () => {
    held = true;
    byId("level-number").textContent = level.value;
    sendLevel();
  });
  level.addEventListener("change", () => {
    held = false;
    byId("level-number").textContent = level.value;
    // The value at which the slider is let go is always sent: once more when it was
    // sent a while ago, because somebody else may have set another since.
    if (performance.now() - sentAt >= SLIDER_RESTS_MS) {
      sentValue = null;
    }
    sendLevel();
  });
  client.watch(draw);
  setInterval(() => {
    if (client.state.link === "no-answer") {
      draw(client.state);
    }
  }, 1000);
}
