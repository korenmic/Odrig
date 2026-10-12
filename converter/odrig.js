#!/usr/bin/env node
// The command line of the converter: node converter/odrig.js <subcommand> ...
//
// Exit status 0 means the subcommand did its work, 1 that an input was rejected, and 2
// that the command line was not understood or that Node.js is too old. An error that is
// none of these ends the program with its own message and status 70.

import {refusal} from "./cli/version.js";

var BROKEN = 70;
var line = refusal(process.versions.node);

if (line !== null) {
  process.stderr.write(line + "\n");
  process.exitCode = 2;
} else {
  import("./cli/main.js")
    .then(function (module) {
      return module.main(process.argv.slice(2));
    })
    .then(
      function (status) {
        process.exitCode = status;
      },
      function (error) {
        process.stderr.write((error instanceof Error && error.stack ? error.stack : String(error)) + "\n");
        process.exitCode = BROKEN;
      }
    );
}
