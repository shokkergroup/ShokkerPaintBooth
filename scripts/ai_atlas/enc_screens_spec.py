"""Lane S - the app's own spec map viewer (ALL / R Metal / G Rough / B Coat) for finishes on the example car. Group: spec."""
import io
from PIL import Image, ImageDraw
import enc_screens as E
from enc_screens import shot
import enc_callouts as C
import enc_screens_pairs as P

FIND_IMG = """() => { const c = Array.from(document.querySelectorAll('img,canvas')).filter(e => { const r = e.getBoundingClientRect();
  if (r.width < 500 || r.height < 500) return false; const x = r.left + r.width / 2, y = r.top + r.height / 2; return document.elementFromPoint(x, y) === e; });
  c.sort((a, b) => b.getBoundingClientRect().width * b.getBoundingClientRect().height - a.getBoundingClientRect().width * a.getBoundingClientRect().height);
  if (!c[0]) return null; const r = c[0].getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; }"""
CH = [("ALL", "COMBINED (all three channels as colour)"), ("R Metal", "R METAL: brighter = more metal"), ("G Rough", "G ROUGH: brighter = rougher"), ("B Coat", "B COAT: brighter = duller clearcoat")]


IDS = {"PAINT": "lightboxPaintBtn", "SPEC MAP": "lightboxSpecBtn", "ALL": "lightboxChAll", "R Metal": "lightboxChR", "G Rough": "lightboxChG", "B Coat": "lightboxChB"}


def open_viewer(c):
    c.js("() => { openPreviewLightbox('spec'); return 1; }")
    c.wait(1800)
    c.pg.click("#lightboxSpecBtn"); c.wait(500)


def close_viewer(c):
    c.esc(); c.wait(400)
    if c.js(FIND_IMG):
        c.esc(); c.wait(400)


def tile(c, label):
    c.pg.click("#" + IDS[label]); c.wait(700)
    r = c.js(FIND_IMG)
    png = c.pg.screenshot(clip={"x": r[0], "y": r[1], "width": r[2], "height": r[3]})
    return Image.open(io.BytesIO(png)).convert("RGB")


def four(sid, title, caption, finish, color, arts, alt, name, extra=None):
    def fn(c):
        P.clear(c); P.add(c, name=name, finish=finish, color=color, **(extra or {})); P.shotpic(c)
        open_viewer(c)
        W = 400
        tiles = [tile(c, a).resize((W, W), Image.LANCZOS) for a, _ in CH]
        close_viewer(c)
        H = 62
        S = Image.new("RGB", (W * 4 + 12 * 3, W + H), (11, 14, 23)); d = ImageDraw.Draw(S)
        f = C._font(17)
        for i, (t, (_, lab)) in enumerate(zip(tiles, CH)):
            x = i * (W + 12); S.paste(t, (x, 0)); d.text((x + W // 2, W + 20), lab.split(":")[0], font=f, fill=(245, 118, 26), anchor="mm")
            if ":" in lab:
                d.text((x + W // 2, W + 44), lab.split(":")[1].strip(), font=C._font(14), fill=(220, 226, 238), anchor="mm")
        E.emit(sid, title, caption, "spec_view", arts, S, alt, maxw=1600, meta={"finish_key": finish})
    E.REG[sid] = ("spec", fn); E.ORDER.append(sid)


SPEC = ["spec.what_is_spec_map", "spec.reading_by_colour", "spec.channel_r_metallic", "spec.channel_g_roughness", "spec.channel_b_clearcoat"]
four("spec_candy", "Spec map of a Candy finish", "The app's spec map viewer for a red Candy base: mostly clearcoat, very little metal.", "base::candy", "#d4111f", SPEC,
     "Four views of the spec map: combined, metal, rough and coat channels, for a candy finish.", "Candy")
four("spec_chrome", "Spec map of a Chrome finish", "The same four views for Chrome: the R METAL channel lights up, roughness stays dark.", "base::chrome", "finish", SPEC,
     "Four views of the spec map for a chrome finish.", "Chrome")
four("spec_matte", "Spec map of a soft matte Foundation", "A soft matte Foundation: high roughness, little metal, dull coat.", "base::f_soft_matte", "source", SPEC,
     "Four views of the spec map for a soft matte foundation.", "Matte")
four("spec_carbon", "Spec map of Carbon Fibre", "A woven finish shows its weave in the spec channels, not only in the paint.", "base::carbon_base", "finish", SPEC,
     "Four views of the spec map for carbon fibre.", "Carbon")
four("spec_astra", "Spec map of an ASTRA finish", "A busy full finish: every channel carries its own pattern, so the shine varies across the car.", "base::astra_event_horizon", "finish", SPEC,
     "Four views of the spec map for an ASTRA finish.", "Event horizon")
four("spec_fractured_forge", "Spec map of a Fractured Forge finish", "Fine filaments drawn in metal and roughness as well as colour.", "monolithic::ff_leviathan_filaments", "finish", SPEC,
     "Four views of the spec map for a Fractured Forge finish.", "Filaments")


@shot("spec", "spec_viewer_buttons")
def spec_viewer_buttons(c):
    P.clear(c); P.add(c, name="Candy", finish="base::chrome", color="finish"); P.shotpic(c)
    open_viewer(c)
    c.pg.click("#lightboxChR"); c.wait(700)
    b = {k: c.pg.locator("#" + IDS[k]).bounding_box() for k in ("PAINT", "SPEC MAP", "ALL", "R Metal", "G Rough", "B Coat")}
    marks = [(1, [b["PAINT"]["x"], b["PAINT"]["y"], b["PAINT"]["width"], b["PAINT"]["height"]]), (2, [b["SPEC MAP"]["x"], b["SPEC MAP"]["y"], b["SPEC MAP"]["width"], b["SPEC MAP"]["height"]]),
             (3, [b["ALL"]["x"], b["ALL"]["y"], b["ALL"]["width"], b["ALL"]["height"]]), (4, [b["R Metal"]["x"], b["R Metal"]["y"], b["R Metal"]["width"], b["R Metal"]["height"]], {"at": "t"}),
             (5, [b["G Rough"]["x"], b["G Rough"]["y"], b["G Rough"]["width"], b["G Rough"]["height"]]), (6, [b["B Coat"]["x"], b["B Coat"]["y"], b["B Coat"]["width"], b["B Coat"]["height"]])]
    im = c.grab([0, 0, 1700, 1000], marks)
    close_viewer(c)
    E.emit("spec_viewer_buttons", "The spec map viewer", "Open the preview full screen and flip between PAINT and SPEC MAP, then pick one channel.", "ui",
           ["ui_shell.preview_channel_views", "spec.what_is_spec_map", "spec.reading_by_colour"], im, "The full-screen spec map viewer showing the metal channel of a chrome zone, with six numbered callouts.",
           ["PAINT (the colour picture)", "SPEC MAP (how the surface reflects)", "ALL channels as colour", "R Metal channel (selected here)", "G Rough channel", "B Coat channel"], maxw=1400)
