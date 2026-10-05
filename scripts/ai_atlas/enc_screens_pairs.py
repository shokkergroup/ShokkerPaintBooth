"""Lane S - before / after pairs of the core actions, both halves the app's own live preview of the example ARCA car. Group: pairs (reuses the cars session)."""
import enc_screens as E
from enc_screens import shot
import enc_callouts as C

BODY = ["Yellow Base", "White Base", "Black Base"]
HIDE = "(names) => { (_psdLayers || []).forEach(l => { if (names.indexOf(l.name) >= 0) l.visible = false; }); try { _finishLayerVisibilityChange(); } catch (e) {} return 1; }"
SHOW = "(names) => { (_psdLayers || []).forEach(l => { if (names.indexOf(l.name) >= 0) l.visible = true; }); try { _finishLayerVisibilityChange(); } catch (e) {} return 1; }"


def clear(c):
    c.js("() => { while (zones.length > 1) zones.splice(0, 1); renderZones(); return zones.length; }")


def add(c, **spec):
    spec.setdefault("region", {"layers": BODY, "everything": True})
    r = c.js("(s) => { const r = SpbProZone.add(s); return { ok: r.ok, w: (r.warnings || []).slice(0, 3) }; }", spec)
    if not r["ok"]:
        raise RuntimeError("add failed %s" % r)


def tweak(c, idx, **kv):
    c.js("([i, kv]) => { Object.assign(zones[i], kv); renderZones(); return 1; }", [idx, kv])


def shotpic(c):
    c.js("() => { renderZones(); triggerPreviewRender(); return 1; }")
    c.js("async () => await SpbProZone.whenSettled(90000)")
    c.wait(500)
    return c.preview_png()


def pair(sid, title, caption, arts, la, lb, alt, a, b, w=700):
    def fn(c):
        ia = a(c); ib = b(c)
        ia = ia.resize((w, w)); ib = ib.resize((w, w))
        im = C.side_by_side(ia, ib, la, lb, gap=16, label_h=38)
        E.emit(sid, title, caption, "before_after", arts, im, alt, maxw=1400)
    E.REG[sid] = ("pairs", fn); E.ORDER.append(sid)


def _plain(c):
    clear(c); return shotpic(c)


def _project(c):
    clear(c)
    for spec in reversed(E.PROJECT):
        add(c, **spec)
    return shotpic(c)


pair("pair_zone_added", "Add zones and the car changes", "Left: the loaded paint with no zones. Right: four zones (chrome numbers, carbon panels, pearl stripes, red candy body).",
     ["zones.what_is_a_zone", "workflows.first_paint", "zones.priority"], "No zones", "Four zones added", "The example car before and after four zones are added.", _plain, _project)


def _base_chrome(c):
    clear(c); add(c, name="Chrome", finish="base::chrome", color="finish"); return shotpic(c)


def _found_chrome(c):
    clear(c); add(c, name="Chrome shine", finish="base::f_chrome", color="source"); return shotpic(c)


pair("pair_base_vs_foundation", "A base repaints; a Foundation keeps your paint", "Same zone, two chrome looks. The Chrome base replaces the colours, the Foundation Chrome keeps your paint and changes only how it shines.",
     ["finishes.foundation_shine_only", "finishes.four_kinds", "finishes.colour_source_modes"], "Chrome base (repaints)", "Foundation Chrome (keeps the paint)", "Two renders of the example car, chrome base and foundation chrome.", _base_chrome, _found_chrome)


def _src(c):
    clear(c); add(c, name="Candy", finish="base::candy", color="source"); return shotpic(c)


def _col(c):
    clear(c); add(c, name="Candy", finish="base::candy", color="#d4111f"); return shotpic(c)


pair("pair_colour_source", "Where the colour comes from", "The same Candy base. Left: Use source paint (your colours stay). Right: a picked red replaces them.",
     ["finishes.colour_source_modes", "finishes.base_colour_tuning"], "Use source paint", "Picked colour (red)", "Candy applied with the source paint colour and with a picked red.", _src, _col)


def _strength(v):
    def f(c):
        clear(c); add(c, name="Event horizon", finish="base::astra_event_horizon", color="finish"); tweak(c, 0, baseStrength=v); return shotpic(c)
    return f


pair("pair_base_strength", "Base Strength: how much of the finish shows", "Same finish, Base Strength 35 percent on the left and 100 percent on the right.",
     ["finishes.base_colour_tuning", "zones.popout_panel"], "Base Strength 35%", "Base Strength 100%", "A finish at low and full base strength on the example car.", _strength(0.35), _strength(1.0))


def _scale(v):
    def f(c):
        clear(c); add(c, name="Plaid", finish="base::at_flannel_forest", color="finish"); tweak(c, 0, baseScale=v); return shotpic(c)
    return f


pair("pair_base_scale", "Base Scale: small or large pattern", "The same plaid finish with Base Scale 0.5 on the left and 2.0 on the right.",
     ["finishes.base_scale_rotation", "spec.scale_rotation"], "Base Scale 0.5", "Base Scale 2.0", "A plaid finish at two scales on the example car.", _scale(0.5), _scale(2.0))


def _hue(v):
    def f(c):
        clear(c); add(c, name="Spectrum", finish="base::astra_causal_origami", color="finish"); tweak(c, 0, baseHueOffset=v); return shotpic(c)
    return f


pair("pair_hue_shift", "Hue Shift turns the colours", "The same finish with Hue Shift at 0 on the left and 140 on the right.",
     ["finishes.base_colour_tuning", "finishes.what_makes_a_finish_pop"], "Hue Shift 0", "Hue Shift 140", "A finish at two hue shift values.", _hue(0), _hue(140))


def _prio(first):
    def f(c):
        clear(c)
        a = dict(name="Red candy", finish="base::candy", color="#d4111f"); b = dict(name="Chrome", finish="base::chrome", color="finish")
        for s in reversed([a, b] if first == "a" else [b, a]):
            add(c, **s)
        return shotpic(c)
    return f


pair("pair_zone_priority", "Zone order decides the winner", "Two zones cover the same body. Left: Red candy is zone 1 (top). Right: Chrome is zone 1. The lower number wins.",
     ["zones.priority", "zones.what_is_a_zone", "zones.card_controls"], "Candy above Chrome", "Chrome above Candy", "Two overlapping zones in both orders.", _prio("a"), _prio("b"))


def _layers(on):
    def f(c):
        clear(c)
        names = ["Contingency Decals", "Tape", "Logos", "Pitbox Colors"]
        c.js(SHOW if on else HIDE, names)
        im = shotpic(c)
        c.js(SHOW, names)
        return im
    return f


pair("pair_layer_hidden", "Hide a layer and it leaves the render", "Left: all layers on. Right: the sponsor, tape, logo and pit-box layers switched off in the LAYERS column.",
     ["layers.panel", "layers.roles"], "All layers on", "Sponsor layers off", "The example car with sponsor layers visible and hidden.", _layers(True), _layers(False))


def _tmpl(on):
    def f(c):
        clear(c)
        names = ["Wire", "Mask", "Car Mandatory"]
        c.js(SHOW if on else HIDE, names)
        im = shotpic(c)
        c.js(HIDE, names)
        return im
    return f


pair("pair_wire_mask_visible", "Wire, Mask and Car Mandatory must be off", "Left: the template guide layers switched on over the paint. Right: switched off, the way you render and export.",
     ["layers.turn_off_before_export", "layers.wire_mask_mandatory", "ui_shell.template_layer_views"], "Template layers ON (wrong for export)", "Template layers OFF", "The example car with the Wire, Mask and Car Mandatory layers shown and hidden.", _tmpl(True), _tmpl(False))
