// The app on the link USB serial, through a stand-in of the APK's sender: its `write` gives
// the line to the target over HTTP, and its `read` gives the reply back in pieces, with
// lines of the board's log before and between them. A setting withholds a reply, or has no
// device at all.

export const withoutTheApp = true;

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// The stand-in of the sender, as `window.Capacitor` is in the app.
function standIn(settings, log) {
  let held = "";
  let waiting = null;
  const target = localStorage.getItem("odrig.target");
  function arrive(text) {
    held += text;
    if (waiting !== null) {
      waiting();
      waiting = null;
    }
  }
  return {
    isNativePlatform: () => true,
    async nativePromise(plugin, method, options) {
      log.push(method);
      if (plugin !== "Target") throw new Error(`no plugin ${plugin}`);
      if (method === "route") return {wifi: true, validated: true, portal: false, others: "wifi"};
      if (method === "send") {
        const answer = await fetch(`http://${options.address}/odrig`, {method: "POST", body: options.line});
        return {status: answer.status, body: await answer.text()};
      }
      if (method === "connect") {
        if (settings.noDevice) throw Object.assign(new Error("no device"), {code: "no-usb"});
        return {};
      }
      if (method === "write") {
        const line = options.text.replace(/\n$/, "");
        log.push(`line ${line}`);
        if (settings.withhold !== undefined && line === settings.withhold && !log.includes("withheld")) {
          log.push("withheld");
          return {};
        }
        arrive("# log: a line of the board before the reply\r\n");
        fetch(`http://${target}/odrig`, {method: "POST", body: line}).then((answer) => answer.text()).then(async (reply) => {
          const whole = `${reply.trim()}\r\n`;
          const half = Math.floor(whole.length / 2);
          arrive(whole.slice(0, half));
          await sleep(5);
          arrive("");
          arrive(whole.slice(half) + "# log: and one after it\r\n");
        });
        return {};
      }
      if (method === "read") {
        if (held === "" && options.timeoutMs > 0) {
          await Promise.race([new Promise((resolve) => { waiting = resolve; }), sleep(options.timeoutMs)]);
        }
        const text = held.slice(0, 64);
        held = held.slice(64);
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
  const log = [];
  localStorage.setItem("odrig.link", "usb");
  const page = await (await fetch("/index.html")).text();
  const frame = app.frame;
  frame.src = "about:blank";
  const blank = loaded(frame);
  document.body.append(frame);
  await blank;
  frame.contentWindow.Capacitor = standIn(settings, log);
  const doc = frame.contentDocument;
  doc.open();
  doc.write(page.replace("<head>", '<head><base href="/">'));
  doc.close();
  const seen = {};
  // Every failure of the link the target screen says, however briefly.
  const failures = [];
  const place = app.byId("link-failure");
  new frame.contentWindow.MutationObserver(() => {
    if (!place.hidden && place.textContent && failures[failures.length - 1] !== place.textContent) failures.push(place.textContent);
  }).observe(place, {attributes: true, childList: true, characterData: true, subtree: true});
  if (settings.noDevice) {
    await app.until(() => !app.byId("link-failure").hidden, "the failure of the link", 10000);
    seen.failure = app.raw("link-failure");
    seen.log = log.filter((entry) => !entry.startsWith("line "));
    return seen;
  }
  if (settings.withhold !== undefined) {
    await app.until(() => log.includes("withheld"), "the withheld reply", 15000);
    await app.until(() => failures.length > 0, "the lost reply", 15000);
    seen.lost = failures[0];
    await app.until(() => app.byId("link-failure").hidden && app.raw("link") === "Answers", "the link again", 20000);
  }
  await app.until(() => app.shown() === "animations" && app.doc.querySelectorAll("#animations-list > .row").length === settings.rows, "the list over USB serial", 15000);
  app.press("Target");
  await app.until(() => app.raw("route") === "Sent over USB serial.", "the line of how requests travel");
  seen.route = app.raw("route");
  seen.wifiShown = !app.byId("wifi-link").hidden;
  seen.usbShown = !app.byId("usb-link").hidden;
  seen.usbState = app.text("usb-state");
  app.press("Animations");
  const row = app.doc.querySelector("#animations-list > .row .play");
  row.click();
  await app.until(() => log.includes(`line play ${row.dataset.id}`), "the play over USB serial");
  seen.played = Number(row.dataset.id);
  seen.sends = log.filter((entry) => entry === "send").length;
  app.press("Target");
  const wifi = app.doc.querySelector('#link-choice input[value="wifi"]');
  wifi.click();
  await app.until(() => log.includes("send"), "a line over Wi-Fi after the switch", 10000);
  seen.after = localStorage.getItem("odrig.link");
  return seen;
}
