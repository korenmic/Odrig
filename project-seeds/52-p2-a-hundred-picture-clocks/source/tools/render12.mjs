// Renders the twelve time animations of seed 52 from their own scripts, frame by frame, in
// a headless Chrome with a profile of its own in a temporary folder, removed afterwards.
//
//   node render12.mjs REFERENCES OUT_DIR STEP_MS
//
// REFERENCES is the seed's folder `references/`. The original six come from
// original/animation.js in its DOM: its six drawing functions, pure functions of the time,
// are called through the one name the page adds after the script's own list of them, on
// the script's own 60 x 60 canvas after the script's own background. The standalone six
// come from standalone/standalone-script.js, whose TimeAnimations.draw(ctx, scene,
// seconds) draws a scene at a time. Each scene's frames at 0, STEP_MS, ... up to its
// period are written as raw RGBA to OUT_DIR/<name>.rgba, 14,400 bytes a frame.

import {spawn} from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

export const ORIGINAL = [
  ["time-original-1-two-times", 18], ["time-original-2-never-zero", 16], ["time-original-3-sand-goes-back-up", 16],
  ["time-original-4-we-were-here", 10], ["time-original-5-every-row-another-time", 720], ["time-original-6-the-clock-melts", 90],
];
export const STANDALONE = [
  ["time-standalone-1-two-times", 18], ["time-standalone-2-never-zero", 18], ["time-standalone-3-reverse-hourglass", 18],
  ["time-standalone-4-we-were-here", 18], ["time-standalone-5-time-bands", 18], ["time-standalone-6-melting-clock", 18],
];
const CHROME = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

function originalPage(references) {
  const folder = path.join(references, "original");
  const script = fs.readFileSync(path.join(folder, "animation.js"), "utf8");
  const list = "const draws=[clocks,countdown,sand,deja,slices,melt];";
  if (script.split(list).length !== 2) throw new Error("the original script's list of drawings is not where it was");
  const exposed = script.replace(list, `${list}window.__frame=(n,t)=>{c.fillStyle='#040609';c.fillRect(0,0,60,60);draws[n](t);return c.getImageData(0,0,60,60).data;};`);
  return `<!doctype html><html><head><meta charset="utf-8"><style>${fs.readFileSync(path.join(folder, "animation.css"), "utf8")}</style>
<script>window.requestAnimationFrame=()=>1;window.matchMedia=()=>({matches:true,addEventListener(){},removeEventListener(){}});</script>
</head><body>${fs.readFileSync(path.join(folder, "animation-dom.html"), "utf8")}<script>${exposed}</script></body></html>`;
}

function standalonePage(references) {
  const script = fs.readFileSync(path.join(references, "standalone", "standalone-script.js"), "utf8");
  return `<!doctype html><html><head><meta charset="utf-8"></head><body><canvas id="tiny" width="60" height="60"></canvas>
<script>${script}</script>
<script>const tiny=document.getElementById('tiny').getContext('2d',{willReadFrequently:true});
window.__frame=(n,t)=>{tiny.clearRect(0,0,60,60);TimeAnimations.draw(tiny,n,t);return tiny.getImageData(0,0,60,60).data;};</script></body></html>`;
}

async function withChrome(work) {
  const profile = fs.mkdtempSync(path.join(os.tmpdir(), "odrig-render12-"));
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
      if (answer.result.exceptionDetails) throw new Error(JSON.stringify(answer.result.exceptionDetails).slice(0, 400));
      return answer.result.result.value;
    };
    await send("Page.enable");
    await work(send, evaluate);
    ws.close();
  } finally {
    spawn("taskkill", ["/F", "/T", "/PID", String(child.pid)], {stdio: "ignore"});
    await sleep(2000);
    fs.rmSync(profile, {recursive: true, force: true, maxRetries: 10, retryDelay: 500});
  }
}

async function renderSet(send, evaluate, page, pagePath, scenes, out, step) {
  fs.writeFileSync(pagePath, page);
  await send("Page.navigate", {url: `file:///${pagePath.replace(/\\/g, "/")}`});
  for (let i = 0; i < 100 && !(await evaluate("typeof window.__frame === 'function'")); i += 1) await sleep(100);
  for (const [scene, [name, seconds]] of scenes.entries()) {
    const count = Math.round((seconds * 1000) / step);
    const fd = fs.openSync(path.join(out, `${name}.rgba`), "w");
    for (let done = 0; done < count; done += 40) {
      const n = Math.min(40, count - done);
      const text = await evaluate(`(() => { let s = ''; for (let i = 0; i < ${n}; i++) { const d = window.__frame(${scene}, (${done} + i) * ${step} / 1000); for (let k = 0; k < d.length; k++) s += String.fromCharCode(d[k]); } return btoa(s); })()`);
      fs.writeSync(fd, Buffer.from(text, "base64"));
    }
    fs.closeSync(fd);
    console.log(`${name}: ${count} frames of ${step} ms`);
  }
}

async function main() {
  const [references, out, stepText] = process.argv.slice(2);
  const step = Number(stepText);
  fs.mkdirSync(out, {recursive: true});
  await withChrome(async (send, evaluate) => {
    await renderSet(send, evaluate, originalPage(references), path.join(out, "original.html"), ORIGINAL, out, step);
    await renderSet(send, evaluate, standalonePage(references), path.join(out, "standalone.html"), STANDALONE, out, step);
  });
}

if (process.argv[1] && path.resolve(process.argv[1]) === path.resolve(new URL(import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, "$1"))) {
  await main();
}
