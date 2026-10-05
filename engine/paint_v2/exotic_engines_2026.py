"""exotic_engines_2026 — the 2026-06-21 expanded engine arsenal.

Aggregates every field-generator engine from engine/paint_v2/exotic_packs/* into one
registry. Each engine: fn(h, w, seed, *, res=...) -> np.ndarray float32 in [0,1], (h,w).
Built by the wave-1 (math families) + wave-2 (grunge/street/gothic/tactical/3D-depth/
damage) designers, then dedup + edgy-taste filtered. The owner-curated, dedup-distinct
subset is FINAL (passed both walls); ENGINES holds everything for flexibility.

Usage:  from engine.paint_v2 import exotic_engines_2026 as ex
        field = ex.field("rust_bloom", h, w, seed)
"""
from __future__ import annotations
import importlib
import pkgutil
import numpy as np

from engine.paint_v2 import exotic_packs as _pkg

ENGINES = {}
_COLLISIONS = []
for _m in pkgutil.iter_modules(_pkg.__path__):
    try:
        _mod = importlib.import_module(f"engine.paint_v2.exotic_packs.{_m.name}")
    except Exception as _e:
        print(f"  [exotic_engines] pack {_m.name} import skipped: {_e}")
        continue
    for _nm, _fn in (getattr(_mod, "ENGINES", {}) or {}).items():
        if _nm in ENGINES:
            _COLLISIONS.append(_nm)
            _nm = f"{_m.name[5:]}_{_nm}"          # namespace on collision
        ENGINES[_nm] = _fn


def _norm(a: np.ndarray) -> np.ndarray:
    a = a.astype(np.float32)
    lo = float(a.min()); rng = float(np.ptp(a))
    return np.zeros_like(a) if rng < 1e-9 else (a - lo) / rng


def field(name: str, h: int, w: int, seed: int) -> np.ndarray:
    """Render engine `name` to a normalized 0..1 (h,w) float32 field."""
    fn = ENGINES[name]
    f = np.asarray(fn(h, w, int(seed)), np.float32)
    if f.ndim == 3:
        f = f[..., :3].mean(2)
    if f.shape[:2] != (h, w):
        import cv2
        f = cv2.resize(f, (w, h), interpolation=cv2.INTER_LINEAR)
    return _norm(f)


def names():
    return sorted(ENGINES.keys())


if __name__ == "__main__":
    print(f"exotic_engines_2026: {len(ENGINES)} engines loaded", "| collisions:", _COLLISIONS)
    print(", ".join(names()))
