// The show screen: what the installation does, its controls, and the animations it has.

import * as client from "../client.js";
import * as capacity from "../capacity.js";
import {Refusal} from "../commands.js";
import {Failure} from "../target.js";
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
const pending = new Map();
let message = () => {};

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
  const made = document.createElement("div");
  made.dataset.id = String(animation.id);
  made.dataset.file = animation.file;
  made.dataset.editable = String(typeof animation.ignored === "boolean");
  const play = document.createElement("button");
  play.type = "button";
  play.dataset.id = String(animation.id);
  play.textContent = `${animation.id} ${animation.file}`;
  play.addEventListener("click", () => client.play(animation.id));
  made.append(play);
  if (typeof animation.ignored === "boolean") {
    const label = document.createElement("label");
    label.className = "check";
    const check = document.createElement("input");
    check.type = "checkbox";
    const words = document.createElement("span");
    label.append(check, words);
    made.append(label);
    check.addEventListener("change", async () => {
      const ignored = !check.checked;
      const version = client.targetVersion();
      pending.set(animation.id, version);
      draw(client.state);
      try {
        await client.ignore(animation.id, ignored);
      } catch (error) {
        if (version === client.targetVersion()) {
          if (error instanceof Refusal) message(messages.ofRefusal(error));
          else if (error instanceof Failure) message(messages.ofFailure(error));
        }
      } finally {
        if (pending.get(animation.id) === version) pending.delete(animation.id);
        draw(client.state);
      }
    });
  }
  return made;
}

function drawRows(animations, onTheLeds) {
  const place = byId("animations");
  const shown = [...place.children];
  if (shown.length !== animations.length || shown.some((made, at) =>
      made.dataset.id !== String(animations[at].id) || made.dataset.file !== animations[at].file ||
      made.dataset.editable !== String(typeof animations[at].ignored === "boolean"))) {
    place.replaceChildren(...animations.map(row));
  }
  [...place.children].forEach((made, at) => {
    const animation = animations[at];
    const current = animation.id === onTheLeds;
    made.setAttribute("aria-current", String(current));
    made.querySelector("button").setAttribute("aria-current", String(current));
    const check = made.querySelector("input");
    if (check) {
      check.checked = !animation.ignored;
      check.disabled = pending.get(animation.id) === client.targetVersion() || client.contentBusy() || client.state.link !== "answers";
      made.querySelector("label span").textContent = `Include in playlist: ${animation.ignored ? "Ignored" : "Included"}`;
    }
  });
}

function draw(state) {
  byId("show-space").textContent = `Internal storage: ${capacity.internal(state.space)}`;
  byId("show-external-space").textContent = capacity.external(state.space);
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
  byId("show-space").classList.toggle("stale", silent);
  byId("show-external-space").classList.toggle("stale", silent);
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
export function start(options) {
  message = options.message;
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
