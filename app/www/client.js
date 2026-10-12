// What the replies told, and the order in which requests are sent. One request is under
// way at a time. The state holds only what a reply said.

import * as commands from "./commands.js";
import {Failure} from "./target.js";

const STATUS_EVERY_MS = 1000;

// `link` is "checking" until the first request has ended, then "answers" or "no-answer",
// with the Failure in `failure`. `status` is the newest reply to `status`, `heardAt` the
// time of the newest reply of any kind, and `answered` whether the target of this
// address has answered at least once.
export const state = {link: "checking", failure: null, status: null, heardAt: null, answered: false};

const watchers = new Set();
let underWay = false;
let statusDue = false;
let statusTimer = null;
// Counts the targets: a reply that belongs to an earlier address is dropped.
let target = 0;

// Calls a function now and whenever the state changes.
export function watch(watcher) {
  watchers.add(watcher);
  watcher(state);
}

function changed() {
  for (const watcher of watchers) {
    watcher(state);
  }
}

function heard() {
  state.link = "answers";
  state.failure = null;
  state.heardAt = Date.now();
  state.answered = true;
}

function failed(error) {
  if (!(error instanceof Failure)) {
    throw error;
  }
  state.link = "no-answer";
  state.failure = error;
}

async function askStatus() {
  const asked = target;
  clearTimeout(statusTimer);
  statusTimer = setTimeout(() => {
    statusDue = true;
    next();
  }, STATUS_EVERY_MS);
  try {
    const reply = await commands.status();
    if (asked !== target) {
      return;
    }
    heard();
    state.status = reply;
  } catch (error) {
    if (asked !== target) {
      return;
    }
    failed(error);
  }
  changed();
}

// The request to send now, or null when nothing is due. Nothing is due while the app is
// not on the screen.
function due() {
  if (statusDue && !document.hidden) {
    statusDue = false;
    return askStatus;
  }
  return null;
}

async function next() {
  if (underWay) {
    return;
  }
  const request = due();
  if (request === null) {
    return;
  }
  underWay = true;
  try {
    await request();
  } finally {
    underWay = false;
    next();
  }
}

// Begins with the address in use: forgets what an earlier target said, and asks.
export function begin() {
  target += 1;
  state.link = "checking";
  state.failure = null;
  state.status = null;
  state.heardAt = null;
  state.answered = false;
  statusDue = true;
  changed();
  next();
}

document.addEventListener("visibilitychange", () => {
  if (!document.hidden) {
    statusDue = true;
    next();
  }
});
