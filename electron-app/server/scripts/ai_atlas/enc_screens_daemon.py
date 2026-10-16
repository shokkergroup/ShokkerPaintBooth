"""Lane S dev helper: ONE long-lived booted app session that executes Python snippets dropped in
_enc_work/daemon/in_<n>.py (globals: c = Ctx, pg, E = enc_screens). Output goes to out_<n>.txt.
Speeds up shot design (the app boot costs ~45 s).  Test server 59879 only (same guards as enc_screens)."""
import sys, os, time, io, traceback, contextlib
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import enc_screens as E
DIR = E.ROOT / "_enc_work" / "daemon"
DIR.mkdir(parents=True, exist_ok=True)
for f in DIR.glob("*"):
    f.unlink()
E.load_modules()
E.chrome_up()
import replay_owner as ro
import drv
assert ":59879" in drv.BASE
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    br = p.chromium.connect_over_cdp("http://127.0.0.1:9791")
    ctx = br.new_context(viewport={"width": E.VIEW[0], "height": E.VIEW[1]}, device_scale_factor=E.DPR)
    pg = ctx.new_page()
    pg.on("dialog", lambda d: d.dismiss())
    pg.route("**/api/ai/learned-cars*", lambda r: r.fulfill(status=200, content_type="application/json", body='{"ok":true,"v":1,"cars":[]}'))
    pg.route("**/api/ai/learned-elements*", lambda r: r.fulfill(status=200, content_type="application/json", body='{"ok":true,"v":1,"rows":[]}'))
    pg.route("**/api/ai/misses*", lambda r: r.fulfill(status=200, content_type="application/json", body='{"ok":true,"rows":[]}'))
    ro.boot_car(pg, "owner")
    assert ":59879" in pg.url
    c = E.Ctx(pg, ro)
    E.setup_owner(c)
    (DIR / "ready").write_text("ok")
    n = 0
    while True:
        f = DIR / f"in_{n}.py"
        if f.exists():
            time.sleep(0.3)
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
                try:
                    exec(compile(f.read_text(encoding="utf8"), str(f), "exec"), {"c": c, "pg": pg, "E": E, "ro": ro, "js": c.js})
                except SystemExit:
                    (DIR / f"out_{n}.txt").write_text("bye")
                    break
                except Exception:
                    traceback.print_exc(limit=4)
            (DIR / f"out_{n}.txt").write_text(buf.getvalue(), encoding="utf8")
            n += 1
        else:
            pg.wait_for_timeout(300)
    ctx.close()
