// An address that was set is there after the app was closed and opened, and an emptied
// field connects to the board's address.

export default async function (app) {
  await app.until(() => app.shown() === "animations", "the show screen is shown");
  app.press("Target");
  app.fill("address", app.settings.other);
  app.press("Connect over Wi-Fi");
  await app.until(() => app.kept() === app.settings.other && app.raw("link") === "Answers", "an answer from the second address");
  await app.reload();
  await app.until(() => app.shown() === "animations", "the show screen after the reload");
  const reloaded = {field: app.byId("address").value, kept: app.kept()};
  app.press("Target");
  app.fill("address", "");
  app.press("Connect over Wi-Fi");
  await app.until(() => app.text("link") === "No answer", "the target screen says No answer", 9000);
  return {reloaded, board: {field: app.byId("address").value, kept: app.kept(), failure: app.text("link-failure")}};
}
