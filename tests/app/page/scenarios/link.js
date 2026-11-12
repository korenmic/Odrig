// The Target screen's switch and its one Wi-Fi button, in a browser, which has no USB
// serial port.

export default async function (app) {
  await app.until(() => ["animations", "target"].includes(app.shown()), "a screen is shown");
  if (app.shown() !== "target") app.press("Target");
  const buttons = [...app.doc.querySelectorAll("#target button")].filter((button) => button.getClientRects().length > 0).map((button) => button.textContent.trim());
  const choices = [...app.doc.querySelectorAll('#link-choice input[name="link"]')];
  return {
    buttons,
    choices: choices.map((choice) => ({value: choice.value, checked: choice.checked, disabled: choice.disabled})),
    why: app.text("link-why"),
    wifiShown: !app.byId("wifi-link").hidden,
    usbShown: !app.byId("usb-link").hidden,
    field: app.byId("address").value,
  };
}
