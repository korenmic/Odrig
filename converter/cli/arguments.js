// The arguments of the command line: the six subcommands, their options and their usage
// texts.
//
// An option is given as `--name value` or `--name=value`, before, between or after the
// positional arguments. An option given twice takes its last value. `--` ends the options.

export const TOOL = "node converter/odrig.js";

export const NAMES = ["import", "encode", "decode", "check", "pack", "thumbnail"];

// A command line that was not understood. `subcommand` is the subcommand it was for, or
// null when none was recognised.
export class UsageError extends Error {
  constructor(message, subcommand = null) {
    super(message);
    this.name = "UsageError";
    this.subcommand = subcommand;
  }
}

const TOOL_USAGE = `usage: ${TOOL} <subcommand> ...

Converts animations between media files, JSON frames, ODRG and ODRGX.

subcommands:
  import   Turns a video or GIF file into a JSON frames file.
  encode   Turns a JSON frames file or the source of a text or a clock into an ODRG
           file or an ODRGX container.
  decode   Turns an ODRG file or an ODRGX container back into its JSON source.
  check    Validates a JSON frames, ODRG or ODRGX file and summarises it.
  pack     Builds the folder of files that is installed for a show.
  thumbnail Makes the preview of an animation, or adds previews to a preview
           catalog.

${TOOL} <subcommand> --help shows the arguments of a subcommand.
`;

const SECONDS = /^[+-]?(?:[0-9]+\.?[0-9]*|\.[0-9]+)(?:[eE]([+-]?[0-9]+))?$/;
const LARGEST_EXPONENT = 9999;

function seconds(text) {
  const match = SECONDS.exec(text);
  if (match === null) {
    return false;
  }
  return match[1] === undefined || Math.abs(Number(match[1])) <= LARGEST_EXPONENT;
}

// For each subcommand: its usage text, the names of its positional arguments with the
// words the usage text has for them, its options that take a value, and its flags. A
// subcommand whose `variadic` is true takes one positional argument or more, as a list; its
// `check` refuses values that do not go together.
const SPECS = {
  import: {
    usage: `usage: ${TOOL} import MEDIA OUT.json --mapping MAPPING [--fit fill|fit|stretch]
                                      [--start SECONDS] [--duration SECONDS]

Turns a video or GIF file into a JSON frames file.

  MEDIA               the .mp4, .mov or .gif file to read
  OUT.json            the JSON frames file to write
  --mapping MAPPING   the mapping file that gives the canvas size
  --fit FIT           how a picture of another shape is put on the canvas:
                      fill, fit or stretch (default: fill)
  --start SECONDS     where the part to convert starts (default: 0)
  --duration SECONDS  how long the part to convert is (default: to the end)
  --help              shows this text
`,
    positionals: [["input", "MEDIA"], ["output", "OUT.json"]],
    options: {
      "--mapping": {name: "mapping", required: true},
      "--fit": {name: "fit", choices: ["fill", "fit", "stretch"], initial: "fill"},
      "--start": {name: "start", seconds: true, initial: "0"},
      "--duration": {name: "duration", seconds: true, initial: null},
    },
    flags: {},
  },
  encode: {
    usage: `usage: ${TOOL} encode IN.json OUT.odrg [--uncompressed]

Turns a JSON frames file into an ODRG file, or into an ODRGX container of frames
when the name of OUT.odrg ends in .odrgx; and the JSON source of a text or a clock
into an ODRGX container, whose name ends in .odrgx.

  IN.json         the JSON frames file or the source of a text or a clock to read
  OUT.odrg        the ODRG file or the ODRGX container to write
  --uncompressed  write the body without compression
  --help          shows this text
`,
    positionals: [["input", "IN.json"], ["output", "OUT.odrg"]],
    options: {},
    flags: {"--uncompressed": "uncompressed"},
  },
  decode: {
    usage: `usage: ${TOOL} decode IN.odrg OUT.json

Turns an ODRG file, or an ODRGX container of frames, back into a JSON frames file,
and an ODRGX container of a text or a clock back into its JSON source.

  IN.odrg   the ODRG file or the ODRGX container to read
  OUT.json  the JSON frames file to write
  --help    shows this text
`,
    positionals: [["input", "IN.odrg"], ["output", "OUT.json"]],
    options: {},
    flags: {},
  },
  check: {
    usage: `usage: ${TOOL} check FILE [--format json|odrg]

Validates a JSON frames, ODRG or ODRGX file and summarises it.

  FILE             the JSON frames, ODRG or ODRGX file to check
  --format FORMAT  the format of FILE, json or odrg, when its name does not end
                   in .json, .odrg or .odrgx; odrg reads an ODRG file and an
                   ODRGX container alike
  --help           shows this text
`,
    positionals: [["file", "FILE"]],
    options: {
      "--format": {name: "format", choices: ["json", "odrg"], initial: null},
    },
    flags: {},
  },
  pack: {
    usage: `usage: ${TOOL} pack --show SHOW --mapping MAPPING --sources DIR --out DIR [--uncompressed]

Builds the folder of files that is installed for a show.

  --show SHOW        the show file
  --mapping MAPPING  the mapping file
  --sources DIR      the folder of JSON frames sources
  --out DIR          the folder to build, new or empty
  --uncompressed     write every ODRG file without compression
  --help             shows this text
`,
    positionals: [],
    options: {
      "--show": {name: "show", required: true},
      "--mapping": {name: "mapping", required: true},
      "--sources": {name: "sources", required: true},
      "--out": {name: "out", required: true},
    },
    flags: {"--uncompressed": "uncompressed"},
  },
  thumbnail: {
    usage: `usage: ${TOOL} thumbnail FILE... (--catalog DIR [--card ODRIG] | --out OUT.gif)

Makes the preview of an animation, a GIF of its pictures over its first loop: with
--catalog the preview of each file is added to the preview catalog of a folder, with
--out the preview of one file is written.

  FILE           an ODRG file or an ODRGX container
  --catalog DIR  the folder of the preview catalog, made when it is missing
  --card ODRIG   the folder odrig of a card: a file inside it is named in the
                 catalog by its path from that folder
  --out OUT.gif  the GIF file to write, for one file
  --help         shows this text
`,
    positionals: [["files", "FILE"]],
    variadic: true,
    options: {
      "--catalog": {name: "catalog", initial: null},
      "--card": {name: "card", initial: null},
      "--out": {name: "out", initial: null},
    },
    flags: {},
    check(values, refuse) {
      if ((values.catalog === null) === (values.out === null)) {
        throw refuse("give one of --catalog and --out");
      }
      if (values.out !== null && values.files.length !== 1) {
        throw refuse(`--out takes one FILE, and ${values.files.length} are given`);
      }
      if (values.out !== null && values.card !== null) {
        throw refuse("--card goes with --catalog");
      }
    },
  },
};

const HELP = ["--help", "-h"];

// The usage text of a subcommand, or of the tool when `subcommand` is null.
export function usage(subcommand = null) {
  return subcommand === null ? TOOL_USAGE : SPECS[subcommand].usage;
}

// What an argument is among the arguments of a subcommand: "end" for `--`, "option" for
// one of the subcommand's own, "value" for a value or a positional argument, "unknown" for
// anything else that begins with a minus sign. A value may begin with a minus sign when a
// digit follows, as in -1 and -.5, when it is the minus sign alone, or when it holds a
// space.
function kindOf(argument, known) {
  if (argument.length < 2 || argument[0] !== "-") {
    return "value";
  }
  if (argument === "--") {
    return "end";
  }
  const equals = argument.indexOf("=");
  if (known.has(argument) || (equals >= 0 && known.has(argument.slice(0, equals)))) {
    return "option";
  }
  if (/^-\.?[0-9]/.test(argument) || argument.includes(" ")) {
    return "value";
  }
  return "unknown";
}

function listed(words) {
  return words.length > 1 ? `${words.slice(0, -1).join(", ")} and ${words[words.length - 1]}` : words[0];
}

// Reads the arguments that follow `node converter/odrig.js`. `available` names the
// subcommands that can be run.
//
// The result is `{subcommand, values}`, or `{help}` with the text to print when `--help`
// was given. A command line that is not understood throws a UsageError.
export function parse(argv, available = NAMES) {
  if (argv.length === 0) {
    throw new UsageError("no subcommand is given");
  }
  const subcommand = argv[0];
  if (HELP.includes(subcommand)) {
    return {help: TOOL_USAGE};
  }
  if (!available.includes(subcommand) || !Object.prototype.hasOwnProperty.call(SPECS, subcommand)) {
    throw new UsageError(`there is no subcommand ${subcommand}`);
  }
  const spec = SPECS[subcommand];
  const refuse = (message) => new UsageError(message, subcommand);
  const known = new Set([...Object.keys(spec.options), ...Object.keys(spec.flags), ...HELP]);

  const values = {};
  for (const option of Object.values(spec.options)) {
    values[option.name] = option.required ? null : option.initial;
  }
  for (const name of Object.values(spec.flags)) {
    values[name] = false;
  }

  const given = new Set();
  const positionals = [];
  const unknown = [];
  const rest = argv.slice(1);
  let ended = false;
  for (let i = 0; i < rest.length; i += 1) {
    const argument = rest[i];
    const kind = ended ? "value" : kindOf(argument, known);
    if (kind === "value") {
      positionals.push(argument);
      continue;
    }
    if (kind === "end") {
      ended = true;
      continue;
    }
    if (kind === "unknown") {
      unknown.push(argument);
      continue;
    }
    const equals = known.has(argument) ? -1 : argument.indexOf("=");
    const flag = equals < 0 ? argument : argument.slice(0, equals);
    const attached = equals < 0 ? null : argument.slice(equals + 1);
    if (HELP.includes(flag) || Object.prototype.hasOwnProperty.call(spec.flags, flag)) {
      if (attached !== null) {
        throw refuse(`${flag} takes no value`);
      }
      if (HELP.includes(flag)) {
        return {help: spec.usage};
      }
      values[spec.flags[flag]] = true;
      continue;
    }
    const option = spec.options[flag];
    let value = attached;
    if (value === null) {
      if (i + 1 >= rest.length || kindOf(rest[i + 1], known) !== "value") {
        throw refuse(`${flag} is given without its value`);
      }
      i += 1;
      value = rest[i];
    }
    if (option.choices !== undefined && !option.choices.includes(value)) {
      throw refuse(`${flag} is "${value}", which is not ${listed(option.choices).replace(" and ", " or ")}`);
    }
    if (option.seconds === true && !seconds(value)) {
      throw refuse(`${flag} is "${value}", which is not a number of seconds`);
    }
    values[option.name] = value;
    given.add(flag);
  }

  const variadic = spec.variadic === true;
  const missing = variadic ? (positionals.length === 0 ? [spec.positionals[0][1]] : []) : spec.positionals.slice(positionals.length).map(([, word]) => word);
  for (const [flag, option] of Object.entries(spec.options)) {
    if (option.required && !given.has(flag)) {
      missing.push(flag);
    }
  }
  if (missing.length > 0) {
    throw refuse(`${listed(missing)} ${missing.length > 1 ? "are" : "is"} missing`);
  }
  if (unknown.length > 0) {
    throw refuse(`there is no option ${unknown[0]}`);
  }
  if (!variadic && positionals.length > spec.positionals.length) {
    const extra = positionals.slice(spec.positionals.length);
    throw refuse(`${extra.length > 1 ? "there are arguments" : "there is an argument"} too many: ${extra.join(" ")}`);
  }
  if (variadic) {
    values[spec.positionals[0][0]] = positionals;
  } else {
    spec.positionals.forEach(([name], place) => {
      values[name] = positionals[place];
    });
  }
  if (spec.check !== undefined) {
    spec.check(values, refuse);
  }
  return {subcommand, values};
}
