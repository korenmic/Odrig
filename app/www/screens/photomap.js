// Settings' mapping from a photo: a photo of the installation showing the diagonal is read,
// its reading shown on the photo and in words, and applied to the mapping on one tap.
import * as client from "../client.js";
import * as mapping from "./mapping.js";
import {SNAKES, analyse, assignment, readPhoto} from "../photo.js";

const ADVICE = "Take the photo from the front with the phone upright, the whole wall in it and the diagonal showing, in a room as dark as can be had.";

// The photo read last: its picture, its reading, the pins the mapping had when it was
// read, the reading shown and the one applied last.
let shown = null;
// A photo is being read.
let busy = false;
let problem = "";
// What the last Apply did, when it saved nothing.
let said = "";

const byId = id => document.getElementById(id);
const same = (a, b) => a.length === b.length && a.every((value, at) => value === b[at]);

function setText(element, text) {
  if (element.textContent !== text) element.textContent = text;
}

function setHidden(element, hidden) {
  if (element.hidden !== hidden) element.hidden = hidden;
}

function setDisabled(element, disabled) {
  if (element.disabled !== disabled) element.disabled = disabled;
}

// The words of a reading's choice: where its gaps at the ends are taken to be.
function choiceWords(reading) {
  const parts = [];
  if (reading.xEnd !== null) parts.push(reading.xEnd === "left" ? "Dark strip at the left" : "Dark strip at the right");
  if (reading.yEnd !== null) parts.push(reading.yEnd === "lowest" ? "Lowest snake missing" : "Highest snake missing");
  return parts.join(" \u00b7 ");
}

// The words of a reading: each position whose snake is not its own, each with none, and
// the spots ignored.
function resultWords(result, reading) {
  const lines = [];
  const filled = new Map(reading.filled.map((entry) => [entry.position, entry.snake]));
  for (let position = 1; position <= SNAKES; position += 1) {
    const snake = reading.positions[position - 1];
    if (snake === null) lines.push(`Position ${position} shows no snake; snake ${filled.get(position)} goes there.`);
    else if (snake !== position) lines.push(`Position ${position} shows snake ${snake}.`);
  }
  if (lines.length === 0) lines.push("Every position shows its own snake.");
  if (result.ignored > 0) lines.push(`${result.ignored} bright ${result.ignored === 1 ? "spot was" : "spots were"} ignored.`);
  return lines;
}

function refusalWords(result) {
  const why = result.why === "few" ? "fewer than two lit LEDs" : "lit LEDs that fit no grid of twenty snakes";
  return [`No reading: ${result.found} bright ${result.found === 1 ? "spot" : "spots"} found, and ${why}.`, ADVICE];
}

// Draws the photo with the chosen reading on it: a circle and the snake's number at each
// stub, a dashed circle at a position with no stub, with the number it gets.
function drawPreview() {
  const canvas = byId("photo-preview");
  const {picture, result} = shown;
  if (canvas.width !== picture.width || canvas.height !== picture.height) {
    canvas.width = picture.width;
    canvas.height = picture.height;
  }
  const context = canvas.getContext("2d");
  const image = context.createImageData(picture.width, picture.height);
  for (let at = 0, pixel = 0; pixel < picture.grey.length; at += 4, pixel += 1) {
    image.data[at] = image.data[at + 1] = image.data[at + 2] = picture.grey[pixel];
    image.data[at + 3] = 255;
  }
  context.putImageData(image, 0, 0);
  if (result.refused) {
    canvas.dataset.marks = "0";
    return;
  }
  const reading = result.readings[shown.chosen];
  const radius = Math.max(6, result.frame.pitch * 2.2);
  context.lineWidth = Math.max(1.5, radius / 8);
  context.font = `bold ${Math.round(Math.max(11, radius * 0.9))}px sans-serif`;
  context.textAlign = "center";
  context.textBaseline = "middle";
  let marks = 0;
  const filled = new Map(reading.filled.map((entry) => [entry.position, entry.snake]));
  for (let position = 1; position <= SNAKES; position += 1) {
    const snake = reading.positions[position - 1] ?? filled.get(position);
    const missing = reading.positions[position - 1] === null;
    const {x, y} = result.frame.point(position, snake, reading);
    context.setLineDash(missing ? [4, 3] : []);
    context.strokeStyle = missing ? "#ffb347" : "#45e0d2";
    context.beginPath();
    context.arc(x, y, radius, 0, 2 * Math.PI);
    context.stroke();
    context.fillStyle = missing ? "#ffb347" : "#45e0d2";
    context.fillText(String(snake), x, y - radius - Math.max(7, radius * 0.6));
    marks += 1;
  }
  canvas.dataset.marks = String(marks);
}

function drawChoices() {
  const place = byId("photo-choices");
  const {result} = shown;
  if (result.refused || result.readings.length < 2) {
    if (place.childElementCount !== 0) place.replaceChildren();
    setHidden(place, true);
    setHidden(byId("photo-choices-note"), true);
    return;
  }
  const key = result.readings.map(choiceWords).join("|");
  if (place.dataset.key !== key) {
    place.dataset.key = key;
    place.replaceChildren(...result.readings.map((reading, at) => {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = choiceWords(reading);
      button.addEventListener("click", () => {
        if (shown === null) return;
        shown.chosen = at;
        draw();
      });
      return button;
    }));
  }
  [...place.children].forEach((button, at) => button.setAttribute("aria-pressed", String(at === shown.chosen)));
  setHidden(place, false);
  setHidden(byId("photo-choices-note"), false);
}

export function draw() {
  const current = mapping.mapping();
  const editable = current !== null && current.editable === true;
  setHidden(byId("photo-take"), !editable);
  setHidden(byId("show-diagonal"), !editable || current.test === true);
  setDisabled(byId("from-photo"), busy || !editable);
  setText(byId("photo-advice"), busy ? "Reading the photo\u2026" : ADVICE);
  setHidden(byId("photo-result"), shown === null);
  const error = problem;
  setText(byId("photo-error"), error);
  setHidden(byId("photo-error"), error === "");
  setText(byId("photo-said"), said);
  setHidden(byId("photo-said"), said === "");
  if (shown === null) return;
  const {result} = shown;
  drawPreview();
  const lines = result.refused ? refusalWords(result) : resultWords(result, result.readings[shown.chosen]);
  const list = byId("photo-words");
  if ([...list.children].map((item) => item.textContent).join("\n") !== lines.join("\n")) {
    list.replaceChildren(...lines.map((line) => {
      const item = document.createElement("li");
      item.textContent = line;
      return item;
    }));
  }
  drawChoices();
  const saving = mapping.saving();
  setHidden(byId("photo-apply"), result.refused);
  setDisabled(byId("photo-apply"), !editable || saving || shown.applied === shown.chosen);
  setHidden(byId("photo-other"), result.refused || result.readings.length < 2 || shown.applied === null);
  setDisabled(byId("photo-other"), !editable || saving);
  setText(byId("photo-discard"), result.refused ? "Try another photo" : "Discard");
}

function discard() {
  shown = null;
  problem = "";
  said = "";
  byId("photo").value = "";
  draw();
}

async function read(file) {
  const current = mapping.mapping();
  if (busy || current === null || current.editable !== true) return;
  busy = true;
  problem = "";
  said = "";
  shown = null;
  draw();
  try {
    const picture = await readPhoto(file);
    const result = analyse(picture);
    shown = {picture, result, pins: [...current.pins], chosen: 0, applied: null};
  } catch (_) {
    problem = "The picture could not be read. Choose a photo of the wall as a JPEG or a PNG.";
  } finally {
    busy = false;
    byId("photo").value = "";
    draw();
  }
}

function apply(at) {
  if (shown === null || shown.result.refused) return;
  const current = mapping.mapping();
  if (current === null || current.editable !== true) return;
  const reading = shown.result.readings[at];
  const next = assignment(shown.pins, reading);
  said = "";
  if (same(next, current.pins)) {
    // The mapping is as this reading says already.
    shown.chosen = at;
    shown.applied = at;
    said = "The mapping is as this reading says already; nothing to save.";
  } else if (mapping.saveFromPhoto(next)) {
    shown.chosen = at;
    shown.applied = at;
  }
  draw();
}

export function showing(visible) {
  if (!visible) discard();
}

export function start() {
  byId("from-photo").addEventListener("click", () => {
    byId("photo").click();
  });
  byId("photo").addEventListener("change", () => {
    const files = byId("photo").files;
    if (files.length === 1) read(files[0]);
  });
  byId("show-diagonal").addEventListener("click", () => {
    client.mappingTest(true).catch(() => {
      problem = "The installation did not start the diagonal.";
      draw();
    });
  });
  byId("photo-apply").addEventListener("click", () => apply(shown === null ? 0 : shown.chosen));
  byId("photo-other").addEventListener("click", () => {
    if (shown === null || shown.applied === null) return;
    apply((shown.applied + 1) % shown.result.readings.length);
  });
  byId("photo-discard").addEventListener("click", () => {
    const refused = shown !== null && shown.result.refused;
    discard();
    if (refused) byId("photo").click();
  });
  client.watch(() => {
    if (shown !== null && mapping.mapping() === null) shown = null;
    draw();
  });
}
