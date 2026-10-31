import {rows, shown} from "../reading.js";

export default async function (app) {
  await shown(app, 0);
  await app.until(() => app.doc.querySelector('[aria-label="Open folder clocks"]') !== null, "Clocks folder");
  app.doc.querySelector('[aria-label="Open folder clocks"]').click();
  await app.until(() => app.text("level-title") === "clocks" && rows(app).length === 6, "Clocks entries");
  if (app.settings.nested) {
    app.doc.querySelector('[aria-label="Open folder clocks/message"]').click();
    await app.until(() => app.text("level-title") === "clocks/message" && rows(app).length === 6, "message entries");
  }
  const client = await app.frame.contentWindow.eval('import("/client.js")');
  const levels = [];
  client.watch(state => levels.push(state.level.path));
  const version = client.state.listVersion;
  await app.step();
  client.refreshContent();
  if (app.settings.navigation) {
    await app.sleep(30);
    app.press("Back");
    await app.until(() => app.text("level-title") === "Root" && client.state.listVersion > version, "chosen Root");
  } else if (app.settings.verificationFailure) {
    await app.sleep(650);
  } else {
    await app.until(() => client.state.listVersion > version, "completed recovery listing", 8000);
  }
  return {path: client.state.level.path, folder: client.state.level.id,
    ids: rows(app).map(row => row.id), visitedRoot: levels.includes("")};
}
