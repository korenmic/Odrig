# Design: the operators' app, converting and uploading

## Overview

The app gets a third screen, the storage screen: the free storage, the installed
animations with their sizes and a button to remove each, and a part that adds an
animation. That part reads the media with what the web view has, the `<video>` element
for a video and `ImageDecoder` for a GIF, hands the frames to the converter's
`importFrames`, encodes the result with the converter's `odrg.encode`, draws it, and
uploads it with the upload commands, one line after the other in the client's one queue.
The core's `status` reports the canvas, which the conversion needs. The converter's
library is served beside the web code under `converter/` and copied into the APK by its
build.

## What this design relies on

- The converter's library runs in a web page as it is, and `importFrames` takes the
  frames of a video as `{width, height, rgba, time}` and those of a GIF as
  `{width, height, rgba, delayMs}`, the GIF's pictures composited as browsers composite
  them ([converter.md](../../converter.md), "The library").
- `upload begin` answers with `chunk`, the most bytes of one `upload data`; `upload end`
  answers `busy` while the target checks the file; an uploaded animation joins the
  playlist by itself ([commands.md](../../commands.md)).
- The app's client sends one request at a time: what the operator asked for first, then a
  status that is due, then a list that is due (seed 09).
- The emulator serves the files of `app/www/` under `/app/` (seed 09, task 10), and the
  APK's web code is the folder `build/app/www`, staged by the build from `app/www/`.
- Android's web view and Chrome have `ImageDecoder` from version 94 and
  `requestVideoFrameCallback` from 83; the APK asks for a web view of 80 at least.

## The core: the canvas in `status`

`status` writes, after `error`, `"width":W,"height":H` from the core's canvas, or
`"width":null,"height":null` while the core has no legs, which is while it has no mapping
it can use. The reply grows by at most 26 bytes; the longest reply stays far under
`ODRIG_REPLY_MAX`. The core takes no memory more. The reference player of
`tests/core/support.py` reports the canvas of its mapping in the same place.

```
{"ok":true,"on":true,"brightness":32,"playing":"all","animation":1,"fps":50,"error":null,"width":60,"height":60}
```

The emulator, the firmware and the command tool hand replies on as they are; their
documents and the tests that name the members of `status` learn the two.

## The converter's library beside the web code

The app imports `./converter/index.js`. That path is not a file of `app/www/`:

- `app/apptool/webserver.py` answers `/converter/<name>.js` with
  `converter/lib/<name>.js`, so `serve` and the suite's server, which uses the same
  handler, give it.
- `app/apptool/stage.py` copies every file of `converter/lib/` into
  `build/app/www/converter/` after the web code, so the APK holds it.
- The emulator's table of the app's files adds `/app/converter/<name>.js` from
  `converter/lib/`.
- The suite of the APK reads every file of `converter/` in the package against
  `converter/lib/`, byte for byte.

## The client

`client.js` keeps more of what the replies said:

- `state.status` has `width` and `height`.
- `state.animations` keeps `bytes` of each animation.
- `state.space` is `{free, total}` of the newest reply to `space`, or null.

New requests:

- `space`: due when the storage screen is shown, every ten seconds while it is, and after
  a removal or an upload.
- `remove(id)`: what the operator asked for, as `play` is. After it, the list and the
  space are due.
- An upload is a job: `client.upload(job)` takes an object with a `step()` that gives the
  next line's function, or null when it is done. Between two lines of the job, a status
  that is due goes first: the queue gives the job a line, then a due status, then the
  job again. Nothing of the job is sent while the app is hidden; it goes on when the app
  is shown again.

## The storage screen

`screens/storage.js` and a third section of `index.html`, `storage`. The bottom has three
buttons, `Show`, `Storage` and `Target`, each a third of the width. The show screen stays
the app's first screen: the back gesture goes from the storage screen or the target
screen to it, and from it out of the app.

From the top:

1. `Free 3.2 MB of 10.4 MB`, from `space`, megabytes of 1,000,000 bytes with one decimal.
2. `Installed`, and a row for each animation of the list: `<id> <file> <size> KB` and a
   button `Remove`. A press opens a confirmation in the place of messages:
   `Remove animation <id> <file> from the installation?` with `Remove it` and `Keep it`.
3. `Add an animation`:
   - `Choose a video or a GIF`: a `<label>` that looks like a button, over an
     `<input type="file" accept="video/*,image/gif">`. The phone shows its own picker.
   - The media's name and length, then three buttons `Fill`, `Fit`, `Stretch`, the one
     chosen marked, each with one line that says what it does, and two fields, `Start at`
     and `Length`, in seconds with up to three decimals.
   - `Make the animation`. While it converts: `Making the animation: 40%` and `Stop`.
   - The result: a `<canvas>` of the target's shape, as wide as the screen, drawing the
     animation's pictures in a loop at their durations, with
     `<frames> frames, <seconds> s, <size> KB`, and `Upload`.
   - While it uploads: `Sending: 45%, 12 KB a second` and `Cancel`.

## Converting

`convert.js` holds the conversion; it knows no screen.

**A GIF.** `new ImageDecoder({data, type: "image/gif"})`. Every frame index is decoded in
turn; the decoder gives the frame composited as the browser shows it, which is the picture
`importFrames` wants. The frame is drawn onto a canvas of its own size and read with
`getImageData`; `delayMs` is the frame's `duration`, which the decoder gives in
microseconds, divided by 1,000. A web view without `ImageDecoder` gets the message
`no-gif-decoder`.

**A video.** A muted `<video>` with the media as its source and `preload` `auto`. From
the start of the part on, every 20 ms tick plus half a millisecond is sought; after each
seek the frame on screen is taken with `requestVideoFrameCallback`, whose `mediaTime` is
the frame's presentation time. A frame whose time was taken already is passed over, so
the source holds each frame of the video once with its own time, given to `importFrames`
as `[microseconds, 1000]`. The frame is drawn onto a canvas of the video's size, at most
1,280 pixels on its longer side: a larger video is drawn smaller, by the web view. The
seeking goes on until `importFrames` asks for no more, or the video ends.

**The conversion.** `importFrames(source, {width, height}, {fit, startMs, durationMs})`
with the canvas of `status`, then `odrg.encode(animation, {compressed: true})`. Progress
is the time the source has reached within the part. `Stop` makes the source throw, which
ends the conversion with nothing kept. Every `Rejection` of the converter is a message
with its reason; a video the web view cannot play is `unreadable-media`, as the command
line names it.

**The preview** draws each picture of the animation, bottom row first as the format
keeps it, scaled up with no smoothing, and waits each frame's `ms` before the next.

## Uploading

`upload.js` makes the job of an animation:

1. The id: the lowest from 1 up that no item of the newest list has. The file name: the
   media's name without its ending, in lower case, every character outside `a`-`z`,
   `0`-`9`, `-` and `_` turned into `-`, `animation` when nothing is left, cut so that
   with `.odrg` it has at most 32 characters, and made unique among the listed files with
   `-2`, `-3` and so on, cut again where needed.
2. Before the first line the file's size is compared with the free storage of `space`:
   `bytes + bytes / 256 + 16,384` more than the free bytes is `no-space`, as the target
   judges it.
3. `upload begin <id> <file> <bytes>`, then `upload data <offset> <base64>` with pieces of
   `chunk` bytes in the base64 of RFC 4648, section 5, without `=`, then
   `upload end <crc32>`, the CRC-32 of zlib in eight hexadecimal digits, which `crc32.js`
   computes. `busy` to `upload end` sends it again after 250 ms.
4. Progress is `received` of the newest reply over the size; the speed is the bytes taken
   in the last two seconds, over two.
5. `Cancel` sends `upload cancel` after the line that is under way.
6. `no-upload` to a line means the target dropped the upload: after the app was away for
   60 seconds, or because something else ended it. The job ends with that message.
7. Afterwards the list and the space are due; the new animation is in the list.

## Messages

Every message is a sentence and its code in brackets, in `messages.js`:

| Code | When | The sentence |
|---|---|---|
| `no-canvas` | `status` has no canvas. | The installation has no usable mapping, so the app does not know the canvas to convert for. |
| `no-gif-decoder` | The web view has no `ImageDecoder`. | This phone's web view cannot read GIF files. Update Android System WebView. |
| `unreadable-media` | The web view or the converter cannot read the media. | The phone cannot read this file as a video or a GIF. |
| `bad-range` | The part is not inside the media. | The part does not lie inside the file: start at `<start>` s and length `<length>` s. |
| other converter reasons | `canvas-too-large`, `too-many-frames` and the like. | The animation cannot be made: `<reason>`. |
| `no-space` | Before the upload, or the target's refusal. | The animation needs `<size>` KB and the installation has `<free>` KB free. |
| `busy` | The target reads its animations, or another upload is open. | The installation is busy. Try again in a moment. |
| `in-use` | `remove` of an animation a cycle lists or that a USB stick holds; `upload begin` of a name or id in use. | Animation `<id>` cannot be removed: a cycle plays it, or it is on a USB stick. / That name or id is in use; the list is asked for again. |
| `unknown-id` | `remove` of an animation removed meanwhile. | Animation `<id>` is not installed any more. |
| `bad-file` | `upload end`. | The installation refused the file: `<reason>`. |
| `bad-checksum`, `incomplete`, `bad-offset` | The upload lost bytes on the way. | The upload did not arrive whole. Upload again. |
| `no-upload` | The target dropped the upload. | The installation dropped the upload, after the app was away for a minute or more. Upload again. |
| `storage-error` | `space`, `remove`, the upload. | The installation could not use its storage. |
| `uploaded` | Success. | Uploaded as animation `<id>` `<file>`. It plays in the playlist. |
| `removed` | Success. | Removed animation `<id>` `<file>`. |

The last two are no failures and have no code in brackets.

## Tests

`tests/app/`, in Chrome without a window, against the emulator unless a stand-in target
is named:

- The storage screen: the space and the rows with their sizes; three buttons at the
  bottom, each a third of the width; the back gesture.
- A removal confirmed, and one kept; `in-use` for an animation a cycle lists, with a
  stand-in target.
- Converting: the media are made while the suite runs, as the converter's suite makes
  them, with the Python of `.venv` and `tests/converter/media_fixtures.py`: a GIF, and an
  mp4 in H.264, which Chrome plays. The test hands the file to the input as the picker
  would. For the GIF with each fit and with a part, the uploaded file is compared with
  what `node converter/odrig.js import` and `encode` make of it, byte for byte; for the
  mp4 the durations are compared, and every colour within 8 of the command line's.
- Uploading both, and playing each with its row on the show screen, which `status`
  then names.
- `Stop` while converting, and `Cancel` while uploading, after which `space` is as it was.
- The messages, with stand-in targets for the refusals.
- The look of the storage screen at widths of 360 and 320 pixels, as the other screens'.

`tests/core/`: `status` with a canvas, with no mapping, with a mapping the core refuses,
and with a show that is invalid for another reason. `tests/emulator/`: the members of the
status event, and the converter's files under `/app/converter/`. `tests/apk/`: the
converter's files in the package.

## Documents

[android-app.md](../../android-app.md): the storage screen, converting, uploading,
removing, the messages, the lines the app sends, the suites and the check on a phone.
[commands.md](../../commands.md), "Status reply"; [core.md](../../core.md) where it names
the reply; [emulator.md](../../emulator.md), the event `status` and the app's files;
[decisions.md](../../decisions.md), a line in the change log; `AGENTS.md`: the seed leaves
"What is coming".

## What needs the owner

- The check on a phone: converting and uploading a video with the APK, to the emulator
  on the local network and to the board on its own network.
