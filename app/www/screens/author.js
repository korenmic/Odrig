// Upload: making a text or a clock for the canvas of the target, its moving preview,
// drawn as the player draws it, and uploading it as a new animation.

import * as client from "../client.js";
import {Refusal} from "../commands.js";
import {NotConverted, makeContainer, pictureOf, readContainer} from "../convert.js";
import * as messages from "../messages.js";
import {Failure} from "../target.js";
import {fileName, fits, freeId, textName, uploading} from "../upload.js";

// The ending of a container, and how often the preview draws its next picture.
const ENDING = ".odrgx";
const PREVIEW_STEP_MS = 40;

// Which form is open, "text" or "widget"; what it makes now: its container and what it
// holds, or why it cannot be made; the preview's timer, the moment its time began and the
// seed of a clock's turn; and the upload under way.
let kind = "text";
let made = null;
let refusal = null;
let previewTimer = null;
let previewSince = 0;
let seed = 1;
let sending = null;
// The canvas the container was made for, as `<width>x<height>`, or null.
let madeFor = null;

function byId(id) {
  return document.getElementById(id);
}

// Whether an upload cannot begin now: one is under way, another job holds the target, or
// the target does not answer.
function locked() {
  return sending !== null || client.contentBusy() || client.state.link !== "answers";
}

// A colour of a colour field, `#rrggbb`, as the integer of the JSON sources.
function colourOf(id) {
  return Number.parseInt(byId(id).value.slice(1), 16);
}

// A whole number of a field, or the text as it is when it is none, which the making of the
// container refuses with its words.
function numberOf(id) {
  const written = byId(id).value.trim();
  return /^[0-9]{1,9}$/.test(written) ? Number(written) : written;
}

// The JSON source of the text the form holds, for a canvas.
function textSource(canvas) {
  return {
    version: 1, type: "text", width: canvas.width, height: canvas.height, text: byId("text-words").value,
    font: byId("text-font").value, color: colourOf("text-color"), background: colourOf("text-background"), align: byId("text-align").value,
    valign: byId("text-valign").value, direction: byId("text-direction").value, wrap: byId("text-wrap").checked, effect: byId("text-effect").value,
    motion: byId("text-motion").value, speed: numberOf("text-speed"), pause_ms: numberOf("text-pause"),
  };
}

// The JSON source of the clock the form holds, for a canvas.
function clockSource(canvas) {
  return {
    version: 1, type: "widget", width: canvas.width, height: canvas.height, widget: byId("clock-widget").value, seconds: numberOf("clock-seconds"),
    face: colourOf("clock-face"), hands: colourOf("clock-hands"), rim: colourOf("clock-rim"), background: colourOf("clock-background"),
    speed_min: numberOf("clock-speed-min"), speed_max: numberOf("clock-speed-max"),
  };
}

// A seed for the preview of a clock, as a turn of it on the installation gets one: a
// random number from 1 to 4,294,967,295.
function newSeed() {
  const drawn = new Uint32Array(1);
  do {
    crypto.getRandomValues(drawn);
  } while (drawn[0] === 0);
  return drawn[0];
}

// The canvas of the target, or null while it reports none.
function canvasOf() {
  const status = client.state.status;
  return status === null || status.width === null || status.height === null ? null : {width: status.width, height: status.height};
}

function stopPreview() {
  clearTimeout(previewTimer);
  previewTimer = null;
}

// Draws the picture of the container at the time of the preview, again and again. The
// format keeps the bottom row first; the canvas draws the top row first. The canvas
// carries the time it shows and the seed, for whoever checks its pixels.
function preview() {
  stopPreview();
  const canvas = byId("author-preview");
  const {width, height} = made.decoded.header;
  canvas.width = width;
  canvas.height = height;
  const context = canvas.getContext("2d");
  const drawn = context.createImageData(width, height);
  previewSince = performance.now();
  const step = () => {
    const ms = Math.floor(performance.now() - previewSince);
    const picture = pictureOf(made.decoded, ms, seed);
    for (let row = 0; row < height; row += 1) {
      const from = (height - 1 - row) * width * 3;
      const to = row * width * 4;
      for (let column = 0; column < width; column += 1) {
        drawn.data[to + column * 4] = picture[from + column * 3];
        drawn.data[to + column * 4 + 1] = picture[from + column * 3 + 1];
        drawn.data[to + column * 4 + 2] = picture[from + column * 3 + 2];
        drawn.data[to + column * 4 + 3] = 255;
      }
    }
    context.putImageData(drawn, 0, 0);
    canvas.dataset.ms = String(ms);
    canvas.dataset.seed = String(seed);
    previewTimer = setTimeout(step, PREVIEW_STEP_MS);
  };
  step();
}

// Makes the container of the form again, and says what it is or why it cannot be made.
function remake() {
  const canvas = canvasOf();
  madeFor = canvas === null ? null : `${canvas.width}x${canvas.height}`;
  stopPreview();
  made = null;
  refusal = null;
  if (canvas === null) {
    refusal = messages.ofConversion({reason: "no-canvas"});
  } else {
    try {
      const source = kind === "text" ? textSource(canvas) : clockSource(canvas);
      const bytes = makeContainer(source);
      made = {bytes, decoded: readContainer(bytes), source};
    } catch (error) {
      if (!(error instanceof NotConverted)) {
        throw error;
      }
      refusal = messages.ofConversion(error);
    }
  }
  byId("author-preview").hidden = made === null;
  const seconds = made === null ? 0 : (made.decoded.header.loopMs / 1000).toFixed(2);
  byId("author-says").textContent = made === null ? refusal : kind === "text" ? `One pass takes ${seconds} seconds.` : `One loop takes ${seconds} seconds.`;
  if (made !== null) {
    preview();
  }
  draw(client.state);
}

// Draws what the state changes: whether an upload can begin, and the container again when
// the target reports another canvas.
function draw() {
  const canvas = canvasOf();
  if (!byId("author").hidden && sending === null && (canvas === null ? null : `${canvas.width}x${canvas.height}`) !== madeFor) {
    remake();
    return;
  }
  byId("author-upload").disabled = made === null || locked();
}

// Opens the form of a text or of a clock.
function open(which) {
  if (sending !== null) {
    return;
  }
  kind = which;
  byId("author-title").textContent = kind === "text" ? "A text" : "A clock";
  byId("text-form").hidden = kind !== "text";
  byId("clock-form").hidden = kind !== "widget";
  byId("author").hidden = false;
  seed = newSeed();
  remake();
  byId(kind === "text" ? "text-words" : "clock-widget").focus({preventScroll: true});
}

function close() {
  if (sending !== null) {
    return;
  }
  stopPreview();
  byId("author").hidden = true;
}

// Uploads the text or the clock that was made as a new item with the lowest free id and a
// file name made from a text's first words, or `clock-<kind>`.
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
  const base = kind === "text" ? textName(made.source.text) : `clock-${made.source.widget}`;
  const file = fileName(base, new Set(listed.map((animation) => animation.file)), ENDING);
  const shown = byId("author-uploading");
  shown.hidden = false;
  shown.textContent = "Sending: 0%";
  byId("author-upload").hidden = true;
  byId("author-cancel").hidden = false;
  sending = uploading(
    {id, file, bytes},
    {
      report(part) {
        shown.textContent = `Sending: ${Math.floor(part * 100)}%`;
      },
      end(how) {
        sending = null;
        byId("author-upload").hidden = false;
        byId("author-cancel").hidden = true;
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
        draw(client.state);
      },
      wake: client.wake,
    },
  );
  client.upload(sending);
  draw(client.state);
}

// Starts the part of Upload that makes texts and clocks. `message` shows a text in the
// place for messages.
export function start(options) {
  const message = options.message;
  byId("make-text").addEventListener("click", () => open("text"));
  byId("make-clock").addEventListener("click", () => open("widget"));
  for (const field of byId("author").querySelectorAll("textarea, input, select")) {
    field.addEventListener("input", remake);
    field.addEventListener("change", remake);
  }
  byId("clock-seed").addEventListener("click", () => {
    seed = newSeed();
    remake();
  });
  byId("author-upload").addEventListener("click", () => upload(message));
  byId("author-cancel").addEventListener("click", () => {
    if (sending !== null) {
      sending.cancel();
    }
  });
  byId("author-close").addEventListener("click", close);
  client.watch(draw);
}
