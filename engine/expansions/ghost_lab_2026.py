# -*- coding: utf-8 -*-
"""GHOST LAB (2026-06-12) — controlled experiments to isolate WHY Ghost
Fracture color-shifts the way it does.

Owner's observations to explain:
  * uncrushed purple -> flashes PURPLE at angle (body color "jumps through")
  * crushed purple   -> wisps of purple + GOLD/AMBER flashes replacing it

Hypothesis (from the measured GF spec: M 187-255 mean 225, G 58-119 glossy,
CC carved 212-148*pattern, swing 124<->240):
  pillar 1: NEAR-MAX METAL EVERYWHERE -> the tinted reflection lobe is huge,
            so even a crushed-to-wisps base color still shows (purple wisps);
            uncrushed, it's the purple flash itself.
  pillar 2: LOW ROUGHNESS -> reflections stay SHARP; flashes are point-like
            detonations instead of soft haze.
  pillar 3: BIG COHERENT CLEARCOAT CELLS -> the paint-INDEPENDENT white lobe
            mirrors the environment per-cell: gold = the SUN, teal = the sky.
            Crushed purple kills the diffuse so the env lobes own the car ->
            gold/amber replaces purple.

Every variant below = the REAL ghost_fracture spec with exactly ONE knob
turned. Identical paint_fn across all 12 -> any on-track difference is the
spec knob, full stop.
"""
import numpy as np
import cv2

from engine.expansions.fusions import spec_ghost_fracture, paint_ghost_fracture

# (id, name, transform-key, what it isolates)
GHOST_LAB_VARIANTS = [
    ("gl_control",      "GL 00 Control (Ghost Fracture)", "control",
     "Byte-identical Ghost Fracture. Your reference — everything else changes ONE thing vs this."),
    ("gl_metal_low",    "GL 01 Metal LOW (~150)", "metal_low",
     "PILLAR 1 TEST: metal dropped to the level our newer finishes use. If the purple stops jumping through, near-max metal is the body-color engine."),
    ("gl_metal_mid",    "GL 02 Metal MID (~185)", "metal_mid",
     "Pillar 1 dose-response: halfway. Tells us the metal threshold where color-jump starts dying."),
    ("gl_rough_pastel", "GL 03 Rough PASTEL (150-200)", "rough_pastel",
     "PILLAR 2 TEST + the pastel doctrine on-track: roughness raised to the light-pastel band. If flashes go soft/hazy, low roughness is what makes them EXPLODE."),
    ("gl_rough_mirror", "GL 04 Rough MIRROR (30-60)", "rough_mirror",
     "Pillar 2 the other direction: glossier than GF. Do flashes get even sharper/harder?"),
    ("gl_cc_flat",      "GL 05 Clearcoat FLAT (no cells)", "cc_flat",
     "PILLAR 3 TEST: same metal+gloss but the carve is GONE (CC uniform 212). If gold still flashes but with no cell pattern, the carve is only the SHAPE; if gold dies, the carve is the engine."),
    ("gl_cc_shallow",   "GL 06 Clearcoat SHALLOW carve", "cc_shallow",
     "Pillar 3 dose-response: carve amplitude halved. How much swing does the two-color travel need?"),
    ("gl_cc_inverted",  "GL 07 Clearcoat INVERTED", "cc_inverted",
     "Cells swap polarity (carved becomes flooded). Should swap WHERE gold vs teal appears — confirms the cells choose which env color shows."),
    ("gl_cells_micro",  "GL 08 Cells MICRO (3x smaller)", "cells_micro",
     "Structure scale: same recipe, 3x finer cells. Does fine structure shimmer instead of detonate?"),
    ("gl_cells_macro",  "GL 09 Cells MACRO (3x bigger)", "cells_macro",
     "Structure scale: 3x bigger cells. Do big panels flash harder but read blocky?"),
    ("gl_pastel_full",  "GL 10 Full PASTEL recipe", "pastel_full",
     "The round-5 pastel doctrine applied to GF geometry (rough 150-170, compressed carve 191-240). Head-to-head vs GL 00 settles whether pastel beats the original on track."),
    ("gl_cc_max",       "GL 11 Clearcoat MAX carve", "cc_max",
     "Carve amplitude pushed to the rails (cells swing 40<->250). Is more swing more magic, or does it clip into noise?"),
]


def _mk_variant(key):
    def spec_fn(shape, mask, seed, sm):
        base = spec_ghost_fracture(shape, mask, seed, sm)
        out = np.asarray(base, np.float32).copy()
        M, G, B = out[:, :, 0], out[:, :, 1], out[:, :, 2]
        if key == "control":
            pass
        elif key == "metal_low":
            out[:, :, 0] = np.clip(M - 75.0, 0, 255)
        elif key == "metal_mid":
            out[:, :, 0] = np.clip(M - 40.0, 0, 255)
        elif key == "rough_pastel":
            out[:, :, 1] = np.clip(150.0 + (G - 58.0) * 0.8, 130, 205)
        elif key == "rough_mirror":
            out[:, :, 1] = np.clip(G * 0.5, 25, 255)
        elif key == "cc_flat":
            out[:, :, 2] = np.where(np.asarray(mask, np.float32)[..., 0] > 0.5 if np.asarray(mask).ndim == 3 else np.asarray(mask, np.float32) > 0.5, 212.0, B)
        elif key == "cc_shallow":
            out[:, :, 2] = np.clip(212.0 + (B - 212.0) * 0.5, 16, 255)
        elif key == "cc_inverted":
            out[:, :, 2] = np.clip(364.0 - B, 16, 255)
        elif key == "cc_max":
            out[:, :, 2] = np.clip(212.0 + (B - 212.0) * 1.95, 40, 250)
        elif key == "pastel_full":
            out[:, :, 1] = np.clip(150.0 + (G - 58.0) * 0.35, 140, 185)
            out[:, :, 2] = np.clip(240.0 - (240.0 - B) * 0.42, 16, 255)
        elif key == "cells_micro":
            small = cv2.resize(out, (max(2, shape[1] // 3), max(2, shape[0] // 3)), interpolation=cv2.INTER_AREA)
            out = np.tile(small, (4, 4, 1))[: shape[0], : shape[1], :]
        elif key == "cells_macro":
            h3, w3 = shape[0] // 3, shape[1] // 3
            crop = out[h3: 2 * h3, w3: 2 * w3, :]
            out = cv2.resize(crop, (shape[1], shape[0]), interpolation=cv2.INTER_LINEAR)
        return np.clip(out, 0, 255).astype(np.uint8)

    return spec_fn


def install_into_engine(mono_reg):
    n = 0
    try:
        import engine.expansions.fusions as _fus
        for fid, _name, key, _desc in GHOST_LAB_VARIANTS:
            entry = (_mk_variant(key), paint_ghost_fracture)
            mono_reg[fid] = entry
            _fus.FUSION_REGISTRY[fid] = entry
            n += 1
    except Exception:
        for fid, _name, key, _desc in GHOST_LAB_VARIANTS:
            mono_reg[fid] = (_mk_variant(key), paint_ghost_fracture)
            n += 1
    return f"ghost-lab: {n} single-variable Ghost Fracture experiments live"
