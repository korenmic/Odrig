// The operator makes a clock on Upload: chooses its kind and sets its fields, sees what a
// loop takes and the preview move, asks for a new random time; then uploads it.

import {shown, spaceKnown, storage} from "../reading.js";

function set(app, id, value) {
  const field = app.byId(id);
  field.value = String(value);
  field.dispatchEvent(new Event("input", {bubbles: true}));
  field.dispatchEvent(new Event("change", {bubbles: true}));
}

// The preview's picture now, top row first, as `[r, g, b]` for each pixel, with the time
// and the seed it shows.
function picture(app) {
  const canvas = app.byId("author-preview");
  const data = canvas.getContext("2d").getImageData(0, 0, canvas.width, canvas.height).data;
  const rgb = [];
  for (let at = 0; at < data.length; at += 4) {
    rgb.push(data[at], data[at + 1], data[at + 2]);
  }
  return {ms: Number(canvas.dataset.ms), seed: Number(canvas.dataset.seed), width: canvas.width, height: canvas.height, rgb};
}

export default async function (app) {
  const settings = app.settings;
  await shown(app, settings.rows);
  app.press("Upload");
  await app.until(() => app.shown() === "upload" && app.text("upload-space") !== "-", "Upload with the space");
  app.press("Make a clock");
  await app.until(() => app.text("author-says") !== null, "the form of a clock");
  const seen = {title: app.text("author-title"), says: []};
  for (const [id, value] of settings.fields || []) {
    set(app, id, value);
    seen.says.push(app.text("author-says"));
  }
  if (app.byId("author-preview").hidden) {
    return seen;
  }
  const first = picture(app);
  await app.until(() => Number(app.byId("author-preview").dataset.ms) >= first.ms + 300, "the preview moving on");
  seen.pictures = [first, picture(app)];
  app.press("New random time");
  seen.pictures.push(picture(app));
  if (settings.upload !== true) {
    return seen;
  }
  app.press("Upload to the installation");
  await app.until(() => app.text("message-text") !== null, "a message after the upload", 20000);
  seen.message = app.text("message-text");
  app.press("OK");
  app.press("Animations");
  await app.until(() => app.shown() === "animations" && spaceKnown(app) && storage(app).rows.length === settings.rows + 1, "Animations with the new row", 10000);
  seen.after = storage(app);
  return seen;
}
