import {rows, shown} from "../reading.js";

export default async function (app) {
  await shown(app, 0);
  await app.until(() => app.doc.querySelector('[aria-label="Open folder clocks"]') !== null, "native Clocks folder");
  app.doc.querySelector('[aria-label="Open folder clocks"]').click();
  await app.until(() => app.text("level-title") === "clocks" && rows(app).length === app.settings.rows, "native clock entries", 25000);
  const client = await app.frame.contentWindow.eval('import("/client.js")');
  const levels = [];
  client.watch(state => levels.push(state.level.path));
  for (let count = 0; count < 3; ++count) {
    const version = client.state.listVersion;
    client.refreshContent();
    await app.until(() => client.state.listVersion > version && !client.state.listBusy, "native folder refresh", 15000);
    await app.sleep(1100);
  }
  return {path: client.state.level.path, rows: rows(app).length,
    uniqueIds: new Set(rows(app).map(row => row.id)).size,
    visitedRoot: levels.includes(""), refreshes: 3};
}
