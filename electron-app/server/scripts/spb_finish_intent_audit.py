"""Read-only catalog census. Cached picker measurements are diagnostics, not quality scores.

Run from repository root: python scripts/spb_finish_intent_audit.py
Re-extracts the current JS catalog; never renders, rebakes or modifies finishes.
"""
from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/finish_audits/intent_2026-09-22'
FORCED = {'Light Waves', 'Metallic Halos', 'Sparkle Systems', 'Spectral Reactive',
          '★ Spectrum Shift', 'Spectrum Shift'}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def histogram_stats(values):
    counts = np.bincount(values.ravel())
    p = counts[counts > 0] / counts.sum()
    return {'effective_bins': round(float(np.exp(-np.sum(p * np.log(p)))), 2),
            'bins_at_least_1pct': int(np.sum(p >= .01))}


def measure(paint, spec):
    """Display-space summaries only; spec bytes may be filtered by picker resizing."""
    hsv = np.asarray(paint.convert('HSV')).astype(float)
    chromatic = (hsv[:, :, 1] >= 64) & (hsv[:, :, 2] >= 32)
    hues = (hsv[:, :, 0] * 12 / 256).astype(int)
    hue_counts = np.bincount(hues[chromatic], minlength=12) / hues.size
    p = np.asarray(paint).astype(float)
    s = np.asarray(spec).astype(float)
    quantized = (s // 16).astype(int)
    packed = quantized[:, :, 0] * 256 + quantized[:, :, 1] * 16 + quantized[:, :, 2]
    result = {
        'hue_families_1pct': int(np.sum(hue_counts >= .01)),
        'chromatic_area': round(float(chromatic.mean()), 4),
        'paint_luma_std': round(float((p @ np.array([.2126, .7152, .0722])).std()), 3),
        'spec_states_16byte': histogram_stats(packed),
        'channels': {},
    }
    for i, name in enumerate(('M', 'Rough', 'Cc')):
        a = s[:, :, i]
        lo, median, hi = np.percentile(a, [1, 50, 99])
        result['channels'][name] = {
            'p01': round(float(lo), 2), 'median': round(float(median), 2),
            'p99': round(float(hi), 2), 'robust_span': round(float(hi-lo), 2),
            'std': round(float(a.std()), 3),
        }
    return result


def band_fit(value, outer_low, ideal_low, ideal_high, outer_high):
    """Proposed two-sided target utility. Bounds require owner-anchor calibration."""
    if not outer_low < ideal_low <= ideal_high < outer_high:
        raise ValueError('Expected outer_low < ideal_low <= ideal_high < outer_high')
    if value is None:
        return None
    if ideal_low <= value <= ideal_high:
        return 100.0
    if value < ideal_low:
        return max(0.0, 100 * (value - outer_low) / (ideal_low - outer_low))
    return max(0.0, 100 * (outer_high - value) / (outer_high - ideal_high))


def evidence_interval(scores, weights):
    """Missing axes retain their weight: return interval, never a inflated point score."""
    if not weights or any(w < 0 for w in weights.values()) or sum(weights.values()) <= 0:
        raise ValueError('Positive total nonnegative weight required')
    total = sum(weights.values())
    observed = {k: v for k, v in scores.items() if k in weights and v is not None}
    if any(not 0 <= v <= 100 for v in observed.values()):
        raise ValueError('Scores must be in [0,100]')
    coverage = sum(weights[k] for k in observed) / total
    low = sum(weights[k] * v for k, v in observed.items()) / total
    return {'lower': round(low, 2), 'upper': round(low + 100*(1-coverage), 2),
            'coverage': round(coverage, 4),
            'score': round(low, 2) if coverage >= 1-1e-10 else None}


def catalog_snapshot():
    js = """const fs=require('fs'),vm=require('vm');
const ctx={console:{log(){},warn(){},error(){}},setTimeout(){}};
vm.createContext(ctx);
vm.runInContext(fs.readFileSync('paint-booth-0-finish-data.js','utf8'),ctx,{timeout:10000});
console.log(JSON.stringify(vm.runInContext('({bases:BASES,baseGroups:BASE_GROUPS,specials:MONOLITHICS,specialGroups:SPECIAL_GROUPS})',ctx)));"""
    return json.loads(subprocess.check_output(['node', '-e', js], cwd=ROOT, text=True, encoding='utf8'))


def load_metric(name):
    path = ROOT / '_workbook_metrics' / (name + '.json')
    data = json.loads(path.read_text(encoding='utf8'))
    return data, {'path': str(path.relative_to(ROOT)), 'sha256': digest(path),
                  'generated': data.get('generated')}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    catalog = catalog_snapshot()
    (OUT / 'catalog_snapshot.json').write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding='utf8')
    metrics, sources = {}, []
    for name in ['m1_sibling_diff', 'm2_intent_fit', 'm5_spec_paint_coherence',
                 'm6_intent_floor_ceiling', 'm7_composite']:
        data, source = load_metric(name)
        metrics[name[:2]] = data['byFinish']
        sources.append(source)
    protected = json.loads((ROOT / 'scripts/protected_finishes.json').read_text(encoding='utf8'))['locked']
    for fid in ('fl_eddy_impedance','fl_photoelastic_iso','fl_isoclinic_dark','fl_magnetic_particle'):
        protected[fid] = {'why': 'Owner 2026-09-18: preserve four FLAW LAB favorites; docs/finish_audits/FLAW_LAB_REBUILD_2026-09-18.md'}
    rows, duplicates, categories = [], defaultdict(list), defaultdict(list)
    for surface, items_key, groups_key in [('base', 'bases', 'baseGroups'), ('monolithic', 'specials', 'specialGroups')]:
        memberships = defaultdict(list)
        for group, ids in catalog[groups_key].items():
            for fid in ids:
                memberships[fid].append(group)
        for item in catalog[items_key]:
            fid = item['id']
            key = surface + ':' + fid
            old = metrics['m7'].get(key, {})
            m6 = metrics['m6'].get(key, {})
            row = {'key': key, 'surface': surface, 'id': fid, 'name': item.get('name', fid),
                   'description': item.get('desc', ''), 'groups': memberships[fid],
                   'protected': fid in protected, 'intent_status': 'needs per-finish contract review',
                   'legacy_m7': old.get('composite'), 'legacy_components': old.get('components', {}),
                   'legacy_category': m6.get('category'), 'legacy_m6': m6.get('score'),
                   'legacy_m2_token_source': metrics['m2'].get(key, {}).get('tokenSource'),
                   'legacy_forced_100_category': m6.get('category') in FORCED,
                   'quality_score': None, 'live_verified': False, 'native_verified': False,
                   'name_test': 'unreviewed', 'flags': [], 'assets': {}}
            if fid in protected:
                row['protection_reason'] = protected[fid]['why']
            for kind, path in [('standard', ROOT/'thumbnails'/surface/(fid+'.png')),
                               ('split', ROOT/'thumbnails/picker_split'/surface/(fid+'.png'))]:
                row['assets'][kind] = {'path': path.relative_to(ROOT).as_posix(), 'exists': path.is_file()}
                if path.is_file():
                    row['assets'][kind].update(sha256=digest(path), modified_utc=datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat())
            if not row['assets']['standard']['exists']:
                row['flags'].append('no_standard_disk_asset')
            split = ROOT / row['assets']['split']['path']
            if split.is_file():
                try:
                    with Image.open(split) as im:
                        w, h = im.size
                        row['assets']['split']['dimensions'] = [w, h]
                        if w != 2*h:
                            raise ValueError(f'Unexpected split aspect {w}x{h}')
                        paint = im.crop((0, 0, h, h)).convert('RGB')
                        spec = im.crop((h, 0, w, h)).convert('RGB')
                        for kind, half in [('paint', paint), ('spec', spec)]:
                            # Include dimensions; these groups prove identical cached pixels only.
                            sig = hashlib.sha256(str(half.size).encode()+half.tobytes()).hexdigest()
                            row[kind+'_pixel_sha256'] = sig
                            duplicates[(kind, sig)].append(key)
                        size = min(128, h)
                        row['measured'] = measure(paint.resize((size,size), Image.Resampling.BOX), spec.resize((size,size), Image.Resampling.BOX))
                        row['measurement_size'] = size
                        if row['measured']['hue_families_1pct'] <= 1:
                            row['flags'].append('restrained_palette_check_intent')
                        for c, values in row['measured']['channels'].items():
                            if values['robust_span'] < 8:
                                row['flags'].append('low_picker_span_'+c)
                except (OSError, ValueError) as exc:
                    row['asset_error'] = str(exc)
                    row['flags'].append('unreadable_or_nonstandard_split')
            else:
                row['flags'].append('no_split_disk_asset')
            if row['legacy_m7'] is None:
                row['flags'].append('no_legacy_m7')
            if row['legacy_m6'] is None:
                row['flags'].append('no_legacy_intent_profile')
            if row['legacy_forced_100_category']:
                row['flags'].append('legacy_category_forces_100')
            if not memberships[fid]:
                row['flags'].append('no_group_membership')
            rows.append(row)
            for group in memberships[fid] or ['(ungrouped)']:
                categories[(surface, group)].append(row)
        print(f'{surface}: {len(catalog[items_key])} entries measured', flush=True)
    exact = [{'surface_kind': k[0], 'sha256': k[1], 'members': v} for k,v in duplicates.items() if len(v)>1]
    summaries = []
    for (surface, category), members in categories.items():
        counts = Counter(flag for row in members for flag in row['flags'])
        summaries.append({'surface': surface, 'category': category, 'count': len(members),
                          'measured': sum('measured' in row for row in members), 'flags': dict(counts)})
    summary = {'entries': len(rows), 'surfaces': dict(Counter(r['surface'] for r in rows)),
               'unique_ids_across_surfaces': len({r['id'] for r in rows}),
               'measured_pairs': sum('measured' in r for r in rows),
               'flags': dict(Counter(f for r in rows for f in r['flags'])),
               'exact_cached_pixel_groups': len(exact), 'categories': summaries}
    report = {'schema': 'spb-intent-census/1', 'generated_utc': datetime.now(timezone.utc).isoformat(),
              'scope': 'All BASES plus separate MONOLITHICS snapshot; group membership retained; no engine or live fetches.',
              'limitations': ['Cached disk assets are not proof of current runtime output.',
                 '128px picker measurements cannot prove native feature scale or material semantics.',
                 'Hue bins and low-span thresholds are triage descriptors, never pass/fail thresholds.',
                 'Exact matches may be aliases, intended uniform substrates, stale bakes or duplicates; not adjudicated.',
                 'No finish has a new quality score until intent, calibration and required evidence are verified.'],
              'catalog_sha256': digest(ROOT/'paint-booth-0-finish-data.js'), 'legacy_sources': sources,
              'summary': summary, 'rows': rows, 'exact_cached_pixel_groups': exact}
    (OUT/'census.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf8')
    fields = ['key','name','groups','legacy_m7','legacy_category','quality_score','flags']
    with (OUT/'finish_inventory.csv').open('w', newline='', encoding='utf-8-sig') as fp:
        writer = csv.DictWriter(fp, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: ' | '.join(row[k]) if isinstance(row[k],list) else row[k] for k in fields})
    write_dashboard(report)
    print(json.dumps({k:v for k,v in summary.items() if k!='categories'}, ensure_ascii=False, indent=2))


def write_dashboard(report):
    live_path = OUT/'live_census.json'
    live = {r['key']:r for r in json.loads(live_path.read_text(encoding='utf8'))['rows']} if live_path.is_file() else {}
    compact = []
    for r in report['rows']:
        row = {k:r.get(k) for k in ['key','name','description','groups','surface','flags','legacy_m7','legacy_category','measured','protected','assets']}
        row['evidence_label']='Historical static disk pair; not live verified'
        row['asset_url']='../../../'+r['assets']['split']['path'] if r['assets']['split']['exists'] else None
        current=live.get(r['key'])
        if current and current['status']=='ok':
            row['measured']=current['measured']
            row['evidence_label']=current['evidence']
            row['asset_url']=current['asset']
            row['flags']=[f for f in row['flags'] if not f.startswith('low_picker_span_') and f!='restrained_palette_check_intent']
            if row['measured']['hue_families_1pct']<=1:
                row['flags'].append('restrained_palette_check_intent')
            for channel,values in row['measured']['channels'].items():
                if values['robust_span']<8:row['flags'].append('low_picker_span_'+channel)
        elif current:
            row['flags']=[*row['flags'],'live_response_unavailable']
        compact.append(row)
    payload = json.dumps(compact, ensure_ascii=False).replace('<', '\\u003c')
    template = (Path(__file__).with_name('spb_finish_intent_dashboard.html')).read_text(encoding='utf8')
    (OUT/'AUDIT.html').write_text(template.replace('__DATA__', payload), encoding='utf8')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf8')
    main()
