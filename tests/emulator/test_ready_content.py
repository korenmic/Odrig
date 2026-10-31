"""The actual emulator host accepts a large encoded movie without changing its bytes."""
import base64
import gc
import hashlib
import json
import pathlib
import shutil
import tempfile
import unittest
import zlib

from odrig import catalog
from emulator.binding import Core, LIBRARY_NAME
from emulator.host import Drive, FolderHost

ROOT = pathlib.Path(__file__).resolve().parents[2]
SPACE_SCAN = ROOT/'collection/card/space/space-scan-10x.odrg'
SPACE_SHA = 'a93e82f12cbea0f5937ac74d761dcd5f2fc3c4590129496a1b8b9e126d297f19'


def verify_ready_content(progress=None):
    data = SPACE_SCAN.read_bytes()
    source_sha = hashlib.sha256(data).hexdigest()
    proof = {'sourceBytes': len(data), 'sourceSha256': source_sha,
             'clock': 'deterministic20ms ticks through the actual emulator Core/FolderHost',
             'checks': [], 'commands': 0, 'polls': 0}

    def expect(condition, label):
        if not condition:
            raise AssertionError(label)
        proof['checks'].append(label)

    expect(len(data) == 34410601 and source_sha == SPACE_SHA, 'actual space-scan source identity')
    with tempfile.TemporaryDirectory(prefix='odrig-ready-') as temporary:
        top = pathlib.Path(temporary)
        show = top/'show'
        show.mkdir()
        shutil.copyfile(ROOT/'mapping/legs-20.json', show/'mapping.json')
        (show/'show.json').write_text(json.dumps({'version': 1, 'brightness': 40, 'items': []}), encoding='utf-8', newline='\n')
        originals = {name: (show/name).read_bytes() for name in ('mapping.json', 'show.json')}
        card = top/'card'
        files = card/'odrig'
        (files/'space').mkdir(parents=True)
        widget = (ROOT/'collection/card/clocks/message/v7-consciousness.odrgx').read_bytes()
        (files/'space/anchor.odrgx').write_bytes(widget)
        _, refused = catalog.rebuild(catalog.Storage(files, drive=True), names=['space/anchor.odrgx'], canvas=(60, 60))
        expect(not refused, 'cataloged60x60 fixture')
        clock = [0]
        hosts = []

        def opened():
            drive = Drive(card, clock=lambda: clock[0]/1000)
            host = FolderHost(show, drive=drive)
            hosts.append(host)
            instance = Core(ROOT/'core/build'/LIBRARY_NAME, host)
            expect(instance.error() is None, 'native emulator core starts')
            return instance, host, drive

        core, host, drive = opened()
        arena = sum(len(block) for block in core._blocks)
        allocations = len(core._blocks)
        expect(arena <= 131072, 'fixed native arena stays within131072 bytes')
        proof['arenaBytes'] = arena

        def ask(line):
            proof['commands'] += 1
            return json.loads(core.command(clock[0], line.encode('ascii')))

        def must(line):
            reply = ask(line)
            if not reply.get('ok'):
                raise AssertionError((line[:90], reply))
            return reply

        def ticks(count):
            for _ in range(count):
                clock[0] += 20
                core.poll(clock[0])
                proof['polls'] += 1

        def upload(path, content, final_error=None):
            begun = must(f'upload begin external {path} {len(content)}')
            must('upload expect 00000000')
            chunk = begun['chunk']
            for offset in range(0, len(content), chunk):
                piece = content[offset:offset+chunk]
                encoded = base64.urlsafe_b64encode(piece).rstrip(b'=').decode('ascii')
                reply = must(f'upload data {offset} {encoded}')
                if reply.get('received') != offset+len(piece):
                    raise AssertionError('chunk acknowledgement changed the byte offset')
                if offset//chunk % 20 == 0:
                    ticks(1)
                if progress and offset//chunk % 4096 == 0:
                    progress(f'sent {offset+len(piece)}/{len(content)} bytes to {path}')
            end = f'upload end {zlib.crc32(content):08x}'
            reply = ask(end)
            for step in range(60000):
                if reply.get('error') != 'busy':
                    break
                ticks(1)
                if step % 100 == 0:
                    reply = ask(end)
                if progress and step and step % 4000 == 0:
                    progress(f'checked {step} native refresh slices of {path}')
            else:
                raise AssertionError('managed validation exceeded its bounded proof window')
            if final_error is None:
                expect(reply.get('ok') is True and isinstance(reply.get('id'), int), 'acknowledged managed commit: '+path)
            else:
                expect(reply.get('error') == final_error, 'authoritative refusal: '+final_error)
            return reply

        try:
            ticks(100)
            root = must('list 0')['items']
            folder_id = next(row['id'] for row in root if row.get('playlist') == 'space')
            expect(must('catalog')['external']['state'] == 'ok', 'external index ready')
            reply = ask(f'upload begin 1 oversized.odrg {len(data)} {zlib.crc32(data):08x}')
            expect(reply.get('error') == 'no-space' and not (show/'upload.part').exists(), 'oversized Internal fallback refused before bytes')
            expect(ask('upload begin external gone/new.odrg 100').get('error') == 'unknown-id', 'missing folder never becomes root')
            drive.writable = False
            expect(ask('upload begin external space/new.odrg 100').get('error') == 'read-only', 'detected read-only is no fallback')
            drive.writable = True
            must('upload begin external space/anchor.odrgx 100')
            expect(ask('upload expect 00000000').get('error') == 'stale', 'existing physical destination refuses creation')
            expect((files/'space/anchor.odrgx').read_bytes() == widget, 'collision preserves the original widget')
            must('upload begin external space/cancelled.odrg 100')
            must('upload expect 00000000')
            must('upload data 0 AQ')
            must('upload cancel')
            expect(not (files/'space/cancelled.odrg').exists(), 'cancel never publishes a file')
            upload('space/truncated.odrg', data[:36], 'bad-file')
            expect(not (files/'space/truncated.odrg').exists(), 'bad payload never publishes')
            before = must('catalog')['external']['generation']
            result = upload('space/space-scan-10x.odrg', data)
            item_id = result['id']
            expect(len(core._blocks) == allocations, 'large upload allocates no additional native blocks')
            stored = files/'space/space-scan-10x.odrg'
            stored_sha = hashlib.sha256(stored.read_bytes()).hexdigest()
            expect(stored_sha == source_sha, 'all34410601 stored bytes match SHA256')
            found = catalog.read(catalog.Storage(files, drive=True))
            entry = found.entry('space/space-scan-10x.odrg')
            expect(found.state == 'ok' and found.marker.generation == before+1, 'atomic catalog generation acknowledged')
            expect(entry.bytes == len(data) and entry.crc == zlib.crc32(data) and entry.total_ms == 720160, 'catalog key and complete720160ms loop')
            rows = must(f'list in {folder_id} 0')['items']
            expect(any(row.get('id') == item_id and row.get('file') == 'space/space-scan-10x.odrg' for row in rows), 'indexed entry is in the explored folder')
            read = must(f'read {item_id} 0')['data']
            expect(base64.urlsafe_b64decode(read+'='*(-len(read)%4)) == data[:600], 'wire readback preserves the prefix')
            must(f'play {item_id}')
            ticks(10)
            expect(must('status')['animation'] == item_id and any(core.frame()), 'uploaded animation plays nonblack LED data')
            must(f'brightness {item_id} 17 save')
            must(f'ignore {item_id} 1')
            host.release()
            del core
            gc.collect()
            core, host, drive = opened()
            ticks(100)
            rows = must(f'list in {folder_id} 0')['items']
            expect(any(row.get('id') == item_id and row.get('ignored') for row in rows), 'restart retains physical namespace and ignore flag')
            must(f'play {item_id}')
            ticks(5)
            status = must('status')
            expect(status['brightness'] == 40 and status['dimming']['value'] == 17 and status['dimming']['saved'] == 17,
                   'restart retains per-file brightness without changing the default')
            must(f'brightness {item_id} default')
            must(f'ignore {item_id} 0')
            must(f'remove {item_id}')
            expect(not stored.exists() and (files/'space/anchor.odrgx').read_bytes() == widget, 'removal preserves the unrelated widget')
            widget_result = upload('space/ready-message.odrgx', widget)
            expect((files/'space/ready-message.odrgx').read_bytes() == widget, 'ODRGX widget bytes unchanged')
            must(f"play {widget_result['id']}")
            ticks(5)
            expect(must('status')['animation'] == widget_result['id'], 'ready-made widget is playable')
            must('upload begin external space/interrupted.odrg 100')
            must('upload expect 00000000')
            must('upload data 0 AQ')
            drive.folder = str(top/'absent-card')
            ticks(60)
            expect(ask('upload data 1 AQ').get('error') == 'no-upload', 'removal stops the original transaction')
            drive.folder = str(files)
            ticks(100)
            expect(ask('upload data 1 AQ').get('error') == 'no-upload', 'reinsertion does not resume or retarget data')
            expect(not (files/'space/interrupted.odrg').exists() and not (show/'interrupted.odrg').exists(), 'interrupted upload is absent from both namespaces')
            expect(all((show/name).read_bytes() == content for name, content in originals.items()), 'mapping and show remain byte-identical')
            expect(hashlib.sha256(SPACE_SCAN.read_bytes()).hexdigest() == source_sha, 'reference input remains unchanged')
            proof.update(storedSha256=stored_sha, key=f'{entry.crc:08x}-{entry.bytes}', frames=18004,
                         totalMs=entry.total_ms, itemId=item_id, folderId=folder_id)
        finally:
            for one in hosts:
                one.release()
    return proof


class ReadyContent(unittest.TestCase):
    def test_large_ready_movie_and_widget_use_the_actual_native_emulator_host(self):
        proof = verify_ready_content()
        self.assertGreaterEqual(len(proof['checks']), 25)
        self.assertEqual(proof['sourceSha256'], proof['storedSha256'])
