#!/usr/bin/env python3
"""Measure the real /preview-render transport at native 2048 resolution.

The probe deliberately uses the public HTTP route instead of importing the
engine so JSON/base64 transport costs are included in the timing.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import statistics
import time
from pathlib import Path

import requests
from PIL import Image


def _data_url(path: Path) -> tuple[str, tuple[int, int], int]:
    with Image.open(path) as source:
        rgb = source.convert("RGB")
        size = rgb.size
        out = io.BytesIO()
        rgb.save(out, "PNG", compress_level=1)
    raw = out.getvalue()
    return "data:image/png;base64," + base64.b64encode(raw).decode("ascii"), size, len(raw)


def _preview_hash(value: str) -> str:
    encoded = value.split(",", 1)[-1]
    return hashlib.sha256(base64.b64decode(encoded)).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True, help="Full /preview-render URL")
    parser.add_argument("--paint", type=Path, required=True)
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument(
        "--transport",
        choices=("inline", "token"),
        default="inline",
        help="token sends the image once and reuses the returned opaque token",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    source, dimensions, png_bytes = _data_url(args.paint)
    if dimensions != (2048, 2048):
        raise SystemExit(f"native-2048 probe requires 2048x2048 input, got {dimensions}")

    base_payload = {
        "preview_scale": 1.0,
        "seed": 51,
        "settings": {},
        "zones": [
            {
                "name": "Native 2048 transport probe",
                "color": "remaining",
                "intensity": 100,
                "base": "gloss",
                "pattern": "none",
                "base_color_mode": "source",
                "base_color_strength": 1,
                "hard_edge": True,
            }
        ],
    }
    session = requests.Session()
    token = None
    paint_sig = None
    spec_sig = None
    rows: list[dict] = []
    expected_hashes = None

    for index in range(args.runs):
        payload = dict(base_payload)
        if paint_sig:
            payload["client_paint_sig"] = paint_sig
        if spec_sig:
            payload["client_spec_sig"] = spec_sig
        if args.transport == "token" and token:
            payload["paint_source_token"] = token
        else:
            payload["paint_image_base64"] = source
        encoded_size = len(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
        started = time.perf_counter()
        response = session.post(args.url, json=payload, timeout=120)
        wall_ms = (time.perf_counter() - started) * 1000
        response.raise_for_status()
        data = response.json()
        if not data.get("success"):
            raise RuntimeError(data)
        token = data.get("paint_source_token") or token
        paint_sig = data.get("paint_sig") or paint_sig
        spec_sig = data.get("spec_sig") or spec_sig
        if data.get("paint_preview") and data.get("spec_preview"):
            hashes = (_preview_hash(data["paint_preview"]), _preview_hash(data["spec_preview"]))
            if expected_hashes is None:
                expected_hashes = hashes
            if hashes != expected_hashes:
                raise RuntimeError("preview pixels changed across identical probe requests")
        elif not (data.get("paint_unchanged") and data.get("spec_unchanged")):
            raise RuntimeError("server omitted preview pixels without unchanged signatures")
        rows.append(
            {
                "run": index + 1,
                "wall_ms": round(wall_ms, 2),
                "request_bytes": encoded_size,
                "response_bytes": len(response.content),
                "engine_ms": data.get("elapsed_ms"),
                "server_total_ms": data.get("server_total_ms"),
                "source_transport": data.get("source_transport", "inline-legacy"),
            }
        )

    walls = [row["wall_ms"] for row in rows]
    result = {
        "url": args.url,
        "paint": str(args.paint.resolve()),
        "dimensions": list(dimensions),
        "source_png_bytes": png_bytes,
        "transport": args.transport,
        "runs": rows,
        "wall_ms_median": round(statistics.median(walls), 2),
        "wall_ms_mean": round(statistics.fmean(walls), 2),
        "preview_hashes": list(expected_hashes or ()),
        "token_returned": bool(token),
    }
    rendered = json.dumps(result, indent=2)
    print(rendered)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
