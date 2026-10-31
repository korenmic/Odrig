import {shown} from "../reading.js";

export default async function (app) {
  const settings = app.settings;
  await shown(app, settings.rows);
  let entered = "";
  for (const part of (settings.path ?? "").split("/").filter(Boolean)) {
    entered += (entered ? "/" : "") + part;
    const path = entered;
    const button = await app.until(() => app.doc.querySelector(`button[aria-label="Open folder ${path}"]`), "the folder row");
    button.click();
    await app.until(() => app.text("level-title") === path, "the explored folder");
  }
  app.press("Upload");
  const response = await fetch(`/m/${settings.file}`);
  if (!response.ok) throw new Error(`fixture fetch failed: ${response.status}`);
  const blob = await response.blob();
  const view = app.frame.contentWindow;
  const handed = new view.DataTransfer();
  handed.items.add(new view.File([blob], settings.name ?? settings.file));
  const field = app.byId("ready-file");
  field.files = handed.files;
  field.dispatchEvent(new view.Event("change", {bubbles: true}));
  await app.until(() => app.text("made-facts") !== null || app.text("message-text") !== null, "ready-made preflight");
  const seen = {facts: app.text("made-facts"), message: app.text("message-text")};
  if (seen.message !== null) return seen;
  const select = app.byId("upload-storage");
  seen.default = select.value;
  seen.externalDisabled = select.options[0].disabled;
  if (settings.store !== undefined) {
    select.value = settings.store;
    select.dispatchEvent(new view.Event("change", {bubbles: true}));
  }
  if (settings.basename !== undefined) app.fill("upload-name", settings.basename);
  seen.destination = app.text("upload-destination");
  seen.reason = app.text("upload-destination-reason");
  seen.preview = app.text("ready-preview-note");
  if (settings.navigate === true) {
    app.press("Animations");
    await app.until(() => app.shown() === "animations", "Animations after preparing");
    app.press("Back");
    await app.until(() => app.text("level-title") !== settings.path, "a different browsing level");
    app.press("Upload");
    await app.until(() => app.shown() === "upload", "Upload after navigation");
    seen.afterNavigation = app.text("upload-destination");
  }
  if (settings.send === false) return seen;
  app.press("Upload to the installation");
  await app.until(() => app.text("message-text") !== null, "upload acknowledgement", settings.timeout ?? 30000);
  seen.message = app.text("message-text");
  return seen;
}
