"""Record a complete scan in the actual emulator and compare its LED bytes."""

import argparse
import base64
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from emulator import binding, host, recfile
from odrig import mapping


def verify(show, output):
    if output.exists():
        raise ValueError("proof output directory already exists")
    canvas = mapping.read(show / "mapping.json")
    assert (canvas.width, canvas.height) == (60, 60)
    show_data = json.loads((show / "show.json").read_text(encoding="utf-8"))
    brightness = show_data["brightness"]
    assert brightness == 40
    assert show_data["items"] == [{"id": 1, "file": "space-scan.odrg", "repeat": 1}]
    source = Path(__file__).with_name("expected.mjs")
    decoded = subprocess.run(["node", str(source), str(show / "space-scan.odrg")],
                             capture_output=True, encoding="utf-8", check=True, timeout=180,
                             creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)
    expected = json.loads(decoded.stdout)
    output.mkdir()
    table = bytes((value * brightness + 127) // 255 for value in range(256))
    order = []
    for leg in canvas.legs:
        for led in range(1, canvas.led_count(leg) + 1):
            x, y = mapping.position(canvas, leg, led)
            order.extend(((y - 1) * 60 + x - 1) * 3 + c for c in range(3))

    def leds(sample):
        rgb = base64.b64decode(sample["rgb"]).translate(table)
        return bytes(rgb[index] for index in order)

    samples = {sample["ms"]: leds(sample) for sample in expected["samples"]}
    samples[expected["loopMs"]] = samples[0]
    samples[expected["loopMs"] + 40] = samples[40]
    files = host.FolderHost(show, storage=67108864)
    start = time.monotonic()
    statuses = []
    matched = []
    produced_count = 0
    try:
        core = binding.Core(ROOT / "core" / "build" / binding.LIBRARY_NAME, files)
        for now in range(0, 6000000, 20):
            core.poll(now)
            if now % 1000 == 0:
                status = json.loads(core.command(now, b"status"))
                assert status["error"] is None and status["unavailable"] == 0, status
                if status["readiness"] == "ready":
                    statuses.append({"ms": now, "status": status})
                    break
        else:
            raise AssertionError("startup check did not finish within its virtual-time bound")
        origin = now + 20
        assert json.loads(core.command(origin, b"play 1"))["ok"] is True

        def ticks():
            nonlocal produced_count
            for offset in range(0, expected["loopMs"] + 80, 20):
                instant = origin + offset
                produced = core.poll(instant)
                frame = core.frame() if produced else b""
                produced_count += int(produced)
                if offset in samples:
                    assert produced, f"no refresh at {offset}ms"
                    assert frame == samples[offset], f"LED bytes differ at {offset}ms"
                    matched.append(offset)
                if offset % 60000 == 0 or offset == expected["loopMs"]:
                    status = json.loads(core.command(instant, b"status"))
                    assert status["error"] is None and status["unavailable"] == 0, status
                    statuses.append({"ms": instant, "status": status})
                    print(f"verified virtual {offset}/{expected['loopMs']}ms", flush=True)
                yield instant, produced, frame

        recfile.write(output / "loop.odrr", core.legs, ticks())
    finally:
        files.release()
    assert matched == sorted(samples)
    assert produced_count == (expected["loopMs"] + 80) // 20
    digest = hashlib.sha256()
    with (output / "loop.odrr").open("rb") as recorded:
        for chunk in iter(lambda: recorded.read(65536), b""):
            digest.update(chunk)
    recording_sha = digest.hexdigest()
    proof = {"animationSha256": expected["sha256"], "loopMs": expected["loopMs"],
             "frames": expected["frames"], "playOriginMs": origin, "matchedSampleTimesMs": matched,
             "producedRefreshes": produced_count, "recordSha256": recording_sha,
             "recordBytes": (output / "loop.odrr").stat().st_size, "statuses": statuses,
             "wallSeconds": round(time.monotonic() - start, 3), "physicalAcceptance": "unperformed"}
    (output / "proof.json").write_text(json.dumps(proof, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({key: value for key, value in proof.items() if key != "statuses"}, indent=2))
    return proof


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("show", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    verify(args.show.resolve(), args.output.resolve())
