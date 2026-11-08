// Ready-made files picked several at once on Upload: the list of them, its names, its sum
// and its button, and the run that sends them one after another.
import {shown} from "../reading.js";

// Hands files of the media folder to a file input of the app, as the phone's chooser does,
// each under the name it is picked by.
export async function pick(app, input, files) {
  const view = app.frame.contentWindow;
  const handed = new view.DataTransfer();
  for (const file of files) {
    const [served, name] = Array.isArray(file) ? file : [file, file];
    const response = await fetch(`/m/${encodeURIComponent(served)}`);
    if (!response.ok) throw new Error(`fixture fetch failed: ${response.status}`);
    handed.items.add(new view.File([await response.blob()], name));
  }
  const field = app.byId(input);
  field.files = handed.files;
  field.dispatchEvent(new view.Event("change", {bubbles: true}));
}

// What each row of the list shows: its name (or the field's text), its state and why its
// name cannot be taken.
export function listed(app) {
  return [...app.doc.querySelectorAll("#batch-rows > li")].map((row) => {
    const field = row.querySelector(".batch-name");
    return {name: field === null || field.hidden ? row.querySelector(".batch-file").textContent : field.value,
      state: row.querySelector(".batch-state").textContent, why: row.querySelector(".batch-why")?.hidden === false ? row.querySelector(".batch-why").textContent : null};
  });
}

export function rename(app, at, text) {
  const field = app.doc.querySelectorAll("#batch-rows > li .batch-name")[at];
  field.value = text;
  field.dispatchEvent(new app.frame.contentWindow.Event("input", {bubbles: true}));
}

// The button of the list and the line under it.
export function button(app) {
  const pressed = app.byId("batch-upload");
  return {words: pressed.textContent, disabled: pressed.disabled, reason: app.text("batch-locked-reason")};
}

export async function upload(app, rows) {
  await shown(app, rows);
  app.press("Upload");
  await app.until(() => /^Internal storage: Free [0-9]/.test(app.raw("upload-space")), "the storage's capacity");
}

async function picking(app) {
  const settings = app.settings;
  await upload(app, settings.rows);
  const seen = {chooser: [...app.doc.querySelectorAll('label[for="ready-file"]')].map((label) => label.textContent.trim()), multiple: app.byId("ready-file").multiple};
  await pick(app, "ready-file", settings.first);
  await app.until(() => app.text("batch-sum") !== null, "the list");
  seen.listed = listed(app);
  seen.formHidden = app.byId("made").hidden || app.text("made-facts") === null;
  seen.sum = app.text("batch-sum");
  seen.button = button(app);
  if (settings.more !== undefined) {
    await pick(app, "batch-more", settings.more);
    await app.until(() => listed(app).length !== seen.listed.length, "the list after Add more");
    seen.more = listed(app);
    seen.sumMore = app.text("batch-sum");
  }
  if (settings.renames !== undefined) {
    seen.renamed = [];
    for (const [at, text] of settings.renames) {
      rename(app, at, text);
      seen.renamed.push({rows: listed(app).map((row) => row.why), button: button(app)});
    }
  }
  if (settings.store !== undefined) {
    seen.storage = app.byId("batch-storage").value;
    const select = app.byId("batch-storage");
    select.value = settings.store;
    select.dispatchEvent(new app.frame.contentWindow.Event("change", {bubbles: true}));
    seen.afterStore = listed(app).map((row) => row.name);
    seen.destination = app.text("batch-destination");
  }
  if (settings.remove !== undefined) {
    for (const at of settings.remove) {
      app.doc.querySelectorAll("#batch-rows > li .batch-remove")[at].click();
    }
    seen.afterRemove = listed(app).map((row) => row.name);
    seen.listShown = app.text("batch-sum") !== null;
  }
  return seen;
}

async function one(app) {
  await upload(app, app.settings.rows);
  await pick(app, "ready-file", [app.settings.file]);
  await app.until(() => app.text("made-facts") !== null || app.text("message-text") !== null, "today's form");
  return {facts: app.text("made-facts"), list: app.text("batch-sum"), button: app.text("upload-made")};
}

export default async function (app) {
  if (app.settings.mode === "one") return one(app);
  return picking(app);
}
