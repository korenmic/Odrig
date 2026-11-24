import json
import time
import unittest

from emulator import binding, host
from . import support
from .only_assets import installed_only


class DelayedFiles(host.FolderHost):
    reads = 0
    delayed = 0

    def read_at(self, name, offset, capacity):
        if name.startswith('drive/'):
            self.reads += 1
            if self.reads % 64 == 0:
                self.delayed += 1
                time.sleep(.001)
        return super().read_at(name, offset, capacity)


class SustainedOnly(unittest.TestCase):
    def run_program(self, messages):
        folder, card, allowed = installed_only(self, messages)
        before = {path.relative_to(card).as_posix(): path.read_bytes() for path in card.rglob('*') if path.is_file()}
        files = DelayedFiles(folder, drive=host.Drive(card, writable=False))
        self.addCleanup(files.release)
        core = binding.Core(support.LIBRARY, files)
        now = 0
        polls = 0
        frames = 0
        lit = 0
        statuses = 0
        fragments = 0
        seen = set()
        longest_command = 0
        while now <= 300000:
            if core.poll(now):
                frames += 1
                lit += any(core.frame())
            if polls % 29 == 0:
                started = time.monotonic()
                status = json.loads(core.command(now, b'status'))
                longest_command = max(longest_command, time.monotonic() - started)
                self.assertEqual(status['clock_mode'], 'only')
                self.assertIsNone(status['error'])
                if status.get('file') is not None:
                    self.assertIn(status['file'], allowed)
                    seen.add(status['file'])
                statuses += 1
            if polls % 97 == 0:
                self.assertEqual(core.feed(now, b'sta'), [])
                core.poll(now + 1)
                answers = core.feed(now + 2, b'tus\n')
                self.assertEqual(len(answers), 1)
                line, reply, cut = answers[0]
                self.assertEqual((line, cut), (b'status', False))
                self.assertEqual(json.loads(reply)['clock_mode'], 'only')
                fragments += 1
            polls += 1
            now += 234 if polls % 80 == 0 else 33
        self.assertGreater(frames, 1000)
        self.assertGreater(lit, 100)
        self.assertGreater(statuses, 200)
        self.assertGreater(fragments, 50)
        self.assertGreater(files.delayed, 0)
        self.assertLess(longest_command, 1)
        self.assertIsNone(core.error())
        self.assertIn('clocks/face.odrgx', seen)
        if messages:
            self.assertGreaterEqual(len([name for name in seen if name.startswith('clocks/message/')]), 2)
        else:
            self.assertEqual(seen, {'clocks/face.odrgx'})
        self.assertEqual({path.relative_to(card).as_posix(): path.read_bytes() for path in card.rglob('*') if path.is_file()}, before)

    def test_five_accelerated_minutes_with_late_polls_and_delayed_clock_reads(self):
        self.run_program(False)

    def test_five_accelerated_minutes_with_shipped_messages_and_fragmented_commands(self):
        self.run_program(True)


class LiveOnlyTransports(unittest.TestCase):
    def test_http_and_tcp_continue_answering_during_only_playback(self):
        folder, card, allowed = installed_only(self)
        emulator = support.entered(self, support.Emulator(folder, '--drive', card, tcp_port=0))
        deadline = time.monotonic() + 10
        while True:
            status = emulator.status()
            if status.get('file') in allowed:
                break
            self.assertLess(time.monotonic(), deadline, status)
            time.sleep(.02)
        with support.Lines(emulator.tcp) as line:
            for _ in range(30):
                started = time.monotonic()
                http = emulator.status()
                tcp = json.loads(line.ask('status'))
                self.assertLess(time.monotonic() - started, 2)
                for reply in (http, tcp):
                    self.assertEqual(reply['clock_mode'], 'only')
                    self.assertIsNone(reply['error'])
                    self.assertIn(reply['file'], allowed)
                time.sleep(.1)
