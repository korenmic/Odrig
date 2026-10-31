// New animations: converted media or original ready-made bytes, with a visible destination.

import * as capacity from "../capacity.js";
import * as client from "../client.js";
import {Refusal} from "../commands.js";
import {NotConverted, Stopped, convert, isGif, stopper, videoLength} from "../convert.js";
import {kilobytes} from "./show.js";
import * as messages from "../messages.js";
import * as previews from "../previews.js";
import {crc32} from "../crc32.js";
import * as destinations from "../upload-destination.js";
import {prepare} from "../ready.js";
import {fileName, freeId, uploading} from "../upload.js";
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
// The captured destination and the serialized preflight, before a job owns the transfer.
let form = null;
let preparing = false;

function byId(id) {
  return document.getElementById(id);
}

function say(id, text) {
  const place = byId(id);
  place.textContent = text === null ? "" : text;
  place.hidden = text === null;
}

function chooseStore(where) {
  if (form === null || sending !== null || preparing) return;
  destinations.select(form, where, client.state.space);
  draw(client.state);
}

// Whether an upload cannot begin now: one is under way, a deletion runs, or the target
// does not answer.
function locked() {
  return preparing || sending !== null || client.contentBusy() || client.state.link !== "answers";
}

function draw(state) {
  byId("upload-space").textContent = `Internal storage: ${capacity.internal(state.space, undefined)}`;
  say("upload-card-space", capacity.external(state.space, undefined));
  const frozen = sending !== null || preparing;
  if (form !== null) {
    if (!frozen) destinations.synchronize(form, state.space);
    for (const storage of ["internal", "external"]) {
      if (form.generations[storage] === null && state.catalog?.[storage]?.generation != null) form.generations[storage] = state.catalog[storage].generation;
    }
    const selector = byId("upload-storage");
    selector.value = form.storage;
    selector.options[0].disabled = !destinations.present(state.space);
    selector.disabled = frozen;
    byId("upload-destination").textContent = destinations.label(form, byId("upload-name").value);
    byId("upload-destination-reason").textContent = frozen && form.storage === "external" && !destinations.present(state.space)
      ? "External storage disconnected. This attempt keeps its original destination and will not move to Internal."
      : destinations.reason(form, state.space);
  }
  for (const id of ["upload-name", "media", "ready-file", "make"]) byId(id).disabled = frozen;
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
  if (byId("upload-name").value === "") {
    const taken = made.ready ? new Set() : new Set((client.state.animations ?? []).map(item => item.file.slice(item.file.lastIndexOf("/") + 1)));
    byId("upload-name").value = fileName(made.file.name, taken, made.ending ?? ".odrg");
  }
  byId("preview").hidden = made.ready === true;
  byId("ready-preview").hidden = true;
  byId("ready-preview-note").hidden = made.ready !== true;
  byId("made").hidden = false;
  if (made.ready) {
    const header = made.header;
    byId("made-facts").textContent = `Ready-made animation, ${header.width} \u00d7 ${header.height}, ${kilobytes(made.bytes.length)} KB. Original bytes, without conversion.`;
    if (made.previewSafe) previews.makeOwn(made.bytes);
    readyPreview();
    draw(client.state);
    return;
  }
  const animation = made.animation;
  const ms = animation.frames.reduce((sum, frame) => sum + frame.ms, 0);
  byId("made-facts").textContent = `${animation.frames.length} frames, ${(ms / 1000).toFixed(2)} s, ${kilobytes(made.bytes.length)} KB`;
  byId("made").hidden = false;
  preview(animation);
  draw(client.state);
}

function readyPreview() {
  if (!made?.ready) return;
  const source = previews.sourceOf(made.key);
  const image = byId("ready-preview");
  image.hidden = source === null;
  if (source !== null) image.src = source;
  byId("ready-preview-note").textContent = source === null
    ? "No preview available yet. The original bytes are kept; the target checks the complete animation before installing."
    : "Preview from the animation catalog. The original animation bytes are kept.";
}

function forget() {
  if (sending !== null) {
    return;
  }
  stopPreview();
  made = null;
  byId("upload-name").value = "";
  byId("made").hidden = true;
  byId("uploading").hidden = true;
}

// Revalidates the displayed destination and uploads a new file after its creation guard.
async function upload(message) {
  if (made === null || locked()) {
    return;
  }
  const prepared = made;
  const captured = form;
  const bytes = prepared.bytes;
  preparing = true;
  client.setContentBusy(true);
  draw(client.state);
  try {
  const fresh = await client.uploadSnapshot(captured.storage === "external" ? captured.level : {path: "", id: null});
  if (form !== captured || made !== prepared) throw new Error("The selected animation changed. Prepare it again.");
  if (destinations.synchronize(captured, fresh.space)) {
    message(`The destination changed to ${destinations.label(captured, byId("upload-name").value)}. Review it and press Upload again.`);
    return;
  }
  const checked = destinations.validate(captured, fresh, byId("upload-name").value, bytes.length, client.targetVersion());
  const {external, path: file} = checked;
  if (checked.noSpace !== undefined) {
    message(messages.ofNoSpace(bytes.length, checked.noSpace, external ? "the card" : undefined));
    return;
  }
  const id = external ? null : freeId(new Set(fresh.root.map(item => item.id)));
  if (!external && id === null) throw new Error("Internal storage has no free animation id.");
  const shown = byId("uploading");
  shown.hidden = false;
  shown.textContent = "Sending: 0%";
  byId("upload-made").hidden = true;
  byId("cancel-upload").hidden = false;
  sending = uploading(
    {id, file, bytes, external, create: true, expect: external ? "00000000" : null},
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
          if (!prepared.ready || prepared.previewSafe) previews.makeOwn(bytes);
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
          } else if (error instanceof Refusal && !external && ["unsupported", "stale"].includes(error.code)) {
            message("The chosen id was taken, or the firmware cannot confirm a safe new upload. No file bytes were sent. Select the file again or update the firmware.");
          } else if (error instanceof Refusal && external && ["bad-argument", "unknown-command", "no-upload", "stale"].includes(error.code)) {
            message("The destination changed, already exists, or the firmware lacks safe folder uploads. Check the folder and filename, or update the firmware. Nothing was acknowledged as installed.");
          } else if (error instanceof Refusal) {
            message(messages.ofRefusal(error, client.state.status === null ? null : client.state.status.error));
          } else if (error instanceof Failure) {
            message(`${messages.ofFailure(error)} The upload was not acknowledged as installed; check the destination before retrying.`);
          }
        }
      },
      wake: client.wake,
    },
  );
  client.upload(sending);
  } catch (error) {
    if (error instanceof Refusal) message(messages.ofRefusal(error, client.state.status?.error ?? null));
    else if (error instanceof Failure) message(messages.ofFailure(error));
    else message(error.message);
  } finally {
    preparing = false;
    client.setContentBusy(false);
    draw(client.state);
  }
}

function choose(file) {
  if (sending !== null || preparing) return;
  if (running !== null) running.stop();
  picked = file;
  forget();
  form = destinations.capture(client.state, client.targetVersion());
  byId("media-controls").hidden = false;
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

async function chooseReady(file, message) {
  if (sending !== null || preparing) return;
  if (running !== null) running.stop();
  picked = file;
  forget();
  form = destinations.capture(client.state, client.targetVersion());
  const captured = form;
  byId("chosen").hidden = false;
  byId("media-controls").hidden = true;
  byId("media-name").textContent = file.name;
  try {
    const prepared = await prepare(file, client.state.status);
    if (picked !== file || form !== captured) return;
    made = {...prepared, key: `${crc32(prepared.bytes)}-${prepared.bytes.length}`};
    showMade();
  } catch (error) {
    if (picked === file && form === captured) message(`Cannot use this animation: ${error.message}`);
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
    const source = picked;
    const captured = form;
    const converted = await convert(source, {width: status.width, height: status.height}, part, running);
    if (picked !== source || form !== captured) return;
    made = {...converted, file: source};
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
      const file = files[0];
      byId("media").value = "";
      choose(file);
    }
  });
  byId("ready-file").addEventListener("change", () => {
    const files = byId("ready-file").files;
    if (files.length === 1) {
      const file = files[0];
      byId("ready-file").value = "";
      chooseReady(file, message);
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
  byId("upload-storage").addEventListener("change", () => chooseStore(byId("upload-storage").value));
  byId("upload-name").addEventListener("input", () => draw(client.state));
  previews.watch(readyPreview);
  client.watch(draw);
}
