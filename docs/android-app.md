# Android app: first notes

A starting point for the operators' app. Nothing here is decided except where it says so.

## What the app is for

Operators at the event control the installation from a phone: choose what plays, switch the
LEDs on and off, change brightness, and see what the board is doing.

## What is already settled

- **The board hosts the Wi-Fi network and the phone joins it.** See [wifi.md](wifi.md).
- **The app sends the same commands as every other client**, over HTTP: `POST /odrig` with
  the command line as the body, and a one-line JSON reply. See [commands.md](commands.md).
- **The emulator accepts the same HTTP commands**, so the app can be developed and tested
  against the emulator before it ever meets the board.

## What the app needs that does not exist yet

- **Names for what can be played.** The command `list` gives every item with its id and its
  file name; see [commands.md](commands.md). A name to show an operator does not exist:
  `show.json` has none.
- **The emulator reachable from a phone.** It listens only on the Mac itself. Testing the app
  on a real phone needs an option to listen on the local network.

Each of these becomes a seed when app work starts. They are not built now, because nothing
uses them yet.

## Ways to build it

| Option | For | Against |
|---|---|---|
| A web page served by the board | No installation, works on any phone, one code base, and the emulator can serve the same page | Needs the browser to stay on the board's address; no presence on the home screen unless added by hand |
| That web page wrapped in an Android app | An icon and an APK, with almost no extra code | Still a web page inside; two things to ship |
| A native Android app (Kotlin) | Best control over the phone's Wi-Fi behaviour and the best feel | The most work, Android only, and a second user interface to keep in step |
| A cross-platform app (Flutter or similar) | Android and iPhone from one code base | A large toolchain for a small app |

The web page is the cheapest way to get operators a working control surface, and wrapping it
later costs little. A native app earns its cost only if the web page cannot hold the
connection reliably.

## Things to check early

- **Phones and networks without internet.** A phone that joins a network with no internet
  access may keep sending traffic over mobile data, or may leave the network. The app, or the
  operators' phone settings, must keep requests going to the board. This is the main technical
  risk and should be tried on a real phone against the real board before choosing how to build.
- **Joining the network.** Whether the operator joins the board's network by hand in the
  phone's settings, or the app asks Android to join it.
- **Several operators at once.** What happens when two phones send commands. The board simply
  obeys the last command, and each phone learns the state by asking for status.

## Questions for the owner

1. Is a web page served by the board acceptable as the first version, or must it be an APK
   from the start?
2. Android only, or iPhones too?
3. What should operators be able to do beyond play, on, off and brightness?
4. Should the network have a password that only operators know?
