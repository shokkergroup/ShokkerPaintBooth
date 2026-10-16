"""Encyclopedia lane S - REAL pictures from the running app (Playwright).

    python scripts/ai_atlas/enc_screens.py <group> [shot-id-prefix ...] [--force]
    python scripts/ai_atlas/enc_screens.py --list

Groups (one app boot per run): ui, pairs, cars, spec, flow  (see the @shot decorators below).
Safety: the TEST server 127.0.0.1:59879 ONLY (never 59876, the owner's live app); its own Chrome
(CDP port 9791, own profile, started by _easy_claude_work/pw/chrome_up_9791.py).  Easy mode is hidden
and never captured.  Before every car shot the Wire / Mask / Car Mandatory template layers are hidden
and _finishLayerVisibilityChange() is called (via replay_owner.HIDE_TEMPLATE).

Every image is written to data/encyclopedia/screens/<id>.webp (<= 250 KB) and its manifest row is
merged into data/encyclopedia/screens.json IMMEDIATELY (atomic), so a crash loses nothing and a re-run
skips what is already on disk.  Output is one verdict line per image.
"""
import io
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

os.environ["SPB_CDP_PORT"] = "9791"          # own Chrome; never the shared ones
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PW = ROOT / "_easy_claude_work" / "pw"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(PW))
from PIL import Image  # noqa: E402

import enc_callouts as C  # noqa: E402

OUT = ROOT / "data" / "encyclopedia" / "screens"
MANIFEST = ROOT / "data" / "encyclopedia" / "screens.json"
MAX_KB = 250
DPR = 2
VIEW = (1700, 1000)
REG = {}      # id -> (group, fn)
ORDER = []


def shot(group, sid):
    def deco(fn):
        REG[sid] = (group, fn)
        ORDER.append(sid)
        return fn
    return deco


# ------------------------------------------------------------------ manifest + saving
def load_manifest():
    if MANIFEST.exists():
        return json.loads(MANIFEST.read_text(encoding="utf8"))
    return {"domain": "screens", "version": 1, "articles": [], "note": "Real pictures from the running app (lane S). Built by scripts/ai_atlas/enc_screens.py.", "screens": []}


def write_row(row):
    m = load_manifest()
    rows = [r for r in m["screens"] if r["id"] != row["id"]]
    rows.append(row)
    rows.sort(key=lambda r: r["id"])
    m["screens"] = rows
    m.setdefault("articles", [])
    m["count"] = len(rows)
    tmp = str(MANIFEST) + ".tmp"
    with open(tmp, "w", encoding="utf8", newline="\n") as f:
        json.dump(m, f, ensure_ascii=False, indent=1)
    os.replace(tmp, MANIFEST)


def have(sid):
    p = OUT / (sid + ".webp")
    if not p.exists():
        return False
    return any(r["id"] == sid for r in load_manifest()["screens"])


def save_webp(sid, im, maxw=1280):
    OUT.mkdir(parents=True, exist_ok=True)
    im = im.convert("RGB")
    if im.width > maxw:
        im = im.resize((maxw, round(im.height * maxw / im.width)), Image.LANCZOS)
    data = b""
    for q in (90, 85, 80, 74, 68, 60, 52):
        buf = io.BytesIO()
        im.save(buf, "WEBP", quality=q, method=6)
        data = buf.getvalue()
        if len(data) <= MAX_KB * 1024:
            break
    while len(data) > MAX_KB * 1024 and im.width > 600:     # still too big: shrink
        im = im.resize((int(im.width * 0.88), int(im.height * 0.88)), Image.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, "WEBP", quality=70, method=6)
        data = buf.getvalue()
    p = OUT / (sid + ".webp")
    tmp = str(p) + ".tmp"
    with open(tmp, "wb") as f:
        f.write(data)
    os.replace(tmp, p)
    return p, len(data), im.size


def emit(sid, title, caption, kind, articles, im, alt, callouts=None, maxw=1280, meta=None):
    p, n, size = save_webp(sid, im, maxw)
    row = {"id": sid, "title": title, "caption": caption, "file": "screens/" + p.name, "alt": alt,
           "article_ids": list(articles), "kind": kind, "w": size[0], "h": size[1], "bytes": n}
    if callouts:
        row["callouts"] = [{"n": i + 1, "label": t} for i, t in enumerate(callouts)]
    if meta:
        row["meta"] = meta
    write_row(row)
    print(f"{sid}: {size[0]}x{size[1]} {n // 1024} KB", flush=True)
    return row


# ------------------------------------------------------------------ the app session
class Ctx:
    def __init__(self, pg, ro):
        self.pg, self.ro = pg, ro

    # --- DOM helpers
    def js(self, code, arg=None):
        return self.ro.js(self.pg, code, arg)

    def rect(self, sel):
        """Page-CSS-px rect [x, y, w, h] of the first VISIBLE element for `sel`.
        sel = 'css'  or  'css::text' (smallest visible element inside css whose text contains `text`)."""
        return self.js(r"""(s) => {
          const parts = s.split('::'); const css = parts[0]; let txt = (parts[1] || '').toLowerCase(); let up = false;
          if (txt.endsWith('>')) { up = true; txt = txt.slice(0, -1); }
          const vis = e => { const r = e.getBoundingClientRect(); if (r.width < 2 || r.height < 2) return false;
                             const c = getComputedStyle(e); return c.visibility !== 'hidden' && c.display !== 'none'; };
          let list = Array.from(document.querySelectorAll(css)).filter(vis);
          if (txt) { list = list.filter(e => (e.innerText || e.value || e.title || '').toLowerCase().includes(txt));
                     list.sort((a, b) => (a.getBoundingClientRect().width * a.getBoundingClientRect().height) - (b.getBoundingClientRect().width * b.getBoundingClientRect().height)); }
          if (!list.length) return null; let el = list[0]; if (up && el.parentElement) el = el.parentElement; const r = el.getBoundingClientRect();
          return [r.x, r.y, r.width, r.height]; }""", sel)

    def items(self, css, limit=14, minw=10):
        """Visible elements matching `css`, ordered top-to-bottom then left-to-right:
        [{r:[x,y,w,h], label}] with the label taken from aria-label / title / own text (the app's own words)."""
        return self.js(r"""(a) => { const css = a[0], lim = a[1], minw = a[2];
          const vis = e => { const r = e.getBoundingClientRect(); if (r.width < minw || r.height < 8) return false;
                             const c = getComputedStyle(e); return c.visibility !== 'hidden' && c.display !== 'none' && r.x < 1700 && r.y < 1000 && r.x + r.width > 0; };
          let out = Array.from(document.querySelectorAll(css)).filter(vis).map(e => { const r = e.getBoundingClientRect();
            let l = (e.getAttribute('aria-label') || '').trim() || (e.innerText || e.value || '').trim().split(String.fromCharCode(10))[0] || (e.title || '').trim();
            return { r: [r.x, r.y, r.width, r.height], label: l.slice(0, 90) }; });
          out.sort((p, q) => (Math.round(p.r[1] / 10) - Math.round(q.r[1] / 10)) || (p.r[0] - q.r[0]));
          return out.slice(0, lim); }""", [css, limit, minw])

    def auto(self, css, limit=14, first=1, **opt):
        """(marks, labels) numbered from `first` for every visible element matching css."""
        its = self.items(css, limit)
        marks = [(first + i, it["r"], dict(opt)) for i, it in enumerate(its)]
        return marks, [it["label"] for it in its]

    def need(self, sel):
        r = self.rect(sel)
        if not r:
            raise RuntimeError("not visible: " + sel)
        return r

    def union(self, sels, pad=0):
        rs = [self.need(s) if isinstance(s, str) else list(s) for s in sels]
        x0 = min(r[0] for r in rs); y0 = min(r[1] for r in rs)
        x1 = max(r[0] + r[2] for r in rs); y1 = max(r[1] + r[3] for r in rs)
        return [x0 - pad, y0 - pad, x1 - x0 + 2 * pad, y1 - y0 + 2 * pad]

    def click(self, sel, wait=500):
        r = self.need(sel)
        self.pg.mouse.click(r[0] + r[2] / 2, r[1] + r[3] / 2)
        self.pg.wait_for_timeout(wait)

    def scroll_to(self, sel, block="start", ms=500):
        """Scroll the element for `sel` (same syntax as rect) into view inside its scroller."""
        self.js(r"""(s) => { const parts = s.split('::'); const css = parts[0]; const txt = (parts[1] || '').toLowerCase().replace(/>$/, '');
          let list = Array.from(document.querySelectorAll(css)); if (txt) list = list.filter(e => (e.innerText || e.value || '').toLowerCase().includes(txt));
          if (txt) list.sort((a, b) => a.getBoundingClientRect().width * a.getBoundingClientRect().height - b.getBoundingClientRect().width * b.getBoundingClientRect().height);
          if (list[0]) list[0].scrollIntoView({ block: '%s' }); return !!list[0]; }""" % block, sel)
        self.pg.wait_for_timeout(ms)

    def wait(self, ms):
        self.pg.wait_for_timeout(ms)

    # --- screenshot with callouts. region: css selector (or list of selectors) or [x,y,w,h]
    def grab(self, region, marks=(), pad=0, clip_to_view=True):
        if isinstance(region, str):
            region = self.union([region], pad)
        elif region and isinstance(region[0], str):
            region = self.union(region, pad)
        x, y, w, h = region
        if clip_to_view:
            x0, y0 = max(0, x), max(0, y)
            x1, y1 = min(VIEW[0], x + w), min(VIEW[1], y + h)
            x, y, w, h = x0, y0, x1 - x0, y1 - y0
        png = self.pg.screenshot(clip={"x": x, "y": y, "width": w, "height": h})
        im = Image.open(io.BytesIO(png)).convert("RGB")
        ms = []
        for mk in marks:
            n, sel = mk[0], mk[1]
            opt = mk[2] if len(mk) > 2 else {}
            r = self.rect(sel) if isinstance(sel, str) else sel
            if not r:
                print("   (mark %s not visible: %s)" % (n, sel))
                continue
            ms.append(dict(n=n, rect=(r[0] - x, r[1] - y, r[2], r[3]), **opt))
        rad = max(7.0, min(11.0, w / 60.0))      # badge size follows the crop size (small crops get small badges)
        return C.annotate(im, ms, scale=DPR, radius=rad) if ms else im

    def full(self, marks=()):
        return self.grab([0, 0, VIEW[0], VIEW[1]], marks)

    # --- app state helpers
    def settle(self):
        """Hide Wire/Mask/Car Mandatory, refresh the template, wait until the live preview stops changing."""
        info, _ = self.ro.settle_preview(self.pg, os.path.join("enc_screens", "settle.png"))
        return info

    def preview_png(self, crop=None):
        """The live preview picture at its natural size, as a PIL image (what the buyer's preview shows)."""
        d = self.js("""() => { const i = document.getElementById('livePreviewImg'); if (!i || !(i.naturalWidth > 32)) return null;
                       const c = document.createElement('canvas'); c.width = i.naturalWidth; c.height = i.naturalHeight;
                       c.getContext('2d').drawImage(i, 0, 0); return c.toDataURL('image/png'); }""")
        if not d:
            return None
        import base64
        return Image.open(io.BytesIO(base64.b64decode(d.split(",", 1)[1]))).convert("RGB")

    def esc(self):
        self.pg.keyboard.press("Escape")
        self.pg.wait_for_timeout(300)


def chrome_up():
    try:
        urllib.request.urlopen("http://127.0.0.1:9791/json/version", timeout=1.5)
        return
    except Exception:
        pass
    subprocess.run([sys.executable, str(PW / "chrome_up_9791.py")], check=True)


def run_group(group, want, force):
    todo = [s for s in ORDER if REG[s][0] == group and (not want or any(s.startswith(w) for w in want))]
    if not force:
        skipped = [s for s in todo if have(s)]
        todo = [s for s in todo if not have(s)] if not want else todo
        for s in skipped:
            if not want:
                print(f"{s}: exists, skipped")
    if not todo:
        print("nothing to do for", group)
        return
    chrome_up()
    import replay_owner as ro      # sets drv.BASE to the TEST server
    import drv
    assert ":59879" in drv.BASE and "59876" not in drv.BASE, drv.BASE
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        br = p.chromium.connect_over_cdp("http://127.0.0.1:9791")
        ctx = br.new_context(viewport={"width": VIEW[0], "height": VIEW[1]}, device_scale_factor=DPR)
        pg = ctx.new_page()
        pg.on("dialog", lambda d: d.dismiss())
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)[:200]))
        # keep the test page away from the owner's real learned-car files
        pg.route("**/api/ai/learned-cars*", lambda r: r.fulfill(status=200, content_type="application/json", body='{"ok":true,"v":1,"cars":[]}'))
        pg.route("**/api/ai/learned-elements*", lambda r: r.fulfill(status=200, content_type="application/json", body='{"ok":true,"v":1,"rows":[]}'))
        pg.route("**/api/ai/misses*", lambda r: r.fulfill(status=200, content_type="application/json", body='{"ok":true,"rows":[]}'))
        t = time.time()
        names = ro.boot_car(pg, "owner")
        assert ":59879" in pg.url, pg.url
        print(f"booted {len(names)} layers in {time.time() - t:.0f}s ({pg.url})", flush=True)
        c = Ctx(pg, ro)
        STATE.setup(c, group)
        for sid in todo:
            t = time.time()
            try:
                REG[sid][1](c)
            except Exception as exc:
                import traceback
                print(f"{sid}: FAILED {type(exc).__name__}: {str(exc)[:200]}")
                traceback.print_exc(limit=2, file=sys.stdout)
                try:
                    c.esc()
                except Exception:
                    pass
            print(f"   ({time.time() - t:.1f}s)", flush=True)
        if errs:
            print("page errors:", errs[:3])
        ctx.close()


class STATE:
    @staticmethod
    def setup(c, group):
        """The owner's real project: its 8 zones restored, template layers hidden, preview settled."""
        fn = SETUPS.get(group, setup_owner)
        fn(c)


PROJECT = [   # the example project every UI shot shows: the owner's example ARCA Chevy PSD with four zones (top first)
    dict(name="Numbers", finish="base::chrome", color="source", region={"layers": ["Numbers"], "everything": True}),
    dict(name="Black panels", finish="base::carbon_base", color="source", region={"layers": ["Black Base"], "everything": True}),
    dict(name="White stripes", finish="base::pearl", color="source", region={"layers": ["White Base"], "everything": True}),
    dict(name="Yellow body", finish="base::candy", color="#d4111f", region={"layers": ["Yellow Base"], "everything": True}),
]


def build_project(c):
    c.js("() => { while (zones.length > 1) zones.splice(0, 1); renderZones(); return zones.length; }")
    for spec in reversed(PROJECT):          # each add lands on top
        r = c.js("(s) => { const r = SpbProZone.add(s); return { ok: r.ok, w: (r.warnings || []).slice(0, 3) }; }", spec)
        if not r["ok"] or r["w"]:
            print("   zone warn:", spec["name"], r)
    c.js("() => { renderZones(); triggerPreviewRender(); return 1; }")
    c.js("async () => await SpbProZone.whenSettled(90000)")


def tidy(c, zone=0):
    """ZONE mode, the wanted zone card selected, the Wire layer card collapsed, toast gone."""
    c.js("() => { const i = document.getElementById('iracingId'); if (i && i.value !== '123456') { i.value = '123456'; i.dispatchEvent(new Event('input', { bubbles: true })); i.dispatchEvent(new Event('change', { bubbles: true })); } return 1; }")   # privacy: never show the owner's real iRacing ID
    c.js("() => { ['rightPanel', 'leftPanel'].forEach(i => { const e = document.getElementById(i); if (e) e.style.visibility = ''; }); return 1; }")   # a failed dropdown shot may have left the side panels hidden
    c.js("() => { if (!document.getElementById('encNoToast')) { const s = document.createElement('style'); s.id = 'encNoToast'; s.textContent = '#toast{display:none !important}'; document.head.appendChild(s); } return 1; }")
    try:
        if c.rect(".layer-row-details"):
            c.click(".layer-row-details button::done", 500)
    except Exception:
        pass
    try:        # the AI copilot panel opens over the window after CHAT mode: close it (its last header button is the X)
        its = c.items("#spbProAI button", 8)
        if its and its[0]["r"][1] < 150:
            hdr = [i for i in its if i["r"][1] < 150]
            r = max(hdr, key=lambda i: i["r"][0])["r"]
            c.pg.mouse.click(r[0] + r[2] / 2, r[1] + r[3] / 2)
            c.wait(500)
    except Exception:
        pass
    c.click("#btnToolbarModeZone", 400)
    c.click("#zone-card-%d" % zone, 700)
    c.wait(300)


def setup_owner(c):
    build_project(c)
    c.settle()
    tidy(c, 0)


SETUPS = {}


# ------------------------------------------------------------------ shots are defined in enc_screens_*.py modules
def load_modules():
    for name in ("enc_screens_ui", "enc_screens_ui2", "enc_screens_ui3", "enc_screens_ui4", "enc_screens_pairs", "enc_screens_cars", "enc_screens_spec", "enc_screens_flow", "enc_screens_tools", "enc_screens_sculpt"):
        if (HERE / (name + ".py")).exists():
            __import__(name)


def main(argv):
    force = "--force" in argv
    args = [a for a in argv if not a.startswith("--")]
    load_modules()
    if "--list" in argv or not args:
        for s in ORDER:
            print(REG[s][0], s, "(done)" if have(s) else "")
        return
    group, want = args[0], args[1:]
    run_group(group, want, force)


if __name__ == "__main__":
    import enc_screens as _m      # shot modules import enc_screens; keep ONE registry
    _m.main(sys.argv[1:])
