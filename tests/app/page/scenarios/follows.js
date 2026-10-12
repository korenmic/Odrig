// What the show screen says over a time: each change of what plays and of the mark.

import {rows, shown, state} from "../reading.js";

export default async function (app) {
  await shown(app, app.settings.rows);
  const seen = [];
  const end = performance.now() + app.settings.ms;
  while (performance.now() < end) {
    const marked = rows(app).filter((row) => row.marked).map((row) => row.id);
    const now = {playing: state(app).playing, now: state(app).now, marked};
    if (seen.length === 0 || JSON.stringify(seen[seen.length - 1]) !== JSON.stringify(now)) {
      seen.push(now);
    }
    await app.sleep(50);
  }
  return seen;
}
