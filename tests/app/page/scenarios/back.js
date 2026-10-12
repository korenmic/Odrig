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
  await app.until(() => app.shown() === "show", "the show screen after back");
  const back = look();
  const toggled = [];
  for (let round = 0; round < 3; round += 1) {
    app.press("Target");
    await app.until(() => app.shown() === "target", "the target screen");
    app.press("Show");
    await app.until(() => app.shown() === "show", "the show screen");
    toggled.push(look());
  }
  return {began, first, second, back, toggled};
}
