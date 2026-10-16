"""PhotoCraft round-trip: SPB layers <-> layered PSD (pure functions, no Flask).

Used by server_routes/photocraft_routes.py and the end-to-end test
scripts/spb_photocraft_roundtrip_test.py.

Layer model (what the client sends / what read_psd returns), bottom layer first:
    {"id": "psd_3", "name": "Sponsors", "group_path": ["Paintable Area"],
     "visible": True, "opacity": 255, "blend": "normal", "clipping": False,
     "bbox": [left, top, right, bottom], "rgba": <PIL RGBA image of bbox size>}

Spec maps travel as a group of four opaque grayscale layers (one per channel) so a
round trip never depends on how an editor treats RGB under alpha=0.
"""
from __future__ import annotations

import os

import numpy as np
from PIL import Image

SPEC_GROUP = "SPB SPEC (R=metallic G=roughness B=clearcoat A=mask)"
SPEC_LAYERS = ("Metallic (R)", "Roughness (G)", "Clearcoat (B)", "Spec Mask (A)")

# SPB canvas composite op / PSD enum key -> psd_tools BlendMode member name
_BLEND_TO_PSD = {
    "normal": "NORMAL", "source-over": "NORMAL", "multiply": "MULTIPLY", "screen": "SCREEN",
    "overlay": "OVERLAY", "darken": "DARKEN", "lighten": "LIGHTEN", "color_dodge": "COLOR_DODGE",
    "color-dodge": "COLOR_DODGE", "color_burn": "COLOR_BURN", "color-burn": "COLOR_BURN",
    "hard_light": "HARD_LIGHT", "hard-light": "HARD_LIGHT", "soft_light": "SOFT_LIGHT",
    "soft-light": "SOFT_LIGHT", "difference": "DIFFERENCE", "exclusion": "EXCLUSION",
    "hue": "HUE", "saturation": "SATURATION", "color": "COLOR", "luminosity": "LUMINOSITY",
    # [SPB-TLAY2 2026-10-10 L2-4] group-only: a pass-through group (SPB group mode) is PSD's "pass through" blend
    "pass-through": "PASS_THROUGH", "pass_through": "PASS_THROUGH", "passthrough": "PASS_THROUGH",
}


def blend_key(psd_blend) -> str:
    """psd_tools BlendMode -> the lowercase key SPB's importer already understands."""
    return str(psd_blend).replace("BlendMode.", "").strip().lower()


def _psd_blend(key):
    from psd_tools.constants import BlendMode
    name = _BLEND_TO_PSD.get(str(key or "normal").lower(), "NORMAL")
    return getattr(BlendMode, name)


def _pixel_layer(psd, img, name, top, left):
    """RGBA PixelLayer WITHOUT psd_tools' frompil mask: in an RGB-mode PSD frompil turns the
    alpha into a user mask and the layer reads back opaque. Build the record directly so alpha is
    the layer's real transparency channel (what Photoshop and PhotoCraft expect)."""
    from psd_tools.api.layers import PixelLayer
    from psd_tools.constants import Compression
    img = img.convert("RGBA")
    rec, chans = PixelLayer._build_layer_record_and_channels(
        img, name, int(left), int(top), Compression.RLE, version=psd._record.header.version)
    layer = PixelLayer(psd, rec, chans)
    psd.append(layer)
    return layer


def build_psd(path, width, height, layers, spec=None, groups=None):
    """Write a layered 8-bit RGB PSD. `layers` bottom-first. `spec` = optional RGBA PIL
    image (R metallic, G roughness, B clearcoat, A spec mask) written as a 4-layer group
    on top, hidden. `groups` (optional, [SPB-TLAY2 2026-10-10 L2-4]) = [{"path": [names], "opacity": 0-255,
    "blend": key, "visible": bool, "pass_through": bool}] so a group keeps its opacity / blend / visibility
    in PhotoCraft instead of silently showing at 100% normal. Returns {"layers": n, "path": path}."""
    from psd_tools import PSDImage
    psd = PSDImage.new("RGB", (int(width), int(height)))
    groups_made = {}  # tuple(group_path) -> Group
    gmeta = {}
    for g in (groups or []):
        try:
            gmeta.setdefault(tuple(str(x) for x in (g.get("path") or [])), g)
        except Exception:
            pass

    def parent_for(gpath):
        gpath = tuple(gpath or ())
        if not gpath:
            return psd
        if gpath in groups_made:
            return groups_made[gpath]
        parent = parent_for(gpath[:-1])
        grp = psd.create_group(name=gpath[-1])
        # create_group appends to the document; move into its parent group when nested
        if parent is not psd:
            psd.remove(grp)
            parent.append(grp)
        groups_made[gpath] = grp
        gm = gmeta.get(gpath)
        if gm:   # [SPB-TLAY2 2026-10-10 L2-4] carry the group's own opacity / blend / visibility
            try:
                grp.opacity = int(max(0, min(255, gm.get("opacity", 255))))
                grp.blend_mode = _psd_blend("pass-through" if gm.get("pass_through") else gm.get("blend"))
                grp.visible = bool(gm.get("visible", True))
            except Exception:
                pass
        return grp

    for lay in layers:
        img = lay["rgba"].convert("RGBA")
        left, top = int(lay["bbox"][0]), int(lay["bbox"][1])
        pl = _pixel_layer(psd, img, lay.get("name") or "Layer", top, left)
        pl.opacity = int(max(0, min(255, lay.get("opacity", 255))))
        pl.blend_mode = _psd_blend(lay.get("blend"))
        pl.visible = bool(lay.get("visible", True))
        if lay.get("clipping"):
            pl.clipping = True
        parent_for(lay.get("group_path")).append(pl)

    if spec is not None:
        arr = np.array(spec.convert("RGBA"))
        grp = psd.create_group(name=SPEC_GROUP)
        for ch, nm in enumerate(SPEC_LAYERS):
            g = arr[:, :, ch]
            rgba = Image.fromarray(np.dstack([g, g, g, np.full_like(g, 255)]), "RGBA")
            pl = _pixel_layer(psd, rgba, nm, 0, 0)
            grp.append(pl)
        grp.visible = False
    psd.save(path)
    return {"layers": len(layers), "path": path}


def walk_order(layers):
    """[SPB-TLAY2 2026-10-10 L2-4] Indexes into `layers` (bottom-first, as sent) in the order read_psd() will return
    them. A group sits where its FIRST member was added, and all its members follow it, so when members of a group are
    not contiguous in the sent list the saved file's order differs from the sent order. The route keeps a
    baseline-index -> SPB-layer-id table; without this it would hand a PhotoCraft edit to the WRONG SPB layer."""
    root = []                      # items: ("L", idx) or ("G", node)
    nodes = {}

    def node_for(gpath):
        if not gpath:
            return root
        if gpath in nodes:
            return nodes[gpath]["items"]
        parent = node_for(gpath[:-1])
        nd = {"items": []}
        nodes[gpath] = nd
        parent.append(("G", nd))
        return nd["items"]

    for i, lay in enumerate(layers):
        node_for(tuple(lay.get("group_path") or ())).append(("L", i))
    out = []

    def flat(items):
        for kind, v in items:
            if kind == "L":
                out.append(v)
            else:
                flat(v["items"])
    flat(root)
    return out


def _walk(node, gpath=()):
    for layer in node:
        if layer.is_group():
            yield from _walk(layer, gpath + (layer.name,))
        else:
            yield gpath, layer


def _group_props(psd):
    """[SPB-TLAY2 2026-10-10 L2-4] {tuple(path): {opacity, blend, visible}} for every group except the SPEC group."""
    res = {}

    def rec(node, gpath):
        for layer in node:
            if layer.is_group():
                gp = gpath + (layer.name,)
                if gp[0] != SPEC_GROUP:
                    res.setdefault(gp, {"opacity": int(layer.opacity), "blend": blend_key(layer.blend_mode),
                                        "visible": bool(layer.visible)})
                rec(layer, gp)
    try:
        rec(psd, ())
    except Exception:
        pass
    return res


def diff_groups(base_doc, new_doc):
    """[SPB-TLAY2 2026-10-10 L2-4] Group-level changes made in PhotoCraft (opacity / blend / visibility / a group that
    is gone or renamed). SPB does not apply these (a group is more than a folder there), so the route reports them and
    the client says so out loud instead of dropping them silently. -> [{"path": [...], "fields": [...]}]"""
    b, n = base_doc.get("groups") or {}, new_doc.get("groups") or {}
    out = []
    for path, bp in b.items():
        np_ = n.get(path)
        if np_ is None:
            out.append({"path": list(path), "fields": ["removed-or-renamed"]})
            continue
        f = [k for k in ("opacity", "blend", "visible") if bp.get(k) != np_.get(k)]
        if f:
            out.append({"path": list(path), "fields": f})
    return out


def read_psd(path):
    """Return {"width","height","layers":[...bottom-first...], "spec": RGBA PIL or None,
    "icc": bool}. Layers inside the SPEC group are not returned as paint layers."""
    from psd_tools import PSDImage

    psd = PSDImage.open(path)
    out, spec_planes = [], {}
    for gpath, layer in _walk(psd):
        im = layer.topil()
        if gpath and gpath[0] == SPEC_GROUP:
            if im is not None and layer.name in SPEC_LAYERS:
                full = Image.new("RGBA", (psd.width, psd.height), (0, 0, 0, 255))
                full.alpha_composite(im.convert("RGBA"), (max(0, layer.left), max(0, layer.top))) \
                    if layer.left >= 0 and layer.top >= 0 else None
                spec_planes[layer.name] = np.array(full.convert("L"))
            continue
        if im is None:
            im = Image.new("RGBA", (max(1, layer.width), max(1, layer.height)), (0, 0, 0, 0))
        out.append({
            "name": layer.name, "group_path": list(gpath), "visible": bool(layer.visible),
            "opacity": int(layer.opacity), "blend": blend_key(layer.blend_mode),
            "clipping": bool(layer.clipping),
            "bbox": [int(layer.left), int(layer.top), int(layer.left + im.width), int(layer.top + im.height)],
            "rgba": im.convert("RGBA"),
        })
    spec = None
    if len(spec_planes) == 4:
        spec = Image.fromarray(np.dstack([spec_planes[n] for n in SPEC_LAYERS]), "RGBA")
    icc = False
    try:
        icc = 1039 in psd.image_resources  # ICC profile resource id
    except Exception:
        pass
    return {"width": psd.width, "height": psd.height, "layers": out, "spec": spec, "icc": icc,
            "groups": _group_props(psd)}   # [SPB-TLAY2 2026-10-10 L2-4] additive key


def layer_full_canvas(lay, width, height):
    """Layer pixels placed on a transparent width x height canvas (np uint8 HxWx4)."""
    canvas = Image.new("RGBA", (int(width), int(height)), (0, 0, 0, 0))
    l, t = lay["bbox"][0], lay["bbox"][1]
    canvas.paste(lay["rgba"], (l, t))  # paste (not composite) keeps exact RGBA, clips offscreen
    return np.array(canvas)


def pixel_diff(a, b):
    """Compare two HxWx4 uint8 arrays the way a painter sees them: alpha exact, RGB only
    where either side has alpha>0 (RGB under alpha=0 is invisible and editor-dependent).
    Returns (max_abs_diff, mean_abs_diff_over_visible, n_visible_px)."""
    d = np.abs(a.astype(np.int16) - b.astype(np.int16))
    vis = (a[:, :, 3] > 0) | (b[:, :, 3] > 0)
    dd = np.concatenate([d[:, :, :3][vis].reshape(-1, 3), d[:, :, 3][vis].reshape(-1, 1)], axis=1) if vis.any() else np.zeros((0, 4))
    alpha_max = int(d[:, :, 3].max()) if d.size else 0
    mx = int(max(alpha_max, dd.max() if dd.size else 0))
    mean = float(dd.mean()) if dd.size else 0.0
    return mx, mean, int(vis.sum())


def diff_against_baseline(base_doc, new_doc):
    """Match new layers to baseline layers (same group path + name, in order) and report.
    Returns dict(changed=[idx_in_new...], same=[...], added=[...], removed=[baseline idx...],
    pairs={new_idx: base_idx}, meta_changed={new_idx: [fields]})."""
    W, H = base_doc["width"], base_doc["height"]
    used = set()
    pairs = {}
    for ni, nl in enumerate(new_doc["layers"]):
        for bi, bl in enumerate(base_doc["layers"]):
            if bi in used:
                continue
            if bl["name"] == nl["name"] and bl["group_path"] == nl["group_path"]:
                used.add(bi)
                pairs[ni] = bi
                break
    res = {"pairs": pairs, "changed": [], "same": [], "added": [], "meta_changed": {}, "removed": [], "stats": {}}
    for ni, nl in enumerate(new_doc["layers"]):
        if ni not in pairs:
            res["added"].append(ni)
            continue
        bl = base_doc["layers"][pairs[ni]]
        meta = [k for k in ("visible", "opacity", "blend") if bl[k] != nl[k]]
        if meta:
            res["meta_changed"][ni] = meta
        mx, mean, nvis = pixel_diff(layer_full_canvas(bl, W, H), layer_full_canvas(nl, W, H))
        res["stats"][ni] = {"max": mx, "mean": round(mean, 4), "visible_px": nvis}
        (res["changed"] if mx > 0 else res["same"]).append(ni)
    res["removed"] = [bi for bi in range(len(base_doc["layers"])) if bi not in used]
    return res
