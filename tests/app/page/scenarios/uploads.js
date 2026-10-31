// The operator makes an animation from a file on Upload, may choose where it is stored,
// and uploads it, or cancels the upload; and then may play it from Animations.

import {playRow, rows, shown, spaceKnown, storage} from "../reading.js";

export default async function (app) {
  const settings = app.settings;
  await shown(app, settings.rows);
  app.press("Upload");
  await app.until(() => app.shown() === "upload" && app.text("upload-space") !== "-", "Upload with the space");
  const blob = await (await fetch(`/m/${settings.file}`)).blob();
  const view = app.frame.contentWindow;
  const handed = new view.DataTransfer();
  handed.items.add(new view.File([blob], settings.file, {type: blob.type}));
  const field = app.byId("media");
  field.files = handed.files;
  field.dispatchEvent(new view.Event("change", {bubbles: true}));
  await app.until(() => app.text("media-name") !== null, "the name of the file");
  app.press("Make the animation");
  await app.until(() => app.text("made-facts") !== null, "the animation", 30000);
  // The named storage choices, including absence, come from the same dropdown.
  const store = app.text("store-on") === null ? null
    : [...app.byId("upload-storage").options].map(option => `${option.textContent}${option.selected ? " (chosen)" : ""}${option.disabled ? " (disabled)" : ""}`);
  const cardSpace = app.text("upload-card-space");
  if (settings.store !== undefined) {
    const selector = app.byId("upload-storage");
    selector.value = settings.store;
    selector.dispatchEvent(new app.frame.contentWindow.Event("change", {bubbles: true}));
  }
  app.press("Upload to the installation");
  const seen = {store, cardSpace};
  if (settings.cancel === true) {
    await app.until(() => /Sending: [0-9]+%, /.test(app.text("uploading") || ""), "the upload under way", 10000);
    app.press("Cancel");
    await app.until(() => app.text("uploading") === "Cancelled.", "the upload cancelled", 10000);
    seen.uploading = app.text("uploading");
    seen.sending = [];
  } else {
    if (settings.hide === true) {
      // The app leaves the screen of the phone while it uploads, and comes back.
      await app.until(() => /Sending: [0-9]+%, /.test(app.text("uploading") || ""), "the upload under way", 10000);
      let hidden = true;
      Object.defineProperty(app.doc, "hidden", {configurable: true, get: () => hidden});
      app.doc.dispatchEvent(new Event("visibilitychange"));
      await app.sleep(400);
      await app.step();
      await app.sleep(2000);
      await app.step();
      hidden = false;
      app.doc.dispatchEvent(new Event("visibilitychange"));
    }
    const progress = [];
    await app.until(() => {
      const now = app.text("uploading");
      if (now !== null && progress[progress.length - 1] !== now) {
        progress.push(now);
      }
      return app.text("message-text") !== null;
    }, "a message after the upload", 30000);
    seen.sending = progress;
  }
  await app.sleep(1500);
  seen.message = app.text("message-text");
  seen.buttons = [...app.doc.querySelectorAll("#made button")].filter((button) => button.getClientRects().length > 0).map((button) => button.textContent.trim());
  app.press("Animations");
  await app.until(() => app.shown() === "animations" && spaceKnown(app), "Animations");
  seen.after = storage(app);
  if (settings.play !== undefined) {
    app.press("OK");
    await app.until(() => rows(app).some((row) => row.text === settings.play), `the row ${settings.play}`);
    playRow(app, Number(settings.play.split(" ")[0]));
    await app.until(() => app.says(`Now ${settings.play.replace(/\./g, "\\.")}`), `${settings.play} on the LEDs`, 8000);
    seen.now = app.text("now");
  }
  return seen;
}
