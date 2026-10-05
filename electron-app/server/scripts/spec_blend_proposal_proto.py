# Prototype: PHYSICAL spec blend modes vs today's Photoshop modes.
# Renders a labeled sheet: base spec alone, today's best (screen/overlay),
# then 6 proposed physics modes. Two rows: classic base+pattern, FM base+pattern.
import sys
import numpy as np
import cv2
sys.path.insert(0, '.')
import shokker_engine_v2 as E
from engine.compose import compose_finish_stacked
from engine.registry import BASE_REGISTRY, PATTERN_REGISTRY

S = 512
mask = np.ones((S, S), np.float32)


def base_spec(bid):
    if bid in BASE_REGISTRY:
        sp = compose_finish_stacked(bid, [], (S, S), mask, 42, 1.0,
                                    monolithic_registry=E.MONOLITHIC_REGISTRY)
    else:
        sp = E.MONOLITHIC_REGISTRY[bid][0]((S, S), mask, 42, 1.0)
    return np.asarray(sp, np.float32)[:, :, :3]


def pattern_field(pid):
    tex = PATTERN_REGISTRY[pid]["texture_fn"]((S, S), mask, 7, 1.0)
    pv = np.asarray(tex["pattern_val"], np.float32)
    pv -= pv.min()
    return pv / max(pv.max(), 1e-6)


def todays_overlay(sp, pv):
    # what the current code does in its strongest useful mode (overlay, M/R only)
    out = sp.copy()
    for ch, rng in ((0, 50.0), (1, 60.0)):
        b = out[:, :, ch] / 255.0
        p = np.clip((pv - 0.5) + 0.5, 0, 1)
        ov = np.where(b < 0.5, 2 * b * p, 1 - 2 * (1 - b) * (1 - p))
        out[:, :, ch] = np.clip(ov * 255.0, 0, 255)
    return out


def m_carve(sp, pv):       # GHOST CARVE: pattern cuts env-mirror cells into clearcoat
    out = sp.copy()
    out[:, :, 2] = np.clip(sp[:, :, 2] + 150 * (pv - 0.72), 0, 255)  # carve lows, flood highs
    out[:, :, 1] = np.clip(sp[:, :, 1] - 25 * pv, 16, 255)
    return out


def m_chrome(sp, pv):      # CHROME INLAY: blue-insight dielectric mirror where pattern is hot
    hot = np.clip(pv * 1.6 - 0.6, 0, 1)
    out = sp.copy()
    out[:, :, 0] = np.clip(sp[:, :, 0] * (1 - 0.85 * hot), 0, 255)
    out[:, :, 1] = np.clip(sp[:, :, 1] * (1 - 0.65 * hot) + 30 * (1 - hot) * 0, 16, 255)
    out[:, :, 2] = np.clip(sp[:, :, 2] + (245 - sp[:, :, 2]) * hot, 0, 255)
    return out


def m_etch(sp, pv):        # FROST ETCH: pattern sandblasts the gloss (R up, M slight down)
    out = sp.copy()
    out[:, :, 1] = np.clip(sp[:, :, 1] + 150 * pv, 16, 255)
    out[:, :, 0] = np.clip(sp[:, :, 0] - 45 * pv, 0, 255)
    out[:, :, 2] = np.clip(sp[:, :, 2] - 35 * pv, 16, 255)
    return out


def m_flip(sp, pv):        # ANGLE FLIP: pattern flashes at one angle, its negative at another
    s = (pv - 0.5) * 2.0
    out = sp.copy()
    out[:, :, 0] = np.clip(sp[:, :, 0] + 85 * s, 0, 255)
    out[:, :, 2] = np.clip(sp[:, :, 2] - 135 * s, 16, 255)
    return out


def m_ember(sp, pv):       # EMBER GATE: only the pattern's top ridges ignite (CC pin + gloss)
    g = np.clip((pv - 0.80) / 0.06, 0, 1)
    out = sp.copy()
    out[:, :, 2] = np.clip(sp[:, :, 2] + (252 - sp[:, :, 2]) * g, 0, 255)
    out[:, :, 1] = np.clip(sp[:, :, 1] * (1 - g) + 34 * g, 16, 255)
    return out


def m_emboss(sp, pv):      # DEPTH PRESS: pattern stamped INTO the paint (lit/shadow spec rims)
    gx = cv2.Sobel(cv2.GaussianBlur(pv, (0, 0), 1.2), cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(cv2.GaussianBlur(pv, (0, 0), 1.2), cv2.CV_32F, 0, 1, ksize=3)
    e = (gx + gy) * 0.7071
    e = e / max(float(np.abs(e).max()), 1e-6)
    out = sp.copy()
    out[:, :, 0] = np.clip(sp[:, :, 0] + 110 * np.clip(e, 0, 1) - 70 * np.clip(-e, 0, 1), 0, 255)
    out[:, :, 2] = np.clip(sp[:, :, 2] + 90 * np.clip(e, 0, 1), 16, 255)
    return out


MODES = [("BASE ALONE", None), ("today: overlay", todays_overlay),
         ("GHOST CARVE", m_carve), ("CHROME INLAY", m_chrome), ("FROST ETCH", m_etch),
         ("ANGLE FLIP", m_flip), ("EMBER GATE", m_ember), ("DEPTH PRESS", m_emboss)]

CASES = [("metallic + carbon_fiber", "metallic", "carbon_fiber"),
         ("fm_python_skin + carbon_fiber", "fm_python_skin", "carbon_fiber")]

CELL = 300
rows = []
for title, bid, pid in CASES:
    sp = base_spec(bid)
    pv = pattern_field(pid)
    tiles = []
    for label, fn in MODES:
        t = sp if fn is None else fn(sp, pv)
        img = cv2.resize(t.astype(np.uint8), (CELL, CELL), interpolation=cv2.INTER_AREA)
        bar = np.zeros((24, CELL, 3), np.uint8)
        cv2.putText(bar, label, (6, 17), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (240, 240, 240), 1, cv2.LINE_AA)
        tiles.append(np.concatenate([bar, img], axis=0))
    row = np.concatenate(tiles, axis=1)
    head = np.zeros((26, row.shape[1], 3), np.uint8)
    cv2.putText(head, title + "   (spec view: R=metal, G=rough, B=clearcoat)", (8, 18),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (140, 220, 255), 1, cv2.LINE_AA)
    rows.append(np.concatenate([head, row], axis=0))

sheet = np.concatenate(rows, axis=0)
cv2.imwrite("SPEC_BLEND_PROPOSAL.png", cv2.cvtColor(sheet, cv2.COLOR_RGB2BGR))
print("wrote SPEC_BLEND_PROPOSAL.png", sheet.shape)
