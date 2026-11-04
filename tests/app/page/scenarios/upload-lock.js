// The Upload screen with a ready-made file chosen, read while the installation answers,
// does not answer, or answers late: what the form, its lines and its button say.

import {shown} from "../reading.js";

function displayed(element) {
  return element.getClientRects().length > 0;
}

// What the form says now.
function snapshot(app) {
  const button = app.byId("upload-made");
  const select = app.byId("upload-storage");
  return {
    buttonShown: displayed(button),
    enabled: displayed(button) && !button.disabled,
    destination: app.text("upload-destination"),
    reason: app.text("upload-destination-reason"),
    storage: select.value,
    externalDisabled: select.options[0].disabled,
    capacity: app.raw("upload-space"),
    capacityStale: app.byId("upload-space").classList.contains("stale"),
  };
}

// Hands the ready-made file of the settings to the picker, as an operator chooses one.
async function chooseReady(app, settings) {
  const response = await fetch(`/m/${settings.file}`);
  if (!response.ok) throw new Error(`fixture fetch failed: ${response.status}`);
  const blob = await response.blob();
  const view = app.frame.contentWindow;
  const handed = new view.DataTransfer();
  handed.items.add(new view.File([blob], settings.file));
  const field = app.byId("ready-file");
  field.files = handed.files;
  field.dispatchEvent(new view.Event("change", {bubbles: true}));
  await app.until(() => app.text("made-facts") !== null || app.text("message-text") !== null, "ready-made preflight");
}

export default async function (app) {
  const settings = app.settings;
  await shown(app, settings.rows);
  app.press("Upload");
  await app.until(() => app.shown() === "upload", "Upload");
  await chooseReady(app, settings);
  const seen = {first: snapshot(app), message: app.text("message-text")};
  if (settings.flow === "space-silent") {
    await app.step();
    await app.until(() => /^External storage/.test(app.text("upload-destination-reason") ?? ""), "the destination line after the reply", 15000);
    seen.after = snapshot(app);
  }
  return seen;
}
