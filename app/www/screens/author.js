// Upload: making a text for the canvas of the target, its moving preview, drawn as the
// player draws it, and uploading it as a new animation.

import * as client from "../client.js";
import {Refusal} from "../commands.js";
import {NotConverted, makeContainer, pictureOf, readContainer} from "../convert.js";
import * as messages from "../messages.js";
import {Failure} from "../target.js";
import {fileName, fits, freeId, textName, uploading} from "../upload.js";

// The ending of a container, and how often the preview draws its next picture.
const ENDING = ".odrgx";
const PREVIEW_STEP_MS = 40;

// What the form makes now: its container and what it holds, or why it cannot be made;
// the preview's timer and the moment its time began; and the upload under way.
let made = null;
let refusal = null;
let previewTimer = null;
let previewSince = 0;
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
// carries the time it shows, for whoever checks its pixels.
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
    const picture = pictureOf(made.decoded, ms, 1);
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
      const source = textSource(canvas);
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
  byId("author-says").textContent = made === null ? refusal : `One pass takes ${(made.decoded.header.loopMs / 1000).toFixed(2)} seconds.`;
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

function open() {
  byId("author").hidden = false;
  remake();
  byId("text-words").focus({preventScroll: true});
}

function close() {
  if (sending !== null) {
    return;
  }
  stopPreview();
  byId("author").hidden = true;
}

// Uploads the text that was made as a new item with the lowest free id and a file name
// made from its first words.
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
  const file = fileName(textName(made.source.text), new Set(listed.map((animation) => animation.file)), ENDING);
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

// Starts the part of Upload that makes texts. `message` shows a text in the place for
// messages.
export function start(options) {
  const message = options.message;
  byId("make-text").addEventListener("click", open);
  for (const field of byId("text-form").querySelectorAll("textarea, input, select")) {
    field.addEventListener("input", remake);
    field.addEventListener("change", remake);
  }
  byId("author-upload").addEventListener("click", () => upload(message));
  byId("author-cancel").addEventListener("click", () => {
    if (sending !== null) {
      sending.cancel();
    }
  });
  byId("author-close").addEventListener("click", close);
  client.watch(draw);
}
