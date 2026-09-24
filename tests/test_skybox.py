import json
from pathlib import Path
import tempfile
import unittest
import skybox

class SkyboxTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.settings = {'enabled_configs': ['Existing'], 'theme': 'dark'}
        (self.home / 'settings.json').write_text(json.dumps(self.settings))

    def test_install_preserves_settings_and_unrelated_files(self):
        folder = self.home / 'configs'
        folder.mkdir()
        other = folder / 'Existing.json'
        other.write_text('{}')
        skybox.install(self.home)
        self.assertEqual(len(skybox.verify(folder)), 6)
        self.assertEqual(json.loads((self.home / 'settings.json').read_text()), self.settings)
        skybox.uninstall(self.home)
        self.assertEqual(other.read_text(), '{}')
        self.assertFalse((folder / skybox.NAME).exists())

    def test_install_refuses_existing_profile(self):
        skybox.install(self.home)
        with self.assertRaises(ValueError):
            skybox.install(self.home)

    def test_modified_texture_blocks_verification_and_removal(self):
        skybox.install(self.home)
        path = self.home / 'configs' / skybox.NAME / 'Up.png'
        path.write_bytes(b'modified')
        with self.assertRaises(ValueError):
            skybox.verify(self.home / 'configs')
        with self.assertRaises(ValueError):
            skybox.uninstall(self.home)
        self.assertEqual(path.read_bytes(), b'modified')

    def test_extra_file_prevents_removal(self):
        skybox.install(self.home)
        extra = self.home / 'configs' / skybox.NAME / 'personal.txt'
        extra.write_text('keep')
        with self.assertRaises(ValueError):
            skybox.uninstall(self.home)
        self.assertTrue(extra.exists())

    def test_installed_check_requires_activation(self):
        skybox.install(self.home)
        with self.assertRaises(ValueError):
            skybox.check_installed(self.home)
        self.settings['enabled_configs'].append(skybox.NAME)
        (self.home / 'settings.json').write_text(json.dumps(self.settings))
        self.assertEqual(len(skybox.check_installed(self.home)), 6)


class ProbeTests(unittest.TestCase):
    setUp = SkyboxTests.setUp
    def activate(self):
        skybox.install(self.home)
        self.settings['enabled_configs'].append(skybox.NAME)
        (self.home / 'settings.json').write_text(json.dumps(self.settings))

    def fake_opener(self, corrupted=False):
        from io import BytesIO
        class Opener:
            def open(inner, req, timeout):
                if req.data:
                    body = json.loads(req.data)
                    inner.face = body[0]['requestId']
                    return BytesIO(json.dumps([{'locations': [
                        {'location': 'https://test.rbxcdn.com/texture'}]}]).encode())
                return BytesIO(b'wrong' if corrupted else skybox.texture(inner.face))
        return Opener()

    def test_proxy_probe_accepts_exact_bytes(self):
        from unittest.mock import patch
        self.activate()
        with patch('skybox.ssl.create_default_context'), patch(
                'skybox.urllib.request.build_opener', return_value=self.fake_opener()):
            self.assertEqual(len(skybox.probe(self.home, Path('test.pem'), 58443)), 6)

    def test_proxy_probe_rejects_unreplaced_bytes(self):
        from unittest.mock import patch
        self.activate()
        with patch('skybox.ssl.create_default_context'), patch(
                'skybox.urllib.request.build_opener', return_value=self.fake_opener(True)):
            with self.assertRaises(ValueError):
                skybox.probe(self.home, Path('test.pem'), 58443)

if __name__ == '__main__':
    unittest.main()
