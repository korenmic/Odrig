// An inventory of pictures: for each tile of a picture, its colours, its base picture and
// what it becomes, a picture clock or the frames of a motion, as docs/converter.md,
// "clocks", says. The subcommand `clocks` writes a file for each tile.

import {BAD_TYPE, BAD_VERSION, DUPLICATE_ID, OUT_OF_RANGE, Rejection, naming} from "./errors.js";
import * as motion from "./motion.js";
import * as odrg from "./odrg.js";
import * as odrgx from "./odrgx.js";
import * as strictjson from "./strictjson.js";

export const VERSION = 1;
export const MEMBERS = ["version", "width", "height", "tiles"];
export const TILE_MEMBERS = ["name", "tile", "kind", "about", "palette", "picture"];
export const KINDS = {dial: "picture-dial", display: "picture-display", motion: null};
export const MOST_TILES = 256;
export const CLOCK_MEMBERS = ["seconds", "speed_min", "speed_max", "direction", "turns"];
const NAME = /^[A-Za-z0-9][A-Za-z0-9-]{0,63}$/;

// An inventory given as bytes, read strictly: `{width, height, tiles}`, each tile
// `{name, tile, kind, about, palette, picture}` with `clock`, the settings of its picture
// clock, or `motion`. A tile's refusal names the tile.
export function loads(bytes) {
  const top = strictjson.loads(bytes);
  strictjson.members(top, MEMBERS);
  const version = strictjson.integer(top.get("version"), null, null, "version");
  if (version !== VERSION) throw new Rejection(BAD_VERSION, `version is ${version}, not ${VERSION}`);
  const width = Number(strictjson.integer(top.get("width"), 1, 65535, "width"));
  const height = Number(strictjson.integer(top.get("height"), 1, 65535, "height"));
  const list = strictjson.array(top.get("tiles"), "tiles");
  if (list.length < 1 || list.length > MOST_TILES) throw new Rejection(OUT_OF_RANGE, `the inventory has ${list.length} tiles, not 1 to ${MOST_TILES}`);
  const names = new Set();
  const tiles = list.map((one, at) => {
    const label = one instanceof Map && typeof one.get("name") === "string" ? one.get("name") : `tile ${at + 1}`;
    return naming(label, () => tileOf(one, width, height, names));
  });
  return {width, height, tiles};
}

function tileOf(one, width, height, names) {
  if (!(one instanceof Map)) throw new Rejection(BAD_TYPE, "the tile is not an object");
  const kind = one.get("kind");
  if (typeof kind !== "string") throw new Rejection(BAD_TYPE, "kind is not a string");
  if (!(kind in KINDS)) throw new Rejection(OUT_OF_RANGE, `kind is ${JSON.stringify(kind)}, not one of ${Object.keys(KINDS).join(", ")}`);
  strictjson.members(one, [...TILE_MEMBERS, kind === "motion" ? "motion" : "clock"], [], "the tile");
  const name = one.get("name");
  if (typeof name !== "string") throw new Rejection(BAD_TYPE, "name is not a string");
  if (!NAME.test(name)) throw new Rejection(OUT_OF_RANGE, `name is ${JSON.stringify(name)}, not letters, digits and dashes`);
  if (names.has(name)) throw new Rejection(DUPLICATE_ID, `the name ${name} is given twice`);
  names.add(name);
  const tile = Number(strictjson.integer(one.get("tile"), 1, 65535, "tile"));
  const about = one.get("about");
  if (typeof about !== "string") throw new Rejection(BAD_TYPE, "about is not a string");
  const {palette, picture} = odrgx.loadsPicture(one.get("palette"), one.get("picture"), width, height, "the tile");
  const made = {name, tile, kind, about, palette, picture};
  if (kind === "motion") {
    made.motion = motion.loadsMotion(one.get("motion"), width, height, palette.length);
    return made;
  }
  const clock = one.get("clock");
  const widget = KINDS[kind];
  strictjson.members(clock, [...CLOCK_MEMBERS, ...(widget === "picture-dial" ? odrgx.DIAL_MEMBERS : odrgx.DISPLAY_MEMBERS)], [], "the clock");
  made.clock = odrgx.loadsPictureSettings(clock, widget, width, height, palette.length, "the clock");
  return made;
}

// The file of each tile: `{name, kind, file, bytes}`, `file` its name, `name.odrgx` for a
// picture clock and `name.odrg` for a motion.
export function filesOf(inventory) {
  const {width, height} = inventory;
  return inventory.tiles.map((tile) => naming(tile.name, () => {
    if (tile.kind === "motion") {
      const frames = motion.framesOf(tile.picture, tile.palette, {width, height}, tile.motion);
      return {name: tile.name, kind: tile.kind, file: `${tile.name}.odrg`, bytes: odrg.encode(frames)};
    }
    const bytes = odrgx.encodeWidget({width, height, ...tile.clock, palette: tile.palette, picture: tile.picture});
    return {name: tile.name, kind: tile.kind, file: `${tile.name}${odrgx.ENDING}`, bytes};
  }));
}
