"""Focused adapter checks; no SPB startup or desktop interaction."""
import asyncio
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'integrations/spb-mcp'))
from browser import Session, bounded, local_url


class AdapterChecks(unittest.TestCase):
    def test_local_targets(self):
        for url in ['http://localhost:59876/','http://127.0.0.1:59880/','http://[::1]:59876/']:
            self.assertEqual(local_url(url),url)
        for url in ['https://example.com','file:///C:/secret','http://user:pass@localhost','http://localhost.example.com']:
            with self.assertRaises(ValueError): local_url(url)

    def test_large_results_are_artifacts(self):
        with tempfile.TemporaryDirectory() as d:
            result=bounded({'payload':'x'*13000},Path(d))
            self.assertTrue(result['truncated'])
            self.assertEqual(len(json.loads(Path(result['artifact']).read_text())['payload']),13000)

    def test_upload_paths(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'paint.png';p.write_bytes(b'fixture')
            self.assertEqual(Session.files(str(p)),[str(p.resolve())])
            with self.assertRaises(ValueError):Session.files('not-a-real-relative-file.png')

    def test_gesture_releases_mouse_and_modifier_on_failure(self):
        async def run():
            s=object.__new__(Session)
            s.check_page=AsyncMock()
            s.scripts={}
            s.page=MagicMock()
            s.page.keyboard.down=AsyncMock();s.page.keyboard.up=AsyncMock()
            s.page.mouse.move=AsyncMock(side_effect=[None,RuntimeError('event failed')])
            s.page.mouse.down=AsyncMock();s.page.mouse.up=AsyncMock()
            loc=MagicMock();loc.bounding_box=AsyncMock(return_value={'x':0,'y':0,'width':100,'height':100})
            loc.evaluate=AsyncMock(return_value={'width':100,'height':100})
            s.unique=AsyncMock(return_value=loc)
            with self.assertRaises(RuntimeError):await s.gesture('#canvas',[[.1,.1],[.2,.2]],modifiers=['Shift'])
            s.page.mouse.up.assert_awaited_once_with(button='left')
            s.page.keyboard.up.assert_awaited_once_with('Shift')
        asyncio.run(run())

    def test_invalid_gesture_does_not_press_mouse(self):
        async def run():
            s=object.__new__(Session);s.check_page=AsyncMock();s.scripts={};s.page=MagicMock()
            s.page.mouse.down=AsyncMock()
            loc=MagicMock();loc.bounding_box=AsyncMock(return_value={'x':0,'y':0,'width':100,'height':100})
            loc.evaluate=AsyncMock(return_value={'width':100,'height':100});s.unique=AsyncMock(return_value=loc)
            for point in [[float('nan'),0],[2,0]]:
                with self.assertRaises(ValueError):await s.gesture('#canvas',[point])
            s.page.mouse.down.assert_not_awaited()
        asyncio.run(run())

    def test_attached_close_removes_handlers_preserves_tab(self):
        async def run():
            page=MagicMock();context=MagicMock()
            context.close=AsyncMock()
            s=Session('test',context,page,'http://localhost:59876/',Path('.'),owned=False)
            await s.close()
            context.close.assert_not_awaited()
            self.assertEqual(page.remove_listener.call_count,5)
            context.remove_listener.assert_called_once()
        asyncio.run(run())


if __name__=='__main__':unittest.main()
