// The storage screen: the free storage of the target, the installed animations with their
// sizes, the removal of one, which is asked about first, and making an animation from a
// video or a GIF.

import * as capacity from "../capacity.js";
import * as client from "../client.js";
import {Refusal} from "../commands.js";
import {NotConverted, Stopped, convert, isGif, stopper, videoLength} from "../convert.js";
import * as messages from "../messages.js";
import {fileName, fits, freeId, uploading} from "../upload.js";
import {Failure} from "../target.js";

// What each way of fitting a picture to the canvas does, in words.
const FITS = {
  fill: "The picture covers the whole canvas; what does not fit is cut off at two sides.",
  fit: "All of the picture is on the canvas; the rest of the canvas is black.",
  stretch: "The picture is stretched to the canvas, as wide and as high as it is.",
};
// A number of seconds as the fields take it: whole, or with up to three decimals.
const SECONDS = /^[0-9]{1,6}(?:\.[0-9]{1,3})?$/;

// The animation the open question would remove, or null while none is asked about.
let asked = null;
// The file the operator picked, the fit chosen, the conversion under way, the animation
// made last, and the timer of its preview.
let picked = null;
let fit = "fill";
let running = null;
let made = null;
let previewTimer = null;
// The upload under way, or null.
let sending = null;
const selected = new Set();
let deleting = false;
let awaitingRefresh = null;
let version = -1;
let listed = null;
let message = () => {};

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
  made.dataset.editable = String(typeof animation.ignored === "boolean");
  const words = document.createElement("p");
  const id = document.createElement("span");
  id.className = "id";
  id.textContent = String(animation.id);
  const file = document.createElement("span");
  file.className = "file";
  file.textContent = animation.file;
  const size = document.createElement("span");
  size.className = "size";
  size.textContent = animation.bytes === null ? "size not read yet" : `${kilobytes(animation.bytes)} KB`;
  words.append(id, " ", file, " ", size);
  made.append(words);
  if (typeof animation.ignored !== "boolean") {
    const note = document.createElement("span");
    note.textContent = "Playback only";
    made.append(note);
    return made;
  }
  const label = document.createElement("label");
  label.className = "check";
  const check = document.createElement("input");
  check.type = "checkbox";
  check.addEventListener("change", () => {
    if (check.checked) selected.add(animation.id);
    else selected.delete(animation.id);
    draw(client.state);
  });
  label.append(check, `Select animation ${animation.id}`);
  made.append(label);
  const remove = document.createElement("button");
  remove.type = "button";
  remove.textContent = "Remove";
  remove.addEventListener("click", () => ask(animation));
  made.append(remove);
  return made;
}

// Asks whether the animation is to be removed.
function ask(animation) {
  if (locked()) return;
  asked = {animation, version: client.targetVersion()};
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
    shown.every((made, at) => made.dataset.id === String(animations[at].id) && made.dataset.file === animations[at].file && made.dataset.bytes === String(animations[at].bytes) && made.dataset.editable === String(typeof animations[at].ignored === "boolean"));
  if (!same) {
    place.replaceChildren(...animations.map(row));
  }
}

function locked() {
  return deleting || awaitingRefresh !== null || sending !== null || client.contentBusy() || client.state.link !== "answers";
}

function draw(state) {
  if (version !== client.targetVersion()) {
    version = client.targetVersion();
    selected.clear();
    deleting = false;
    awaitingRefresh = null;
    listed = null;
    close();
    byId("bulk-progress").textContent = "";
  }
  const animations = state.animations === null ? [] : state.animations;
  if (listed !== state.animations) {
    listed = state.animations;
    const ids = new Set(animations.filter(item => typeof item.ignored === "boolean").map(item => item.id));
    for (const id of selected) if (!ids.has(id)) selected.delete(id);
  }
  if (awaitingRefresh !== null && state.listVersion > awaitingRefresh) awaitingRefresh = null;
  byId("bulk-progress").dataset.refreshing = String(awaitingRefresh !== null);
  const counted = capacity.counts(state);
  byId("space").textContent = capacity.internal(state.space, counted.internal);
  byId("external-space").textContent = capacity.external(state.space, counted.external);
  drawRows(animations);
  for (const made of byId("installed").children) {
    const check = made.querySelector("input");
    if (check) {
      check.checked = selected.has(Number(made.dataset.id));
      check.disabled = locked();
    }
    for (const button of made.querySelectorAll("button")) button.disabled = locked();
  }
  byId("select-all").disabled = locked() || !animations.some(item => typeof item.ignored === "boolean");
  byId("clear-selection").disabled = locked() || selected.size === 0;
  byId("delete-selected").disabled = locked() || selected.size === 0;
  byId("upload").disabled = locked();
  byId("installed-none").hidden = state.animations === null || animations.length > 0;
  const silent = state.link === "no-answer";
  byId("space").classList.toggle("stale", silent);
  byId("external-space").classList.toggle("stale", silent);
  byId("installed").classList.toggle("stale", silent);
}

function askSelected() {
  if (locked() || selected.size === 0) return;
  const animations = client.state.animations.filter(item => selected.has(item.id));
  asked = {animations, version: client.targetVersion()};
  byId("confirm-text").textContent = `Delete ${animations.length} animations from internal storage? ` + animations.map(item => `${item.id} ${item.file}`).join(", ");
  byId("confirm").hidden = false;
}

async function deleteSelected(question) {
  const ownVersion = question.version;
  if (ownVersion !== client.targetVersion() || locked()) return;
  const ids = question.animations.map(item => item.id);
  let done = 0;
  deleting = true;
  client.setContentBusy(true);
  try {
    while (done < ids.length) {
      if (ownVersion !== client.targetVersion() || document.hidden) throw new Error("deletion stopped");
      const batch = ids.slice(done, done + 32);
      await client.removeMany(batch);
      if (ownVersion !== client.targetVersion()) return;
      done += batch.length;
      for (const id of batch) selected.delete(id);
      byId("bulk-progress").textContent = `Deleted ${done} of ${ids.length}.`;
    }
    message(`Deleted ${done} animations.`);
  } catch (error) {
    if (ownVersion !== client.targetVersion()) return;
    const detail = error instanceof Refusal ? messages.ofRefusal(error) :
      "No confirmed reply. The last batch may already be deleted. Refreshing the list before another attempt.";
    message(`Deleted ${done} of ${ids.length}. ${detail}`);
  } finally {
    if (ownVersion === client.targetVersion()) {
      deleting = false;
      awaitingRefresh = client.state.listVersion;
      client.setContentBusy(false);
      client.refreshContent();
      draw(client.state);
    }
  }
}

// Milliseconds of a field, or null for an empty field where `empty` allows it. A text
// that is no number throws.
function millisecondsOf(text, empty) {
  const written = text.trim();
  if (written === "" && empty) {
    return null;
  }
  if (!SECONDS.test(written)) {
    throw new NotConverted("bad-part", written);
  }
  return Math.round(Number(written) * 1000);
}

function stopPreview() {
  clearTimeout(previewTimer);
  previewTimer = null;
}

// Draws the pictures of an animation one after the other at their durations, again and
// again. The format keeps the bottom row first; the canvas draws the top row first.
function preview(animation) {
  stopPreview();
  const canvas = byId("preview");
  canvas.width = animation.width;
  canvas.height = animation.height;
  const context = canvas.getContext("2d");
  const drawn = context.createImageData(animation.width, animation.height);
  let at = 0;
  const step = () => {
    const frame = animation.frames[at];
    const picture = frame.picture;
    for (let row = 0; row < animation.height; row += 1) {
      const from = (animation.height - 1 - row) * animation.width * 3;
      const to = row * animation.width * 4;
      for (let column = 0; column < animation.width; column += 1) {
        drawn.data[to + column * 4] = picture[from + column * 3];
        drawn.data[to + column * 4 + 1] = picture[from + column * 3 + 1];
        drawn.data[to + column * 4 + 2] = picture[from + column * 3 + 2];
        drawn.data[to + column * 4 + 3] = 255;
      }
    }
    context.putImageData(drawn, 0, 0);
    at = (at + 1) % animation.frames.length;
    previewTimer = setTimeout(step, frame.ms);
  };
  step();
}

// The animation that was made: its preview and what it is.
function showMade() {
  const animation = made.animation;
  const ms = animation.frames.reduce((sum, frame) => sum + frame.ms, 0);
  byId("made-facts").textContent = `${animation.frames.length} frames, ${(ms / 1000).toFixed(2)} s, ${kilobytes(made.bytes.length)} KB`;
  byId("made").hidden = false;
  preview(animation);
}

function forget() {
  if (sending !== null) {
    return;
  }
  stopPreview();
  made = null;
  byId("made").hidden = true;
  byId("uploading").hidden = true;
}

// Uploads the animation that was made, as a new item with the lowest free id and a file
// name made from the media's name.
function upload(message) {
  if (made === null || locked()) {
    return;
  }
  const state = client.state;
  const bytes = made.bytes;
  if (state.space !== null && !fits(bytes.length, state.space.free)) {
    message(messages.ofNoSpace(bytes.length, state.space.free));
    return;
  }
  const listed = state.animations === null ? [] : state.animations;
  const id = freeId(new Set([...listed.map((animation) => animation.id), ...state.cycles]));
  const file = fileName(made.file.name, new Set(listed.map((animation) => animation.file)));
  const shown = byId("uploading");
  shown.hidden = false;
  shown.textContent = "Sending: 0%";
  byId("upload").hidden = true;
  byId("cancel-upload").hidden = false;
  sending = uploading(
    {id, file, bytes},
    {
      report(part, speed) {
        shown.textContent = `Sending: ${Math.floor(part * 100)}%, ${Math.round(speed / 1000)} KB a second`;
      },
      end(how) {
        sending = null;
        byId("upload").hidden = false;
        byId("cancel-upload").hidden = true;
        if (how.done) {
          shown.hidden = true;
          message(messages.ofUploaded(id, file));
        } else if (how.cancelled) {
          shown.textContent = "Cancelled.";
        } else {
          shown.hidden = true;
          const error = how.error;
          if (error instanceof Refusal && error.code === "no-space") {
            message(messages.ofNoSpace(bytes.length, client.state.space === null ? null : client.state.space.free));
          } else if (error instanceof Refusal) {
            message(messages.ofRefusal(error, client.state.status === null ? null : client.state.status.error));
          } else if (error instanceof Failure) {
            message(messages.ofFailure(error));
          }
        }
      },
      wake: client.wake,
    },
  );
  client.upload(sending);
}

function choose(file) {
  picked = file;
  forget();
  byId("chosen").hidden = false;
  byId("media-name").textContent = file.name;
  if (!isGif(file)) {
    videoLength(file).then((ms) => {
      if (picked === file && ms !== null) {
        byId("media-name").textContent = `${file.name}, ${(ms / 1000).toFixed(2)} s`;
      }
    });
  }
}

function chooseFit(name) {
  fit = name;
  for (const other of Object.keys(FITS)) {
    byId(`fit-${other}`).setAttribute("aria-pressed", String(other === name));
  }
  byId("fit-says").textContent = FITS[name];
}

// Makes the animation of the picked file for the canvas of the target, with the fit and
// the part chosen.
async function make(message) {
  if (picked === null || running !== null) {
    return;
  }
  const status = client.state.status;
  if (status === null || status.width === null || status.height === null) {
    message(messages.ofConversion({reason: "no-canvas"}));
    return;
  }
  let part;
  try {
    part = {fit, startMs: millisecondsOf(byId("start").value, false), lengthMs: millisecondsOf(byId("length").value, true)};
  } catch (error) {
    message(messages.ofConversion(error));
    return;
  }
  forget();
  const making = byId("making");
  making.hidden = false;
  making.textContent = "Making the animation: 0%";
  byId("stop-making").hidden = false;
  running = stopper((done) => {
    making.textContent = `Making the animation: ${Math.floor(done * 100)}%`;
  });
  try {
    made = {...(await convert(picked, {width: status.width, height: status.height}, part, running)), file: picked};
    making.hidden = true;
    showMade();
  } catch (error) {
    if (error instanceof Stopped) {
      making.textContent = "Stopped.";
    } else if (error instanceof NotConverted) {
      making.hidden = true;
      message(messages.ofConversion(error));
    } else {
      throw error;
    }
  } finally {
    running = null;
    byId("stop-making").hidden = true;
  }
}

// Starts the screen. `message` shows a text in the place for messages.
export function start(options) {
  message = options.message;
  byId("select-all").addEventListener("click", () => {
    for (const item of client.state.animations || []) if (typeof item.ignored === "boolean") selected.add(item.id);
    draw(client.state);
  });
  byId("clear-selection").addEventListener("click", () => { selected.clear(); draw(client.state); });
  byId("delete-selected").addEventListener("click", askSelected);
  byId("media").addEventListener("change", () => {
    const files = byId("media").files;
    if (files.length === 1) {
      choose(files[0]);
    }
  });
  for (const name of Object.keys(FITS)) {
    byId(`fit-${name}`).addEventListener("click", () => chooseFit(name));
  }
  chooseFit("fill");
  byId("make").addEventListener("click", () => make(message));
  byId("upload").addEventListener("click", () => upload(message));
  byId("cancel-upload").addEventListener("click", () => {
    if (sending !== null) {
      sending.cancel();
    }
  });
  byId("stop-making").addEventListener("click", () => {
    if (running !== null) {
      running.stop();
    }
  });
  byId("confirm-yes").addEventListener("click", () => {
    const question = asked;
    close();
    if (question === null || question.version !== client.targetVersion()) return;
    if (question.animations) deleteSelected(question);
    else client.remove(question.animation, (removed) => message(messages.ofRemoved(removed)));
  });
  byId("confirm-no").addEventListener("click", close);
  client.watch(draw);
}
