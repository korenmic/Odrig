// pack on folders: the sources read from a folder, and the output folder built beside its
// place and moved into it when it is complete.

import fs from "node:fs";
import path from "node:path";

import {errors, mapping, pack as packing} from "../lib/index.js";
import * as files from "./files.js";

function exists(name) {
  try {
    fs.lstatSync(name);
    return true;
  } catch (error) {
    if (!files.isSystemError(error)) {
      throw error;
    }
    return false;
  }
}

function isFolder(name) {
  try {
    return fs.statSync(name).isDirectory();
  } catch (error) {
    if (!files.isSystemError(error)) {
      throw error;
    }
    return false;
  }
}

// A folder and a name as one path: the folder, the separator of the system unless the
// folder is empty or ends in one already, and the name. The folder stays as it was given.
export function joined(folder, name) {
  if (folder === "" || folder.endsWith("/") || folder.endsWith(path.sep)) {
    return `${folder}${name}`;
  }
  return `${folder}${path.sep}${name}`;
}

// Makes a folder and the folders above it that are not there yet, the topmost first.
function makeFolders(name) {
  const above = path.dirname(name);
  if (above !== name && path.basename(name) !== "" && !fs.existsSync(above)) {
    try {
      makeFolders(above);
    } catch (error) {
      if (error.code !== "EEXIST") {
        throw error;
      }
    }
  }
  try {
    fs.mkdirSync(name);
  } catch (error) {
    if (!isFolder(name)) {
      throw error;
    }
  }
}

// Writes `mapping.json`, `show.json` and every `.odrg` file the show names into the
// output folder.
//
// The checks run in this order: the mapping file, the show file and its ids, the output
// folder, then each source in the order the show names them. Nothing is written before
// every source has been read, checked and encoded.
export function pack(values) {
  const mappingBytes = files.read(values.mapping, errors.MAPPING_MISSING);
  errors.naming(values.mapping, () => mapping.loads(mappingBytes));
  const showBytes = files.read(values.show, errors.SHOW_MISSING);
  const plan = packing.begin(mappingBytes, showBytes, {mapping: values.mapping, show: values.show});

  const out = values.out;
  if (exists(out) && (!isFolder(out) || fs.readdirSync(out).length > 0)) {
    throw new errors.Rejection(errors.OUTPUT_NOT_EMPTY, `${out}: the output folder is not empty`);
  }

  const content = new Map([
    [packing.MAPPING_NAME, mappingBytes],
    [packing.SHOW_NAME, showBytes],
  ]);
  for (const name of plan.names) {
    const source = joined(values.sources, packing.sourceName(name));
    const sourceBytes = files.read(source, errors.FILE_MISSING);
    content.set(name, packing.encodeSource(plan, name, sourceBytes, source, {compressed: !values.uncompressed}));
  }
  writeFolder(out, content);
}

// Makes the folder `out` hold exactly `content`, or leaves it as it was.
//
// The files are written into `<out>.part`, which then takes the place of `out`. Folders
// above `out` that do not exist are made.
function writeFolder(out, content) {
  const building = `${path.resolve(out)}.part`;
  const existed = isFolder(out);
  let made = false;
  try {
    makeFolders(path.dirname(building));
    fs.mkdirSync(building);
    made = true;
    for (const [name, data] of content) {
      fs.writeFileSync(joined(building, name), data);
    }
    if (existed) {
      fs.rmdirSync(out);
    }
    fs.renameSync(building, out);
  } catch (error) {
    if (!files.isSystemError(error)) {
      throw error;
    }
    if (made) {
      fs.rmSync(building, {recursive: true, force: true});
    }
    if (existed && !exists(out)) {
      try {
        fs.mkdirSync(out);
      } catch (second) {
        if (!files.isSystemError(second)) {
          throw second;
        }
      }
    }
    throw new errors.Rejection(errors.CANNOT_WRITE, `${error.path || out}: ${files.why(error)}`);
  }
}
