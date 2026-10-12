// The subcommands, the exit statuses and the error line.
//
// Exit status 0 means the subcommand did its work, 1 that an input was rejected, and 2
// that the command line was not understood.

import {errors, jsonframes, odrg, whole} from "../lib/index.js";
import {TOOL, UsageError, parse, usage} from "./arguments.js";
import * as files from "./files.js";
import * as folder from "./folder.js";

function encode(values) {
  const source = files.read(values.input);
  const data = errors.naming(values.input, () => odrg.encode(jsonframes.loads(source), {compressed: !values.uncompressed}));
  files.write(values.output, data);
}

function decode(values) {
  const data = files.read(values.input);
  const decoded = errors.naming(values.input, () => odrg.decode(data));
  const animation = {width: decoded.width, height: decoded.height, frames: decoded.records};
  files.write(values.output, jsonframes.dumps(animation));
}

// What `check` prints for a JSON frames file ("json") or an ODRG file ("odrg") given as
// bytes: its lines, each with a line feed.
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
    const decoded = odrg.decode(data);
    ({width, height, records: frames} = decoded);
    lines.push("format: odrg");
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

function check(values, streams) {
  let kind = values.format;
  if (kind === null) {
    const name = values.file.toLowerCase();
    if (name.endsWith(".json")) {
      kind = "json";
    } else if (name.endsWith(".odrg")) {
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
