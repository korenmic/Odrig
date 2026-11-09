// The operator downloads an animation from its row's menu on the link USB serial, through a
// stand-in of the APK's sender that is a board: it takes the lines in the order they were
// written, one at a time, gives each to the target over HTTP, and may hold a reply past the
// client's limit before it writes it to the port. What the app saves through the sender's
// Save plugin is what the scenario gives the test.

import {choose, menuOf} from "../reading.js";

export const withoutTheApp = true;

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// The stand-in of the sender, as `window.Capacitor` is in the app. `late` maps a line to the
// milliseconds its reply is held, the first time it is written.
function standIn(settings, lines, saved) {
  const target = localStorage.getItem("odrig.target");
  const late = new Map(Object.entries(settings.late ?? {}));
  const queue = [];
  let held = "";
  let waiting = null;
  let working = false;
  function arrive(text) {
    held += text;
    if (waiting !== null) {
      waiting();
      waiting = null;
    }
  }
  async function work() {
    if (working) return;
    working = true;
    while (queue.length > 0) {
      const line = queue.shift();
      const reply = await (await fetch(`http://${target}/odrig`, {method: "POST", body: line})).text();
      if (late.has(line)) {
        const ms = late.get(line);
        late.delete(line);
        await sleep(ms);
      }
      arrive(`${reply.trim()}\r\n`);
    }
    working = false;
  }
  return {
    isNativePlatform: () => true,
    async nativePromise(plugin, method, options) {
      if (plugin === "Save") {
        if (method === "begin") saved.push({name: options.name, pieces: []});
        if (method === "append") saved[saved.length - 1].pieces.push(options.data);
        if (method === "finish") return {saved: true, name: saved[saved.length - 1].name};
        return {};
      }
      if (plugin !== "Target") throw new Error(`no plugin ${plugin}`);
      if (method === "route") return {wifi: true, validated: true, portal: false, others: "wifi"};
      if (method === "connect") return {};
      if (method === "write") {
        const line = options.text.replace(/\n$/, "");
        lines.push(line);
        queue.push(line);
        work();
        return {};
      }
      if (method === "read") {
        if (held === "" && options.timeoutMs > 0) {
          await Promise.race([new Promise((resolve) => { waiting = resolve; }), sleep(options.timeoutMs)]);
        }
        const text = held.slice(0, 256);
        held = held.slice(256);
        return {text};
      }
      throw new Error(`no method ${method}`);
    },
  };
}

function loaded(frame) {
  return new Promise((resolve) => frame.addEventListener("load", resolve, {once: true}));
}

export default async function (app) {
  const settings = app.settings;
  const lines = [];
  const saved = [];
  localStorage.setItem("odrig.link", "usb");
  const page = await (await fetch("/index.html")).text();
  const frame = app.frame;
  frame.src = "about:blank";
  const blank = loaded(frame);
  document.body.append(frame);
  await blank;
  frame.contentWindow.Capacitor = standIn(settings, lines, saved);
  const doc = frame.contentDocument;
  doc.open();
  doc.write(page.replace("<head>", '<head><base href="/">'));
  doc.close();
  await app.until(() => app.shown() === "animations" && app.doc.querySelectorAll("#animations-list > .row").length === settings.rows, "the list over USB serial", 15000);
  await app.until(() => [...app.doc.querySelectorAll("#animations-list > .row")].every((row) =>
    !row.querySelector(".meta").textContent.includes("size not read yet")), "the sizes of the animations", 15000);
  const client = await frame.contentWindow.eval('import("/client.js")');
  await app.until(() => client.state.link === "answers", "the link answers", 15000);
  const menu = menuOf(app, settings.one);
  if (menu.includes("Download (disabled)")) throw new Error(`Download is disabled: ${menu.join(", ")}`);
  choose(app, "Download");
  await app.until(() => app.byId("download-dialog").hidden && !app.byId("message").hidden, "the end of the run and its message", 60000);
  return {message: app.text("message-text"), saved: saved.map((file) => ({name: file.name, data: file.pieces})), lines};
}
