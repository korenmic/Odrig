// What the show screen says of a target.

import {rows, shown, state} from "../reading.js";

export default async function (app) {
  await shown(app, app.settings.rows);
  if (app.settings.until !== undefined) {
    await app.until(() => app.says(app.settings.until), `on the screen: ${app.settings.until}`, 8000);
  }
  return {...state(app), rows: rows(app)};
}
