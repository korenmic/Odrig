// The operator gives the app one address after the other.

export default async function (app) {
  const seen = [];
  for (const address of app.settings.addresses) {
    if (app.shown() !== "target") {
      app.press("Target");
    }
    app.fill("address", address);
    app.press("Use");
    await app.until(() => app.kept() === address && app.raw("link") !== "Checking", `an end of the check of ${address}`, 9000);
    seen.push({address, link: app.raw("link"), failure: app.raw("link-failure"), shown: app.shown()});
  }
  return seen;
}
