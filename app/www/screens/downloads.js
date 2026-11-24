// Downloads and backups from the list. `Download` in an animation's menu saves its file under
// its own name. `Download selected` saves one zip of the selected files and folders of one
// storage, named from the level shown, after the operator has seen that storage and level;
// a selection of both storages is backed up one storage at a time, the operator choosing
// which. Progress, Stop and the end are shown in the dialog, and the outcome in a message.

import * as backups from "../backups.js";
import * as client from "../client.js";
import {Refusal} from "../commands.js";
import * as messages from "../messages.js";
import * as save from "../save.js";
import * as target from "../target.js";
import {Failure} from "../target.js";

let message = () => {};
let redraw = () => {};
let chosen = () => ({files: [], folders: []});
// The selection the dialog asks about, with the level and the target it was made at; and
// the run under way.
let asking = null;
let running = null;

function byId(id) {
  return document.getElementById(id);
}

export function busy() {
  return running !== null;
}

function refusalText(error) {
  if (error instanceof Refusal && error.code === "unknown-command") return "This installation's firmware cannot read files back. Install the newer firmware.";
  if (error instanceof Refusal) return messages.ofRefusal(error, client.state.status?.error ?? null);
  if (error instanceof Failure) return messages.ofFailure(error);
  return error.message;
}

function waitVisible() {
  return new Promise((resolve) => {
    if (!document.hidden) {
      resolve();
      return;
    }
    const seen = () => {
      if (!document.hidden) {
        document.removeEventListener("visibilitychange", seen);
        resolve();
      }
    };
    document.addEventListener("visibilitychange", seen);
  });
}

function plural(count, one) {
  return `${count} ${one}${count === 1 ? "" : "s"}`;
}

function show(title, go) {
  byId("download-dialog-title").textContent = title;
  byId("download-go").textContent = go;
  byId("download-progress").textContent = "";
  byId("download-dialog").hidden = false;
}

function close() {
  asking = null;
  byId("download-dialog").hidden = true;
}

// Draws the dialog's buttons for a run under way or for a question.
function buttons() {
  const under = running !== null;
  byId("download-go").hidden = under || asking === null;
  byId("download-go").disabled = under || client.state.link !== "answers" || client.contentBusy();
  byId("download-cancel").hidden = under;
  byId("download-stop").hidden = !under;
  byId("download-storage").disabled = under;
}

// Begins a run for the target of this version. Gives what the run is told: whether the
// operator pressed Stop, and whether another target was chosen since.
function begin(version) {
  const run = {stop: false, version};
  running = run;
  client.setContentBusy("download");
  buttons();
  return {stopped: () => run.stop, changed: () => version !== client.targetVersion()};
}

function end() {
  running = null;
  client.setContentBusy(false);
  buttons();
}

// The actions an animation's menu gets: `Download`, disabled while its file is unavailable
// or its size is not known yet.
export function menu(animation) {
  if (typeof animation.file !== "string") return [];
  const unready = typeof animation.fault === "string" || typeof animation.bytes !== "number";
  return [{label: "Download", act: () => downloadOne(animation), disabled: client.state.link !== "answers" || running !== null || client.contentBusy() || unready}];
}

async function downloadOne(row) {
  if (running !== null || client.contentBusy()) return;
  const storage = backups.storageOf(row);
  const level = client.state.level.id;
  show("Download", "Save");
  byId("download-source").textContent = `From ${backups.label(storage, row.file)}`;
  byId("download-what").textContent = `${row.bytes} bytes, saved under the name ${backups.baseOf(row.file)}.`;
  byId("download-choice").hidden = true;
  const {stopped, changed} = begin(client.targetVersion());
  const progress = byId("download-progress");
  try {
    const result = await backups.download({client, row, level, stopped, changed, visible: waitVisible, open: (name) => save.begin(name),
      report: ({read, size}) => { progress.textContent = `Read ${read} of ${size} bytes.`; }});
    message(result.saved ? `Saved ${result.name}: ${result.size} bytes of ${backups.label(storage, row.file)}, as the installation keeps them.` :
      `${result.name} was not saved: no place was chosen.`);
  } catch (error) {
    message(`${backups.label(storage, row.file)} was not downloaded. ${refusalText(error)}`);
  } finally {
    end();
    close();
  }
}

// The storages the selection holds, each with its files and folders.
function parts(selection) {
  const found = [];
  for (const storage of ["internal", "external"]) {
    const files = selection.files.filter((row) => backups.storageOf(row) === storage);
    const folders = selection.folders.filter((row) => backups.storageOf(row) === storage);
    if (files.length + folders.length > 0) found.push({storage, files, folders});
  }
  return found;
}

function describe() {
  if (asking === null) return;
  const part = asking.parts.find((one) => one.storage === byId("download-storage").value) ?? asking.parts[0];
  const base = asking.level.path;
  byId("download-source").textContent = `From ${backups.label(part.storage, base === "" ? "" : `${base}/`)}: entries are named from there.`;
  const counted = [plural(part.files.length, "file")];
  if (part.folders.length > 0) counted.push(`${plural(part.folders.length, "folder")} with everything in them`);
  byId("download-what").textContent = `${counted.join(" and ")}, saved as one zip with the manifest ${backups.MANIFEST}.`;
}

function openSelected() {
  if (running !== null) return;
  const selection = chosen();
  const found = parts(selection);
  if (found.length === 0) return;
  asking = {parts: found, level: {...client.state.level}, version: client.targetVersion()};
  show("Download selected", "Save the backup");
  const storage = byId("download-storage");
  storage.replaceChildren(...found.map((part) => {
    const option = document.createElement("option");
    option.value = part.storage;
    option.textContent = `${part.storage === "external" ? "External" : "Internal"} storage: ${plural(part.files.length, "file")}${part.folders.length > 0 ? `, ${plural(part.folders.length, "folder")}` : ""}`;
    return option;
  }));
  storage.value = found[0].storage;
  byId("download-choice").hidden = found.length < 2;
  byId("download-choice-reason").textContent = found.length < 2 ? "" :
    "The selection holds files of both storages. A backup holds one: back up each in its turn.";
  describe();
  buttons();
}

function summary(result, storage, base) {
  const files = result.manifest.files;
  const saved = files.filter((file) => file.outcome === "saved").length;
  const failed = files.filter((file) => file.outcome === "failed");
  const unread = files.filter((file) => file.outcome === "stopped" || file.outcome === "not-started").length;
  const where = backups.label(storage, base);
  const words = [result.saved ? `Saved the backup ${result.name} of ${where}: ${saved} of ${plural(files.length, "file")}.` :
    `The backup ${result.name} of ${where} was not saved: no place was chosen.`];
  if (result.manifest.partial) words.push("It is a partial backup.");
  if (failed.length > 0) words.push(`Failed ${failed.length}: ${failed.map((file) => `${file.path} (${file.reason})`).join("; ")}.`);
  if (unread > 0) words.push(`Not read after Stop: ${unread}.`);
  return words.join(" ");
}

async function runSelected() {
  const asked = asking;
  if (asked === null || running !== null || asked.version !== client.targetVersion()) return;
  const part = asked.parts.find((one) => one.storage === byId("download-storage").value) ?? asked.parts[0];
  const base = asked.level.path;
  const {stopped, changed} = begin(asked.version);
  const progress = byId("download-progress");
  try {
    const result = await backups.backup({client, storage: part.storage, base, level: asked.level.id, files: part.files, folders: part.folders,
      address: target.address(), stopped, changed, visible: waitVisible, open: (name) => save.begin(name, "application/zip"),
      report: (step) => {
        progress.textContent = step.phase === "scope" ? "Reading the selected folders\u2026" :
          `File ${step.at + 1} of ${step.count}: ${step.path}${step.size === null ? "" : `, ${step.read} of ${step.size} bytes`}`;
      }});
    message(summary(result, part.storage, base));
  } catch (error) {
    message(`The backup was not saved. ${refusalText(error)}`);
  } finally {
    end();
    close();
    redraw();
  }
}

// Draws the dialog's buttons with the screen. A change of target ends the question.
export function draw() {
  if (asking !== null && running === null && asking.version !== client.targetVersion()) close();
  buttons();
}

export function start(options) {
  message = options.message;
  redraw = options.redraw;
  chosen = options.chosen;
  byId("download-selected").addEventListener("click", openSelected);
  byId("download-storage").addEventListener("change", describe);
  byId("download-go").addEventListener("click", runSelected);
  byId("download-cancel").addEventListener("click", close);
  byId("download-stop").addEventListener("click", () => {
    if (running !== null) running.stop = true;
  });
}
