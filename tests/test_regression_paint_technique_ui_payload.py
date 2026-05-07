"""SPB-7 browser-path regression coverage for Paint Technique bases."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest


def test_paint_technique_picker_keeps_source_paint_payload():
    """The JS picker path must not flatten Paint Technique bases to swatches."""

    if shutil.which("node") is None:
        pytest.skip("node not available; skipping JS picker payload harness")

    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        ["node", str(root / "tests" / "_runtime_harness" / "paint_technique_picker_payload.mjs")],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    payload = json.loads(result.stdout)
    assert len(payload["rows"]) == 6
    assert {row["payload_base_color_mode"] for row in payload["rows"]} == {"source"}
