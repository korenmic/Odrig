// Clocks only on a target that plays the clocks of both storages: the Clocks level and the
// folders of each storage's Clocks subtree, Back, play and restart, the line of the animation
// playing now, and an upload of each kind, single, batch and archive, at the level explored.
// The settings give the acts in their order: `mode` the Clocks dropdown of Settings, `enter` a
// folder row by its id, `back`, `play` a row by its id, `restart`, `refresh` the list, `step`
// the test, `wait` some milliseconds, `until` the screen is so, `look`, and `upload`, `batch`
// or `archive` with the files of the media folder, each looked at and sent with `send`; an
// archive's rows may be named anew with `renames`, and the mode changed to `leave` before it is
// looked at.
import {shown} from "../reading.js";
import {listed, pick} from "./batch.js";
import {rows as archiveRows} from "./archive.js";

function look(app, client) {
  const opened = (row) => row.matches("button") ? row : row.querySelector(".folder-open");
  return {
    screen: app.shown(),
    level: app.raw("level-title"),
    backHidden: app.byId("level-back").hidden,
    headMarked: app.byId("level-head").getAttribute("aria-current") === "true",
    unavailable: client.state.onlyUnavailable,
    rootClocks: JSON.stringify(client.state.rootNames?.clocks ?? null),
    folders: [...app.doc.querySelectorAll("#animations-list > .folder-row")].map((row) => ({
      id: Number(row.dataset.id), name: row.querySelector(".name").textContent, storage: row.dataset.storage,
      label: opened(row).getAttribute("aria-label"), open: !opened(row).disabled, marked: row.getAttribute("aria-current") === "true"})),
    rows: [...app.doc.querySelectorAll("#animations-list > .row")].map((row) => ({
      id: Number(row.dataset.id), file: row.dataset.file, external: row.dataset.external === "true", disabled: row.querySelector(".play").disabled})),
    restart: {text: app.raw("play-all"), disabled: app.byId("play-all").disabled},
    boundary: app.text("only-boundary"),
    now: app.raw("now-text"),
    file: app.raw("level-file"),
    mode: app.byId("clocks").value,
    reason: app.raw("clocks-state"),
  };
}

function matches(seen, until) {
  return Object.entries(until).every(([key, value]) => key === "rows" ? seen.rows.length === value :
    key === "folders" ? seen.folders.length === value : key === "files" ? JSON.stringify(seen.rows.map((row) => row.file)) === JSON.stringify(value) :
    key === "names" ? JSON.stringify(seen.folders.map((row) => row.name)) === JSON.stringify(value) : seen[key] === value);
}

function choose(app, id, value) {
  const select = app.byId(id);
  select.value = value;
  select.dispatchEvent(new app.frame.contentWindow.Event("change", {bubbles: true}));
}

// The Upload screen after its capacity came.
async function uploadScreen(app) {
  app.press("Upload");
  await app.until(() => /^Internal storage: Free [0-9]/.test(app.raw("upload-space")), "the storage's capacity");
}

async function single(app, act) {
  await uploadScreen(app);
  await pick(app, "ready-file", [act.file]);
  await app.until(() => app.text("made-facts") !== null || app.text("message-text") !== null, "the ready-made file");
  const select = app.byId("upload-storage");
  const seen = {storage: select.value, externalDisabled: select.options[0].disabled, internalDisabled: select.options[1].disabled,
    uploadDisabled: app.byId("upload-made").disabled, destination: app.text("upload-destination"), reason: app.text("upload-destination-reason")};
  if (act.store !== undefined) {
    choose(app, "upload-storage", act.store);
    seen.stored = select.value;
  }
  if (act.send) {
    app.press("Upload to the installation");
    await app.until(() => app.text("message-text") !== null, "the upload's end", 30000);
    seen.message = app.text("message-text");
    app.byId("message-close").click();
  }
  return seen;
}

async function several(app, act) {
  await uploadScreen(app);
  await pick(app, "ready-file", act.files);
  await app.until(() => app.text("batch-sum") !== null && listed(app).length === act.files.length, "the batch's list");
  const select = app.byId("batch-storage");
  const button = app.byId("batch-upload");
  const seen = {storage: select.value, externalDisabled: select.options[0].disabled, internalDisabled: select.options[1].disabled,
    destination: app.text("batch-destination"), names: listed(app).map((row) => row.name), disabled: button.disabled, reason: app.text("batch-locked-reason")};
  if (act.send) {
    const batch = await app.frame.contentWindow.eval('import("/batch.js")');
    button.click();
    await app.until(() => batch.running(), "the run", 15000);
    await app.until(() => !batch.running(), "the end of the run", 60000);
    seen.rows = listed(app).map((row) => row.state);
  }
  return seen;
}

async function archived(app, act) {
  await uploadScreen(app);
  await pick(app, "archive-file", [act.zip]);
  await app.until(() => app.text("archive-name") !== null || app.text("message-text") !== null, "the archive");
  const select = app.byId("archive-storage");
  const button = app.byId("archive-upload");
  for (const [at, text] of act.renames ?? []) {
    const field = app.doc.querySelectorAll("#archive-rows > li .archive-name")[at];
    field.value = text;
    field.dispatchEvent(new app.frame.contentWindow.Event("input", {bubbles: true}));
  }
  if (act.leave !== undefined) {
    // The mode is changed in Settings, and the archive looked at again on Upload.
    const client = await app.frame.contentWindow.eval('import("/client.js")');
    app.press("Settings");
    await app.until(() => !app.byId("clocks").disabled, "the clocks' dropdown");
    choose(app, "clocks", act.leave);
    await app.until(() => client.state.status?.clockMode === act.leave && !app.byId("clocks").disabled, "the mode confirmed");
    await uploadScreen(app);
  }
  const seen = {storage: select.value, externalDisabled: select.options[0].disabled, internalDisabled: select.options[1].disabled,
    names: archiveRows(app).map((row) => row.name), why: archiveRows(app).map((row) => row.why), disabled: button.disabled, reason: app.text("archive-locked-reason")};
  if (act.send) {
    const batch = await app.frame.contentWindow.eval('import("/batch.js")');
    button.click();
    await app.until(() => batch.running(), "the run", 15000);
    await app.until(() => !batch.running(), "the end of the run", 60000);
    seen.rows = archiveRows(app).map((row) => row.state);
  }
  return seen;
}

export default async function (app) {
  await shown(app, app.settings.rows ?? 0);
  const client = await app.frame.contentWindow.eval('import("/client.js")');
  const seen = {first: look(app, client)};
  for (const act of app.settings.acts ?? []) {
    if (act.mode !== undefined) {
      app.press("Settings");
      await app.until(() => !app.byId("clocks").disabled, "the clocks' dropdown");
      choose(app, "clocks", act.mode);
    }
    if (act.step) await app.step();
    if (act.wait !== undefined) await app.sleep(act.wait);
    if (act.refresh) client.refreshContent();
    if (act.enter !== undefined) app.doc.querySelector(`#animations-list > .folder-row[data-id="${act.enter}"]`).click();
    if (act.back) app.byId("level-back").click();
    if (act.play !== undefined) app.doc.querySelector(`#animations-list > .row[data-id="${act.play}"] .play`).click();
    if (act.restart) app.byId("play-all").click();
    if (act.until !== undefined) await app.until(() => matches(look(app, client), act.until), JSON.stringify(act.until), act.within ?? 15000);
    if (act.look !== undefined) seen[act.look] = look(app, client);
    for (const [kind, run] of [["upload", single], ["batch", several], ["archive", archived]]) {
      if (act[kind] === undefined) continue;
      seen[act[kind].as] = await run(app, act[kind]);
      app.press("Animations");
      await app.until(() => app.shown() === "animations", "Animations again");
    }
  }
  seen.sent = client.state.status === null ? null : client.state.status.clockMode;
  return seen;
}
