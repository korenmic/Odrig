// The subcommands, the exit statuses and the error line.
//
// Exit status 0 means the subcommand did its work, 1 that an input was rejected, and 2
// that the command line was not understood.

import fs from "node:fs";

import {errors, jsonframes, mapping, odrg, odrgx, timeline, whole} from "../lib/index.js";
import {TOOL, UsageError, parse, usage} from "./arguments.js";
import * as files from "./files.js";
import * as folder from "./folder.js";
import * as gif from "./gif.js";
import * as video from "./video.js";

// The reader of each kind of media file, by the ending of its name.
const KINDS = {".gif": "gif", ".mp4": "video", ".mov": "video"};

// The ending of a file name, in small letters: what follows the last point of the last
// part of the path, when that part does not begin with it.
export function ending(name) {
  const separators = process.platform === "win32" ? ["/", "\\"] : ["/"];
  const base = Math.max(...separators.map((separator) => name.lastIndexOf(separator))) + 1;
  const point = name.lastIndexOf(".");
  let first = base;
  while (first < point && name[first] === ".") {
    first += 1;
  }
  return first < point ? name.slice(point).toLowerCase() : "";
}

function isFile(name) {
  try {
    return fs.statSync(name).isFile();
  } catch (error) {
    if (!files.isSystemError(error)) {
      throw error;
    }
    return false;
  }
}

// Seconds given as a decimal number, in whole milliseconds, rounded to the nearest, halves
// away from zero.
export function milliseconds(text) {
  return whole.whole(whole.rounded(whole.fromDecimal(text, 1000)));
}

// The checks run in this order: the mapping file, the name of the media file, that it is
// there, the packages that read it, a negative start and a duration that is not above 0,
// the content, and last the part against the length of the media.
async function importMedia(values) {
  const mappingBytes = files.read(values.mapping, errors.MAPPING_MISSING);
  const canvas = errors.naming(values.mapping, () => mapping.loads(mappingBytes));
  const kind = KINDS[ending(values.input)];
  if (kind === undefined) {
    throw new errors.Rejection(errors.UNSUPPORTED_MEDIA, `${values.input}: the name does not end in .mp4, .mov or .gif`);
  }
  if (!isFile(values.input)) {
    throw new errors.Rejection(errors.NOT_FOUND, `${values.input}: there is no such file`);
  }
  let frames;
  if (kind === "gif") {
    const found = await gif.reader();
    if (found.failure !== undefined) {
      throw found.failure;
    }
    frames = gif.frames(values.input, found.GifReader);
  } else {
    const found = video.program();
    if (found.failure !== undefined) {
      throw found.failure;
    }
    frames = video.frames(values.input, found.file);
  }
  const options = {
    fit: values.fit,
    startMs: milliseconds(values.start),
    durationMs: values.duration === null ? null : milliseconds(values.duration),
  };
  const animation = await errors.naming(values.input, () => timeline.importFrames({kind, frames}, canvas, options));
  files.write(values.output, jsonframes.dumps(animation));
}

// Writes an ODRG file of JSON frames, or an ODRGX container when the output's name ends in
// `.odrgx`, which a text is always written as.
function encode(values) {
  const source = files.read(values.input);
  const container = ending(values.output) === odrgx.ENDING;
  const read = errors.naming(values.input, () => odrgx.loadsSource(source));
  if (read.type !== "frames" && !container) {
    throw new UsageError(`${values.output}: a text or a widget is written as .odrgx`, "encode");
  }
  const options = {compressed: !values.uncompressed};
  const data = errors.naming(values.input, () => (container ? odrgx.encodeSource(read, options) : odrg.encode(read.animation, options)));
  files.write(values.output, data);
}

// What a runtime file holds, read by its first bytes: an ODRG file, or an ODRGX container
// with `type`, the name of its content type.
export function readRuntime(data) {
  if (odrgx.isContainer(data)) {
    return {format: "odrgx", ...odrgx.decode(data)};
  }
  return {format: "odrg", type: "frames", header: null, ...odrg.decode(data)};
}

// Writes the JSON frames of frames, and the JSON source of a text or a clock.
function decode(values) {
  const data = files.read(values.input);
  const decoded = errors.naming(values.input, () => readRuntime(data));
  if (decoded.type === "text") {
    files.write(values.output, odrgx.dumpsText(odrgx.textOf(decoded)));
    return;
  }
  if (decoded.type === "widget") {
    files.write(values.output, odrgx.dumpsWidget(odrgx.widgetOf(decoded)));
    return;
  }
  const animation = {width: decoded.width, height: decoded.height, frames: decoded.records};
  files.write(values.output, jsonframes.dumps(animation));
}

// What `check` prints for a JSON frames file ("json") or a runtime file ("odrg"), an ODRG
// file or an ODRGX container, given as bytes: its lines, each with a line feed.
export function summary(kind, data) {
  let width;
  let height;
  let frames;
  const lines = [];
  const more = [];
  if (kind === "json") {
    ({width, height, frames} = jsonframes.loads(data));
    lines.push("format: json-frames");
  } else {
    const decoded = readRuntime(data);
    if (decoded.type === "text") {
      return textSummary(decoded, data);
    }
    if (decoded.type === "widget") {
      return widgetSummary(decoded, data);
    }
    ({width, height, records: frames} = decoded);
    lines.push(`format: ${decoded.format}`);
    if (decoded.header !== null) {
      lines.push(`type: ${odrgx.TYPE_NAMES[decoded.header.type]}`);
    }
    more.push(`palette: ${decoded.paletteSize}`, `compressed: ${decoded.compressed ? "yes" : "no"}`);
  }
  lines.push(
    `canvas: ${width}x${height}`,
    `frames: ${frames.length}`,
    `duration_ms: ${frames.reduce((sum, frame) => whole.plus(sum, frame.ms), 0)}`,
    `colours: ${jsonframes.colourCount(frames)}`,
    `file_bytes: ${data.length}`,
  );
  return `${[...lines, ...more].join("\n")}\n`;
}

// What `check` prints for a container of a text.
function textSummary(decoded, data) {
  const lines = [
    "format: odrgx",
    "type: text",
    `canvas: ${decoded.header.width}x${decoded.header.height}`,
    `loop_ms: ${decoded.header.loopMs}`,
    `font: ${decoded.settings.font}`,
    `effect: ${decoded.settings.effect} ${decoded.settings.motion}`,
    `block: ${decoded.block.width}x${decoded.block.height}`,
    `glyphs: ${decoded.glyphs.length}`,
    `text_bytes: ${new TextEncoder().encode(decoded.text).length}`,
    `file_bytes: ${data.length}`,
  ];
  return `${lines.join("\n")}\n`;
}

// What `check` prints for a container of a clock.
function widgetSummary(decoded, data) {
  const lines = [
    "format: odrgx",
    "type: widget",
    `canvas: ${decoded.header.width}x${decoded.header.height}`,
    `loop_ms: ${decoded.header.loopMs}`,
    `widget: ${decoded.settings.widget}`,
    `speed: ${decoded.settings.speedMin} to ${decoded.settings.speedMax}`,
    `file_bytes: ${data.length}`,
  ];
  return `${lines.join("\n")}\n`;
}

function check(values, streams) {
  let kind = values.format;
  if (kind === null) {
    const name = values.file.toLowerCase();
    if (name.endsWith(".json")) {
      kind = "json";
    } else if (name.endsWith(".odrg") || name.endsWith(odrgx.ENDING)) {
      kind = "odrg";
    } else {
      throw new UsageError(`the name of ${values.file} does not tell its format; give --format`, "check");
    }
  }
  const data = files.read(values.file);
  streams.out.write(errors.naming(values.file, () => summary(kind, data)));
}

// The subcommands that can be run: for each name the function that does the work. It is
// given the values of the arguments and the two streams.
export const SUBCOMMANDS = new Map([
  ["import", importMedia],
  ["encode", encode],
  ["decode", decode],
  ["check", check],
  ["pack", folder.pack],
]);

// White space as Python's `str.split` knows it.
const WHITE_SPACE = /[\t\n\v\f\r\x1c-\x1f \x85\xa0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]+/;

// The line that reports a rejection, with every run of white space in the detail written
// as one space.
export function errorLine(rejection) {
  const detail = rejection.detail.split(WHITE_SPACE).filter((word) => word !== "").join(" ");
  return `error: ${rejection.reason}: ${detail}\n`;
}

function usageMessage(error) {
  const text = usage(error.subcommand);
  const head = text.slice(0, text.indexOf("\n\n") + 1);
  const name = error.subcommand === null ? TOOL : `${TOOL} ${error.subcommand}`;
  return `${head}${name}: error: ${error.message}\n`;
}

// Runs one command line and gives the exit status. `argv` holds the arguments after the
// name of the program. An error that is neither a rejection nor a command line that was
// not understood is thrown on.
export async function main(argv, streams = {out: process.stdout, err: process.stderr}, subcommands = SUBCOMMANDS) {
  try {
    const parsed = parse(argv, [...subcommands.keys()]);
    if (parsed.help !== undefined) {
      streams.out.write(parsed.help);
      return 0;
    }
    await subcommands.get(parsed.subcommand)(parsed.values, streams);
    return 0;
  } catch (error) {
    if (error instanceof UsageError) {
      streams.err.write(usageMessage(error));
      return 2;
    }
    if (error instanceof errors.Rejection) {
      streams.err.write(errorLine(error));
      return 1;
    }
    throw error;
  }
}
