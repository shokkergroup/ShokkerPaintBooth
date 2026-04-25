import json
import subprocess
import sys
from pathlib import Path

import pytest


REPO = Path(__file__).resolve().parent.parent


def _clean_server_boot_payload():
    code = r"""
import contextlib
import io
import json

buf = io.StringIO()
with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
    import server_v5
    import engine.registry as registry

ids = [
    "hex_mandala",
    "lace_filigree",
    "honeycomb_organic",
    "baroque_scrollwork",
    "art_nouveau_vine",
    "penrose_quasi",
    "topographic_dense",
    "interference_rings",
]
fallback_ids = ["aurora", "sparkle_diamond_dust", "chameleon_deep_ocean", "prizm_galaxy"]
mono = server_v5.MONOLITHIC_REGISTRY

def fn_name(fn):
    return getattr(fn, "__name__", str(fn))

entries = {}
for mid in ids:
    entry = mono.get(mid)
    entries[mid] = {
        "present": bool(entry),
        "spec_name": fn_name(entry[0]) if entry else None,
        "paint_name": fn_name(entry[1]) if entry else None,
        "same_as_fallback": any(entry is mono.get(fid) for fid in fallback_ids),
        "same_pair_as_fallback": any(
            entry and mono.get(fid) and entry[0] is mono[fid][0] and entry[1] is mono[fid][1]
            for fid in fallback_ids
        ),
        "registry_same_entry": registry.MONOLITHIC_REGISTRY.get(mid) is entry,
    }

payload = {
    "entries": entries,
    "numeric_ids": sorted(k for k in mono if str(k).isdigit()),
}
print(json.dumps(payload, sort_keys=True))
"""
    proc = subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        timeout=120,
    )
    if proc.returncode != 0:
        pytest.fail(
            f"server_v5 clean import failed (exit {proc.returncode})\n"
            f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )
    return json.loads(proc.stdout)


def test_server_boot_preserves_pattern_driven_ornamentals():
    payload = _clean_server_boot_payload()
    bad = {}
    for finish_id, info in payload["entries"].items():
        if (
            not info["present"]
            or "aurora" in str(info["spec_name"]).lower()
            or "aurora" in str(info["paint_name"]).lower()
            or info["same_as_fallback"]
            or info["same_pair_as_fallback"]
            or not info["registry_same_entry"]
        ):
            bad[finish_id] = info
    assert not bad, f"ornamental specials resolved to stale/fallback registry entries: {bad}"


def test_server_boot_does_not_add_numeric_catalog_junk_ids():
    payload = _clean_server_boot_payload()
    assert payload["numeric_ids"] == []
