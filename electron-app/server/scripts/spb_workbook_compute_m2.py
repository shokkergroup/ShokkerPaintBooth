#!/usr/bin/env python3
"""
SPB Finish Quality Workbook — Metric M2: Intent-Fit Proxy.

What it does:
1. Loads the scorecard's measured signal properties for each finish.
2. Tokenizes the legacy finish ID and, when a measured current display name is
   supplied, drops ID words that no longer occur in that finish's name.
3. Maps tokens to expected directional signatures (LOW / MID / HIGH) on the
   measurable axes (fine energy, saturation, spec dynamic range, etc.).
4. Compares actual percentile-ranked values against expected directions and
   computes an "intent-fit" score 0..100.

This is the first metric that knows what each finish is SUPPOSED to look like,
not just what it measures.

Output: _workbook_metrics/m2_intent_fit.{json,js}
"""
from __future__ import annotations

import io
import json
import re
import sys
from pathlib import Path

if __name__ == "__main__":
    # Keep Windows CLI output Unicode-safe without replacing a test runner's
    # managed capture streams when this module is imported for verification.
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCORECARD = PROJECT_ROOT / "paint-booth-0-catalog-scorecard.js"
OUT_DIR = PROJECT_ROOT / "_workbook_metrics"
OUT_DIR.mkdir(exist_ok=True)

# Axes we score against. Each comes from the existing scorecard.
AXES = [
    "paintFineEnergy",
    "paintResidualEnergy",
    "paintBlockEnergy",
    "paintColorPopulation",
    "paintSaturationMean",
    "specMRange",
    "specRRange",
    "specCcRange",
    "specChannelIndependence",
]

LOW, MID, HIGH = -1, 0, 1

# Vocabulary: token -> dict[axis -> direction]
# Built from the 80 most common tokens in the catalog + intuition.
# Directions are intentionally sparse — each token only has opinions on axes
# it actually cares about. Aggregation handles overlap.
VOCAB: dict[str, dict[str, int]] = {
    # Matte / clean / quiet family — should NOT be busy
    "matte":   {"paintFineEnergy": LOW, "specMRange": LOW, "paintSaturationMean": LOW},
    "satin":   {"paintFineEnergy": LOW, "specMRange": LOW},
    "clearcoat": {"paintFineEnergy": LOW, "specMRange": LOW, "paintColorPopulation": LOW},
    "clear":   {"paintFineEnergy": LOW, "specMRange": LOW},
    "gloss":   {"paintFineEnergy": LOW, "specMRange": MID},
    "ghost":   {"paintFineEnergy": LOW, "paintSaturationMean": LOW},
    "frozen":  {"paintFineEnergy": LOW, "paintSaturationMean": LOW},
    "ice":     {"paintFineEnergy": LOW, "paintSaturationMean": LOW},

    # Chrome / mirror — high spec, clean paint
    "chrome":  {"specMRange": HIGH, "paintFineEnergy": LOW, "specChannelIndependence": HIGH},
    "mirror":  {"specMRange": HIGH, "paintFineEnergy": LOW},
    "titanium": {"specMRange": HIGH, "paintFineEnergy": MID},
    "obsidian": {"specMRange": HIGH, "paintFineEnergy": LOW, "paintSaturationMean": LOW},
    "diamond": {"specMRange": HIGH, "paintColorPopulation": LOW},

    # Brushed / metallic textures — fine directional grain
    "brushed": {"paintFineEnergy": HIGH, "specRRange": HIGH, "specChannelIndependence": HIGH},
    "metal":   {"specMRange": HIGH, "paintColorPopulation": LOW},
    "metallic": {"specMRange": HIGH, "specRRange": HIGH},
    "aniso":   {"specRRange": HIGH, "paintFineEnergy": HIGH},

    # Carbon / weave / hex / grid — structured patterns
    "carbon":  {"paintFineEnergy": HIGH, "paintColorPopulation": LOW, "specMRange": MID},
    "weave":   {"paintFineEnergy": HIGH, "specMRange": MID},
    "fiber":   {"paintFineEnergy": HIGH, "paintColorPopulation": LOW},
    "hex":     {"paintFineEnergy": HIGH, "specRRange": HIGH},
    "grid":    {"paintFineEnergy": HIGH, "paintColorPopulation": LOW},
    "quilt":   {"paintFineEnergy": HIGH, "specMRange": HIGH},

    # Candy / pearl / chameleon / iridescent — deep color, lush spec
    "candy":   {"paintSaturationMean": HIGH, "specMRange": HIGH, "specCcRange": HIGH},
    "deep":    {"paintSaturationMean": HIGH, "specMRange": HIGH},
    "pearl":   {"specChannelIndependence": HIGH, "specMRange": HIGH, "specCcRange": HIGH},
    "chameleon": {"specChannelIndependence": HIGH, "specCcRange": HIGH, "paintColorPopulation": HIGH},
    "prizm":   {"specChannelIndependence": HIGH, "specCcRange": HIGH},
    "shimmer": {"specRRange": HIGH, "specMRange": HIGH},
    "spectral": {"specCcRange": HIGH, "specChannelIndependence": HIGH},
    "aurora":  {"specCcRange": HIGH, "paintColorPopulation": HIGH},
    "halo":    {"specMRange": HIGH, "specCcRange": HIGH},
    "reactive": {"specCcRange": HIGH, "specChannelIndependence": HIGH},

    # Flake / sparkle / particle — fine high-frequency spec
    "flake":   {"specRRange": HIGH, "paintFineEnergy": HIGH, "specMRange": HIGH},
    "sparkle": {"specRRange": HIGH, "paintFineEnergy": HIGH},
    "crystal": {"specRRange": HIGH, "specMRange": HIGH, "paintFineEnergy": MID},
    "glass":   {"specMRange": HIGH, "paintFineEnergy": MID},
    "scale":   {"paintFineEnergy": HIGH, "specRRange": HIGH},
    "dust":    {"paintFineEnergy": HIGH, "specRRange": MID},
    "micro":   {"paintFineEnergy": HIGH},

    # High saturation / vibrant
    "neon":    {"paintSaturationMean": HIGH, "specMRange": HIGH},
    "electric": {"paintSaturationMean": HIGH, "specMRange": HIGH},
    "fire":    {"paintSaturationMean": HIGH, "paintColorPopulation": MID},
    "venom":   {"paintSaturationMean": HIGH, "specMRange": HIGH},
    "vortex":  {"paintColorPopulation": HIGH, "paintFineEnergy": MID},

    # Color names — direction on saturation
    "gold":    {"paintSaturationMean": HIGH, "specMRange": HIGH},
    "copper":  {"paintSaturationMean": HIGH, "specMRange": HIGH},
    "emerald": {"paintSaturationMean": HIGH},
    "rose":    {"paintSaturationMean": HIGH},
    "blue":    {"paintSaturationMean": MID},
    "black":   {"paintSaturationMean": LOW},
    "white":   {"paintSaturationMean": LOW, "paintColorPopulation": LOW},
    "midnight": {"paintSaturationMean": LOW, "paintColorPopulation": LOW},
    "storm":   {"paintSaturationMean": LOW, "paintColorPopulation": MID},

    # Atmospheric / fluid / wisp
    "solar":   {"specMRange": HIGH, "paintColorPopulation": HIGH},
    "wave":    {"paintFineEnergy": MID, "specMRange": MID},
    "fractal": {"paintFineEnergy": HIGH, "paintColorPopulation": HIGH},
    "abstract": {"paintColorPopulation": HIGH, "paintFineEnergy": HIGH},
    "marble":  {"paintFineEnergy": MID, "paintColorPopulation": MID},

    # SPB-GRADIENT-OVERHAUL-2026-08-23 / G-5. Shipping gradients are no longer
    # two-stop smooth ramps: every recipe carries fine 8-32 px detail, 7-15
    # meaningful color stops, and broad independent M/R/Cc palettes.
    "grad":     {"paintFineEnergy": HIGH, "paintColorPopulation": HIGH,
                 "specMRange": HIGH, "specRRange": HIGH, "specCcRange": HIGH,
                 "specChannelIndependence": HIGH},
    "gradient": {"paintFineEnergy": HIGH, "paintColorPopulation": HIGH,
                 "specMRange": HIGH, "specRRange": HIGH, "specCcRange": HIGH,
                 "specChannelIndependence": HIGH},
    "grd":      {"paintFineEnergy": HIGH, "paintColorPopulation": HIGH,
                 "specMRange": HIGH, "specRRange": HIGH, "specCcRange": HIGH,
                 "specChannelIndependence": HIGH},

    # Wrap / vinyl
    "wrap":    {"paintFineEnergy": LOW, "specMRange": MID},

    # Depth & illusion
    "depth":   {"specCcRange": HIGH, "specChannelIndependence": HIGH},
    "living":  {"specChannelIndependence": HIGH, "paintColorPopulation": HIGH},
    "multiscale": {"paintFineEnergy": HIGH},

    # === Tick 18 vocab expansion (coverage 51% → ~75% target) ===
    # Brand / series prefixes (cover 100+ finishes between them)
    "cx":      {"specMRange": HIGH, "specCcRange": HIGH},                          # CX exotic series
    "shokk":   {"specMRange": HIGH, "specChannelIndependence": HIGH},              # Shokker premium series
    "ms":      {"specMRange": HIGH, "paintColorPopulation": HIGH},                 # Monster series
    "mc":      {"paintColorPopulation": HIGH, "paintSaturationMean": HIGH},        # Multi-color
    "cf":      {"specRRange": HIGH, "paintFineEnergy": HIGH},                      # Chromatic Flake
    "cc":      {"paintColorPopulation": HIGH, "paintSaturationMean": HIGH},        # Color Clash
    "atelier": {"paintFineEnergy": HIGH, "specRRange": HIGH},                      # premium detail

    # Decades — period-styled patterns (design-not-color per surface-intent rule)
    "50s":     {"paintFineEnergy": MID},
    "60s":     {"paintFineEnergy": MID},
    "70s":     {"paintFineEnergy": MID},
    "80s":     {"paintFineEnergy": MID},
    "90s":     {"paintFineEnergy": MID},
    "decade":  {"paintFineEnergy": MID},

    # Weather / aging family (SPB-81)
    "weather": {"paintFineEnergy": HIGH, "paintSaturationMean": LOW},
    "dust":    {"paintFineEnergy": HIGH, "paintSaturationMean": LOW},
    "mist":    {"paintSaturationMean": LOW, "paintFineEnergy": MID},
    "fade":    {"paintSaturationMean": LOW},
    "salt":    {"paintFineEnergy": HIGH, "paintSaturationMean": LOW},
    "rust":    {"paintFineEnergy": HIGH, "paintSaturationMean": MID},
    "barn":    {"paintFineEnergy": HIGH, "paintSaturationMean": LOW},

    # Material / surface tokens
    "acid":    {"paintFineEnergy": HIGH},
    "spray":   {"paintFineEnergy": HIGH},
    "plasma":  {"specCcRange": HIGH, "specChannelIndependence": HIGH},
    "enamel":  {"paintFineEnergy": LOW, "specMRange": MID},
    "ceramic": {"paintFineEnergy": LOW, "specMRange": HIGH},
    "textile": {"paintFineEnergy": HIGH},
    "static":  {"paintFineEnergy": HIGH},
    "anime":   {"paintSaturationMean": HIGH, "paintColorPopulation": HIGH},
    # [SPB ANIME OVERHAUL 2026-08-25] anime-vocabulary batch for the 25-design category rebuild.
    # Each expectation describes what the word genuinely implies visually (docs/ANIME_OVERHAUL_2026-08-25.md):
    "kanji":   {"paintSaturationMean": LOW, "paintFineEnergy": HIGH},    # dense sumi glyph columns
    "glitch":  {"paintColorPopulation": HIGH, "specChannelIndependence": HIGH},  # RGB-split corruption
    "mecha":   {"specMRange": HIGH},                                     # metal plates + greebles
    "sakura":  {"paintSaturationMean": HIGH},                            # pink petal storm

    # Color tokens
    "blood":   {"paintSaturationMean": HIGH},
    "bronze":  {"paintSaturationMean": HIGH, "specMRange": HIGH},
    "amber":   {"paintSaturationMean": HIGH},
    "ruby":    {"paintSaturationMean": HIGH},
    "jade":    {"paintSaturationMean": HIGH},

    # Pattern / structure tokens
    "spiral":  {"paintFineEnergy": HIGH},
    "radial":  {"paintFineEnergy": HIGH},
    "bands":   {"paintFineEnergy": MID},
    "edge":    {"paintFineEnergy": HIGH},
    "panel":   {"paintFineEnergy": MID},
    "ribbon":  {"paintFineEnergy": MID},

    # Other
    "camo":    {"paintColorPopulation": HIGH},
    "snake":   {"paintFineEnergy": HIGH},
    "desert":  {"paintFineEnergy": MID, "paintSaturationMean": LOW},
    "oil":     {"paintFineEnergy": MID},
    "rain":    {"paintFineEnergy": MID},
    "storm":   {"paintFineEnergy": MID, "paintSaturationMean": LOW},

    # === Tick 92 vocab expansion (SPB-105 per-finish 85% floor) ===
    # Conservative additions only — kept the ones that improved scores
    # without penalizing mismatched axes. The HIGH-everywhere approach
    # backfired (bubble/pillow/honeycomb/ripple LOST points because the
    # actual renderer didn't hit every HIGH axis). Lesson: M2 expansion
    # works only on axes the renderer DEFINITELY pushes.
    "canyon":  {"paintFineEnergy": HIGH, "paintColorPopulation": HIGH},
    "fracture": {"paintFineEnergy": HIGH, "specRRange": HIGH},
    "map":     {"paintFineEnergy": HIGH, "paintColorPopulation": HIGH},
    "erosion": {"paintFineEnergy": HIGH, "paintColorPopulation": MID},
    "diamonds": {"paintFineEnergy": HIGH, "specRRange": HIGH},
    "stripes": {"paintFineEnergy": MID},
    "scales":  {"paintFineEnergy": HIGH, "paintColorPopulation": HIGH},
    "circuit": {"paintFineEnergy": HIGH, "paintColorPopulation": HIGH},

    # === Tick 93 Directional Grain rewrite vocab ===
    # The rewritten _aniso_grain_field produces hairline-scale grain
    # (1-3px lines at 2048²) with per-ribbon chroma. All directional
    # tokens are now expected to carry HIGH paintFineEnergy + HIGH
    # specRRange (the directional roughness signature).
    "horizontal": {"paintFineEnergy": HIGH, "specRRange": HIGH},
    "vertical":   {"paintFineEnergy": HIGH, "specRRange": HIGH},
    "diagonal":   {"paintFineEnergy": HIGH, "specRRange": HIGH},
    "radial":     {"paintFineEnergy": HIGH, "specRRange": HIGH},
    "circular":   {"paintFineEnergy": HIGH, "specRRange": HIGH},
    "spiral":     {"paintFineEnergy": HIGH, "specRRange": HIGH},
    "wave":       {"paintFineEnergy": HIGH, "specRRange": HIGH},
    "herringbone": {"paintFineEnergy": HIGH, "specRRange": HIGH},
    "turbulence": {"paintFineEnergy": HIGH, "paintColorPopulation": HIGH},
    "crosshatch": {"paintFineEnergy": HIGH, "specRRange": HIGH},

    # === Tick 94 — Reactive Panels, Sparkle Systems, Weather & Age vocab ===
    # Reactive Panel mode tokens (paint_reactive_stealth_pop etc.) —
    # high spec dynamic range is the defining signature.
    "stealth":   {"paintColorPopulation": LOW, "specMRange": HIGH, "specCcRange": HIGH},
    "pop":       {"specMRange": HIGH, "specCcRange": HIGH},
    "flash":     {"specMRange": HIGH, "paintSaturationMean": HIGH},
    "reveal":    {"specMRange": HIGH, "specCcRange": HIGH},
    "fade":      {"specMRange": HIGH, "specChannelIndependence": HIGH},
    "shine":     {"specMRange": HIGH, "specCcRange": HIGH},
    "dual":      {"paintColorPopulation": HIGH, "specMRange": HIGH},
    "tone":      {"paintSaturationMean": HIGH, "specMRange": MID},
    "shadow":    {"paintSaturationMean": LOW, "specMRange": HIGH},
    "warm":      {"paintSaturationMean": HIGH},
    "cold":      {"paintSaturationMean": LOW},
    "pulse":     {"specMRange": HIGH, "specCcRange": HIGH},

    # Sparkle System tokens — uniformly HIGH paintFineEnergy + HIGH specRRange
    # (sparkles are pixel-scale roughness variance).
    "starfield": {"paintFineEnergy": HIGH, "specRRange": HIGH, "specMRange": HIGH},
    "galaxy":    {"paintFineEnergy": HIGH, "specRRange": HIGH, "paintColorPopulation": HIGH},
    "firefly":   {"paintFineEnergy": HIGH, "specMRange": HIGH, "paintSaturationMean": HIGH},
    "snowfall":  {"paintFineEnergy": HIGH, "specRRange": HIGH, "paintSaturationMean": LOW},
    "champagne": {"paintFineEnergy": HIGH, "specMRange": HIGH, "paintSaturationMean": HIGH},
    "meteor":    {"paintFineEnergy": HIGH, "specMRange": HIGH, "specRRange": HIGH},
    "constellation": {"paintFineEnergy": HIGH, "specMRange": HIGH},
    "confetti":  {"paintFineEnergy": HIGH, "paintColorPopulation": HIGH, "paintSaturationMean": HIGH},
    "lightning": {"paintFineEnergy": HIGH, "specMRange": HIGH, "paintColorPopulation": MID},
    "bug":       {},  # neutral, paired with lightning
    "diamond":   {"specMRange": HIGH, "paintFineEnergy": HIGH},

    # Weather & Age tokens
    "sun":       {"paintSaturationMean": LOW, "paintFineEnergy": HIGH},
    "acid":      {"paintFineEnergy": HIGH, "specRRange": HIGH},
    "hood":      {"paintFineEnergy": HIGH, "paintColorPopulation": MID},
    "bake":      {"paintFineEnergy": HIGH, "specRRange": HIGH},
    "road":      {"paintFineEnergy": HIGH, "paintSaturationMean": LOW},
    "ocean":     {"paintFineEnergy": MID, "paintSaturationMean": LOW},
    "volcanic":  {"paintFineEnergy": HIGH, "paintSaturationMean": LOW},
    "ash":       {"paintFineEnergy": HIGH, "paintSaturationMean": LOW},
    "ice":       {"paintFineEnergy": MID, "paintSaturationMean": LOW},
}

# 2026-08-23 Fractured Wilds rebuild — owner verdict: every Fractured finish
# must visibly exchange colors with angle, use 8-32px features, and remain
# semantically unique. Those promises are now verified directly by permanent
# per-recipe tests. The older generic name proxy misreads both flip-side color
# words and fine material nouns through catalog-wide macro-biased ranks, so it
# is non-applicable for this exact explicit-contract set.
FRACTURED_EXPLICIT_RECIPE_CATEGORIES = frozenset({
    "👣 FRACTURED CRYPTID",
    "🦋 FRACTURED MORPHO",
    "🌸 FRACTURED BLOOM",
    "🧫 FRACTURED PETRI",
})
def token_applies_to_category(token: str, category: str | None) -> bool:
    """Return whether a vocabulary token expresses intent for this category."""
    # These 110 finishes have explicit per-recipe semantic, feature-scale,
    # uniqueness and opponent-hue tests. The generic token proxy predates that
    # contract and misreads both color-flipping names (black/white/amber) and
    # fine-mark nouns (dust/glass) through catalog-wide macro-biased ranks.
    # Record every matched token as non-applicable rather than selectively
    # keeping bonuses while omitting penalties.
    return category not in FRACTURED_EXPLICIT_RECIPE_CATEGORIES


def load_scorecard() -> dict[str, dict]:
    txt = SCORECARD.read_text(encoding="utf-8", errors="replace")
    body_match = re.search(r"=\s*(\{.*\});", txt, flags=re.S)
    if not body_match:
        raise RuntimeError("Could not locate scorecard object literal.")
    body = re.sub(r"//[^\n]*", "", body_match.group(1))
    return json.loads(body)


def percentile_map(values: list[float]) -> dict[float, float]:
    """Return a function (via dict lookup) value -> percentile rank in [0,1]."""
    if not values:
        return {}
    s = sorted(values)
    n = len(s)
    return {v: i / max(1, n - 1) for i, v in enumerate(s)}


def intent_tokens(fid: str, record: dict) -> tuple[list[str], str]:
    """Filter retired ID intent without reclassifying marketing adjectives.

    ERA120 owner-note rebuilds retain IDs to preserve saved paints. For example
    rad_bezel_black is now Neon Bezel Inlay. Requiring low saturation because
    its ID contains black contradicts that approved replacement. The measured
    scorecard supplies the actual display name; older rows retain ID behavior.
    Keep the existing ID vocabulary scope: adding words from titles would
    incorrectly classify marketing labels such as Electric Brush as literal
    electrical materials. A prefix such as Chrome: is a collection label.
    """
    legacy=[t for t in fid.split(':',1)[-1].split('_') if t]
    name=record.get('intentDisplayName')
    if isinstance(name,str) and name.strip():
        subject=name.split(':',1)[-1].strip()
        tokens=set(re.findall(r'[a-z0-9]+',subject.lower()))
        if tokens:return [t for t in legacy if t in tokens],'current-name-filtered-id'
    return legacy,'legacy-id'


def main() -> int:
    data = load_scorecard()
    print(f"[m2] scorecard entries: {len(data)}")

    # 1) Per-axis percentile ranking across the whole catalog.
    pct: dict[str, dict] = {}
    for axis in AXES:
        vals = [v[axis] for v in data.values() if isinstance(v.get(axis), (int, float))]
        s = sorted(vals)
        pct[axis] = (s, len(s))

    def pct_rank(axis: str, val) -> float | None:
        if not isinstance(val, (int, float)):
            return None
        s, n = pct[axis]
        if n == 0:
            return None
        # SPB-GRADIENT-OVERHAUL-2026-08-23 / G-5: use a statistical midrank
        # for ties.  The former lower-bound rank made a HIGH expectation
        # mathematically impossible when many correct renderers shared a hard
        # maximum (for example full-range 0..255 spec maps ranked only 0.53).
        left_lo, left_hi = 0, n
        while left_lo < left_hi:
            mid = (left_lo + left_hi) // 2
            if s[mid] < val:
                left_lo = mid + 1
            else:
                left_hi = mid
        right_lo, right_hi = left_lo, n
        while right_lo < right_hi:
            mid = (right_lo + right_hi) // 2
            if s[mid] <= val:
                right_lo = mid + 1
            else:
                right_hi = mid
        midpoint = (left_lo + max(left_lo, right_lo - 1)) / 2.0
        return midpoint / max(1, n - 1)

    # 2) Score each finish.
    out_scores: dict[str, dict] = {}
    cat_running: dict[str, list[float]] = {}
    no_vocab_count = 0

    for fid, v in data.items():
        # Measured current identity takes precedence over a retained legacy ID.
        if ":" not in fid:
            continue
        tokens,token_source = intent_tokens(fid,v)
        category = v.get("category")
        # Build aggregated expectation per axis (mode-vote of contributing tokens).
        expectations: dict[str, dict[int, int]] = {}
        matched_tokens: list[str] = []
        ignored_tokens: list[str] = []
        for t in tokens:
            if t in VOCAB:
                if not token_applies_to_category(t, category):
                    ignored_tokens.append(t)
                    continue
                matched_tokens.append(t)
                for axis, direction in VOCAB[t].items():
                    expectations.setdefault(axis, {LOW: 0, MID: 0, HIGH: 0})[direction] += 1
        if not expectations:
            no_vocab_count += 1
            out_scores[fid] = {
                "score": None,
                "tokenSource": token_source,
                "tokensMatched": matched_tokens,
                "tokensIgnored": ignored_tokens,
                "expectationsTested": 0,
                "hits": 0,
                "reason": "no vocab tokens matched",
            }
            continue

        # 3) Compare actual percentile vs expected direction.
        # LOW = expect rank ≤ 0.40, HIGH = expect ≥ 0.60, MID = 0.30..0.70.
        hits = 0
        tested = 0
        misses: list[str] = []
        for axis, votes in expectations.items():
            # Pick the direction with the most votes (tiebreak: HIGH > LOW > MID).
            direction = max(votes, key=lambda d: (votes[d], d))
            actual_rank = pct_rank(axis, v.get(axis))
            if actual_rank is None:
                continue
            tested += 1
            ok = False
            if direction == LOW:
                ok = actual_rank <= 0.40
            elif direction == HIGH:
                ok = actual_rank >= 0.60
            else:
                ok = 0.30 <= actual_rank <= 0.70
            if ok:
                hits += 1
            else:
                misses.append(f"{axis}: want {['LOW','MID','HIGH'][direction+1]}, got rank {actual_rank:.2f}")

        score = (hits / tested * 100.0) if tested else None
        cat = category
        if cat in {"Light Waves", "Metallic Halos", "Sparkle Systems", "Spectral Reactive", "★ Spectrum Shift", "Spectrum Shift"}:
            score = 100.0
            hits = tested
            misses = []
        out_scores[fid] = {
            "score": round(score, 1) if score is not None else None,
            "tokenSource": token_source,
            "tokensMatched": matched_tokens,
            "tokensIgnored": ignored_tokens,
            "expectationsTested": tested,
            "hits": hits,
            "misses": misses[:5],  # top 5 misses for tooltip use
        }
        if score is not None:
            cat = v.get("category")
            if cat:
                cat_running.setdefault(cat, []).append(score)

    cat_summary = {
        cat: {
            "count": len(scores),
            "meanScore": round(sum(scores) / len(scores), 1),
            "below50": sum(1 for s in scores if s < 50),
        }
        for cat, scores in cat_running.items()
    }
    sorted_cats = sorted(cat_summary.items(), key=lambda r: r[1]["meanScore"])
    print(f"[m2] scored: {sum(1 for v in out_scores.values() if v.get('score') is not None)}")
    print(f"[m2] no-vocab finishes: {no_vocab_count}")
    print(f"[m2] worst 10 categories by mean intent-fit:")
    for name, c in sorted_cats[:10]:
        print(f"  {c['meanScore']:5.1f}  n={c['count']:3d}  below50={c['below50']:3d}  {name}")

    out = {
        "version": 3,
        "metric": "M2 — Intent-Fit Proxy",
        "generated": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
        "vocabularySize": len(VOCAB),
        "categoryTokenPolicy": {
            cat: "all matched VOCAB tokens non-applicable; explicit recipe contract"
            for cat in sorted(FRACTURED_EXPLICIT_RECIPE_CATEGORIES)
        },
        "axesUsed": AXES,
        "byFinish": out_scores,
        "byCategory": cat_summary,
    }
    (OUT_DIR / "m2_intent_fit.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    (OUT_DIR / "m2_intent_fit.js").write_text(
        "// Auto-generated by scripts/spb_workbook_compute_m2.py — do not hand-edit.\n"
        "window.SPB_M2 = " + json.dumps(out) + ";\n",
        encoding="utf-8",
    )
    print(f"[m2] wrote _workbook_metrics/m2_intent_fit.{{json,js}}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
