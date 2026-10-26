// The target has just started and still reads what it has installed: the rows come
// when it lists them. What the screen says before that is kept.

import {rows, state} from "../reading.js";

export default async function (app) {
  await app.until(() => app.shown() === "animations" && app.text("power") !== "-", "the show screen with a status");
  const before = {...state(app), rows: rows(app), message: app.text("message-text")};
  const began = Date.now();
  await app.until(() => rows(app).length === app.settings.rows, `${app.settings.rows} rows`, 20000);
  return {before, after: {...state(app), rows: rows(app), message: app.text("message-text")}, ms: Date.now() - began};
}
