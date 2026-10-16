# -*- coding: utf-8 -*-
"""Build spb-recipe-card-logo.js from the current brand art.

[SPB-RECIPE-CARD-004 2026-08-26] Owner: replace the graffiti banner on the RENDER RECIPE card
with the new gold "Abbey Road" SHOKKER PAINT BOOTH logo (Downloads/SPBBeatles.png), add QR codes
in the bottom-LEFT (Discord) and bottom-RIGHT (Payhip / Get the App) corners, and put the actual
link text bottom-middle — covering none of the art (links live on an added black strip below it).

Outputs (embedded base64 in spb-recipe-card-logo.js):
  SPB_LOGO_DATAURL    — clean logo, 460px wide (faint card watermark)
  SPB_QR_LOGO_DATAURL — banner + QRs + links, 1100px wide (drawn top AND bottom of the card)

Re-run me whenever the logo art or links change:
  python scripts/build_recipe_card_logo_asset.py [--source <logo.png>]
"""
import argparse
import base64
import io
import os

import qrcode
from PIL import Image, ImageDraw, ImageFont

ROOT = r"C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum"
DEFAULT_SOURCE = r"C:\Users\Ricky's PC\Downloads\SPBBeatles.png"
DISCORD_URL = "https://discord.gg/GwXxyhwtDu"      # owner-supplied 2026-08-26 (case-sensitive!)
PAYHIP_URL = "https://payhip.com/b/AhgpV"
GOLD = (255, 209, 66)
GOLD_DIM = (214, 171, 46)
WHITE = (245, 245, 245)


def _font(size, bold=True):
    for name in (("arialbd.ttf" if bold else "arial.ttf"), "segoeuib.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(os.path.join(r"C:\Windows\Fonts", name), size)
        except Exception:
            continue
    return ImageFont.load_default()


def _qr_card(url, label, module_px=7):
    """White rounded card with a scannable QR + gold label underneath."""
    q = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, border=2,
                      box_size=module_px)
    q.add_data(url)
    q.make(fit=True)
    qr_img = q.make_image(fill_color="black", back_color="white").convert("RGB")
    pad = 10
    label_h = 44
    W = qr_img.width + pad * 2
    H = qr_img.height + pad * 2 + label_h
    card = Image.new("RGB", (W, H), (0, 0, 0))
    d = ImageDraw.Draw(card)
    d.rounded_rectangle([0, 0, W - 1, qr_img.height + pad * 2 - 1], radius=14, fill=(255, 255, 255))
    card.paste(qr_img, (pad, pad))
    f = _font(26)
    tw = d.textlength(label, font=f)
    d.text(((W - tw) / 2, qr_img.height + pad * 2 + 6), label, font=f, fill=GOLD)
    return card


def build_banner(source_path):
    art = Image.open(source_path).convert("RGB")
    AW, AH = art.size                                   # e.g. 1680x944
    strip_h = int(AH * 0.175)                            # black strip below the art for the links
    W, H = AW, AH + strip_h
    banner = Image.new("RGB", (W, H), (0, 0, 0))
    banner.paste(art, (0, 0))
    d = ImageDraw.Draw(banner)

    # QR cards in the true bottom corners (over black art corners + the strip; covers no art)
    m = int(W * 0.014)
    qr_l = _qr_card(DISCORD_URL, "JOIN THE DISCORD")
    qr_r = _qr_card(PAYHIP_URL, "GET THE APP")
    target_h = int(H * 0.235)
    for i, (img_, xside) in enumerate(((qr_l, "l"), (qr_r, "r"))):
        s = target_h / img_.height
        img2 = img_.resize((int(img_.width * s), target_h), Image.LANCZOS)
        x = m if xside == "l" else W - img2.width - m
        banner.paste(img2, (x, H - img2.height - m))

    # link text, centered on the strip
    f_link = _font(int(strip_h * 0.34))
    f_lead = _font(int(strip_h * 0.22))
    cy = AH + int(strip_h * 0.14)
    line1_lead, line1_url = "JOIN THE DISCORD:  ", DISCORD_URL.replace("https://", "")
    line2_lead, line2_url = "GET THE APP:  ", PAYHIP_URL.replace("https://", "")
    for lead, url, yy in ((line1_lead, line1_url, cy), (line2_lead, line2_url, cy + int(strip_h * 0.44))):
        w_lead = d.textlength(lead, font=f_lead)
        w_url = d.textlength(url, font=f_link)
        x0 = (W - (w_lead + w_url)) / 2
        d.text((x0, yy + int(strip_h * 0.07)), lead, font=f_lead, fill=GOLD_DIM)
        d.text((x0 + w_lead, yy), url, font=f_link, fill=WHITE)
    return banner


def to_dataurl(img, width):
    s = width / img.width
    out = img.resize((width, int(img.height * s)), Image.LANCZOS)
    buf = io.BytesIO()
    out.save(buf, format="PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode(), out.size


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default=DEFAULT_SOURCE)
    ap.add_argument("--preview-only", action="store_true", help="write preview PNGs, skip the JS")
    args = ap.parse_args()

    banner = build_banner(args.source)
    banner.save(os.path.join(ROOT, "_anime_overhaul_work", "recipe_banner_preview.png"))
    logo_url, (lw, lh) = to_dataurl(Image.open(args.source).convert("RGB"), 460)
    qr_url, (qw, qh) = to_dataurl(banner, 1100)
    print(f"logo {lw}x{lh}  banner {qw}x{qh}  (source {args.source})")
    if args.preview_only:
        return

    js = (
        "/* SPB-RECIPE-CARD-004 (2026-08-26) logo assets for the RENDER RECIPE card.\n"
        "   Owner: new gold Abbey-Road SHOKKER PAINT BOOTH logo (was the graffiti banner), QR codes\n"
        "   bottom-left (Discord " + DISCORD_URL + ") / bottom-right (Payhip " + PAYHIP_URL + "),\n"
        "   link text bottom-middle on an added strip so nothing in the art is covered.\n"
        "   REGENERATE with: python scripts/build_recipe_card_logo_asset.py  (do NOT hand-edit) */\n"
        f'window.SPB_LOGO_DATAURL = "{logo_url}";\n'
        f"window.SPB_LOGO_W = {lw};\n"
        f"window.SPB_LOGO_H = {lh};\n"
        f'window.SPB_QR_LOGO_DATAURL = "{qr_url}";\n'
        f"window.SPB_QR_LOGO_W = {qw};\n"
        f"window.SPB_QR_LOGO_H = {qh};\n"
    )
    dest = os.path.join(ROOT, "spb-recipe-card-logo.js")
    tmp = dest + ".tmp_logo"
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        f.write(js)
    os.replace(tmp, dest)
    print(f"wrote spb-recipe-card-logo.js ({len(js) // 1024} KB)")


if __name__ == "__main__":
    main()
