// The storage screen: the free storage of the target, the installed animations with their
// sizes, and the removal of one, which is asked about first.

import * as client from "../client.js";
import * as messages from "../messages.js";

// The animation the open question would remove, or null while none is asked about.
let asked = null;

function byId(id) {
  return document.getElementById(id);
}

// A size in megabytes of 1,000,000 bytes, with one decimal.
export function megabytes(bytes) {
  return (bytes / 1000000).toFixed(1);
}

// A size in kilobytes of 1,000 bytes, rounded up, so that a small file is never 0.
export function kilobytes(bytes) {
  return String(Math.ceil(bytes / 1000));
}

function row(animation) {
  const made = document.createElement("div");
  made.className = "row";
  made.dataset.id = String(animation.id);
  made.dataset.file = animation.file;
  made.dataset.bytes = String(animation.bytes);
  const words = document.createElement("p");
  const id = document.createElement("span");
  id.className = "id";
  id.textContent = String(animation.id);
  const file = document.createElement("span");
  file.className = "file";
  file.textContent = animation.file;
  const size = document.createElement("span");
  size.className = "size";
  size.textContent = `${kilobytes(animation.bytes)} KB`;
  words.append(id, " ", file, " ", size);
  const remove = document.createElement("button");
  remove.type = "button";
  remove.textContent = "Remove";
  remove.addEventListener("click", () => ask(animation));
  made.append(words, remove);
  return made;
}

// Asks whether the animation is to be removed.
function ask(animation) {
  asked = animation;
  byId("confirm-text").textContent = messages.ofRemoval(animation);
  byId("confirm").hidden = false;
}

function close() {
  asked = null;
  byId("confirm").hidden = true;
}

// Shows the rows anew only when the list is another one, so that a press is never lost
// to a reply that arrives.
function drawRows(animations) {
  const place = byId("installed");
  const shown = [...place.children];
  const same =
    shown.length === animations.length &&
    shown.every((made, at) => made.dataset.id === String(animations[at].id) && made.dataset.file === animations[at].file && made.dataset.bytes === String(animations[at].bytes));
  if (!same) {
    place.replaceChildren(...animations.map(row));
  }
}

function draw(state) {
  byId("space").textContent = state.space === null ? "-" : `Free ${megabytes(state.space.free)} MB of ${megabytes(state.space.total)} MB`;
  const animations = state.animations === null ? [] : state.animations;
  drawRows(animations);
  byId("installed-none").hidden = state.animations === null || animations.length > 0;
  const silent = state.link === "no-answer";
  byId("space").classList.toggle("stale", silent);
  byId("installed").classList.toggle("stale", silent);
}

// Starts the screen. `message` shows a text in the place for messages.
export function start({message}) {
  byId("confirm-yes").addEventListener("click", () => {
    const animation = asked;
    close();
    if (animation !== null) {
      client.remove(animation, (removed) => message(messages.ofRemoved(removed)));
    }
  });
  byId("confirm-no").addEventListener("click", close);
  client.watch(draw);
}
