import {shown} from "../reading.js";
export default async function(app) {
  await shown(app, 2);
  await app.until(() => app.raw("show-space").includes("1.0 MB"), "boot capacity");
  const before = app.raw("show-space");
  await app.step();
  await app.until(() => app.says("has not answered"), "lost target");
  await app.step();
  await app.until(() => app.raw("show-space").includes("2.0 MB"), "recovered capacity", 6000);
  const recovered = app.raw("show-space");
  let hidden = true;
  Object.defineProperty(app.doc, "hidden", {configurable: true, get: () => hidden});
  app.doc.dispatchEvent(new Event("visibilitychange"));
  await app.step();
  hidden = false;
  app.doc.dispatchEvent(new Event("visibilitychange"));
  await app.until(() => app.raw("show-space").includes("3.0 MB"), "foreground capacity", 4000);
  return {before, recovered, foreground: app.raw("show-space")};
}
