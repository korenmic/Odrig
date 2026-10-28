// The subcommand clocks: the animations of an inventory of pictures, a file for each tile.

import fs from "node:fs";
import nodePath from "node:path";

import {errors, inventory} from "../lib/index.js";
import * as files from "./files.js";

// Reads the inventory, makes every file, and only then writes them into the folder, which
// is made when it is missing; prints a line for each.
export function clocks(values, streams) {
  const bytes = files.read(values.inventory);
  const made = errors.naming(values.inventory, () => inventory.filesOf(inventory.loads(bytes)));
  try {
    fs.mkdirSync(values.out, {recursive: true});
  } catch (error) {
    if (!files.isSystemError(error)) {
      throw error;
    }
    throw new errors.Rejection(errors.CANNOT_WRITE, `${values.out}: ${files.why(error, values.out)}`);
  }
  for (const one of made) {
    files.write(nodePath.join(values.out, one.file), one.bytes);
    streams.out.write(`${one.file} ${one.kind} ${one.bytes.length}\n`);
  }
}
