"""Produce native-source evidence for one staged FRACTURED HOUDINI route.

The paint panel proves no visible motif was authored in RGB; the combined map
and grazing panel are diagnostics for material-only behavior.  Neither panel
is an iRacing track-light substitute, so this tool never marks a card live.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine.expansions.fractured_houdini_2026 import LIVE_PAIRS  # noqa: E402


def grazing(spec: np.ndarray, weights: tuple[float, float, float] = (.70, .55, .35)) -> np.ndarray:
    metal = spec[..., 0].astype(np.float32) / 255.0
    rough = spec[..., 1].astype(np.float32) / 255.0
    coat = spec[..., 2].astype(np.float32) / 255.0
    wm, wc, wr = weights
    response = wm * metal + wc * coat + wr * (1.0 - rough)
    lo, hi = np.percentile(response, (1, 99))
    return cv2.applyColorMap(np.clip((response - lo) * 255 / max(hi - lo, 1e-5), 0, 255).astype(np.uint8), cv2.COLORMAP_TURBO)


def paint_colored_material_sim(paint_rgb: np.ndarray, spec: np.ndarray, grazing_light: bool) -> np.ndarray:
    """Conservative flat-panel material response diagnostic, never track proof.

    No normal/track environment exists here, so this intentionally answers only
    whether neighbouring metallic/rough/coat states separate in a paint-colour
    render as light moves from broad neutral to a hard glancing reflection.
    """
    paint = paint_rgb.astype(np.float32) / 255.0
    metal, rough, coat = (spec[..., n].astype(np.float32) / 255.0 for n in range(3))
    diffuse = paint * (.21 + .44*(1.0-metal))[..., None]
    gloss = np.power(np.clip(1.0-rough, 0, 1), .72)
    if grazing_light:
        reflection = (.06 + .94*metal) * (.16 + .84*gloss) * (.16 + .84*coat)
        clear = np.power(coat, 1.45) * (.25 + .75*gloss)
    else:
        reflection = (.04 + .36*metal) * (.12 + .43*gloss) * (.16 + .30*coat)
        clear = np.power(coat, 1.75) * (.05 + .24*gloss)
    # Slight cool skylight and neutral clear lobe; RGB paint remains visible.
    sky = np.array((.36, .54, .92), np.float32)
    out = diffuse + sky[None, None, :]*reflection[..., None]*.54 + clear[..., None]*.26
    return np.clip(np.power(np.clip(out, 0, 1), 1/1.08)*255, 0, 255).astype(np.uint8)


def response_profile(spec: np.ndarray, weights: tuple[float, float, float, float]) -> np.ndarray:
    """Grayscale material state response for controlled, non-track comparisons."""
    metal = spec[..., 0].astype(np.float32)
    rough = spec[..., 1].astype(np.float32)
    coat = spec[..., 2].astype(np.float32)
    wm, wg, ws, wc = weights
    value = wm*metal + wg*(255.0-rough) + ws*rough + wc*coat
    lo, hi = np.percentile(value, (1, 99))
    return np.clip((value-lo)*255/max(hi-lo, 1e-5), 0, 255).astype(np.uint8)


def strongest_material_detail(spec: np.ndarray, size: int = 384) -> np.ndarray:
    """Return an actual native-resolution combined-spec crop for owner-eye QA."""
    response = (.70 * spec[..., 0].astype(np.float32) + .55 * spec[..., 2].astype(np.float32)
                + .35 * (255.0 - spec[..., 1].astype(np.float32)))
    probe = cv2.resize(response, (64, 64), interpolation=cv2.INTER_AREA)
    py, px = np.unravel_index(np.argmax(probe), probe.shape)
    h, w = spec.shape[:2]
    cx, cy = int((px + .5) * w / 64), int((py + .5) * h / 64)
    x0 = int(np.clip(cx - size // 2, 0, w - size)); y0 = int(np.clip(cy - size // 2, 0, h - size))
    return cv2.cvtColor(spec[y0:y0 + size, x0:x0 + size], cv2.COLOR_RGB2BGR)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("finish_id", choices=sorted(LIVE_PAIRS))
    parser.add_argument("--size", type=int, default=2048)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    spec_fn, paint_fn = LIVE_PAIRS[args.finish_id]
    shape = (args.size, args.size)
    source = np.full((args.size, args.size, 3), 132, np.uint8)
    mask = np.full(shape, 255, np.uint8)
    started = time.perf_counter()
    spec = spec_fn(shape, args.seed)
    paint = paint_fn(source, shape, mask, args.seed, 1.0, None)
    elapsed = time.perf_counter() - started
    paint_u8 = np.clip(paint * 255 if paint.max() <= 1.5 else paint, 0, 255).astype(np.uint8)
    # Author paint is RGB; cv2's writer/panel convention is BGR.  Convert so
    # the proof carrier hue matches the actual staged thumbnail.
    paint_bgr = cv2.cvtColor(paint_u8, cv2.COLOR_RGB2BGR)
    combined = cv2.cvtColor(spec, cv2.COLOR_RGB2BGR)
    detail = strongest_material_detail(spec)
    panels = [cv2.resize(panel, (512, 512), interpolation=cv2.INTER_AREA) for panel in (paint_bgr, combined, grazing(spec), detail)]
    sheet = np.concatenate(panels, axis=1)
    cv2.putText(sheet, f"{args.finish_id.upper()}  PAINT / COMBINED M-R-CC / GRAZING / NATIVE MATERIAL DETAIL", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, .52, (255, 255, 255), 1, cv2.LINE_AA)
    out = ROOT / "_houdini_proof" / f"{args.finish_id}_native_material_audit_current.png"
    cv2.imwrite(str(out), sheet)
    # Literal isolated channels, saved separately so Houdini inspection never
    # has to infer individual material behavior from the packed RGB swatch.
    zero = np.zeros(spec.shape[:2], np.uint8)
    isolated = [
        cv2.cvtColor(np.dstack((spec[..., 0], zero, zero)), cv2.COLOR_RGB2BGR),
        cv2.cvtColor(np.dstack((zero, spec[..., 1], zero)), cv2.COLOR_RGB2BGR),
        cv2.cvtColor(np.dstack((zero, zero, spec[..., 2])), cv2.COLOR_RGB2BGR),
    ]
    isolated = [cv2.resize(panel, (512, 512), interpolation=cv2.INTER_AREA) for panel in isolated]
    channel_out = ROOT / "_houdini_proof" / f"{args.finish_id}_literal_mrc_current.png"
    cv2.imwrite(str(channel_out), np.concatenate(isolated, axis=1))
    # Two diagnostic lighting conditions for controlled material comparison.
    # They are explicitly not presented as iRacing track evidence.
    soft = grazing(spec, (.36, .28, .24))
    hard = grazing(spec, (.92, .84, .52))
    grazing_out = ROOT / "_houdini_proof" / f"{args.finish_id}_soft_hard_grazing_sim_current.png"
    cv2.imwrite(str(grazing_out), np.concatenate((soft, hard), axis=1))
    # Paint-coloured response is deliberately separate from the Turbo channel
    # diagnostic above; it is a sober material illustration, not a track shot.
    neutral = paint_colored_material_sim(paint_u8, spec, False)
    glancing = paint_colored_material_sim(paint_u8, spec, True)
    pbr_out = ROOT / "_houdini_proof" / f"{args.finish_id}_neutral_grazing_material_sim_not_track.png"
    cv2.imwrite(str(pbr_out), np.concatenate((neutral, glancing), axis=1))
    # Four channel-relationship conditions answer a more precise question than
    # one rainbow map: does the encoded relief change its hierarchy when the
    # material preference changes? These are diagnostics—not a track renderer.
    # Chrome / satin / clearcoat / balanced mixed.  These must not be scalar
    # multiples: the purpose is to expose genuine state-dependent hierarchy.
    profiles = ((.92, .55, .03, .15), (.08, .05, .94, .06),
                (.25, .45, .02, .95), (.62, .48, .00, .58))
    cells = [cv2.cvtColor(cv2.resize(response_profile(spec, w), (512, 512), interpolation=cv2.INTER_AREA), cv2.COLOR_GRAY2BGR) for w in profiles]
    suite_out = ROOT / "_houdini_proof" / f"{args.finish_id}_material_angle_suite_not_track.png"
    cv2.imwrite(str(suite_out), np.concatenate((np.concatenate(cells[:2], axis=1), np.concatenate(cells[2:], axis=1)), axis=0))
    print(f"native_2048_s={elapsed:.3f}" if args.size == 2048 else f"render_s={elapsed:.3f}")
    print(f"paint_mean={paint.mean():.4f} paint_std={paint.std():.4f}")
    print("mrc_std=%.2f/%.2f/%.2f" % tuple(spec[..., channel].std() for channel in range(3)))
    print(f"proof={out}")
    print(f"literal_channels={channel_out}")
    print(f"soft_hard_grazing_sim={grazing_out}")
    print(f"neutral_grazing_material_sim_not_track={pbr_out}")
    print(f"material_angle_suite_not_track={suite_out}")


if __name__ == "__main__":
    main()
