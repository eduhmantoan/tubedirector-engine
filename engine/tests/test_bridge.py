import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

MODULE = Path(__file__).resolve().parents[1] / 'src-tauri/resources/bridge.py'

class EngineContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        import os
        cls.env = patch.dict(os.environ, {'HOME':cls.temp.name, 'TD_TTS_PIPER_ONLY':'1', 'TD_TTS_SITE_ORIGIN':'https://tubedirector.com.br', 'TD_TTS_PORT':'8765'})
        cls.env.start()
        spec = importlib.util.spec_from_file_location('td_bridge', MODULE)
        cls.bridge = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.bridge)

    @classmethod
    def tearDownClass(cls):
        cls.env.stop()
        cls.temp.cleanup()

    def test_site_origin(self):
        self.assertIn('https://tubedirector.com.br', self.bridge.ALLOWED_ORIGINS)
        self.assertNotIn('https://evil.example', self.bridge.ALLOWED_ORIGINS)

    def test_server_only_on_loopback(self):
        self.assertEqual(self.bridge.HOST, '127.0.0.1')
        self.assertEqual(self.bridge.PORT, 8765)

    def test_token_strength(self):
        self.assertGreaterEqual(len(self.bridge.TOKEN), 30)

    def test_windows_voices_are_piper(self):
        self.assertEqual(self.bridge.SUPPORTED_LANGUAGES, ('Portuguese',))
        self.assertIn('piper_cadu', self.bridge.PIPER_VOICES)

    def test_filename_blocks_traversal(self):
        for bad in ('../secret', 'foo/bar', 'abc\\def', '  '):
            with self.assertRaises(ValueError): self.bridge.safe_audio_filename(bad)
        self.assertEqual(self.bridge.safe_audio_filename('Mau Hóspede'), 'Mau Hóspede.wav')

    def test_split_text(self):
        original='Olá! '+('Este é um teste de narração. '*60)
        parts=self.bridge.split_text(original)
        self.assertTrue(len(parts)>1)
        self.assertTrue(all(len(p)<=380 for p in parts))

if __name__=='__main__': unittest.main()
