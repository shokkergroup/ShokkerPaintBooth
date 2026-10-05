"""Runtime wave multiplier for overnight finish iteration.

Each worker tick bumps `wave` in _loop_state/overnight_wave.json.
Renderers read wave_mult() to escalate spec/glint/flake strength per cycle.
"""
from __future__ import annotations

import json
from pathlib import Path

_WAVE_FILE = Path(__file__).resolve().parent.parent / "_loop_state" / "overnight_wave.json"

_RAMP = {
    "spec": 0.045,
    "flake": 0.085,
    "glint": 0.065,
    "shift": 0.055,
    "sparkle": 0.07,
}


def _load() -> dict:
    if not _WAVE_FILE.exists():
        return {"wave": 1, "last_portal": "", "last_batch": []}
    try:
        return json.loads(_WAVE_FILE.read_text(encoding="utf-8") or "{}")
    except Exception:
        return {"wave": 1, "last_portal": "", "last_batch": []}


def current_wave() -> int:
    return max(1, int(_load().get("wave", 1)))


def wave_mult(base: float = 1.0, key: str = "spec") -> float:
    w = current_wave()
    ramp = _RAMP.get(key, 0.04)
    return float(base) * (1.0 + (w - 1) * ramp)


def bump_wave(portal_slug: str, batch: list[str]) -> int:
    data = _load()
    data["wave"] = max(1, int(data.get("wave", 1)) + 1)
    data["last_portal"] = portal_slug
    data["last_batch"] = list(batch)
    _WAVE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _WAVE_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return int(data["wave"])
