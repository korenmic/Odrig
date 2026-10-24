// The operator picks a file on Upload, chooses the fit and the part, and makes the
// animation, or stops making it.

import {shown} from "../reading.js";

export default async function (app) {
  const settings = app.settings;
  await shown(app, settings.rows);
  app.press("Upload");
  await app.until(() => app.shown() === "upload", "Upload");
  // The file is handed to the field as the phone's picker hands it.
  const blob = await (await fetch(`/m/${settings.file}`)).blob();
  const view = app.frame.contentWindow;
  const handed = new view.DataTransfer();
  handed.items.add(new view.File([blob], settings.file, {type: blob.type}));
  const field = app.byId("media");
  field.files = handed.files;
  field.dispatchEvent(new view.Event("change", {bubbles: true}));
  await app.until(() => app.text("media-name") !== null, "the name of the file");
  if (settings.video === true) {
    await app.until(() => /, [0-9.]+ s$/.test(app.text("media-name")), "the length of the video");
  }
  if (settings.fit !== undefined) {
    app.press(settings.fit);
  }
  if (settings.start !== undefined) {
    app.fill("start", settings.start);
  }
  if (settings.length !== undefined) {
    app.fill("length", settings.length);
  }
  const fits = ["fit-fill", "fit-fit", "fit-stretch"].filter((id) => app.byId(id).getAttribute("aria-pressed") === "true");
  app.press("Make the animation");
  if (settings.stop === true) {
    await app.until(() => /Making the animation: [1-9]/.test(app.text("making") || ""), "the making under way");
    app.press("Stop");
    await app.until(() => app.text("making") === "Stopped.", "the making stopped");
    return {making: app.text("making"), facts: app.text("made-facts"), stopShown: app.text("stop-making")};
  }
  await app.until(() => app.text("made-facts") !== null || app.text("message-text") !== null, "the animation or a message", 30000);
  const preview = app.byId("preview");
  return {
    name: app.text("media-name"),
    fits,
    fitSays: app.text("fit-says"),
    facts: app.text("made-facts"),
    message: app.text("message-text"),
    preview: app.text("made-facts") === null ? null : [preview.width, preview.height],
  };
}
