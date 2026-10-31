import hashlib
import json
import pathlib
import subprocess
import tempfile
import unittest
from unittest import mock

from fwtool import provenance


class SourceIdentity(unittest.TestCase):
    def test_revision_and_tracked_dirty_state_are_recorded_without_untracked_files(self):
        replies=[subprocess.CompletedProcess([],0,'c'*40+'\n',''),
                 subprocess.CompletedProcess([],0,' M core/player.cpp\n','')]
        with mock.patch.object(provenance.process,'run',side_effect=replies) as run:
            self.assertEqual(provenance.git_identity(pathlib.Path('source with spaces')),
                             dict(commit='c'*40,trackedDirty=True))
        self.assertEqual(run.call_args.args[0][-3:],['status','--porcelain','--untracked-files=no'])

    def test_input_identity_changes_with_current_sources_but_excludes_builds_and_operator_secrets(self):
        with tempfile.TemporaryDirectory(prefix='odrig-fw-inputs-') as directory:
            root=pathlib.Path(directory)
            core=root/'core';core.mkdir()
            source=core/'player.cpp';source.write_bytes(b'int current=1;\n')
            first=provenance.source_inputs(root)
            (core/'build').mkdir();(core/'build'/'toolchain.json').write_bytes(b'host-specific')
            (root/'firmware').mkdir();(root/'firmware'/'wifi.json').write_bytes(b'private operator settings')
            self.assertEqual(first,provenance.source_inputs(root))
            source.write_bytes(b'int current=2;\n')
            second=provenance.source_inputs(root)
            self.assertNotEqual(first['sha256'],second['sha256'])
            self.assertEqual(list(second['files']),['core/player.cpp'])

    def test_record_identifies_source_host_toolchain_and_exact_image_bytes(self):
        with tempfile.TemporaryDirectory(prefix='odrig-fw-record-') as directory:
            root=pathlib.Path(directory)
            image=root/'firmware.bin';image.write_bytes(b'compiled image')
            package=root/'pio'/'packages'/'compiler';package.mkdir(parents=True)
            (package/'package.json').write_text(json.dumps(dict(name='compiler',version='14.2.0')),encoding='utf-8',newline='\n')
            with mock.patch.object(provenance,'git_identity',return_value=dict(commit='a'*40,trackedDirty=False)), \
                 mock.patch.object(provenance,'versions',return_value=dict(platformio='6.2.0',node='20.18.0')):
                record=provenance.record('firmware','odrig_microsd',image,True,root,pio_root=root/'pio')
            self.assertEqual(record['image'],dict(file='firmware.bin',bytes=14,sha256=hashlib.sha256(b'compiled image').hexdigest()))
            self.assertEqual(record['source'],dict(commit='a'*40,trackedDirty=False))
            self.assertEqual(record['environment'],'odrig_microsd')
            self.assertEqual(record['packages'][0]['version'],'14.2.0')
            self.assertIn('architecture',record['host'])
            self.assertIn('timestamps',record['comparison'])

    def test_provenance_is_published_as_utf8_lf_without_a_partial_file(self):
        with tempfile.TemporaryDirectory(prefix='odrig-fw-publication-') as directory:
            image=pathlib.Path(directory,'image.bin');image.write_bytes(b'image')
            record=dict(source=dict(commit='b'*40),note='caf\u00e9')
            with mock.patch.object(provenance,'record',return_value=record):
                target=provenance.write('firmware','odrig_microsd',image,True)
            data=target.read_bytes()
            self.assertNotIn(b'\r',data)
            self.assertEqual(json.loads(data),record)
            self.assertFalse(target.with_name(target.name+'.part').exists())
