import readyUpload from "./ready-upload.js";

export default async function (app) {
  const settings = app.settings;
  settings.send = false;
  const seen = await readyUpload(app);
  const view = app.frame.contentWindow;
  const select = app.byId("upload-storage");
  if (settings.explicit === true) {
    select.value = "internal";
    select.dispatchEvent(new view.Event("change", {bubbles: true}));
  }
  async function refresh() {
    app.press("Animations");
    await app.until(() => app.shown() === "animations", "Animations for fresh storage");
    app.press("Upload");
    await app.until(() => app.shown() === "upload", "Upload for fresh storage");
  }
  if (settings.mode === "hotplug") {
    await app.step();
    await refresh();
    await app.until(() => select.options[0].disabled, "External grayed out");
    seen.absent = {storage: select.value, destination: app.text("upload-destination")};
    await app.step();
    await refresh();
    await app.until(() => !select.options[0].disabled, "External detected again");
    seen.returned = select.value;
    const response = await fetch(`/m/${settings.file}`);
    const blob = await response.blob();
    const picked = new view.DataTransfer();
    picked.items.add(new view.File([blob], settings.file));
    const field = app.byId("ready-file");
    field.files = picked.files;
    field.dispatchEvent(new view.Event("change", {bubbles: true}));
    await app.until(() => app.text("made-facts") !== null, "new form of the same file");
    seen.nextForm = select.value;
    return seen;
  }
  if (settings.mode === "preflight") await app.step();
  app.press("Upload to the installation");
  if (settings.mode === "inflight") {
    await app.until(() => /^Sending: [1-9]/.test(app.text("uploading") ?? ""), "active byte transfer");
    seen.frozen = app.text("upload-destination");
    await app.step();
  }
  await app.until(() => app.text("message-text") !== null, "safe upload refusal", 15000);
  seen.message = app.text("message-text");
  seen.afterDestination = app.text("upload-destination");
  return seen;
}
