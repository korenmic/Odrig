// The target: its address, and how one command line travels to it. This is the only
// file that knows whether a line is sent by the app's sender or by the browser.

export const BOARD = "4.3.2.1";

const KEY = "odrig.target";
const LABEL = "[a-z0-9](?:[a-z0-9-]*[a-z0-9])?";
const ADDRESS = new RegExp(`^(${LABEL}(?:\\.${LABEL})*)(?::([0-9]{1,5}))?$`);

// What went wrong on the way to the target or back. `kind` is `bad-address`, `no-wifi`,
// `no-answer` or `bad-reply`; `detail` is the address, or the text that is no address.
export class Failure extends Error {
  constructor(kind, detail) {
    super(`${kind}: ${detail}`);
    this.kind = kind;
    this.detail = detail;
  }
}

// The address as it is kept, `host` or `host:port`, of a text an operator wrote: a host
// name or an IPv4 address, alone or with a port from 1 to 65,535, with `http://` in
// front and one `/` at the end dropped.
export function parse(text) {
  let rest = String(text).trim().toLowerCase();
  if (rest.startsWith("http://")) {
    rest = rest.slice("http://".length);
  }
  if (rest.endsWith("/")) {
    rest = rest.slice(0, -1);
  }
  const found = ADDRESS.exec(rest);
  if (found === null) {
    throw new Failure("bad-address", String(text));
  }
  const host = found[1];
  const port = found[2];
  if (/^[0-9.]+$/.test(host)) {
    const numbers = host.split(".");
    if (numbers.length !== 4 || numbers.some((number) => number.length > 3 || Number(number) > 255)) {
      throw new Failure("bad-address", String(text));
    }
  }
  if (port === undefined) {
    return host;
  }
  if (Number(port) < 1 || Number(port) > 65535) {
    throw new Failure("bad-address", String(text));
  }
  return `${host}:${Number(port)}`;
}

// The address in use: the one that was set, or the board's.
export function address() {
  let kept = null;
  try {
    kept = window.localStorage.getItem(KEY);
  } catch (error) {
    kept = null;
  }
  if (kept === null) {
    return BOARD;
  }
  try {
    return parse(kept);
  } catch (error) {
    return BOARD;
  }
}

// Takes a text as the address in use and keeps it. A text that is no address throws and
// leaves the address in use as it is.
export function setAddress(text) {
  const kept = parse(text);
  window.localStorage.setItem(KEY, kept);
  return kept;
}

function sender() {
  const bridge = window.Capacitor;
  return bridge !== undefined && typeof bridge.isNativePlatform === "function" && bridge.isNativePlatform() ? bridge : null;
}

// A promise that is refused when the one given has not settled in time.
function within(promise, ms) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error("no reply from the sender")), ms);
    promise.then(
      (value) => {
        clearTimeout(timer);
        resolve(value);
      },
      (error) => {
        clearTimeout(timer);
        reject(error);
      },
    );
  });
}

// The reply as an object, of what came back for a line.
function replyOf(status, body, to) {
  if (status !== 200) {
    throw new Failure("bad-reply", to);
  }
  let reply;
  try {
    reply = JSON.parse(body);
  } catch (error) {
    throw new Failure("bad-reply", to);
  }
  if (reply === null || typeof reply !== "object" || Array.isArray(reply) || typeof reply.ok !== "boolean") {
    throw new Failure("bad-reply", to);
  }
  return reply;
}

// Sends one command line to the address in use and gives the reply as an object. The
// line is sent once. It throws a Failure when no reply comes within the limit, in
// milliseconds, or when what comes is not a reply.
export async function send(line, limit = 5000) {
  const to = address();
  const bridge = sender();
  if (bridge !== null) {
    let answer;
    try {
      answer = await within(bridge.nativePromise("Target", "send", {address: to, line, timeoutMs: limit}), limit + 1000);
    } catch (error) {
      throw new Failure(error !== null && typeof error === "object" && error.code === "no-wifi" ? "no-wifi" : "no-answer", to);
    }
    return replyOf(answer.status, answer.body, to);
  }
  const stop = new AbortController();
  const timer = setTimeout(() => stop.abort(), limit);
  let status;
  let body;
  try {
    const answer = await fetch(`http://${to}/odrig`, {method: "POST", body: line, cache: "no-store", signal: stop.signal});
    status = answer.status;
    body = await answer.text();
  } catch (error) {
    throw new Failure("no-answer", to);
  } finally {
    clearTimeout(timer);
  }
  return replyOf(status, body, to);
}

// How requests travel: `{sender: false}` in a browser, and in the app what the sender
// says of the phone's networks.
export async function route() {
  const bridge = sender();
  if (bridge === null) {
    return {sender: false};
  }
  try {
    const found = await within(bridge.nativePromise("Target", "route", {}), 2000);
    return {sender: true, wifi: found.wifi === true, validated: found.validated === true, portal: found.portal === true, others: String(found.others)};
  } catch (error) {
    return {sender: true, wifi: false, validated: false, portal: false, others: "none"};
  }
}
