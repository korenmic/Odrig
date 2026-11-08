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

// Opens the folders of a path on Animations, as the operator browses to a folder of the card.
async function browse(app, path) {
  let entered = "";
  for (const part of (path ?? "").split("/").filter(Boolean)) {
    entered += (entered ? "/" : "") + part;
    const name = entered;
    const button = await app.until(() => app.doc.querySelector(`button[aria-label="Open folder ${name}"]`), "the folder row");
    button.click();
    await app.until(() => app.text("level-title") === name, "the explored folder");
  }
}

function hide(app, hidden) {
  Object.defineProperty(app.doc, "hidden", {configurable: true, value: hidden});
  app.doc.dispatchEvent(new app.frame.contentWindow.Event("visibilitychange"));
}

// Picks the files, presses `Upload <n> animations`, does what the settings ask while the run
// lasts, and gives the rows' states, the line's words as they changed, and what the other
// forms said meanwhile.
async function running(app) {
  const settings = app.settings;
  await shown(app, settings.rows);
  await browse(app, settings.path);
  app.press("Upload");
  await app.until(() => /^Internal storage: Free [0-9]/.test(app.raw("upload-space")), "the storage's capacity");
  await pick(app, "ready-file", settings.files);
  await app.until(() => app.text("batch-sum") !== null && !app.byId("batch-upload").disabled, "the list ready");
  if (settings.store !== undefined) {
    const select = app.byId("batch-storage");
    select.value = settings.store;
    select.dispatchEvent(new app.frame.contentWindow.Event("change", {bubbles: true}));
  }
  const batch = await app.frame.contentWindow.eval('import("/batch.js")');
  const client = await app.frame.contentWindow.eval('import("/client.js")');
  const lines = [];
  const record = () => {
    const line = app.byId("batch-line");
    const words = line.hidden ? null : line.textContent;
    if (words !== null && lines[lines.length - 1] !== words) lines.push(words);
  };
  const recorder = setInterval(record, 10);
  const seen = {};
  const state = (at) => listed(app)[at].state;
  app.byId("batch-upload").click();
  await app.until(() => batch.running(), "the run", 15000);
  for (const action of settings.actions ?? []) {
    const [what, ...rest] = action;
    if (what === "row") await app.until(() => new RegExp(rest[1]).test(state(rest[0])), `row ${rest[0]} ${rest[1]}`, rest[2] ?? 30000);
    else if (what === "line") await app.until(() => lines.includes(rest[0]), `the line ${rest[0]}`, rest[1] ?? 30000);
    else if (what === "step") await app.step();
    else if (what === "hide") hide(app, true);
    else if (what === "show") hide(app, false);
    else if (what === "sleep") await app.sleep(rest[0]);
    else if (what === "stop") app.byId("batch-stop").click();
    else if (what === "target") client.begin();
    else if (what === "elsewhere") {
      app.press("Animations");
      await app.until(() => app.shown() === "animations", "Animations during the run");
      await app.until(() => app.text("batch-line") !== null, "the line on Animations");
      seen.onAnimations = app.text("batch-line");
      seen.deletionLocked = client.contentBusy();
      app.press("Upload");
      await app.until(() => app.shown() === "upload", "Upload again");
    } else if (what === "forms") {
      await pick(app, "ready-file", [settings.files[0]]);
      await app.until(() => app.text("made-facts") !== null, "today's form under the list");
      seen.single = {disabled: app.byId("upload-made").disabled, reason: app.text("upload-locked-reason"), list: app.text("batch-sum") !== null};
      await pick(app, "ready-file", settings.files.slice(0, 2));
      await app.until(() => app.text("message-text") !== null, "the refusal of a second list");
      seen.second = app.text("message-text");
      app.byId("message-close").click();
      app.press("Make a text");
      await app.until(() => app.text("author-locked-reason") !== null, "the text form's line");
      seen.text = {disabled: app.byId("author-upload").disabled, reason: app.text("author-locked-reason")};
      app.press("Close");
    }
  }
  await app.until(() => !batch.running(), "the end of the run", settings.timeout ?? 90000);
  record();
  clearInterval(recorder);
  seen.rows = listed(app).map((row) => row.state);
  seen.lines = lines;
  seen.end = app.text("batch-line");
  seen.retry = app.text("batch-retry");
  if (settings.retry) {
    app.byId("batch-retry").click();
    await app.until(() => batch.running(), "the second run", 15000);
    await app.until(() => !batch.running(), "the end of the second run", settings.timeout ?? 90000);
    seen.retried = listed(app).map((row) => row.state);
    seen.retriedEnd = app.text("batch-line");
  }
  if (settings.tap) {
    app.press("Settings");
    await app.until(() => app.shown() === "settings", "Settings");
    app.byId("batch-line").click();
    await app.until(() => app.shown() === "upload", "Upload after the tap");
    seen.tapped = {screen: app.shown(), line: app.text("batch-line")};
  }
  return seen;
}

// The measures of the list before its run and after it, and where the line stands while
// Animations scrolls.
async function look(app) {
  const {measure} = await import("./look.js");
  await upload(app, app.settings.rows);
  await pick(app, "ready-file", app.settings.files);
  await app.until(() => app.text("batch-sum") !== null && listed(app).length === app.settings.files.length, "the list");
  const before = measure(app);
  const batch = await app.frame.contentWindow.eval('import("/batch.js")');
  app.byId("batch-upload").click();
  await app.until(() => batch.running(), "the run");
  await app.until(() => !batch.running(), "the end of the run", 60000);
  const after = measure(app);
  app.press("Animations");
  await app.until(() => app.shown() === "animations", "Animations");
  app.frame.contentWindow.scrollTo(0, app.doc.documentElement.scrollHeight);
  await app.sleep(100);
  const line = app.byId("batch-line").getBoundingClientRect();
  return {before, after, line: {top: line.top, bottom: line.bottom, shown: line.height > 0}, scrolled: app.frame.contentWindow.scrollY};
}

export default async function (app) {
  if (app.settings.mode === "look") return look(app);
  if (app.settings.mode === "one") return one(app);
  if (app.settings.mode === "run") return running(app);
  return picking(app);
}
