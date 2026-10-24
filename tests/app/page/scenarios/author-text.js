// The operator makes a text on Upload: writes it and sets its fields, sees what a pass
// takes or why the text cannot be made, and the preview move; then uploads it, or cancels
// the upload.

import {shown, spaceKnown, storage} from "../reading.js";

// Sets a field as the operator does: a text, a choice, a colour or a checkbox.
function set(app, id, value) {
  const field = app.byId(id);
  if (field.type === "checkbox") {
    field.checked = value === true;
  } else {
    field.value = String(value);
  }
  field.dispatchEvent(new Event("input", {bubbles: true}));
  field.dispatchEvent(new Event("change", {bubbles: true}));
}

// The preview's picture now, top row first, as `[r, g, b]` for each pixel, with the time
// it shows.
function picture(app) {
  const canvas = app.byId("author-preview");
  const data = canvas.getContext("2d").getImageData(0, 0, canvas.width, canvas.height).data;
  const rgb = [];
  for (let at = 0; at < data.length; at += 4) {
    rgb.push(data[at], data[at + 1], data[at + 2]);
  }
  return {ms: Number(canvas.dataset.ms), width: canvas.width, height: canvas.height, rgb};
}

export default async function (app) {
  const settings = app.settings;
  await shown(app, settings.rows);
  app.press("Upload");
  await app.until(() => app.shown() === "upload" && app.text("upload-space") !== "-", "Upload with the space");
  app.press("Make a text");
  await app.until(() => app.text("author-says") !== null, "the form of a text");
  const seen = {says: []};
  for (const [id, value] of settings.fields || []) {
    set(app, id, value);
    seen.says.push(app.text("author-says"));
  }
  seen.preview = app.text("author-says") !== null && app.byId("author-preview").hidden === false;
  if (seen.preview) {
    const first = picture(app);
    await app.until(() => Number(app.byId("author-preview").dataset.ms) >= first.ms + 300, "the preview moving on");
    seen.pictures = [first, picture(app)];
  }
  if (settings.upload !== true) {
    return seen;
  }
  app.press("Upload to the installation");
  if (settings.cancel === true) {
    await app.until(() => app.text("author-uploading") === "Sending: 0%", "the upload under way");
    await app.sleep(500);
    app.press("Cancel");
    await app.until(() => app.text("author-uploading") === "Cancelled.", "the upload cancelled", 15000);
    seen.uploading = app.text("author-uploading");
    return seen;
  }
  await app.until(() => app.text("message-text") !== null, "a message after the upload", 20000);
  seen.message = app.text("message-text");
  app.press("OK");
  app.press("Animations");
  await app.until(() => app.shown() === "animations" && spaceKnown(app) && storage(app).rows.length === settings.rows + 1, "Animations with the new row", 10000);
  seen.after = storage(app);
  return seen;
}
