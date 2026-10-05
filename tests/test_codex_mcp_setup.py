"""Focused isolated checks; never reads or modifies the buyer's Codex settings."""
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
import tomllib
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server_routes.codex_setup import setup_payload, install_setup
from server_routes import mcp_bridge_routes as bridge
from flask import Flask


class CodexSetupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.env = patch.dict(os.environ, {'CODEX_HOME': str(self.root / 'codex'), 'SPB_MCP_DIR': str(self.root / 'pairing')})
        self.env.start()
        (self.root / 'mcp' / 'server').mkdir(parents=True)
        (self.root / 'mcp' / 'server' / 'index.js').write_text('// test')
        self.payload = setup_payload(self.root / 'mcp', '59876')

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def test_append_preserves_other_settings_and_is_idempotent(self):
        target = Path(self.payload['configPath'])
        target.parent.mkdir()
        original = b'model = "my-chosen-model"\r\n[mcp_servers.other]\r\ncommand = "other"\r\n'
        target.write_bytes(original)
        self.assertTrue(install_setup(self.payload)['ok'])
        self.assertTrue(target.read_bytes().startswith(original))
        config = tomllib.loads(target.read_text())
        self.assertEqual(config['model'], 'my-chosen-model')
        self.assertEqual(config['mcp_servers']['shokker-paint-booth']['tool_timeout_sec'], 200)
        installed = target.read_bytes()
        self.assertTrue(install_setup(self.payload)['alreadyConfigured'])
        self.assertEqual(target.read_bytes(), installed)
        self.assertEqual(target.with_name('config.toml.spb-backup').read_bytes(), original)

    def test_existing_entry_and_invalid_toml_are_preserved(self):
        target = Path(self.payload['configPath'])
        target.parent.mkdir()
        original = b'[mcp_servers.shokker-paint-booth]\ncommand = "custom"\n'
        target.write_bytes(original)
        self.assertFalse(install_setup(self.payload)['ok'])
        self.assertEqual(target.read_bytes(), original)
        target.write_text('broken = [')
        with self.assertRaises(ValueError):
            install_setup(self.payload)
        self.assertEqual(target.read_text(), 'broken = [')

    def test_reconnect_preserves_first_backup_and_backs_up_latest_settings(self):
        target = Path(self.payload['configPath'])
        target.parent.mkdir()
        first = b'model = "first-model"\n'
        target.write_bytes(first)
        self.assertTrue(install_setup(self.payload)['ok'])
        # Buyer removes only SPB's connection and changes their chosen model.
        latest = b'model = "second-model"\n[mcp_servers.other]\ncommand = "other"\n'
        target.write_bytes(latest)
        self.assertTrue(install_setup(self.payload)['ok'])
        self.assertTrue(target.read_bytes().startswith(latest))
        self.assertEqual(target.with_name('config.toml.spb-backup').read_bytes(), first)
        additional = list(target.parent.glob('config.toml.spb-backup-*'))
        self.assertEqual(len(additional), 1)
        self.assertEqual(additional[0].read_bytes(), latest)
        self.assertTrue(install_setup(self.payload)['alreadyConfigured'])
        self.assertEqual(len(list(target.parent.glob('config.toml.spb-backup-*'))), 1)

    def test_apostrophe_path_and_missing_node(self):
        with patch('server_routes.codex_setup.shutil.which', return_value="C:/Ricky's PC/node.exe"):
            p = setup_payload(self.root / 'mcp', '59877')
            self.assertIn("Ricky''s PC", p['command'])
            cfg = tomllib.loads(p['config'])
            self.assertEqual(cfg['mcp_servers']['shokker-paint-booth']['env']['SPB_PORT'], '59877')
        with patch('server_routes.codex_setup.shutil.which', return_value=None):
            self.assertFalse(install_setup(setup_payload(self.root / 'mcp', '59876'))['ok'])

    def app(self):
        bridge._STATE.update(enabled=False, loaded=True, last_poll=0, calls=0, last_tool=None, last_call=0)
        bridge._QUEUE.clear(); bridge._RESULTS.clear(); bridge._PENDING.clear()
        app = Flask(__name__)
        bridge.register_mcp_bridge_routes(app)
        return app

    def test_origin_token_and_confirmation_guards(self):
        client = self.app().test_client()
        self.assertEqual(client.get('/api/mcp/codex-setup', headers={'Origin': 'https://evil.example'}).status_code, 403)
        self.assertEqual(client.post('/api/mcp/codex-setup', json={}).status_code, 400)
        self.assertEqual(client.post('/api/mcp/call', json={'tool': 'status'}).status_code, 401)

    def test_disable_fails_delivered_call_and_discards_late_result(self):
        app = self.app()
        client = app.test_client()
        client.post('/api/mcp/enable', json={'enabled': True})
        bridge._STATE['last_poll'] = time.time()
        answer = []
        def invoke():
            with app.test_client() as c:
                answer.append(c.post('/api/mcp/call', json={'tool': 'apply_scheme', 'timeout': 5}, headers={'X-SPB-MCP-Token': bridge._token()}).get_json())
        worker = threading.Thread(target=invoke)
        worker.start()
        call = client.get('/api/mcp/poll?wait=1').get_json()['call']
        client.post('/api/mcp/enable', json={'enabled': False})
        worker.join(2)
        self.assertFalse(worker.is_alive())
        self.assertFalse(answer[0]['ok'])
        self.assertIn('off', answer[0]['error'])
        self.assertEqual(client.post('/api/mcp/result', json={'id': call['id'], 'ok': True, 'result': {}}).status_code, 409)


if __name__ == '__main__':
    unittest.main()
