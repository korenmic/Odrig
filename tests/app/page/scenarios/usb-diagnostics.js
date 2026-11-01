export default async function (app) {
  app.tap("to-target");
  const controls = app.byId("usb-controls");
  if (!app.settings.native) return {availability: app.text("usb-availability"), hidden: controls.hidden};
  const win = app.frame.contentWindow;
  let status = {state: "idle", active: false, detail: "Ready", bytes: 0, text: ""};
  const port = {device: "test-usb", port: 0, label: "CDC test"};
  const other = {device: "other-usb", port: 1, label: "Other port"};
  let devices = [port, other];
  let opened;
  let reports = 0;
  let shares = 0;
  let stops = 0;
  const output = "Guru Meditation\n<script>window.usbInjected = true</script>\n";
  const usb = {
    devices: async () => ({supported: true, attached: devices.length, ports: devices}),
    status: async () => ({...status}),
    open: async (port) => { opened = port; status = {state: "capturing", active: true, detail: "Listening", bytes: output.length, text: output}; },
    stop: async () => { ++stops; status = {...status, state: "stopped", active: false}; },
    diagnostics: async () => { ++reports; },
    share: async () => { ++shares; }
  };
  win.Capacitor = {isNativePlatform: () => true, nativePromise: (plugin, method, options) => {
    if (plugin === "UsbDiagnostics") return usb[method](options);
    return Promise.reject({code: "no-wifi"});
  }};
  const screen = await win.eval('import("/screens/usb-diagnostics.js")');
  screen.start();
  screen.showing(true);
  await app.until(() => !app.byId("usb-start").disabled, "USB start ready");
  const selectedVisible = app.byId("usb-device").selectedOptions.length === 1;
  app.tap("usb-start");
  await app.until(() => app.byId("usb-log").value === output, "serial text displayed");
  const textSafe = !win.usbInjected && !app.byId("usb-panel").querySelector("script");
  app.tap("usb-diagnostics");
  await app.until(() => reports === 1 && !app.byId("usb-share").disabled, "report button");
  app.tap("usb-share");
  await app.until(() => shares === 1 && !app.byId("usb-share").disabled, "share button");
  status = {...status, state: "error", active: false, detail: "USB disconnected"};
  await app.until(() => app.text("usb-state").includes("disconnected"), "unplug visible");
  const unpluggedLogKept = app.byId("usb-log").value === output && !app.byId("usb-share").disabled;
  devices = [other, port];
  app.tap("usb-refresh");
  await app.until(() => app.byId("usb-device").options[0]?.textContent === "Other port", "USB ports reordered");
  const selectionKept = app.byId("usb-device").selectedOptions[0]?.textContent === "CDC test";
  status = {...status, state: "permission", active: true};
  const before = stops;
  screen.showing(false);
  await app.sleep(20);
  const stoppedOnLeave = stops > before && !status.active;
  status = {...status, state: "error", active: false, detail: "USB permission was denied"};
  screen.showing(true);
  await app.until(() => app.text("usb-state").includes("denied"), "permission denial visible");
  const denialVisible = app.text("usb-state").includes("denied");
  devices = [];
  app.tap("usb-refresh");
  await app.until(() => app.text("usb-availability").includes("No USB"), "absence visible");
  const noDevicesDisabled = app.byId("usb-start").disabled;
  screen.showing(false);
  return {open: opened, reports, shares, textSafe, unpluggedLogKept, stoppedOnLeave, denialVisible, noDevicesDisabled, selectedVisible, selectionKept};
}
