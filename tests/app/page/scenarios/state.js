// What the show screen says of a target.

import {playing, rows, shown, state} from "../reading.js";

export default async function (app) {
  await shown(app, app.settings.rows);
  if (app.settings.until !== undefined) {
    await app.until(() => app.says(app.settings.until), `on the screen: ${app.settings.until}`, 8000);
  }
  if (app.settings.line !== undefined) {
    await app.until(() => new RegExp(app.settings.line).test(playing(app)), `the line of what plays: ${app.settings.line}`, 8000);
  }
  return {...state(app), rows: rows(app)};
}
