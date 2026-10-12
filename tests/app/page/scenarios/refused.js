// The operator writes something that is no address.

export default async function (app) {
  await app.until(() => app.shown() === "show", "the show screen is shown");
  app.press("Target");
  const before = {message: app.text("message-text"), kept: app.kept()};
  app.fill("address", app.settings.text);
  app.press("Use");
  await app.until(() => app.text("message-text") !== null, "a message");
  const refused = {message: app.text("message-text"), kept: app.kept(), field: app.byId("address").value, link: app.text("link")};
  await app.sleep(1500);
  const later = {message: app.text("message-text"), link: app.text("link")};
  app.press("OK");
  return {before, refused, later, dismissed: app.text("message-text")};
}
