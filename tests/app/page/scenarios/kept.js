// An address that was set is there after the app was closed and opened, and the button
// `Board` puts the board's address back.

export default async function (app) {
  await app.until(() => app.shown() === "animations", "the show screen is shown");
  app.press("Target");
  app.fill("address", app.settings.other);
  app.press("Use");
  await app.until(() => app.kept() === app.settings.other && app.raw("link") === "Answers", "an answer from the second address");
  await app.reload();
  await app.until(() => app.shown() === "animations", "the show screen after the reload");
  const reloaded = {field: app.byId("address").value, kept: app.kept()};
  app.press("Target");
  app.press("Board");
  await app.until(() => app.text("link") === "No answer", "the target screen says No answer", 9000);
  return {reloaded, board: {field: app.byId("address").value, kept: app.kept(), failure: app.text("link-failure")}};
}
