// The oldest Node.js the tool runs with. This file is read before any other of the tool,
// so it is written in the oldest form of the language that knows modules.

export var OLDEST = 20;

// The line to write when Node.js of the given version is too old, or null when it is not.
export function refusal(version) {
  var major = parseInt(String(version).split(".")[0], 10);
  if (major >= OLDEST) {
    return null;
  }
  return "node converter/odrig.js needs Node.js " + OLDEST + " or later; this is Node.js " + version;
}
