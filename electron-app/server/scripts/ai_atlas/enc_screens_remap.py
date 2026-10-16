"""Lane S pass 2: also credit EXISTING screens to further articles they genuinely show (idempotent, atomic).
    python scripts/ai_atlas/enc_screens_remap.py
Only ids that already exist in screens.json (both screen and article) are touched; run after the captures."""
import json, os, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
MAN = ROOT / "data" / "encyclopedia" / "screens.json"
# screen id -> extra article ids it truly illustrates
ALSO = {
    "ui_undo_history": ["history.panel"],
    "ui_shortcuts_dialog": ["shortcuts.table", "tools.shortcuts_quick"],
    "ui_finish_picker": ["shortcuts.finish_shelves"],
    "ui_finish_picker_cards": ["shortcuts.finish_shelves", "finishes.surface_intent"],
    "cat_foundation": ["finishes.surface_intent", "finishes.ghost_geometry_clearcoat"],
    "spec_candy": ["shortcuts.spec_cheat_sheet", "spec.metal_rough_grid"],
    "spec_chrome": ["shortcuts.spec_cheat_sheet", "spec.metal_rough_grid", "finishes.surface_intent"],
    "spec_matte": ["shortcuts.spec_cheat_sheet", "spec.metal_rough_grid"],
    "flow_step6_recipe_card": ["spec.colour_space_and_files"],
    "cat_spectrum_shift": ["spec.angle_reveal"],
    "car_spectrum_event_horizon": ["spec.angle_reveal"],
    "pair_base_vs_foundation": ["spec.paint_spec_marriage"],
    "pair_colour_source": ["spec.paint_spec_marriage"],
    "ui_layers_column": ["layers.open_psd"],
    "ui_header_rows": ["layers.open_psd"],
    "ui_zones_column": ["zones.recipe_split_car"],
    "ui_zone_apply_area": ["zones.recipe_split_car"],
    "flow_step2_zone_added": ["zones.recipe_split_car"],
    "pair_zone_added": ["zones.recipe_split_car"],
    "ui_chat_car_parts": ["zones.named_parts"],
    "ui_zone_empty_message": ["zones.not_showing"],
    "spec_wear": ["finishes.wear"],
}
d = json.loads(MAN.read_text(encoding="utf8"))
by = {s["id"]: s for s in d["screens"]}
n = 0
for sid, arts in ALSO.items():
    s = by.get(sid)
    if not s:
        print("missing screen", sid); continue
    for a in arts:
        if a not in s["article_ids"]:
            s["article_ids"].append(a); n += 1
t = str(MAN) + ".tmp"
Path(t).write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf8"); os.replace(t, MAN)
print("remap: +%d article links" % n)
