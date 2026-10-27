// Upload: making an animation from a video or a GIF of the phone for the canvas of the
// target, and uploading it as a new animation, to the card when the target may write it
// and the operator keeps that choice, else to the board's own storage.

import * as capacity from "../capacity.js";
import * as client from "../client.js";
import {Refusal} from "../commands.js";
import {NotConverted, Stopped, convert, isGif, stopper, videoLength} from "../convert.js";
import {kilobytes} from "./show.js";
import * as messages from "../messages.js";
import * as previews from "../previews.js";
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

// The file the operator picked, the fit chosen, the conversion under way, the animation
// made last, and the timer of its preview.
let picked = null;
let fit = "fill";
let running = null;
let made = null;
let previewTimer = null;
// The upload under way, or null.
let sending = null;
// Where an upload goes while the card can be written: "card", as at first, or "board".
let storeOn = "card";

function byId(id) {
  return document.getElementById(id);
}

function say(id, text) {
  const place = byId(id);
  place.textContent = text === null ? "" : text;
  place.hidden = text === null;
}

function chooseStore(where) {
  storeOn = where;
  draw(client.state);
}

// Whether an upload cannot begin now: one is under way, a deletion runs, or the target
// does not answer.
function locked() {
  return sending !== null || client.contentBusy() || client.state.link !== "answers";
}

function draw(state) {
  const writable = capacity.cardWritable(state.space);
  byId("upload-space").textContent = `Internal storage: ${capacity.internal(state.space, undefined)}`;
  say("upload-card-space", writable ? capacity.external(state.space, undefined) : null);
  byId("store-on").hidden = !writable;
  for (const where of ["card", "board"]) {
    const button = byId(`store-${where}`);
    button.setAttribute("aria-pressed", String(storeOn === where));
    button.disabled = sending !== null;
  }
  byId("upload-made").disabled = locked();
  byId("upload-space").classList.toggle("stale", state.link === "no-answer");
  byId("upload-card-space").classList.toggle("stale", state.link === "no-answer");
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

// Uploads the animation that was made, with a file name made from the media's name: to
// the card, which gives it its id, when the target may write the card and the operator
// keeps that choice; otherwise as a new item of the board's own storage with the lowest
// free id, when it fits there.
function upload(message) {
  if (made === null || locked()) {
    return;
  }
  const state = client.state;
  const bytes = made.bytes;
  const external = storeOn === "card" && capacity.cardWritable(state.space);
  if (!external && state.space !== null && !fits(bytes.length, state.space.free)) {
    message(messages.ofNoSpace(bytes.length, state.space.free));
    return;
  }
  const listed = state.animations === null ? [] : state.animations;
  const id = external ? null : freeId(new Set([...listed.map((animation) => animation.id), ...state.cycles]));
  const file = fileName(made.file.name, new Set(listed.map((animation) => animation.file)));
  const shown = byId("uploading");
  shown.hidden = false;
  shown.textContent = "Sending: 0%";
  byId("upload-made").hidden = true;
  byId("cancel-upload").hidden = false;
  sending = uploading(
    {id, file, bytes, external},
    {
      report(part, speed) {
        shown.textContent = `Sending: ${Math.floor(part * 100)}%, ${Math.round(speed / 1000)} KB a second`;
      },
      end(how) {
        sending = null;
        byId("upload-made").hidden = false;
        byId("cancel-upload").hidden = true;
        if (how.done) {
          shown.hidden = true;
          message(messages.ofUploaded(external ? how.id : id, file, external));
          previews.makeOwn(bytes);
        } else if (how.cancelled) {
          shown.textContent = "Cancelled.";
        } else {
          shown.hidden = true;
          const error = how.error;
          if (error instanceof Refusal && error.code === "no-space" && external) {
            const card = client.state.space === null ? null : client.state.space.external;
            message(messages.ofNoSpace(bytes.length, card === null || card.free === null ? null : card.free, "the card"));
          } else if (error instanceof Refusal && error.code === "no-space") {
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
  const message = options.message;
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
  byId("upload-made").addEventListener("click", () => upload(message));
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
  byId("store-card").addEventListener("click", () => chooseStore("card"));
  byId("store-board").addEventListener("click", () => chooseStore("board"));
  client.watch(draw);
}
