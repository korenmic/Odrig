// The panel Archive on Upload: a zip opened, its rows, their names and ticks, the sum, and the
// upload of the ticked files.
import {shown} from "../reading.js";
import {pick} from "./batch.js";

export function rows(app) {
  return [...app.doc.querySelectorAll("#archive-rows > li")].map((item) => {
    const field = item.querySelector(".archive-name");
    const why = item.querySelector(".archive-why");
    return {path: item.querySelector(".archive-path").textContent, state: item.querySelector(".archive-state").textContent,
      facts: item.querySelector(".archive-facts").textContent, ticked: item.querySelector(".archive-tick").checked,
      tickable: !item.querySelector(".archive-tick").disabled, name: field.hidden ? null : field.value, why: why.hidden ? null : why.textContent,
      replace: !item.querySelector(".archive-replace").hidden};
  });
}

function button(app) {
  const pressed = app.byId("archive-upload");
  return {disabled: pressed.disabled, reason: app.text("archive-locked-reason")};
}

function rename(app, at, text) {
  const field = app.doc.querySelectorAll("#archive-rows > li .archive-name")[at];
  field.value = text;
  field.dispatchEvent(new app.frame.contentWindow.Event("input", {bubbles: true}));
}

export default async function (app) {
  const settings = app.settings;
  await shown(app, settings.rows);
  app.press("Upload");
  await app.until(() => /^Internal storage: Free [0-9]/.test(app.raw("upload-space")), "the storage's capacity");
  await pick(app, "archive-file", [settings.zip]);
  await app.until(() => app.text("archive-name") !== null || app.text("message-text") !== null, "the archive");
  const seen = {name: app.text("archive-name"), message: app.text("message-text"), rows: rows(app), sum: app.text("archive-sum"), button: button(app)};
  if (seen.name === null) return seen;
  if (settings.store !== undefined) {
    const select = app.byId("archive-storage");
    select.value = settings.store;
    select.dispatchEvent(new app.frame.contentWindow.Event("change", {bubbles: true}));
    seen.stored = rows(app).map((row) => row.name);
  }
  for (const [at, text] of settings.renames ?? []) rename(app, at, text);
  if (settings.renames !== undefined) seen.renamed = {rows: rows(app).map((row) => row.why), button: button(app)};
  if (settings.none) {
    app.byId("archive-none").click();
    seen.none = {ticked: rows(app).map((row) => row.ticked), button: button(app)};
    app.byId("archive-all").click();
    seen.all = rows(app).map((row) => row.ticked);
  }
  for (const at of settings.untick ?? []) {
    const box = app.doc.querySelectorAll("#archive-rows > li .archive-tick")[at];
    box.click();
  }
  for (const at of settings.replace ?? []) {
    app.doc.querySelectorAll("#archive-rows > li .archive-replace input")[at].click();
  }
  if (settings.send) {
    const batch = await app.frame.contentWindow.eval('import("/batch.js")');
    seen.before = button(app);
    app.byId("archive-upload").click();
    await app.until(() => batch.running(), "the run", 15000);
    for (const action of settings.actions ?? []) {
      if (action[0] === "row") await app.until(() => new RegExp(action[2]).test(rows(app)[action[1]].state), `row ${action[1]}`, 30000);
      if (action[0] === "stop") app.byId("archive-stop").click();
    }
    await app.until(() => !batch.running(), "the end of the run", 90000);
    seen.after = rows(app).map((row) => row.state);
    seen.line = app.text("batch-line");
  }
  return seen;
}
