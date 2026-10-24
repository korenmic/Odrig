// The system's back gesture, as the page's history has it.

import {shown} from "../reading.js";

export default async function (app) {
  const view = app.frame.contentWindow;
  const look = () => ({shown: app.shown(), state: view.history.state, entries: view.history.length});
  const began = look();
  if (app.settings.answers !== true) {
    await app.until(() => app.text("link") === "No answer", "the target screen says No answer", 9000);
    return {began, unanswered: look()};
  }
  await shown(app, app.settings.rows);
  const first = look();
  app.press("Target");
  await app.until(() => app.shown() === "target", "the target screen");
  const second = look();
  view.history.back();
  await app.until(() => app.shown() === "animations", "Animations after back");
  const back = look();
  const toggled = [];
  for (let round = 0; round < 3; round += 1) {
    app.press("Target");
    await app.until(() => app.shown() === "target", "the target screen");
    app.press("Animations");
    await app.until(() => app.shown() === "animations", "Animations");
    toggled.push(look());
  }
  app.press("Upload");
  await app.until(() => app.shown() === "upload", "Upload");
  const upload = look();
  app.press("Settings");
  await app.until(() => app.shown() === "settings", "Settings");
  const settings = look();
  app.press("Target");
  await app.until(() => app.shown() === "target", "the target screen after Settings");
  const across = look();
  view.history.back();
  await app.until(() => app.shown() === "animations", "Animations after back from the target screen");
  const home = look();
  app.press("Add animation");
  await app.until(() => app.shown() === "upload", "Upload after Add animation");
  const added = look();
  return {began, first, second, back, toggled, upload, settings, across, home, added};
}
