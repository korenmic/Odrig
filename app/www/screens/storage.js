// The storage screen: the free storage of the target, the installed animations with their
// sizes, the removal of one, which is asked about first, and making an animation from a
// video or a GIF.

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
  if (made === null || sending !== null) {
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
export function start({message}) {
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
    const animation = asked;
    close();
    if (animation !== null) {
      client.remove(animation, (removed) => message(messages.ofRemoved(removed)));
    }
  });
  byId("confirm-no").addEventListener("click", close);
  client.watch(draw);
}
