"""Capture the retained HTML and delivered widgets at fixed times for visual review."""
import base64
import json
import pathlib
import subprocess
import sys

from PIL import Image, ImageDraw
from tests.app import support

ROOT = pathlib.Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'project-seeds/59-p2-message-clock-widgets-and-clocks-only-mode'


def capture(out):
    out.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((SOURCE / 'source/manifest.json').read_text(encoding='utf-8'))
    groups = []
    for item in manifest['files']:
        at, times = 0, []
        for caption in item['captions']:
            times.append(at + 700)
            if caption['flags'] & 4:
                times.extend([at + 3400, at + 3600, at + 5000])
            at += caption['duration']
        groups.append(dict(tab=item['tab'], seed=12345, times=sorted(set(times))))
    html = (SOURCE / 'references/led_grid_simulator_v7_tabs_v4_no_blink.html').read_text(encoding='utf-8')
    seen = support.run('message-source', settings=dict(groups=groups, html=html)).seen
    reference = out / 'reference.json'
    reference.write_text(json.dumps(seen, ensure_ascii=False) + '\n', encoding='utf-8', newline='\n')
    result = subprocess.run(['node', str(SOURCE / 'source/render-portable.mjs'), str(reference)],
                            cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    combined = json.loads(result.stdout)
    (out / 'comparison.json').write_bytes(result.stdout + b'\n')
    for tab in range(1, 8):
        samples = [s for s in combined['samples'] if s['tab'] == tab]
        sheet = Image.new('RGB', (640, len(samples) * 285), '#171a20')
        draw = ImageDraw.Draw(sheet)
        for row, sample in enumerate(samples):
            y = row * 285
            draw.text((8, y + 3), f"tab {tab}, seed {sample['seed']}, {sample['t']} ms; reference / portable", fill='white')
            for column, key in enumerate(('rgb', 'portable')):
                pic = Image.frombytes('RGB', (60, 60), base64.b64decode(sample[key]))
                sheet.paste(pic.resize((240, 240), Image.Resampling.NEAREST), (20 + column * 320, y + 30))
        sheet.save(out / f'tab-{tab}.png')
    return combined


if __name__ == '__main__':
    result = capture(pathlib.Path(sys.argv[1]))
    print(f"Captured {len(result['samples'])} source/portable pairs across all seven sequences")
