# Requirements: the operators' app, converting and uploading

Seed: [`project-seeds/17-p2-operators-app-converting-and-uploading/seed.md`](../../../project-seeds/17-p2-operators-app-converting-and-uploading/seed.md).

The second part of the operators' app. On the phone the operator picks a video or a GIF,
chooses how it fits the canvas and which part of it to use, sees the result drawn, and
uploads it to the installation with the progress shown. The app also shows the size of
each installed animation and the free storage, and removes an animation.

The seed has no open question. The owner approved on 2026-10-12 the one change of the
command list it needs: the reply to `status` reports the size of the canvas. The owner
approved the seed for implementation on 2026-10-15.

In this document "the app" is the web code of `app/www/` in the APK, in a browser and in
the emulator's page; "the target" is the installation or an emulator, at the address the
app has; "the converter" is the library `converter/lib/`; and "the media" is the video or
GIF file the operator picks.

## Requirement 1: the canvas in `status`

1. The reply to `status` SHALL have two more members, after `error`: `width` and `height`,
   the canvas of the installed mapping in pixels, as the core reads it. While the core has
   no mapping that it can use, both SHALL be `null`.
2. They SHALL be reported while the show is invalid for a reason other than the mapping.
3. The core, the emulator, the firmware and the command tool SHALL give and print them
   alike, and the reference player of the core's suite SHALL report them.

## Requirement 2: the storage screen

1. The app SHALL have a third screen, the storage screen, beside the show screen and the
   target screen, reached with a third button at the bottom.
2. It SHALL show the free and the total storage of the target, as `space` reports them,
   in megabytes with one decimal.
3. It SHALL list every installed animation in the order of the show, with its id, its
   file's name and its size in kilobytes, as `list` reports them. Cycles are not listed.
4. Each animation SHALL have a button that removes it. A press SHALL ask for a
   confirmation that names the animation; only a confirmed removal SHALL send `remove`.
5. After a removal and after an upload, the list and the space SHALL be asked for again.
   While the screen is shown they SHALL be asked for every ten seconds.

## Requirement 3: converting

1. The operator SHALL pick the media with the phone's own way of choosing a file: a video
   or a GIF. The app SHALL take files that the phone's web view can decode: GIF, and
   videos that its video element plays.
2. The operator SHALL choose the fit, `fill`, `fit` or `stretch`, as the converter defines
   them, with `fill` chosen at first; and the part: a start and a length in seconds, the
   whole media at first.
3. The app SHALL convert with the converter: it decodes the media with what the web view
   provides, hands the frames to the converter's `importFrames` with the canvas of the
   target's `status` and the chosen fit and part, and encodes the animation as a
   compressed ODRG file.
4. For a GIF the file SHALL be byte for byte the one the converter's command line makes
   from the same GIF with the same fit and part, with `import` and then `encode`. For a video, its frames SHALL have the
   durations of the command line's, and the colours MAY differ by the little that two
   decoders differ.
5. Converting SHALL show its progress and SHALL be stoppable. The rest of the app SHALL
   keep working while it converts.
6. The result SHALL be drawn on a canvas of the target's shape, playing in a loop at the
   durations of its frames, with its size in kilobytes and its length in seconds.
7. Without a canvas in `status`, converting SHALL be refused with a message that says why.

## Requirement 4: uploading

1. The operator SHALL upload the converted animation with one press. The app SHALL choose
   the id, the lowest from 1 up that no listed item has, and the file name: the media's
   name in lower case, every character outside `a`-`z`, `0`-`9`, `-` and `_` turned into
   `-`, cut so that the whole name has at most 32 characters with `.odrg`, and made
   unique among the listed files with `-2`, `-3` and so on.
2. The app SHALL upload with `upload begin`, `upload data` and `upload end` as
   [commands.md](../../commands.md) defines them, one line at a time, in pieces as large as
   the reply to `upload begin` allows. While the target answers `upload end` with `busy`,
   the app SHALL send it again.
3. The upload SHALL show the percentage of the file sent and the speed, in kilobytes a
   second, and SHALL be stoppable: the app then sends `upload cancel`.
4. Before the upload the app SHALL compare the file's size with the free storage, and say
   when it does not fit; the target's own refusal stays the judge.
5. The uploaded animation SHALL take its place in the playlist without anything else
   being sent, and the show screen SHALL list it.
6. While the app is not on the phone's screen it SHALL send nothing. When it is back, the
   upload SHALL go on; when the target has dropped it meanwhile, the app SHALL say so.

## Requirement 5: what the operator is told

1. Every failure SHALL be told in a sentence with its code in brackets, as the app's other
   messages are: media the converter or the web view cannot read, a part outside the
   media, a file that does not fit, and every refusal of `space`, `remove` and the upload
   commands, with the reason of `bad-file`.
2. A successful upload SHALL be told with the id and the file name it got, and a
   successful removal with the id and the file name removed.

## Requirement 6: the app as a package

1. The web code SHALL stay plain JavaScript, HTML and CSS. It SHALL import its own files
   and the converter's library, which is served beside it under `converter/`, and nothing
   else. No decoder of video or GIF is added.
2. The converter's library SHALL be used as it is: the build of the APK copies it into
   the package, and `serve`, the suite's server and the emulator's page serve it from
   `converter/lib/`. No copy of it is kept in the repository.
3. The APK SHALL be built with `python3 app/app.py build`, and the suite of the APK SHALL
   check that the package holds the web code and the converter's library byte for byte.
4. The core's working memory for the 60 x 60 canvas with 100 items SHALL stay under
   128 KB.

## Requirement 7: tests and documents

1. The app's suite SHALL drive the web code in Chrome without a window against the
   emulator, and cover: the storage screen, a removal confirmed and one not, converting a
   GIF and a video with each fit and with a part, the comparison of Requirement 3.4,
   uploading both and playing them afterwards, stopping a conversion and an upload, and
   every message.
2. Every suite that needs no board and no phone SHALL pass.
3. [android-app.md](../../android-app.md) SHALL say how to convert, upload and remove,
   what each message means, and the check on a phone; [commands.md](../../commands.md) and
   [core.md](../../core.md) SHALL have the two members of `status`.
4. The owner SHALL convert and upload a video with the APK on a phone, to the emulator on
   the local network and to the board on its own network, and see it play. Only a person
   can make that check.

## Left out on purpose

- Turning a video that was filmed upright: the converter does not apply a rotation.
- Editing an animation after it was converted, and uploading a file made elsewhere.
- Uploading to a USB stick: the stick is read only.
- Changing `show.json` from the app: the order, cycles, `start` and the turn's numbers.
