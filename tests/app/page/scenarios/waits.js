// The app is left alone for a time.

export default async function (app) {
  await app.sleep(app.settings.ms);
  return {link: app.raw("link")};
}
