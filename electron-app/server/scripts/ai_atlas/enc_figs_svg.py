"""Encyclopedia v2 lane D - the 20 SVG explainer diagrams (g01..g20).

    python scripts/ai_atlas/enc_figs_svg.py            # build all, merge manifest
    python scripts/ai_atlas/enc_figs_svg.py g03 g18    # only these ids
    python scripts/ai_atlas/enc_figs_svg.py --png      # also write review PNGs via Edge headless

Pure string templates, no engine boot. Every number comes from code through src()/reg()
so it carries a verified "file:line". Dark theme = the app's tokens (enc_figs_lib.C).
Diagrams g11-g20 live in enc_figs_svg2.py (same decorator).
"""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import enc_figs_lib as L  # noqa: E402
from enc_figs_lib import C, Svg, figure, reg, src  # noqa: E402

diagram, _title, _lin = L.diagram, L.title, L.lin
DIAGRAMS = L.DIAGRAMS


# ------------------------------------------------------------------ g01
@diagram("g01_spec_channels")
def g01():
    s = Svg(640)
    y0 = _title(s, "The spec map: four channels per pixel",
                "Next to your paint, iRacing reads a second picture. Each pixel carries four numbers from 0 to 255.")
    cards = [
        ("R", "Metallic", C["R"], "0 = plain paint", "255 = metal / chrome", "More metal makes the body colour flash harder."),
        ("G", "Roughness", C["G"], "0 = perfect mirror", "255 = flat matte", "Low = sharp mirror flashes. High = soft satin glow."),
        ("B", "Clearcoat", C["B"], "0 = no coat", "255 = dull", "Backwards on purpose: a smaller number is a glossier coat. 0 means no coat at all."),
        ("A", "Spec mask", C["A"], "0 = transparent", "255 = active pixel", "Follows your zones. You never paint this one by hand."),
    ]
    cw, ch, gap = 305, 192, 14
    for i, (letter, name, col, lo, hi, note) in enumerate(cards):
        x = 12 + (i % 2) * (cw + gap)
        y = y0 + (i // 2) * (ch + gap)
        s.card(x, y, cw, ch, accent=col)
        s.circle(x + 36, y + 34, 18, col)
        s.text(x + 36, y + 41, letter, 22, "#0b0e17", "middle", True)
        s.text(x + 66, y + 41, name, 19, C["hi"], bold=True)
        gid = f"gr{i}"
        _lin(s, gid, "#000000" if letter != "A" else "#2a2f3f", col)
        s.rect(x + 18, y + 76, cw - 36, 20, f"url(#{gid})", C["line"], 1, r=4)
        if letter == "B":  # tick at 16
            tx = x + 18 + (cw - 36) * 16 / 255
            s.line(tx, y + 70, tx, y + 102, C["gold"], 2.5)
            s.text(tx + 6, y + 68, "16 = MAX gloss", 13, C["gold"], bold=True)
        s.text(x + 18, y + 118, lo, 14, C["text"])
        s.text(x + cw - 18, y + 118, hi, 14, C["text"], anchor="end")
        if note:
            s.para(x + 18, y + 144, note, cw - 36, 13, C["dim"], 1.3)
    yb = y0 + 2 * ch + gap + 26
    s.para(16, yb, "It is data, not colour. Seen on screen the spec map looks odd (chrome shows bright red, gloss shows dark green-black) "
                   "only because the four numbers are packed into red, green, blue and alpha.", s.w - 32, 14, C["dim"])
    srcs = [src("shokker_engine_v2.py", r"SPEC-MAP CHANNEL SEMANTICS"), src("shokker_engine_v2.py", r"R = Metallic"),
            src("shokker_engine_v2.py", r"B = Clearcoat"), src("shokker_engine_v2.py", r"A = Spec mask"),
            src("engine/SPEC_MAP_REFERENCE.md", r"Clearcoat \(blue\)"), src("scripts/ai_atlas/ui_map.json", r"A Mask")]
    figure("g01_spec_channels", "The spec map: four channels",
           "The spec map is a second picture iRacing reads next to your paint. Red is metal, green is roughness (0 is a mirror), "
           "blue is clearcoat (16 is the glossiest, bigger is duller) and alpha is the mask that follows your zones.",
           srcs, "Four cards for the spec map channels. R metallic from 0 plain paint to 255 bare metal. G roughness from 0 mirror to 255 matte. "
                 "B clearcoat where 16 is maximum gloss and 255 is dull. A spec mask from 0 transparent to 255 active.")
    return s


# ------------------------------------------------------------------ g02
@diagram("g02_roughness_scale")
def g02():
    s = Svg(640)
    y0 = _title(s, "G = Roughness: from mirror to matte",
                "The lower the green number, the sharper the reflection.")
    x0, x1, yb = 40, 600, y0 + 96
    X = lambda v: x0 + v / 255 * (x1 - x0)  # noqa: E731
    _lin(s, "rg", "#04100a", C["G"])
    s.rect(x0, yb, x1 - x0, 26, "url(#rg)", C["line"], 1, r=4)
    stops = [("Chrome", "f_chrome"), ("Gloss", "gloss"), ("Satin", "satin"), ("Soft matte", "f_soft_matte")]
    srcs = [src("engine/SPEC_MAP_REFERENCE.md", r"Green \(R\)"), src("shokker_engine_v2.py", r"ROUGHNESS_FLOOR_NONMIRROR = 15")]
    for name, fid in stops:
        m, r, cc, so = reg(fid)
        srcs.append(so)
        cx = X(r)
        sid = s.gid("sp")
        blur = 0.4 + r / 255 * 11
        s.defs(f'<radialGradient id="{sid}b" cx="0.4" cy="0.35" r="0.8"><stop offset="0" stop-color="#6b7488"/><stop offset="1" stop-color="#1a1e2c"/></radialGradient>'
               f'<filter id="{sid}f" x="-60%" y="-60%" width="220%" height="220%"><feGaussianBlur stdDeviation="{blur:.1f}"/></filter>'
               f'<clipPath id="{sid}c"><circle cx="{cx:.1f}" cy="{yb - 50}" r="26"/></clipPath>')
        s.circle(cx, yb - 50, 26, f"url(#{sid}b)")
        hr = 5 + r / 255 * 20
        op = max(0.30, 1 - r / 255 * 0.7)
        s.raw(f'<g clip-path="url(#{sid}c)"><ellipse cx="{cx - 8:.1f}" cy="{yb - 59}" rx="{hr:.1f}" ry="{hr * 0.8:.1f}" fill="#ffffff" opacity="{op:.2f}" filter="url(#{sid}f)"/></g>')
        s.line(cx, yb - 22, cx, yb, C["dim"], 1.5)
        s.circle(cx, yb + 13, 6, C["gold"], C["bg"], 2)
        s.text(cx, yb + 56, name, 14, C["hi"], "middle", True)
        s.text(cx, yb + 74, f"G = {r}", 14, C["G"], "middle", True)
    for v in (0, 64, 128, 192, 255):
        s.line(X(v), yb + 26, X(v), yb + 32, C["dim"], 1.5)
    s.text(x0, yb + 112, "0", 13, C["dim"], bold=True)
    s.text(x1, yb + 112, "255", 13, C["dim"], anchor="end", bold=True)
    s.text(x0 + 24, yb + 112, "mirror, sharp reflections", 13, C["dim"])
    s.text(x1 - 30, yb + 112, "flat, soft glow", 13, C["dim"], anchor="end")
    # floor note
    yn = yb + 134
    s.card(14, yn, 612, 96, accent=C["orange"])
    s.text(32, yn + 28, "The floor of 15", 16, C["hi"], bold=True)
    s.para(32, yn + 50, "Any pixel that is not a mirror metal (metallic below 240) is held at roughness 15 or higher. "
                        "Only true chrome-level metal may go lower, down to 0.", 580, 14, C["text"])
    figure("g02_roughness_scale", "Roughness scale",
           "Roughness runs from 0 (a perfect mirror) to 255 (flat matte). Chrome sits near 2, gloss near 30, satin near 95, soft matte near 200. "
           "Only mirror-level metal may go below 15.",
           srcs, "A bar from mirror on the left to matte on the right with four spheres whose highlight gets softer: Chrome G 2, Gloss G 30, Satin G 95, Soft matte G 200.")
    return s


# ------------------------------------------------------------------ g03
@diagram("g03_clearcoat_scale")
def g03():
    s = Svg(640)
    y0 = _title(s, "B = Clearcoat is backwards",
                "A smaller number is a glossier coat. 16 is the best you can ask for.")
    x0, x1, yb = 30, 610, y0 + 96
    X = lambda v: x0 + v / 255 * (x1 - x0)  # noqa: E731
    _lin(s, "cg", "#7fa6ff", "#1a2038")
    s.rect(X(16), yb, x1 - X(16), 28, "url(#cg)", C["line"], 1)
    s.defs(f'<pattern id="hatch" width="7" height="7" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="7" height="7" fill="#2a0d17"/><line x1="0" y1="0" x2="0" y2="7" stroke="{C["bad"]}" stroke-width="3"/></pattern>')
    s.rect(X(1), yb, X(16) - X(1), 28, "url(#hatch)", C["bad"], 1)
    s.rect(X(0) - 2, yb, 4, 28, C["text"])
    s.rect(X(16) - 1.5, yb - 4, 3, 36, C["gold"])
    # callouts above: longest leader belongs to the leftmost mark so no text crosses a leader
    s.line(X(0), yb - 84, X(0), yb, C["text"], 1.5)
    s.text(X(0) + 8, yb - 82, "0 = no coat at all (valid)", 14, C["text"])
    s.line(X(8), yb - 56, X(8), yb, C["bad"], 1.5)
    s.text(X(8) + 8, yb - 54, "1 to 15 = never use", 14, C["bad"], bold=True)
    s.line(X(16), yb - 30, X(16), yb - 4, C["gold"], 1.5)
    s.text(X(16) + 8, yb - 28, "16 = MAX GLOSS", 15, C["gold"], bold=True)
    srcs = [src("shokker_engine_v2.py", r"B = Clearcoat"), src("shokker_engine_v2.py", r"CC_FLOOR = 16"),
            src("engine/SPEC_MAP_REFERENCE.md", r"16 = max active clearcoat"), src("engine/SPEC_MAP_REFERENCE.md", r"1.15 = no-coat")]
    names = [("Gloss", "gloss"), ("Satin", "satin"), ("Soft matte", "f_soft_matte")]
    for nm, fid in names:
        m, r, cc, so = reg(fid)
        srcs.append(so)
        cx = X(cc)
        s.circle(cx, yb + 14, 5, C["gold"] if cc == 16 else C["B"], C["bg"], 2)
        s.text(cx, yb + 52, nm, 14, C["hi"], "middle", True)
        s.text(cx, yb + 70, f"CC {cc}", 14, C["B"], "middle", True)
    ya = yb + 98
    s.arrow(X(24), ya, x1 - 4, ya, C["dim"], 2)
    s.text(X(24), ya + 22, "bigger number = less gloss", 14, C["dim"])
    s.text(x1, ya + 22, "255 = dull", 14, C["dim"], anchor="end", bold=True)
    row = ya + 24
    s.card(14, row + 22, 612, 100, accent=C["bad"])
    s.text(32, row + 50, "Iron rule", 16, C["hi"], bold=True)
    s.para(32, row + 72, "Anywhere there is paint, clearcoat must be 16 or more, or exactly 0. "
                         "Values 1 to 15 blow out to white in iRacing, so Shokker raises them to 16.", 580, 14, C["text"])
    figure("g03_clearcoat_scale", "Clearcoat scale (backwards)",
           "Clearcoat is backwards: 16 is the glossiest coat and the number gets duller as it goes up to 255. 0 means no coat. "
           "Never use 1 to 15; Shokker lifts those to 16.",
           srcs, "A bar from 0 to 255. 0 is no coat, 1 to 15 is hatched red as never use, 16 is marked MAX GLOSS and 17 to 255 fades to dull. "
                 "Gloss is 16, satin 70, soft matte 165 (catalogue values).")
    return s


# ------------------------------------------------------------------ g04
@diagram("g04_metal_rough_grid")
def g04():
    s = Svg(640)
    y0 = _title(s, "Metal x roughness: where real finishes live",
                "Every material is a point on this map. Gloss paint and chrome are opposite corners.")
    px0, px1, py0, py1 = 74, 612, y0 + 8, y0 + 338
    X = lambda r: px0 + r / 255 * (px1 - px0)  # noqa: E731
    Y = lambda m: py1 - m / 255 * (py1 - py0)  # noqa: E731
    s.rect(px0, py0, px1 - px0, py1 - py0, C["inset"], C["line"], 1.2)
    # mirror-metal band M>=240 and no-go strip
    s.rect(px0, Y(255), px1 - px0, Y(240) - Y(255), "#13261e", None, 0)
    s.defs(f'<pattern id="hatch2" width="7" height="7" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="7" height="7" fill="#1c0b13"/><line x1="0" y1="0" x2="0" y2="7" stroke="{C["bad"]}" stroke-width="2.5"/></pattern>')
    s.rect(X(0), Y(239), X(15) - X(0), py1 - Y(239), "url(#hatch2)", C["bad"], 1)
    for v in (0, 64, 128, 192, 255):
        s.line(X(v), py1, X(v), py1 + 6, C["dim"], 1.5)
        s.text(X(v), py1 + 22, str(v), 13, C["dim"], "middle", True)
        s.line(px0 - 6, Y(v), px0, Y(v), C["dim"], 1.5)
        s.text(px0 - 10, Y(v) + 5, str(v), 13, C["dim"], "end", True)
        if v not in (0, 255):
            s.line(X(v), py0, X(v), py1, "#1b2133", 1)
            s.line(px0, Y(v), px1, Y(v), "#1b2133", 1)
    s.text((px0 + px1) / 2, py1 + 44, "G Roughness  (mirror  <-  0 ... 255  ->  matte)", 14, C["G"], "middle", True)
    s.raw(f'<text transform="translate(18,{(py0 + py1) / 2:.0f}) rotate(-90)" text-anchor="middle" font-family="{L.FONT}" font-size="14" font-weight="700" fill="{C["R"]}">R Metallic  (paint -> metal)</text>')
    pts = [("Chrome", "f_chrome", 12, -10), ("Satin chrome", "f_satin_chrome", 12, 20), ("Metallic", "f_metallic", 12, 5), ("Brushed", "f_brushed", 12, 5),
           ("Pearl", "f_pearl", 12, 5), ("Gloss", "gloss", 10, -12), ("Satin", "satin", 10, -12), ("Soft matte", "f_soft_matte", -10, -12)]
    srcs = [src("shokker_engine_v2.py", r"Where M < 240"), src("shokker_engine_v2.py", r"CHROME_M_THRESHOLD = 240"),
            src("shokker_engine_v2.py", r"ROUGHNESS_FLOOR_NONMIRROR = 15")]
    for nm, fid, dx, dy in pts:
        m, r, cc, so = reg(fid)
        srcs.append(so)
        cx, cy = X(r), Y(m)
        s.circle(cx, cy, 7, C["gold"], C["bg"], 2)
        s.text(cx + dx, cy + dy + (4 if dy > -12 else 0), nm, 14, C["hi"], "end" if dx < 0 else "start", True)
    s.text(px0 + 40, py0 + 36, "mirror metal", 13, C["dim"], italic=True)
    s.text(px1 - 8, py0 + 36, "rough metal", 13, C["dim"], "end", italic=True)
    s.text(px0 + 40, py1 - 70, "wet gloss paint", 13, C["dim"], italic=True)
    s.text(px1 - 8, py1 - 8, "flat matte paint", 13, C["dim"], "end", italic=True)
    yl = py1 + 62
    s.rect(16, yl, 16, 16, "url(#hatch2)", C["bad"], 1)
    s.text(40, yl + 13, "Not allowed: roughness under 15 on anything below metal 240", 13, C["text"])
    s.rect(16, yl + 24, 16, 16, "#13261e", C["line"], 1)
    s.text(40, yl + 37, "Mirror metals (metal 240 or more) may go all the way to roughness 0", 13, C["text"])
    figure("g04_metal_rough_grid", "Metal x roughness map",
           "Metal on the vertical, roughness across. Chrome is top-left, wet gloss paint bottom-left, matte paint bottom-right. "
           "The red strip is off limits: below roughness 15 only mirror metals are allowed.",
           srcs, "A plot with metallic up the side and roughness along the bottom. Chrome sits top left at 255 and 2, gloss bottom left, soft matte bottom right, "
                 "with brushed, metallic, satin chrome and pearl between. A hatched strip marks the roughness-under-15 no-go zone.")
    return s


# ------------------------------------------------------------------ g18
@diagram("g18_iron_rules")
def g18():
    s = Svg(640)
    y0 = _title(s, "The three iron rules",
                "Shokker applies these to every spec map it makes, so a render cannot break them by accident.")
    srcs = [src("shokker_engine_v2.py", r"IRON RULES"), src("shokker_engine_v2.py", r"CC must be >= 16"),
            src("shokker_engine_v2.py", r"Where M < 240"), src("shokker_engine_v2.py", r"The alpha \(spec mask\)"),
            src("shokker_engine_v2.py", r"def _enforce_iron_rules"), src("shokker_engine_v2.py", r"CC_FLOOR = 16"),
            src("shokker_engine_v2.py", r"ROUGHNESS_FLOOR_NONMIRROR = 15"), src("shokker_engine_v2.py", r"CHROME_M_THRESHOLD = 240")]
    y = y0
    # rule 1
    s.card(14, y, 612, 128, accent=C["B"])
    s.text(32, y + 28, "1   Clearcoat is 16 or more (or exactly 0)", 17, C["hi"], bold=True)
    bx0, bx1 = 32, 600
    X = lambda v: bx0 + v / 255 * (bx1 - bx0)  # noqa: E731
    s.rect(X(0) - 2, y + 48, 4, 22, C["good"])
    s.defs(f'<pattern id="hatch3" width="7" height="7" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="7" height="7" fill="#1c0b13"/><line x1="0" y1="0" x2="0" y2="7" stroke="{C["bad"]}" stroke-width="2.5"/></pattern>')
    s.rect(X(1), y + 48, X(16) - X(1), 22, "url(#hatch3)", C["bad"], 1)
    s.rect(X(16), y + 48, bx1 - X(16), 22, C["B"], None, 0, extra='opacity="0.55"')
    s.text(X(0) + 10, y + 90, "0 ok", 13, C["good"], bold=True)
    s.text(X(8) + 28, y + 90, "1-15 raised to 16", 13, C["bad"], bold=True)
    s.text(X(16) + 150, y + 90, "16 to 255 ok", 13, C["B"], anchor="start", bold=True)
    s.text(32, y + 114, "The values 1 to 15 whiten the paint in iRacing's shader.", 13, C["dim"])
    y += 142
    # rule 2
    s.card(14, y, 612, 150, accent=C["G"])
    s.text(32, y + 28, "2   Roughness is 15 or more, unless it is a mirror metal", 17, C["hi"], bold=True)
    chips = [("Gloss paint", "M 0 / G 30", "stays 30", C["good"]), ("Chrome", "M 255 / G 2", "stays 2 (mirror metal)", C["good"]),
             ("Too low (example)", "M 100 / G 5", "raised to 15", C["bad"])]
    for k, (a, b, c, col) in enumerate(chips):
        x = 32 + k * 196
        s.rect(x, y + 46, 184, 70, C["raised"], C["line"], 1, r=8)
        s.text(x + 10, y + 68, a, 14, C["hi"], bold=True)
        s.text(x + 10, y + 88, b, 13, C["dim"], mono=True)
        s.text(x + 10, y + 108, c, 13, col, bold=True)
    s.text(32, y + 138, "Mirror metal means metallic 240 or higher.", 13, C["dim"])
    y += 164
    # rule 3
    s.card(14, y, 612, 92, accent=C["A"])
    s.text(32, y + 28, "3   The spec mask follows your zones", 17, C["hi"], bold=True)
    s.para(32, y + 52, "Alpha comes from the union of your zone areas. It is not something you paint by hand.", 580, 14, C["text"])
    figure("g18_iron_rules", "The three iron rules",
           "Clearcoat is 16 or more (or exactly 0). Roughness is at least 15 unless the surface is a mirror metal (metal 240 or more). "
           "The spec mask follows your zones. Shokker enforces the first two for you.",
           srcs, "Three cards. One: clearcoat 1 to 15 is not allowed and is raised to 16. Two: roughness has a floor of 15 except for mirror metals. Three: the spec mask follows the zones.")
    return s


# ------------------------------------------------------------------ g09
@diagram("g09_render_export_flow")
def g09():
    s = Svg(640)
    y0 = _title(s, "From Render to iRacing in five steps")
    steps = [
        ("1", "Press RENDER in Shokker", "Needs your iRacing User ID and your car chosen in iRacing Car Folder."),
        ("2", "Two files are written", "car_num_<ID>.tga (or car_<ID>.tga) is the paint. car_spec_<ID>.tga is the shine."),
        ("3", "They are copied into your iRacing paint folder", "Documents\\iRacing\\paint\\<car folder>\\  If no car folder is set, nothing reaches iRacing."),
        ("4", "Alt+Tab to iRacing", "Be in a session with your car. In a replay, pick a moment when you are not in the pits."),
        ("5", "Press Ctrl+R (Reload Car Textures)", "The car flashes white and shows the new paint. No restart needed."),
    ]
    y = y0
    bh = 82
    for i, (n, t, d) in enumerate(steps):
        s.card(14, y, 612, bh, accent=C["orange"])
        s.circle(46, y + 41, 17, C["orange"])
        s.text(46, y + 48, n, 18, "#0b0e17", "middle", True)
        s.text(78, y + 30, t, 16, C["hi"], bold=True)
        s.para(78, y + 52, d, 535, 14, C["dim"])
        if i < len(steps) - 1:
            s.arrow(46, y + bh + 1, 46, y + bh + 15, C["orange"], 2.5)
        y += bh + 16
    figure("g09_render_export_flow", "Render to iRacing",
           "Render in Shokker, the paint and spec files are copied into your iRacing car folder, then Alt+Tab to iRacing and press Ctrl+R. "
           "If no car folder is set, the files are not copied anywhere iRacing can see.",
           [src("js/spb-support-answers.js", r"How to get your paint into iRacing"), src("js/spb-support-answers.js", r"Making iRacing show the new paint"),
            src("js/spb-support-answers.js", r"Where the files go"), src("server.py", r'car_prefix = "car_num"')],
           "Five stacked steps: press Render, two TGA files are written, they are copied to the iRacing paint folder, Alt+Tab to iRacing, press Ctrl+R.")
    return s


# ------------------------------------------------------------------ g10
@diagram("g10_file_naming")
def g10():
    s = Svg(640)
    y0 = _title(s, "car_num_ or car_ ? Two number modes",
                "There is no place to type a car number in Shokker. These switches only pick the file name.")
    cw = 300
    cols = [
        ("Custom Number", "car_num_<ID>.tga", "Your paint carries its own number.", "iRacing loads it when Graphics > Hide Car Numbers is ON.", C["orange"]),
        ("Sim-Stamped Number", "car_<ID>.tga", "iRacing stamps your number and sponsors on top.", "iRacing loads it by default (Hide Car Numbers OFF).", C["cyan"]),
    ]
    for i, (h, f, a, b, col) in enumerate(cols):
        x = 14 + i * (cw + 12)
        s.card(x, y0, cw, 212, accent=col)
        s.text(x + 18, y0 + 30, h, 18, C["hi"], bold=True)
        s.rect(x + 18, y0 + 46, cw - 36, 38, C["inset"], col, 1.5, r=6)
        s.text(x + cw / 2, y0 + 71, f, 16, col, "middle", True, mono=True)
        yy = s.para(x + 18, y0 + 112, a, cw - 36, 14, C["text"])
        s.para(x + 18, yy + 8, b, cw - 36, 14, C["dim"])
    yy = y0 + 228
    s.card(14, yy, 612, 62, accent=C["good"])
    s.text(32, yy + 26, "Both modes also write", 14, C["text"])
    s.text(212, yy + 26, "car_spec_<ID>.tga", 15, C["good"], bold=True, mono=True)
    s.text(380, yy + 26, "(the shine)", 14, C["text"])
    s.text(32, yy + 50, "The paint tells iRacing the colour. The spec file tells it how shiny.", 13, C["dim"])
    yy += 76
    s.card(14, yy, 612, 94, accent=C["bad"])
    s.text(32, yy + 28, "The switch and the iRacing setting must agree", 16, C["hi"], bold=True)
    s.para(32, yy + 50, "If they do not, iRacing finds no file and quietly shows your paint-shop colours. Not sure? Render once in each mode: "
                        "both files stay in the folder and iRacing picks the right one.", 580, 14, C["text"])
    figure("g10_file_naming", "car_num_ vs car_",
           "Custom Number writes car_num_ID.tga and iRacing loads it when Hide Car Numbers is on. Sim-Stamped Number writes car_ID.tga, the iRacing default. "
           "The Shokker switch and the iRacing setting must agree.",
           [src("js/spb-support-answers.js", r"Custom Number vs Sim-Stamped Number"), src("server.py", r'car_prefix = "car_num"'),
            src("server.py", r"car_num_ \(custom numbers\)")],
           "Two cards. Custom Number writes car_num_ID.tga and needs Hide Car Numbers ON. Sim-Stamped Number writes car_ID.tga, the default. Both also write car_spec_ID.tga.")
    return s


# ------------------------------------------------------------------ main
def main(argv):
    import enc_hidden as H  # noqa: F401
    globals()["H"] = H
    import enc_figs_svg2  # noqa: F401  (registers g05..g08, g11..g17, g19, g20)
    want = [a for a in argv if not a.startswith("--")]
    ids = [i for i in sorted(DIAGRAMS) if not want or any(i.startswith(w) for w in want)]
    for fid in ids:
        L.FIGS[:] = [f for f in L.FIGS if f["id"] != fid]
        s = DIAGRAMS[fid]()
        ent = [f for f in L.FIGS if f["id"] == fid][0]
        svg = s.render(ent["title"], ent["alt"])
        # owner rule 2026-10-04: hidden features (enc_hidden_features.json) must never reach a figure
        if H.mentions(svg) or H.mentions(ent["title"] + " " + ent["alt"] + " " + str(ent.get("caption", ""))):
            raise SystemExit(f"{fid}: figure text names a hidden feature (see enc_hidden_features.json)")
        p = L.save_svg(fid, svg)
        print(f"{fid}: {len(svg)//1024 + 1} KB h={s.maxy:.0f} warns={len(s.warn)}" + ("  " + "; ".join(s.warn[:3]) if s.warn else ""))
    n = L.write_manifest("g")
    print(f"manifest entries total: {n}")
    if "--png" in argv:
        png_review(ids)


def png_review(ids):
    edge = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    outd = Path(L.ROOT) / "_enc_work" / "review"
    outd.mkdir(parents=True, exist_ok=True)
    for fid in ids:
        svg = L.OUT / f"{fid}.svg"
        h = int(__import__("re").search(r'height="(\d+)"', svg.read_text(encoding="utf8")).group(1))
        subprocess.run([edge, "--headless", "--disable-gpu", "--hide-scrollbars", f"--screenshot={outd / (fid + '.png')}",
                        f"--window-size=640,{h}", "--force-device-scale-factor=1", svg.as_uri()],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60)
    print("review pngs in", outd)


if __name__ == "__main__":
    main(sys.argv[1:])
