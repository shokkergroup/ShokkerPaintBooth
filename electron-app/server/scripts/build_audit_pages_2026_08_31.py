# -*- coding: utf-8 -*-
"""Audit pages for the 2026-08-31 overnight rebuild.

One builder for the five lanes the owner commissioned in a single brief, so the
review loop (BUILD -> AUDIT -> VERDICTS -> ACT -> REGENERATE) has a page per
category instead of a wall of contact sheets:

    cosmos      FRACTURED COSMOS      60 rebuilt
    elements    FRACTURED ELEMENTS    60 rebuilt (ATMOSPHERE retired into it)
    nightshift  FRACTURED NIGHTSHIFT  101 -> 50, day/night flip now measured
    paradigm    PARADIGM              34 -> 50, redesigned around one idea
    mortalshokk MORTAL SHOKK          26 finishes kept, all 26 specs rebuilt

Same composition as the FLAMES page: [full 2048 view | true 1:1 on-car crop |
spec at 1:1]. The spec panel is 1:1 because a 2048 spec downsampled to 512
aliases 10px material cells into pixel noise and makes a correct map look like
confetti (learned the hard way on the FLAMES round).

usage: python scripts/build_audit_pages_2026_08_31.py [lane ...]
"""
import contextlib
import io
import json
import logging
import os
import sys
import time

ROOT = r"C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum"
os.chdir(ROOT)
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import cv2                                                       # noqa: E402
import numpy as np                                               # noqa: E402
from spb_audit_page_builder import build_page                     # noqa: E402

logging.disable(logging.CRITICAL)
_buf = io.StringIO()
with contextlib.redirect_stdout(_buf), contextlib.redirect_stderr(_buf):
    import shokker_engine_v2 as eng

SHAPE = (2048, 2048)
MASK = np.ones(SHAPE, np.float32)
BASE = np.full(SHAPE + (3,), 0.5, np.float32)
PANEL = 512
PANELS = (("FULL 2048 VIEW", "full"), ("TRUE 1:1 ON-CAR CROP", "crop"),
          ("SPEC M/R/Cc  (1:1)", "spec"))


def measured(progress_file):
    """The lane's own best-of-2 cold timings beat anything measured here — this
    pass competes with the owner's live server for the CPU."""
    out = {}
    if os.path.exists(progress_file):
        for line in io.open(progress_file, encoding="utf-8"):
            try:
                r = json.loads(line)
            except Exception:
                continue
            if r.get("phase") == "verify" and r.get("fid"):
                out[r["fid"]] = r.get("sec")
    return out


def _lane_cosmos():
    import engine.expansions.fractured_cosmos_2026 as m
    return [(f, "%s  \u00b7  %s" % (d["name"], m.CHAPTERS[d["chapter"]]), d["desc"])
            for f, d in m.COSMOS.items()], "FRACTURED_COSMOS_PROGRESS.jsonl"


def _lane_elements():
    import engine.expansions.fractured_elements_2026 as m
    return [(f, "%s  \u00b7  %s" % (d["name"], m.CHAPTERS[d["chapter"]]), d["desc"])
            for f, d in m.ELEMENTS.items()], "FRACTURED_ELEMENTS_PROGRESS.jsonl"


def _lane_nightshift():
    # NIGHTSHIFT has no chapters \u2014 it is one flat set of 50, and what identifies
    # a card is the pair of material cards that own day and night.
    import engine.expansions.fractured_nightshift_2026 as m
    return [(f, "%s  \u00b7  %s \u2194 %s"
             % (d["name"], d["day_card"].replace("_", " "),
                d["night_card"].replace("_", " ")),
             "%s   [day %s \u00b7 night %s \u00b7 night share %.2f]"
             % (d["desc"], d["day_card"], d["night_card"], float(d.get("share", 0.5))))
            for f, d in m.NIGHTSHIFT.items()], "FRACTURED_NIGHTSHIFT_PROGRESS.jsonl"


def _lane_paradigm():
    import engine.expansions.paradigm_2026 as m
    return [(f, "%s  \u00b7  %s" % (m.title(f), m.CHAPTERS[d["chapter"]]),
             "%s   [reads as %s, behaves like the %s deck]"
             % (d["desc"], d["implies"].replace("_", " "),
                d["bands"][-1][0].replace("_", " ")))
            for f, d in m.PARADIGM.items()], "PARADIGM_PROGRESS.jsonl"


def _lane_mortalshokk():
    from engine.paint_v2.mortal_shokk_spec_2026 import MORTAL_SHOKK_SPECS as S
    rows = []
    for fid, r in S.items():
        rows.append((fid, fid[3:].replace("_", " ").title() + "  \u00b7  MORTAL SHOKK",
                     "spec rebuilt: %s   [ground %s \u00b7 figure %s \u00b7 veins %s \u00b7 flash %s]"
                     % (r.get("note", ""), r.get("ground"), r.get("figure"),
                        r.get("vein_card"), r.get("flash_card"))))
    return rows, "MORTAL_SHOKK_PROGRESS.jsonl"



def _lane_money():
    import engine.expansions.money_shokk_2026 as m
    return [(f, "%s  ·  %s" % (m.title(f), m.CHAPTERS[d["chapter"]]), d["desc"])
            for f, d in m.MONEY.items()], "MONEY_SHOKK_PROGRESS.jsonl"


def _lane_world():
    import engine.expansions.world_of_color_2026 as m
    return [(f, "%s  ·  %s" % (m.title(f), m.CHAPTERS[d["chapter"]]), d["desc"])
            for f, d in m.WORLD.items()], "WORLD_OF_COLOR_PROGRESS.jsonl"


def _lane_cultural():
    """All five cultural shelves on one page — the paint is unchanged, so what is
    under review is the MATERIAL each spec was given."""
    import json as _json
    import subprocess as _sp
    import numpy as _np
    from engine.paint_v2 import cultural_spec_2026 as _CS
    cats = {"viva_mexico": "MEXICO", "rising_sun": "RISING", "union_jacked": "UNION",
            "forbidden_dragon": "DRAGON", "let_freedom_ring": "FREEDOM"}
    rows = []
    for cat, key in cats.items():
        r = _sp.run(["node", "scripts/spb_catalog_query.js", "dump", key],
                    capture_output=True, text=True, encoding="utf-8")
        items = _json.loads(r.stdout[r.stdout.index("["):r.stdout.rindex("]") + 1])
        for it in items:
            fid = it["id"]
            try:
                _s, pf = eng.MONOLITHIC_REGISTRY[fid]
                q = _np.asarray(pf(_np.full((256, 256, 3), 0.5, _np.float32), (256, 256),
                                   _np.ones((256, 256), _np.float32), 51, 1.0, None), _np.float32)
                if q.max() > 1.5:
                    q = q / 255.0
                sname, note = _CS.story_of(cat, fid, q)
            except Exception:
                sname, note = "?", ""
            rows.append((fid, "%s  ·  %s" % (it["name"], cat.replace("_", " ").upper()),
                         "spec material: **%s** — %s" % (sname, note)))
    return rows, "CULTURAL_SPEC_PROGRESS.jsonl"



def _era_lane(modname, table_attr):
    """The five 2026-09-01 shelves are BASES, not monolithics: their spec is
    `spec(shape, seed, sm, base_m, base_r)` returning three channels, so the
    render loop below needs a different call. Rows carry a marker for that."""
    import importlib
    m = importlib.import_module("engine.paint_v2." + modname)
    table = getattr(m, table_attr)
    rows = []
    for fid, d in table.items():
        rows.append((fid, "%s  ·  %s" % (m.title(fid), m.LANES[d["lane"]]),
                     "%s   [deck: %s]" % (d["desc"], d["deck"])))
    return rows, "%s_PROGRESS.jsonl" % modname.upper(), m


def _lane_far_out():
    return _era_lane("era_1970s_2026", "FAR_OUT")


def _lane_bad_and_rad():
    return _era_lane("era_1980s_2026", "BAD_AND_RAD")


def _lane_all_that():
    return _era_lane("era_1990s_2026", "ALL_THAT")


def _lane_tactical():
    return _era_lane("tactical_2026", "TACTICAL")


def _lane_cyberpunk():
    return _era_lane("cyberpunk_2026", "CYBERPUNK")


LANES = {
    "farout": dict(
        build=_lane_far_out, accent="#c98a2e",
        title=('<span class="flag">🩩 FAR OUT — the 1970s</span> — Round 1 Audit '
               '<span style="color:var(--dim);font-weight:400">(60 finishes)</span>'),
        sub=("Your words: <i>“OPTIC LAB — currently 50 finishes of kind of bullshit here too… we already have SOCK HOP for 1950s looks, GROOVY VIBES for 1960s looks, how about we make OPTIC LAB totally 1970s — DISCO, SHAG CARPET LOOKS, OUTLAW COUNTRY WESTERN.”</i> The old shelf was five unrelated one-off modules under a technique name. Four rooms of the decade, fifteen each: 🩩 DISCO · 🟫 SHAG · 🤠 OUTLAW · 🚐 VAN ART.")),
    "badandrad": dict(
        build=_lane_bad_and_rad, accent="#d43a8a",
        title=('<span class="flag">⚡ BAD & RAD — the 1980s</span> — Round 1 Audit '
               '<span style="color:var(--dim);font-weight:400">(60 finishes)</span>'),
        sub=("Your words: <i>“MARBLE & ONYX — tons of repeating designs in here. LAZY… needs total rework… Maybe the 80s can be Bad and Rad.”</i> The old shelf was ONE veining algorithm recoloured nineteen times. Four rooms: 🕹 ARCADE · 🌆 GRID · 📐 MEMPHIS · 🎸 RADICAL.")),
    "allthat": dict(
        build=_lane_all_that, accent="#2fa8a0",
        title=('<span class="flag">💿 ALL THAT — the 1990s</span> — Round 1 Audit '
               '<span style="color:var(--dim);font-weight:400">(60 finishes)</span>'),
        sub=("Your words: <i>“I do NOT have a category for this yet but let’s also do 1990s and come up with a cute name for it that is Totally 90s.”</i> Four rooms: 💾 CD-ROM · 🛹 EXTREME · 🎤 FRESH · 🎸 FLANNEL.")),
    "tactical": dict(
        build=_lane_tactical, accent="#6b7a4a",
        title=('<span class="flag">🎯 TACTICAL & FIELD</span> — Round 1 Audit '
               '<span style="color:var(--dim);font-weight:400">(60 finishes)</span>'),
        sub=("Your words: <i>“The TACTICAL side will also include camo, outdoors-y stuff — all different kinds of camo/military looks along with actual tactical stuff, hunting/fishing etc.”</i> Almost nothing here is shiny, which makes it the shelf that tests the FLAT end of the material deck. Four lanes: 🌲 CAMO · 🔫 HARDWARE · 🎣 FIELD · 🌙 NIGHT.")),
    "cyberpunk": dict(
        build=_lane_cyberpunk, accent="#8b3fd4",
        title=('<span class="flag">🌃 CYBERPUNK</span> — Round 1 Audit '
               '<span style="color:var(--dim);font-weight:400">(60 finishes)</span>'),
        sub=("Your words: <i>“The Cyberpunk can be it’s own thing with 60 finishes. There’s so many lanes we can play with in Cyberpunk.”</i> The old shelf’s failure was that “cyberpunk” meant “neon” — and neon is a light source, not a material. Four lanes that are four different KINDS of surface: 🌃 STREET (wet, emissive) · 🦾 CHROME (metal, ceramic) · 💊 NETRUN (glass, glitch) · ☢ SPRAWL (oxide, rubber, chalk).")),
    "money": dict(
        build=_lane_money, accent="#3fa96a",
        title=('<span class="flag">💵 MONEY SHOKK</span> — Total Rework Audit '
               '<span style="color:var(--dim);font-weight:400">(40 rebuilt)</span>'),
        sub=("Your words: <i>“forty themed exotic engines about wealth in every form — mint "
             "foil, vault steel, counterfeit gold, burn-a-stack green. Flexes harder than chrome. Right "
             "now we are falling WELL SHORT.”</i> The old 40 were <b>{colour} {creature}</b> in four "
             "seeded batches — Canary Coffin, Cerulean Cobra, Lime Scorpion, Seafoam Piranha — "
             "with nothing about money in them. Money is not a colour, it is a MANUFACTURING PROCESS, and "
             "currency is the most over-engineered printed object on earth: intaglio you can feel with a "
             "thumbnail, guilloche cut on a rose engine, microtext too small to photocopy, a security "
             "thread windowed through the paper. Five chapters of eight: 🖨 MINT · "
             "🏦 VAULT · 💎 ASSET · 🎭 COUNTERFEIT · "
             "🔥 BURN. The loud cards are all here — chrome, mercury, carrier, spectraflame "
             "— but EARNED: the foil stripe, the bullion, the diamond table. Never the whole panel.")),
    "world": dict(
        build=_lane_world, accent="#2f8fd0",
        title=('<span class="flag">🌍 WORLD OF COLOR</span> — COLORSHOXX Repurposed '
               '<span style="color:var(--dim);font-weight:400">(77 → 100)</span>'),
        sub=("Your words: <i>“COLORSHOXX... was originally designed to try to do something unique "
             "with color flipping. It’s outdated and very repetitive now. Take it from 77 to 100 and "
             "repurpose it to WORLD OF COLOR which will take colors/styles from various COUNTRIES.”</i> "
             "The old specs were the tell: <b>a median of 2 material cards over 2 families, roughness sigma "
             "7.0 and clearcoat sigma 2.5</b> — two flat cards, 77 times. These 100 are twenty places "
             "× five, and every finish is a MATERIAL OR PROCESS that place actually makes colour with: "
             "a tartan sett, an indigo vat, a celadon glaze, an ochre bed, a salt terrace. That is a "
             "deliberately different axis from the five CULTURAL shelves, which are flags and iconography "
             "— so this one cannot become a second copy of those. Everything is drawn from "
             "commercially made textiles, ceramics, minerals and landscape; no sacred or ceremonial "
             "designs are used.")),
    "cultural": dict(
        build=_lane_cultural, accent="#c08a3e",
        title=('<span class="flag">🌐 CULTURAL</span> — Spec Rebuild Audit '
               '<span style="color:var(--dim);font-weight:400">(185 finishes, paint untouched)</span>'),
        sub=("Your brief: <i>“keep the designs in place that’s there now for the base paint and "
             "rework ALL of the specs... apply specs that make sense to EACH finish in EACH of those "
             "categories.”</i> <b>The paint is byte-identical</b> — these are hand-authored "
             "plates and they stay. What was measurably wrong was the spec: <b>47 of the 185 had a "
             "clearcoat sigma below 20</b>, meaning the coat itself did nothing, and UNION JACKED was flat "
             "across all 45 cards (median 12, maximum 22). Twenty more scored below 0.30 on whether the "
             "spec sat on the artwork at all. Every spec is now authored live from that finish’s OWN "
             "plate: six material roles found in the artwork, each dealt a complete card from the shared "
             "deck. The vocabulary is what each culture actually builds things out of — Viva Mexico’s "
             "talavera, worked silver and hammered copper; Rising Sun’s urushi, raku and kintsugi; "
             "Union Jacked’s wet asphalt, vitreous enamel and brass; Forbidden Dragon’s "
             "cloisonné, jade and carved lacquer; Let Freedom Ring’s bumper chrome and hard "
             "enamel — and each finish is matched to a material <b>by measuring its own paint</b>, "
             "not by hand. Each card below names the material it was given.")),
    "cosmos": dict(
        build=_lane_cosmos, accent="#7b5cff",
        title=('<span class="flag">\U0001f30c FRACTURED COSMOS</span> \u2014 Round 1 Audit '
               '<span style="color:var(--dim);font-weight:400">(60 rebuilt)</span>'),
        sub=("Your brief: the Fractured categories must be <b>unique, cool, and live up to what "
             "they say they do</b>. COSMOS says off-planet, space, UFO. What was on the shelf was "
             "three unrelated blocks \u2014 20 genuinely on-theme, then <b>20 colour-name "
             "recolours</b> (Cyan Drift / Cyan Dust Lane / Cyan Shockwave / Cyan Spiral, then the "
             "same four in gilded, magenta, teal and violet), then <b>20 iridescent finishes with "
             "no space in them at all</b> (Oil-Slick Prism Shatter, Rainbow Truchet, Spectral "
             "Marble Flow). These 60 are all things you can only see off Earth, in five chapters: "
             "\u25ce CONTACT \u00b7 \U0001fa90 WORLDS \u00b7 \u2734 DEEP \u00b7 \u2604 EVENT \u00b7 "
             "\U0001f6f8 VESSEL. Palettes are named after real objects, not colours.")),
    "elements": dict(
        build=_lane_elements, accent="#3fb6d8",
        title=('<span class="flag">\U0001f30a FRACTURED ELEMENTS</span> \u2014 Round 1 Audit '
               '<span style="color:var(--dim);font-weight:400">(60 rebuilt)</span>'),
        sub=("Your brief: weather \u2014 water, rain, sleet, snow, ice, tornadoes, hurricanes, "
             "tsunamis, sandstorms, <b>anything but fire</b>, since fire has its own category. The "
             "old shelf was 20 deep-sea creatures plus two colour grids. These 60 are weather in "
             "five chapters: \U0001f327 RAIN \u00b7 \u2744 FROZEN \u00b7 \U0001f300 STORM \u00b7 "
             "\U0001f30a WATER \u00b7 \U0001f3dc DRY. The good ideas from SHOKKER \u25b8 ATMOSPHERE "
             "came across and <b>that category is retired</b>, as you asked.")),
    "nightshift": dict(
        build=_lane_nightshift, accent="#c94fd6",
        title=('<span class="flag">\U0001f317 FRACTURED NIGHTSHIFT</span> \u2014 Round 1 Audit '
               '<span style="color:var(--dim);font-weight:400">(101 \u2192 50)</span>'),
        sub=("Your words: <i>\u201cthis was supposed to make cars change hues between day and night "
             "and not JUST blow it out to white, but this category did NOT live up to the "
             "hype.\u201d</i> You were right, and it is now measured rather than asserted. Metals "
             "tint their reflection with their own albedo and kill diffuse; dielectric and "
             "clearcoat highlights stay white. So each of these 50 carries <b>two populations</b> "
             "\u2014 a matte dielectric that owns the daylight in hue A, and a chrome-tier metal "
             "that owns the night in hue B \u2014 interleaved at 8\u201332px so the car changes "
             "colour rather than changing brightness. The old 101 scored a <b>median hue swing of "
             "0.000</b>; these 50 score 0.123, with a median dominant-hue change of 150\u00b0.")),
    "paradigm": dict(
        build=_lane_paradigm, accent="#8f9bb3",
        title=('<span class="flag">\u25c8 PARADIGM</span> \u2014 Round 1 Audit '
               '<span style="color:var(--dim);font-weight:400">(34 \u2192 50)</span>'),
        sub=("Your words: <i>\u201cour original Shokker design system which now feels ancient... "
             "redesign this entire category and expand it from 35 to 50. Give it it\u2019s OWN "
             "unique feel somehow.\u201d</i> The 34 had no shared idea \u2014 some physics, some "
             "weather, some materials \u2014 and several duplicated the categories rebuilt "
             "overnight (Hypercane and Seismic are ELEMENTS now, Wormhole and Event Horizon are "
             "COSMOS, Volcanic and Ember are FLAMES). <b>The new idea: a PARADIGM finish argues "
             "with itself.</b> Each one shows you a substance you know on sight \u2014 hessian, "
             "moss, corduroy, cracked concrete, kraft paper, rust \u2014 and then behaves like "
             "something it absolutely is not. The weave is real and it is machined out of mercury. "
             "This is the one thing SPB can do that a texture pack cannot: paint and spec are "
             "separate channels, so a surface can LOOK like one material and BEHAVE like another. "
             "The spec still follows the artwork\u2019s geometry exactly; only the substance lies. "
             "Five chapters: \u2b22 WOVEN \u00b7 \u2b23 GROWN \u00b7 \u2b21 MINERAL \u00b7 "
             "\u2b20 MADE \u00b7 \u2b1f RUINED. Gated on ARGUE \u2014 the distance in the M/R/Cc "
             "cube between the material the substance implies and the one it was given.")),
    "mortalshokk": dict(
        build=_lane_mortalshokk, accent="#e0364f",
        title=('<span class="flag">\u2620 MORTAL SHOKK</span> \u2014 Spec Rebuild Audit '
               '<span style="color:var(--dim);font-weight:400">(26 finishes, 26 new spec maps)'
               '</span>'),
        sub=("Your brief: <b>keep all 26 finishes, rebuild every spec map with the new math</b>, "
             "still following the base paint\u2019s design, every one unique \u2014 <i>\u201clike MS "
             "Zero Hour, it has the steel grey with crisis veins; this one should have a frozen "
             "look in the spec but with the hot pink (fractured) highlights and some other specs "
             "in there too.\u201d</i> The paint is untouched. Each spec now reads the artwork into "
             "six roles \u2014 void, ground, figure, vein, hot, flash \u2014 from a "
             "structure-weighted luma+chroma field with adaptive histogram cuts, then deals a "
             "<b>complete material card</b> to each role from the shared deck. Zero Hour is frozen "
             "metal ground, gunmetal figure, crisis veins ignited to the Fractured carrier, chrome "
             "at the breaks. No two of the 26 use the same role assignment.")),
}


def run(lane):
    cfg = LANES[lane]
    built = cfg["build"]()
    era_mod = None
    if len(built) == 3:
        rows, prog, era_mod = built
    else:
        rows, prog = built
    thumbs = os.path.join(ROOT, "thumbnails", "audit", lane)
    os.makedirs(thumbs, exist_ok=True)
    times = measured(prog)
    meta = []
    for fid, name, desc in rows:
        if era_mod is not None:                       # BASE contract
            paint_fn = getattr(era_mod, "paint_" + fid)
            sf = getattr(era_mod, "spec_" + fid)
            t0 = time.time()
            p = paint_fn(BASE.copy(), SHAPE, MASK, 51, 1.0, None)
            _M, _R, _C = sf(SHAPE, 51, 1.0, 60, 28)
            s = np.dstack([_M, _R, _C])
        else:
            spec_fn, paint_fn = eng.MONOLITHIC_REGISTRY[fid]
            t0 = time.time()
            p = paint_fn(BASE.copy(), SHAPE, MASK, 51, 1.0, None)
            s = spec_fn(SHAPE, MASK, 51, 1.0)
        dt = times.get(fid) or (time.time() - t0)
        p8 = np.clip(np.asarray(p, np.float32) * 255.0, 0, 255).astype(np.uint8)
        s8 = np.asarray(s)[..., :3].astype(np.uint8)
        c0 = (2048 - PANEL) // 2
        imgs = {"full": cv2.resize(p8, (PANEL, PANEL), interpolation=cv2.INTER_AREA),
                "crop": p8[c0:c0 + PANEL, c0:c0 + PANEL],
                "spec": s8[c0:c0 + PANEL, c0:c0 + PANEL]}
        tile = np.full((PANEL + 26, PANEL * 3 + 16, 3), 14, np.uint8)
        for i, (lab, key) in enumerate(PANELS):
            x0 = i * (PANEL + 8)
            tile[26:26 + PANEL, x0:x0 + PANEL] = imgs[key]
            cv2.putText(tile, lab, (x0 + 4, 18), cv2.FONT_HERSHEY_SIMPLEX, .5,
                        (200, 200, 200), 1)
        cv2.imwrite(os.path.join(thumbs, fid + ".png"), tile[..., ::-1])
        meta.append({"id": fid, "name": name, "kind": "finish",
                     "render_s": round(float(dt), 2), "desc": desc})
        print("%s %.2fs" % (fid, dt), flush=True)
    out = os.path.join(ROOT, "SPB_AUDIT_%s.html" % lane)
    build_page(lane, cfg["title"], cfg["sub"] + LEGEND, meta, thumbs, out,
               accent=cfg["accent"])
    print("PAGE OK %s (%d cards)" % (os.path.basename(out), len(meta)))


LEGEND = (" &nbsp;&mdash;&nbsp; LEFT = full 2048 view \u00b7 MIDDLE = true 1:1 on-car pixel crop "
          "(<b>judge the finish here</b>) \u00b7 RIGHT = the spec map at 1:1. "
          "\u23f1 = full-size render (all \u2264 3s).")


if __name__ == "__main__":
    for lane in (sys.argv[1:] or list(LANES)):
        run(lane)
