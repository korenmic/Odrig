// Upload: making a text or a clock for the canvas of the target, its moving preview,
// drawn as the player draws it, and uploading it as a new animation; and editing one that
// is installed, read back from the target and saved in its place.

import * as client from "../client.js";
import {Refusal} from "../commands.js";
import {NotConverted, makeContainer, pictureOf, readContainer} from "../convert.js";
import {crc32} from "../crc32.js";
import * as messages from "../messages.js";
import * as previews from "../previews.js";
import {Failure} from "../target.js";
import {fileName, fits, freeId, textName, uploading} from "../upload.js";
import {answers, extend, isEditable} from "./show.js";

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
// The animation the form edits: its id, its file and the CRC-32 of its bytes on the
// target; null while the form makes a new one. Whether its file is being read.
let editing = null;
let reading = false;
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
  byId("author-upload").disabled = made === null || reading || locked();
}

// What the form is about: its title and the words of its button.
function label() {
  byId("author-title").textContent = editing !== null ? `Animation ${editing.id} ${editing.file}` : kind === "text" ? "A text" : "A clock";
  byId("author-upload").textContent = editing !== null ? "Save" : "Upload to the installation";
}

// A colour of the JSON sources as a colour field takes it, `#rrggbb`.
function hexOf(value) {
  return `#${value.toString(16).padStart(6, "0")}`;
}

// Fills the form with what an installed text or clock holds.
function fill(read) {
  const settings = read.settings;
  if (read.type === "text") {
    byId("text-words").value = read.text;
    for (const name of ["font", "effect", "motion", "align", "valign", "direction"]) {
      byId(`text-${name}`).value = settings[name];
    }
    byId("text-wrap").checked = settings.wrap;
    byId("text-color").value = hexOf(settings.color);
    byId("text-background").value = hexOf(settings.background);
    byId("text-speed").value = String(settings.speed);
    byId("text-pause").value = String(settings.pause);
  } else {
    byId("clock-widget").value = settings.widget;
    byId("clock-seconds").value = String(settings.seconds);
    for (const name of ["face", "hands", "rim", "background"]) {
      byId(`clock-${name}`).value = hexOf(settings[name]);
    }
    byId("clock-speed-min").value = String(settings.speedMin);
    byId("clock-speed-max").value = String(settings.speedMax);
  }
}

// Shows the form of a text or of a clock.
function showForm(which) {
  kind = which;
  byId("text-form").hidden = kind !== "text";
  byId("clock-form").hidden = kind !== "widget";
  byId("author").hidden = false;
  label();
}

// Edits an installed text or clock: reads its file from the target, fills the form with
// it, and saves it in its place.
async function edit(animation, message, go) {
  if (sending !== null || reading) {
    return;
  }
  go("upload");
  editing = null;
  reading = true;
  stopPreview();
  made = null;
  showForm(animation.type === "widget" ? "widget" : "text");
  byId("author-title").textContent = `Animation ${animation.id} ${animation.file}`;
  byId("author-preview").hidden = true;
  byId("author-says").textContent = "Reading the animation from the installation.";
  draw(client.state);
  const version = client.targetVersion();
  let bytes;
  let read;
  try {
    bytes = await client.readFile(animation.id);
    read = readContainer(bytes);
  } catch (error) {
    reading = false;
    if (version !== client.targetVersion()) {
      return;
    }
    byId("author").hidden = true;
    if (error instanceof Refusal) {
      message(messages.ofRefusal(error));
    } else if (error instanceof Failure) {
      message(messages.ofFailure(error));
    } else if (error instanceof NotConverted) {
      message(messages.ofConversion(error));
    }
    return;
  }
  reading = false;
  if (version !== client.targetVersion()) {
    return;
  }
  fill(read);
  editing = {id: animation.id, file: animation.file, crc: crc32(bytes)};
  showForm(read.type === "widget" ? "widget" : "text");
  seed = newSeed();
  remake();
}

// Opens the form of a text or of a clock.
function open(which) {
  if (sending !== null) {
    return;
  }
  editing = null;
  showForm(which);
  seed = newSeed();
  remake();
  byId(kind === "text" ? "text-words" : "clock-widget").focus({preventScroll: true});
}

function close() {
  if (sending !== null) {
    return;
  }
  stopPreview();
  editing = null;
  byId("author").hidden = true;
}

// Uploads the text or the clock that was made as a new item with the lowest free id and a
// file name made from a text's first words, or `clock-<kind>`; or, for one that is edited,
// in the place of its file, while that file is still the one that was read.
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
  const saving = editing;
  const id = saving !== null ? saving.id : freeId(new Set([...listed.map((animation) => animation.id), ...state.cycles]));
  const base = kind === "text" ? textName(made.source.text) : `clock-${made.source.widget}`;
  const file = saving !== null ? saving.file : fileName(base, new Set(listed.map((animation) => animation.file)), ENDING);
  const shown = byId("author-uploading");
  shown.hidden = false;
  shown.textContent = "Sending: 0%";
  byId("author-upload").hidden = true;
  byId("author-cancel").hidden = false;
  sending = uploading(
    {id, file, bytes, expect: saving === null ? null : saving.crc},
    {
      report(part) {
        shown.textContent = `Sending: ${Math.floor(part * 100)}%`;
      },
      end(how) {
        sending = null;
        byId("author-upload").hidden = false;
        byId("author-cancel").hidden = true;
        if (how.done && saving !== null) {
          shown.hidden = true;
          // What is on the target now is what was saved.
          saving.crc = crc32(bytes);
          message(messages.ofSaved(id, file));
          previews.makeOwn(bytes);
        } else if (how.done) {
          shown.hidden = true;
          message(messages.ofUploaded(id, file));
          previews.makeOwn(bytes);
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
  // An installed text or clock of the board's own storage can be edited from its row.
  extend({menu: (animation) => (isEditable(animation) && (animation.type === "text" || animation.type === "widget") && animation.fault === undefined
    ? [{label: "Edit", act: () => edit(animation, message, options.go), disabled: !answers() || sending !== null || reading}] : [])});
  client.watch(draw);
}
