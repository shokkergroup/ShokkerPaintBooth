"""Lane S - finishes RENDERED ON A REAL CAR (the owner's example ARCA Chevy PSD), as the app's own live preview. Group: cars.
cat_<shelf>  = the best finish of each shelf; car_<finish id> = the next best ones. The finish picks come from the finish pages' own ratings."""
import json, re
import enc_screens as E
from enc_screens import shot

IDX = json.load(open(E.ROOT / "_enc_work" / "finish_idx.json", encoding="utf8"))
CONCEPT = {"astra": "finishes.astra", "foundation": "finishes.foundation_and_efx", "foundation_efx": "finishes.foundation_and_efx",
           "fractured_shokk": "finishes.fractured_mortal_neon", "neon_underground": "finishes.fractured_mortal_neon",
           "shokk_works": "finishes.plates_xlab_works", "x_lab": "finishes.plates_xlab_works", "prism_forge": "finishes.plates_xlab_works",
           "source_pattern_plates": "finishes.plates_xlab_works", "viva_mexico": "finishes.retro_cultural", "rising_sun": "finishes.retro_cultural",
           "union_jacked": "finishes.retro_cultural", "sock_hop": "finishes.retro_cultural", "let_freedom_ring": "finishes.retro_cultural",
           "groovy_vibes": "finishes.retro_cultural", "tactical_field": "finishes.nature_tactical_cyberpunk", "cyberpunk": "finishes.nature_tactical_cyberpunk",
           "dark_city": "finishes.nature_tactical_cyberpunk", "spectrum_shift": "finishes.colorshoxx_and_shift", "color_clash": "finishes.colorshoxx_and_shift",
           "fractured_wilds": "finishes.nature_tactical_cyberpunk"}
BODY = ["Yellow Base", "White Base", "Black Base"]


def ranked(items):
    own = [i for i in items if i["own"]] or items
    return sorted(own, key=lambda i: (-i["hero"], i["risk"], -i["appeal"], i["key"]))


def paint_for(f):
    if f["own"]:
        return "finish"
    return "#c8102e"


def pick_plan():
    plan = []        # (sid, group_domain, finish)
    for dom, items in IDX.items():
        sh = dom.replace("finish_", "")
        r = ranked(items)
        plan.append(("cat_" + sh, dom, r[0]))
        extra = 3 if len(items) >= 400 else (1 if len(items) >= 25 else 0)
        for f in r[1:1 + extra]:
            plan.append(("car_" + re.sub(r"^\w+::", "", f["key"]), dom, f))
    return plan


def render_tile(c, f):
    spec = dict(name=f["title"][:40], finish=f["key"], color=paint_for(f), region={"layers": BODY, "everything": True})
    c.js("() => { while (zones.length > 1) zones.splice(0, 1); renderZones(); return zones.length; }")
    r = c.js("(s) => { const r = SpbProZone.add(s); return { ok: r.ok, w: (r.warnings || []).slice(0, 3) }; }", spec)
    if not r["ok"]:
        raise RuntimeError("zone add failed: %s" % r)
    c.js("() => { renderZones(); triggerPreviewRender(); return 1; }")
    c.js("async () => await SpbProZone.whenSettled(90000)")
    c.wait(400)
    return c.preview_png()


def make(sid, dom, f):
    def fn(c):
        im = render_tile(c, f)
        if im is None:
            raise RuntimeError("no preview")
        sh = f["shelf"]
        cap = "%s on the example ARCA car (shelf: %s). Spec character: metal %s, roughness %s, clearcoat %s." % (f["title"], re.sub(r"^[^\w]+", "", sh).strip(), f["m"], f["r"], f["cc"])
        arts = [f["id"]] + ([CONCEPT[dom.replace("finish_", "")]] if sid.startswith("cat_") and dom.replace("finish_", "") in CONCEPT else [])
        E.emit(sid, f["title"] + " on the car", cap, "car_render", arts, im, "The app's live preview of the example ARCA car with the finish %s applied to the body." % f["title"],
               maxw=1024, meta={"finish_key": f["key"], "shelf": sh})
    return fn


for _sid, _dom, _f in pick_plan():
    E.REG[_sid] = ("cars", make(_sid, _dom, _f))
    E.ORDER.append(_sid)
