// Phone-only USB evidence collection, independent of the Wi-Fi target and its commands.
// The board's own USB serial port is also the port of the app's USB serial link: a
// capture is not started on it while that link is in use.
import {link, usbDiagnostics} from "../target.js";
const byId = (id) => document.getElementById(id);
let plugin;
let visible = false;
let timer;
let epoch = 0;
let busy = false;
let ports = [];
let last = {active: false, state: "idle", detail: "", bytes: 0, text: ""};

function render() {
  byId("usb-start").disabled = busy || last.active || ports.length === 0;
  byId("usb-refresh").disabled = busy || last.active;
  byId("usb-device").disabled = busy || last.active || ports.length === 0;
  byId("usb-stop").disabled = !last.active;
  byId("usb-diagnostics").disabled = busy || last.state !== "capturing";
  byId("usb-share").disabled = busy || last.bytes === 0;
  const state = `${last.detail || "Ready to capture."} Received ${last.bytes} bytes.`;
  if (byId("usb-capture-state").textContent !== state) byId("usb-capture-state").textContent = state;
  const log = byId("usb-log");
  if (log.value !== last.text) {
    const bottom = log.scrollTop + log.clientHeight >= log.scrollHeight - 8;
    log.value = last.text;
    if (bottom) log.scrollTop = log.scrollHeight;
  }
}

function error(caught) {
  byId("usb-error").textContent = caught?.message || "USB diagnostics failed.";
  byId("usb-error").hidden = false;
}

async function refresh() {
  const found = await plugin.devices();
  const select = byId("usb-device");
  const kept = ports[Number(select.value)];
  ports = found.ports;
  select.replaceChildren();
  ports.forEach((port, at) => {
    const option = document.createElement("option");
    option.value = String(at);
    option.textContent = port.label;
    select.append(option);
  });
  const same = kept ? ports.findIndex((port) => port.device === kept.device && port.port === kept.port) : -1;
  if (ports.length) select.value = String(Math.max(0, same));
  byId("usb-availability").textContent = !found.supported ? "This phone does not report USB host support." :
    ports.length ? "Close the flasher and other USB apps before starting capture." :
      found.attached ? "A USB device is connected, but no supported serial port was found." :
        "No USB serial device found. Connect the board to this phone through USB OTG.";
  render();
}

async function action(work) {
  if (busy) return;
  busy = true;
  byId("usb-error").hidden = true;
  render();
  try { await work(); last = await plugin.status(); }
  catch (caught) { error(caught); }
  finally { busy = false; render(); }
}

async function poll(token) {
  try {
    const found = await plugin.status();
    if (!visible || token !== epoch) return;
    last = found;
    render();
  } catch (caught) { if (visible && token === epoch) error(caught); }
  if (visible && token === epoch) timer = setTimeout(() => poll(token), 500);
}

export function showing(shown) {
  visible = shown;
  ++epoch;
  clearTimeout(timer);
  if (!plugin) return;
  if (shown) {
    refresh().catch(error);
    poll(epoch);
  } else {
    // Stop always cancels pending permission too; a late native grant cannot reopen it.
    plugin.stop().catch(() => {});
  }
}

export function start() {
  plugin = usbDiagnostics();
  byId("usb-controls").hidden = !plugin;
  if (!plugin) {
    byId("usb-availability").textContent = "USB log capture is available in the Android app.";
    return;
  }
  byId("usb-refresh").addEventListener("click", () => action(refresh));
  byId("usb-start").addEventListener("click", () => action(async () => {
    const port = ports[Number(byId("usb-device").value)];
    if (!port) return;
    if (port.link === true && link() === "usb") {
      throw new Error("The app's USB serial link uses this port. Choose Wi-Fi above to capture from it, or capture from the board's COM/UART port.");
    }
    await plugin.open({device: port.device, port: port.port});
  }));
  byId("usb-stop").addEventListener("click", () => action(() => plugin.stop()));
  byId("usb-diagnostics").addEventListener("click", () => action(() => plugin.diagnostics()));
  byId("usb-share").addEventListener("click", () => action(() => plugin.share()));
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) {
      ++epoch;
      clearTimeout(timer);
      plugin.stop().catch(() => {});
    } else if (visible) showing(true);
  });
  render();
  if (visible) showing(true);
}
