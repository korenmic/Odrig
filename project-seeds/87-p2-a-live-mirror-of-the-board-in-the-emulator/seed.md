# A live mirror of the board in the emulator

## Summary

Let the emulator on a computer show, as it happens, what a real board shows on its LEDs,
from what the board tells of its playback and never from its pixels. While asked to, the
board keeps a plan: the turn on the LEDs and the turns it has decided to play next, the
shuffled clocks and messages among them with the seeds that draw them, each named by the
key of its file and by the board times of its start and its end, under a version that
grows at every change. Joined to the board by a USB cable or over Wi-Fi, the emulator
plays the same files, found by their keys in the collection or fetched from the board
once, at the same moments, with its own core. It also stands between the operators' app
and the board: every line of the app in its Controller view, of a phone that reaches it
and of the command tool on its line port goes to the board through it, and the reply comes
back to the one who sent the line, as if each were on the board's own port. The plan's
lines are the mirror's, and everything else goes back to the one who asked. The app stays
as it is.

## Priority

`P2`.

## Product Context

On 2026-11-10 the owner asked to "connect via both PC and android into a real working
esp32s3 board, and have the emulator show me what would be shown on the esp32s3", from what
the board tells as it plays, since the board and the computer's clone share the catalog of
every file uploaded. The owner settled the design the same day, in words and in answers to
four questions:

- **Identities and times, never pixels.** The board tells "only by ID when a new animation
  starts", and gives no fingerprint of its frames. Over a link that cannot push, each
  exchange gives when the turn ends and "the next few intended playlist items (even when it
  is supposed to be 'random' / 'shuffled')", so that the computer asks again only when
  they are spent.
- **The commands.** `plan`, `plan since <version>` and `plan push on|off` were approved on
  2026-11-10, and the owner added that "plan should be toggleable", which this seed makes
  `plan on` and `plan off`.
- **The seed of a clock** is drawn when the clock is placed in the plan, not when its turn
  begins.
- **The phone is a controller only, forever.** It stays one with the emulator alone, with
  this mirror (the owner's "50% emu 50% board") and with the board alone: "the phone app
  never changes based on what is being used". The app's side of the emulator "should not
  behave differently and should remain the same".
- **A man in the middle.** In the emulator, "a man in the middle piece of code" receives the
  board's answers. The plan's answers make the mirror, and "everything else would go
  directly to the app's runtime side of the emulator". The board's USB serial port is
  supported, its traffic forwarded "without issues as if it was connected directly to
  serial via the phone".

What there is today:

- **The emulator.** It runs its own core on a show folder and draws what the core sends to
  each leg. Lines reach it as `POST /odrig`, on its line port on Windows and on its serial
  port on a Mac. Its Controller view runs the app's own files, `app/www/`, with the
  emulator's address as the app's target.
- **The board's transports.** The board takes the same lines on its two USB sockets, the
  chip's own and the one marked COM, and as `POST /odrig` over Wi-Fi. It writes its log as
  `#log` lines between replies on the socket marked COM, and the chip's loader prints lines
  there at a start. A line that begins with `#` is no reply: the command tool and the app's
  USB link of seed 82 pass over it.
- **Status.** `status` names what is on the LEDs now: `animation`, `file` and a widget's
  `seed`. It says nothing of what comes next, nor when the turn ends: `left` is the 24
  hours of the playlist's window.
- **Widget seeds.** A widget's seed is drawn when its turn begins, from a noise that the
  times of the refreshes make. Nothing outside the board can know it before.
- **Time.** The core keeps time on a grid of 20 ms and never stretches a turn: a late
  refresh skips frames. The end of a turn is an exact board time once its loop's length is
  known.
- **The files and their keys.** Every file the installation was given is in `collection/`,
  and the heavy ones are on the share, whose path is `ODRIG_ANIMATIONS` in `env`. A file's
  key is its CRC-32 and its size, `1a2b3c4d-52340`. The catalogs of the board's own storage
  and of the card give the key of each of their files, and `read <id> <offset> <count>`
  gives a file back, 720 bytes at a time.
- **Serial ports.** The command tool opens a serial port without resetting the chip, RTS
  lowered first and DTR second, on macOS, Linux and Windows (`odrigctl/winserial.py`).

## Required Behavior

### The plan, on the board and in the emulator's core alike

1. **Planning, switched on and off.** `plan on` makes the board decide its turns ahead: the
   turn on the LEDs and those that begin within the next 10 minutes, at most 8 in all, in
   the order they will play, decided further as time passes. `plan off` stops it, and each
   turn is again decided as it begins. Planning is off at every start and is not saved.
   With planning off, the board plays exactly as it does before this seed.
2. **What is decided is what plays.** A turn the plan holds plays as the plan says, unless a
   change of rule 4 comes first.
   - **Shuffled orders.** They are drawn when the plan needs them: the next clock of the
     order of the clocks, a new order when one is used up, and the next message of its bag.
   - **Seeds.** Every turn of a widget, a clock, a message or another, gets its seed when it
     is placed in the plan. It is drawn from the same noise and in the same way as today,
     with the start the plan gives the turn. With planning off it gets its seed when it
     begins, as today.
   - **Breaks.** A turn that a break pauses when its 5 minutes are counted is two items: its
     part before the break, and after the break its rest, with the point of its time it goes
     on from.
3. **The plan.** `plan` answers with the plan, in one reply:

   ```
   plan
   {"ok":true,"planning":true,"version":41,"now":5120334,"on":true,"brightness":128,"rotation":0,"mini":false,"test":false,"snake":null,"items":[{"start":5101200,"end":5131200,"id":60004,"key":"9f3a10c2-52340"},{"start":5131200,"end":5161200,"id":7,"key":"0c11d2e4-40","seed":2271034987},{"start":5161200,"end":5185600,"id":8,"key":"77ab0f10-29996","seed":19224},{"start":5185600,"end":5199200,"from":30000,"id":60004,"key":"9f3a10c2-52340"}]}
   ```

   - `planning` says whether planning is on.
   - `version` grows by one at every change of what the reply says, `now` aside. It is 1 at
     the start.
   - `now` is the board's time when the reply was made: the milliseconds since the start,
     on the clock of its refreshes. Every other time of the reply is on that clock.
   - `on` says whether the LEDs are on now, and `brightness` is the runtime default, as
     `status` gives both.
   - `rotation` is the saved orientation in degrees, and `mini` whether the miniature
     output is on, as acknowledged.
   - `test` and `snake` are as `mapping get` gives them: the diagonal or a snake's test that
     shows. While a test shows, `items` is empty.
   - `items` holds the turns, the one on the LEDs first, and is empty while nothing plays.
     Each item has these members:
     - `start`: the board time at which the turn began or begins.
     - `end`: the time it ends, or `null` while that is not known yet, as for a file whose
       loop's length the board has not learnt. An item whose `end` is `null` is the last.
     - `from`: the point of the turn's own time at `start`, in milliseconds. It is given
       only when it is not 0, for a turn that goes on after a break.
     - `id`: its animation's id, as `play` and `read` take it.
     - `key`: its file's key, as its storage's catalog gives it, or `null` when no
       catalog names the file.
     - `seed`: given for a widget.
     - `brightness`: given when a saved brightness makes the file's value differ from the
       default.
   - The reply holds as many items as fit into a reply of 1,024 bytes, in order. It is
     answered while the show is invalid too, with no items. With planning off it holds the
     turn on the LEDs alone.
4. **A new version at every change.** Whatever changes what the reply would say makes a new
   version, at once. Among the causes:
   - the turn on the LEDs that ends, and the turn decided after the last;
   - a line from any client, by any way, that changes what plays or how it shows: `play`,
     `play all`, `on`, `off`, `brightness` in its three forms, `repeat`, `order move`,
     `ignore`, `remove`, an installed upload, `clocks`, `mapping test`, `rotation set`,
     `debug mini`, `schedule` and `time` lines, and a folder made, removed or moved;
   - `plan on` and `plan off`;
   - the card put in or pulled out, or its catalog read again;
   - a file read whole after a start, or found faulty;
   - a playlist's window that ends;
   - the schedule switching the LEDs.

   A change makes the board decide again the turns after the one on the LEDs. A turn on
   the LEDs that the change leaves as it was keeps its start, its point and its seed. A
   restart begins at version 1, with planning and every push off.
5. **Asking for changes only.** `plan since <version>` answers
   `{"ok":true,"planning":true,"version":41,"now":5122410,"unchanged":true}` while the
   board's version is the one given, and the whole plan otherwise. So a client that polls
   gets the plan only when it changed, and a client whose board restarted gets it at once.
6. **The push.** `plan push on` makes the board write the plan on that serial way as one
   line, `#plan ` and the reply `plan` would give, at once and at every new version.
   - **The ways.** A way is each of the board's two USB sockets, the emulator's serial
     port, or one connection of its line port.
   - **Off.** `plan push off` stops it. The push is not saved, and a restart stops it.
   - **Timing.** The line is written between replies and never inside one. It never makes
     a reply or a refresh wait: each way has one place for its newest plan, and a newer
     version replaces a line not begun yet.
   - **HTTP.** HTTP carries no line the client did not ask for, so `plan push on` and
     `plan push off` sent over it are answered `unsupported`.
   - **Clients.** A `#plan` line is no reply: every client that passes over `#` lines, the
     command tool and the app among them, passes over it.
7. **Never in the way.**
   - Deciding ahead takes at most one turn's decision at a refresh, with the storage reads
     the playlist makes anyway.
   - The reply and the pushed line are made from what the plan keeps, without reading
     storage.
   - The plan is a fixed table of the core, counted in the memory table of `docs/core.md`.
     It allocates nothing as it runs, and needs no room beyond one reply.
   - The board's refresh rate stays where it is, within 20 to 50 a second.
8. **The command tool.** `python -m odrigctl (--port NAME | --tcp ADDRESS | --http ADDRESS)
   plan [since N | on | off | push on | push off]` sends the line and prints the reply.

### The mirror, in the emulator

9. **Three ways of working, one app.** The operators' app is a controller in each of them,
   with no screen, word or step that differs between them, and with no control of the
   mirror:
   - **The emulator alone**, as today.
   - **The mirror** of this seed. The app in the Controller view keeps the emulator's
     address as its target and reaches the board through it. A phone reaches the board
     through the emulator's `--lan` address, or straight at the board's own address while
     the mirror runs.
   - **The board alone**, the phone talking to the board, as today.
10. **Starting a mirror.**

    ```
    python -m emulator SHOW_DIR (--mirror-port NAME | --mirror-tcp ADDRESS | --mirror-http ADDRESS) [the other options]
    ```

    - **The link.** A serial port, `COM5` or `/dev/cu.usbmodem101`; the line port of
      another emulator, `127.0.0.1:8601`; or a board or an emulator over HTTP,
      `http://4.3.2.1`.
    - **The show folder** gives the mapping on which the LEDs are drawn. Nothing of its
      show plays, and nothing is written into it while the mirror runs.
    - **Other options.** `--drive`, `--drive-folder` and `--record` do not go with a mirror:
      status 2. `--lan` does, and its warning says that the network's devices reach the
      board through the emulator too.
    - **Start.** The emulator prints `mirror: <link>` beside its other lines. A link that
      cannot be opened is tried again every 2 seconds, while the page says it waits for
      the board.
11. **The board's USB serial port.**
    - **Opening.** The emulator opens the port as the command tool does: 115,200 bits a
      second, eight data bits, no parity, one stop bit, RTS lowered first and DTR second. It
      never resets the chip nor enters its loader, on either socket.
    - **While it runs.** It keeps the port open while it runs. A port that goes away is
      opened again when it comes back.
    - **Other tools.** While the emulator holds the port, the command tool and its `--log`
      reach the board through the emulator's line port. The firmware tool needs the
      emulator stopped first.
12. **The man in the middle.**
    - **Clients' lines.** Every line a client sends to the emulator goes to the board over
      the link, and the board's reply goes back to that client unchanged. A client sends by
      HTTP (the Controller view, a phone, `odrigctl --http`), on the line port or on the
      serial port. The emulator's own core answers none of these lines.
    - **One line at a time on a serial link or a line port.** Lines go in the order they
      came, each waiting for its reply before the next, as a client of the board's port
      waits:
      - A reply goes only to the client of its own line.
      - A client that has stopped waiting gets nothing, and its late reply is dropped, never
        given to another line.
      - A long wait is waited as long as its client waits, as for the check of an upload
        before `upload end` answers.
    - **An HTTP link.** Over an HTTP link, each line goes as its own request, as its client
      sent it, so the board is asked as a phone asks it over Wi-Fi.
    - **Lines from the board that are no reply.**
      - A `#plan` line is the mirror's, and reaches no client.
      - Every other such line, the board's `#log` and the chip's loader's, goes to the
        clients of the line port and of the serial port, as the board's own port would
        give it, and into the page's log.
      - A client of HTTP gets replies only, as from a board.
    - **The mirror's own lines.** `plan on`, `plan push on`, `plan since`, `read` and
      `status` take the link between the clients' lines, a client's line first. Their
      replies reach no client.
    - **A lost link** ends every wait. The request of an HTTP client is closed without a
      reply, which the app takes as a lost reply, as from a board that did not answer, and
      the page says that the link is lost.
13. **Keeping the plan.**
    - **On joining.** The mirror sends `plan on`, and `plan push on` over a serial link or
      a line port, and asks for the plan. It then takes every `#plan` line, and asks `plan
      since <version>` every 10 seconds all the same.
    - **Over HTTP.** It asks `plan since <version>` every 2 seconds, and at once after a
      client's line that may change what plays.
    - **A restart.** A reply whose `now` went back, or which says that planning is off,
      means the board restarted or another client switched planning off. The mirror then
      switches it on again and asks anew. On a serial link the chip's loader lines, and a
      port that went away, tell a restart too.
    - **At its end.** On Ctrl-C the mirror sends `plan push off` before it ends, and `plan
      off` when it had found planning off.
14. **What the mirror shows.** At every moment the LEDs view shows what the plan says the
    board shows: the item's file, at the point of its turn the board is at.
    - **The item.** The file plays with the plan's seed and with the item's brightness.
      The board's rotation applies, and so does the miniature output, as the emulator shows
      its own.
    - **Tests.** The diagonal or a snake's test shows while one shows on the board.
    - **Dark.** The LEDs view is dark while the board's LEDs are off. It is also dark after
      the last item whose end has passed, until a newer plan says more.
    - **The board's clock.** The emulator keeps the offset between its clock and the
      board's from each reply's `now` and half of its round trip, and follows the board's
      clock at every reply.
    - **A new version** that leaves the turn on the LEDs as it was, the same start and id,
      does not restart it.
    - **A turn joined late,** at the mirror's start or once its file is there, plays from
      the point the board is at, as the seek bar's move does.
    - **A lost link.** While the link is lost, the mirror goes on with the plan it has, and
      the page says since when.
    - **How close.** On one computer, an emulator that mirrors another shows each turn's
      frames within two refreshes of the other's.
15. **The files.**
    - **Where a file comes from.** It plays from the copy whose key is the item's: among
      the files of `collection/`, of the share's collection where `env` names it, and of
      the files the mirror fetched before. Fetched files are kept in `build/mirror/` by
      their keys.
    - **A file found nowhere.** It is fetched from the board with `read`, 720 bytes at a
      time, between the clients' lines. Its key is checked once it is whole, and it is
      kept. Meanwhile its turn is dark, with a band naming the file and the part fetched.
    - **An item whose key is `null`** is dark, with the reason: no catalog of its storage
      names the file. `catalog rebuild` makes one.
16. **The page.**
    - **The header** names the link, its state and the plan's version. It shows the board's
      `status`: the latest reply to a `status` that crossed the link, which the emulator
      asks for itself every 2 seconds while no client does.
    - **The command log** lists each client's line with the board's reply, marked as the
      board's, and the board's `#log` lines. The mirror's own lines are not listed.
    - **The seek bar** is not shown and `POST /seek` is refused, since the page does not
      move the board's playback.
    - **Another canvas.** For a board whose canvas differs from the show folder's mapping,
      the page names both and the LEDs stay dark, while the lines still go through.
    - **The event stream.** `hello` names the link, and a `mirror` event carries the
      mirror's state: the link, the version, the offset, and a fetch under way.
17. **An emulator as the board.** The emulator's core plans as the board's does, and its
    line port and its serial port push. So an emulator mirrors another one by
    `--mirror-tcp` or `--mirror-http`, which is how the suites test the mirror without a
    board.
18. **What is not mirrored.**
    - WLED's current limiter, and the budgets of seed 45.
    - The board's pins. The show folder's mapping file draws the LEDs.
    - The board's frames themselves.

## Technical Constraints

- **Where it is built.** On the branch of pull request #63, `all-unmerged-seeds`, as seed
  61 was, because the plan covers what its seeds add:
  - board time and the daily schedule, 64;
  - the quarter turns, 65;
  - Clocks only, 66 and 68;
  - the board's own clocks, 61;
  - the display tests, 83;
  - the folders, 74, 85 and 86.

  It reaches master with them.
- **One way of deciding turns.** Planning decides by the same code the turns the playlist
  would decide, only earlier, and the turn that begins takes what the plan kept: its seed
  and the orders drawn for it. With planning off nothing of today's playback changes, and
  the core's tests of seeds and turns pass as they are. New tests cover planning on.
- **The emulator's own core draws the mirror.** One entry of the core's library, which the
  emulator calls and no command reaches, as the seek's moves are, plays a given file from a
  given point of its turn. It plays the file with a given seed and brightness, and the
  board's state: on or off, the rotation, a test, the miniature output. It plays in place
  of the core's own playlist, writing nothing to storage. The board never calls it. There
  is no second renderer, and no emulator-only command.
- **The emulator's dependencies.** It stays on Python's standard library and the
  repository's packages. The serial link uses the command tool's port code, `termios` and
  `odrigctl/winserial.py`, on macOS, Linux and Windows alike.
- **The app.** The app's files, `app/www/`, and the APK do not change, and the app's suite
  runs unchanged.
- **The firmware.** The `#plan` line goes to either socket that asked for it. The chip's own
  socket, which today carries replies only, carries `#plan` lines when asked. Neither the
  log's queue nor the push holds back a reply, a refresh or the other.
- **The commands.** The six forms, approved by the owner on 2026-11-10, go to every route,
  to `docs/commands.md`, and to the command lists of the suites. Over HTTP the push is
  `unsupported`.
- **Decisions.** `docs/decisions.md` changes in four places, each approved by the owner:
  - "Commands" names the plan and its push.
  - "Emulator" names the mirror and its man in the middle.
  - "Animation formats" says that a widget's seed is drawn when it is planned, while
    planning is on.
  - The change log records the approval.
- **Tests.**
  - **The core:** the planned turns are the turns that play, with planning on and off;
    versions and `since`; seeds drawn when placed; a break's pause and resume; a reply
    within 1,024 bytes; the memory table.
  - **The firmware's host tests:** the push's place for each way.
  - **The emulator,** with an emulator mirrored by another over its line port and over
    HTTP:
    - the frames agree within two refreshes;
    - a late join;
    - a missing file fetched and kept;
    - changes made by a client of either;
    - a lost link and its return, and a restart;
    - the man in the middle's routing: each reply to its own client, a lost reply over
      HTTP, `#log` and `#plan` lines, the order of lines, and a long `upload end`.
  - **The command tool's `plan`.**
- **Documents.**
  - `docs/commands.md`: the plan's commands and `#plan` lines.
  - `docs/core.md`: planning and its memory.
  - `docs/show.md`: when a seed is drawn.
  - `docs/firmware.md`: the push on both sockets.
  - `docs/emulator.md`: the mirror, and its check list by eye.
  - `docs/decisions.md`.
  - `agent/vocabulary.md`: the plan and the mirror.

## Open Questions

None.

**What the owner decided on 2026-11-10:**

- identities and times, with no pixel and no fingerprint;
- the items ahead, shuffled ones included;
- `plan`, `plan since <version>` and `plan push on|off`, and a plan that can be switched on
  and off;
- a widget's seed drawn when it is placed in the plan;
- the phone a controller only, and the app unchanged, in every way of working;
- the man in the middle, which keeps the plan's lines and passes on everything else;
- the board's USB serial port behind it, as a phone's cable would be.

**What this seed decides:**

- The toggle is `plan on` and `plan off`. Planning is off at every start, so that a board
  with no mirror plays as today. The push is per serial way and is not saved.
- The plan holds 8 turns or 10 minutes ahead, whichever is less.
- The version grows at every change, and a turn that ends is a change.
- The end of a turn is a member of the plan's items. `left` stays the playlist's window.
- A paused turn is two items, the second with its point.
- Over HTTP the mirror polls every 2 seconds, with no WebSocket, and with a push it still
  asks every 10 seconds.
- Missing files are fetched once and kept in `build/mirror/` by their keys. An item
  without a key is dark, with the reason.
- The mirror also shows the LEDs off, the brightness, the rotation, the tests and the
  miniature output. WLED's limiter and seed 45 are not mirrored.
- The links are three options of the emulator, and the serial link is opened as the
  command tool opens a port.
- On a serial link or a line port, lines go one at a time. Over HTTP, each is its own
  request.
- The board's other `#` lines go to the clients of the serial port and the line port.
- The seek bar is hidden. A board of another canvas is refused, with the reason.
- The show folder only gives the mapping and is not written to.
- The emulator's core draws through a library entry, not a command.
- It is built on pull request #63's branch.

## Definition Of Done

1. A requirements/design/tasks specification of the plan, its commands and its push, the
   mirror, the man in the middle and the files.
2. The core plans, versions, answers `plan` and `plan since` and draws a widget's seed when
   it places the turn, and with planning off plays as before. The firmware pushes on both
   sockets, and the emulator's core and transports plan and push alike.
3. The emulator mirrors a board:
   - over a serial port, on either socket, on macOS and on Windows;
   - over HTTP, and over another emulator's line port;
   - with its man in the middle, through which the Controller view and a phone on `--lan`
     work against the board;
   - with its files from the collection, the share or the board.
4. The command tool sends `plan` in its six forms.
5. The suites of the core, the firmware's host tests, the emulator, the command tool and
   the onboarding pass. The app's suite passes unchanged, and `app/www/` is untouched.
6. The documents of the technical constraints.
7. A board session, with the firmware that plans, under the rules "If you have a board".
8. The owner's checks by eye:
   - the emulator beside the wall, over USB and over Wi-Fi;
   - a clock and a message showing the wall's time and words;
   - the LEDs off, and a display test;
   - the phone controlling the board through the emulator, and straight.
