// The subcommands, the exit statuses and the error line.
//
// Exit status 0 means the subcommand did its work, 1 that an input was rejected, and 2
// that the command line was not understood.

import {errors} from "../lib/index.js";
import {TOOL, UsageError, parse, usage} from "./arguments.js";

// The subcommands that can be run: for each name the function that does the work. It is
// given the values of the arguments and the two streams.
export const SUBCOMMANDS = new Map();

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
