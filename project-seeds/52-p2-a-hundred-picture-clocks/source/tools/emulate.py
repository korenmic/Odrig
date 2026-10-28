"""Plays the 112 animations of seed 52 in the emulator, and records two picture clocks.

    python emulate.py drive WORKTREE FILES_DIR WORK_DIR
        Starts the emulator of the worktree on an empty show of the 60 x 60 mapping, with a
        drive whose folder `odrig` holds the files, on free ports; lists the drive's
        animations over HTTP, plays each with `play <id>` and asks `status`. Prints one line
        for each and a summary; the emulator is stopped at the end.

    python emulate.py record WORKTREE DIAL DISPLAY WORK_DIR
        Installs a show of the two files on the 60 x 60 mapping and records 16 seconds in
        record mode: each played twice, each turn begun by `play`; prints the seed of each
        turn and how many LEDs change between the refreshes a second apart.
"""

import json
import pathlib
import shutil
import subprocess
import sys
import time
import urllib.request


def post(port, line):
    request = urllib.request.Request(f"http://127.0.0.1:{port}/odrig", data=line.encode(), method="POST")
    with urllib.request.urlopen(request, timeout=10) as answer:
        return json.loads(answer.read().decode())


def empty_show(tree, folder):
    folder.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(tree / "mapping" / "legs-20.json", folder / "mapping.json")
    (folder / "show.json").write_text(json.dumps({"version": 1, "brightness": 255, "items": []}, indent=2) + "\n", encoding="utf-8")


def drive(tree, files, work):
    files, work = files.resolve(), work.resolve()
    if work.exists():
        shutil.rmtree(work)
    show = work / "show"
    empty_show(tree, show)
    odrig = work / "drive" / "odrig"
    odrig.mkdir(parents=True)
    names = sorted(path.name for path in files.iterdir() if path.suffix in (".odrg", ".odrgx"))
    for name in names:
        shutil.copyfile(files / name, odrig / name)
    python = tree / ".venv" / "Scripts" / "python.exe"
    process = subprocess.Popen([str(python), "-m", "emulator", str(show), "--port", "0", "--tcp-port", "0", "--drive", str(work / "drive")],
                               cwd=tree, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
    try:
        port = None
        while port is None:
            line = process.stdout.readline()
            if not line:
                raise SystemExit("the emulator ended before it said its address")
            if line.startswith("page: "):
                port = int(line.strip().rstrip("/").rsplit(":", 1)[1])
        deadline = time.time() + 300
        while True:
            items = []
            start = 0
            while start is not None:
                reply = post(port, f"list {start}" if start else "list")
                if not reply["ok"]:
                    if time.time() > deadline:
                        raise SystemExit(f"list stays refused: {reply}")
                    time.sleep(0.5)
                    start = 0
                    items = []
                    continue
                items += reply["items"]
                start = reply["next"]
            found = {item["file"]: item for item in items if item.get("external")}
            if len(found) >= len(names) or time.time() > deadline:
                break
            time.sleep(1)
        listed = sum(1 for name in names if name in found)
        played = 0
        for name in names:
            item = found.get(name)
            if item is None:
                print(f"{name}: not listed")
                continue
            answer = post(port, f"play {item['id']}")
            time.sleep(0.12)
            status = post(port, "status")
            good = answer["ok"] and status["animation"] == item["id"] and status["error"] is None
            widget = item["type"] == "widget"
            if widget:
                good = good and isinstance(status["seed"], int)
            played += good
            print(f"{name}: id {item['id']} {item['type']} play {answer['ok']} animation {status['animation']} seed {status['seed']} {'plays' if good else 'FAILS'}")
        print(f"{len(names)} files, {listed} listed, {played} played")
    finally:
        process.terminate()
        process.wait(timeout=20)


def record(tree, dial, display, work):
    dial, display, work = dial.resolve(), display.resolve(), work.resolve()
    if work.exists():
        shutil.rmtree(work)
    show = work / "show"
    empty_show(tree, show)
    shutil.copyfile(dial, show / "a.odrgx")
    shutil.copyfile(display, show / "b.odrgx")
    (show / "show.json").write_text(json.dumps({"version": 1, "brightness": 255, "items": [{"id": 1, "file": "a.odrgx"}, {"id": 2, "file": "b.odrgx"}]}) + "\n",
                                    encoding="utf-8")
    script = work / "script.txt"
    starts = [0, 4000, 8000, 12000]
    lines = []
    for start, number in zip(starts, [1, 1, 2, 2]):
        lines += [f"{start} play {number}", f"{start + 20} status"]
    script.write_text("\n".join(lines) + "\n", encoding="utf-8")
    out = work / "turns.odrr"
    python = tree / ".venv" / "Scripts" / "python.exe"
    done = subprocess.run([str(python), "-m", "emulator", str(show), "--record", str(out), "--seconds", "16", "--script", str(script)],
                          cwd=tree, capture_output=True, text=True, timeout=600)
    if done.returncode != 0:
        raise SystemExit(done.stdout + done.stderr)
    replies = [json.loads(line.split(" ", 2)[2]) for line in done.stdout.splitlines() if line.startswith("reply ")]
    seeds = [reply["seed"] for reply in replies if "seed" in reply]
    sys.path.insert(0, str(tree))
    from emulator import recfile
    recording = recfile.read(out)
    by_time = {tick.ms: tick for tick in recording.ticks}

    def data(at):
        return by_time[at].data

    for (start, number), seed in zip(zip(starts, [1, 1, 2, 2]), seeds):
        frames = [bytes(data(start + 40 + 1000 * second)) for second in range(4) if start + 40 + 1000 * second in by_time]
        changes = [sum(1 for led in range(0, len(a), 3) if a[led:led + 3] != b[led:led + 3]) for a, b in zip(frames, frames[1:])]
        print(json.dumps({"turn_start_ms": start, "item": number, "seed": seed, "leds_changed_each_second": changes}))
    return seeds


if __name__ == "__main__":
    command = sys.argv[1]
    if command == "drive":
        drive(pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3]), pathlib.Path(sys.argv[4]))
    else:
        record(pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3]), pathlib.Path(sys.argv[4]), pathlib.Path(sys.argv[5]))
