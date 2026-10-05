#!/usr/bin/env python3
"""Build an owner-review package of likely SPB renderer rebuild candidates.

This script renders visible picker catalog entries through the visual workbench,
scores them with broad visual-quality heuristics, and writes:

  review_candidates.html       visual cards with descriptions, reasons, notes
  rebuild_candidates_review.md checkbox review sheet for owner feedback
  triage_report.json           full machine-readable report

It intentionally flags suspects, not final truth. Owner confirmation decides
which candidates turn into rebuild work.
"""

from __future__ import annotations

import argparse
import html
import json
import math
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image


REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts import spb_visual_workbench as wb


@dataclass
class CatalogItem:
    id: str
    kind: str
    group_type: str
    groups: list[str]
    name: str = ""
    desc: str = ""
    swatch_image: str = ""
    app_visible: bool = False


@dataclass
class Candidate:
    id: str
    kind: str
    group_type: str
    groups: list[str]
    name: str
    desc: str
    swatch_image: str
    app_visible: bool
    review_type: str
    severity: int
    reasons: list[str]
    files: dict[str, str]
    metrics: dict[str, Any]


DETAIL_PROMISE_WORDS = {
    "circuit", "trace", "wire", "fiber", "weave", "woven", "carbon", "kevlar",
    "crystal", "shard", "flake", "sparkle", "glitter", "lace", "filigree",
    "mandala", "ornate", "scroll", "geometric", "fractal", "topographic",
    "crackle", "crack", "marble", "vein", "brushed", "grain", "honeycomb",
    "scale", "snake", "reptile", "data", "matrix", "glitch", "plasma",
    "lightning", "gear", "mechanical", "panel", "rivet", "scratch", "scuff",
}


def _visible_catalog() -> list[CatalogItem]:
    picker = wb._load_picker_groups()
    meta = picker.get("meta", {})
    catalog: dict[tuple[str, str], CatalogItem] = {}
    group_specs = [
        ("base", "base"),
        ("pattern", "pattern"),
        # Specials can legally point at monolithics or base-registry entries.
        ("special", "auto"),
        ("spec", "spec-pattern"),
    ]
    for group_type, kind in group_specs:
        for group_name, ids in (picker.get(group_type, {}) or {}).items():
            if not isinstance(ids, list):
                continue
            for item_id in ids:
                if not item_id:
                    continue
                key = (group_type, item_id)
                item_meta = meta.get(item_id, {}) or {}
                if key not in catalog:
                    catalog[key] = CatalogItem(
                        id=item_id,
                        kind=kind,
                        group_type=group_type,
                        groups=[],
                        name=str(item_meta.get("name", "")),
                        desc=str(item_meta.get("desc", "")),
                        swatch_image=str(item_meta.get("swatch_image", "")),
                        app_visible=bool(item_meta),
                    )
                if group_name not in catalog[key].groups:
                    catalog[key].groups.append(group_name)
    return list(catalog.values())


def _preview_vector(out_dir: Path, row: wb.WorkbenchRow) -> np.ndarray | None:
    if not row.files or "paint_preview" not in row.files:
        return None
    path = out_dir / row.files["paint_preview"]
    try:
        img = Image.open(path).convert("L").resize((32, 32), Image.Resampling.BILINEAR)
    except Exception:
        return None
    arr = np.asarray(img, dtype=np.float32).ravel()
    std = float(arr.std())
    if std < 1e-6:
        return None
    return (arr - float(arr.mean())) / std


def _duplicate_reasons(vectors: dict[str, np.ndarray], limit: int = 8) -> dict[str, list[str]]:
    ids = list(vectors)
    reasons: dict[str, list[str]] = {}
    for i, a_id in enumerate(ids):
        a = vectors[a_id]
        hits: list[tuple[str, float]] = []
        for b_id in ids[i + 1:]:
            b = vectors[b_id]
            corr = float(np.dot(a, b) / max(len(a), 1))
            if abs(corr) > 0.965:
                hits.append((b_id, corr))
        for b_id, corr in hits[:limit]:
            reasons.setdefault(a_id, []).append(f"near-duplicate visual match with `{b_id}` (corr {corr:.3f})")
            reasons.setdefault(b_id, []).append(f"near-duplicate visual match with `{a_id}` (corr {corr:.3f})")
    return reasons


def _reason_item(item: CatalogItem, row: wb.WorkbenchRow, duplicate_notes: list[str], size: int) -> tuple[int, list[str]]:
    reasons: list[str] = []
    severity = 0
    text = f"{item.name} {item.desc}".lower()
    foundation_reference = item.group_type == "base" and "Foundation" in item.groups
    intentionally_plain = (
        "foundation" in text
        or "reference base" in text
        or "plain " in text
        or "smooth " in text
        or "no baked-in" in text
        or "zero texture" in text
        or "zero sheen" in text
        or "dead flat" in text
        or "flat clearcoat" in text
        or "matte look" in text
        or "clean baseline" in text
        or "clean starting point" in text
    )
    explicitly_textured = any(word in text for word in DETAIL_PROMISE_WORDS)
    explicitly_textured = explicitly_textured and not (
        "no baked-in" in text
        or "without visible" in text
        or "without color" in text
        or "without metallic" in text
        or "add a " in text
    )
    if "Foundation" in item.groups and not explicitly_textured:
        intentionally_plain = True

    if row.kind == "image_pattern":
        return 0, []

    if row.status == "BROKEN" and row.error and "not found for kind 'auto'" in row.error:
        if item.app_visible:
            return 86, ["app-visible JS finish has no Python audit renderer yet; add renderer/tool support before judging visual rebuild need"]
        return 82, ["blank orphan/deleted picker reference; not app-visible, scrub from visual rebuild review"]

    if row.status == "BROKEN" and row.error and "no texture_fn and no image asset" in row.error:
        return 92, ["image/upload pattern is not wired to a source asset; preserve the uploaded artwork and fix asset mapping instead of rebuilding procedurally"]

    if row.status == "BROKEN":
        return 100, [f"renderer broke: {row.error}"]

    if foundation_reference:
        return 0, []

    render_ms = float(row.render_ms)
    slow_threshold = 1800.0 if size <= 256 else 3500.0
    if render_ms > slow_threshold:
        severity += 32
        reasons.append(f"slow render for triage size ({render_ms:.0f} ms at {size}px)")

    spec_only_overlay = row.kind == "spec_pattern"

    if not spec_only_overlay and not intentionally_plain and row.paint_luma_std < 0.006 and row.residual_energy < 0.004:
        severity += 28
        reasons.append("paint output is very flat / low-detail")
    if spec_only_overlay and row.paint_luma_std < 0.006 and row.residual_energy < 0.004:
        severity += 24
        reasons.append("spec-pattern preview is very flat / low-detail")
    if not intentionally_plain and row.fine_energy < 0.004 and row.residual_energy < 0.004:
        severity += 22
        reasons.append("little fine-scale detail survives the canvas")
    if row.block_energy > 0.18 and row.residual_energy < 0.026:
        severity += 24
        reasons.append("coarse/blocky field likely visible as square or lazy texture")
    if not spec_only_overlay and not intentionally_plain and row.color_population < 2:
        severity += 14
        reasons.append("low color population")
    if not intentionally_plain and row.kind in {"base", "monolithic", "spec_pattern"} and row.spec_m_range < 8.0:
        severity += 20
        reasons.append("metallic/spec channel is nearly flat")

    if explicitly_textured:
        if row.fine_energy < 0.009 or row.residual_energy < 0.006:
            severity += 18
            reasons.append("description/name promises visible material detail but metrics are weak")

    if not intentionally_plain:
        for note in duplicate_notes[:3]:
            severity += 18
            reasons.append(note)

    if row.flags:
        for flag in row.flags:
            if intentionally_plain and flag in {"low detail", "flat metallic channel"}:
                continue
            if flag not in reasons:
                severity += 6
                reasons.append(flag)

    return severity, reasons


def _render_review_html(out_dir: Path, candidates: list[Candidate], size: int) -> None:
    cards = []
    for idx, c in enumerate(candidates, 1):
        files = c.files
        reasons = "".join(f"<li>{html.escape(reason)}</li>" for reason in c.reasons)
        groups = ", ".join(c.groups)
        card = [f'<article class="card" id="{html.escape(c.id)}">']
        card.append(f"<h2>{idx}. {html.escape(c.id)} <span>{html.escape(c.kind)} / {html.escape(c.group_type)}</span></h2>")
        card.append(f'<p class="name">{html.escape(c.name or c.id)}</p>')
        card.append(f'<p class="severity"><strong>Review lane:</strong> {html.escape(c.review_type)}</p>')
        card.append(f'<p class="desc"><strong>Supposed to look like:</strong> {html.escape(c.desc or "(no picker description)")}</p>')
        card.append(f'<p class="groups"><strong>Picker group(s):</strong> {html.escape(groups)}</p>')
        if c.swatch_image:
            card.append(f'<p class="groups"><strong>Picker source image:</strong> {html.escape(c.swatch_image)}</p>')
        if files.get("source_asset"):
            card.append(f'<p class="groups"><strong>Rendered asset:</strong> {html.escape(files["source_asset"])}</p>')
        card.append(f'<p class="severity"><strong>Codex suspicion score:</strong> {c.severity}</p>')
        card.append(f"<ul>{reasons}</ul>")
        card.append('<label class="decision"><input type="checkbox"> Owner confirms this needs work</label>')
        card.append('<textarea placeholder="Owner notes: what feels wrong, what it should do instead"></textarea>')
        for key, label in (
            ("paint_preview", "Paint"),
            ("spec_preview", "Spec"),
            ("detail_crop", "Detail crop"),
            ("center_crop", "Center crop"),
            ("luma_preview", "Luma"),
        ):
            if key in files:
                href = files.get("paint_full" if key == "paint_preview" else "spec_full" if key == "spec_preview" else key, files[key])
                card.append(
                    f'<figure><a href="{html.escape(href)}"><img src="{html.escape(files[key])}" alt="{html.escape(label)}"></a>'
                    f"<figcaption>{html.escape(label)}</figcaption></figure>"
                )
        card.append("</article>")
        cards.append("\n".join(card))
    css = """
body { margin: 0; background: #101217; color: #edf1f5; font-family: system-ui, Segoe UI, sans-serif; }
header { position: sticky; top: 0; z-index: 2; padding: 14px 18px; background: #171b23; border-bottom: 1px solid #303846; }
h1 { font-size: 18px; margin: 0 0 4px; }
header p { margin: 0; color: #bfccd9; font-size: 12px; }
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(440px, 1fr)); gap: 14px; padding: 14px; }
.card { background: #1b2029; border: 1px solid #394250; border-radius: 6px; padding: 12px; }
h2 { font-size: 15px; margin: 0 0 6px; }
h2 span { color: #9facbb; font-size: 12px; font-weight: 500; margin-left: 8px; }
.name { font-weight: 700; margin: 0 0 6px; }
.desc, .groups, .severity { color: #d4deea; font-size: 12px; line-height: 1.45; margin: 0 0 8px; }
ul { margin: 0 0 10px 18px; padding: 0; color: #ffd89a; font-size: 12px; line-height: 1.45; }
.decision { display: block; margin: 8px 0; font-size: 13px; }
textarea { width: 100%; min-height: 64px; box-sizing: border-box; background: #101318; color: #edf1f5; border: 1px solid #3b4554; border-radius: 4px; padding: 8px; margin: 0 0 10px; }
figure { display: inline-block; width: 31%; margin: 0 1% 10px 0; vertical-align: top; }
img { width: 100%; aspect-ratio: 1 / 1; object-fit: cover; background: #080a0d; border: 1px solid #333c49; }
figcaption { color: #aeb9c7; font-size: 11px; margin-top: 3px; }
"""
    doc = (
        "<!doctype html><html><head><meta charset=\"utf-8\">"
        f"<title>SPB Rebuild Candidate Review</title><style>{css}</style></head><body>"
        f"<header><h1>SPB Candidate Review</h1><p>{len(candidates)} suspected work items from {size}px broad triage. Image/upload patterns are preserved and routed to asset wiring, not procedural rebuild. Checkboxes/notes are for visual review; save notes separately in chat or Linear.</p></header>"
        f"<main class=\"grid\">{''.join(cards)}</main></body></html>"
    )
    (out_dir / "review_candidates.html").write_text(doc, encoding="utf-8")


def _render_nonvisual_reports(
    out_dir: Path,
    title: str,
    filename_stem: str,
    candidates: list[Candidate],
    intro: str | None = None,
) -> None:
    rows = []
    md = [
        f"# {title}",
        "",
        intro or "These entries were removed from the main visual review page because they have no rendered preview.",
        "",
    ]
    for c in candidates:
        reason = "; ".join(c.reasons)
        preview = ""
        if c.files.get("paint_preview"):
            preview = f'<a href="{html.escape(c.files["paint_preview"])}">paint</a>'
        if c.files.get("spec_preview"):
            preview = (preview + " / " if preview else "") + f'<a href="{html.escape(c.files["spec_preview"])}">spec</a>'
        rows.append(
            "<tr>"
            f"<td>{html.escape(c.id)}</td>"
            f"<td>{html.escape(c.name or c.id)}</td>"
            f"<td>{html.escape(c.kind)} / {html.escape(c.group_type)}</td>"
            f"<td>{html.escape(', '.join(c.groups))}</td>"
            f"<td>{preview}</td>"
            f"<td>{html.escape(reason)}</td>"
            "</tr>"
        )
        md.extend([
            f"## {c.id} - {c.name or c.id}",
            "",
            f"- Kind: `{c.kind}` / `{c.group_type}`",
            f"- Groups: {', '.join(c.groups)}",
            f"- App-visible JS catalog entry: {'yes' if c.app_visible else 'no'}",
            f"- Paint preview: `{c.files.get('paint_preview', '')}`",
            f"- Spec preview: `{c.files.get('spec_preview', '')}`",
            f"- Reason: {reason}",
            f"- Supposed to look like: {c.desc or '(no picker description)'}",
            "",
        ])
    css = """
body { margin: 0; background: #101217; color: #edf1f5; font-family: system-ui, Segoe UI, sans-serif; }
main { padding: 16px; }
h1 { font-size: 20px; }
p { color: #cbd5e1; }
table { width: 100%; border-collapse: collapse; font-size: 12px; }
th, td { border: 1px solid #334155; padding: 7px; vertical-align: top; }
th { background: #1e293b; text-align: left; }
td { background: #111827; }
"""
    doc = (
        "<!doctype html><html><head><meta charset=\"utf-8\">"
        f"<title>{html.escape(title)}</title><style>{css}</style></head><body><main>"
        f"<h1>{html.escape(title)}</h1>"
        f"<p>{len(candidates)} entries.</p>"
        "<table><thead><tr><th>ID</th><th>Name</th><th>Kind</th><th>Groups</th><th>Preview</th><th>Reason</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table></main></body></html>"
    )
    (out_dir / f"{filename_stem}.html").write_text(doc, encoding="utf-8")
    (out_dir / f"{filename_stem}.md").write_text("\n".join(md), encoding="utf-8")


def _render_review_markdown(out_dir: Path, candidates: list[Candidate]) -> None:
    lines = [
        "# SPB Rebuild Candidate Review",
        "",
        "Use this as the owner decision sheet. Check the entries that truly need work and add why. Image/upload patterns should be preserved and routed to asset wiring, not procedural rebuild.",
        "",
    ]
    for c in candidates:
        lines.extend([
            f"## {c.id} - {c.name or c.id}",
            "",
            f"- [ ] Work confirmed by owner",
            f"- Kind: `{c.kind}` / `{c.group_type}`",
            f"- Review lane: {c.review_type}",
            f"- Groups: {', '.join(c.groups)}",
            f"- Supposed to look like: {c.desc or '(no picker description)'}",
            f"- Picker source image: {c.swatch_image or '(none)'}",
            f"- Rendered asset: `{c.files.get('source_asset', '')}`",
            f"- Codex suspicion score: {c.severity}",
            f"- Reasons: {'; '.join(c.reasons)}",
            f"- Paint preview: `{c.files.get('paint_preview', '')}`",
            f"- Spec preview: `{c.files.get('spec_preview', '')}`",
            "- Owner notes:",
            "",
        ])
    (out_dir / "rebuild_candidates_review.md").write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ids", help="Optional comma-separated IDs for a small/smoke package.")
    parser.add_argument("--size", type=int, default=192, help="Broad triage render size. Use 192/256 for full catalog.")
    parser.add_argument("--seed", type=int, default=7301)
    parser.add_argument("--out-dir")
    parser.add_argument("--limit", type=int, default=0, help="Limit catalog items for smoke runs.")
    parser.add_argument("--max-candidates", type=int, default=260)
    parser.add_argument("--min-score", type=int, default=18)
    args = parser.parse_args(argv)

    stamp = time.strftime("%Y%m%d-%H%M%S")
    out_dir = Path(args.out_dir) if args.out_dir else REPO / "audit" / "spb_rebuild_triage" / stamp
    out_dir.mkdir(parents=True, exist_ok=True)

    full_catalog = _visible_catalog()
    if args.ids:
        wanted = {x.strip() for x in args.ids.split(",") if x.strip()}
        catalog = [item for item in full_catalog if item.id in wanted]
    else:
        catalog = full_catalog
    if args.limit > 0:
        catalog = catalog[: args.limit]

    eng = wb._quiet_engine()
    rows: list[dict[str, Any]] = []
    vectors: dict[str, np.ndarray] = {}
    item_by_key: dict[str, CatalogItem] = {}

    for index, item in enumerate(catalog, 1):
        key = f"{item.group_type}:{item.id}"
        item_by_key[key] = item
        row = wb._process_item(
            eng,
            item.id,
            item.kind,
            args.size,
            args.seed,
            out_dir,
            {"name": item.name, "desc": item.desc, "swatch_image": item.swatch_image},
        )
        vector = _preview_vector(out_dir, row)
        if vector is not None:
            vectors[key] = vector
        rows.append({
            "key": key,
            "catalog": asdict(item),
            "workbench": asdict(row),
        })
        if index % 50 == 0:
            print(f"Rendered {index}/{len(catalog)}...")

    dupes = _duplicate_reasons(vectors)
    candidates: list[Candidate] = []
    spec_driven_references: list[Candidate] = []
    for row_payload in rows:
        key = row_payload["key"]
        item = item_by_key[key]
        wb_row = wb.WorkbenchRow(**row_payload["workbench"])
        if item.group_type == "base" and "Foundation" in item.groups and wb_row.status != "BROKEN":
            spec_driven_references.append(Candidate(
                id=item.id,
                kind=wb_row.kind,
                group_type=item.group_type,
                groups=item.groups,
                name=item.name,
                desc=item.desc,
                swatch_image=item.swatch_image,
                app_visible=item.app_visible,
                review_type="spec-driven foundation/reference",
                severity=0,
                reasons=[
                    "Foundation/base-category material: paint preview is intentionally quiet; do not flag as a paint-output rebuild without app/spec behavior evidence"
                ],
                files=wb_row.files or {},
                metrics={
                    "render_ms": wb_row.render_ms,
                    "paint_luma_std": wb_row.paint_luma_std,
                    "paint_luma_span": wb_row.paint_luma_span,
                    "fine_energy": wb_row.fine_energy,
                    "residual_energy": wb_row.residual_energy,
                    "block_energy": wb_row.block_energy,
                    "color_population": wb_row.color_population,
                    "spec_m_range": wb_row.spec_m_range,
                },
            ))
            continue
        severity, reasons = _reason_item(item, wb_row, dupes.get(key, []), args.size)
        if severity >= args.min_score:
            if reasons and "source asset" in reasons[0]:
                review_type = "image asset wiring"
            elif reasons and "app-visible JS finish has no Python audit renderer" in reasons[0]:
                review_type = "audit renderer gap"
            elif reasons and "blank orphan/deleted picker reference" in reasons[0]:
                review_type = "scrubbed orphan/deleted reference"
            else:
                review_type = "renderer rebuild review"
            candidates.append(Candidate(
                id=item.id,
                kind=wb_row.kind,
                group_type=item.group_type,
                groups=item.groups,
                name=item.name,
                desc=item.desc,
                swatch_image=item.swatch_image,
                app_visible=item.app_visible,
                review_type=review_type,
                severity=severity,
                reasons=reasons,
                files=wb_row.files or {},
                metrics={
                    "render_ms": wb_row.render_ms,
                    "paint_luma_std": wb_row.paint_luma_std,
                    "paint_luma_span": wb_row.paint_luma_span,
                    "fine_energy": wb_row.fine_energy,
                    "residual_energy": wb_row.residual_energy,
                    "block_energy": wb_row.block_energy,
                    "color_population": wb_row.color_population,
                    "spec_m_range": wb_row.spec_m_range,
                },
            ))
    candidates.sort(key=lambda c: (-c.severity, c.group_type, c.id))
    visual_candidates = [c for c in candidates if c.files.get("paint_preview")]
    unrendered_live = [c for c in candidates if not c.files.get("paint_preview") and c.app_visible]
    scrubbed_orphans = [c for c in candidates if not c.files.get("paint_preview") and not c.app_visible]
    if args.max_candidates > 0:
        visual_candidates = visual_candidates[: args.max_candidates]

    report = {
        "size": args.size,
        "seed": args.seed,
        "catalog_count": len(catalog),
        "candidate_count": len(visual_candidates),
        "unrendered_live_count": len(unrendered_live),
        "scrubbed_blank_orphan_count": len(scrubbed_orphans),
        "spec_driven_reference_count": len(spec_driven_references),
        "generated_at": stamp,
        "candidates": [asdict(c) for c in visual_candidates],
        "unrendered_live_candidates": [asdict(c) for c in unrendered_live],
        "scrubbed_blank_orphans": [asdict(c) for c in scrubbed_orphans],
        "spec_driven_references": [asdict(c) for c in spec_driven_references],
        "all_scored_candidates": [asdict(c) for c in candidates],
        "rows": rows,
    }
    (out_dir / "triage_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    _render_review_html(out_dir, visual_candidates, args.size)
    _render_review_markdown(out_dir, visual_candidates)
    _render_nonvisual_reports(
        out_dir,
        "Live But Unrendered Audit Gaps",
        "unrendered_live_candidates",
        unrendered_live,
    )
    _render_nonvisual_reports(
        out_dir,
        "Scrubbed Blank Orphan/Deleted References",
        "scrubbed_blank_orphans",
        scrubbed_orphans,
    )
    _render_nonvisual_reports(
        out_dir,
        "Spec-Driven Foundation References",
        "spec_driven_foundation_references",
        spec_driven_references,
        "These Foundation/base-category entries were removed from rebuild scoring because their paint preview is intentionally quiet. Judge them by in-app material/spec behavior, not by paint-output metrics alone.",
    )

    print(f"Catalog rendered: {len(catalog)}")
    print(f"Visual candidates: {len(visual_candidates)}")
    print(f"Live unrendered: {len(unrendered_live)}")
    print(f"Scrubbed blank orphans: {len(scrubbed_orphans)}")
    print(f"Spec-driven references: {len(spec_driven_references)}")
    print(f"Review HTML: {out_dir / 'review_candidates.html'}")
    print(f"Review MD: {out_dir / 'rebuild_candidates_review.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
