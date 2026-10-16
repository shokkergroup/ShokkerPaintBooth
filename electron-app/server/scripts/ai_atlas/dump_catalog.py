#!/usr/bin/env python
"""Dump the RUNNING app's full finish catalogue to _easy_claude_work/atlas/catalog_dump.json (input of build_atlas.py).

Why from the running page: the static finish-data file alone has ~2,440 specials / 181 spec patterns; other files add the rest at runtime
(3,035 / 301), and the buyer-visible shelves come from spbEasy._internals().buildCatalogSections().

Usage:  python scripts/ai_atlas/dump_catalog.py [--cdp 9444] [--url http://127.0.0.1:59876/]
  --cdp N   attach to a Chrome started with --remote-debugging-port=N (otherwise a headless Chromium is launched by Playwright)
"""
import argparse, json, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / '_easy_claude_work' / 'atlas' / 'catalog_dump.json'
JS = """() => {
  const o = {};
  const isUI = v => /(^|::)ui_/.test(String((v && v.id) || v)); // maintainer's own Shokk Drop imports never ship (purge_user_imports.py)
  const pick = (a, keys) => a.filter(x => !isUI(x)).map(x => { const r = {}; keys.forEach(k => { if (x[k] !== undefined) r[k] = x[k]; }); return r; });
  o.bases = pick(BASES, ['id', 'name', 'desc', 'swatch', 'swatch2', 'swatch3', 'astraLane', 'tags', 'category']);
  o.monolithics = pick(MONOLITHICS, ['id', 'name', 'desc', 'swatch', 'swatch2', 'swatch3', 'tags', 'category']);
  o.patterns = pick(PATTERNS, ['id', 'name', 'desc', 'swatch', 'tags', 'category']);
  o.spec_patterns = pick(SPEC_PATTERNS, ['id', 'name', 'desc', 'category', 'defaults', 'defaultChannels', 'legacy']);
  const g = n => { try { return eval(n); } catch (e) { return null; } };
  o.BASE_GROUPS = g('BASE_GROUPS'); o.SPECIAL_GROUPS = g('SPECIAL_GROUPS'); o.MONOLITHIC_GROUPS = g('MONOLITHIC_GROUPS'); o.PATTERN_GROUPS = g('PATTERN_GROUPS'); o.SPEC_PATTERN_GROUPS = g('SPEC_PATTERN_GROUPS');
  o.BASE_GROUP_SUBSECTIONS = g('BASE_GROUP_SUBSECTIONS'); o.FINISH_TAGS = g('FINISH_TAGS'); o.FINISH_COUNT_BY_CATEGORY = g('FINISH_COUNT_BY_CATEGORY');
  const I = spbEasy._internals();
  o.sections = (I.buildCatalogSections() || []).map(s => ({ title: s.title, ids: (s.ids || s.keys || []).filter(i => !isUI(i)) })); o.top = I.buildTopShelf() || [];
  return o; }"""

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--cdp', type=int, default=0); ap.add_argument('--url', default='http://127.0.0.1:59876/'); a = ap.parse_args()
    with sync_playwright() as p:
        if a.cdp:
            br = p.chromium.connect_over_cdp('http://127.0.0.1:%d' % a.cdp); pg = br.contexts[0].new_page()
        else:
            br = p.chromium.launch(headless=True); pg = br.new_page()
        pg.goto(a.url, wait_until='domcontentloaded'); pg.wait_for_timeout(12000)
        for _ in range(30):
            if pg.evaluate("() => typeof spbEasy !== 'undefined' && typeof BASES !== 'undefined' && BASES.length > 0 && MONOLITHICS.length > 0"): break
            pg.wait_for_timeout(2000)
        d = pg.evaluate(JS)
        pg.close()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(d, ensure_ascii=False), encoding='utf-8')
    print({k: (len(v) if hasattr(v, '__len__') else v) for k, v in d.items()})

if __name__ == '__main__':
    sys.exit(main())
