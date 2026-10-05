from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps


Image.MAX_IMAGE_PIXELS = None

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "assets" / "patterns" / "spec_overlay_patterns"
OUT = ROOT / "assets" / "reference_textures" / "pattern_plates"


FINISHES = [
    ("1191.jpg", "pp_holographic_oil_circuit", "Holographic Oil Circuit", "#ba9dff", "holo"),
    ("1222.jpg", "pp_black_emboss_mandala", "Black Emboss Mandala", "#2e2926", "emboss"),
    ("12maret21_01.jpg", "pp_graphite_cross_lattice", "Graphite Cross Lattice", "#c7c4bc", "lattice"),
    ("13551.jpg", "pp_marble_flow_pearl", "Marble Flow Pearl", "#d8d2c8", "marble"),
    ("197.jpg", "pp_acid_carbon_mesh", "Acid Carbon Mesh", "#c7e23c", "carbon"),
    ("1f85204a-b42b-4830-af86-7116ea61ca99.jpg", "pp_noir_houndstooth_star", "Noir Houndstooth Star", "#5a5962", "textile"),
    ("2985daa1-202c-4c0e-afd9-5699057cb89a.jpg", "pp_hazard_chevron_weave", "Hazard Chevron Weave", "#e3c817", "chevron"),
    ("378822.jpg", "pp_burn_hole_mesh", "Burn Hole Mesh", "#4d4238", "mesh_burn"),
    ("3878.jpg", "pp_teal_hex_haze", "Teal Hex Haze", "#7ec3bf", "soft_hex"),
    ("4cf1f092-7c7c-4852-b99c-646486313c1a.jpg", "pp_shadow_diamond_mesh", "Shadow Diamond Mesh", "#8b8e91", "diamond"),
    ("51795.jpg", "pp_talavera_tile_riot", "Talavera Tile Riot", "#1e8cb6", "cultural_tile"),
    ("67_05_05_fury_plane_green.jpg", "pp_green_plasma_vein", "Green Plasma Vein", "#64d550", "plasma"),
    ("9eb3cf63-8f0f-4f5a-ba0f-8684627f66a5.jpg", "pp_neon_fracture_net", "Neon Fracture Net", "#3aff45", "fracture"),
    ("abstract-geometric-texture-background.jpg", "pp_pink_checker_carbon", "Pink Checker Carbon", "#ed4fa4", "checker"),
    ("bg_zig_zag_02.jpg", "pp_red_herringbone_heat", "Red Herringbone Heat", "#bd181d", "herringbone"),
    ("cbe40243-5be5-460d-b9fc-5ced5a85cbd0.jpg", "pp_chrome_oval_chain", "Chrome Oval Chain", "#d8dce4", "chain"),
    ("colored-ceramic-stones-abstract-smooth-brown-mosiac-texture-abstract-ceramic-mosaic-adorned-building-abstract-seamless-pattern.jpg", "pp_terracotta_ceramic_grid", "Terracotta Ceramic Grid", "#9b5d3e", "ceramic"),
    ("geometricpatterngray_16.jpg", "pp_gunmetal_geo_tessellation", "Gunmetal Geo Tessellation", "#74787b", "geo"),
    ("japan_09.jpg", "pp_tokyo_script_textile", "Tokyo Script Textile", "#cf302c", "script"),
    ("OBN15X0.jpg", "pp_lime_pixel_confetti", "Lime Pixel Confetti", "#90d93b", "confetti"),
    ("OBN1E50.jpg", "pp_psychedelic_floral_spin", "Psychedelic Floral Spin", "#d37ad6", "floral"),
    ("OBSK4M0.jpg", "pp_ice_facet_shatter", "Ice Facet Shatter", "#8fc8ff", "ice_facets"),
    ("OBSKHY0.jpg", "pp_ember_circuit_maze", "Ember Circuit Maze", "#ef4b1e", "circuit"),
    ("round_geometry_2.jpg", "pp_blue_polygon_shatter", "Blue Polygon Shatter", "#2954c6", "polygon"),
]

SPEC_DESC = {
    "holo": "Rainbow oil-film highlights, polished low-roughness arcs, and prismatic clearcoat response.",
    "emboss": "Dark raised relief, satin valleys, and glossy mandala edge catches.",
    "lattice": "Graphite lattice ribs with crisp bright intersections and controlled satin gaps.",
    "marble": "Pearl marble veins with soft clearcoat rivers and polished vein ridges.",
    "carbon": "Acid-tinted mesh/carbon contrast with tight gloss cells and matte under-weave.",
    "textile": "Noir textile stars and houndstooth checks with thread-level roughness shifts.",
    "chevron": "Hazard chevrons with bright cut edges, dark rubber troughs, and woven directionality.",
    "mesh_burn": "Burned mesh crater texture with scorched rough pits and polished raised rim detail.",
    "soft_hex": "Teal hex haze with pearly bokeh cells and restrained translucent clearcoat.",
    "diamond": "Shadow diamond mesh with repeating raised ridges and satin recessed panels.",
    "cultural_tile": "Talavera ceramic tile gloss with enamel ridges and deep grout contrast.",
    "plasma": "Green plasma veins with electrical gloss streaks and smoky rough shadows.",
    "fracture": "Neon fracture net with hot crack clearcoat and black low-sheen islands.",
    "checker": "Pink checker carbon geometry with glossy colored cells and dark woven breaks.",
    "herringbone": "Red herringbone heat weave with diagonal satin grain and hot edge flashes.",
    "chain": "Chrome oval chain links with mirror ridges and dark open-pocket roughness.",
    "ceramic": "Terracotta ceramic grid with glazed stone islands and gritty grout channels.",
    "geo": "Gunmetal micro tessellation with precise satin/metal facet shifts.",
    "script": "Tokyo script textile with inked cloth valleys and glossy red-white calligraphy strokes.",
    "confetti": "Lime pixel confetti with small hard gloss pops across a matte field.",
    "floral": "Psychedelic guilloche floral rings with shifting satin petals and chrome thread lines.",
    "ice_facets": "Ice crystal shards with cold clearcoat facets and bright frozen cuts.",
    "circuit": "Ember circuit maze with heated copper lines and dark insulated cells.",
    "polygon": "Blue polygon shatter with angular clearcoat facets and graphite separators.",
}

PROFILE = {
    "holo": (0.34, 0.18, 0.82, 0.34, 0.22, 0.30),
    "emboss": (0.24, 0.50, 0.58, 0.46, 0.30, 0.24),
    "lattice": (0.55, 0.36, 0.66, 0.48, 0.22, 0.22),
    "marble": (0.22, 0.32, 0.78, 0.28, 0.18, 0.24),
    "carbon": (0.64, 0.44, 0.74, 0.50, 0.28, 0.22),
    "textile": (0.18, 0.72, 0.36, 0.34, 0.26, 0.18),
    "chevron": (0.42, 0.36, 0.70, 0.50, 0.22, 0.30),
    "mesh_burn": (0.18, 0.76, 0.42, 0.38, 0.30, 0.18),
    "soft_hex": (0.18, 0.42, 0.68, 0.26, 0.20, 0.22),
    "diamond": (0.38, 0.46, 0.60, 0.46, 0.22, 0.22),
    "cultural_tile": (0.36, 0.30, 0.82, 0.50, 0.18, 0.28),
    "plasma": (0.34, 0.26, 0.90, 0.52, 0.22, 0.36),
    "fracture": (0.42, 0.22, 0.92, 0.56, 0.22, 0.38),
    "checker": (0.38, 0.38, 0.72, 0.48, 0.22, 0.28),
    "herringbone": (0.42, 0.40, 0.70, 0.50, 0.24, 0.28),
    "chain": (0.70, 0.16, 0.86, 0.50, 0.18, 0.30),
    "ceramic": (0.20, 0.58, 0.60, 0.38, 0.28, 0.20),
    "geo": (0.48, 0.42, 0.62, 0.44, 0.20, 0.22),
    "script": (0.26, 0.56, 0.62, 0.46, 0.24, 0.24),
    "confetti": (0.34, 0.52, 0.66, 0.50, 0.26, 0.22),
    "floral": (0.34, 0.24, 0.82, 0.46, 0.20, 0.30),
    "ice_facets": (0.48, 0.18, 0.92, 0.54, 0.18, 0.34),
    "circuit": (0.46, 0.28, 0.86, 0.54, 0.22, 0.34),
    "polygon": (0.46, 0.24, 0.82, 0.54, 0.20, 0.32),
}


def _norm(a: np.ndarray) -> np.ndarray:
    a = a.astype(np.float32)
    lo = float(np.percentile(a, 1))
    hi = float(np.percentile(a, 99))
    if hi <= lo + 1e-6:
        return np.zeros_like(a, dtype=np.float32)
    return np.clip((a - lo) / (hi - lo), 0.0, 1.0)


def _push_std(a: np.ndarray, target: float, low: float, high: float) -> np.ndarray:
    a = np.clip(a.astype(np.float32), low, high)
    mean = float(a.mean())
    std = float(a.std())
    if std < 1e-6:
        return a
    scale = min(2.8, max(1.0, target / std))
    return np.clip((a - mean) * scale + mean, low, high)


def _fit_plate(path: Path) -> Image.Image:
    img = Image.open(path).convert("RGB")
    return ImageOps.fit(img, (2048, 2048), method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))


def _spec_from_plate(plate: Image.Image, style: str) -> Image.Image:
    rgb = np.asarray(plate, dtype=np.float32) / 255.0
    bgr8 = cv2.cvtColor((rgb * 255).astype(np.uint8), cv2.COLOR_RGB2BGR)
    gray8 = cv2.cvtColor(bgr8, cv2.COLOR_BGR2GRAY)
    luma = _norm(gray8.astype(np.float32) / 255.0)
    sat = _norm(rgb.max(axis=2) - rgb.min(axis=2))

    blur1 = cv2.GaussianBlur(luma, (0, 0), 1.2)
    blur7 = cv2.GaussianBlur(luma, (0, 0), 7.0)
    local = _norm(np.abs(blur1 - blur7))
    sx = cv2.Sobel(luma, cv2.CV_32F, 1, 0, ksize=3)
    sy = cv2.Sobel(luma, cv2.CV_32F, 0, 1, ksize=3)
    edge = _norm(np.sqrt(sx * sx + sy * sy))
    lap = _norm(np.abs(cv2.Laplacian(luma, cv2.CV_32F, ksize=3)))
    fine = _norm(0.55 * edge + 0.30 * lap + 0.15 * local)
    high = _norm(np.clip(luma - 0.58, 0.0, 1.0) + 0.45 * edge + 0.20 * sat)
    dark = _norm((1.0 - luma) + 0.45 * local)

    base_m, base_r, base_cc, m_gain, r_gain, cc_gain = PROFILE[style]
    cool = _norm(rgb[:, :, 2] * 0.55 + rgb[:, :, 1] * 0.25 - rgb[:, :, 0] * 0.18)
    warm = _norm(rgb[:, :, 0] * 0.55 + rgb[:, :, 1] * 0.22 - rgb[:, :, 2] * 0.16)

    metallic = base_m + m_gain * (0.48 * fine + 0.22 * sat + 0.18 * high + 0.12 * cool)
    roughness = base_r + r_gain * (0.58 * dark + 0.32 * local + 0.10 * warm) - 0.22 * fine
    clearcoat = base_cc + cc_gain * (0.46 * high + 0.26 * sat + 0.18 * edge + 0.10 * (1.0 - dark))
    clearcoat = 0.68 * clearcoat + 0.18 * fine + 0.10 * local + 0.04 * (1.0 - dark)

    metallic = _push_std(metallic, 0.16, 0.04, 0.98)
    roughness = _push_std(roughness, 0.155, 0.05, 0.96)
    if float(roughness.std()) < 0.08:
        roughness = _push_std(0.58 * roughness + 0.28 * fine + 0.14 * local, 0.13, 0.05, 0.96)
    clearcoat = _push_std(clearcoat, 0.16, 0.05, 0.96)
    if float(clearcoat.std()) < 0.09:
        clearcoat = _push_std(0.55 * clearcoat + 0.30 * fine + 0.15 * luma, 0.14, 0.05, 0.96)
    spec = np.dstack([metallic, roughness, clearcoat, np.ones_like(metallic)])
    return Image.fromarray(np.clip(spec * 255.0, 0, 255).astype(np.uint8), "RGBA")


def _stats(spec: Image.Image) -> dict:
    arr = np.asarray(spec.convert("RGBA"), dtype=np.uint8)
    out = {}
    for idx, key in enumerate(("M", "R", "CC")):
        ch = arr[:, :, idx]
        out[f"{key}_std"] = round(float(ch.std()), 2)
        out[f"{key}_range"] = [int(ch.min()), int(ch.max())]
    return out


def _make_contact(items: list[dict]) -> None:
    thumb = 190
    label_h = 42
    cols = 4
    rows = int(np.ceil(len(items) / cols))
    sheet = Image.new("RGB", (cols * thumb * 2, rows * (thumb + label_h)), (18, 18, 18))
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("arial.ttf", 14)
    except Exception:
        font = ImageFont.load_default()
    for i, item in enumerate(items):
        x = (i % cols) * thumb * 2
        y = (i // cols) * (thumb + label_h)
        plate = Image.open(OUT / item["texture"]).convert("RGB").resize((thumb, thumb), Image.Resampling.LANCZOS)
        spec = Image.open(OUT / item["spec"]).convert("RGB").resize((thumb, thumb), Image.Resampling.LANCZOS)
        sheet.paste(plate, (x, y))
        sheet.paste(spec, (x + thumb, y))
        draw.text((x + 6, y + thumb + 5), item["name"][:48], fill=(235, 235, 235), font=font)
        draw.text((x + 6, y + thumb + 23), item["id"], fill=(160, 160, 160), font=font)
    sheet.save(OUT / "_reference_pattern_plate_contact.jpg", quality=92)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    entries = []
    for source, finish_id, name, swatch, style in FINISHES:
        src_path = SRC / source
        if not src_path.exists():
            raise FileNotFoundError(src_path)
        plate = _fit_plate(src_path)
        spec = _spec_from_plate(plate, style)
        texture_name = f"{finish_id}.png"
        spec_name = f"{finish_id}_spec.png"
        plate.save(OUT / texture_name, optimize=True)
        spec.save(OUT / spec_name, optimize=True)
        entry = {
            "id": finish_id,
            "spec_id": "spec_" + finish_id.removeprefix("pp_"),
            "name": name,
            "spec_name": f"SPEC {name}",
            "desc": SPEC_DESC[style],
            "swatch": swatch,
            "source": source,
            "texture": texture_name,
            "spec": spec_name,
            "style": style,
            "stats_2048": _stats(spec),
        }
        entries.append(entry)

    manifest = {
        "batch": "reference_pattern_plates_2026_05_30",
        "source_dir": str(SRC.relative_to(ROOT)).replace("\\", "/"),
        "size": [2048, 2048],
        "channel_order": ["metallic", "roughness", "clearcoat", "alpha"],
        "owner_doctrine": "Real source plates; no generated filler; full 2048 coverage; spec channels derived from luma, edges, saturation, and local contrast.",
        "finishes": entries,
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    _make_contact(entries)
    print(f"Built {len(entries)} reference pattern plates in {OUT}")
    for item in entries:
        print(item["id"], item["spec_id"], item["stats_2048"])


if __name__ == "__main__":
    main()
