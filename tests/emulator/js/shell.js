/* A JavaScript shell for Node.js that takes the command line the tests give `jsc`, the
   shell of macOS:

       node shell.js [FILE | -e CODE]... [-- ARGUMENT...]

   The files and the code run in the order given, in one global scope. What follows `--`
   is the global `arguments`. The scope has what the scripts of the tests use of that
   shell: `print`, `read`, `load` and `checkSyntax`. An exception that nothing catches is
   written to standard error and ends the shell with status 3. */

"use strict";

var fs = require("fs");
var vm = require("vm");

function run(code, name) {
  return vm.runInThisContext(code, {filename: name});
}

globalThis.print = function () {
  process.stdout.write(Array.prototype.join.call(arguments, " ") + "\n");
};

globalThis.read = function (path) {
  return fs.readFileSync(path, "utf8");
};

globalThis.load = function (path) {
  return run(fs.readFileSync(path, "utf8"), path);
};

globalThis.checkSyntax = function (path) {
  return new vm.Script(fs.readFileSync(path, "utf8"), {filename: path}) && undefined;
};

var words = process.argv.slice(2);
var end = words.indexOf("--");
globalThis.arguments = end < 0 ? [] : words.slice(end + 1);

try {
  var given = end < 0 ? words : words.slice(0, end);
  for (var index = 0; index < given.length; index += 1) {
    if (given[index] === "-e") {
      index += 1;
      run(given[index], "-e");
    } else {
      load(given[index]);
    }
  }
} catch (error) {
  process.stderr.write("Exception: " + (error && error.stack ? error.stack : String(error)) + "\n");
  process.exitCode = 3;
}
