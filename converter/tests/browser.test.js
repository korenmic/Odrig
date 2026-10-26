import assert from "node:assert/strict";
import {spawn} from "node:child_process";
import fs from "node:fs";
import http from "node:http";
import os from "node:os";
import path from "node:path";
import test from "node:test";

import * as library from "../lib/index.js";
import {base64, sourcePictures, work} from "./page/page.js";
import {CONVERTER, ROOT, runJs, temporary} from "./support.js";

const PAGE = path.join(CONVERTER, "tests", "page");
const LIB = path.join(CONVERTER, "lib");
const SOURCE = path.join(ROOT, "animations", "hello.json");
const WAIT_MS = 60000;

// The Chrome to start: the program the environment variable ODRIG_CHROME names, or the
// first of the usual places that has one. The result is `{program}` or `{looked}`, the
// places that were looked at.
function chrome() {
  const named = process.env.ODRIG_CHROME;
  const places = [];
  if (named !== undefined && named !== "") {
    places.push(named);
  }
  if (process.platform === "darwin") {
    places.push("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "/Applications/Chromium.app/Contents/MacOS/Chromium");
  } else if (process.platform === "win32") {
    for (const base of [process.env.PROGRAMFILES, process.env["PROGRAMFILES(X86)"], process.env.LOCALAPPDATA]) {
      if (base) {
        places.push(path.join(base, "Google", "Chrome", "Application", "chrome.exe"));
      }
    }
  } else {
    for (const folder of ["/usr/bin", "/usr/local/bin", "/snap/bin", "/opt/google/chrome"]) {
      for (const name of ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome"]) {
        places.push(path.join(folder, name));
      }
    }
  }
  const program = places.find((place) => fs.existsSync(place));
  return program === undefined ? {looked: places} : {program};
}

const TYPES = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".json": "application/json"};

// A server on the loopback address that hands out the page, the library as its files are,
// and one source, and takes the one answer of the page.
function serve() {
  let answered;
  const answer = new Promise((resolve) => {
    answered = resolve;
  });
  const asked = [];
  const files = (url) => {
    if (url === "/" || url === "/index.html") {
      return path.join(PAGE, "index.html");
    }
    if (url === "/page.js") {
      return path.join(PAGE, "page.js");
    }
    if (url === "/hello.json") {
      return SOURCE;
    }
    const inLib = /^\/lib\/([a-z]+\.js)$/.exec(url);
    return inLib === null ? null : path.join(LIB, inLib[1]);
  };
  const server = http.createServer((request, response) => {
    asked.push(`${request.method} ${request.url}`);
    if (request.method === "POST" && request.url === "/result") {
      const parts = [];
      request.on("data", (part) => parts.push(part));
      request.on("end", () => {
        response.writeHead(204).end();
        answered(JSON.parse(Buffer.concat(parts).toString("utf8")));
      });
      return;
    }
    const file = request.method === "GET" ? files(request.url) : null;
    if (file === null || !fs.existsSync(file)) {
      response.writeHead(404, {"content-type": "text/plain"}).end("not found");
      return;
    }
    response.writeHead(200, {"content-type": TYPES[path.extname(file)], "cache-control": "no-store"}).end(fs.readFileSync(file));
  });
  return new Promise((resolve) => {
    server.listen(0, "127.0.0.1", () => {
      resolve({server, answer, asked, address: `http://127.0.0.1:${server.address().port}/`});
    });
  });
}

function ended(child) {
  return new Promise((resolve) => {
    if (child.exitCode !== null || child.signalCode !== null) {
      resolve();
    } else {
      child.once("exit", () => resolve());
    }
  });
}

// The version of the Chrome that runs with a profile folder, as its DevTools give it, or
// why it is not known. Chrome is not asked with --version: on Windows that opens a window.
async function versionOf(profile) {
  try {
    const port = Number(fs.readFileSync(path.join(profile, "DevToolsActivePort"), "utf8").split("\n")[0]);
    const response = await fetch(`http://127.0.0.1:${port}/json/version`);
    return (await response.json()).Browser;
  } catch (error) {
    return `not known: ${error.message}`;
  }
}

// Starts Chrome without a window on the page, with a profile folder of its own, waits for
// the page's answer, asks Chrome its version, ends Chrome and removes the folder.
async function inChrome(program) {
  const profile = fs.mkdtempSync(path.join(os.tmpdir(), "odrig-converter-chrome-"));
  const {server, answer, asked, address} = await serve();
  const child = spawn(program, [
    "--headless=new",
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-extensions",
    "--disable-background-networking",
    "--disable-sync",
    "--disable-component-update",
    "--disable-breakpad",
    "--use-mock-keychain",
    "--password-store=basic",
    "--remote-debugging-port=0",
    `--user-data-dir=${profile}`,
    address,
  ], {stdio: "ignore"});
  let timer;
  try {
    const outcome = await Promise.race([
      answer.then((given) => ({given})),
      new Promise((resolve) => {
        timer = setTimeout(() => resolve({failure: `the page did not answer within ${WAIT_MS / 1000} seconds; it asked for: ${asked.join(", ")}`}), WAIT_MS);
      }),
      new Promise((resolve) => {
        child.once("error", (error) => resolve({failure: `Chrome could not be started: ${error.message}`}));
        child.once("exit", (code, signal) => resolve({failure: `Chrome ended before the page answered, with ${signal === null ? `status ${code}` : signal}; the page asked for: ${asked.join(", ")}`}));
      }),
    ]);
    const version = outcome.failure === undefined ? await versionOf(profile) : "not known";
    return {...outcome, asked, version, pid: child.pid};
  } finally {
    clearTimeout(timer);
    child.removeAllListeners("exit");
    child.removeAllListeners("error");
    child.on("error", () => {});
    if (child.exitCode === null && child.signalCode === null) {
      child.kill();
      const forced = setTimeout(() => child.kill("SIGKILL"), 10000);
      await ended(child);
      clearTimeout(forced);
    }
    await new Promise((resolve) => server.close(resolve));
    for (let attempt = 0; attempt < 20 && fs.existsSync(profile); attempt += 1) {
      try {
        fs.rmSync(profile, {recursive: true, force: true});
      } catch (error) {
        await new Promise((resolve) => setTimeout(resolve, 250));
      }
    }
    assert.equal(fs.existsSync(profile), false, `the profile folder ${profile} is removed`);
  }
}

function bytesOf(text) {
  return Buffer.from(text, "base64");
}

test("the page of the test loads the library as it is, and nothing else", () => {
  const html = fs.readFileSync(path.join(PAGE, "index.html"), "utf8");
  assert.deepEqual(html.match(/<script\b[^>]*>/g), ['<script type="module" src="page.js">']);
  const page = fs.readFileSync(path.join(PAGE, "page.js"), "utf8");
  assert.deepEqual([...page.matchAll(/\bimport\s*\(\s*["']([^"']+)["']\s*\)/g)].map((match) => match[1]), ["/lib/index.js"]);
  assert.equal(/^\s*import\s/m.test(page), false, "the page imports nothing when it is loaded");
  assert.equal(/\bnode:|\brequire\b|\bprocess\b|\bBuffer\b/.test(page), false);
});

test("what the page asks of the library gives the same in Node.js as the command line writes", async (t) => {
  const source = new Uint8Array(fs.readFileSync(SOURCE));
  const results = await work(library, source);
  const folder = temporary(t);
  for (const [name, flags] of [["compressed", []], ["uncompressed", ["--uncompressed"]]]) {
    const out = path.join(folder, `${name}.odrg`);
    assert.deepEqual(runJs(["encode", SOURCE, out, ...flags]), {status: 0, out: "", err: ""});
    assert.ok(bytesOf(results[name]).equals(fs.readFileSync(out)), name);
  }
  assert.ok(bytesOf(results.decoded[0]).equals(Buffer.from(source)));
  assert.ok(bytesOf(results.decoded[1]).equals(Buffer.from(source)));
  assert.equal(results.reasons, 55);
  assert.equal(sourcePictures().length, 3);
  assert.equal(base64(Uint8Array.of(1, 2, 3, 4, 5)), Buffer.from([1, 2, 3, 4, 5]).toString("base64"));
  assert.equal(base64(Uint8Array.of(255)), "/w==");
});

test("the library gives the same in Chrome as in Node.js, byte for byte", async (t) => {
  const found = chrome();
  if (found.program === undefined) {
    t.skip(`no Chrome was found; looked at ${found.looked.join(", ")}; the environment variable ODRIG_CHROME names another place`);
    return;
  }
  const source = new Uint8Array(fs.readFileSync(SOURCE));
  const expected = await work(library, source);
  const {given, failure, asked, version} = await inChrome(found.program);
  t.diagnostic(`${found.program}: ${version}`);
  assert.equal(failure, undefined, failure);
  assert.equal(given.error, undefined, `the page met an error: ${given.error}`);
  t.diagnostic(`the page ran in ${given.agent}`);

  await t.test("the page was served the page, the library file by file, and the source", () => {
    assert.ok(asked.includes("GET /"), asked.join(", "));
    assert.ok(asked.includes("GET /page.js"));
    assert.ok(asked.includes("GET /lib/index.js"));
    assert.ok(asked.includes("GET /hello.json"));
    for (const name of fs.readdirSync(LIB)) {
      assert.ok(asked.includes(`GET /lib/${name}`), `the page loaded lib/${name}`);
    }
    assert.equal(asked.filter((line) => line.startsWith("POST ")).length, 1);
  });

  await t.test("Hello world, encoded in the page, is the file the command line writes", () => {
    const folder = temporary(t);
    for (const [name, flags] of [["compressed", []], ["uncompressed", ["--uncompressed"]]]) {
      const out = path.join(folder, `${name}.odrg`);
      assert.deepEqual(runJs(["encode", SOURCE, out, ...flags]), {status: 0, out: "", err: ""});
      assert.ok(bytesOf(given.results[name]).equals(fs.readFileSync(out)), `${name}: ${bytesOf(given.results[name]).length} bytes in the page`);
    }
    assert.equal(bytesOf(given.results.compressed)[5], 1);
    assert.equal(bytesOf(given.results.uncompressed)[5], 0);
  });

  await t.test("both files, decoded in the page, give the frames of the source", () => {
    assert.ok(bytesOf(given.results.decoded[0]).equals(Buffer.from(source)));
    assert.ok(bytesOf(given.results.decoded[1]).equals(Buffer.from(source)));
  });

  await t.test("three source pictures, imported and fitted in the page with each fit, give the canvas pictures of Node.js", () => {
    for (const name of ["fill", "fit", "stretch"]) {
      assert.equal(given.results.imported[name], expected.imported[name], `imported with ${name}`);
      assert.equal(given.results.placed[name].length, 9);
      assert.deepEqual(given.results.placed[name], expected.placed[name], `fitted with ${name}`);
    }
    assert.notEqual(expected.imported.fill, expected.imported.fit);
    assert.notEqual(expected.imported.fit, expected.imported.stretch);
    assert.equal(given.results.video, expected.video);
  });

  await t.test("everything the page was asked is the same as in Node.js", () => {
    assert.deepEqual(given.results, expected);
  });
});
