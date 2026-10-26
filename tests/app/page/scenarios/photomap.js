// Settings' mapping from a photo: the button and its words, the diagonal offered, a photo
// given to the input, the preview, the words, the choices, Apply, Discard, Other reading,
// and the photo dropped on leaving.
import {shown} from "../reading.js";
import {photoCanvas} from "./photo-analysis.js";

const displayed = (element) => element !== null && !element.hidden && element.getClientRects().length > 0;

// Gives a photo of the wall to the file input, as a file picked on the phone.
async function give(app, options) {
  const canvas = photoCanvas(app, options);
  const blob = await new Promise((resolve) => canvas.toBlob(resolve, options.png === false ? "image/jpeg" : "image/png"));
  const view = app.frame.contentWindow;
  const file = new view.File([blob], options.png === false ? "wall.jpg" : "wall.png", {type: blob.type});
  const transfer = new view.DataTransfer();
  transfer.items.add(file);
  const input = app.byId("photo");
  input.files = transfer.files;
  input.dispatchEvent(new view.Event("change", {bubbles: true}));
}

export default async function(app) {
  const settings = app.settings;
  await shown(app, settings.rows || 2);
  app.press("Settings");
  await app.until(() => app.shown() === "settings", "Settings");
  const seen = {};
  if (settings.unsupported) {
    await app.until(() => app.says("does not support|only supports"), "the mapping explanation");
    seen.hidden = !displayed(app.byId("photo-take"));
    return seen;
  }
  await app.until(() => displayed(app.byId("from-photo")) && !app.byId("from-photo").disabled, "From a photo");
  seen.advice = app.text("photo-advice");
  seen.diagonalOffered = displayed(app.byId("show-diagonal"));
  if (settings.diagonal) {
    app.press("Show the diagonal");
    await app.until(() => !displayed(app.byId("show-diagonal")), "the diagonal showing");
    await app.step();
    seen.diagonalOffered = displayed(app.byId("show-diagonal"));
  }
  await give(app, settings.photo);
  await app.until(() => displayed(app.byId("photo-result")) && app.doc.querySelectorAll("#photo-words li").length > 0, "the result", 15000);
  seen.words = [...app.doc.querySelectorAll("#photo-words li")].map((item) => item.textContent);
  seen.marks = Number(app.byId("photo-preview").dataset.marks);
  seen.previewWidth = app.byId("photo-preview").getBoundingClientRect().width;
  seen.choices = [...app.doc.querySelectorAll("#photo-choices button")].map((button) => [button.textContent, button.getAttribute("aria-pressed")]);
  seen.applyShown = displayed(app.byId("photo-apply"));
  seen.discardWords = app.text("photo-discard");
  if (settings.pick) {
    app.pressIn("#photo-choices", settings.pick);
    seen.picked = [...app.doc.querySelectorAll("#photo-choices button")].map((button) => button.getAttribute("aria-pressed"));
    seen.wordsPicked = [...app.doc.querySelectorAll("#photo-words li")].map((item) => item.textContent);
  }
  if (settings.discard) {
    app.press("Discard");
    seen.hiddenAfterDiscard = !displayed(app.byId("photo-result"));
    seen.inputEmpty = app.byId("photo").value === "";
    return seen;
  }
  if (settings.refused) {
    return seen;
  }
  app.press("Apply");
  await app.until(() => app.says("Saved from the photo|nothing to save|changed on the target|No confirmed reply") && !app.byId("mapping-reload").disabled, "the save said", 15000);
  seen.said = `${app.text("mapping-summary")} ${app.text("mapping-error") || ""} ${app.text("photo-said") || ""}`.trim();
  seen.applyDisabled = app.byId("photo-apply").disabled;
  seen.otherShown = displayed(app.byId("photo-other"));
  await app.step();
  if (settings.other) {
    app.press("Other reading");
    await app.until(() => app.says("Saved from the photo") && !app.byId("mapping-reload").disabled && app.doc.querySelector('#photo-choices button[aria-pressed="true"]') !== app.doc.querySelector("#photo-choices button"), "the other reading saved", 15000);
    seen.otherPicked = [...app.doc.querySelectorAll("#photo-choices button")].map((button) => button.getAttribute("aria-pressed"));
    await app.step();
  }
  // Leaving Settings drops the photo.
  app.press("Animations");
  await app.until(() => app.shown() === "animations", "Animations");
  app.press("Settings");
  await app.until(() => app.shown() === "settings", "Settings again");
  seen.droppedOnLeaving = !displayed(app.byId("photo-result"));
  return seen;
}
