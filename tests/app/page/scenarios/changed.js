// The target is changed by somebody else, and the screen follows.

import {rows, shown, state} from "../reading.js";

export default async function (app) {
  await shown(app, app.settings.rows);
  const before = {...state(app), rows: rows(app)};
  await app.step();
  const asked = performance.now();
  await app.until(() => app.says(app.settings.until), `on the screen: ${app.settings.until}`, app.settings.within);
  const ms = performance.now() - asked;
  await app.sleep(300);
  return {before, ms, after: {...state(app), rows: rows(app)}};
}
