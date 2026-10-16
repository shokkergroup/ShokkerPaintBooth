"""Phase 2: add inventory ids to covers[] of EXISTING lane-C articles whose text already explains them (idempotent)."""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import enc_write_C as W

ROOT = W.ROOT
INV = [r['id'] for r in json.loads((ROOT / 'scripts' / 'ai_atlas' / 'enc_inventory.json').read_text(encoding='utf-8'))['records']]


def one(prefix):
    m = [i for i in INV if i.startswith(prefix)]
    assert len(m) == 1, (prefix, m)
    return m[0]


MAP = {
    'workflows.user_id_and_folder': ['doc.10.support_the_iracing_user_id'],
    'preview_render.number_modes': ['doc.10.support_custom_number_vs_sim'],
    'preview_render.where_files_go': ['doc.10.support_where_iracing_looks'],
    'preview_render.auto_deploy': ['doc.10.support_how_files_get_into_iracing'],
    'preview_render.reload_in_iracing': ['doc.10.support_making_iracing_show_the_new_paint'],
    'preview_render.trading_paints_mip': ['doc.10.support_the_spec_file_and_the_mip'],
    'preview_render.render_history_stats': ['html.render_history.2481'],
    'support.not_in_iracing': ['doc.10.support_checklist_when_my_paint'],
    'support.colours_differ': ['doc.10.support_the_paint_looks_different'],
    'support.render_slow_or_fails': ['doc.10.support_the_render_button_will_not_start'],
    'support.error_messages': ['doc.10.support_render_errors'],
    'support.preview_render_mismatch': ['doc.10.support_the_live_preview_is_stuck'],
    'support.trading_paints': ['doc.10.support_trading_paints_other'],
    'support.reporting_problem': ['doc.10.support_how_to_help_a_buyer'],
    'support.flat_or_shiny': ['doc.03.recipe_why_does_it_look_flat'],
    'support.zone_no_show': ['doc.03.recipe_why_does_it_look_flat'],
    'settings.overview': ['doc.10.support_where_the_settings_are'],
    'ai_copilot.mcp_claude_chatgpt': ['doc.10.support_the_two_ways_to_use_claude', 'doc.04.chatgpt_codex_subscription_connection'],
    'ai_copilot.offline_vs_ai': ['doc.04.works_without_an_ai_key', 'doc.04.three_ways_to_talk_to_shokker'],
    'workflows.what_is_shokker': ['doc.10.support_limits_and_things_shokker_does_not_do'],
    'recipes.two_tone': ['doc.03.recipe_matte_body_with_gloss_accents'],
}

n = 0
for aid, prefixes in MAP.items():
    dom = aid.split('.')[0]
    doc = W._load(dom)
    art = [a for a in doc['articles'] if a['id'] == aid]
    assert art, aid
    art = art[0]
    for p in prefixes:
        i = one(p)
        if i not in art['covers']:
            art['covers'].append(i)
            n += 1
    W._save(dom, doc)
print('covers added', n)
