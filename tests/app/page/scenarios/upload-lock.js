// The Upload screen with a ready-made file chosen, read while the installation answers,
// does not answer, or answers late, and while the app is busy: what the form, its lines
// and its button say.

import {shown, startSelection} from "../reading.js";

function displayed(element) {
  return element.getClientRects().length > 0;
}

// The words of the line under the button, or null while it is not on the screen.
function lockOf(app) {
  const line = app.doc.getElementById("upload-locked-reason");
  return line === null || !displayed(line) ? null : line.textContent.trim();
}

// What the form says now, and the look of the line under the button while it is shown:
// its colour and size beside those of the capacity line, its right edge, and the width
// of the view and of the page.
function snapshot(app) {
  const button = app.byId("upload-made");
  const select = app.byId("upload-storage");
  const space = app.byId("upload-space");
  const view = app.frame.contentWindow;
  const line = app.doc.getElementById("upload-locked-reason");
  const lock = lockOf(app);
  let look = null;
  if (lock !== null) {
    const own = view.getComputedStyle(line);
    const other = view.getComputedStyle(space);
    look = {colour: own.color, size: parseFloat(own.fontSize), spaceColour: other.color, spaceSize: parseFloat(other.fontSize),
      right: line.getBoundingClientRect().right, width: view.innerWidth, scrollWidth: app.doc.documentElement.scrollWidth};
  }
  return {
    buttonShown: displayed(button),
    enabled: displayed(button) && !button.disabled,
    lock,
    describedBy: button.getAttribute("aria-describedby"),
    look,
    destination: app.text("upload-destination"),
    reason: app.text("upload-destination-reason"),
    storage: select.value,
    externalDisabled: select.options[0].disabled,
    capacity: app.raw("upload-space"),
    capacityStale: space.classList.contains("stale"),
    message: app.text("message-text"),
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

const SILENT = /^The installation does not answer\./;

export default async function (app) {
  const settings = app.settings;
  await shown(app, settings.rows);
  app.press("Upload");
  await app.until(() => app.shown() === "upload", "Upload");
  await chooseReady(app, settings);
  const seen = {first: snapshot(app)};
  if (settings.flow === "space-silent") {
    // The request for the capacity gets no reply: the line names the silence until the
    // next status answers.
    await app.until(() => SILENT.test(lockOf(app) ?? ""), "the line naming the silence", 12000);
    seen.silent = snapshot(app);
    await app.step();
    await app.until(() => /^External storage/.test(app.text("upload-destination-reason") ?? "") && !app.byId("upload-made").disabled, "the destination line after the reply", 15000);
    seen.after = snapshot(app);
  } else if (settings.flow === "status-fails") {
    await app.step();
    await app.until(() => SILENT.test(lockOf(app) ?? ""), "the line naming the failure", 8000);
    seen.failing = snapshot(app);
    await app.step();
    await app.until(() => !app.byId("upload-made").disabled, "the button enabled again", 8000);
    seen.again = snapshot(app);
  } else if (settings.flow === "deletion") {
    app.press("Animations");
    await app.until(() => app.shown() === "animations", "Animations");
    if (startSelection(app) === null) throw new Error("no row offers Select");
    await app.until(() => displayed(app.byId("delete-selected")), "the selection bar");
    app.tap("delete-selected");
    await app.until(() => app.text("confirm-text") !== null, "the question");
    app.tap("confirm-yes");
    app.press("Upload");
    await app.until(() => app.shown() === "upload", "Upload during the deletion");
    await app.until(() => /^A deletion is under way/.test(lockOf(app) ?? ""), "the line naming the deletion", 8000);
    seen.deleting = snapshot(app);
    await app.until(() => !app.byId("upload-made").disabled, "the button enabled after the deletion", 12000);
    seen.after = snapshot(app);
  } else if (settings.flow === "preflight") {
    await app.step();
    app.press("Upload to the installation");
    await app.until(() => /^Checking the destination/.test(lockOf(app) ?? ""), "the line naming the check", 8000);
    seen.checking = snapshot(app);
    await app.until(() => app.text("message-text") !== null, "upload acknowledgement", 30000);
    seen.done = snapshot(app);
  }
  return seen;
}
