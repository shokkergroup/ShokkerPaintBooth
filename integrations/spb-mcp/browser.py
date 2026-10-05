"""SPB-only browser sessions. Playwright events stay inside Chrome, never desktop input.

General controls deliberately reuse the real UI/controllers and history dispatch.
This adapter does not directly assign Zone masks or Layer pixel buffers.
"""
from __future__ import annotations

import asyncio
import json
import math
import time
import uuid
from collections import deque
from pathlib import Path
from urllib.parse import urljoin, urlparse

from playwright.async_api import async_playwright

PAGE_JS = Path(__file__).with_name('page.js').read_text(encoding='utf-8')


def local_url(url: str) -> str:
    p = urlparse(url)
    if p.scheme not in ('http', 'https') or p.hostname not in ('localhost', '127.0.0.1', '::1') or p.username or p.password:
        raise ValueError('SPB URL must be an explicit localhost/loopback HTTP(S) address.')
    return url


def bounded(value, artifact_dir: Path, limit: int = 12000):
    payload = json.dumps(value, ensure_ascii=False, default=str)
    if len(payload) <= limit:
        return value
    artifact = artifact_dir / ('result-' + uuid.uuid4().hex[:12] + '.json')
    artifact.write_text(payload, encoding='utf-8')
    return {'truncated': True, 'characters': len(payload), 'artifact': str(artifact), 'preview': payload[:1000]}


class Session:
    def __init__(self, sid, context, page, url, artifacts, owned=True):
        self.id, self.context, self.page, self.url = sid, context, page, url
        self.artifacts, self.owned = artifacts, owned
        self.lock = asyncio.Lock()
        self.events = deque(maxlen=40)
        self.downloads = []
        self.jobs = set()
        self.dialog = None
        self.chooser = None
        self.dialog_response = None
        self.expected_upload = None
        self.watched = set()
        self.handlers = {}
        self.baselines = {}
        self.scripts = {}
        self.watch(page)
        self.on_new_page = self.watch
        context.on('page', self.on_new_page)

    def watch(self, page):
        if page in self.watched:
            return
        self.watched.add(page)
        handlers = {
            'pageerror': lambda e: self.events.append({'kind':'error','message':str(e)[:500]}),
            'console': lambda m: self.events.append({'kind':m.type,'message':m.text[:500]}) if m.type in ('error','warning') else None,
            'dialog': lambda d: self.job(self.on_dialog(d)),
            'filechooser': lambda c: self.job(self.on_chooser(c)),
            'download': lambda d: self.job(self.on_download(d))}
        for event,callback in handlers.items(): page.on(event,callback)
        self.handlers[page] = handlers

    def job(self, coro):
        task = asyncio.create_task(coro)
        self.jobs.add(task)
        def done(t):
            self.jobs.discard(t)
            if not t.cancelled() and t.exception():
                self.events.append({'kind':'adapter-error','message':str(t.exception())[:500]})
        task.add_done_callback(done)

    async def on_dialog(self, dialog):
        if self.dialog_response is not None:
            reply, self.dialog_response = self.dialog_response, None
            if reply.get('accept', True):
                await dialog.accept(str(reply.get('text', '')))
            else:
                await dialog.dismiss()
        else:
            self.dialog = dialog

    async def on_chooser(self, chooser):
        if self.expected_upload is not None:
            files, self.expected_upload = self.expected_upload, None
            await chooser.set_files(files)
        else:
            self.chooser = chooser

    async def on_download(self, download):
        dest = self.artifacts / (uuid.uuid4().hex[:8] + '-' + Path(download.suggested_filename).name)
        await download.save_as(dest)
        self.downloads.append({'name':download.suggested_filename,'path':str(dest),'bytes':dest.stat().st_size})

    async def check_page(self):
        if self.page.is_closed():
            raise ValueError('Selected page closed; use spb_pages to select another page.')
        p, base = urlparse(self.page.url), urlparse(self.url)
        if (p.scheme,p.hostname,p.port) != (base.scheme,base.hostname,base.port):
            raise ValueError('Selected page is outside this SPB origin; select an SPB page.')
        if self.dialog:
            raise ValueError('Native dialog pending; respond with spb_dialog first.')
        await self.page.evaluate(PAGE_JS)

    async def status(self):
        common = {'session':self.id,'pendingDialog':None,'pendingFileChooser':bool(self.chooser),
                  'downloads':self.downloads[-8:], 'recentErrors':list(self.events)[-5:],
                  'operations':[{'id':k,'done':v.done()} for k,v in self.scripts.items()]}
        if self.dialog:
            common['pendingDialog'] = {'type':self.dialog.type,'message':self.dialog.message,'default':self.dialog.default_value}
            return common
        await self.check_page()
        common.update(await self.page.evaluate('() => window.__spbMcp.state()'))
        return common

    def locator(self, target):
        if not target:
            raise ValueError('Supply target: a ref from spb_controls, or a CSS selector from observed app UI.')
        if target.startswith('ref:'):
            name = target[4:]
            if not all(c.isalnum() or c == '-' for c in name):
                raise ValueError('Invalid control reference.')
            return self.page.locator('[data-spb-mcp-ref="' + name + '"]')
        return self.page.locator(target)

    async def unique(self, target):
        loc = self.locator(target)
        count = await loc.count()
        if count != 1:
            raise ValueError(f'Target matches {count} controls; refresh spb_controls or supply an exact selector.')
        return loc

    async def action(self, a):
        kind = a['kind']
        target, value = a.get('target'), a.get('value')
        timeout = max(100, min(int(a.get('timeout_ms', 4000)), 15000))
        if kind == 'dialog':
            if not self.dialog:
                raise ValueError('No dialog is pending.')
            d, self.dialog = self.dialog, None
            await (d.accept(str(value or '')) if a.get('accept', True) else d.dismiss())
            return
        await self.check_page()
        self.assert_idle()
        if kind == 'wait':
            await self.locator(target).wait_for(state=value or 'visible',timeout=timeout)
            return
        if kind in ('click','double_click','hover','fill','select','check','uncheck','press','range','scroll','wait','upload','drag'):
            loc = await self.unique(target)
            if kind == 'click': await loc.click(button=a.get('button','left'), modifiers=a.get('modifiers',[]), timeout=timeout, no_wait_after=True)
            elif kind == 'double_click': await loc.dblclick(timeout=timeout)
            elif kind == 'hover': await loc.hover(timeout=timeout)
            elif kind == 'fill': await loc.fill(str(value), timeout=timeout)
            elif kind == 'select': await loc.select_option(value=value, timeout=timeout)
            elif kind == 'check': await loc.check(timeout=timeout)
            elif kind == 'uncheck': await loc.uncheck(timeout=timeout)
            elif kind == 'press': await loc.press(str(value), timeout=timeout, no_wait_after=True)
            elif kind == 'scroll':
                await loc.evaluate('(e,v) => e.scrollBy({left:v[0],top:v[1],behavior:"instant"})', value)
            elif kind == 'wait': await loc.wait_for(state=value or 'visible', timeout=timeout)
            elif kind == 'upload': await loc.set_input_files(self.files(value), timeout=timeout)
            elif kind == 'drag': await loc.drag_to(await self.unique(str(value)), timeout=timeout)
            elif kind == 'range':
                await loc.evaluate('''(el,value) => {
                    if (el.tagName !== 'INPUT' || el.type !== 'range') throw Error('Target is not a range input');
                    if (!Number.isFinite(Number(value))) throw Error('Range value must be numeric');
                    const set = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set;
                    set.call(el,String(value));
                    el.dispatchEvent(new Event('input',{bubbles:true}));
                    el.dispatchEvent(new Event('change',{bubbles:true}));
                }''',value)
        elif kind == 'key': await self.page.keyboard.press(str(value))
        elif kind == 'text': await self.page.keyboard.insert_text(str(value))
        elif kind == 'wheel': await self.page.mouse.wheel(float(value[0]),float(value[1]))
        else: raise ValueError('Unsupported action: ' + kind)

    @staticmethod
    def files(value):
        paths = value if isinstance(value,list) else [value]
        if not paths or len(paths) > 30:
            raise ValueError('Supply 1–30 local file paths.')
        result = []
        for raw in paths:
            path = Path(raw).expanduser()
            if not path.is_absolute() or not path.is_file():
                raise ValueError('Upload must name an existing absolute file path: ' + str(path))
            result.append(str(path.resolve()))
        return result

    async def gesture(self, target, points, space='normalized', button='left', modifiers=None, duration_ms=250, mode='stroke'):
        await self.check_page()
        self.assert_idle()
        loc = await self.unique(target)
        box = await loc.bounding_box()
        if not box or not box['width'] or not box['height']:
            raise ValueError('Gesture target is not visible.')
        dims = await loc.evaluate('(e) => ({width:e.width||e.clientWidth,height:e.height||e.clientHeight})')
        if not 1 <= len(points) <= 2000:
            raise ValueError('Supply 1–2000 points.')
        converted = []
        for pt in points:
            x,y = float(pt[0]),float(pt[1])
            if not all(math.isfinite(v) for v in (x,y)):
                raise ValueError('Coordinates must be finite.')
            if space == 'normalized': x,y = x*box['width'],y*box['height']
            elif space == 'canvas': x,y = x*box['width']/dims['width'],y*box['height']/dims['height']
            elif space != 'css': raise ValueError('space must be normalized, canvas or css')
            if not (0 <= x <= box['width'] and 0 <= y <= box['height']):
                raise ValueError('Point outside target. Pan/zoom or use a containing surface for off-canvas gestures.')
            converted.append((box['x']+x,box['y']+y))
        keys = modifiers or []
        down = False
        start = time.perf_counter()
        try:
            for key in keys: await self.page.keyboard.down(key)
            await self.page.mouse.move(*converted[0])
            if mode == 'stroke':
                await self.page.mouse.down(button=button)
                down = True
            for i,point in enumerate(converted[1:],1):
                await self.page.mouse.move(*point)
                delay = duration_ms/1000*i/max(1,len(converted)-1) - (time.perf_counter()-start)
                if delay > 0: await asyncio.sleep(delay)
            if mode == 'double_click':
                await self.page.mouse.dblclick(*converted[-1],button=button)
        finally:
            if down: await self.page.mouse.up(button=button)
            for key in reversed(keys): await self.page.keyboard.up(key)
        return {'points':len(points),'elapsedMs':round((time.perf_counter()-start)*1000,1),'space':space,'surface':target}

    def assert_idle(self):
        if any(not task.done() for task in self.scripts.values()):
            raise ValueError('App operation is running. Use spb_operation or answer its pending dialog first.')

    async def close(self):
        if self.dialog:
            await self.dialog.dismiss()
        if self.jobs:
            await asyncio.gather(*list(self.jobs), return_exceptions=True)
        for task in self.scripts.values():
            if not task.done(): task.cancel()
        if self.scripts: await asyncio.gather(*self.scripts.values(),return_exceptions=True)
        self.context.remove_listener('page',self.on_new_page)
        for page,handlers in self.handlers.items():
            for event,callback in handlers.items(): page.remove_listener(event,callback)
        self.handlers.clear()
        if self.owned:
            await self.context.close()
            if self.context.browser: await self.context.browser.close()


class BrowserManager:
    def __init__(self, artifacts: Path):
        self.artifacts = artifacts.resolve()
        self.artifacts.mkdir(parents=True, exist_ok=True)
        self.sessions = {}
        self.lock = asyncio.Lock()
        self.pw = None
        self.browsers = []

    async def open(self, url, visible=False, cdp_url=None, page_url=None):
        url = local_url(url)
        if not self.pw:
            self.pw = await async_playwright().start()
        sid = uuid.uuid4().hex[:12]
        dest = self.artifacts / sid
        dest.mkdir()
        if cdp_url:
            browser = await self.pw.chromium.connect_over_cdp(local_url(cdp_url))
            pages = [p for c in browser.contexts for p in c.pages if p.url == (page_url or url)]
            if len(pages) != 1:
                raise ValueError('CDP attachment needs one exact existing SPB page_url. No tab was selected.')
            page = pages[0]
            context, owned = page.context, False
        else:
            browser = await self.pw.chromium.launch(channel='chrome',headless=not visible,
                args=['--disable-background-timer-throttling','--disable-renderer-backgrounding'])
            self.browsers.append(browser)
            context = await browser.new_context(viewport={'width':1920,'height':1080},accept_downloads=True)
            # Never spawn a server-side Windows file dialog from an unattended session.
            # The normal in-app Shokker picker and HTML uploads stay available.
            await context.route('**/api/native-dialog',lambda route: route.fulfill(status=409,
                content_type='application/json',body='{"error":"Use the Shokker in-app picker in this MCP session."}'))
            page, owned = await context.new_page(), True
        session = Session(sid,context,page,url,dest,owned)
        self.sessions[sid] = session
        try:
            if owned:
                await page.goto(url,wait_until='domcontentloaded',timeout=30000)
            await session.check_page()
            return session
        except BaseException:
            await session.close()
            del self.sessions[sid]
            if owned: await browser.close()
            raise

    def get(self, sid):
        if sid not in self.sessions:
            raise ValueError('Unknown session; call spb_open_session first.')
        return self.sessions[sid]

    async def close(self):
        for s in self.sessions.values(): await s.close()
        for b in self.browsers: await b.close()
        if self.pw: await self.pw.stop()
