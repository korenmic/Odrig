// Renders the message of the clock breaks from the owner's page, frame by frame, in a
// headless Chrome with a profile of its own in a temporary folder, removed afterwards.
//
//   node render-message.mjs PAGE.html OUT.json
//
// PAGE.html is `references/horror-text-60x60.html` beside the seed. Before its script runs,
// the page's clock is replaced: `performance.now` answers the time the tool sets,
// `requestAnimationFrame` keeps the callback for the tool to call, and `matchMedia` answers
// that reduced motion is off. The tool then steps the clock to 0, 50, ... 5,950 ms, calls
// the page's own callback at each, and takes the page's 60 x 60 canvas as it is drawn,
// colours untouched. OUT.json is the JSON frames file of the 120 frames of 50 ms.

import {spawn} from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const CHROME = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const STEP = 50;
const COUNT = 120;
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

const CLOCK = `(() => {
  window.__now = 0;
  window.__callback = null;
  performance.now = () => window.__now;
  window.requestAnimationFrame = (callback) => { window.__callback = callback; return 1; };
  window.cancelAnimationFrame = () => { window.__callback = null; };
  window.matchMedia = (query) => ({matches: false, media: query, onchange: null,
    addEventListener() {}, removeEventListener() {}, addListener() {}, removeListener() {}});
})();`;

async function withChrome(work) {
  const profile = fs.mkdtempSync(path.join(os.tmpdir(), "odrig-render-message-"));
  const child = spawn(CHROME, ["--headless=new", "--no-first-run", "--no-default-browser-check", "--disable-extensions", "--disable-sync",
    "--disable-background-networking", `--user-data-dir=${profile}`, "--remote-debugging-port=0", "about:blank"], {stdio: "ignore"});
  try {
    const active = path.join(profile, "DevToolsActivePort");
    for (let i = 0; i < 200 && !fs.existsSync(active); i += 1) await sleep(100);
    const port = Number(fs.readFileSync(active, "utf8").split("\n")[0]);
    const target = (await (await fetch(`http://127.0.0.1:${port}/json/list`)).json()).find((one) => one.type === "page");
    const ws = new WebSocket(target.webSocketDebuggerUrl);
    await new Promise((resolve) => ws.addEventListener("open", resolve, {once: true}));
    let id = 0;
    const pending = new Map();
    ws.addEventListener("message", (event) => {
      const message = JSON.parse(event.data);
      if (pending.has(message.id)) {
        pending.get(message.id)(message);
        pending.delete(message.id);
      }
    });
    const send = (method, params = {}) => new Promise((resolve) => {
      id += 1;
      pending.set(id, resolve);
      ws.send(JSON.stringify({id, method, params}));
    });
    const evaluate = async (expression) => {
      const answer = await send("Runtime.evaluate", {expression, returnByValue: true});
      if (answer.error) throw new Error(answer.error.message);
      if (answer.result.exceptionDetails) throw new Error(JSON.stringify(answer.result.exceptionDetails).slice(0, 400));
      return answer.result.result.value;
    };
    await work(send, evaluate);
    ws.close();
  } finally {
    spawn("taskkill", ["/F", "/T", "/PID", String(child.pid)], {stdio: "ignore"});
    await sleep(2000);
    fs.rmSync(profile, {recursive: true, force: true, maxRetries: 10, retryDelay: 500});
  }
}

async function render(page) {
  const frames = [];
  await withChrome(async (send, evaluate) => {
    await send("Page.enable");
    await send("Page.addScriptToEvaluateOnNewDocument", {source: CLOCK});
    await send("Page.navigate", {url: `file:///${path.resolve(page).replace(/\\/g, "/")}`});
    for (let i = 0; i < 100 && !(await evaluate("typeof window.__callback === 'function'")); i += 1) await sleep(100);
    if (!(await evaluate("typeof window.__callback === 'function'"))) throw new Error("the page did not start its animation");
    if (await evaluate("matchMedia('(prefers-reduced-motion: reduce)').matches")) throw new Error("reduced motion is on");
    for (let k = 0; k < COUNT; k += 1) {
      const pixels = await evaluate(`(() => {
        const t = ${k * STEP};
        window.__now = t;
        const callback = window.__callback;
        window.__callback = null;
        if (typeof callback !== 'function') throw new Error('no callback at ' + t + ' ms');
        callback(t);
        const d = document.getElementById('screen').getContext('2d').getImageData(0, 0, 60, 60).data;
        const out = [];
        for (let p = 0; p < 3600; p++) {
          if (d[p * 4 + 3] !== 255) throw new Error('a pixel that is not opaque at ' + t + ' ms');
          out.push(d[p * 4] * 65536 + d[p * 4 + 1] * 256 + d[p * 4 + 2]);
        }
        return out;
      })()`);
      frames.push({ms: STEP, pixels});
    }
  });
  return frames;
}

async function main() {
  const [page, out] = process.argv.slice(2);
  if (!page || !out) throw new Error("usage: node render-message.mjs PAGE.html OUT.json");
  const frames = await render(page);
  const colours = new Set(frames.flatMap((frame) => frame.pixels));
  const text = `{\n  "version": 1,\n  "width": 60,\n  "height": 60,\n  "frames": [\n${frames
    .map((frame) => `    {"ms": ${frame.ms}, "pixels": [${frame.pixels.join(",")}]}`).join(",\n")}\n  ]\n}\n`;
  fs.writeFileSync(out, text);
  console.log(`${out}: ${frames.length} frames of ${STEP} ms, ${colours.size} colours`);
}

await main();
