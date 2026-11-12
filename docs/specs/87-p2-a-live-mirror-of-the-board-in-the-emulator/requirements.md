# Requirements

Seed 87, `project-seeds/87-p2-a-live-mirror-of-the-board-in-the-emulator/seed.md`. The core,
the firmware, the emulator and the command tool. Six forms of one command word, `plan`, are
added, approved by the owner on 2026-11-10: `plan`, `plan since <version>`, `plan on`, `plan
off`, `plan push on` and `plan push off`. The app, its files and the APK are not changed.
Built on the branch of pull request #63, `all-unmerged-seeds`, as the seed says.

## 1. Planning

1.1 `plan on` switches planning on and `plan off` switches it off, for the whole core. Both
answer `{"ok":true}`. Planning is off at every start and is not saved.
1.2 With planning off, every turn plays, and every seed and order is drawn, exactly as before
this seed; the core's suites pass unchanged.
1.3 With planning on, the plan holds the turn on the LEDs and the turns that begin within the
next 10 minutes, at most 8 in all, in the order they will play.
1.4 What the plan holds is what plays, unless a change of 3.2 comes first: each planned
turn begins at its planned start with its planned animation, point, seed and brightness.
1.5 The plan is decided by the code that decides the turns as they come, run ahead on a
copy of the playback's state that is put back afterwards; the playback is not disturbed by
it, no file is opened and nothing is written.
1.6 The plan ends early, its last item the last it can be sure of:
- at a turn whose end is not known yet: an animation whose loop's length the core has not
  learnt, its `end` `null`;
- at the turn during which the current playlist's window passes: what plays after it is
  planned once it has passed;
- where nothing would play.

## 2. The reply of `plan`

2.1 One JSON object of at most 1,024 bytes:
`{"ok":true,"planning":<bool>,"version":<n>,"now":<ms>,"on":<bool>,"brightness":<0-255>,`
`"rotation":<0|90|180|270>,"mini":<bool>,"test":<bool>,"snake":<n|null>,"items":[...]}`.
2.2 `now` is the core's time of the reply, on the clock of its refreshes, in milliseconds;
every time of the reply is on that clock.
2.3 `on` is the LEDs' visibility now; `brightness` the runtime default; `rotation` the saved
orientation; `mini` whether the miniature output is acknowledged on; `test` and `snake` as
`mapping get` gives them. While a test shows, `items` is empty.
2.4 Each item: `start`, when its part begins on the LEDs; `end`, when it ends, or `null`;
`from`, the turn's own time at `start` in milliseconds, given when not 0; `id`, its
animation's id; `key`, its file's CRC-32 and size as `crc-size`, or `null` when no catalog
names it; `loop`, its loop's length in milliseconds when known; `seed`, for a widget, when it
is known; `brightness`, when the file's selected value differs from the default.
2.5 The item on the LEDs is first. For a turn that went on after a break, the item on the
LEDs may give the moment its turn's time was 0 as `start` with no `from`: its point at any
moment is the same.
2.6 The reply holds as many items as fit, in order. `items` is empty while nothing plays,
while the show is invalid and while a test shows; `plan` is answered then too.
2.7 With planning off the reply holds the item on the LEDs alone, its `seed` only when it was
drawn.
2.8 A cycle that plays gives its turns as items: each animation of its list for its
`seconds`, a text's rounded up to whole passes.

## 3. Versions and `plan since`

3.1 `version` is 1 at the start and grows by one at each change of what the reply says,
`now` aside; it is counted with planning off too.
3.2 A change is: every command line but those that only read, which are `status`, `space`,
`fault`, `list` and `list in`, `read`, `saved`, `catalog` and `catalog page`, `order get`,
`mapping get`, `rotation`, `time`, `schedule`, `plan` and `plan since`; the turn on the LEDs
that changes; a drive taken up or dropped; a file read whole or found faulty; a catalog read
again; the window of a playlist that passes; the LEDs switched by the schedule; and the
miniature output acknowledged.
3.3 A change that leaves what the reply says as it was may still count; the version never
stays when the reply changed.
3.4 `plan since <version>` answers
`{"ok":true,"planning":<bool>,"version":<n>,"now":<ms>,"unchanged":true}` when the core's
version is the one given, and the whole reply of `plan` otherwise. `<version>` is 0 to
4,294,967,295 in decimal; another form is `bad-argument`.

## 4. The push

4.1 A serial way is a route that carries lines the client did not ask for: the board's UART
on the socket marked COM, the chip's own USB socket, the emulator's serial port and each
connection of its line port. HTTP is none.
4.2 `plan push on`, on a serial way, makes the core give that way a line `#plan ` and the
reply of `plan` at once and after every new version; `plan push off` stops it. Both answer
`{"ok":true}`. Over HTTP both are answered `unsupported`.
4.3 The push is not saved; a restart stops it on every way.
4.4 A way is given only the newest version: a version that a newer one passes before the way
has room for it is not given.
4.5 The host writes a `#plan` line between replies, never inside one, and never waits for
room: the UART writes it when its queue takes the line whole, the chip's own socket in
pieces as its buffer takes them, answering the next line only after it.
4.6 A client that passes over `#` lines, the command tool and the app among them, passes over
`#plan` lines.

## 5. Draws while planning

5.1 While planning is on, every draw takes the noise that was the core's when planning was
switched on, in place of the noise of the moment: a widget's seed is
`mix(noise ^ mix(id ^ start))` of that noise, and a new order of the clocks or of the
messages is drawn from it. The planned turn and the turn that plays draw the same values.
5.2 A turn that goes on after a break keeps the seed it had.
5.3 With planning off, the draws are as before this seed.

## 6. The core's entry for the mirror

6.1 One entry of the core's library, `odrig_core_mirror`, which no command reaches, makes
the core show at every refresh, in place of its show, a turn the host describes: a file
opened by name through the host, its loop's length when known, the moment its time was 0
on the clock of the polls, its seed, its brightness, whether the LEDs are on, the rotation,
and the diagonal or a snake's test. A name that is empty shows nothing.
6.2 The host owns the description and may change it between polls; a call with none ends
it, and the core goes back to its show. The core writes nothing to storage meanwhile, and
the board never calls the entry.
6.3 A file's picture at a time of its turn is the one its own playback shows at that time,
the frames, a text and a clock with the same seed alike.

## 7. Memory and time

7.1 The core asks for no new block; its object stays at most 4,096 bytes, and the target
file with a drive below 131,072 bytes, as the suite measures; the memory table of
`docs/core.md` gives the new figures.
7.2 Every new frame of the stack stays under 512 bytes.
7.3 A reply of `plan` decides at most 8 turns, each as a turn's end decides the next, with
the storage reads the playlist makes anyway; nothing of it is done at a refresh with
planning off.
7.4 The board's refresh rate stays within 20 to 50 a second.

## 8. The firmware

8.1 The UART of the socket marked COM is way 1 and the chip's own USB socket way 2; their
lines reach the core with their way, HTTP's without one.
8.2 Each serial way writes the `#plan` lines the core gives it, as 4.5 says, beside the log
on the UART.

## 9. The emulator as a board

9.1 The emulator's serial port is way 1 and each connection of its line port gets a way
of its own while it is open; a way that ends is switched off as `plan push off` would.
9.2 A connection whose push is on gets the `#plan` lines between the replies to its lines.

## 10. The command tool

10.1 `odrigctl (--port NAME | --tcp ADDRESS | --http ADDRESS) plan [since N | on | off |
push on | push off]` sends the line and prints the reply.

## 11. Starting a mirror

11.1 `python -m emulator SHOW_DIR --mirror-port NAME`, `--mirror-tcp ADDRESS` or
`--mirror-http ADDRESS`: one of the three, a serial port, another emulator's line port, or
a board or an emulator over HTTP.
11.2 `--drive`, `--drive-folder` and `--record` do not go with a mirror: status 2. `--lan`
does; its warning says that the network's devices reach the board through the emulator.
11.3 The emulator prints `mirror: <link>` after its other lines.
11.4 The show folder gives the mapping the LEDs are drawn on; nothing of its show plays and
nothing is written into it while the mirror runs.
11.5 A link that cannot be opened is tried again every 2 seconds; the emulator runs
meanwhile and its page says it waits for the board.
11.6 A serial port is opened as the command tool opens one: 115,200 bits a second, eight data
bits, no parity, one stop bit, RTS lowered first and DTR second, never resetting the chip;
it is kept open; a port that goes away is opened again when it comes back.

## 12. The man in the middle

12.1 Every line a client sends to the emulator, over HTTP, on the line port or on the serial
port, goes to the board over the link, and the board's reply goes back to that client
unchanged. The emulator's own core answers none of them.
12.2 On a serial link or a line port the lines go one at a time, in the order they came, each
waiting for its reply. A reply goes only to the client of its own line; a client that has
stopped waiting gets nothing, and a reply that comes too late is dropped, never given to
another line. A line is waited for as long as its client waits, so the check of an upload
before `upload end` answers is waited for too.
12.3 Over an HTTP link each line goes as its own request, as its client sent it.
12.4 From the board, a `#plan` line is the mirror's and reaches no client; every other line
that is no reply goes to the clients of the line port and of the serial port and into the
page's log; a client of HTTP gets replies only.
12.5 The mirror's own lines take the link between the clients' lines, a client's first, and
their replies reach no client.
12.6 A lost link ends every wait: an HTTP client's request is closed without a reply, and the
page says the link is lost.

## 13. Keeping the plan

13.1 On joining, the mirror reads the board's `status`, then sends `plan on`, and `plan push
on` over a serial link or a line port, and asks for the plan. It takes every `#plan` line,
and asks `plan since <version>` every 10 seconds all the same.
13.2 Over HTTP it asks `plan since <version>` every 2 seconds, and at once after a client's
line that may change what plays.
13.3 A reply whose `now` went back, or that says planning is off, means a restart or another
client's `plan off`: the mirror switches planning on again and asks anew. On a serial link,
the loader's lines and a port that went away tell a restart too.
13.4 On Ctrl-C the mirror sends `plan push off`, and `plan off` when it had found planning
off, before the emulator ends.

## 14. What the mirror shows

14.1 At every moment the LEDs view shows what the latest plan says the board shows: the item
whose part holds the board's time, its file at the turn's point then, with its seed, its
brightness, the board's on or off, rotation, test and miniature output.
14.2 The board's time is the emulator's time plus an offset, kept from each reply's `now`
and half of its round trip.
14.3 A new version that leaves the item on the LEDs as it was does not restart it.
14.4 A turn joined late plays from the point the board is at.
14.5 The LEDs view is dark where the plan says nothing, after the last item's end, for an
item whose file is missing or has no key, and while no plan is known.
14.6 While the link is lost the mirror goes on with the plan it has.
14.7 On one computer, a mirror of another emulator shows every refresh's picture within two
refreshes of the other's.
14.8 WLED's current limiter and the budgets of seed 45 are not mirrored, nor the board's pins:
the show folder's mapping draws the LEDs.

## 15. The files

15.1 An item's file is the local file of its key, a file whose CRC-32 and size are the key's,
looked for in `collection/`, in the share's collection where `env` names it as
`ODRIG_ANIMATIONS`, and in `build/mirror/`.
15.2 A key found nowhere is fetched from the board with `read <id> <offset> 720`, between the
clients' lines, checked against the key when whole, kept in `build/mirror/` under its key,
and played from the board's point once there.
15.3 Meanwhile the page shows a band naming the item and the bytes fetched.
15.4 An item whose key is `null` is dark, with the reason that no catalog of its storage names
the file.

## 16. The page and the events

16.1 The header names the mirror's link, its state and the plan's version, and the board's
`status`: the latest reply to a `status` the link carried, asked for by the emulator itself
every 2 seconds while no client asks.
16.2 The command log lists each client's line with the board's reply, marked as the board's,
and the board's other `#` lines; the mirror's own lines are not listed.
16.3 The seek bar is not shown, and `POST /seek` answers `{"ok":false,"error":"mirror"}`.
16.4 A board whose canvas differs from the show folder's mapping is named with both sizes in
a band; the LEDs stay dark; lines still go through.
16.5 The event stream's `hello` names the link, and a `mirror` event carries its state.

## 17. The app

17.1 The app's files, `app/www/`, and the APK are not changed. The Controller view runs them
with the emulator as its target, and a phone reaches the board through the emulator's
`--lan` address, both through the man in the middle.

## 18. Documents and delivery

18.1 `docs/commands.md`, `docs/core.md`, `docs/show.md`, `docs/firmware.md`,
`docs/emulator.md` with its check list by eye, `docs/decisions.md` with the change log of the
owner's approval of 2026-11-10, `agent/vocabulary.md`, and entries at the end of
`docs/drifts.md`.
18.2 The suites of the core, the firmware's host tests, the emulator, the command tool and the
onboarding pass with the new tests, each seen failing first; the app's suite passes
unchanged.
18.3 Firmware images for the installation's board and the spare's module, built as
`firmware/fw.py` builds them, and an APK signed with the persistent key, all from the pushed
head.
18.4 The owner's checks stay open until the owner reports them: the emulator beside the wall
over USB and over Wi-Fi, a clock and a message with the wall's time and words, the LEDs off,
a display test, and the phone controlling the board through the emulator and straight.
