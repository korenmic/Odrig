// The target stops answering while the show screen is shown, and answers again.

import {rows, shown, state} from "../reading.js";

export default async function (app) {
  await shown(app, app.settings.rows);
  const before = {...state(app), rows: rows(app), listDimmed: app.byId("animations-list").classList.contains("stale")};
  await app.step();
  await app.until(() => app.text("silent") !== null, "the line that says the target does not answer", 8000);
  const first = {...state(app), rows: rows(app), listDimmed: app.byId("animations-list").classList.contains("stale"), shown: app.shown()};
  await app.sleep(2300);
  const later = state(app);
  await app.step();
  await app.until(() => app.text("silent") === null, "the line gone again", 5000);
  return {before, first, later, again: {...state(app), listDimmed: app.byId("animations-list").classList.contains("stale")}};
}
