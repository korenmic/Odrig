import unittest
import zlib

from odrig import mapping
from . import support
from .test_mini import ENABLE, files_for, frame, projected, replies
from .test_clocks import clock_of
from .test_texts import text_of
from .test_pictures import picture_of
from .test_message_clock import message_file


def revision(degrees):
    return zlib.crc32(bytes([degrees // 90]))


def turn(degrees, before=0):
    return support.line(0, f'rotation set {revision(before)} {degrees}')


def rotated(pixels, degrees):
    result = pixels
    for _ in range(degrees // 90):
        result = [list(row) for row in zip(*result)][::-1]
    return result


def picture(run, files):
    canvas = mapping.loads(files['mapping.json'].encode('utf-8'))
    latest = {int(line.split()[1]): bytes.fromhex(line.split()[2])
              for line in run.lines if line.startswith('data ')}
    pixels = [[(0, 0, 0)] * canvas.width for _ in range(canvas.height)]
    for leg in canvas.legs:
        data = latest[leg.leg]
        for n, at in enumerate(support.led_pixels(canvas, leg)):
            pixels[at // canvas.width][at % canvas.width] = tuple(data[3 * n:3 * n + 3])
    return pixels


class Rotation(unittest.TestCase):
    def test_fresh_production_bootstrap_accepts_an_upload_and_all_rotations(self):
        from tests.firmware.test_fresh_board import initialize
        from .test_upload import Script

        fresh = initialize()['files']
        payload = files_for()['picture.odrg']
        with support.installed(fresh) as folder:
            initial = support.session(folder, [support.line(0, 'status'), support.line(0, 'rotation')])
            self.assertIsNone(initial.error)
            self.assertTrue(replies(initial)[-1]['supported'])
            uploaded = support.session(folder, Script().upload(1, 'probe.odrg', payload).lines)
            self.assertTrue(all(value['ok'] for value in replies(uploaded)))
            self.assertEqual(support.folder_files(folder)['probe.odrg'], payload)
            files = {'mapping.json': fresh['mapping.json'].decode('utf-8')}
            baseline = picture(support.session(folder, ['poll 0']), files)
            before = 0
            for degrees in (90, 180, 270, 0):
                result = support.session(folder, [turn(degrees, before), 'poll 0'])
                self.assertEqual(picture(result, files), rotated(baseline, degrees))
                again = replies(support.session(folder, [support.line(0, 'rotation')]))[0]
                self.assertEqual(again['degrees'], degrees)
                before = degrees

    def test_rotation_configuration_is_independent_of_missing_or_invalid_content(self):
        square = files_for()
        cases = {
            'missing mapping and show': {},
            'missing show': {'mapping.json': square['mapping.json']},
            'missing mapping': {'show.json': square['show.json']},
            'malformed mapping': {'mapping.json': b'broken', 'show.json': square['show.json']},
            'malformed show': {'mapping.json': square['mapping.json'], 'show.json': b'broken'},
            'unavailable animation': {name: value for name, value in square.items() if name != 'picture.odrg'},
            'empty show': {'mapping.json': square['mapping.json'],
                           'show.json': b'{"version":1,"brightness":32,"items":[]}'},
        }
        for label, files in cases.items():
            with self.subTest(label=label), support.installed(files) as folder:
                before = 0
                for degrees in (90, 180, 270, 0):
                    initial = replies(support.session(folder, [support.line(0, 'rotation')]))[0]
                    self.assertTrue(initial['supported'])
                    self.assertEqual(initial['degrees'], before)
                    changed = replies(support.session(folder, [turn(degrees, before)]))[0]
                    self.assertEqual(changed, dict(ok=True, supported=True, degrees=degrees,
                                                   revision=revision(degrees), error=None))
                    self.assertEqual(support.folder_files(folder)['rotation.txt'], f'1 {degrees}\n'.encode())
                    before = degrees

    def test_missing_installation_still_reports_real_storage_failure(self):
        result = support.start({}, [turn(90)], ['--no-storage'])
        self.assertEqual(replies(result)[0], dict(ok=False, error='storage-error'))

    def test_inventory_validation_does_not_block_rotation_configuration(self):
        with support.installed(files_for()) as folder:
            result = support.session(folder, [turn(90)], check_first=False)
            self.assertEqual(replies(result)[0]['degrees'], 90)

    def test_default_and_all_persistent_confirmed_values(self):
        with support.installed(files_for()) as folder:
            initial = replies(support.session(folder, [support.line(0, 'rotation')]))[0]
            self.assertEqual(initial, dict(ok=True, supported=True, degrees=0,
                                           revision=revision(0), error=None))
            before = 0
            for degrees in (90, 180, 270, 0):
                values = replies(support.session(folder, [turn(degrees, before)]))
                self.assertEqual(values[0]['degrees'], degrees)
                self.assertEqual(values[0]['revision'], revision(degrees))
                self.assertEqual(support.folder_files(folder)['rotation.txt'], f'1 {degrees}\n'.encode())
                again = replies(support.session(folder, [support.line(0, 'rotation')]))[0]
                self.assertEqual(again['degrees'], degrees)
                before = degrees

    def test_rgb_and_palette_are_exact_coordinate_permutations(self):
        colours = [(240, 10, 30), (5, 200, 60), (20, 40, 230), (30, 80, 150)]
        sources = [None, [[colours[(x // 17 + y // 23) % 4] for x in range(60)] for y in range(60)]]
        for pixels in sources:
            files = files_for(pixels)
            baseline = picture(support.start(files, ['poll 0']), files)
            for angle in (90, 180, 270, 0):
                with self.subTest(palette=pixels is not None, angle=angle):
                    result = support.start(files, [turn(angle), 'poll 0'])
                    self.assertEqual(picture(result, files), rotated(baseline, angle))

    def test_text_clock_message_and_picture_layers_rotate_as_composed(self):
        contents = [text_of(width=60, height=60, effect='static'), message_file(),
                    *(clock_of(widget, canvas=(60, 60)) for widget in (1, 2, 3)),
                    *(picture_of(widget, canvas=(60, 60)) for widget in ('picture-dial', 'picture-display'))]
        for content in contents:
            files = files_for()
            files['picture.odrg'] = content
            baseline = picture(support.start(files, ['poll 0', 'poll 1200']), files)
            for angle in (90, 180, 270):
                with self.subTest(angle=angle, kind=content[:16]):
                    result = support.start(files, [turn(angle), 'poll 0', 'poll 1200'])
                    self.assertEqual(picture(result, files), rotated(baseline, angle))

    def test_miniature_averages_rotated_samples_without_rotating_physical_chain(self):
        files = files_for()
        baseline = picture(support.start(files, ['poll 0']), files)
        for angle in (0, 90, 180, 270):
            result = support.start(files, [turn(angle), *ENABLE, 'poll 0', 'mini frame'])
            expected = projected(rotated(baseline, angle))
            self.assertEqual(frame(result), expected)
            self.assertEqual(frame(result, 'chain'), bytes(expected[3 * (y * 10 + x) + c]
                             for x in range(10) for y in range(6) for c in range(3)))

    def test_stale_or_invalid_changes_do_not_write(self):
        bad = ['rotation extra', 'rotation set', 'rotation set 0 90',
               f'rotation set {revision(0)} 45', f'rotation set {revision(0)} -90',
               f'rotation set {revision(0)} 360', f'rotation set {revision(0)} 90 extra']
        result, kept = support.start_and_keep(files_for(), [support.line(0, line) for line in bad])
        self.assertTrue(all(not value['ok'] for value in replies(result)))
        self.assertNotIn('rotation.txt', kept)
        self.assertEqual(replies(result)[2]['error'], 'rotation-conflict')

    def test_noop_and_frames_do_not_write_rotation(self):
        result = support.start(files_for(), [turn(0), *[f'poll {n}' for n in range(0, 400, 20)]],
                               ['--trace-store', '--trace-read-at'])
        self.assertTrue(replies(result)[0]['ok'])
        self.assertFalse(any(line.startswith('store ') and 'rotation.' in line for line in result.lines))
        self.assertFalse(any(line.startswith('read_at rotation.') for line in result.lines))

    def test_bad_saved_data_reports_error_and_deliberate_zero_repairs_it(self):
        for saved in (b'', b'1 90', b'2 90\n', b'1 360\n', b'1 90\nextra'):
            with self.subTest(saved=saved):
                source = {**files_for(), 'rotation.txt': saved}
                result, kept = support.start_and_keep(source, [support.line(0, 'rotation'), turn(0)])
                values = replies(result)
                self.assertEqual((values[0]['degrees'], values[0]['error']), (0, 'unreadable'))
                self.assertIsNone(values[1]['error'])
                self.assertEqual(kept['rotation.txt'], b'1 0\n')

    def test_each_failed_save_retains_live_value_and_old_file(self):
        source = {**files_for(), 'rotation.txt': b'1 90\n'}
        script = [turn(180, 90), support.line(0, 'rotation')]
        baseline, _ = support.start_and_keep(source, script, ['--trace-store'])
        calls = sum(line.startswith('store ') for line in baseline.lines)
        self.assertGreaterEqual(calls, 4)
        for at in range(len(baseline.stored) + 1, len(baseline.stored) + calls + 1):
            with self.subTest(at=at):
                result, kept = support.start_and_keep(source, script, ['--store-fails-at', str(at)])
                self.assertEqual(replies(result)[0], dict(ok=False, error='storage-error'))
                self.assertEqual(replies(result)[-1]['degrees'], 90)
                self.assertEqual(kept['rotation.txt'], b'1 90\n')

    def test_physical_diagnostics_bypass_rotation_and_refuse_changes(self):
        script = [support.line(0, 'mapping test on'), 'poll 0', turn(180, 90)]
        normal = support.start(files_for(), script[:2])
        source = {**files_for(), 'rotation.txt': b'1 90\n'}
        turned = support.start(source, script)
        self.assertEqual(picture(normal, files_for()), picture(turned, source))
        self.assertEqual(replies(turned)[-1], dict(ok=False, error='in-use'))

    def test_legacy_rectangular_playback_is_unsupported_without_a_fit_choice(self):
        result = support.start(support.example_show(), [support.line(0, 'rotation'), turn(90), 'poll 0'])
        self.assertFalse(replies(result)[0]['supported'])
        self.assertEqual(replies(result)[1], dict(ok=False, error='unsupported'))

    def test_saved_read_failure_is_reported_without_invalidating_the_show(self):
        source = {**files_for(), 'rotation.txt': b'1 90\n'}
        result = support.start(source, [support.line(0, 'rotation'), 'poll 0'],
                               ['--read-fails', 'rotation.txt', '0'])
        state = replies(result)[0]
        self.assertEqual((state['degrees'], state['error']), (0, 'unreadable'))
        self.assertTrue(any(c for row in picture(result, source) for pixel in row for c in pixel))

    def test_read_only_storage_and_active_upload_do_not_publish_a_change(self):
        result = support.start(files_for(), [turn(90)], ['--no-storage'])
        self.assertEqual(replies(result)[0], dict(ok=False, error='storage-error'))
        result = support.start(files_for(), [support.line(0, 'upload begin 1 picture.odrg 100'),
                                            turn(90), support.line(0, 'rotation')])
        self.assertEqual(replies(result)[1], dict(ok=False, error='busy'))
        self.assertEqual(replies(result)[2]['degrees'], 0)
