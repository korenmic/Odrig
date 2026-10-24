// The operator turns the test animations on in Settings, starts tests from the Tests group
// of Animations, and stops them.

import {playRow, rows, shown} from "../reading.js";

const entries = (app) => [...app.doc.querySelectorAll("#tests-grid button")].filter((button) => button.getClientRects().length > 0).map((button) => button.textContent);

export default async function (app) {
  const settings = app.settings;
  await shown(app, settings.rows);
  const seen = {hidden: app.byId("tests").hidden, entriesOff: entries(app), rowsBefore: rows(app).map((row) => row.id)};
  if (settings.watch) {
    // Another controller's test is named here, with the group hidden.
    await app.until(() => app.text("test-now-text") !== null, "the test of another controller", 8000);
    seen.named = app.text("test-now-text");
    app.press("Stop test");
    await app.until(() => app.text("test-now-text") === null, "the test stopped", 8000);
    seen.after = app.text("test-now-text");
    return seen;
  }
  app.press("Settings");
  await app.until(() => app.shown() === "settings", "Settings");
  seen.checkbox = {checked: app.byId("show-tests").checked, label: app.byId("show-tests").closest("label").innerText.replace(/\s+/g, " ").trim()};
  app.byId("show-tests").click();
  app.press("Animations");
  await app.until(() => app.shown() === "animations" && entries(app).length === 21, "the Tests group", 8000);
  seen.entries = entries(app);
  seen.head = app.byId("tests-toggle").textContent;
  seen.above = app.byId("tests").getBoundingClientRect().bottom <= app.byId("animations-list").getBoundingClientRect().top;
  if (settings.unsupported) {
    await app.until(() => /another one|no test animations/.test(app.text("tests-note") || ""), "the explanation", 8000);
    seen.note = app.text("tests-note");
    seen.disabled = [...app.doc.querySelectorAll("#tests-grid button")].every((button) => button.disabled);
    return seen;
  }
  await app.until(() => [...app.doc.querySelectorAll("#tests-grid button")].every((button) => !button.disabled), "the tests available", 8000);
  await app.reload();
  await shown(app, settings.rows);
  await app.until(() => entries(app).length === 21 && [...app.doc.querySelectorAll("#tests-grid button")].every((button) => !button.disabled), "the Tests group after a reload", 8000);
  seen.kept = true;
  app.press("Tests · 21");
  seen.collapsed = entries(app).length;
  app.press("Tests · 21");
  seen.opened = entries(app).length;
  app.press("Snake 3");
  await app.until(() => app.text("test-now-text") === "Test: Snake 3 is showing. Normal playback is paused.", "Snake 3 named", 8000);
  seen.pressed = [...app.doc.querySelectorAll('#tests-grid button[aria-pressed="true"]')].map((button) => button.textContent);
  await app.step();
  app.press("Stop test");
  await app.until(() => app.text("test-now-text") === null && app.text("playing") === "Playlist", "playback resumed", 8000);
  await app.step();
  app.press("Diagonal");
  await app.until(() => app.text("test-now-text") === "Test: Diagonal is showing. Normal playback is paused.", "the diagonal named", 8000);
  await app.step();
  // The test is named with the group hidden too, and a play of an animation ends it.
  app.press("Settings");
  app.byId("show-tests").click();
  app.press("Animations");
  await app.until(() => app.shown() === "animations" && app.byId("tests").hidden, "the group hidden", 8000);
  seen.namedHidden = app.text("test-now-text");
  playRow(app, settings.play);
  await app.until(() => app.text("test-now-text") === null && app.text("playing") === "Playlist", "the play ended the test", 8000);
  await app.step();
  seen.rowsAfter = rows(app).map((row) => row.id);
  seen.inList = app.doc.querySelectorAll("#animations-list .test, #animations-list [data-snake]").length;
  return seen;
}
