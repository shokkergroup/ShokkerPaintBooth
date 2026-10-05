from __future__ import annotations

import json
import subprocess
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent


def test_psd_layer_overlay_payload_matrix_runtime_harness():
    result = subprocess.run(
        ["node", "tests/_runtime_harness/psd_layer_overlay_payload.mjs"],
        cwd=REPO,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
