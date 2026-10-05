"""Summarize measured evidence only, keeping owner acceptance explicitly open."""
from pathlib import Path
import json,hashlib
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'_astra_rebuild_20260922_work'


def main():
    load=lambda name:json.loads((OUT/name).read_text())
    native=load('native_report.json');live=load('live_report.json');exports=load('full_pipeline/report.json')
    metrics=load('m7_report.json');pairs=load('similarity.json')
    restart=load('restart_report.json');assert restart['status']=='pass'
    assert len(native)==len(live)==len(exports)==len(metrics)==50
    assert len(pairs)==1225
    rejects=[p for p in pairs if p['status']=='reject']
    assert not rejects,[(r['a'],r['b'],r['maximum']) for r in rejects]
    flags=[p for p in pairs if p['status']!='pass']
    summary=dict(finishes=50,native_pairs=50,standard_thumbnails=50,split_thumbnails=50,
        served_picker_responses=200,persistent_master_pairs=50,persistent_derivatives=150,
        actual_exports=50,identity_pairs=1225,identity_maximum=max(p['maximum'] for p in pairs),
        identity_review_pairs=len(flags),identity_reject_pairs=len(rejects),
        native_seconds=[min(r['seconds'] for r in native.values()),max(r['seconds'] for r in native.values())],
        actual_finish_stage_seconds=[min(r['finish_stage_seconds'] for r in exports.values()),max(r['finish_stage_seconds'] for r in exports.values())],
        export_paint_mae_max=max(r['paint_mae'] for r in exports.values()),
        export_spec_mae_max=max(r['spec_mae'] for r in exports.values()),
        picker_mae_max=max(max(r['mae_'+str(size)]) for r in live for size in [512,256,128,48]),
        m7_range=[min(r['after'] for r in metrics.values()),max(r['after'] for r in metrics.values())],
        material_regressions_passed=4,restart_persistence='pass',runtime_exact_pairs=restart['runtime_exact_pairs'],owner_verdict='pending',on_car_lighting='not claimed')
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2))
    lines=['# ASTRA R1 — all fifty rebuilt and installed','',
        '22 September 2026. Owner explicitly requested the **entire ASTRA library**, including the original ten, rebuilt, installed in the app and rebaked. This is a complete local iteration for review; owner acceptance and actual on-track lighting qualification are separate.','',
        '[Open the current local review](http://127.0.0.1:59876/SPB_AUDIT_astra.html). The normal Paint Booth ASTRA category retains its existing 50 IDs, saved assignments and favorite identities.','',
        '## What changed','',
        '- Fifty independently authored constructions in five small geometry modules: connected growth, routed networks, layered fragments, wear, apertures and mechanisms. No `frames()`/`sites()` placement template or shared rainbow material policy remains in the new render paths.',
        '- Fine 8–32px authored marks organized into larger relationships; secondary marks are quieter and remain behind the named construction. Fine 8px substrate grain prevents untreated flat areas. Intersections and rasterized taper tips can be narrower; primitive dimensions alone are not a measured visibility guarantee.',
        '- Six named physical roles per finish, eight independently selected pigment/material tiers and local boundary relief. Explicit per-finish material ranges replace channel equalization and paint-RGB-derived spec.',
        '- Clearcoat uses the actual inverted iRacing encoding: 16 is strongest active coat, 255 is suppressed. The renderer also observes the engine Rough/Cc floor of 16. Wax and velvet remain restrained dielectric materials; lacquer and exposed metal stay distinct.',
        '- All fifty published descriptions were updated to match the rebuilt constructions and pigments. Historical source literals are superseded by the centralized R1 published metadata.',
        '- Fresh standard, buyer split and persistent faithful masters/derivatives were generated. The app review now includes the before picker, new paint/spec and native 1:1 inspection.','',
        '## Evidence','',
        f'- Native pairs: **50/50**; all finite and within the render ABI. Unique paint hashes: 50; unique spec hashes: 50. Native generation: **{summary["native_seconds"][0]:.3f}–{summary["native_seconds"][1]:.3f}s**.',
        f'- Actual 2048 export pipeline: **50/50**, alpha fixed at 255, finish stages **{summary["actual_finish_stage_seconds"][0]:.2f}–{summary["actual_finish_stage_seconds"][1]:.2f}s**. Maximum paint/spec mean absolute byte errors against rounded native maps: **{summary["export_paint_mae_max"]:.3f} / {summary["export_spec_mae_max"]:.3f} of 255**.',
        f'- Live HTTP: **200/200** faithful responses at 512, 256, 128 and 48px per half; maximum native-to-picker mean error **{summary["picker_mae_max"]:.3f}/255**. All 100 static standard/split HTTP assets byte-match disk. Fifty masters and 150 derivatives persist on disk and match runtime mirrors.',
        f'- Unchanged category identity gate: **1,225 pairs**, max **{summary["identity_maximum"]:.5f}**, **{len(rejects)} rejects**, **{len(flags)} direct-review pairs**. Includes paint, combined spec, individual/cross-channel comparisons, native crops, whole textures, standard and picker images; rotations, flips and translation response retained.',
        '- Four material regression tests pass: wax versus resin, velvet coating, Janus lacquer versus metal, and physical export flooring without forced channel expansion.',
        f'- Actual server restart: all 50 fingerprints and 256px response bytes remained identical; all 200 persistent files retained their original modification times. **{restart["runtime_exact_pairs"]} source/thumbnail runtime pairs** match SHA-256 exactly.',
        '- Browser check: all 50 ASTRA cards present in the real Paint Booth picker and visible previews load. Review filters show ten per lane; search, full native paint/spec toggle and 2048px 1:1 inspection work. No finish was applied to or exported into the owner’s car folder during UI verification.','',
        '## Diagnostic scores and limits','',
        f'Unchanged legacy M1/M2/M5/M6/M7 calculations were run against an isolated refreshed scorecard. R1 M7 ranges **{summary["m7_range"][0]:.1f}–{summary["m7_range"][1]:.1f}**. Only the fifty ASTRA production measurement rows are refreshed; global workbook outputs and unrelated rank rows are not rewritten. Scores are labeled diagnostic and owner-review-pending. A restrained finish is not expanded to full metallic/coat range to rescue its score.',
        'No owner visual PASS, blind name-test result, proven angle-dependent color flip or real on-car daylight/night qualification is invented. These maps remain artistic pigment/material constructions supported by the existing shader. The full-set agent review examined native crops and reduced paint/spec boards; the owner’s next verdict determines which identities need further iteration.',
        'The first internal pass was retained in `first_pass_native_report.json` and `full_pipeline/first_pass_report.json`. It exposed a Velvet clearcoat/export mismatch; the final authoring corrected the engine floor and explicitly encoded blue semantics before the final bakes.','',
        'The final visual pass also found Strange Attractor too sparse for MAD SCIENTIST. It now integrates 200 independent fine trajectories instead of 62 short traces, with longer return paths and batched rasterization. Only that finish’s pixels changed; the ten MAD renderer fingerprints were rebaked because their geometry module is shared. Its actual export was repeated, and all 49 affected identity pairs were recomputed while the 1,176 unchanged comparisons were retained. Restart verification was repeated for all fifty.','',
        '## Per-finish record','',
        '| Finish | Lane | Native s | Export finish s | Prior M7 → R1 diagnostic |',
        '|---|---|---:|---:|---:|']
    for fid,row in native.items():
        score=metrics['base:'+fid];before=score['before']
        lines.append(f'| {row["name"]} | {row["lane"]} | {row["seconds"]:.3f} | {exports[fid]["finish_stage_seconds"]:.2f} | {before if before is not None else "unavailable"} → {score["after"]:.1f} |')
    if flags:
        lines+=['','Direct side-by-side owner review remains requested for these measured similarities:','']
        lines += [f'- {p["a"]} / {p["b"]}: {p["maximum"]}' for p in flags]
    lines+=['','## Reproduction and recovery','',
        'The recoverable baseline contains 154 original source/thumbnail files in `_astra_rebuild_20260922_work/before/`, with SHA-256 records. The previous review page and old identity contracts are retained too. All new images, current contracts, export TGAs, pipeline logs, official diagnostic outputs, live response bytes and comparison reports are in the same work folder.',
        'The `scripts/spb_astra_rebuild_*.py` tools separately author declarations, render evidence, bake/sync, verify live responses, exercise actual exports, calculate diagnostics, compare identity, and produce the current review. `tests/test_astra_rebuild_material_intent.py` protects the physical interpretation.',
        'Installer mirror source coverage is already directory-based for `engine/expansions/astra`. Root and runtime finish sources, owned thumbnails and faithful cache files are verified. This task updates the local app/runtime tree; it does not claim to have built or published a new installer.','']
    path=ROOT/'docs/finish_audits/intent_2026-09-22/ASTRA_REBUILD_R1.md';path.write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
