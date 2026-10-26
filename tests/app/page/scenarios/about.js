// The target screen, opened from Animations once the installation answers: the line that
// names the installation and the one of its last fault, each null while it is not shown.

export default async function (app) {
  await app.until(() => app.shown() === "animations" && app.text("power") !== "-", "the show screen with a status");
  app.press("Target");
  await app.until(() => app.shown() === "target", "the target screen");
  if (app.settings.fault) {
    await app.until(() => app.text("last-fault") !== null, "the line of the last fault");
  } else {
    await app.sleep(1500);
  }
  return {host: app.text("host"), fault: app.text("last-fault")};
}
