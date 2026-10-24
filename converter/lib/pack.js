// pack: the files that are installed for a show, built from a show file, a mapping file
// and sources, all held in memory: JSON frames for an `.odrg` file and for an `.odrgx`
// container of frames.

import {FILE_MALFORMED, FILE_MISSING, Rejection, SIZE_MISMATCH, naming} from "./errors.js";
import * as jsonframes from "./jsonframes.js";
import * as mapping from "./mapping.js";
import * as odrg from "./odrg.js";
import * as odrgx from "./odrgx.js";
import * as show from "./show.js";

export const MAPPING_NAME = "mapping.json";
export const SHOW_NAME = "show.json";
export const SOURCE_ENDING = ".json";

// Reads and checks the mapping file and then the show file. `labels` has the names the two
// files have in a detail, `mapping` and `show`.
//
// The result is the plan of the pack: `canvas`, the mapping; `show`, the show; and
// `names`, the different files the show names, in the order of their first use.
export function begin(mappingBytes, showBytes, labels = {}) {
  const canvas = naming(labels.mapping === undefined ? MAPPING_NAME : labels.mapping, () => mapping.loads(mappingBytes));
  const listed = naming(labels.show === undefined ? SHOW_NAME : labels.show, () => show.loads(showBytes));
  return {canvas, show: listed, names: show.files(listed)};
}

// The name of the source of a file a show names: `X.json` for `X.odrg` and for `X.odrgx`.
export function sourceName(name) {
  const ending = name.endsWith(odrgx.ENDING) ? odrgx.ENDING : show.ENDING;
  return name.slice(0, name.length - ending.length) + SOURCE_ENDING;
}

// The installed file `name` of a plan, encoded from the bytes of its source: an ODRG file,
// or for a name that ends in `.odrgx` a container of frames. `label` is the name the
// source has in a detail. A source that is null is missing; one that is no JSON frames
// file, or is of another canvas size than the mapping's, is refused.
export function encodeSource(plan, name, sourceBytes, label = sourceName(name), {compressed = true} = {}) {
  if (sourceBytes === null || sourceBytes === undefined) {
    throw new Rejection(FILE_MISSING, `${label}: the show names ${name} and its source is not there`);
  }
  let animation;
  try {
    animation = jsonframes.loads(sourceBytes);
  } catch (error) {
    if (!(error instanceof Rejection)) {
      throw error;
    }
    throw new Rejection(FILE_MALFORMED, `${label}: ${error.reason}: ${error.detail}`);
  }
  const {canvas} = plan;
  if (animation.width !== canvas.width || animation.height !== canvas.height) {
    throw new Rejection(
      SIZE_MISMATCH,
      `${label}: the canvas is ${animation.width} x ${animation.height} and the mapping's is ${canvas.width} x ${canvas.height}`,
    );
  }
  if (name.endsWith(odrgx.ENDING)) {
    return naming(label, () => odrgx.encodeFrames(animation, {compressed}));
  }
  return naming(label, () => odrg.encode(animation, {compressed}));
}

// The installed file set of a show, by name: `mapping.json` and `show.json`, each the
// bytes that were given, and every file the show names, in the order of first use,
// encoded from its source.
//
// `sources` holds the bytes of the sources by name, `X.json` for `X.odrg` and for
// `X.odrgx`, as a `Map` or as an object. Nothing is given before every source was read, checked and
// encoded.
export function pack({mapping: mappingBytes, show: showBytes, sources}, {compressed = true} = {}) {
  const plan = begin(mappingBytes, showBytes);
  const source = (name) => {
    if (sources instanceof Map) {
      return sources.has(name) ? sources.get(name) : null;
    }
    return Object.prototype.hasOwnProperty.call(sources, name) ? sources[name] : null;
  };
  const files = new Map([
    [MAPPING_NAME, mappingBytes],
    [SHOW_NAME, showBytes],
  ]);
  for (const name of plan.names) {
    const from = sourceName(name);
    files.set(name, encodeSource(plan, name, source(from), from, {compressed}));
  }
  return files;
}
