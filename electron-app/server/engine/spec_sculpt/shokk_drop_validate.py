"""SHOKK DROP — uploaded spec-map iron-rule VALIDATION (advisory, 2026-06-18 overnight).

ADDITIVE + WARN-ONLY. Given the R/G/B channels a guest uploaded (R=Metallic, G=Roughness,
B=Clearcoat), report where iRacing's PBR shader tends to render poorly — clearcoat in the
1–15 whitewash band, sub-floor roughness on non-mirror panels, huge full-chrome areas, dead-flat
channels. It NEVER changes a single byte: the SHOKK DROP exact/`authored_set` path renders
VERBATIM and stays sacred. This just informs the creator so they can fix it *in their source art*
if they want. Nothing here imports or touches `user_imports` / the ingest / the render path.

Thresholds mirror the engine's own iron rules (`shokker_engine_v2._enforce_iron_rules`):
CC_FLOOR=16 (clearcoat 0=matte, 1–15=whitewash), ROUGHNESS_FLOOR_NONMIRROR=15, CHROME_M_THRESHOLD=240.
"""
from __future__ import annotations

import numpy as np

# Single source of truth: pull the live iron-rule constants; fall back to known values.
try:
    from shokker_engine_v2 import CC_FLOOR, ROUGHNESS_FLOOR_NONMIRROR, CHROME_M_THRESHOLD
except Exception:  # pragma: no cover - fallback keeps the validator usable in isolation
    CC_FLOOR, ROUGHNESS_FLOOR_NONMIRROR, CHROME_M_THRESHOLD = 16, 15, 240


def _chan(a):
    """Coerce a channel to float32 HxW in 0..255 (accept 0..1 floats too)."""
    arr = np.asarray(a, dtype=np.float32)
    if arr.ndim == 3:
        arr = arr[:, :, 0]
    if arr.size and arr.max() <= 1.0001:
        arr = arr * 255.0
    return arr


def validate_spec_channels(metallic, roughness, clearcoat, *, warn_pct: float = 0.5):
    """Return an advisory report on uploaded spec channels. WARN-ONLY — alters nothing.

    Args:
        metallic/roughness/clearcoat: HxW arrays (0..255 or 0..1). R=M, G=Rough, B=Cc.
        warn_pct: minimum % of pixels for a band/floor issue to be reported.

    Returns:
        dict: {"ok": bool, "warnings": [{code, severity, pct, message}], "stats": {...}}.
        ok=True means no warnings (clean for iRacing PBR).
    """
    M, R, CC = _chan(metallic), _chan(roughness), _chan(clearcoat)
    n = max(1, M.size)
    warnings = []

    def pct(mask):
        return round(100.0 * float(np.count_nonzero(mask)) / n, 2)

    # 1) Clearcoat whitewash band: 0 < Cc < CC_FLOOR (in-sim wash-out).
    cc_band = (CC > 0) & (CC < CC_FLOOR)
    p = pct(cc_band)
    if p >= warn_pct:
        warnings.append({
            "code": "cc_whitewash_band", "severity": "warn", "pct": p,
            "message": (f"{p}% of pixels have Clearcoat in the 1–{CC_FLOOR - 1} band — this tends to "
                        f"whitewash in iRacing. Use 0 (matte) or ≥{CC_FLOOR} (true clearcoat)."),
        })

    # 2) Sub-floor roughness on non-mirror panels (reads unnaturally glossy / plasticky).
    nonmirror_lowrough = (M < CHROME_M_THRESHOLD) & (R < ROUGHNESS_FLOOR_NONMIRROR)
    p = pct(nonmirror_lowrough)
    if p >= warn_pct:
        warnings.append({
            "code": "roughness_below_floor", "severity": "warn", "pct": p,
            "message": (f"{p}% of non-mirror pixels have Roughness < {ROUGHNESS_FLOOR_NONMIRROR} — "
                        f"may look too wet/glossy in-sim. iRacing-safe non-mirror roughness is "
                        f"≥{ROUGHNESS_FLOOR_NONMIRROR}."),
        })

    # 3) Large fully-chrome area (fake-chrome look across a whole panel).
    chrome = M >= CHROME_M_THRESHOLD
    p = pct(chrome)
    if p >= 40.0:
        warnings.append({
            "code": "large_chrome_area", "severity": "info", "pct": p,
            "message": (f"{p}% of pixels are full chrome (Metallic ≥ {CHROME_M_THRESHOLD}). Big "
                        f"all-chrome areas can read as fake chrome — intentional is fine, just a heads-up."),
        })

    # 4) Dead-flat channels (no material variation — the spec does nothing interesting).
    for name, ch in (("Metallic", M), ("Roughness", R), ("Clearcoat", CC)):
        if ch.size and float(ch.std()) < 1.0:
            warnings.append({
                "code": "flat_channel", "severity": "info", "pct": 100.0,
                "message": f"{name} channel is essentially flat (std<1) — uniform, no spatial detail.",
            })

    stats = {
        "metallic": {"min": round(float(M.min()), 1), "mean": round(float(M.mean()), 1), "max": round(float(M.max()), 1)},
        "roughness": {"min": round(float(R.min()), 1), "mean": round(float(R.mean()), 1), "max": round(float(R.max()), 1)},
        "clearcoat": {"min": round(float(CC.min()), 1), "mean": round(float(CC.mean()), 1), "max": round(float(CC.max()), 1)},
    }
    return {"ok": len(warnings) == 0, "warnings": warnings, "stats": stats}


def validate_spec_rgba(spec_rgba, **kw):
    """Convenience: validate an HxWx(3|4) spec array (R=M, G=Rough, B=Cc)."""
    s = np.asarray(spec_rgba)
    return validate_spec_channels(s[:, :, 0], s[:, :, 1], s[:, :, 2], **kw)


def format_report(result) -> str:
    """Human-readable advisory text. Emphasises that nothing was changed."""
    lines = ["SHOKK DROP spec check (advisory — your uploaded channels are rendered VERBATIM):"]
    if result.get("ok"):
        lines.append("  ✓ No iRacing-PBR concerns found.")
    else:
        for w in result["warnings"]:
            tag = "⚠" if w["severity"] == "warn" else "ℹ"
            lines.append(f"  {tag} [{w['code']}] {w['message']}")
    st = result.get("stats", {})
    if st:
        lines.append(f"  channels — M {st['metallic']} · Rough {st['roughness']} · Cc {st['clearcoat']}")
    return "\n".join(lines)
