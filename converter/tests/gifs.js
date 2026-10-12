// Reads GIF files with cli/gif.js in a program of its own, so that a test can give the
// whole run a time limit: node converter/tests/gifs.js LIST.json
//
// LIST.json holds the paths of the files. For each file one line is written: the number of
// frames it gave, or the rejection it ended with.

import fs from "node:fs";

import * as gif from "../cli/gif.js";
import {errors} from "../lib/index.js";

const found = await gif.reader();
if (found.failure !== undefined) {
  throw found.failure;
}
const results = [];
for (const file of JSON.parse(fs.readFileSync(process.argv[2], "utf8"))) {
  try {
    let count = 0;
    for (const frame of gif.frames(file, found.GifReader)) {
      count += frame.rgba.length === 4 * frame.width * frame.height ? 1 : NaN;
    }
    results.push({frames: count});
  } catch (error) {
    if (!(error instanceof errors.Rejection)) {
      throw error;
    }
    results.push({reason: error.reason, detail: error.detail});
  }
}
process.stdout.write(JSON.stringify(results));
