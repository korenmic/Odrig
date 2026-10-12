// mp4 and mov through the decoder program: the ffmpeg that the package ffmpeg-static puts
// into converter/node_modules/. No other ffmpeg is used, and none is looked up.
//
// One run of the program gives the frames of the first video stream as red, green, blue
// and alpha on its standard output, and one line for each frame, with its presentation
// time, in its log on standard error.

import {spawn} from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import {fileURLToPath} from "node:url";

import {errors} from "../lib/index.js";

// The reason of a failure of the setup: a package that reads media is not installed. It
// is no rejection of an input, and docs/reasons.md does not list it.
export const DECODER_MISSING = "decoder-missing";

const CONVERTER = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const PACKAGE = path.join(CONVERTER, "node_modules", "ffmpeg-static");

// The command that installs the packages, for the folder this tool is in.
export function installCommand() {
  return `npm ci --prefix ${CONVERTER}`;
}

// The path of the decoder program in converter/node_modules/.
export function programPath() {
  return path.join(PACKAGE, process.platform === "win32" ? "ffmpeg.exe" : "ffmpeg");
}

function missing(what) {
  return new errors.Rejection(DECODER_MISSING, `${what}; install it with: ${installCommand()}`);
}

// The decoder program, or the failure that says how to install it.
export function program() {
  const file = programPath();
  if (!fs.existsSync(PACKAGE)) {
    return {failure: missing("the package ffmpeg-static, which reads mp4 and mov files, is not installed")};
  }
  if (!fs.existsSync(file)) {
    return {failure: missing(`the package ffmpeg-static is installed without its program ${file}`)};
  }
  return {file};
}

function unreadable(what) {
  return new errors.Rejection(errors.UNREADABLE_MEDIA, what);
}

const TIME_BASE = /\bconfig in time_base: (\d+)\/(\d+)/;
const FRAME = /\bn: *\d+ pts: *(\S+) .*\bs:(\d+)x(\d+)\b/;
const NOISE = /^\[(Parsed_showinfo|swscaler)[^\]]*\]/;
const NO_STREAM = /Stream map '[^']*' matches no streams/;

// How many bytes of frames are held before the program is made to wait.
const HELD_BYTES = 64 * 1024 * 1024;

// The arguments of the one run of the program for a file.
export function argumentsFor(file) {
  return [
    "-hide_banner", "-nostdin", "-nostats", "-loglevel", "info", "-noautorotate", "-copyts",
    "-i", `file:${file}`,
    "-map", "0:v:0", "-an", "-sn", "-dn",
    "-vf", "showinfo=checksum=0,scale=flags=bilinear,format=rgba",
    "-fps_mode", "passthrough", "-f", "rawvideo", "pipe:1",
  ];
}

// The frames of the first video stream of a file, in the order they are shown, as the
// library takes them: `{width, height, rgba, time}`, the time in milliseconds as the
// fraction `[n, d]`, or null for a frame without a presentation time. Sound is ignored,
// and a rotation the file records is not applied. The program is started when the first
// frame is asked for and ended when no more frames are asked for.
export async function* frames(file, decoder) {
  const child = spawn(decoder, argumentsFor(file), {stdio: ["ignore", "pipe", "pipe"]});
  const infos = [];
  const chunks = [];
  let held = 0;
  let timeBase = null;
  let lastLine = "";
  let noStream = false;
  let log = "";
  let ended = null;
  let failure = null;
  let waiting = null;
  let wanted = 0;

  const wake = () => {
    if (waiting !== null) {
      const resume = waiting;
      waiting = null;
      resume();
    }
  };
  const changed = () => new Promise((resolve) => {
    waiting = resolve;
  });

  const line = (text) => {
    const frame = FRAME.exec(text);
    if (frame !== null && NOISE.test(text)) {
      infos.push({pts: frame[1], width: Number(frame[2]), height: Number(frame[3])});
      return;
    }
    const base = TIME_BASE.exec(text);
    if (base !== null) {
      timeBase = [BigInt(base[1]), BigInt(base[2])];
      return;
    }
    if (NO_STREAM.test(text)) {
      noStream = true;
    }
    if (text.trim() !== "" && !NOISE.test(text)) {
      lastLine = text.trim();
    }
  };

  child.stderr.setEncoding("utf8");
  child.stderr.on("data", (text) => {
    log += text;
    let end = log.indexOf("\n");
    while (end >= 0) {
      line(log.slice(0, end));
      log = log.slice(end + 1);
      end = log.indexOf("\n");
    }
    wake();
  });
  child.stdout.on("data", (chunk) => {
    chunks.push(chunk);
    held += chunk.length;
    if (held >= HELD_BYTES && held >= wanted) {
      child.stdout.pause();
    }
    wake();
  });
  child.on("error", (error) => {
    failure = error;
    wake();
  });
  child.on("close", (code, signal) => {
    if (log !== "") {
      line(log);
      log = "";
    }
    ended = {code, signal};
    wake();
  });

  const take = (count) => {
    const bytes = new Uint8Array(count);
    let at = 0;
    while (at < count) {
      const chunk = chunks[0];
      const part = Math.min(chunk.length, count - at);
      bytes.set(chunk.subarray(0, part), at);
      at += part;
      if (part === chunk.length) {
        chunks.shift();
      } else {
        chunks[0] = chunk.subarray(part);
      }
    }
    held -= count;
    return bytes;
  };

  const undecodable = () => {
    if (noStream) {
      return unreadable("the file has no video stream");
    }
    return unreadable(`the video cannot be decoded: ${lastLine === "" ? "the decoder program gave no frame and no reason" : lastLine}`);
  };

  try {
    for (;;) {
      while (infos.length === 0 && ended === null && failure === null) {
        await changed();
      }
      if (failure !== null) {
        throw failure;
      }
      if (infos.length === 0) {
        if (ended.code !== 0) {
          throw undecodable();
        }
        return;
      }
      const info = infos.shift();
      if (timeBase === null) {
        throw unreadable("the video cannot be decoded: the decoder program named no time base");
      }
      wanted = 4 * info.width * info.height;
      while (held < wanted && ended === null && failure === null) {
        child.stdout.resume();
        await changed();
      }
      if (failure !== null) {
        throw failure;
      }
      if (held < wanted) {
        throw ended.code !== 0 ? undecodable() : unreadable("the video cannot be decoded: a frame is cut short");
      }
      const rgba = take(wanted);
      wanted = 0;
      if (held < HELD_BYTES) {
        child.stdout.resume();
      }
      const time = /^-?\d+$/.test(info.pts) ? [BigInt(info.pts) * timeBase[0] * 1000n, timeBase[1]] : null;
      yield {width: info.width, height: info.height, rgba, time};
    }
  } finally {
    if (ended === null) {
      child.stdout.destroy();
      child.stderr.destroy();
      child.kill("SIGKILL");
    }
  }
}
