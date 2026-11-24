import pathlib
import tempfile

from odrig import catalog
from tests.core.test_clock_modes import mode_file
from tests.core.test_clocks import clock_of
from tests.core.test_mini import files_for
from . import support


def installed_only(test, messages=True):
    root = pathlib.Path(support.entered(test, tempfile.TemporaryDirectory()))
    folder = support.installed(root / 'show', {**files_for(), 'clocks.txt': mode_file('only', messages)})
    card = root / 'card'
    drive = card / 'odrig'
    files = {'clocks/face.odrgx': clock_of(canvas=(60, 60))}
    files.update({'clocks/message/' + path.name: path.read_bytes()
                  for path in (support.ROOT / 'collection/card/clocks/message').glob('v7-*.odrgx')})
    test.assertEqual(len(files), 8)
    for name in files:
        (drive / name).parent.mkdir(parents=True, exist_ok=True)
    support.installed(drive, files)
    _, refused = catalog.rebuild(catalog.Storage(drive, drive=True), names=sorted(files), canvas=(60, 60))
    test.assertEqual(refused, [])
    return folder, card, set(files)
