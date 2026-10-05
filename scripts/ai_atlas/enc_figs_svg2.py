"""Encyclopedia v2 lane D - diagrams g05-g08 (zones, layers, UV sheet) and g11-g17, g19, g20.
Registered into enc_figs_lib.DIAGRAMS; run through enc_figs_svg.py."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import enc_figs_lib as L  # noqa: E402
from enc_figs_lib import C, Svg, figure, reg, src  # noqa: E402

diagram, _title, _lin = L.diagram, L.title, L.lin


def ui(i):
    return src("scripts/ai_atlas/ui_map.json", r'"id": "%s"' % i.replace(".", r"\."))


def ac(i):
    return src("scripts/ai_atlas/app_controls.json", r'"id": "%s"' % i)


def hatch(s, pid, bg="#1c0b13", fg=None):
    fg = fg or C["bad"]
    s.defs(f'<pattern id="{pid}" width="7" height="7" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
           f'<rect width="7" height="7" fill="{bg}"/><line x1="0" y1="0" x2="0" y2="7" stroke="{fg}" stroke-width="2.5"/></pattern>')


# ------------------------------------------------------------------ g05
@diagram("g05_zone_priority")
def g05():
    s = Svg(640)
    y0 = _title(s, "Zones: the one on top wins",
                "Where two zones both claim a pixel, the higher one gets it. Lower number = stronger.")
    # left stack
    x, w = 14, 292
    zones = [("Zone 1", "Hood stripe", C["orange"], "wins every overlap"),
             ("Zone 2", "Body colour", C["cyan"], "wins what Zone 1 leaves"),
             ("Everything Else", "Remaining (catch-all)", C["dim"], "always last: gets only what nobody above claims")]
    y = y0
    for i, (n, d, col, note) in enumerate(zones):
        h = 100 if i < 2 else 112
        s.card(x, y, w, h, accent=col)
        s.text(x + 18, y + 28, n, 17, C["hi"], bold=True)
        s.text(x + 18, y + 50, d, 14, col, bold=True)
        s.para(x + 18, y + 72, note, w - 34, 13, C["dim"])
        y += h + 12
    s.arrow(x + w + 10, y0 + 10, x + w + 10, y - 20, C["dim"], 2)
    # right: two mini sheets
    mx, mw, mh = 340, 286, 118

    def mini(yy, top, label):
        s.text(mx, yy, label, 14, C["hi"], bold=True)
        yy += 10
        s.rect(mx, yy, mw, mh, C["inset"], C["line"], 1.2, r=6)
        a, b = (C["orange"], C["cyan"]) if top == "A" else (C["cyan"], C["orange"])
        # A = orange box left, B = cyan box right, overlap in the middle
        s.rect(mx + 20, yy + 18, 160, 82, C["orange"], None, 0, r=4, extra='opacity="0.85"')
        s.rect(mx + 100, yy + 34, 166, 66, C["cyan"], None, 0, r=4, extra='opacity="0.85"')
        win = C["orange"] if top == "A" else C["cyan"]
        s.rect(mx + 100, yy + 34, 80, 66, win, None, 0)
        s.rect(mx + 100, yy + 34, 80, 66, "none", C["hi"], 2, extra='stroke-dasharray="5 4"')
        s.text(mx + 60, yy + 64, "Zone 1", 14, "#0b0e17", "middle", True)
        s.text(mx + 224, yy + 78, "Zone 2", 14, "#0b0e17", "middle", True)
        s.text(mx + 140, yy + 90, "overlap", 13, "#0b0e17", "middle", True)
        return yy + mh

    ya = mini(y0 + 6, "A", "Zone 1 above 2: overlap is Zone 1")
    s.text(mx + mw / 2, ya + 28, "drag a zone to swap", 13, C["dim"], "middle", italic=True)
    s.arrow(mx + mw / 2, ya + 34, mx + mw / 2, ya + 52, C["dim"], 2)
    yb = mini(ya + 74, "B", "Swapped: overlap now goes to Zone 2")
    yy = max(y, yb) + 22
    s.card(14, yy, 612, 76, accent=C["orange"])
    s.para(32, yy + 28, "Hiding a zone with its eye icon is only for testing. Zones that sit lower never get pixels a higher zone already owns.", 580, 14, C["text"])
    figure("g05_zone_priority", "Zone priority",
           "The zone higher in the list wins any pixel two zones both claim, and Everything Else only gets what nobody above it took. "
           "Drag a zone up or down to change who wins.",
           [ui("zone.order"), ui("zone.remaining"), ui("zone.mute"), src("mcp/server/index.js", r"LOWER index = higher priority")],
           "A stack of Zone 1, Zone 2 and Everything Else with a priority arrow. Two overlapping boxes show the overlap taking the colour of the higher zone, and the colour flips when the zones are swapped.")
    return s


# ------------------------------------------------------------------ g06
@diagram("g06_zone_selectors")
def g06():
    s = Svg(640)
    y0 = _title(s, "Four ways a zone picks its pixels",
                "A zone only paints what it selects. Mix them: colour or layer first, then limit by area.")
    rows = [
        ("By colour", "PICK COLOR FROM CAR", "Click a colour on the car and the zone takes every pixel of it. Tolerance: 6 = that exact shade, 30 to 50 = normal, 100 = loose.", C["orange"], "chips"),
        ("By layer", "RESTRICT TO LAYERS", "Tick layers such as Car Paint, Sponsors or Numbers. The zone only covers pixels that exist on those layers.", C["cyan"], "layers"),
        ("By drawn area", "APPLY AREA: Draw box / Lasso", "Draw a rectangle or a free-hand shape. The zone only affects what is inside it.", C["pink"], "box"),
        ("Everything else", "Remaining", "The catch-all: gets every pixel no zone above it claims.", C["dim"], "rest"),
    ]
    y = y0
    for t, ctl, d, col, ic in rows:
        h = 98
        s.card(14, y, 612, h, accent=col)
        # glyph
        gx, gy = 30, y + 18
        s.rect(gx, gy, 92, 62, C["inset"], C["line"], 1, r=6)
        if ic == "chips":
            for k, cc in enumerate(("#d62d20", "#e8e8ee", "#1b6fd1")):
                s.circle(gx + 22 + k * 24, gy + 31, 10, cc, C["hi"] if k == 0 else None, 2)
        elif ic == "layers":
            for k, cc in enumerate((C["cyan"], "#5b667e", "#3a4260")):
                s.rect(gx + 12 + k * 6, gy + 10 + k * 14, 58, 22, cc, C["bg"], 1.5, r=3, extra='opacity="0.95"')
        elif ic == "box":
            s.rect(gx + 12, gy + 10, 68, 42, "none", C["pink"], 2, extra='stroke-dasharray="5 4"')
            s.rect(gx + 22, gy + 20, 30, 22, C["pink"], None, 0, extra='opacity="0.6"')
        else:
            s.rect(gx + 6, gy + 6, 80, 50, C["dim"], None, 0, r=4, extra='opacity="0.35"')
            s.rect(gx + 6, gy + 6, 28, 50, C["orange"], None, 0, r=4)
            s.rect(gx + 34, gy + 6, 22, 24, C["cyan"], None, 0)
        s.text(138, y + 28, t, 18, C["hi"], bold=True)
        s.text(138 + tw_(t, 18) + 14, y + 28, ctl, 13, col, bold=True)
        s.para(138, y + 52, d, 470, 14, C["text"])
        y += h + 10
    s.card(14, y, 612, 74, accent=C["good"])
    s.text(32, y + 28, "Chat and the AI copilot add a fifth way", 15, C["hi"], bold=True)
    s.para(32, y + 50, "Name a part of the car: left side, right side, hood, roof, trunk or a bumper.", 580, 14, C["text"])
    figure("g06_zone_selectors", "How a zone picks pixels",
           "A zone can pick pixels by colour, by PSD layer, by a box or lasso you draw, or take everything no other zone claims. "
           "Chat and the AI copilot can also place things on named parts like the hood.",
           [ui("zone.pick_color_from_car"), ui("zone.tolerance"), ui("zone.restrict_layers"), ui("zone.draw_box"), ui("zone.lasso"),
            ui("zone.remaining"), src("mcp/server/index.js", r"NAMED PARTS")],
           "Four rows with small pictures: by colour with colour chips, by layer with stacked layers, by drawn area with a dashed box, and everything else as the catch-all, plus a note about named parts.")
    return s


def tw_(t, size):
    return L.tw(t, size, True)


# ------------------------------------------------------------------ g07
@diagram("g07_layer_stack_roles")
def g07():
    s = Svg(640)
    y0 = _title(s, "Your template's layers and what they do",
                "Layer names vary by car. The jobs are always the same.")
    px, pw = 14, 330
    s.rect(px, y0, pw, 372, C["panel"], C["line"], 1.2, r=10)
    s.text(px + 14, y0 + 24, "LAYERS", 13, C["dim"], bold=True)

    def row(y, name, on, indent=0, tag=None, col=None, group=False):
        fill = C["raised"] if not group else "#1a1426"
        s.rect(px + 8, y, pw - 16, 38, fill, C["line"], 1, r=6)
        # eye
        ex = px + 24
        if on:
            s.circle(ex, y + 19, 9, "none", C["good"], 2)
            s.circle(ex, y + 19, 3.5, C["good"])
        else:
            s.circle(ex, y + 19, 9, "none", C["faint"], 2)
            s.line(ex - 8, y + 27, ex + 8, y + 11, C["bad"], 2)
        s.text(px + 46 + indent, y + 25, name, 14, C["hi"] if on else C["dim"], bold=group)
        if tag:
            s.pill(px + pw - 16 - L.tw(tag, 13, True) - 18, y + 8, tag, 13, C["inset"], col)

    y = y0 + 36
    row(y, "Turn Off Before Exporting TGA", True, 0, None, None, True)
    s.text(px + pw - 24, y + 25, "group", 13, C["dim"], "end")
    y += 44
    for nm in ("Wire", "Mask", "Car_Mandatory"):
        row(y, nm, False, 24)
        y += 44
    y += 6
    for nm, tg in (("Numbers", None), ("Sponsors", None), ("Car Paint", None)):
        row(y, nm, True)
        y += 44
    s.text(px + 14, y + 12, "top layers cover the ones under them", 13, C["dim"], italic=True)
    # annotations
    ax = px + pw + 20
    aw = 626 - ax
    s.line(px + pw, y0 + 58, ax - 6, y0 + 58, C["bad"], 2)
    s.text(ax, y0 + 52, "Guides: switch OFF", 15, C["bad"], bold=True)
    yy = s.para(ax, y0 + 74, "Wire draws the panel outlines, Mask marks the paintable area, Car_Mandatory is the template's own guide.", aw, 13, C["text"])
    s.para(ax, yy + 2, "Left on, they are baked into your paint: grid lines and grey masks on the car.", aw, 13, C["bad"])
    s.line(px + pw, y0 + 240, ax - 6, y0 + 240, C["good"], 2)
    s.text(ax, y0 + 234, "Your art: keep ON", 15, C["good"], bold=True)
    yy = s.para(ax, y0 + 256, "These carry your paint, numbers and sponsors. Eye = show / hide.", aw, 13, C["text"])
    s.para(ax, yy + 2, "A zone can be limited to one of them (RESTRICT TO LAYERS).", aw, 13, C["dim"])
    s.card(14, y0 + 388, 612, 74, accent=C["orange"])
    s.para(32, y0 + 416, "Switch the guide layers off before you press RENDER, or they are painted into your car. One click on the eye of the group does it.", 580, 14, C["text"])
    figure("g07_layer_stack_roles", "Template layers and their jobs",
           "Guide layers such as Wire, Mask and Car_Mandatory sit under Turn Off Before Exporting TGA: switch them off before you render or they get painted into the car. "
           "Your own art layers stay on.",
           [src("js/spb-support-answers.js", r"Switch the template layers"),
            src("js/spb-pro-carmap.js", r"Mask layer \(paintable area\)"), ui("layer.eye"), ui("zone.restrict_layers")],
           "A layer list. The group Turn Off Before Exporting TGA holds Wire, Mask and Car_Mandatory, all with the eye off. Numbers, Sponsors and Car Paint have the eye on. Notes explain guides off, art on.")
    return s


# ------------------------------------------------------------------ g08
@diagram("g08_uv_sheet_parts")
def g08():
    s = Svg(640)
    y0 = _title(s, "The car cut open: one flat 2048 x 2048 sheet",
                "Every part of the car lies flat on one picture. Example: NASCAR Next Gen 2024 template.")
    d = json.loads((L.ROOT / "scripts/ai_atlas/car_atlas_clusters.json").read_text(encoding="utf8"))
    car = [c for c in d["cars"] if c["id"] == "nextgen-camry-camaro-2024"][0]
    sx, sy, ss = 40, y0 + 6, 560
    s.rect(sx, sy, ss, ss, C["inset"], C["line"], 1.5)
    cols = {"front bumper": C["cyan"], "rear bumper": C["blue"], "spoiler": C["pink"], "right side": C["orange"],
            "left side": C["gold"], "hood": C["good"], "roof": "#b07cff", "trunk": "#ff7ab6"}
    for name, p in car["parts"].items():
        x0, y0b, x1, y1 = p["box"]
        X0, Y0, W, H = sx + x0 / 100 * ss, sy + y0b / 100 * ss, (x1 - x0) / 100 * ss, (y1 - y0b) / 100 * ss
        col = cols.get(name, C["dim"])
        s.rect(X0, Y0, W, H, col, col, 1.5, r=4, extra='fill-opacity="0.22"')
        lab = name.upper()
        if W > L.tw(lab, 13, True) + 8:
            s.text(X0 + W / 2, Y0 + H / 2 + 5, lab, 13, C["hi"], "middle", True)
        else:  # tall narrow parts: rotated label
            s.raw(f'<text transform="translate({X0 + W / 2 + 5:.1f},{Y0 + H / 2:.1f}) rotate(-90)" text-anchor="middle" font-family="{L.FONT}" font-size="13" font-weight="700" fill="{C["hi"]}">{lab}</text>')
        if "front" in p:
            ar = {"left": (X0 + 8, Y0 + 14, X0 + 8 + 30, Y0 + 14), "right": (X0 + W - 38, Y0 + 14, X0 + W - 8, Y0 + 14)}[p["front"]]
            s.arrow(*ar, col, 2)
            if p["front"] == "left":
                s.text(ar[2] + 6, Y0 + 19, "front", 13, col, "start", True)
            else:
                s.text(ar[0] - 6, Y0 + 19, "front", 13, col, "end", True)
    s.text(sx, sy + ss + 22, "0", 13, C["dim"], bold=True)
    s.text(sx + ss, sy + ss + 22, "2048 px", 13, C["dim"], "end", bold=True)
    s.card(14, sy + ss + 36, 612, 96, accent=C["orange"])
    s.para(32, sy + ss + 64, "Part positions differ per car template. Shokker knows the layout of each one, so you can say left side or hood and it lands on the right panel. "
                              "Arrows show which way the front of the car points. On this template the right side is printed upside down.", 580, 14, C["text"])
    figure("g08_uv_sheet_parts", "The car laid flat",
           "The paint is one flat 2048 by 2048 picture of the whole car cut open: side panels, hood, roof, trunk, bumpers and spoiler. "
           "The layout changes from car to car; this one is the NASCAR Next Gen 2024 template.",
           [src("scripts/ai_atlas/car_atlas_clusters.json", r'"id": "nextgen-camry-camaro-2024"'), src("mcp/server/index.js", r"ONE flat 2048x2048 picture"),
            src("js/spb-pro-carmap.js", r"Mask layer \(paintable area\)")],
           "A square sheet with eight labelled boxes: front bumper, rear bumper, spoiler, right side, left side, hood, roof and trunk, with arrows showing which way the front faces.", meta={"template": "nextgen-camry-camaro-2024"})
    return s


# ------------------------------------------------------------------ g11
@diagram("g11_mip_pipeline")
def g11():
    s = Svg(640)
    y0 = _title(s, "Who makes which file",
                "Shokker writes TGA files. iRacing turns the spec into a .mip. Trading Paints wants the .mip for the spec.")
    colw = 196
    heads = [("Shokker writes", C["orange"]), ("iRacing makes", C["cyan"]), ("Trading Paints takes", C["good"])]
    items = [
        ["car_num_<ID>.tga", "or car_<ID>.tga", "(the paint)", None, "car_spec_<ID>.tga", "(the shine)"],
        ["Loads the paint", "and the spec", None, None, "car_spec_<ID>.mip", "(built next to the spec the first time it loads)"],
        ["Paint: the .tga or .png", None, None, None, "Spec: only the .mip", "(drive once in a test session first)"],
    ]
    for i, (h, col) in enumerate(heads):
        x = 12 + i * (colw + 14)
        s.card(x, y0, colw, 196, accent=col)
        s.text(x + 18, y0 + 28, h, 16, C["hi"], bold=True)
        yy = y0 + 56
        for t in items[i]:
            if t is None:
                yy += 8
                continue
            mono = t.endswith(".tga") or t.endswith(".mip") or t.endswith(".png")
            if t.startswith("("):
                yy = s.para(x + 18, yy, t, colw - 30, 13, C["dim"]) + 2
            elif mono and len(t) < 24 and not t.startswith(("Paint", "Spec")):
                s.text(x + 18, yy, t, 14, col, bold=True, mono=True)
                yy += 22
            else:
                yy = s.para(x + 18, yy, t, colw - 30, 14, C["text"]) + 2
        if i < 2:
            s.arrow(x + colw + 1, y0 + 100, x + colw + 13, y0 + 100, C["orange"], 3)
    yy = y0 + 212
    s.card(14, yy, 612, 78, accent=C["bad"])
    s.text(32, yy + 28, "Never upload the project file", 15, C["hi"], bold=True)
    s.para(32, yy + 50, "The .spb or .shokk file is your Shokker project. Only Shokker can open it. Ctrl+R in iRacing rebuilds the .mip after a new render.", 580, 14, C["text"])
    figure("g11_mip_pipeline", "TGA, .mip and Trading Paints",
           "Shokker writes the paint and spec as TGA files. iRacing builds a .mip from the spec the first time it loads it. "
           "Trading Paints takes the paint as .tga or .png but the spec only as that .mip.",
           [src("js/spb-support-answers.js", r"Which files go to Trading Paints"), src("js/spb-support-answers.js", r"the sim builds a compiled"),
            src("server.py", r"iRacing compiles paint .tga files into .mip")],
           "Three columns. Shokker writes car_num or car TGA for paint and car_spec TGA. iRacing makes car_spec MIP. Trading Paints takes the paint TGA or PNG and only the spec MIP. A warning not to upload the project file.")
    return s


# ------------------------------------------------------------------ g12
@diagram("g12_window_tour")
def g12():
    s = Svg(640)
    y0 = _title(s, "The Pro window, area by area", "Numbers match the list underneath.")
    x, y, w, h = 14, y0, 612, 360
    s.rect(x, y, w, h, C["inset"], C["line"], 1.5, r=8)

    def box(bx, by, bw, bh, n, fill=None, label=None):
        s.rect(bx, by, bw, bh, fill or C["panel"], C["line"], 1, r=4)
        if label:
            if n:
                s.text(bx + 30, by + bh / 2 + 5, label, 13, C["dim"], "start", True)
            else:
                s.text(bx + bw / 2, by + bh / 2 + 5, label, 13, C["dim"], "middle", True)
        if n:
            s.circle(bx + 14, by + 14 if bh > 30 else by + bh / 2, 11, C["orange"])
            s.text(bx + 14, (by + 19) if bh > 30 else by + bh / 2 + 5, str(n), 13, "#0b0e17", "middle", True)

    box(x + 8, y + 8, 372, 34, 1, label="ID  Number  Source  Car Folder")
    box(x + 388, y + 8, 150, 34, 2, label="PRO CHAT")
    box(x + 546, y + 8, 58, 34, 4, label="gear")
    box(x + 8, y + 50, 596, 30, 3, label="tools   ZONE / LAYER   menus   Save / Open")
    box(x + 8, y + 88, 596, 24, 9, label="tool options (change with the tool)")
    box(x + 8, y + 120, 150, 224, 5, label="ZONES")
    box(x + 166, y + 120, 142, 190, 7, label="SOURCE paint")
    box(x + 316, y + 120, 142, 168, 8, label="LIVE PREVIEW")
    box(x + 316, y + 294, 142, 22, 11, label="COMBINED R G B")
    box(x + 316, y + 320, 142, 24, 12, label="RENDER")
    box(x + 166, y + 320, 142, 24, 10, label="selection bar")
    box(x + 466, y + 120, 138, 224, 13, label="LAYER LIST")
    s.text(x + 535, y + 252, "(PSD layers)", 13, C["dim"], "middle", True)
    s.rect(x + 70, y + 240, 160, 76, "#1b2036", C["orange"], 2, r=6, extra='stroke-dasharray="6 4"')
    s.circle(x + 84, y + 254, 11, C["orange"])
    s.text(x + 84, y + 259, "6", 13, "#0b0e17", "middle", True)
    s.text(x + 104, y + 280, "zone editor", 13, C["hi"], "start", True)
    s.text(x + 104, y + 300, "(pop-out)", 13, C["dim"], "start", True)
    s.circle(x + 568, y + 334, 14, C["pink"])
    s.text(x + 568, y + 339, "AI", 13, "#0b0e17", "middle", True)
    s.circle(x + 546, y + 318, 11, C["orange"])
    s.text(x + 546, y + 323, "14", 13, "#0b0e17", "middle", True)
    items = [
        ("1", "Header: ID, Source Paint, Car Folder"), ("2", "PRO / CHAT switch"),
        ("3", "Toolbar, ZONE / LAYER switch, menus"), ("4", "Settings (gear)"),
        ("5", "ZONES list (top = strongest)"), ("6", "Zone editor pop-out (click a zone)"),
        ("7", "SOURCE: your paint file"), ("8", "LIVE PREVIEW of the car"),
        ("9", "Tool options bar"), ("10", "Selection / mask bar"),
        ("11", "Spec channel strip (R, G, B)"), ("12", "RENDER button"),
        ("13", "Layer list (right column)"), ("14", "AI copilot button (bottom right)"),
    ]
    ly = y + h + 22
    for k, (n, t) in enumerate(items):
        cx = 18 + (k % 2) * 312
        cy = ly + (k // 2) * 26
        s.circle(cx + 11, cy - 5, 11, C["orange"])
        s.text(cx + 11, cy - 0.5, n, 13, "#0b0e17", "middle", True)
        s.text(cx + 30, cy, t, 13.5, C["text"])
    figure("g12_window_tour", "The Pro window",
           "A map of the Pro window: header rows and the PRO / CHAT switch on top, the toolbar, ZONES on the left, your source paint and the live preview in the middle, "
           "the layer list on the right and the AI button bottom right.",
           [ui("pro.header"), ui("pro.modes"), ui("pro.toolbar"), ui("pro.settings"), ui("pro.zones"), ui("pro.zone_editor"), ui("pro.center"),
            ui("pro.tool_options"), ui("pro.selection_bar"), ui("pro.preview"), ui("pro.render"), ui("pro.right"), ui("pro.ai")],
           "A simplified wireframe of the Pro window with fourteen numbered areas and a legend: header rows, mode switch, toolbar, settings, zones list, zone editor, source, live preview, tool options, selection bar, spec channel strip, render button, finishes and layers tabs, and the AI button.")
    return s


# ------------------------------------------------------------------ g13
@diagram("g13_four_kinds_of_look")
def g13():
    s = Svg(640)
    y0 = _title(s, "Four kinds of look: what each one changes",
                "Colour is what you see. Shine is how it reflects. Pick the kind that changes what you want.")
    kinds = [
        ("BASE", C["orange"], "A plain material: gloss, matte, satin, chrome, candy, pearl, metallic, carbon. The colour comes from the zone's colour mode.", 1, 1),
        ("MONOLITHIC", C["pink"], "A complete special look that brings its own colour and texture. Use it for a whole effect like galaxy or hologram.", 1, 1),
        ("PATTERN", C["cyan"], "A visible pattern on top of the base: carbon weave, camo, stripes, flames. Its spec amount starts at 0, so your base shine stays.", 1, 0.5),
        ("SPEC PATTERN", C["good"], "A texture for shine only: flake, sparkle, engine-turn, weave. The colour does not change. Up to 5 can stack.", 0, 1),
    ]
    cw, ch, gap = 300, 214, 12
    for i, (nm, col, d, c_, sh) in enumerate(kinds):
        x = 14 + (i % 2) * (cw + gap)
        y = y0 + (i // 2) * (ch + gap)
        s.card(x, y, cw, ch, accent=col)
        s.text(x + 18, y + 30, nm, 18, col, bold=True)
        s.para(x + 18, y + 54, d, cw - 34, 13.5, C["text"])
        for k, (lab, v) in enumerate((("Changes colour", c_), ("Changes shine", sh))):
            yy = y + ch - 54 + k * 26
            s.text(x + 18, yy, lab, 13, C["dim"], bold=True)
            for j in range(2):
                filled = v >= (j + 1) * 0.5 if v < 1 else True
                if v == 0:
                    filled = False
                if v == 0.5:
                    filled = (j == 0)
                s.circle(x + 168 + j * 26, yy - 4, 8, col if filled else "none", col, 2)
            s.text(x + 232, yy, "yes" if v == 1 else ("a little" if v == 0.5 else "no"), 13, C["hi"] if v else C["faint"], bold=True)
    yy = y0 + 2 * ch + gap + 24
    s.card(14, yy, 612, 66, accent=C["gold"])
    s.para(32, yy + 28, "A zone can also blend a second to fifth base over the first (OVERLAYS), for example a gloss body with a pearl layer at 40%.", 580, 14, C["text"])
    figure("g13_four_kinds_of_look", "Base, monolithic, pattern, spec pattern",
           "Base finishes are plain materials. Monolithic finishes bring their own colour and texture. Patterns add a visible design on top. "
           "Spec patterns change only the shine, never the colour.",
           [src("docs/ai_knowledge/02_spec_and_finishes.md", r"## Four kinds of"), src("docs/ai_knowledge/02_spec_and_finishes.md", r"- SPEC PATTERN"),
            ui("zone.pattern_spec_amount"), ui("zone.section_overlays"), ui("zone.add_spec_overlay")],
           "Four cards. Base changes colour and shine. Monolithic changes both. Pattern changes colour and shine only a little. Spec pattern changes shine only. A note about second to fifth base overlays.")
    return s


# ------------------------------------------------------------------ g14
@diagram("g14_colour_modes")
def g14():
    s = Svg(640)
    y0 = _title(s, "Where a zone's colour comes from",
                "The BASE COLOR dropdown in a zone. Five choices.")
    rows = [
        ("Use finish's own color", "finish", "The material keeps its own colour. New zones start here.", "finish"),
        ("Use source paint (spec only)", "source", "Keeps your car's existing paint. Only the shine and texture change.", "source"),
        ("Use solid color", "solid", "One exact colour you choose, with the finish's shine on top.", "solid"),
        ("From special", "special", "Takes its colours from another special finish.", "special"),
        ("Custom gradient", "gradient", "2 to 10 colour stops fading across the zone in a direction you set.", "gradient"),
    ]
    y = y0
    for lab, key, d, ic in rows:
        h = 76
        s.card(14, y, 612, h, accent=C["orange"])
        gx, gy = 30, y + 12
        if ic == "finish":
            _lin(s, "gf", "#2d8f9b", "#a0e6d0")
            s.rect(gx, gy, 96, 52, "url(#gf)", C["line"], 1, r=6)
        elif ic == "source":
            s.rect(gx, gy, 96, 52, "#1f3b8f", C["line"], 1, r=6)
            s.rect(gx, gy + 16, 96, 8, "#e8e8ee")
            s.rect(gx, gy + 32, 96, 8, "#d62d20")
            _lin(s, "gs", "#ffffff", "#ffffff")
            s.rect(gx, gy, 96, 52, "#ffffff", None, 0, r=6, extra='opacity="0.10"')
        elif ic == "solid":
            s.rect(gx, gy, 96, 52, "#d62d20", C["line"], 1, r=6)
        elif ic == "special":
            _lin(s, "gp", "#b07cff", "#ffaa00")
            s.rect(gx, gy, 96, 52, "url(#gp)", C["line"], 1, r=6)
            for k in range(5):
                s.circle(gx + 14 + k * 17, gy + 26 + (k % 2) * 8 - 4, 3, "#ffffff", extra='opacity="0.7"')
        else:
            s.defs('<linearGradient id="gg" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#ff3366"/><stop offset="0.5" stop-color="#ffaa00"/><stop offset="1" stop-color="#33ff66"/></linearGradient>')
            s.rect(gx, gy, 96, 52, "url(#gg)", C["line"], 1, r=6)
        s.text(142, y + 30, lab, 16, C["hi"], bold=True)
        s.para(142, y + 52, d, 470, 13.5, C["text"])
        y += h + 8
    s.card(14, y + 4, 612, 66, accent=C["good"])
    s.para(32, y + 32, "Want to keep your livery and only change the shine? Choose Use source paint (spec only).", 580, 14, C["text"])
    figure("g14_colour_modes", "Zone colour modes",
           "The BASE COLOR dropdown decides where a zone's colour comes from: the finish itself, your existing paint (spec only), one solid colour, another special finish, or a custom gradient.",
           [ac("zone_base_colour_mode"), ui("zone.base_color_mode"), ui("zone.solid_color"), ui("zone.gradient")],
           "Five rows with small colour tiles: finish's own colour, source paint, solid colour, from special, custom gradient, each with a one-line meaning.")
    return s


# ------------------------------------------------------------------ g15
@diagram("g15_surface_intent")
def g15():
    s = Svg(640)
    y0 = _title(s, "What each kind of finish mainly controls",
                "Some finishes change the colour, some only the shine. The catalogue is grouped that way.")
    fam = [
        ("Shine only", "Foundation, Clearcoat, Ghost Geometry", "Your paint stays as it is. The spec map does the work.", C["good"],
         [src("engine/paint_v2/surface_intent.py", r'^\s*"Foundation":\s'), src("engine/paint_v2/surface_intent.py", r'^\s*"Clearcoat":\s'), src("engine/paint_v2/surface_intent.py", r'^\s*"Ghost Geometry":\s')]),
        ("Pattern design", "Carbon & Weave, Geometric, Optical, Decades 50s to 90s", "The shape of the pattern matters. Its colour does not.", C["cyan"],
         [src("engine/paint_v2/surface_intent.py", r'^\s*"Carbon & Weave":\s'), src("engine/paint_v2/surface_intent.py", r'^\s*"Geometric":\s'), src("engine/paint_v2/surface_intent.py", r'^\s*"Optical":\s')]),
        ("Pattern with its own colour", "Cultural", "Image-based patterns that bring their colours with them.", C["pink"],
         [src("engine/paint_v2/surface_intent.py", r'^\s*"Cultural":\s')]),
        ("Fine structural colour", "Neon, ASTRA, FRACTURED lanes", "Tiny 8 to 32 pixel structure with colour and shine that move together.", C["gold"],
         [src("engine/paint_v2/surface_intent.py", r'^\s*"Neon":\s'), src("engine/paint_v2/surface_intent.py", r'^\s*"ASTRA":\s')]),
        ("Everything (paint and shine)", "All other categories, including Foundation EFX", "The finish sets both colour and shine.", C["orange"],
         [src("engine/paint_v2/surface_intent.py", r'^\s*"Foundation EFX":\s'), src("engine/paint_v2/surface_intent.py", r"^DEFAULT_INTENT")]),
    ]
    srcs = [src("engine/paint_v2/surface_intent.py", r"^CATEGORY_INTENT")]
    y = y0
    for t, cats, d, col, ss in fam:
        srcs += ss
        h = 88
        s.card(14, y, 612, h, accent=col)
        s.text(32, y + 28, t, 17, col, bold=True)
        s.text(32, y + 50, cats, 14, C["hi"], bold=True)
        s.text(32, y + 72, d, 13.5, C["text"])
        y += h + 8
    figure("g15_surface_intent", "What a finish mainly controls",
           "Finishes are grouped by what they mainly change: shine only, a pattern's shape, a pattern with its own colour, fine structural colour, or everything. "
           "Foundation finishes, for example, leave your paint alone.",
           srcs, "Five stacked cards naming the families: shine only, pattern design, pattern with its own colour, fine structural colour, and everything, with example category names.")
    return s


# ------------------------------------------------------------------ g16
@diagram("g16_foundation_spec_only")
def g16():
    s = Svg(640)
    y0 = _title(s, "Foundation finishes change only the shine",
                "Same paint in every column. Only the three spec numbers move.")
    cols = [("Chrome", "f_chrome"), ("Satin chrome", "f_satin_chrome"), ("Soft matte", "f_soft_matte")]
    cw = 196
    srcs = [src("mcp/server/index.js", r"FOUNDATION finish"), src("mcp/server/index.js", r"base::f_chrome for mirror chrome")]
    for i, (nm, fid) in enumerate(cols):
        m, r, cc, so = reg(fid)
        srcs.append(so)
        x = 12 + i * (cw + 14)
        s.card(x, y0, cw, 326, accent=C["orange"])
        s.text(x + 18, y0 + 28, nm, 17, C["hi"], bold=True)
        s.text(x + 18, y0 + 46, "base::" + fid, 13, C["dim"], mono=True) if False else None
        # identical paint swatch (a livery: blue with white + red stripes)
        s.rect(x + 18, y0 + 58, cw - 36, 80, "#1f3b8f", C["line"], 1, r=6)
        s.rect(x + 18, y0 + 84, cw - 36, 10, "#e8e8ee")
        s.rect(x + 18, y0 + 100, cw - 36, 10, "#d62d20")
        s.text(x + cw / 2, y0 + 158, "paint: unchanged", 13.5, C["good"], "middle", True)
        for k, (lab, v, col) in enumerate((("R metal", m, C["R"]), ("G rough", r, C["G"]), ("B coat (low = glossy)", cc, C["B"]))):
            yy = y0 + 190 + k * 44
            s.text(x + 18, yy, lab, 13, C["dim"], bold=True)
            s.text(x + cw - 18, yy, str(v), 14, col, "end", True)
            s.rect(x + 18, yy + 8, cw - 36, 10, C["inset"], C["line"], 1, r=5)
            s.rect(x + 18, yy + 8, max(3, (cw - 36) * v / 255), 10, col, None, 0, r=5)
    yy = y0 + 342
    s.card(14, yy, 612, 78, accent=C["good"])
    s.text(32, yy + 28, "Use these when you only want a different shine", 15, C["hi"], bold=True)
    s.para(32, yy + 50, "Set the zone colour to Use source paint. Do not use plain chrome, metallic or candy for this: they repaint the car.", 580, 13.5, C["text"])
    figure("g16_foundation_spec_only", "Foundation: only the shine changes",
           "A Foundation finish with the colour set to your source paint leaves the paint exactly as it is and changes only the spec numbers. "
           "Chrome, satin chrome and soft matte shown with their catalogue values.",
           srcs, "Three columns with an identical blue striped paint swatch. Below each, three bars for metal, roughness and clearcoat: chrome 255, 2, 16; satin chrome 250, 45, 40; soft matte 0, 200, 165.")
    return s


# ------------------------------------------------------------------ g17
@diagram("g17_pick_a_door")
def g17():
    s = Svg(640)
    y0 = _title(s, "Pick a door: PRO or CHAT",
                "Both edit the same zones and the same car. Switch any time with the pill at the top.")
    doors = [
        ("PRO", C["orange"], "I want exact control", "Zones, finishes, layers, masks, spec tools and every slider. The full paint shop.",
         "New buyers can feel lost here. Start with Chat, or turn on the Tutorial."),
        ("CHAT", C["cyan"], "I want to just say it", "Type what you want in plain words: make the hood matte black. Watch the car change.",
         "Works with no key. A key or Claude / ChatGPT makes it smarter. Every change has Undo."),
    ]
    y = y0
    for nm, col, q, d, n in doors:
        h = 132
        s.card(14, y, 612, h, accent=col)
        s.rect(30, y + 18, 90, 96, C["inset"], col, 2, r=8)
        s.text(75, y + 74, nm, 20, col, "middle", True)
        s.text(140, y + 32, q, 17, C["hi"], bold=True)
        yy = s.para(140, y + 56, d, 470, 14, C["text"])
        s.para(140, yy + 2, n, 470, 13, C["dim"])
        y += h + 10
    figure("g17_pick_a_door", "PRO or CHAT",
           "PRO is the full paint shop. CHAT lets you say what you want in plain words. Both work on the same zones.",
           [ui("mode.pro"), ui("mode.chat")],
           "Two cards. PRO for exact control, CHAT for typing what you want.")
    return s


# ------------------------------------------------------------------ g19
@diagram("g19_scale_on_car")
def g19():
    s = Svg(640)
    y0 = _title(s, "Why finish detail must be tiny",
                "The 2048 px sheet covers the whole car. Small on the sheet is already big on the car.")
    d = json.loads((L.ROOT / "scripts/ai_atlas/car_atlas_clusters.json").read_text(encoding="utf8"))
    car = [c for c in d["cars"] if c["id"] == "nextgen-camry-camaro-2024"][0]
    sx, sy, ss = 20, y0 + 6, 360
    k = ss / 2048
    s.rect(sx, sy, ss, ss, C["inset"], C["line"], 1.5)
    for name, p in car["parts"].items():
        x0, y0b, x1, y1 = p["box"]
        s.rect(sx + x0 / 100 * ss, sy + y0b / 100 * ss, (x1 - x0) / 100 * ss, (y1 - y0b) / 100 * ss, "#1f2740", C["line"], 1, r=3)
    ls = car["parts"]["left side"]["box"]
    lx, ly = sx + ls[0] / 100 * ss, sy + ls[1] / 100 * ss
    lw, lh = (ls[2] - ls[0]) / 100 * ss, (ls[3] - ls[1]) / 100 * ss
    sq = 256 * k
    s.rect(lx + 6, ly + lh - sq - 4, sq, sq, "none", C["orange"], 2)
    s.text(lx + 6 + sq / 2, ly + lh - sq / 2 + 1, "256", 13, C["orange"], "middle", True)
    cxs, cys = lx + 6 + sq + 22, ly + lh - 32 * k - 8
    s.rect(cxs, cys, 32 * k, 32 * k, C["cyan"], C["cyan"], 1)
    s.line(cxs + 32 * k + 3, cys + 3, cxs + 32 * k + 20, cys - 16, C["cyan"], 1.5)
    s.text(cxs + 32 * k + 22, cys - 12, "32", 13, C["cyan"], "start", True)
    s.text(lx + 4, ly - 6, "left side panel", 13, C["dim"], bold=True)
    s.text(sx + ss / 2, sy + ss + 20, "whole sheet = 2048 px", 13, C["dim"], "middle", True)
    # right legend
    rx = 400
    s.text(rx, y0 + 30, "Same sheet, two sizes", 16, C["hi"], bold=True)
    s.rect(rx, y0 + 50, 22, 22, "none", C["orange"], 2)
    yy = s.para(rx + 32, y0 + 62, "256 px: an eighth of the sheet. A big blob on the car.", 205, 13.5, C["text"])
    s.rect(rx + 6, yy + 12, 10, 10, C["cyan"], C["cyan"], 1)
    yy = s.para(rx + 32, yy + 21, "32 px: about the size of a side mirror. Good fine detail is 8 to 32 px.", 205, 13.5, C["text"])
    s.card(rx - 6, yy + 12, 232, 118, accent=C["good"])
    s.text(rx + 12, yy + 38, "In the zone editor", 14, C["hi"], bold=True)
    s.para(rx + 12, yy + 58, "Base Scale 0.5 = twice as fine. 0.05x to 5.0x. Smaller = finer, more repeats.", 198, 13, C["text"])
    ybot = max(sy + ss + 40, yy + 150)
    s.card(14, ybot, 612, 72, accent=C["orange"])
    s.para(32, ybot + 28, "When a texture looks like smeared paint on the car, make it finer: lower Base Scale or pattern Scale below 1.", 580, 14, C["text"])
    figure("g19_scale_on_car", "Scale on the car",
           "The 2048 pixel sheet covers a whole car, so a 256 pixel detail is a huge blob while a 32 pixel detail is about a side mirror. "
           "Lower the scale slider for finer texture.",
           [src("CLAUDE.md", r"A noise octave of 64"), src("engine/paint_v2/surface_intent.py", r"Owner doctrine requires 8-32px"), ac("zone_base_scale"), ac("zone_pattern_scale")],
           "A sheet outline with the left side panel marked. An orange square shows a 256 pixel area and a small cyan square shows a 32 pixel detail, with a note about the scale slider.")
    return s


# ------------------------------------------------------------------ g20
@diagram("g20_selection_modes")
def g20():
    s = Svg(640)
    y0 = _title(s, "Selection modes: Add, Replace, Subtract",
                "How a new selection combines with the one you already have.")
    modes = [("Add", "+", "Keeps the old and adds the new. Shift + click with the Wand.", "add"),
             ("Replace", "", "Throws the old away. Only the new selection is left.", "rep"),
             ("Subtract", "-", "Cuts the new one out of the old. Alt + click with the Wand.", "sub")]
    cw, gap = 196, 14
    for i, (nm, sym, d, kind) in enumerate(modes):
        x = 12 + i * (cw + gap)
        s.card(x, y0, cw, 330, accent=C["orange"])
        s.text(x + 18, y0 + 30, nm, 18, C["hi"], bold=True)
        # before: two circles
        bx, by = x + 18, y0 + 50
        s.text(bx, by + 8, "Before", 13, C["dim"], bold=True)
        s.rect(bx, by + 16, cw - 36, 76, C["inset"], C["line"], 1, r=6)
        s.circle(bx + 54, by + 54, 28, C["cyan"], None, 0, extra='opacity="0.85"')
        s.circle(bx + 86, by + 54, 28, "none", C["orange"], 2.5, extra='stroke-dasharray="5 4"')
        s.text(bx + 36, by + 58, "old", 13, "#0b0e17", "middle", True)
        s.text(bx + 112, by + 58, "new", 13, C["orange"], "middle", True)
        # after
        ay = by + 108
        s.text(bx, ay + 8, "After", 13, C["dim"], bold=True)
        s.rect(bx, ay + 16, cw - 36, 76, C["inset"], C["line"], 1, r=6)
        mid = s.gid("m")
        old = f'<circle cx="{bx + 54}" cy="{ay + 54}" r="28"/>'
        new = f'<circle cx="{bx + 86}" cy="{ay + 54}" r="28"/>'
        if kind == "add":
            s.raw(f'<g fill="{C["good"]}" opacity="0.9">{old}{new}</g>')
        elif kind == "rep":
            s.raw(f'<g fill="{C["good"]}" opacity="0.9">{new}</g>')
        else:
            s.defs(f'<mask id="{mid}"><rect x="0" y="0" width="640" height="2000" fill="white"/><g fill="black">{new}</g></mask>')
            s.raw(f'<g mask="url(#{mid})" fill="{C["good"]}" opacity="0.9">{old}</g>')
        s.para(x + 18, ay + 116, d, cw - 34, 13, C["text"])
    yy = y0 + 346
    s.card(14, yy, 612, 70, accent=C["dim"])
    s.para(32, yy + 28, "Pick the mode in the Selection mode dropdown. Tolerance sets how similar a colour must be to be picked.", 580, 14, C["text"])
    figure("g20_selection_modes", "Add, Replace and Subtract",
           "Add keeps the old selection and adds the new one. Replace keeps only the new one. Subtract cuts the new one out of the old. "
           "With the Magic Wand, Shift adds and Alt subtracts.",
           [ui("selectionMode"), ui("vtModeWand")],
           "Three cards each with a before and after picture of two overlapping circles. Add shows both, Replace shows only the new, Subtract shows the old with the new cut out.")
    return s
